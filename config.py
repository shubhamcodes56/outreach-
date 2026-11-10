import os
from dotenv import load_dotenv

load_dotenv()

# Groq AI Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_RAW_KEYS = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]
GROQ_SEARCH_RAW_KEYS = [k.strip() for k in os.getenv("GROQ_SEARCH_API_KEYS", "").split(",") if k.strip()]
GROQ_API_KEYS = list(dict.fromkeys(
    GROQ_RAW_KEYS + GROQ_SEARCH_RAW_KEYS + ([GROQ_API_KEY] if GROQ_API_KEY else [])
))
GROQ_SEARCH_API_KEYS = list(dict.fromkeys(
    GROQ_SEARCH_RAW_KEYS + GROQ_RAW_KEYS + ([GROQ_API_KEY] if GROQ_API_KEY else [])
))
GROQ_SEARCH_MODEL = os.getenv("GROQ_SEARCH_MODEL", "openai/gpt-oss-20b").strip()
GROQ_SEARCH_DAILY_QUERY_LIMIT = max(2000, int(os.getenv("GROQ_SEARCH_DAILY_QUERY_LIMIT", "2000")))

OMNIROUTE_BASE_URL = os.getenv("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1").rstrip("/")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")
OMNIROUTE_MODEL = os.getenv("OMNIROUTE_MODEL", "auto/fast")

BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
BRAVE_SEARCH_DAILY_QUERY_LIMIT = int(os.getenv("BRAVE_SEARCH_DAILY_QUERY_LIMIT", "0"))

KIMI_API_KEY = os.getenv("KIMI_API_KEY", "").strip()
KIMI_API_BASE_URL = os.getenv("KIMI_API_BASE_URL", "https://api.moonshot.ai/v1").rstrip("/")
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-k2.6").strip()
KIMI_SEARCH_DAILY_QUERY_LIMIT = max(0, int(os.getenv("KIMI_SEARCH_DAILY_QUERY_LIMIT", "0")))

AI_MODEL = "Groq Multi-Model Engine (Fast Fallback)"

# Gmail SMTP & IMAP Settings
GMAIL_USER = os.getenv("GMAIL_USER", "dixitshubham68359@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

# Business Outreach Rules - United Kingdom
SENDER_NAME = os.getenv("YOUR_NAME", "Shubham Dixit")
BASE_PRICE = os.getenv("STARTING_PRICE", "£129")
PORTFOLIO_URL = os.getenv("PORTFOLIO_URL", "https://portfolio-public-theta-three.vercel.app/").strip()
MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", "1"))
MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", "3"))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "200"))
PORT = int(os.getenv("PORT", "5070"))

# Database & State files for UK Engine
DB_FILE = "pipeline_uk_db.json"
STATE_FILE = "web_discovery_uk_state.json"
ACCOUNTS_FILE = "accounts_db.json"

