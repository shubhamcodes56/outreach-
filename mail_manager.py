import smtplib
import imaplib
import email
import html
import re
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import config
from accounts_manager import AccountsManager

KOLKATA = ZoneInfo("Asia/Kolkata")
PORTFOLIO_MARKER = "[[PORTFOLIO_LINK]]"
PORTFOLIO_OPTOUT_PATTERN = re.compile(
    r"\b(?:unsubscribe|stop\s+(?:emailing|contacting|messaging)|remove me|do not contact|don't contact|no more emails?|not interested|won't contact|will not contact)\b",
    re.IGNORECASE,
)


def local_now():
    return datetime.now(KOLKATA)


def is_gmail_quota_error(err):
    msg = str(err).lower()
    return "5.4.5" in msg or "daily user sending limit exceeded" in msg or "sending limit exceeded" in msg


def portfolio_optout_requested(text: str) -> bool:
    return bool(PORTFOLIO_OPTOUT_PATTERN.search(str(text or "")))


def ensure_portfolio_link(body_text: str) -> str:
    """Add one hidden-URL portfolio link to outbound copy, except opt-out replies."""
    body_text = str(body_text or "").strip()
    if PORTFOLIO_MARKER in body_text or portfolio_optout_requested(body_text):
        return body_text
    return f"{body_text}\n\nExamples of my work: {PORTFOLIO_MARKER}".strip()


