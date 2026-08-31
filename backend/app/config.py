import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("UAA_DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'uaa.db'}"

# JWT for local (employee/admin) sessions
SECRET_KEY = os.environ.get("UAA_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7

# UniFi Access dev-token scopes used when we mint our own token during
# the UNVR/UDM bootstrap flow (see unifi_client.UnvrClient.login).
TOKEN_SCOPES = [
    "edit:user", "edit:space", "edit:visitor",
    "edit:credential", "view:system_log", "edit:policy", "edit:device",
]
TOKEN_VALIDITY_PERIOD = 0  # 永久

LOG_TOPIC = "door_openings"

# late/early-leave 判斷（沒有設定 duty 時間就一律 normal）
DEFAULT_LATE_GRACE_MINUTES = 0
