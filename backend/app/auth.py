"""
兩條認證路徑，刻意分開：

- 管理員：不落地帳密，即時打 UniFi OS 的 SSO endpoint（POST {base_url}/api/auth/login）驗證，
  這個端點是 UniFi OS 這層的，不管底層裝置是 UCKP 還是 UNVR/UDM 都一樣有——跟 unifi_client.py
  裡「抓資料」用的憑證（API Key / Token）是完全不同的關注點，管理員驗證通過不代表我們儲存了
  他的密碼、也不代表資料 API 憑證有設定。
- 員工：本地帳號，跟 UniFi Access 帳號無關，只用來送請假/看自己的紀錄。
"""
from __future__ import annotations

import ssl
import json as _json
from datetime import datetime, timedelta, timezone
from urllib import error as urlerr
from urllib import request as urlreq

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import AdminSession, Employee

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def verify_unifi_admin(base_url: str, username: str, password: str) -> bool:
    """打 UniFi OS SSO 驗證帳密，成功回 True。不儲存密碼。"""
    url = base_url.rstrip("/") + "/api/auth/login"
    body = _json.dumps({"username": username, "password": password, "token": "", "rememberMe": False}).encode()
    req = urlreq.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlreq.urlopen(req, timeout=10, context=_INSECURE_CTX) as resp:
            return resp.status == 200
    except urlerr.HTTPError:
        return False
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"無法連線 UniFi 主機驗證帳密：{exc}") from exc


def make_token(sub: str, role: str, display_name: str) -> str:
    payload = {
        "sub": sub,
        "role": role,
        "display_name": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="登入已過期或無效，請重新登入") from exc


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少登入憑證")
    return auth.split(" ", 1)[1]


def current_claims(request: Request) -> dict:
    return _decode(_bearer(request))


def require_admin(claims: dict = Depends(current_claims)) -> dict:
    if claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="僅限管理員")
    return claims


def require_employee(claims: dict = Depends(current_claims)) -> dict:
    if claims.get("role") not in ("admin", "employee"):
        raise HTTPException(status_code=403, detail="請先登入")
    return claims


def current_employee(claims: dict = Depends(require_employee), db: Session = Depends(get_db)) -> Employee:
    if claims.get("role") != "employee":
        raise HTTPException(status_code=403, detail="僅限員工帳號")
    emp = db.query(Employee).filter(Employee.id == claims["sub"]).first()
    if not emp or not emp.is_active:
        raise HTTPException(status_code=401, detail="帳號不存在或已停用")
    return emp


def _bytes72(raw: str) -> bytes:
    # bcrypt 本身限制密碼最多 72 bytes，比照官方建議直接截斷而不是讓 hash 拋例外
    return raw.encode("utf-8")[:72]


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_bytes72(raw), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(_bytes72(raw), hashed.encode("utf-8"))


def record_admin_seen(db: Session, username: str) -> None:
    row = db.query(AdminSession).filter(AdminSession.username == username).first()
    if row:
        row.last_login_at = datetime.now(timezone.utc)
    else:
        db.add(AdminSession(username=username))
    db.commit()
