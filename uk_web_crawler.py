"""
Nexus UK & British Isles Live Web Discovery & Audit Engine.
Discovers verified independent businesses across hundreds of UK cities and towns,
inspects their live websites for real conversion flaws, and generates qualified leads.
"""

import json
import os
import re
import time
from groq import Groq
import config
from website_auditor import audit_website, generate_issue_pitch_angle

STATE_FILE = os.path.join(os.path.dirname(__file__), "web_discovery_uk_state.json")

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

IGNORED_DOMAINS = {
    "sentry.io", "wixpress.com", "example.com", "cloudflare.com", "google.com",
    "yell.com", "checkatrade.com", "trustpilot.com", "tripadvisor.co.uk", "tripadvisor.com",
    "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "linkedin.com",
    "youtube.com", "apple.com", "microsoft.com", "github.com", "schema.org",
    "wordpress.org", "godaddy.com", "squarespace.com"
}

# 250+ UK Cities, Towns, and Commercial Districts Across England, Scotland, Wales, and Northern Ireland
UK_LOCATIONS = [
    # Greater London & Suburbs
    "Central London UK", "City of Westminster London UK", "Camden London UK", "Islington London UK",
    "Hackney London UK", "Greenwich London UK", "Kensington and Chelsea London UK", "Richmond London UK",
    "Croydon Greater London UK", "Wimbledon London UK", "Fulham London UK", "Kingston upon Thames UK",
    "Bromley Greater London UK", "Ealing London UK", "Enfield London UK", "Harrow Greater London UK",
    "Barnet London UK", "Stratford London UK", "Shoreditch London UK", "Canary Wharf London UK",
    "Clapham London UK", "Battersea London UK", "Chiswick London UK", "Hampstead London UK",

    # West Midlands & Central England
    "Birmingham West Midlands UK", "Coventry UK", "Wolverhampton UK", "Solihull West Midlands UK",
    "Dudley UK", "Walsall UK", "West Bromwich UK", "Stourbridge UK", "Sutton Coldfield UK",
    "Royal Leamington Spa UK", "Warwick UK", "Stratford-upon-Avon UK", "Worcester UK", "Hereford UK",
    "Shrewsbury Shropshire UK", "Telford UK", "Stafford UK", "Stoke-on-Trent UK", "Lichfield UK",
    "Tamworth Staffordshire UK", "Kidderminster UK", "Redditch Worcestershire UK",

    # Greater Manchester & North West
    "Manchester City Centre UK", "Salford Greater Manchester UK", "Bolton UK", "Stockport UK",
    "Oldham UK", "Rochdale UK", "Bury Greater Manchester UK", "Wigan UK", "Altrincham UK",
    "Sale Greater Manchester UK", "Cheadle Greater Manchester UK", "Wilmslow Cheshire UK",
    "Liverpool Merseyside UK", "Birkenhead Wirral UK", "Southport Merseyside UK", "St Helens Merseyside UK",
    "Chester Cheshire UK", "Warrington UK", "Preston Lancashire UK", "Blackpool UK",
    "Lancaster UK", "Blackburn UK", "Burnley UK", "Carlisle Cumbria UK", "Kendal Lake District UK",
    "Macclesfield Cheshire UK", "Crewe Cheshire UK", "Ellesmere Port UK",

    # Yorkshire & The Humber
    "Leeds West Yorkshire UK", "Sheffield South Yorkshire UK", "Bradford West Yorkshire UK",
    "York North Yorkshire UK", "Harrogate North Yorkshire UK", "Huddersfield UK", "Halifax West Yorkshire UK",
    "Wakefield UK", "Doncaster South Yorkshire UK", "Rotherham UK", "Barnsley UK",
    "Hull East Yorkshire UK", "Grimsby UK", "Scunthorpe UK", "Scarborough North Yorkshire UK",
    "Ripon North Yorkshire UK", "Skipton North Yorkshire UK", "Beverley East Yorkshire UK",

    # North East England
    "Newcastle upon Tyne UK", "Gateshead UK", "Sunderland Tyne and Wear UK", "Durham UK",
    "Middlesbrough UK", "Darlington UK", "Hartlepool UK", "South Shields UK", "Tynemouth UK",
    "Stockton-on-Tees UK", "Hexham Northumberland UK",

    # East Midlands
    "Nottingham Nottinghamshire UK", "Leicester Leicestershire UK", "Derby Derbyshire UK",
    "Northampton UK", "Lincoln Lincolnshire UK", "Mansfield UK", "Chesterfield Derbyshire UK",
    "Loughborough UK", "Kettering UK", "Corby UK", "Boston Lincolnshire UK", "Newark-on-Trent UK",
    "Grantham Lincolnshire UK", "Hinckley Leicestershire UK", "Melton Mowbray UK",

    # South West England
    "Bristol UK", "Bath Somerset UK", "Plymouth Devon UK", "Exeter Devon UK",
    "Bournemouth Dorset UK", "Poole Dorset UK", "Cheltenham Gloucestershire UK", "Gloucester UK",
    "Swindon Wiltshire UK", "Salisbury Wiltshire UK", "Torquay Devon UK", "Taunton Somerset UK",
    "Truro Cornwall UK", "Newquay Cornwall UK", "Falmouth Cornwall UK", "Weston-super-Mare UK",
    "Weymouth Dorset UK", "St Ives Cornwall UK", "Penzance Cornwall UK", "Barnstaple Devon UK",

    # South East, Home Counties & East Anglia
    "Brighton and Hove East Sussex UK", "Oxford Oxfordshire UK", "Cambridge Cambridgeshire UK",
    "Southampton Hampshire UK", "Portsmouth Hampshire UK", "Reading Berkshire UK",
    "Milton Keynes Buckinghamshire UK", "Slough Berkshire UK", "Windsor Berkshire UK",
    "Maidstone Kent UK", "Canterbury Kent UK", "Tunbridge Wells Kent UK", "Chatham Kent UK",
    "Guildford Surrey UK", "Woking Surrey UK", "Epsom Surrey UK", "Farnham Surrey UK",
    "St Albans Hertfordshire UK", "Watford Hertfordshire UK", "Hemel Hempstead UK", "Stevenage UK",
    "Chelmsford Essex UK", "Colchester Essex UK", "Southend-on-Sea Essex UK", "Brentwood Essex UK",
    "Norwich Norfolk UK", "Ipswich Suffolk UK", "Bury St Edmunds UK", "Peterborough Cambridgeshire UK",
    "Bedford Bedfordshire UK", "Luton Bedfordshire UK", "Aylesbury Buckinghamshire UK", "Chichester West Sussex UK",
    "Winchester Hampshire UK", "Basingstoke Hampshire UK", "Eastbourne East Sussex UK", "Hastings East Sussex UK",
    "Folkestone Kent UK", "Dover Kent UK", "Crawley West Sussex UK", "Horsham West Sussex UK",

    # Scotland
    "Glasgow Scotland UK", "Edinburgh Scotland UK", "Aberdeen Scotland UK", "Dundee Scotland UK",
    "Inverness Scottish Highlands UK", "Stirling Scotland UK", "Perth Scotland UK",
    "Paisley Renfrewshire UK", "East Kilbride Scotland UK", "Dunfermline Fife UK",
    "Livingston West Lothian UK", "Ayr South Ayrshire UK", "Kilmarnock Scotland UK",
    "Falkirk Scotland UK", "Dumfries Scotland UK", "St Andrews Fife UK", "Motherwell Scotland UK",

    # Wales (Cymru)
    "Cardiff Wales UK", "Swansea Wales UK", "Newport South Wales UK", "Wrexham North Wales UK",
    "Bangor Gwynedd Wales UK", "Barry Vale of Glamorgan UK", "Bridgend Wales UK",
    "Llanelli Wales UK", "Neath Wales UK", "Aberystwyth Ceredigion UK", "Llandudno Conwy UK",
    "Caerphilly Wales UK", "Rhyl Denbighshire UK", "Merthyr Tydfil Wales UK", "Carmarthen Wales UK",

    # Northern Ireland
    "Belfast Northern Ireland UK", "Derry Londonderry Northern Ireland UK", "Lisburn Northern Ireland UK",
    "Newry Northern Ireland UK", "Bangor County Down UK", "Craigavon County Armagh UK",
    "Newtownabbey Northern Ireland UK", "Ballymena County Antrim UK", "Coleraine Northern Ireland UK",
    "Omagh County Tyrone UK", "Enniskillen County Fermanagh UK"
]

