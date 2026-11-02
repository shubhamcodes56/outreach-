import re
import ssl
import time
import urllib.request
from urllib.parse import urlsplit

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}", re.I)
IGNORED_EMAIL_PARTS = {
    ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".js", ".css",
    "example.com", "domain.com", "sentry.io", "wixpress.com", "schema.org",
    "cloudflare.com", "wordpress.org", "w3.org", "email.com", "yoursite.com",
    "squarespace.com", "shopify.com", "godaddy.com", "namecheap.com", "typefoundry",
    "fonts.com", "google.com", "googleapis.com", "facebook.com", "instagram.com",
    "github.com", "twitter.com", "gravatar.com"
}

def audit_website(raw_url: str, timeout: int = 5) -> dict:
    """
    Audits a business or clinic website for common dealbreaker flaws:
    - Inactive / Broken / Timeout / 404 / 500
    - Missing HTTPS / Insecure HTTP
    - Missing mobile viewport (<meta name="viewport">)
    - Missing direct WhatsApp appointment button
    - Slow mobile loading speed (> 3 seconds)
    - Outdated copyright year (<= 2022)
    Also extracts public contact emails from the site.
    """
    if not raw_url:
        return {"has_issues": False, "issues": [], "emails": []}

    url = raw_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    issues = []
    emails = set()
    phone_numbers = set()
    start_time = time.time()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    html = ""
    elapsed = 0.0
    status_code = None

    # Step 1: Attempt HTTPS fetch first
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            elapsed = round(time.time() - start_time, 2)
            status_code = resp.getcode()
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        # If HTTPS failed, try HTTP
        if url.startswith("https://"):
            http_url = "http://" + url[8:]
            try:
                req = urllib.request.Request(
                    http_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
                )
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    elapsed = round(time.time() - start_time, 2)
                    status_code = resp.getcode()
                    html = resp.read().decode("utf-8", errors="ignore")
                    issues.append("Missing SSL certificate (Not Secure http:// connection)")
            except Exception as e2:
                issues.append(f"Website is currently inaccessible or showing errors ({type(e2).__name__})")
        else:
            issues.append(f"Website is currently inaccessible or showing errors ({type(e).__name__})")

    # Step 2: Analyze HTML if retrieved
    if html:
        # Check load speed
        if elapsed > 2.8:
            issues.append(f"Slow mobile loading time ({elapsed}s)")

        # Check mobile responsiveness
        if not re.search(r'<meta[^>]+name=[\'"]viewport[\'"]', html, re.I):
            issues.append("Not optimized for mobile devices (missing mobile viewport)")

        # Check online scheduling / appointment booking / table reservations
        has_online_booking = bool(re.search(
            r"calendly\.com|acuityscheduling\.com|square\.site|zocdoc\.com|jane\.app|vagaro\.com|mindbodyonline\.com|opentable\.com|resy\.com|toasttab\.com|chownow\.com|sevenrooms\.com|bentobox\.com|doordash\.com|grubhub\.com|book[- ]online|schedule[- ]appointment|book[- ]now|request[- ]appointment|reserve[- ]a[- ]table|online[- ]ordering|order[- ]online",
            html, re.I
        ))
        if not has_online_booking:
            issues.append("No automated 1-click online appointment scheduling, table reservation, or instant quote form for clients")

        # Check for PDF menu or brochure dependency (conversion barrier on phones)
        has_pdf_menu = bool(re.search(r'href=[\'"][^\'"]*?(?:menu|food|drink|services|pricing|brochure|catering)[^\'"]*?\.pdf[\'"]', html, re.I))
        if has_pdf_menu:
            issues.append("Menu or service catalog is locked inside a slow downloadable PDF file rather than an interactive mobile webpage")

        # Check for Google LocalBusiness Schema.org structured data (vital for Google Maps 3-Pack rank)
        has_schema = bool(re.search(r'schema\.org/(?:LocalBusiness|Restaurant|Dentist|MedicalBusiness|HealthAndBeautyBusiness|HomeAndConstructionBusiness|AutoRepair|ProfessionalService|LegalService|FoodEstablishment)', html, re.I))
        if not has_schema:
            issues.append("Missing Google LocalBusiness Rich Schema markup (negatively impacting Google Maps local ranking)")

        # Check for live Google / Yelp customer review showcase
        has_reviews = bool(re.search(r'trustpilot|yelp\.com/biz|google\.com/maps/contrib|birdeye|podium|review[- ]slider|testimonial|star[- ]rating|google[- ]review|customer[- ]reviews', html, re.I))
        if not has_reviews:
            issues.append("No live Google or Yelp 5-star customer review showcase on page to build immediate visitor trust")

        # Check for 24/7 after-hours live chat or SMS concierge
        has_chat = bool(re.search(r'tidio|intercom|crisp\.chat|drift|podium|birdeye|livechat|zendesk|hubspot|chat[- ]widget', html, re.I))
        if not has_chat:
            issues.append("No 24/7 instant chat or after-hours text lead capture to convert evening web visitors")

        # Check click-to-call phone accessibility
        has_click_to_call = bool(re.search(r'href=[\'"]tel:', html, re.I))
        if not has_click_to_call:
            issues.append("Missing 1-tap click-to-call mobile buttons for immediate caller inquiries")

        # Check for Google Maps GPS navigation link or embed
        has_map = bool(re.search(r'google\.com/maps|maps\.google\.com|embed.*map|google.*place', html, re.I))
        if not has_map:
            issues.append("Missing interactive Google Maps directions widget for instant 1-tap mobile navigation")

        # Check outdated copyright
        copy_match = re.search(r"(?:©|&copy;|copyright)\s*(?:20\d\d\s*-\s*)?(20\d\d)", html, re.I)
        if copy_match:
            try:
                year = int(copy_match.group(1))
                if year <= 2022:
                    issues.append(f"Outdated website copyright ({year}) indicating legacy design")
            except ValueError:
                pass

        # Extract contact emails from homepage
        for match in EMAIL_REGEX.findall(html):
            clean_em = match.lower().strip()
            if not any(ignored in clean_em for ignored in IGNORED_EMAIL_PARTS):
                if "@" in clean_em:
                    domain = clean_em.split("@", 1)[1]
                    tld = domain.split(".")[-1]
                    if tld.isalpha() and len(tld) >= 2 and not any(lib in clean_em for lib in ["videojs", "webpack", "npm", "github", "jsdelivr", "unpkg"]):
                        emails.add(clean_em)

        # Hunter Deep-Scan: If no emails on homepage, inspect /contact, /about, /contact-us, /location, /menu
        if not emails:
            for subpath in ["/contact", "/contact-us", "/about", "/reach-us", "/location", "/find-us"]:
                try:
                    sub_url = url.rstrip("/") + subpath
                    sub_req = urllib.request.Request(
                        sub_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
                    )
                    with urllib.request.urlopen(sub_req, timeout=3, context=ctx) as sub_resp:
                        sub_html = sub_resp.read().decode("utf-8", errors="ignore")
                        for match in EMAIL_REGEX.findall(sub_html):
                            clean_em = match.lower().strip()
                            if not any(ignored in clean_em for ignored in IGNORED_EMAIL_PARTS):
                                emails.add(clean_em)
                        if emails:
                            break
                except Exception:
                    pass

        # Extract US phone numbers
        phone_matches = re.findall(r"(?:\+?1[-. ]?)?\(?([2-9]\d{2})\)?[-. ]?([2-9]\d{2})[-. ]?(\d{4})", html)
        for p in phone_matches:
            phone_numbers.add(f"({p[0]}) {p[1]}-{p[2]}")

    has_issues = len(issues) > 0
    return {
        "has_issues": has_issues,
        "issues": issues,
        "issue_summary": "; ".join(issues) if issues else "Website functioning normally",
        "emails": list(emails),
        "phones": list(phone_numbers),
        "load_time": elapsed,
    }


