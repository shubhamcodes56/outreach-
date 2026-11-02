import os
import json
import re
import smtplib
import imaplib
import threading
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import config

KOLKATA = ZoneInfo("Asia/Kolkata")
ACCOUNTS_DB_FILE = os.path.join(os.path.dirname(__file__), "accounts_db.json")
ACCOUNTS_LOCK = threading.RLock()


def local_now():
    return datetime.now(KOLKATA)


def next_local_midnight():
    tomorrow = local_now().date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), KOLKATA)


class AccountsManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AccountsManager, cls).__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self.accounts = {}
        self._load()

    def _load(self):
        with ACCOUNTS_LOCK:
            if os.path.exists(ACCOUNTS_DB_FILE):
                try:
                    with open(ACCOUNTS_DB_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self.accounts = data
                except Exception as e:
                    print(f"[!] Error loading accounts DB: {e}")
                    self.accounts = {}

            # Seed with default account from config/.env if empty
            if not self.accounts and config.GMAIL_USER and config.GMAIL_APP_PASSWORD:
                default_email = config.GMAIL_USER.strip().lower()
                self.accounts[default_email] = {
                    "email": default_email,
                    "app_password": config.GMAIL_APP_PASSWORD.strip(),
                    "sender_name": config.SENDER_NAME or "Shubham Dixit",
                    "daily_limit": max(50, int(config.DAILY_LIMIT or 100)),
                    "sent_today": 0,
                    "last_sent_date": local_now().date().isoformat(),
                    "status": "ACTIVE",
                    "error_message": None,
                    "cooldown_until": None,
                    "created_at": local_now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self._save()

            self._reset_daily_quotas_if_needed()

    def _save(self):
        with ACCOUNTS_LOCK:
            tmp = ACCOUNTS_DB_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, indent=4, ensure_ascii=False)
            os.replace(tmp, ACCOUNTS_DB_FILE)

    def _reset_daily_quotas_if_needed(self):
        today_str = local_now().date().isoformat()
        changed = False
        with ACCOUNTS_LOCK:
            for acc in self.accounts.values():
                if acc.get("last_sent_date") != today_str:
                    acc["sent_today"] = 0
                    acc["last_sent_date"] = today_str
                    if acc.get("status") == "QUOTA_EXCEEDED":
                        acc["status"] = "ACTIVE"
                        acc["error_message"] = None
                        acc["cooldown_until"] = None
                    changed = True
                elif acc.get("status") == "QUOTA_EXCEEDED" and acc.get("cooldown_until"):
                    try:
                        cooldown = datetime.fromisoformat(acc["cooldown_until"])
                        if cooldown.tzinfo is None:
                            cooldown = cooldown.replace(tzinfo=KOLKATA)
                        if cooldown <= local_now():
                            acc["status"] = "ACTIVE"
                            acc["error_message"] = None
                            acc["cooldown_until"] = None
                            changed = True
                    except Exception:
                        pass
            if changed:
                self._save()

    @staticmethod
    def test_credentials(email_addr: str, app_password: str) -> tuple[bool, str]:
        """Validates Gmail SMTP & IMAP credentials live."""
        email_clean = email_addr.strip().lower()
        pwd_clean = app_password.strip()

        if not email_clean.endswith("@gmail.com"):
            return False, "Only valid @gmail.com addresses are supported."

        if not pwd_clean:
            return False, "Google App Password cannot be empty."

        # 1. Test SMTP
        try:
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=12) as smtp:
                smtp.starttls()
                smtp.login(email_clean, pwd_clean)
        except smtplib.SMTPAuthenticationError:
            return False, (
                "SMTP Authentication Failed: Incorrect password or 2-Step Verification disabled. "
                "Please generate a 16-character App Password at myaccount.google.com/apppasswords"
            )
        except Exception as e:
            return False, f"SMTP Connection Error: {str(e)}"

        # 2. Test IMAP
        try:
            imap = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT, timeout=12)
            imap.login(email_clean, pwd_clean)
            imap.select("inbox")
            imap.logout()
        except Exception as e:
            return False, f"IMAP Access Error: {str(e)}. Please ensure IMAP access is enabled in Gmail settings."

        return True, "Authenticated successfully! SMTP & IMAP verified."

    def add_account(self, email_addr: str, app_password: str, sender_name: str, daily_limit: int = 200) -> tuple[bool, str]:
        email_clean = email_addr.strip().lower()
        pwd_clean = app_password.strip().replace("  ", " ")
        name_clean = sender_name.strip() or config.SENDER_NAME or "Shubham Dixit"
        limit = max(10, min(500, int(daily_limit)))

        # Test credentials live before adding
        success, msg = self.test_credentials(email_clean, pwd_clean)
        if not success:
            return False, msg

        with ACCOUNTS_LOCK:
            existing = self.accounts.get(email_clean, {})
            self.accounts[email_clean] = {
                "email": email_clean,
                "app_password": pwd_clean,
                "sender_name": name_clean,
                "daily_limit": limit,
                "sent_today": existing.get("sent_today", 0),
                "last_sent_date": existing.get("last_sent_date", local_now().date().isoformat()),
                "status": "ACTIVE",
                "error_message": None,
                "cooldown_until": None,
                "created_at": existing.get("created_at", local_now().strftime("%Y-%m-%d %H:%M:%S"))
            }
            self._save()

        return True, f"Account {email_clean} connected and verified successfully!"

    def update_daily_limit(self, email_addr: str, new_limit: int) -> bool:
        with ACCOUNTS_LOCK:
            clean_em = email_addr.strip().lower()
            if clean_em in self.accounts:
                self.accounts[clean_em]["daily_limit"] = int(new_limit)
                self._save()
                return True
            return False

    def toggle_account(self, email_addr: str) -> tuple[bool, str]:
        email_clean = email_addr.strip().lower()
        with ACCOUNTS_LOCK:
            if email_clean not in self.accounts:
                return False, f"Account {email_clean} not found."
            acc = self.accounts[email_clean]
            if acc["status"] == "ACTIVE":
                acc["status"] = "PAUSED"
                msg = f"Account {email_clean} paused."
            else:
                acc["status"] = "ACTIVE"
                acc["error_message"] = None
                acc["cooldown_until"] = None
                msg = f"Account {email_clean} activated."
            self._save()
            return True, msg

    def delete_account(self, email_addr: str) -> tuple[bool, str]:
        email_clean = email_addr.strip().lower()
        with ACCOUNTS_LOCK:
            if email_clean not in self.accounts:
                return False, f"Account {email_clean} not found."
            del self.accounts[email_clean]
            self._save()
            return True, f"Account {email_clean} deleted successfully."

    def get_all_accounts(self, shared_db: dict = None) -> list:
        self._load()
        self._reset_daily_quotas_if_needed()
        result = []

        # Precompute per-account metrics from shared_db if provided
        metrics_by_sender = {}
        if shared_db and isinstance(shared_db, dict):
            for lead_em, rec in shared_db.items():
                sender = rec.get("assigned_sender")
                st = rec.get("status")
                if sender:
                    if sender not in metrics_by_sender:
                        metrics_by_sender[sender] = {
                            "lifetime": 0,
                            "active_convos": 0,
                            "recent_all": []
                        }
                    m = metrics_by_sender[sender]
                    if st in ["SENT", "NEGOTIATING", "MEETING_BOOKED", "FAILED"]:
                        m["lifetime"] += 1
                        if st in ["NEGOTIATING", "MEETING_BOOKED"]:
                            m["active_convos"] += 1
                        m["recent_all"].append({
                            "business_name": rec.get("lead_info", {}).get("Business Name", "Unknown"),
                            "lead_email": lead_em,
                            "status": st,
                            "timestamp": rec.get("last_updated", "")
                        })

            # Sort recent items by timestamp descending and take top 10
            for sender, m in metrics_by_sender.items():
                m["recent"] = sorted(
                    m["recent_all"],
                    key=lambda x: str(x.get("timestamp") or ""),
                    reverse=True
                )[:10]

        with ACCOUNTS_LOCK:
            for acc in self.accounts.values():
                pwd = acc.get("app_password", "")
                masked_pwd = (pwd[:4] + " **** **** " + pwd[-4:]) if len(pwd) >= 12 else "****"
                acc_email = acc["email"]
                m = metrics_by_sender.get(acc_email, {"lifetime": 0, "active_convos": 0, "recent": []})

                result.append({
                    "email": acc_email,
                    "sender_name": acc.get("sender_name", "Shubham Dixit"),
                    "daily_limit": acc.get("daily_limit", 200),
                    "sent_today": acc.get("sent_today", 0),
                    "sent_lifetime": m["lifetime"],
                    "active_conversations_count": m["active_convos"],
                    "recent_sends": m.get("recent", []),
                    "status": acc.get("status", "ACTIVE"),
                    "error_message": acc.get("error_message"),
                    "cooldown_until": acc.get("cooldown_until"),
                    "app_password_masked": masked_pwd,
                    "created_at": acc.get("created_at", "")
                })
        return result

    def get_best_sender_for_lead(self, preferred_email: str = None, excluded_emails: set = None) -> dict | None:
        """
        Smart sender selection with 100% conversation continuity & dynamic ratio balancing:
        1. If preferred_email is active, under quota, and not in excluded_emails, use it!
        2. Otherwise, pick the active unexcluded account with the lowest (sent_today / daily_limit) ratio.
        """
        self._load()
        self._reset_daily_quotas_if_needed()
        excluded = set(e.strip().lower() for e in (excluded_emails or []))

        with ACCOUNTS_LOCK:
            if preferred_email:
                pref_clean = preferred_email.strip().lower()
                if pref_clean not in excluded:
                    pref_acc = self.accounts.get(pref_clean)
                    if pref_acc and pref_acc.get("status") == "ACTIVE":
                        if pref_acc.get("sent_today", 0) < pref_acc.get("daily_limit", 200):
                            return dict(pref_acc)

            candidates = []
            for acc in self.accounts.values():
                em = acc["email"].lower()
                if em in excluded:
                    continue
                if acc.get("status") != "ACTIVE":
                    continue
                limit = acc.get("daily_limit", 200)
                sent = acc.get("sent_today", 0)
                if sent >= limit:
                    continue
                ratio = sent / max(1, limit)
                candidates.append((ratio, acc))

            if not candidates:
                return None

            # Sort by lowest load ratio, breaking ties randomly for even alternation
            candidates.sort(key=lambda x: (x[0], random.random()))
            return dict(candidates[0][1])

    def record_send_success(self, email_addr: str):
        email_clean = email_addr.strip().lower()
        today_str = local_now().date().isoformat()
        with ACCOUNTS_LOCK:
            acc = self.accounts.get(email_clean)
            if acc:
                if acc.get("last_sent_date") != today_str:
                    acc["sent_today"] = 1
                    acc["last_sent_date"] = today_str
                else:
                    acc["sent_today"] = acc.get("sent_today", 0) + 1

                if acc["sent_today"] >= acc.get("daily_limit", 200):
                    acc["status"] = "QUOTA_EXCEEDED"
                    acc["error_message"] = f"Daily limit of {acc['daily_limit']} emails reached."
                    acc["cooldown_until"] = next_local_midnight().isoformat()

                self._save()

    def record_quota_exceeded(self, email_addr: str, reason: str = "Gmail daily sending limit exceeded"):
        email_clean = email_addr.strip().lower()
        with ACCOUNTS_LOCK:
            acc = self.accounts.get(email_clean)
            if acc:
                acc["status"] = "QUOTA_EXCEEDED"
                acc["error_message"] = reason
                acc["cooldown_until"] = next_local_midnight().isoformat()
                self._save()

    def record_auth_error(self, email_addr: str, reason: str):
        email_clean = email_addr.strip().lower()
        with ACCOUNTS_LOCK:
            acc = self.accounts.get(email_clean)
            if acc:
                acc["status"] = "AUTH_FAILED"
                acc["error_message"] = reason[:80]
                self._save()

    def get_account_by_email(self, email_addr: str) -> dict | None:
        email_clean = email_addr.strip().lower()
        with ACCOUNTS_LOCK:
            acc = self.accounts.get(email_clean)
            return dict(acc) if acc else None

    def get_all_active_accounts_raw(self) -> list[dict]:
        with ACCOUNTS_LOCK:
            return [dict(acc) for acc in self.accounts.values() if acc.get("status") in ["ACTIVE", "QUOTA_EXCEEDED"]]