# 160+ High-Converting Commercial Niches in the UK
UK_SECTORS = [
    # Specialty Cafes, Bakeries & Dining
    "artisan coffee shop and espresso bar",
    "specialty coffee roastery and cafe",
    "independent sourdough bakery and patisserie",
    "gastro pub and craft alehouse",
    "traditional British pub and dining room",
    "independent bistro and wine bar",
    "fish and chips restaurant and takeaway",
    "afternoon tea room and tea parlour",
    "wood fired artisan pizza restaurant",
    "craft burger and smokehouse kitchen",
    "authentic ramen and noodle bar",
    "plant based vegan and vegetarian cafe",
    "farm to table local restaurant",
    "artisan gelato and dessert parlour",
    "independent tapas and pintxos bar",

    # Private Healthcare, Dental & Aesthetics
    "private dental practice and implant clinic",
    "cosmetic dentistry and Invisalign clinic",
    "teeth whitening and smile makeover studio",
    "aesthetic skin clinic and Botox doctor",
    "laser skin clinic and hair removal centre",
    "dermatology and anti-ageing clinic",
    "physiotherapy and sports injury clinic",
    "osteopathy and physical therapy centre",
    "chiropractic clinic and spinal wellness",
    "podiatry and chiropody clinic",
    "private medical and health screening clinic",
    "acupuncture and holistic wellness clinic",
    "independent optician and eyewear boutique",
    "hearing care and audiology centre",

    # Trades & Property Services (UK Tradies)
    "Gas Safe registered heating engineer and boiler installation",
    "emergency domestic plumber and bathroom fitter",
    "NICEIC registered electrician and electrical contractor",
    "roofing contractor and guttering specialist",
    "independent builder and home extension specialist",
    "joinery and bespoke carpenter",
    "painter and decorator commercial and domestic",
    "locksmith and 24-hour security specialist",
    "double glazing and window door installer",
    "damp proofing and timber treatment specialist",
    "landscape gardener and driveway paving contractor",
    "tree surgeon and arborist service",
    "plastering and rendering contractor",
    "kitchen designer and bespoke installation",
    "air conditioning and heat pump installer",
    "carpet cleaning and upholstery specialist",
    "domestic and commercial pest control",

    # Auto, Garage & MOT
    "mobile car valeting and detailing service",
    "ceramic paint protection and auto detailing studio",
    "independent garage and MOT testing station",
    "car service and diagnostic mechanic",
    "mobile tyre fitting and puncture repair",
    "car body repair and dent removal specialist",
    "vehicle wrapping and window tinting",
    "EV home charger installer and specialist",

    # Hair, Beauty & Grooming
    "gentlemen's traditional barbershop",
    "boutique hair salon and colour specialist",
    "lash extension and brow lamination studio",
    "nail salon and luxury manicure bar",
    "luxury day spa and massage sanctuary",
    "bridal hair and makeup artist studio",
    "semi-permanent makeup and microblading clinic",

    # Boutique Fitness, Sports & Leisure
    "boutique reformer Pilates and yoga studio",
    "CrossFit box and strength conditioning gym",
    "boxing and martial arts academy",
    "personal training and fitness studio",
    "indoor golf simulator lounge and coaching studio",
    "dance academy and performing arts school",
    "climbing and bouldering gym",

    # B2B & Professional Local Services
    "chartered certified accountants and tax advisers",
    "independent estate agent and letting agency",
    "commercial cleaning contractor and office cleaners",
    "architectural designer and planning consultant",
    "wedding and event caterer",
    "commercial and wedding photographer",
    "dog grooming salon and canine spa",
    "independent veterinary clinic and animal hospital",
    "self storage facility and removals service",
    "florist and bespoke floral design studio"
]


