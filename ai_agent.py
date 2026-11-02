"""
Nexus UK AI Proposal Generator & Drafting Agent.
Generates high-converting, human-like, emoji-rich mini-proposals specifically tailored
for independent UK business owners, cafes, clinics, and tradespeople.
"""

import json
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import httpx
from groq import Groq
import config

MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b"
]


class AIProviderRateLimitError(RuntimeError):
    def __init__(self, message, retry_after_seconds=None, insufficient_balance=False, organization_quota=False):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.insufficient_balance = insufficient_balance
        self.organization_quota = organization_quota


PORTFOLIO_MARKER = "[[PORTFOLIO_LINK]]"


def _ensure_portfolio_reference(body: str, fallback_sentence: str) -> str:
    """Keep generated copy clean and place one clickable portfolio marker right before the sign-off."""
    body = str(body or "").strip()
    
    # Remove any http/www links the model might have written inside the letter
    body = re.sub(r"(?i)\bhttps?://[^\s<>\"']+", "", body)
    body = re.sub(r"(?i)\bwww\.[^\s<>\"']+", "", body)

    # Ensure fallback sentence is placed right before the signoff
    if PORTFOLIO_MARKER not in body:
        signoff = re.search(r"(?im)^(?:cheers|warm regards|best regards|kind regards|thanks|thank you|best)[,! ]*$", body)
        if signoff:
            body = f"{body[:signoff.start()].rstrip()}\n\n{fallback_sentence}\n\n{body[signoff.start():]}"
        else:
            body = f"{body.rstrip()}\n\n{fallback_sentence}"
    else:
        # If multiple markers exist, keep only the last one
        parts = body.split(PORTFOLIO_MARKER)
        body = "".join(parts[:-1]) + PORTFOLIO_MARKER + parts[-1]

    return body


