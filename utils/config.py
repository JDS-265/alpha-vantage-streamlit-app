from pathlib import Path
import os

from dotenv import load_dotenv


APP_NAME = "Alpha Vantage Financial Dashboard"
APP_VERSION = "V7 - Complete Module"

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "Data"
CACHE_DIR = DATA_DIR / "cache"
EXPORTS_DIR = DATA_DIR / "exports"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

BASE_URL = "https://www.alphavantage.co/query"

DEFAULT_OUTPUTSIZE = "compact"
API_SLEEP_SECONDS = 15