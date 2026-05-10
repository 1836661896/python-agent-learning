"""集中放DATABASE+URL"""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres@127.0.0.1:5432/agent_db",
)