class MailManager:
    def __init__(self):
        self.accounts_mgr = AccountsManager()

    def send_email(self, to_email: str, subject: str, body_text: str, preferred_sender: str = None, include_portfolio: bool = True) -> tuple[bool, str]:
        """
        Sends an email with automatic account rotation & failover.
        'ek se fail toh dusre se' - guarantees trying all available accounts before failing!
        1. Attempts to use preferred_sender (for conversation continuity).
        2. If unavailable or hits any error, auto-rotates immediately to next unattempted active account.
        Returns: (True, sender_used) on success, or raises Exception if all accounts fail.
        """
        body_text = ensure_portfolio_link(body_text) if include_portfolio else str(body_text or "").strip()
        attempted_accounts = set()
        last_error = None

        while True:
            # Pick candidate among unattempted accounts
            account = self.accounts_mgr.get_best_sender_for_lead(
                preferred_email=preferred_sender if preferred_sender and preferred_sender not in attempted_accounts else None,
                excluded_emails=attempted_accounts
            )
            if not account:
                all_accs = self.accounts_mgr.get_all_accounts()
                active_count = sum(1 for a in all_accs if a["status"] == "ACTIVE")
                if active_count == 0:
                    raise ValueError("All connected Gmail accounts are currently paused or have exceeded their daily limits.")
                if last_error:
                    raise last_error
                raise ValueError(f"No available active Gmail accounts with remaining daily quota. (Checked {len(attempted_accounts)} accounts)")

            sender_email = account["email"]
            sender_pwd = account["app_password"]
            sender_name = account.get("sender_name") or config.SENDER_NAME or "Shubham Dixit"
            attempted_accounts.add(sender_email)

            try:
                self._dispatch_smtp(sender_email, sender_pwd, sender_name, to_email, subject, body_text)
                self.accounts_mgr.record_send_success(sender_email)
                return True, sender_email

            except Exception as err:
                last_error = err
                err_str = str(err)
                print(f"[!] Dispatch to {to_email} from {sender_email} failed: {err_str}")

                if is_gmail_quota_error(err):
                    self.accounts_mgr.record_quota_exceeded(sender_email, "Daily sending limit exceeded (5.4.5)")
                elif isinstance(err, smtplib.SMTPAuthenticationError):
                    self.accounts_mgr.record_auth_error(sender_email, f"Auth Error: {err}")

                # Check if there are other unattempted accounts available:
                remaining_candidates = [
                    a["email"] for a in self.accounts_mgr.get_all_active_accounts_raw()
                    if a["email"] not in attempted_accounts and a.get("status") == "ACTIVE"
                ]
                if remaining_candidates:
                    print(f"[*] 'Ek se fail toh dusre se' -> Failing over from {sender_email} to {remaining_candidates[0]}...")
                    continue
                else:
                    # All active accounts were attempted and failed
                    raise err

    def send_email_from_account(self, sender_email: str, to_email: str, subject: str, body_text: str, include_portfolio: bool = True) -> bool:
        """Sends an email explicitly from a specified account."""
        body_text = ensure_portfolio_link(body_text) if include_portfolio else str(body_text or "").strip()
        acc = self.accounts_mgr.get_account_by_email(sender_email)
        if not acc:
            raise ValueError(f"Account {sender_email} not found in connected accounts.")

        sender_pwd = acc["app_password"]
        sender_name = acc.get("sender_name") or config.SENDER_NAME or "Shubham Dixit"
        self._dispatch_smtp(sender_email, sender_pwd, sender_name, to_email, subject, body_text)
        self.accounts_mgr.record_send_success(sender_email)
        return True

    def _dispatch_smtp(self, sender_email: str, sender_pwd: str, sender_name: str, to_email: str, subject: str, body_text: str):
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        marker = PORTFOLIO_MARKER
        plain_body = body_text.replace(marker, "my portfolio")
        portfolio_url = html.escape(config.PORTFOLIO_URL, quote=True)
        html_body = html.escape(body_text).replace(marker, f'<a href="{portfolio_url}">View portfolio</a>')
        html_body = html_body.replace("\r\n", "\n").replace("\n", "<br>\n")
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(f"<html><body style=\"font-family:Arial,sans-serif;line-height:1.6\">{html_body}</body></html>", "html", "utf-8"))

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(sender_email, sender_pwd)
            server.send_message(msg)

    def check_for_replies(self, active_emails: list) -> list:
        """
        Checks inboxes across ALL active connected Gmail accounts.
        Preserves client conversation continuity by tagging each reply with 'recipient_account'.
        """
        all_replies = []
        active_set = set(e.lower() for e in active_emails)
        accounts = self.accounts_mgr.get_all_active_accounts_raw()

        for acc in accounts:
            acc_email = acc["email"]
            acc_pwd = acc["app_password"]

            try:
                mail = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT, timeout=12)
                mail.login(acc_email, acc_pwd)
                mail.select("inbox", readonly=True)

                since_date = (local_now().date() - timedelta(days=2)).strftime("%d-%b-%Y")
                status, messages = mail.search(None, "SINCE", since_date)
                if status != "OK" or not messages or not messages[0]:
                    mail.logout()
                    continue

                for num in messages[0].split():
                    res, data = mail.fetch(num, "(RFC822)")
                    for response_part in data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            from_header = str(msg.get("From", ""))
                            sender_email = email.utils.parseaddr(from_header)[1].lower()

                            if sender_email in active_set and sender_email != acc_email.lower():
                                sub_raw = msg.get("Subject", "")
                                try:
                                    sub_parts = decode_header(sub_raw)
                                    subject = ""
                                    for part, encoding in sub_parts:
                                        if isinstance(part, bytes):
                                            subject += part.decode(encoding or "utf-8", errors="ignore")
                                        else:
                                            subject += str(part)
                                except Exception:
                                    subject = str(sub_raw)

                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                body = payload.decode(errors="ignore")
                                                break
                                else:
                                    payload = msg.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode(errors="ignore")

                                date_hdr = str(msg.get("Date", ""))
                                all_replies.append({
                                    "from_email": sender_email,
                                    "recipient_account": acc_email,
                                    "subject": subject,
                                    "date": date_hdr,
                                    "body": body.strip()
                                })

                mail.logout()
            except Exception as e:
                if "authentication failed" in str(e).lower():
                    self.accounts_mgr.record_auth_error(acc_email, f"IMAP Auth Error: {e}")
                print(f"[!] IMAP check error for {acc_email}: {e}")

        return all_replies