def _default_state():
    return {
        "date": time.strftime("%Y-%m-%d"),
        "daily_groq_searches": 0,
        "last_groq_search_epoch": 0,
        "last_groq_search_success_epoch": 0,
        "groq_key_cursor": 0,
        "query_cursor": 0,
        "seen_emails": [],
        "seen_websites": [],
    }


def _load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)
        state = _default_state()
        state.update(saved if isinstance(saved, dict) else {})
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        state = _default_state()

    today = time.strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["daily_groq_searches"] = 0
        state["last_groq_search_epoch"] = 0
        state["last_groq_search_success_epoch"] = 0

    state["daily_groq_searches"] = max(0, int(state.get("daily_groq_searches", 0)))
    state["query_cursor"] = max(0, int(state.get("query_cursor", 0)))
    state["groq_key_cursor"] = max(0, int(state.get("groq_key_cursor", 0)))
    state["pending_leads"] = list(state.get("pending_leads", []))
    state["seen_emails"] = list(state.get("seen_emails", []))[-10000:]
    state["seen_websites"] = list(state.get("seen_websites", []))[-10000:]
    return state


def _save_state(state):
    tmp_path = STATE_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False)
        os.replace(tmp_path, STATE_FILE)
    except OSError:
        pass


def clean_email(email: str) -> str:
    if not email:
        return ""
    em = email.strip().lower()
    em = re.sub(r"^(?:u003[ec]|&[gl]t;|\W)+", "", em)
    em = re.sub(r"[,\s;]+.*$", "", em).strip()
    return em


