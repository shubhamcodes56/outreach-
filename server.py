import sys
import os
import time
import json
import threading
import random
import re
import smtplib
import imaplib
import email
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.stdout.reconfigure(encoding="utf-8")

import config
from ai_agent import AIAgent, AIProviderRateLimitError
from mail_manager import MailManager, ensure_portfolio_link, is_gmail_quota_error, portfolio_optout_requested
from accounts_manager import AccountsManager
from uk_scale_leads import harvest_real_uk_leads

app = Flask(__name__)
CORS(app)

# Global Engine Controls
AUTO_SEND_STATE_FILE = os.path.join(os.path.dirname(__file__), "auto_send_uk_state.json")
LEAD_SEARCH_STATE_FILE = os.path.join(os.path.dirname(__file__), "lead_search_uk_state.json")


def load_lead_search_state():
    if os.path.exists(LEAD_SEARCH_STATE_FILE):
        try:
            with open(LEAD_SEARCH_STATE_FILE, "r") as f:
                data = json.load(f)
                resume_after = data.get("resume_after")
                if resume_after:
                    resume_dt = datetime.fromisoformat(resume_after.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) >= resume_dt:
                        data["lead_search"] = True
                        data["resume_after"] = None
                        with open(LEAD_SEARCH_STATE_FILE, "w") as out:
                            json.dump(data, out, indent=4)
                        add_log("[HUNTER RESUMED] 48-hour re-outreach window ended! Automatic lead hunting resumed.")
                        return True
                    else:
                        return False
                return data.get("lead_search", True)
        except Exception:
            pass
    return True


def save_lead_search_state(val):
    try:
        data = {"lead_search": val}
        with open(LEAD_SEARCH_STATE_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


LEAD_SEARCH_ENABLED = load_lead_search_state()

HARVEST_INTERVAL_SECONDS = 60
HARVEST_BATCH_SIZE = 30
HARVEST_LOCK = threading.Lock()
WORKER_LOGS = []
LOG_LOCK = threading.Lock()
DB_LOCK = threading.RLock()
SENDER_STATE_LOCK = threading.RLock()
KOLKATA = ZoneInfo("Asia/Kolkata")
SENDER_STATE_FILE = os.path.join(os.path.dirname(__file__), "sender_state.json")
INSTANCE_LOCK_HANDLE = None


def local_now():
    return datetime.now(KOLKATA)


def load_sender_state():
    try:
        with open(SENDER_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        pause_until = datetime.fromisoformat(state["pause_until"]) if state.get("pause_until") else None
        if pause_until and pause_until.tzinfo is None:
            pause_until = pause_until.replace(tzinfo=KOLKATA)
        return pause_until, state.get("pause_reason")
    except (OSError, ValueError, KeyError, TypeError):
        return None, None


SENDER_PAUSE_UNTIL, SENDER_PAUSE_REASON = load_sender_state()


def save_sender_state():
    with SENDER_STATE_LOCK:
        state = {
            "pause_until": SENDER_PAUSE_UNTIL.isoformat() if SENDER_PAUSE_UNTIL else None,
            "pause_reason": SENDER_PAUSE_REASON,
        }
        tmp_file = SENDER_STATE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_file, SENDER_STATE_FILE)


def set_sender_pause(until, reason):
    global SENDER_PAUSE_UNTIL, SENDER_PAUSE_REASON
    with SENDER_STATE_LOCK:
        if SENDER_PAUSE_UNTIL is None or until > SENDER_PAUSE_UNTIL:
            SENDER_PAUSE_UNTIL = until
            SENDER_PAUSE_REASON = reason
        save_sender_state()


def clear_expired_sender_pause():
    global SENDER_PAUSE_UNTIL, SENDER_PAUSE_REASON
    with SENDER_STATE_LOCK:
        if SENDER_PAUSE_UNTIL and SENDER_PAUSE_UNTIL <= local_now():
            SENDER_PAUSE_UNTIL = None
            SENDER_PAUSE_REASON = None
            save_sender_state()
            return True
    return False


def sender_pause_snapshot():
    with SENDER_STATE_LOCK:
        return SENDER_PAUSE_UNTIL, SENDER_PAUSE_REASON


def history_has_outbound(history):
    return any(str(item.get("sender", "")).strip().lower() != "client" for item in history if isinstance(item, dict))


def history_date(value):
    value = str(value or "").strip()
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", value):
            return value[:10]
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=KOLKATA)
        return parsed.astimezone(KOLKATA).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def sent_count_today():
    accounts_mgr = AccountsManager()
    accs = accounts_mgr.get_all_accounts()
    return sum(a.get("sent_today", 0) for a in accs)


def is_temporary_send_error(err):
    if isinstance(err, smtplib.SMTPResponseException):
        return 400 <= int(err.smtp_code) < 500
    if isinstance(err, smtplib.SMTPRecipientsRefused):
        return any(400 <= int(response[0]) < 500 for response in err.recipients.values())
    return isinstance(err, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, TimeoutError, ConnectionError))


