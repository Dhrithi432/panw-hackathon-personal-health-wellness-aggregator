from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://dhrithigulannavar:postgresql@localhost:5432/healthdata",
)

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