def is_genuine_business_email(email: str, website: str = "") -> bool:
    if not email or "@" not in email:
        return False
    em = clean_email(email)
    if not EMAIL_RE.match(em):
        return False
    domain = em.split("@", 1)[1]
    if domain in IGNORED_DOMAINS or any(ext in em for ext in [".png", ".jpg", ".svg", ".webp", ".js", ".css"]):
        return False
    if any(fake in em for fake in ["example", "yoursite", "test@", "demo@", "admin@example"]):
        return False
    if any(lib in em for lib in ["videojs", "webpack", "npm", "github", "jsdelivr", "unpkg", "polyfill", "bootstrap", "react@"]):
        return False
    tld = domain.split(".")[-1]
    if not tld.isalpha() or len(tld) < 2:
        return False
    return True


def _call_groq_uk_live_discovery(sector: str, location: str, api_key: str, cursor: int = 0) -> list:
    """
    Uses Groq browser_search to discover real independently owned UK businesses across
    Yell.com, Checkatrade, Google Local UK, and local commercial directories.
    """
    clean_sec = sector.lower()
    is_dining = any(k in clean_sec for k in ["coffee", "cafe", "roastery", "bakery", "pub", "bistro", "restaurant", "tea", "pizza", "burger", "tapas", "ramen", "gelato", "food"])
    is_health = any(k in clean_sec for k in ["dental", "dentist", "smile", "skin", "botox", "laser", "physio", "osteopath", "chiro", "podiatry", "optician", "hearing", "clinic"])
    is_trade = any(k in clean_sec for k in ["plumber", "heating", "gas safe", "boiler", "electric", "roof", "builder", "joiner", "carpenter", "locksmith", "glazing", "painter", "landscape", "tree", "plaster", "kitchen", "cleaner", "pest"])

    if is_trade:
        prompt = (
            f"Search Yell.com, Checkatrade, TrustATrader, and UK business directories for independently owned {sector} businesses located in {location}, United Kingdom.\n"
            "For each real business found, extract:\n"
            "1. Exact Business Name\n"
            "2. Official Website Domain URL (.co.uk or .com)\n"
            "3. Published contact Email (from contact page, footer, or official directory listing)\n"
            "4. Town and County in the UK\n"
            "5. UK Phone number (+44 or 01/02/07)\n\n"
            "Return 12 to 16 real local businesses, one per line in this EXACT pipe-separated format:\n"
            "Business Name | Website URL | Email | City, UK | Phone\n\n"
            "Strict rules: Return ONLY real UK businesses. If email is not directly on the snippet, put N/A and provide the official website URL so our crawler can inspect the webapp. No invented or placeholder emails."
        )
    elif is_health:
        prompt = (
            f"Search Google Local UK, Yell.com, and verified UK directories for {sector} in {location}, United Kingdom.\n"
            "For each real clinic, practice, or salon found, extract:\n"
            "1. Exact Business Name\n"
            "2. Official Website Domain URL\n"
            "3. Published contact Email\n"
            "4. Town and County in the UK\n"
            "5. UK Phone number\n\n"
            "Return 12 to 16 real local businesses, one per line in this EXACT pipe-separated format:\n"
            "Business Name | Website URL | Email | City, UK | Phone\n\n"
            "Strict rules: Return ONLY real UK businesses. If email is not directly on the snippet, put N/A and provide the official website URL. No invented or placeholder emails."
        )
    elif is_dining:
        prompt = (
            f"Search Google Maps UK, Tripadvisor UK, Harden's, SquareMeal, and UK food guides for independent local {sector} in {location}, United Kingdom.\n"
            "For each real cafe, pub, or restaurant found, extract:\n"
            "1. Exact Business Name\n"
            "2. Official Website Domain URL\n"
            "3. Published contact Email\n"
            "4. Town and County in the UK\n"
            "5. UK Phone number\n\n"
            "Return 12 to 16 real local businesses, one per line in this EXACT pipe-separated format:\n"
            "Business Name | Website URL | Email | City, UK | Phone\n\n"
            "Strict rules: Return ONLY real UK businesses. If email is not directly on the snippet, put N/A and provide the official website URL. No invented or placeholder emails."
        )
    else:
        prompt = (
            f"Search the live web in the United Kingdom, Yell.com, and Google Local for independently owned {sector} businesses in {location}, UK.\n"
            "For each real business found, extract:\n"
            "1. Exact Business Name\n"
            "2. Their official Website URL\n"
            "3. Published contact Email (from contact page, footer, or official listing)\n"
            "4. City and County, UK\n"
            "5. UK Phone number\n\n"
            "Return 12 to 16 real businesses, one per line in this EXACT pipe-separated format:\n"
            "Business Name | Website URL | Email | City, UK | Phone\n\n"
            "Strict rules: Return ONLY real UK businesses. If email is not directly on the snippet, put N/A and provide the official website URL so our crawler can inspect the webapp. No invented or placeholder emails."
        )

    client = Groq(api_key=api_key, timeout=75, max_retries=0)
    search_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    content = ""

    for smodel in search_models:
        try:
            response = client.chat.completions.create(
                model=smodel,
                messages=[{"role": "user", "content": prompt}],
                tools=[{"type": "browser_search"}],
                tool_choice="required",
                reasoning_effort="low",
                max_completion_tokens=2200,
            )
            content = response.choices[0].message.content or ""
            if content:
                break
        except Exception as e:
            if smodel == search_models[-1]:
                raise e

    # Clean non-breaking spaces and citation tags
    content = re.sub(r"【.*?】", "", content)
    content = content.replace("\u202f", " ").replace("\xa0", " ")

    results = []
    for line in content.splitlines():
        line = line.strip()
        if "|" in line:
            parts = [p.strip().strip("*`") for p in line.split("|")]
            if len(parts) >= 2:
                name = parts[0]
                url = parts[1].replace(" ", "").rstrip("/")
                email = parts[2].strip() if len(parts) > 2 and "@" in parts[2] else ""
                loc = parts[3].strip() if len(parts) > 3 and parts[3] != "N/A" else location
                phone = parts[4].strip() if len(parts) > 4 and parts[4] != "N/A" else "UK"

                # Filter out markdown header rows
                if "business name" in name.lower() or "website url" in url.lower():
                    continue

                if email:
                    email = re.sub(r"[,\s;]+.*$", "", email).strip().lower()

                if url.startswith(("http://", "https://", "www.")) or "." in url:
                    results.append({
                        "name": name,
                        "url": url if url.startswith("http") else "https://" + url,
                        "email": email,
                        "location": loc,
                        "phone": phone,
                        "category": sector.title(),
                    })
    return results