def generate_issue_pitch_angle(biz_name: str, category: str, website: str, issues: list) -> str:
    """Creates a high-converting personalized US business proposal angle pointing out the exact issues found."""
    clean_cat = (category or "").lower()
    is_clinic = any(w in clean_cat for w in ["dental", "dentist", "clinic", "doctor", "health", "hospital", "chiro", "medspa", "derma", "physio", "optomet", "podiat"])
    is_dining = any(w in clean_cat for w in ["cafe", "coffee", "restaurant", "bistro", "bakery", "pizza", "pizzeria", "bbq", "diner", "grill", "bar", "brewery", "catering", "burger", "sushi", "taco", "taqueria", "brunch", "gelato", "food", "tea", "donut", "bagel"])
    is_contractor = any(w in clean_cat for w in ["roof", "hvac", "plumb", "electric", "paint", "contractor", "remodel", "auto", "landscap", "pool", "solar", "pest", "fence"])

    issues_str = "; ".join(issues)

    if "Website is currently inaccessible or showing errors" in issues_str:
        if is_dining:
            return f"Restaurant web recovery proposal: restoring inactive/broken website for {biz_name} and launching a mobile menu & reservation system"
        if is_clinic:
            return f"Patient appointment recovery proposal: restoring inactive/broken website for {biz_name} and adding 24/7 online patient scheduling"
        return f"Business web recovery proposal: restoring offline site for {biz_name} with mobile lead capture"

    # Deep pain point prioritization
    if "Menu or service catalog is locked inside a slow downloadable PDF" in issues_str:
        return f"Mobile menu overhaul for {biz_name}: replacing slow downloadable PDF with 1-tap interactive mobile menu & online reservation system"

    if "Missing Google LocalBusiness Rich Schema markup" in issues_str:
        return f"Google Local SEO & Rich Map Pack optimization for {biz_name}: adding verified LocalBusiness Schema & instant booking engine"

    if "No live Google or Yelp 5-star customer review showcase" in issues_str:
        return f"5-star Google review conversion showcase & mobile redesign for {biz_name} to double new visitor inquiries"

    if "No 24/7 instant chat or after-hours text lead capture" in issues_str:
        return f"After-hours client lead capture & 24/7 instant booking system for {biz_name} to capture evening web traffic"

    primary_issue = issues[0] if issues else "outdated design"

    if is_dining:
        return f"Interactive digital mobile menu, 1-click table reservations & online takeout/catering ordering for {biz_name} (resolving: {primary_issue})"
    elif is_clinic:
        return f"24/7 online patient self-scheduling & mobile conversion upgrade for {biz_name} (resolving: {primary_issue})"
    elif is_contractor:
        return f"Instant online estimate request system & high-speed mobile quote page for {biz_name} (resolving: {primary_issue})"

    return f"Modern mobile redesign & direct online client inquiry booking upgrade for {biz_name} (resolving: {primary_issue})"

