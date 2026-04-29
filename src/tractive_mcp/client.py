import json
import math
import os
from contextlib import asynccontextmanager
from pathlib import Path

from aiotractive import Tractive

CONFIG_DIR = Path.home() / ".config" / "tractive-mcp"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"

EARTH_RADIUS_M = 6_371_000


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the distance in metres between two lat/lon points."""
    lat1, lon1, lat2, lon2 = (math.radians(v) for v in (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_M * 2 * math.asin(math.sqrt(a))


def load_credentials() -> tuple[str, str]:
    """Load credentials from env vars first, then fall back to credentials file."""
    email = os.environ.get("TRACTIVE_EMAIL")
    password = os.environ.get("TRACTIVE_PASSWORD")

    if email and password:
        return email, password

    if CREDENTIALS_FILE.exists():
        data = json.loads(CREDENTIALS_FILE.read_text())
        email = data.get("email")
        password = data.get("password")
        if email and password:
            return email, password

    raise RuntimeError(
        "Tractive credentials not found. "
        "Run `tractive-mcp auth` to set them up, "
        "or set TRACTIVE_EMAIL and TRACTIVE_PASSWORD environment variables."
    )


def save_credentials(email: str, password: str) -> None:
    """Save credentials to the config file with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps({"email": email, "password": password}))
    CREDENTIALS_FILE.chmod(0o600)


@asynccontextmanager
async def tractive_client():
    """Async context manager that yields an authenticated Tractive client."""
    email, password = load_credentials()
    async with Tractive(email, password) as client:
        yield client
