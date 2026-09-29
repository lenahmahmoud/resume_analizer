import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to the .env file.")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing. Add it to the .env file.")

# Model names are configurable because Google retires models over time.
CHAT_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_CHAT_MODELS", "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.6-flash").split(",")
    if m.strip()
]
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIMENSIONS = 768

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
UPLOAD_DIR = BASE_DIR / "uploads"
MAX_UPLOAD_MB = 5