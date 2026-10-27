from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_SOURCE = os.getenv("POLAR_DATA_SOURCE", "demo").lower()
DEMO_SESSION_PATH = os.getenv("POLAR_DEMO_SESSION_PATH", str(ROOT / "data" / "demo_polar_session.json"))
ACCESSLINK_EXERCISES_URL = "https://www.polaraccesslink.com/v3/exercises"

