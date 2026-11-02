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


def build_kicksa_premium_html(sender_name: str, to_email: str, subject: str, body_text: str, portfolio_url: str) -> str:
    """
    Renders a bold, black, ultra-premium HTML email template for Kicksa Studio
    featuring minimalist branding, high-contrast typography, and a dynamic loop showcase.
    """
    escaped_body = html.escape(body_text)
    paragraphs = [p.strip() for p in re.split(r'\n{2,}|\r\n\r\n', escaped_body) if p.strip()]

    formatted_paragraphs = []
    for p in paragraphs:
        if PORTFOLIO_MARKER in p:
            p = p.replace(PORTFOLIO_MARKER, f'<a href="{portfolio_url}" target="_blank" style="color: #00f2fe; text-decoration: underline; font-weight: 600;">Explore live systems &rarr;</a>')

        lines = p.split('\n')
        bullet_lines = [l for l in lines if l.strip().startswith(('•', '-', '*', '📱', '⚡', '📍', '📈', '💡'))]
        if bullet_lines and len(bullet_lines) >= 2:
            card_content = '<br>'.join(lines)
            formatted_paragraphs.append(
                f'<div style="margin: 18px 0; padding: 16px 20px; background-color: #171720; border-left: 3px solid #00f2fe; border-radius: 6px; color: #f4f4f5; font-size: 13.5px; line-height: 1.65; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">{card_content}</div>'
            )
        else:
            formatted_p = p.replace('\n', '<br>')
            formatted_paragraphs.append(
                f'<p style="margin: 0 0 16px 0; color: #d4d4d8; font-size: 14px; line-height: 1.7; font-weight: 400;">{formatted_p}</p>'
            )

    body_html = '\n'.join(formatted_paragraphs)
    showcase_gif_url = "https://raw.githubusercontent.com/shubhamcodes56/outreach-/main/assets/kicksa_showcase_loop.gif"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin: 0; padding: 24px 12px; background-color: #070709; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
  <!-- Outer Email Table Container -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #070709;">
    <tr>
      <td align="center">
        <!-- Main Card (Max 580px) -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width: 580px; background-color: #111116; border: 1px solid #23232b; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);">
          
          <!-- Header Bar with Minimalist Kicksa Logo -->
          <tr>
            <td style="padding: 20px 28px; border-bottom: 1px solid #1f1f27; background-color: #0d0d12;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td align="left" style="vertical-align: middle;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="vertical-align: middle; padding-right: 10px;">
                          <!-- Geometric Minimal 'K' Emblem -->
                          <div style="width: 30px; height: 30px; background: #181822; border: 1px solid #2a2a38; border-radius: 7px; text-align: center; line-height: 28px;">
                            <span style="color: #00f2fe; font-weight: 900; font-size: 15px; font-family: monospace;">K</span>
                          </div>
                        </td>
                        <td style="vertical-align: middle;">
                          <span style="font-size: 15px; font-weight: 900; letter-spacing: 2.2px; color: #ffffff; text-transform: uppercase;">KICKSA</span>
                          <span style="font-size: 9px; font-weight: 700; color: #71717a; letter-spacing: 1.5px; margin-left: 6px; text-transform: uppercase;">STUDIO</span>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td align="right" style="vertical-align: middle;">
                    <span style="display: inline-block; font-size: 9px; font-family: -apple-system, monospace; font-weight: 700; color: #00f2fe; background-color: rgba(0, 242, 254, 0.08); border: 1px solid rgba(0, 242, 254, 0.28); padding: 4px 10px; border-radius: 12px; letter-spacing: 0.8px; text-transform: uppercase;">
                      GROWTH SYSTEMS
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Main Email Content Area -->
          <tr>
            <td style="padding: 28px 28px 20px 28px;">
              {body_html}
            </td>
          </tr>

          <!-- Featured Work Showcase with Loop Animation -->
          <tr>
            <td style="padding: 10px 28px 28px 28px;">
              <div style="padding-top: 20px; border-top: 1px solid #1f1f27;">
                <div style="font-size: 10px; font-weight: 800; letter-spacing: 1.5px; color: #a1a1aa; text-transform: uppercase; margin-bottom: 12px;">
                  FEATURED CLIENT REBUILDS &amp; PROFIT IMPACT
                </div>
                <!-- Animated Showcase Loop GIF -->
                <a href="{portfolio_url}" target="_blank" style="display: block; text-decoration: none;">
                  <img src="{showcase_gif_url}" alt="Kicksa Interactive Showcase Loop" width="100%" style="display: block; width: 100%; max-width: 524px; border-radius: 8px; border: 1px solid #2a2a38; box-shadow: 0 4px 16px rgba(0,0,0,0.4);" />
                </a>
                <!-- CTA Button -->
                <div style="text-align: center; margin-top: 20px;">
                  <a href="{portfolio_url}" target="_blank" style="display: inline-block; background-color: #ffffff; color: #09090b; font-size: 13px; font-weight: 700; padding: 12px 26px; border-radius: 6px; text-decoration: none; letter-spacing: -0.2px; box-shadow: 0 2px 10px rgba(255, 255, 255, 0.15);">
                    Explore Live Client Systems &amp; Proof &rarr;
                  </a>
                </div>
              </div>
            </td>
          </tr>

          <!-- Minimalist Luxury Footer -->
          <tr>
            <td style="padding: 18px 28px; background-color: #0b0b0f; border-top: 1px solid #1a1a22; text-align: center;">
              <p style="margin: 0; font-size: 11px; color: #71717a; font-weight: 500;">
                Kicksa Studio &bull; Digital Architecture &amp; Customer Acquisition
              </p>
              <p style="margin: 6px 0 0 0; font-size: 10px; color: #3f3f46;">
                Delivering high-converting mobile engines across the UK &bull; Reply &apos;opt out&apos; to unsubscribe
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


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
        portfolio_url = config.PORTFOLIO_URL
        plain_body = body_text.replace(marker, f"Kicksa Systems: {portfolio_url}")

        html_content = build_kicksa_premium_html(sender_name, to_email, subject, body_text, portfolio_url)

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

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
