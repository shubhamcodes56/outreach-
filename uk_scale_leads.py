"""
Nexus UK Lead Pipeline & Validation Engine.
Harvests verified UK businesses, conducts live audits, and prepares candidate leads.
"""

import json
import os
import re
import time
from uk_web_crawler import harvest_uk_web_candidates, is_genuine_business_email as is_valid_email


def harvest_real_uk_leads(
    target_count: int = 1500,
    existing_db: dict = None,
    on_lead_found=None,
    on_status=None,
    require_no_website: bool = False,
) -> list:
    if existing_db is None:
        existing_db = {}

    discovered = []
    seen_emails = set(existing_db.keys())

    def report_status(message):
        if on_status:
            try:
                on_status(message)
            except Exception:
                pass

    report_status("Searching UK commercial markets across England, Scotland, Wales & Northern Ireland...")
    candidates = harvest_uk_web_candidates(on_status=report_status)

    for cand in candidates:
        em = cand.get("email", "").strip().lower()
        if not is_valid_email(em) or em in seen_emails:
            continue

        seen_emails.add(em)
        lead_info = cand.get("lead_info", {})
        item = {
            "email": em,
            "lead_info": lead_info,
            "status": "NEW",
            "draft": None,
            "history": [],
            "error_message": None,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        discovered.append(item)
        if on_lead_found:
            try:
                on_lead_found(item)
            except Exception:
                pass

    report_status(f"UK harvest pass complete: {len(discovered)} qualified leads added.")
    return discovered
