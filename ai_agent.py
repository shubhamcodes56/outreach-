"""
Nexus UK AI Proposal Generator & Drafting Agent (Kicksa Studio).
Generates high-converting, business-revenue focused proposals without upfront pricing.
Focuses on ROI, customer acquisition, booking leakage, and profit growth.
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
    
    # Remove any raw URLs the model might have written inside the letter
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
        Drafts a high-impact, business-minded proposal from Kicksa Studio.
        Focuses on ROI, customer acquisition, booking leakage, and revenue growth.
        NEVER mentions upfront pricing.
        """
        biz_name = lead.get('Business Name', lead.get('name', 'Business'))
        location = lead.get('City / Address', lead.get('location', 'UK'))
        category = lead.get('Category', lead.get('sector', 'Local Business'))
        website = lead.get('Website', lead.get('website', 'None'))
        pitch_angle = lead.get('Freelance Pitch Angle', lead.get('pitch_angle', 'Modern mobile rebuild'))
        detected_flaws = "; ".join(lead.get('Website Issues', [])) if lead.get('Website Issues') else "Mobile friction & missing Google Schema"

        prompt = f"""
You are {config.SENDER_NAME} from Kicksa Studio, a premium digital systems agency helping high-performing UK local businesses scale direct bookings, enquiries, and profit.
Write an authentic, highly engaging business-growth email to the owner/director of {biz_name}.
Think like a seasoned digital partner who cares about their bottom-line revenue, not a cheap freelancer selling web pages.

Target Business Details:
- Business Name: {biz_name}
- Industry: {category}
- Location: {location}
- Current Web Presence: {website}
- Observed Digital Friction: {detected_flaws}
- Core Angle: {pitch_angle}

STRICT WRITING RULES:
1. NO PRICING: NEVER mention prices, costs, rates, £129, or discounts. We do not sell cheap websites; we discuss business profit, booking leakage, and customer conversion.
2. Tone: Confident, sharp, warm, executive-level, professional British English. Include 3-4 tasteful emojis (✨, 💡, 📈, 📱, 🚀) to keep it engaging and modern.
3. Business Value Structure:
   - Opening: A respectful, genuine greeting to the {biz_name} team, recognizing their strong reputation in {location}.
   - The Revenue Leak: Explain that while auditing their digital customer journey on mobile, you identified a friction point that quietly costs them paying customers every single week:
     (e.g., over 70% of high-intent local customers browse on phones—if menus/services are hard to tap or booking takes more than 2 clicks, they immediately bounce to a competitor).
   - The Profit Solution: Outline how Kicksa builds custom high-converting mobile engines:
     • ⚡ Instant 1-tap booking / table reservation & WhatsApp call widget (capturing after-hours enquiries).
     • 📍 Google Maps & Local Schema integration so you rank above local competitors when customers search in {location}.
     • 📈 Built-in trust architecture with live Google Review showcase.
   - Low-Pressure Next Step: Offer to send over a complimentary 60-second video walkthrough showing the exact spots where {biz_name} is losing mobile traffic and how we eliminate that friction.
4. Add this exact standalone sentence right before sign-off: "Explore recent Kicksa systems & live builds: [[PORTFOLIO_LINK]]"
5. Sign-off:
   Warm regards,
   {config.SENDER_NAME}
   Kicksa Studio

Output format (Valid JSON only):
{{
    "subject": "Compelling, executive subject line with emoji (e.g. 'A quick observation regarding {biz_name} 💡' or 'Revenue & mobile booking idea for {biz_name} ✨')",
    "body": "The complete formatted email body"
}}
"""
        messages = [
            {"role": "system", "content": "You write high-converting, executive-level business growth emails for UK business owners focusing on ROI and customer acquisition without mentioning pricing. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=True)
        result = json.loads(content)
        result["body"] = _ensure_portfolio_reference(
            result.get("body", ""), "Explore recent Kicksa systems & live builds: [[PORTFOLIO_LINK]]"
        )
        return result

    def draft_followup_pitch(self, lead: dict, previous_subject: str = "") -> dict:
        """
        Drafts a high-impact, gentle follow-up email from Kicksa Studio focusing on business profit and booking impact.
        """
        biz_name = lead.get('Business Name', lead.get('name', 'Business'))
        location = lead.get('City / Address', lead.get('location', 'UK'))
        detected_flaws = "; ".join(lead.get('Website Issues', [])) if lead.get('Website Issues') else "Slow mobile load, missing reviews proof"

        prompt = f"""
You are {config.SENDER_NAME} from Kicksa Studio, following up with the owner/director of {biz_name} in {location}.
Write a polite, warm, concise follow-up email focusing on booking retention and customer acquisition.
DO NOT mention prices or cheap fees. Keep it focused on revenue and customer experience.

Target Details:
- Business Name: {biz_name}
- Location: {location}
- Friction Point: {detected_flaws}
- Previous Subject: {previous_subject or "Our initial note"}

Guidelines:
1. Acknowledge they're busy running daily operations at {biz_name}.
2. Reiterate that we mapped out a quick concept showing how eliminating mobile friction increases direct reservations/enquiries in {location}.
3. Ask if they’d be open to a 60-second video demo showing how this works.
4. Add: "Explore recent Kicksa systems & live builds: [[PORTFOLIO_LINK]]"
5. Sign-off:
   Warm regards,
   {config.SENDER_NAME}
   Kicksa Studio

Output format (Valid JSON only):
{{
    "subject": "Follow-up subject line (e.g. 'Quick follow-up for {biz_name} ☕' or 'Re: {previous_subject}')",
    "body": "The full formatted email body"
}}
"""
        messages = [
            {"role": "system", "content": "You write polite, executive-level follow-up emails for British local business owners focusing on ROI. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=True)
        result = json.loads(content)
        result["body"] = _ensure_portfolio_reference(
            result.get("body", ""), "Explore recent Kicksa systems & live builds: [[PORTFOLIO_LINK]]"
        )
        return result

    def answer_incoming_reply(self, lead: dict, incoming_message: str) -> str:
        """
        Drafts a high-converting, professional response to an interested UK business owner from Kicksa Studio.
        """
        prompt = f"""
You are {config.SENDER_NAME} from Kicksa Studio, responding to a reply from a UK business owner.
Business Name: {lead.get('Business Name', 'Client')}
Their Message: "{incoming_message}"

Guidelines:
1. Be warm, enthusiastic, polite, and British in tone.
2. Answer their question with clarity and confidence.
3. Focus on their business goals (more bookings, seamless mobile experience, saving staff time).
4. Offer to share a personalized 60-second concept preview or arrange a quick 5-minute call.
5. Include: "Recent client systems & live builds: [[PORTFOLIO_LINK]]"
6. Sign-off:
   Warm regards,
   {config.SENDER_NAME}
   Kicksa Studio
"""
        messages = [
            {"role": "system", "content": "You are a senior digital consultant at Kicksa Studio assisting UK business owners. Reply directly in text."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=False)
        return _ensure_portfolio_reference(content, "Recent client systems & live builds: [[PORTFOLIO_LINK]]")