def parse_retry_after(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.replace(tzinfo=KOLKATA) if parsed.tzinfo is None else parsed
    except ValueError:
        return None


def extract_bounced_recipients(msg):
    recipients = set()
    for part in msg.walk():
        if part.get_content_type().lower() == "message/delivery-status":
            blocks = part.get_payload()
            for block in blocks if isinstance(blocks, list) else []:
                action = str(block.get("Action", "")).strip().lower()
                status = str(block.get("Status", "")).strip()
                if action != "failed" and not status.startswith("5."):
                    continue
                for field in ("Final-Recipient", "Original-Recipient"):
                    value = str(block.get(field, ""))
                    match = re.search(r"[A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", value, re.I)
                    if match:
                        recipients.add(match.group(0).lower())
        if part.get_content_type().lower() == "text/plain":
            try:
                payload = part.get_payload(decode=True)
                body = payload.decode(part.get_content_charset() or "utf-8", errors="ignore") if payload else ""
            except Exception:
                body = ""
            for pattern in (
                r"wasn.t delivered to\s*<?([A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
                r"couldn.t be delivered to\s*<?([A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
                r"failed to deliver to\s*<?([A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
                r"recipient address rejected[^\r\n]*?<?([A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
            ):
                recipients.update(match.lower() for match in re.findall(pattern, body, re.I))
    x_failed = str(msg.get("X-Failed-Recipients", ""))
    recipients.update(match.lower() for match in re.findall(r"[A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", x_failed, re.I))
    return recipients


def add_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with LOG_LOCK:
        WORKER_LOGS.append(entry)
        if len(WORKER_LOGS) > 300:
            WORKER_LOGS.pop(0)


def load_initial_db():
    if os.path.exists(config.DB_FILE):
        try:
            with open(config.DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and len(data) > 0:
                    return data
        except Exception as e:
            print(f"[!] Error loading DB: {e}")
    return {}


SHARED_DB = load_initial_db()


def load_ai_drafter_pause():
    pending = [
        parse_retry_after(record.get("ai_retry_after"))
        for record in SHARED_DB.values()
        if record.get("status") == "NEW" and record.get("ai_retry_after")
    ]
    future = [retry_at for retry_at in pending if retry_at and retry_at > local_now()]
    return max(future) if future else None


AI_DRAFTER_PAUSE_UNTIL = load_ai_drafter_pause()


def persist_db():
    with DB_LOCK:
        if not SHARED_DB or len(SHARED_DB) == 0:
            return
        tmp_file = config.DB_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(SHARED_DB, f, indent=4, ensure_ascii=False)
        os.replace(tmp_file, config.DB_FILE)


def set_ai_drafter_pause(until, reason):
    global AI_DRAFTER_PAUSE_UNTIL
    with DB_LOCK:
        if AI_DRAFTER_PAUSE_UNTIL is None or until > AI_DRAFTER_PAUSE_UNTIL:
            AI_DRAFTER_PAUSE_UNTIL = until
        pause_value = AI_DRAFTER_PAUSE_UNTIL.isoformat()
        for record in SHARED_DB.values():
            if record.get("status") == "NEW":
                record["ai_retry_after"] = pause_value
                record["ai_retry_count"] = int(record.get("ai_retry_count", 0)) + 1
                record["error_message"] = reason
                record["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
        persist_db()


# -------------------------------------------------------------
# THREAD 1: Continuous High-Capacity Harvester
# -------------------------------------------------------------
def continuous_harvester_loop():
    add_log(
        f"[HUNTER] Continuous search active: up to {HARVEST_BATCH_SIZE} new published Gmail leads "
        f"without a listed website every {HARVEST_INTERVAL_SECONDS // 60} minutes."
    )
    time.sleep(3)

    while True:
        cycle_started = time.monotonic()
        try:
            is_active = load_lead_search_state()
            if not WORKER_RUNNING or not is_active:
                time.sleep(5)
                continue

            with DB_LOCK:
                current_total = len(SHARED_DB)
                current_keys = set(SHARED_DB.keys())

            if current_total < 10000:
                do_harvest()

            remaining_interval = HARVEST_INTERVAL_SECONDS - (time.monotonic() - cycle_started)
            if remaining_interval > 0:
                time.sleep(remaining_interval)

        except Exception as e:
            add_log(f"[HUNTER NOTICE] {e}")
            time.sleep(20)


# -------------------------------------------------------------
# THREAD 2: Rapid AI Drafter (Drafts all 'NEW' leads with Groq)
# -------------------------------------------------------------
def continuous_drafter_loop():
    global AI_DRAFTER_PAUSE_UNTIL
    add_log("[AI DRAFTER] OmniRoute/Kimi/Groq provider fallback thread online.")
    agent = AIAgent()
    time.sleep(2)

    while True:
        try:
            is_active = load_lead_search_state()
            if not WORKER_RUNNING or not is_active:
                time.sleep(4)
                continue

            if AI_DRAFTER_PAUSE_UNTIL and AI_DRAFTER_PAUSE_UNTIL > local_now():
                time.sleep(min(30, max(1, int((AI_DRAFTER_PAUSE_UNTIL - local_now()).total_seconds()))))
                continue
            elif AI_DRAFTER_PAUSE_UNTIL:
                AI_DRAFTER_PAUSE_UNTIL = None
                with DB_LOCK:
                    for record in SHARED_DB.values():
                        if record.get("status") == "NEW" and record.get("ai_retry_after"):
                            record.pop("ai_retry_after", None)
                            record.pop("ai_retry_count", None)
                            if record.get("error_message") and "Groq" in str(record.get("error_message")):
                                record["error_message"] = None
                persist_db()
                add_log("[AI DRAFTER] Provider cooldown ended; resuming queued drafting.")

            target_items = []
            with DB_LOCK:
                for em, r in SHARED_DB.items():
                    if r.get("status") == "NEW":
                        if "@" in em and "." in em.split("@")[-1]:
                            target_items.append((em, r["lead_info"]))
                            if len(target_items) >= 12:
                                break
                        else:
                            r["status"] = "FAILED"
                            r["error_message"] = "Invalid email format"

            if target_items:
                for target_email, lead_info in target_items:
                    try:
                        draft = agent.draft_initial_outreach(lead_info)
                        with DB_LOCK:
                            if target_email in SHARED_DB and SHARED_DB[target_email].get("status") == "NEW":
                                SHARED_DB[target_email]["draft"] = draft
                                SHARED_DB[target_email]["status"] = "DRAFTED"
                                SHARED_DB[target_email]["error_message"] = None
                                SHARED_DB[target_email].pop("ai_retry_after", None)
                                SHARED_DB[target_email].pop("ai_retry_count", None)
                                SHARED_DB[target_email]["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        persist_db()
                        add_log(f"[AI DRAFT READY] Drafted pitch for {lead_info.get('Business Name')} ({target_email})")
                        time.sleep(0.4)
                    except AIProviderRateLimitError as e:
                        delay = min(10, max(2, e.retry_after_seconds or 5))
                        reason = "Brief key rotation cooldown."
                        retry_at = local_now() + timedelta(seconds=delay)
                        set_ai_drafter_pause(retry_at, reason)
                        add_log(f"[AI DRAFT PAUSED] Brief pause {delay}s before next batch...")
                        break
                    except Exception as e:
                        add_log(f"[AI DRAFT ERROR] {target_email}: {e}")
                        time.sleep(1)

            time.sleep(1)

        except Exception as e:
            add_log(f"[DRAFTER EXCEPTION] {e}")
            time.sleep(5)


# -------------------------------------------------------------
# THREAD 3: Multi-Account Auto-Sender with Smart Rotation & Failover
# -------------------------------------------------------------
def restore_send_target(target_email, retry_after=None, message=None):
    with DB_LOCK:
        record = SHARED_DB.get(target_email)
        if record:
            history = record.get("history", [])
            if history_has_outbound(history):
                has_client_reply = any(
                    isinstance(item, dict) and str(item.get("sender", "")).strip().lower() == "client"
                    for item in history
                )
                record["status"] = "NEGOTIATING" if has_client_reply else "SENT"
                record["error_message"] = None
                record.pop("retry_after", None)
            else:
                record["status"] = "DRAFTED"
                record["error_message"] = message
                if retry_after:
                    record["retry_after"] = retry_after.isoformat()
                else:
                    record.pop("retry_after", None)
            record["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
    persist_db()


def next_local_midnight():
    tomorrow = local_now().date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), KOLKATA)


def continuous_sender_loop():
    add_log("[AUTO-SENDER] Multi-Account Auto-Dispatcher online with dynamic quota balancing & failover.")
    mailer = MailManager()
    accounts_mgr = AccountsManager()
    time.sleep(4)

    while True:
        try:
            is_active = load_lead_search_state()
            if not WORKER_RUNNING or not is_active:
                time.sleep(3)
                continue

            # Verify if ANY active account has remaining quota
            best_candidate = accounts_mgr.get_best_sender_for_lead()
            if not best_candidate:
                all_accs = accounts_mgr.get_all_accounts()
                active_count = sum(1 for a in all_accs if a["status"] == "ACTIVE")
                if active_count == 0:
                    add_log("[AUTO-SENDER PAUSED] No ACTIVE Gmail accounts found. Please add or enable accounts in Gmail Senders panel.")
                    time.sleep(15)
                    continue

                retry_at = next_local_midnight()
                set_sender_pause(retry_at, "All connected Gmail accounts reached daily quota")
                add_log(f"[ALL GMAIL QUOTAS REACHED] All {active_count} active accounts reached their daily limits. Resuming at midnight ({retry_at.strftime('%H:%M IST')}).")
                time.sleep(60)
                continue

            target = None
            repaired_sent_state = False
            with DB_LOCK:
                for em, r in SHARED_DB.items():
                    if r.get("status") == "DRAFTED" and r.get("draft"):
                        if "@" in em and "." in em.split("@")[-1]:
                            if history_has_outbound(r.get("history", [])):
                                has_client_reply = any(
                                    isinstance(item, dict) and str(item.get("sender", "")).strip().lower() == "client"
                                    for item in r.get("history", [])
                                )
                                r["status"] = "NEGOTIATING" if has_client_reply else "SENT"
                                r["error_message"] = None
                                r.pop("retry_after", None)
                                repaired_sent_state = True
                                continue
                            retry_after = parse_retry_after(r.get("retry_after"))
                            if retry_after and retry_after > local_now():
                                continue
                            r["status"] = "SENDING"
                            r.pop("retry_after", None)
                            target = (em, r["lead_info"], r["draft"], r.get("assigned_sender"))
                            break
                        else:
                            r["status"] = "FAILED"
                            r["error_message"] = "Invalid email format"
                            repaired_sent_state = True

            if repaired_sent_state:
                persist_db()

            if target:
                target_email, lead, draft, prev_sender = target
                draft["body"] = ensure_portfolio_link(draft.get("body", ""))
                add_log(f"[DISPATCHING] Sending pitch to {lead.get('Business Name')} <{target_email}>...")

                try:
                    success, used_sender = mailer.send_email(
                        target_email,
                        draft["subject"],
                        draft["body"],
                        preferred_sender=prev_sender
                    )
                    with DB_LOCK:
                        if target_email in SHARED_DB:
                            SHARED_DB[target_email]["status"] = "SENT"
                            SHARED_DB[target_email]["assigned_sender"] = used_sender
                            SHARED_DB[target_email]["error_message"] = None
                            SHARED_DB[target_email].pop("retry_after", None)
                            SHARED_DB[target_email].setdefault("history", []).append({
                                "sender": used_sender,
                                "sender_email": used_sender,
                                "subject": draft["subject"],
                                "text": draft["body"],
                                "timestamp": local_now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            SHARED_DB[target_email]["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
                    persist_db()
                    add_log(f"[SENT SUCCESS] Outreach delivered to {target_email} via {used_sender} ({lead.get('Business Name')})")

                    delay = random.randint(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
                    add_log(f"[PACING] Pausing {delay}s before next send...")
                    time.sleep(delay)

                except smtplib.SMTPRecipientsRefused as err:
                    with DB_LOCK:
                        if target_email in SHARED_DB:
                            SHARED_DB[target_email]["status"] = "FAILED"
                            SHARED_DB[target_email]["error_message"] = "Gmail SMTP permanently refused this recipient (550)."
                            SHARED_DB[target_email]["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
                    persist_db()
                    add_log(f"[GMAIL RECIPIENT REFUSED] {target_email}; permanently blocked.")

                except Exception as err:
                    err_str = str(err)
                    if "No available active Gmail accounts" in err_str or "All connected Gmail accounts" in err_str:
                        restore_send_target(target_email, retry_after=local_now() + timedelta(minutes=10), message="Waiting for active Gmail quota")
                        add_log(f"[QUOTA NOTICE] {err_str}. Pausing 30s...")
                        time.sleep(30)
                    elif is_temporary_send_error(err):
                        defer_temporary_send_error(target_email, err)
                    else:
                        with DB_LOCK:
                            if target_email in SHARED_DB:
                                SHARED_DB[target_email]["status"] = "FAILED"
                                SHARED_DB[target_email]["error_message"] = f"SMTP error: {err_str[:45]}"
                                SHARED_DB[target_email]["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
                        persist_db()
                        add_log(f"[SEND ERROR] {target_email}: {err_str}")
            else:
                time.sleep(3)

        except Exception as e:
            add_log(f"[SENDER EXCEPTION] {e}")
            time.sleep(5)


# -------------------------------------------------------------
# THREAD 4: Auto-Chat & Multi-Inbox Reply Monitor
# -------------------------------------------------------------
def continuous_autochat_and_bounce_loop():
    add_log("[AUTO-CHAT & MULTI-INBOX MONITOR] IMAP Monitor thread active across all accounts.")
    agent = AIAgent()
    mailer = MailManager()
    accounts_mgr = AccountsManager()
    time.sleep(6)

    while True:
        try:
            is_active = load_lead_search_state()
            if not WORKER_RUNNING or not is_active:
                time.sleep(10)
                continue

            with DB_LOCK:
                active_emails = list(SHARED_DB.keys())

            # 1. Delivery bounces across all active accounts
            active_accounts = accounts_mgr.get_all_active_accounts_raw()
            for acc in active_accounts:
                try:
                    mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT, timeout=10)
                    mail.login(acc["email"], acc["app_password"])
                    mail.select("inbox", readonly=True)

                    since_date = (local_now().date() - timedelta(days=2)).strftime("%d-%b-%Y")
                    status, msgs = mail.search(None, "SINCE", since_date)
                    if msgs and msgs[0]:
                        msg_ids = msgs[0].split()
                        for mid in msg_ids:
                            res, data = mail.fetch(mid, b"(BODY.PEEK[])")
                            for part in data:
                                if isinstance(part, tuple):
                                    msg = email.message_from_bytes(part[1])
                                    from_hdr = str(msg.get("From", "")).lower()
                                    sub = str(msg.get("Subject", "")).lower()

                                    if "mailer-daemon" not in from_hdr and "delivery status" not in sub and "failure" not in sub:
                                        continue
                                    for em_lower in extract_bounced_recipients(msg):
                                        with DB_LOCK:
                                            record = SHARED_DB.get(em_lower)
                                            if not record or record.get("status") == "FAILED":
                                                continue
                                            record["status"] = "FAILED"
                                            record["error_message"] = "Gmail delivery failure confirmed by delivery status notification."
                                            record["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
                                        persist_db()
                                        add_log(f"[BOUNCE CONFIRMED] Delivery notice from {acc['email']} for {em_lower}; marked as FAILED.")
                    mail.logout()
                except Exception:
                    pass

            # 2. Capture client replies across ALL accounts
            if active_emails:
                replies = mailer.check_for_replies(active_emails)
                for rep in replies:
                    from_em = rep["from_email"].lower()
                    recip_acc = rep.get("recipient_account")
                    if from_em in SHARED_DB:
                        with DB_LOCK:
                            rec = SHARED_DB[from_em]
                            lead = rec["lead_info"]
                            history = rec.get("history", [])

                            already_logged = any(h.get("sender") == "Client" and h.get("text") == rep["body"] for h in history)

                        if already_logged:
                            continue

                        add_log(f"[REPLY DETECTED] New client reply from {lead.get('Business Name')} ({from_em}) received on {recip_acc}!")

                        if not AUTO_SEND_ENABLED:
                            with DB_LOCK:
                                rec = SHARED_DB.get(from_em)
                                if rec:
                                    if recip_acc:
                                        rec["assigned_sender"] = recip_acc
                                    rec.setdefault("history", []).append({
                                        "sender": "Client",
                                        "text": rep["body"],
                                        "timestamp": local_now().strftime("%Y-%m-%d %H:%M:%S")
                                    })
                                    rec["status"] = "NEGOTIATING"
                                    rec["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
                            persist_db()
                            add_log(f"[REPLY CAPTURED] {from_em} on {recip_acc}: auto-reply is paused.")
                            continue

                        negotiation = agent.generate_reply_and_negotiate(lead, history, rep["body"])
                        intent = negotiation.get("detected_intent", "GENERAL_REPLY")
                        resp_body = negotiation.get("reply_body", "")
                        intent_upper = str(intent).strip().upper()
                        include_portfolio = (
                            not any(term in intent_upper for term in ("NOT_INTERESTED", "UNSUBSCRIBE", "OPT_OUT", "STOP", "DECLIN"))
                            and not portfolio_optout_requested(rep["body"])
                        )
                        if include_portfolio:
                            resp_body = ensure_portfolio_link(resp_body)

                        subject = f"Re: {rec.get('draft', {}).get('subject', 'Website & Digital Setup')}"
                        sender_to_use = recip_acc or rec.get("assigned_sender")

                        try:
                            if sender_to_use:
                                mailer.send_email_from_account(sender_to_use, from_em, subject, resp_body, include_portfolio=include_portfolio)
                            else:
                                _, sender_to_use = mailer.send_email(from_em, subject, resp_body, include_portfolio=include_portfolio)
                            add_log(f"[AUTO-REPLY SENT] Dispatched response via {sender_to_use} to {lead.get('Business Name')} ({from_em})")
                        except Exception as e:
                            add_log(f"[AUTO-REPLY FAILED] Could not send reply: {e}")

                        with DB_LOCK:
                            rec["status"] = "MEETING_BOOKED" if "READY" in intent else "NEGOTIATING"
                            if sender_to_use:
                                rec["assigned_sender"] = sender_to_use
                            rec["history"].append({"sender": "Client", "text": rep["body"], "timestamp": local_now().strftime("%Y-%m-%d %H:%M:%S")})
                            rec["history"].append({
                                "sender": sender_to_use or config.SENDER_NAME,
                                "sender_email": sender_to_use,
                                "text": resp_body,
                                "timestamp": local_now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            rec["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
                        persist_db()
                        add_log(f"[AUTO-CHAT SUCCESS] Intent: {intent}. Meeting negotiation updated on dashboard.")

            time.sleep(15)

        except Exception as e:
            add_log(f"[AUTO-CHAT NOTICE] {e}")
            time.sleep(15)


def start_background_workers():
    threading.Thread(target=continuous_harvester_loop, daemon=True).start()
    threading.Thread(target=continuous_drafter_loop, daemon=True).start()
    threading.Thread(target=continuous_sender_loop, daemon=True).start()
    threading.Thread(target=continuous_autochat_and_bounce_loop, daemon=True).start()


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def get_stats():
    with DB_LOCK:
        total = len(SHARED_DB)
        drafted = sum(1 for r in SHARED_DB.values() if r.get("status") in ["DRAFTED", "SENDING"])
        sent = sum(1 for r in SHARED_DB.values() if r.get("status") == "SENT")
        negotiating = sum(1 for r in SHARED_DB.values() if r.get("status") == "NEGOTIATING")
        meeting_booked = sum(1 for r in SHARED_DB.values() if r.get("status") == "MEETING_BOOKED")
        new_leads = sum(1 for r in SHARED_DB.values() if r.get("status") == "NEW")
        failed = sum(1 for r in SHARED_DB.values() if r.get("status") == "FAILED")

    pause_until, pause_reason = sender_pause_snapshot()

    mgr = AccountsManager()
    accs = mgr.get_all_accounts()
    total_capacity = sum(a.get("daily_limit", 200) for a in accs)
    total_sent = sum(a.get("sent_today", 0) for a in accs)
    active_senders = [a["email"] for a in accs if a["status"] == "ACTIVE"]
    has_available_sender = mgr.get_best_sender_for_lead() is not None

    return jsonify({
        "total_leads": total,
        "new_leads": new_leads,
        "drafted": drafted,
        "sent": sent,
        "failed": failed,
        "negotiating": negotiating,
        "meeting_booked": meeting_booked,
        "worker_running": WORKER_RUNNING,
        "auto_send": AUTO_SEND_ENABLED,
        "lead_search_enabled": LEAD_SEARCH_ENABLED,
        "harvest_interval_seconds": HARVEST_INTERVAL_SECONDS,
        "sender_pause_until": pause_until.isoformat() if pause_until else None,
        "sender_pause_reason": pause_reason,
        "sender_cooldown": not has_available_sender and len(active_senders) > 0,
        "sent_today": total_sent,
        "daily_limit": total_capacity or max(1, int(config.DAILY_LIMIT or 200)),
        "active_sender": ", ".join(active_senders) if active_senders else "None",
        "active_senders_count": len(active_senders),
        "total_accounts_count": len(accs),
        "ai_model": config.AI_MODEL,
        "starting_price": config.BASE_PRICE
    })


@app.route("/api/leads", methods=["GET"])
def get_leads():
    with DB_LOCK:
        lead_list = []
        for em, rec in SHARED_DB.items():
            info = rec.get("lead_info", {})
            lead_list.append({
                "email": em,
                "business_name": info.get("Business Name", "Unknown"),
                "contact_person": info.get("Contact Person", "N/A"),
                "category": info.get("Category", "General Business"),
                "phone": info.get("Phone", "N/A"),
                "address": info.get("City / Address", "Global"),
                "website": info.get("Website", ""),
                "website_status": info.get("Website Status", "No Website"),
                "website_issues": info.get("Website Issues", []),
                "pitch_angle": info.get("Freelance Pitch Angle", ""),
                "status": rec.get("status", "NEW"),
                "assigned_sender": rec.get("assigned_sender"),
                "error_message": rec.get("error_message", None),
                "last_updated": rec.get("last_updated", "")
            })
    return jsonify(list(reversed(lead_list)))


@app.route("/api/outreach", methods=["GET"])
def get_outreach():
    with DB_LOCK:
        outreach_list = []
        for em, rec in SHARED_DB.items():
            info = rec.get("lead_info", {})
            draft = rec.get("draft")
            history = rec.get("history", [])
            status = rec.get("status", "NEW")
            pitch_angle = info.get("Freelance Pitch Angle", "Modern digital presence & WhatsApp catalog")

            pitch_body = ""
            pitch_subject = f"Quick catalog & website for {info.get('Business Name', 'your business')}"

            if draft and draft.get("body"):
                pitch_body = draft.get("body")
                pitch_subject = draft.get("subject", pitch_subject)
            elif history and len(history) > 0 and history[0].get("text") and "Outreach pitch sent on" not in history[0].get("text"):
                pitch_body = history[0].get("text", "")
                pitch_subject = history[0].get("subject", pitch_subject)
            elif status == "NEW":
                pitch_body = f"Pitch Angle: {pitch_angle}\n\n[Status: Queued in pipeline for Groq AI personalization & auto-dispatch]"
                pitch_subject = f"[Queued Pitch] Idea for {info.get('Business Name', 'Business')}"
            elif status == "FAILED":
                err = rec.get("error_message") or "Address not found"
                pitch_body = f"Pitch Angle: {pitch_angle}\n\n[Delivery Notice: {err}]"
                pitch_subject = f"[Delivery Notice] {info.get('Business Name', 'Business')}"
            else:
                pitch_body = f"Pitch Angle: {pitch_angle}"

            outreach_list.append({
                "email": em,
                "business_name": info.get("Business Name", "Unknown"),
                "contact_person": info.get("Contact Person", "N/A"),
                "category": info.get("Category", "Business"),
                "website": info.get("Website", ""),
                "website_status": info.get("Website Status", "No Website"),
                "website_issues": info.get("Website Issues", []),
                "status": "SENT" if status == "SENDING" else status,
                "assigned_sender": rec.get("assigned_sender"),
                "error_message": rec.get("error_message", None),
                "retry_after": rec.get("retry_after", None),
                "subject": pitch_subject,
                "body": pitch_body,
                "history": history,
                "last_updated": rec.get("last_updated", "")
            })

        # Priority Sorting: Active negotiations & replies ALWAYS at top!
        def sort_priority(item):
            st = item.get("status")
            if st in ["MEETING_BOOKED", "NEGOTIATING"] or len(item.get("history", [])) > 1:
                return 0
            if st == "SENT":
                return 1
            if st in ["DRAFTED", "SENDING"]:
                return 2
            if st == "NEW":
                return 3
            return 4

        outreach_list.sort(key=sort_priority)
    return jsonify(outreach_list)


@app.route("/api/logs", methods=["GET"])
def get_logs():
    with LOG_LOCK:
        return jsonify(list(WORKER_LOGS))


@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    mgr = AccountsManager()
    with DB_LOCK:
        accs = mgr.get_all_accounts(SHARED_DB)
    total_capacity = sum(a.get("daily_limit", 200) for a in accs)
    total_sent = sum(a.get("sent_today", 0) for a in accs)
    active_count = sum(1 for a in accs if a["status"] == "ACTIVE")
    return jsonify({
        "accounts": accs,
        "total_capacity": total_capacity,
        "total_sent_today": total_sent,
        "active_accounts": active_count,
        "total_accounts": len(accs)
    })


@app.route("/api/accounts/add", methods=["POST"])
def add_account_endpoint():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    app_pwd = data.get("app_password", "").strip()
    sender_name = data.get("sender_name", "").strip()
    daily_limit = data.get("daily_limit", 200)

    if not email_addr or not app_pwd:
        return jsonify({"success": False, "error": "Email and Google App Password are required."})

    mgr = AccountsManager()
    success, msg = mgr.add_account(email_addr, app_pwd, sender_name, daily_limit)
    if success:
        add_log(f"[ACCOUNT CONNECTED] Successfully verified and activated {email_addr} (Limit: {daily_limit}/day)")
    return jsonify({"success": success, "message": msg, "error": msg if not success else None})


@app.route("/api/accounts/update_limit", methods=["POST"])
def update_account_limit_endpoint():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    new_limit = int(data.get("daily_limit", 200))
    if not email_addr:
        return jsonify({"success": False, "error": "Email is required."})

    mgr = AccountsManager()
    if mgr.update_daily_limit(email_addr, new_limit):
        add_log(f"[ACCOUNT LIMIT] Updated {email_addr} daily sending limit to {new_limit}/day")
        return jsonify({"success": True, "message": f"Updated limit to {new_limit}"})
    return jsonify({"success": False, "error": "Account not found"}), 404


@app.route("/api/accounts/toggle", methods=["POST"])
def toggle_account_endpoint():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    if not email_addr:
        return jsonify({"success": False, "error": "Email is required."})

    mgr = AccountsManager()
    success, msg = mgr.toggle_account(email_addr)
    if success:
        add_log(f"[ACCOUNT TOGGLE] {msg}")
    return jsonify({"success": success, "message": msg})


@app.route("/api/accounts/delete", methods=["POST"])
def delete_account_endpoint():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    if not email_addr:
        return jsonify({"success": False, "error": "Email is required."})

    mgr = AccountsManager()
    success, msg = mgr.delete_account(email_addr)
    if success:
        add_log(f"[ACCOUNT DELETED] {msg}")
    return jsonify({"success": success, "message": msg})


@app.route("/api/accounts/test", methods=["POST"])
def test_account_endpoint():
    data = request.json or {}
    email_addr = data.get("email", "").strip()
    if not email_addr:
        return jsonify({"success": False, "error": "Email is required."})

    mgr = AccountsManager()
    acc = mgr.get_account_by_email(email_addr)
    if not acc:
        return jsonify({"success": False, "error": f"Account {email_addr} not found."})

    success, msg = mgr.test_credentials(acc["email"], acc["app_password"])
    return jsonify({"success": success, "message": msg, "error": msg if not success else None})


@app.route("/api/reply/send", methods=["POST"])
def send_manual_reply():
    data = request.json or {}
    target_email = data.get("email", "").strip().lower()
    reply_text = data.get("message", "").strip()

    if not target_email or not reply_text:
        return jsonify({"success": False, "error": "Email and message text required."})

    reply_text = ensure_portfolio_link(reply_text)

    with DB_LOCK:
        if target_email not in SHARED_DB:
            return jsonify({"success": False, "error": f"Lead {target_email} not found."})
        record = SHARED_DB[target_email]
        lead = record["lead_info"]
        draft = record.get("draft") or {}
        assigned_sender = record.get("assigned_sender")
        subject = f"Re: {draft.get('subject', 'Website Development & Digital Setup')}"

    mailer = MailManager()
    try:
        if assigned_sender:
            try:
                mailer.send_email_from_account(assigned_sender, target_email, subject, reply_text)
                used_sender = assigned_sender
            except Exception:
                _, used_sender = mailer.send_email(target_email, subject, reply_text, preferred_sender=assigned_sender)
        else:
            _, used_sender = mailer.send_email(target_email, subject, reply_text)

        with DB_LOCK:
            record["assigned_sender"] = used_sender
            record["status"] = "NEGOTIATING"
            record["error_message"] = None
            record["history"].append({
                "sender": used_sender,
                "sender_email": used_sender,
                "text": reply_text,
                "timestamp": local_now().strftime("%Y-%m-%d %H:%M:%S")
            })
            record["last_updated"] = local_now().strftime("%Y-%m-%d %H:%M:%S")
        persist_db()
        add_log(f"[MANUAL REPLY SENT] Sent direct reply via {used_sender} to {lead.get('Business Name')} ({target_email})")
        return jsonify({"success": True, "message": f"Reply delivered via {used_sender}!"})
    except Exception as e:
        with DB_LOCK:
            record["error_message"] = str(e)[:60]
        persist_db()
        add_log(f"[MANUAL REPLY ERROR] {target_email}: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/suggest-reply", methods=["POST"])
def suggest_reply():
    data = request.json or {}
    target_email = data.get("email", "").strip().lower()
    with DB_LOCK:
        if target_email not in SHARED_DB:
            return jsonify({"success": False, "error": "Lead not found."})
        rec = SHARED_DB[target_email]
        history = list(rec.get("history", []))
        lead_info = dict(rec["lead_info"])

    agent = AIAgent()
    latest_client_msg = "Hello, what are your charges and what features will you provide?"
    for msg in reversed(history):
        if msg.get("sender") == "Client":
            latest_client_msg = msg.get("text")
            break

    try:
        negotiation = agent.generate_reply_and_negotiate(lead_info, history, latest_client_msg)
        return jsonify({"success": True, "suggestion": negotiation.get("reply_body", "")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/worker/toggle", methods=["POST"])
def toggle_worker():
    global WORKER_RUNNING
    WORKER_RUNNING = not WORKER_RUNNING
    add_log(f"Worker state changed: {'RUNNING' if WORKER_RUNNING else 'PAUSED'}")
    return jsonify({"worker_running": WORKER_RUNNING})


@app.route("/api/autosend/toggle", methods=["POST"])
def toggle_autosend():
    global AUTO_SEND_ENABLED
    AUTO_SEND_ENABLED = not AUTO_SEND_ENABLED
    save_auto_send_state(AUTO_SEND_ENABLED)
    add_log(f"Auto-Send state changed: {'ACTIVE' if AUTO_SEND_ENABLED else 'PAUSED'}")
    return jsonify({"auto_send": AUTO_SEND_ENABLED})


@app.route("/api/leadsearch/toggle", methods=["POST"])
def toggle_lead_search():
    global LEAD_SEARCH_ENABLED
    LEAD_SEARCH_ENABLED = not LEAD_SEARCH_ENABLED
    save_lead_search_state(LEAD_SEARCH_ENABLED)
    add_log(f"Lead Search state changed: {'HUNTING ACTIVE' if LEAD_SEARCH_ENABLED else 'HUNTING PAUSED (Outreach continues)'}")
    return jsonify({"lead_search_enabled": LEAD_SEARCH_ENABLED})


@app.route("/api/harvest-now", methods=["POST"])
def harvest_now():
    add_log("Manual trigger: High-capacity verified @gmail.com harvest starting...")
    threading.Thread(target=lambda: do_harvest(), daemon=True).start()
    return jsonify({"success": True, "message": "Harvest started in background"})


def do_harvest():
    if not HARVEST_LOCK.acquire(blocking=False):
        add_log("Manual harvest skipped: an automatic harvest is already running.")
        return

    try:
        with DB_LOCK:
            current_total = len(SHARED_DB)
            current_keys = set(SHARED_DB.keys())

        target_total = current_total + HARVEST_BATCH_SIZE
        new_leads = harvest_real_uk_leads(
            target_count=target_total,
            existing_db={k: {} for k in current_keys},
            require_no_website=True,
            on_status=add_log,
        )
        added = 0
        with DB_LOCK:
            for item in new_leads:
                em = item["email"].strip().lower()
                if em in SHARED_DB:
                    continue
                SHARED_DB[em] = {
                    "lead_info": item["lead_info"],
                    "status": "NEW",
                    "draft": None,
                    "history": [],
                    "error_message": None,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                added += 1
        if added:
            persist_db()
        with DB_LOCK:
            final_total = len(SHARED_DB)
        add_log(f"UK harvest pass complete: added {added} qualified leads. Total DB: {final_total}.")
    finally:
        HARVEST_LOCK.release()


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    dist_dir = os.path.join(os.path.dirname(__file__), "dashboard", "dist")
    if path != "" and os.path.exists(os.path.join(dist_dir, path)):
        return send_from_directory(dist_dir, path)
    return send_from_directory(dist_dir, "index.html")


def acquire_single_instance_lock():
    lock_path = os.path.join(os.path.dirname(__file__), ".server_uk.lock")
    handle = open(lock_path, "a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


if __name__ == "__main__":
    INSTANCE_LOCK_HANDLE = acquire_single_instance_lock()
    if INSTANCE_LOCK_HANDLE is None:
        print("Another Nexus UK backend is already running; refusing to start duplicate outreach workers.")
        raise SystemExit(1)
    add_log(f"Starting Nexus UK & British Isles API Backend on port {config.PORT}")
    start_background_workers()
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