def harvest_uk_web_candidates(on_status=None) -> list:
    """
    Executes fast-paced UK web discovery, visits client webapps,
    audits their live sites, and returns genuine qualified leads.
    """
    state = _load_state()
    now_epoch = int(time.time())
    daily_limit = max(2000, config.GROQ_SEARCH_DAILY_QUERY_LIMIT)
    minimum_interval = 35

    can_search = (
        state["daily_groq_searches"] < daily_limit
        and (now_epoch - state["last_groq_search_epoch"] >= minimum_interval)
    )

    all_keys = list(dict.fromkeys(
        config.GROQ_SEARCH_API_KEYS + config.GROQ_API_KEYS + ([config.GROQ_API_KEY] if config.GROQ_API_KEY else [])
    ))

    if can_search and all_keys:
        cursor = int(state.get("query_cursor", 0))
        location = UK_LOCATIONS[cursor % len(UK_LOCATIONS)]
        sector = UK_SECTORS[(cursor // len(UK_LOCATIONS)) % len(UK_SECTORS)]
        state["query_cursor"] = cursor + 1

        num_keys = len(all_keys)
        raw_businesses = []

        for attempt in range(num_keys):
            key_index = (state["groq_key_cursor"] + attempt) % num_keys
            api_key = all_keys[key_index]
            try:
                raw_businesses = _call_groq_uk_live_discovery(sector, location, api_key, cursor)
                state["groq_key_cursor"] = (key_index + 1) % num_keys
                state["daily_groq_searches"] += 1
                state["last_groq_search_epoch"] = now_epoch
                state["last_groq_search_success_epoch"] = now_epoch
                _save_state(state)
                if on_status:
                    on_status(
                        f"UK Discovery: Searched '{sector}' in {location} ({state['daily_groq_searches']}/{daily_limit}); "
                        f"found {len(raw_businesses)} candidate businesses."
                    )
                break
            except Exception as e:
                if attempt == num_keys - 1:
                    state["daily_groq_searches"] += 1
                    state["last_groq_search_epoch"] = now_epoch
                    state["groq_key_cursor"] = (state["groq_key_cursor"] + 1) % num_keys
                    _save_state(state)
                    if on_status:
                        code = getattr(e, "status_code", None) or getattr(e, "code", None)
                        on_status(f"UK Discovery search failed ({code}) [{type(e).__name__}].")

        # Now, inspect the actual live webapps of every candidate found!
        seen_sites = set(state.get("seen_websites", []))
        seen_emails = set(state.get("seen_emails", []))
        qualified_leads = []

        for b in raw_businesses:
            url = b["url"]
            if url in seen_sites:
                continue
            seen_sites.add(url)

            try:
                # DEEP WEBAPP AUDIT & EMAIL EXTRACTION
                audit = audit_website(url, timeout=4)
                candidate_email = clean_email(b["email"])

                # If search snippet email was missing, extract genuine email directly from webapp HTML
                if not candidate_email or not is_genuine_business_email(candidate_email):
                    site_emails = [
                        clean_email(em) for em in audit.get("emails", [])
                        if is_genuine_business_email(em, url)
                    ]
                    if site_emails:
                        candidate_email = site_emails[0]

                candidate_email = clean_email(candidate_email)
                if not candidate_email or not is_genuine_business_email(candidate_email):
                    continue

                if candidate_email in seen_emails:
                    continue

                seen_emails.add(candidate_email)
                issues = audit.get("issues", [])
                pitch = generate_issue_pitch_angle(b["name"], b["category"], url, issues)

                lead = {
                    "email": candidate_email,
                    "lead_info": {
                        "name": b["name"],
                        "company": b["name"],
                        "Business Name": b["name"],
                        "Contact Person": "Business Owner",
                        "Email (Gmail)": candidate_email,
                        "Phone": b["phone"] if b["phone"] != "UK" else (audit.get("phones", ["UK"])[0] if audit.get("phones") else "+44 (Local UK)"),
                        "Category": b["category"],
                        "sector": b["category"],
                        "City / Address": b["location"],
                        "location": b["location"],
                        "Website": url,
                        "website": url,
                        "Website Status": "Has Website (Flaws Detected)" if issues else "Has Website",
                        "Website Issues": issues,
                        "Lead Source": "Live UK Webapp Discovery & Audit",
                        "Lead URL": url,
                        "Freelance Pitch Angle": pitch,
                        "market": "UK",
                        "country": "United Kingdom"
                    }
                }
                qualified_leads.append(lead)
                if on_status:
                    on_status(f"[UK QUALIFIED] Verified {b['name']} ({candidate_email}) in {b['location']}")
            except Exception:
                pass

        state["seen_websites"] = list(seen_sites)[-10000:]
        state["seen_emails"] = list(seen_emails)[-10000:]
        _save_state(state)
        return qualified_leads

    return []
