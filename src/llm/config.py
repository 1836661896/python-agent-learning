import os

from dotenv import load_dotenv

load_dotenv()

base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
model = os.getenv("OLLAMA_MODEL", "qwen:7b")
timeout = 120