def _rate_limit_details(error):
    response = getattr(error, "response", None)
    status_code = getattr(error, "status_code", None) or getattr(response, "status_code", None)
    message = str(error)
    if status_code != 429 and not re.search(r"\b429\b|rate_limit_error|rate limit", message, re.I):
        return None

    retry_after = None
    headers = getattr(response, "headers", {}) or {}
    header_value = headers.get("retry-after") or headers.get("Retry-After")
    if header_value:
        try:
            retry_after = max(1, int(float(header_value)))
        except (TypeError, ValueError):
            try:
                retry_time = parsedate_to_datetime(str(header_value))
                if retry_time.tzinfo is None:
                    retry_time = retry_time.replace(tzinfo=timezone.utc)
                retry_after = max(1, int((retry_time - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass

    if retry_after is None:
        patterns = (
            r"try again in\s*(?:(\d+)m)?\s*(\d+(?:\.\d+)?)s",
            r"retry[- ]after\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)?",
            r"(\d+(?:\.\d+)?)\s*seconds?",
        )
        for pattern in patterns:
            match = re.search(pattern, message, re.I)
            if match:
                if pattern.startswith("try"):
                    minutes = int(match.group(1) or 0)
                    seconds = float(match.group(2))
                    retry_after = max(1, int(minutes * 60 + seconds))
                else:
                    retry_after = max(1, int(float(match.group(1))))
                break

    insufficient_balance = bool(re.search(r"insufficient\s+(?:account\s+)?balance|insufficient funds", message, re.I))
    organization_quota = bool(
        re.search(r"\borganization\b.*\b(?:TPD|TPM|RPD|RPM)\b", message, re.I)
        or re.search(r"tokens per day\s*\(TPD\)|tokens per minute\s*\(TPM\)|requests per (?:day|minute)", message, re.I)
    )
    return retry_after, insufficient_balance, organization_quota


class AIAgent:
    def __init__(self):
        self.groq_clients = []
        for key in config.GROQ_API_KEYS:
            try:
                self.groq_clients.append(Groq(api_key=key))
            except Exception:
                pass

        self.groq_cooldowns = [0.0] * len(self.groq_clients)
        self.groq_disabled = [False] * len(self.groq_clients)

        # OmniRoute and Kimi clients
        self.omniroute_disabled = True
        self.kimi_disabled = True

    def _call_with_fallback(self, messages: list, json_mode: bool = False) -> str:
        last_error = None
        now = time.monotonic()

        for client_index, client in enumerate(self.groq_clients):
            if self.groq_disabled[client_index] or self.groq_cooldowns[client_index] > now:
                continue

            for model in MODELS:
                try:
                    kwargs = {
                        "model": model,
                        "messages": messages,
                    }
                    if json_mode:
                        kwargs["response_format"] = {"type": "json_object"}
                    resp = client.chat.completions.create(**kwargs)
                    return resp.choices[0].message.content
                except Exception as e:
                    rate_limit = _rate_limit_details(e)
                    if rate_limit is not None:
                        retry_after, insufficient_balance, organization_quota = rate_limit
                        if insufficient_balance:
                            self.groq_disabled[client_index] = True
                            last_error = e
                            break
                        last_error = e
                        continue

                    status_code = getattr(e, "status_code", None)
                    if status_code in (401, 403):
                        error_text = str(e).lower()
                        if "invalid" in error_text or "unauthorized" in error_text:
                            self.groq_disabled[client_index] = True
                            break
                        continue

                    last_error = e
                    continue

            self.groq_cooldowns[client_index] = time.monotonic() + 10

        if all(self.groq_disabled) and self.groq_clients:
            raise AIProviderRateLimitError(
                "All configured Groq API keys reported invalid credentials.",
                insufficient_balance=True,
            ) from last_error

        raise AIProviderRateLimitError(
            "All Groq keys in short rotation cooldown.",
            retry_after_seconds=5,
        ) from last_error

    def draft_initial_outreach(self, lead: dict) -> dict:
        """
        Drafts a high-impact, catchy, human-like proposal email with tasteful emojis
        specifically designed for UK business owners.
        """
        biz_name = lead.get('Business Name', lead.get('name', 'Business'))
        location = lead.get('City / Address', lead.get('location', 'UK'))
        category = lead.get('Category', lead.get('sector', 'Local Business'))
        website = lead.get('Website', lead.get('website', 'None'))
        pitch_angle = lead.get('Freelance Pitch Angle', lead.get('pitch_angle', 'Modern mobile rebuild'))
        detected_flaws = "; ".join(lead.get('Website Issues', [])) if lead.get('Website Issues') else "Outdated mobile UX, missing Google Schema"

        prompt = f"""
You are {config.SENDER_NAME}, an independent web designer and conversion specialist reaching out to an independent UK business.
Write a warm, authentic, highly engaging proposal email. It should feel handwritten by a real human, not an automated robot, and include tasteful emojis to make it lively and easy to scan.

Target UK Business Details:
- Business Name: {biz_name}
- Category: {category}
- Location: {location}
- Current Website: {website}
- Detected Friction Points: {detected_flaws}
- Pitch Angle: {pitch_angle}
- Base Flat Price: {config.BASE_PRICE} (UK Pounds £)

Strict Writing Guidelines for UK Business Owners:
1. Tone: Warm, human, friendly, professional British tone. Use natural contractions ("I've", "you'd", "we're").
2. Emojis: Include 3-5 tasteful emojis (e.g. ✨, 💡, 📍, ☕, 📱, 🚀) to structure points and make it catchy.
3. Structure like a High-Quality Mini-Proposal:
   - Opening: A friendly greeting ("Hi {biz_name} team," or "Hi there,") and a warm compliment showing you noticed their spot in {location}.
   - The Audit / Friction: Mention that while checking their website on a phone, you noticed 1-2 specific friction points (e.g., menu/services aren't thumb-friendly, missing Google Maps Schema markup, or lack of instant 1-click booking/enquiry).
   - The Proposal: Outline a crisp 2-3 bullet point upgrade:
     • 📱 Modern, clean mobile-first redesign built for 2026
     • ⚡ 1-click WhatsApp/Call button & fast booking calendar
     • 📍 Google Maps Schema so more locals in {location} find you
   - The Offer & Terms: Flat {config.BASE_PRICE} (strictly British Pounds £129, no hidden fees, no monthly retainer, 100% full ownership). Delivered in 48 to 72 hours.
   - Low-Pressure CTA: Ask if they’d be open to seeing a free 60-second video demo or concept preview for {biz_name} this week.
4. Add this exact standalone sentence right before sign-off: "Examples of my recent work: [[PORTFOLIO_LINK]]"
5. British Sign-off: "Cheers,\n{config.SENDER_NAME}" or "Warm regards,\n{config.SENDER_NAME}".
6. No raw URLs. Currency must ALWAYS be British Pounds (£129). Never mention Dollars ($) or Rupees (₹).

Output format (Valid JSON only):
{{
    "subject": "Catchy, authentic subject line with an emoji (e.g. 'Quick idea for {biz_name} ✨' or 'Spotted your website in {location} 💡')",
    "body": "The full formatted email body"
}}
"""
        messages = [
            {"role": "system", "content": "You are a master UK copywriter who writes human, authentic, high-converting web design proposals for British business owners with clean emoji formatting. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=True)
        result = json.loads(content)
        result["body"] = _ensure_portfolio_reference(
            result.get("body", ""), "Examples of my recent work: [[PORTFOLIO_LINK]]"
        )
        return result

    def draft_followup_pitch(self, lead: dict, previous_subject: str = "") -> dict:
        """
        Drafts a high-impact, gentle follow-up email with emojis and deeper audit points.
        """
        biz_name = lead.get('Business Name', lead.get('name', 'Business'))
        location = lead.get('City / Address', lead.get('location', 'UK'))
        detected_flaws = "; ".join(lead.get('Website Issues', [])) if lead.get('Website Issues') else "Slow mobile load, missing reviews proof"

        prompt = f"""
You are {config.SENDER_NAME}, following up with the owner of {biz_name} in {location}.
Write a polite, warm, human-like follow-up email. Keep it light, friendly, with 2-3 tasteful emojis.

Target Details:
- Business Name: {biz_name}
- Location: {location}
- Audit Observations: {detected_flaws}
- Price: {config.BASE_PRICE} (flat fee)
- Previous Subject: {previous_subject or "Our initial note"}

Guidelines:
1. Acknowledge they're probably busy running {biz_name}.
2. Mention you drafted a quick concept layout that solves the mobile navigation and Google Maps visibility.
3. Reiterate the flat {config.BASE_PRICE} rate and 48-72h turnaround.
4. Add: "Examples of my recent work: [[PORTFOLIO_LINK]]"
5. Friendly British sign-off: "Cheers,\n{config.SENDER_NAME}".

Output format (Valid JSON only):
{{
    "subject": "Follow-up subject line (e.g. 'Quick follow-up for {biz_name} ☕' or 'Re: {previous_subject}')",
    "body": "The full formatted email body"
}}
"""
        messages = [
            {"role": "system", "content": "You write polite, human, effective follow-up emails for British local business owners. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=True)
        result = json.loads(content)
        result["body"] = _ensure_portfolio_reference(
            result.get("body", ""), "Examples of my recent work: [[PORTFOLIO_LINK]]"
        )
        return result

    def answer_incoming_reply(self, lead: dict, incoming_message: str) -> str:
        """
        Drafts a high-converting, professional response to an interested UK business owner.
        """
        prompt = f"""
You are {config.SENDER_NAME}, responding to a reply from a UK business owner.
Business Name: {lead.get('Business Name', 'Client')}
Their Message: "{incoming_message}"

Guidelines:
1. Be warm, enthusiastic, polite, and British in tone.
2. Answer their question clearly.
3. Reiterate the flat {config.BASE_PRICE} price, 48-72 hour delivery, and offer to share a preview or hop on a 5-minute call.
4. Include: "Recent client examples: [[PORTFOLIO_LINK]]"
5. Sign-off: "Cheers,\n{config.SENDER_NAME}".
"""
        messages = [
            {"role": "system", "content": "You are a professional web consultant assisting UK business owners. Reply directly in text."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=False)
        return _ensure_portfolio_reference(content, "Recent client examples: [[PORTFOLIO_LINK]]")
