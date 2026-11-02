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
1. NO FILLER OPENERS: NEVER start with "I came across your business", "While reviewing places in {location}", or "I stumbled upon your website". Cut all introductory fluff and hit their exact operational pain point immediately in the first sentence.
2. NO PRICING: NEVER mention prices, costs, rates, £129, or discounts. We do not sell cheap websites; we discuss business profit, booking leakage, and beating local competitors.
3. Tone: Confident, sharp, executive-level British English. Include 3-4 tasteful emojis (✨, 💡, 📈, 📱, 🚀) to keep it engaging and modern.
4. Business Value Structure:
   - Direct Pain Point Opening: "Hi {biz_name} team," followed immediately by how local mobile customers in {location} are currently slipping away to competing businesses because of {detected_flaws}. Over 75% of customers search and decide on mobile within seconds; any friction sends them straight to a local competitor.
   - The Competitive Edge Solution: Show how eliminating this friction helps them capture high-intent customers before competitors do:
     • ⚡ 1-Tap Direct Action: Instant booking / inquiry widget capturing high-intent and after-hours customers before they bounce.
     • 📍 Local Search Dominance: Outpositioning competitors in {location} mobile search with sub-second page speed.
     • 📈 Revenue Retention: Turning mobile visitors into confirmed, paying customers instead of losing them.
   - DIRECT CALL TO ACTION (NO COMPLIMENTARY WALKTHROUGH FLUFF): Ask directly for a brief 10-minute Google Meet or phone call:
     "Would you be open to a brief 10-minute Google Meet or quick call this Thursday or Friday to look at how we can eliminate this leak and outposition your local competitors?"
5. Add this exact standalone sentence right before sign-off: "Explore recent selected systems (ONYX, PDR World, Kaktus, Salvas): [[PORTFOLIO_LINK]]"
6. Sign-off:
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
            {"role": "system", "content": "You write high-converting, executive-level business growth emails for UK business owners focusing on ROI and competitor dominance without mentioning pricing. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        content = self._call_with_fallback(messages, json_mode=True)
        result = json.loads(content)
        result["body"] = _ensure_portfolio_reference(
            result.get("body", ""), "Explore recent selected systems (ONYX, PDR World, Kaktus, Salvas): [[PORTFOLIO_LINK]]"
        )
        return result

    def draft_followup_pitch(self, lead: dict, previous_subject: str = "") -> dict:
        """
        Drafts a high-impact, direct follow-up email from Kicksa Studio focusing on competitor dominance and scheduling a brief meet.
        """
        biz_name = lead.get('Business Name', lead.get('name', 'Business'))
        location = lead.get('City / Address', lead.get('location', 'UK'))
        detected_flaws = "; ".join(lead.get('Website Issues', [])) if lead.get('Website Issues') else "Slow mobile load, missing reviews proof"

        prompt = f"""
You are {config.SENDER_NAME} from Kicksa Studio, following up with the owner/director of {biz_name} in {location}.
Write a polite, direct, concise follow-up email focusing on booking retention and beating local competitors.
DO NOT mention prices or cheap fees. DO NOT offer a video walkthrough. Ask for a brief 10-minute meet.

Target Details:
- Business Name: {biz_name}
- Location: {location}
- Friction Point: {detected_flaws}
- Previous Subject: {previous_subject or "Our initial note"}

Guidelines:
1. Keep it short (under 90 words).
2. Point out that local competitors in {location} are picking up high-intent mobile searches simply because of minor mobile friction on their end.
3. Ask if they have 10 minutes for a quick Google Meet this week to walk through how to plug this leak.
4. Add: "Explore recent selected systems (ONYX, PDR World, Kaktus, Salvas): [[PORTFOLIO_LINK]]"
5. Sign-off:
   Warm regards,
   {config.SENDER_NAME}
   Kicksa Studio

Output format (Valid JSON only):
{{
    "subject": "Follow-up subject line (e.g. '10 min quick chat for {biz_name}? ☕' or 'Re: {previous_subject}')",
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
            result.get("body", ""), "Explore recent selected systems (ONYX, PDR World, Kaktus, Salvas): [[PORTFOLIO_LINK]]"
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
