"""
UniFi Access 雙主機連接抽象層。

背景：UniFi Access 的 Developer API（登入拿使用者/門禁 log）在不同硬體上路徑跟認證方式不一樣，
這件事**官方 API 文件沒有寫**（文件只涵蓋 port 12445 那組、且宣稱不分主機都一樣）。以下兩組都是
從已經在正式環境跑穩的整合實測驗證過的：

- UCKP（Cloud Key Gen2 Plus 這類跑 UniFi OS 的一體機）：
    base_url 不帶 port（即 443），路徑前綴 /proxy/access/integration/v1/developer/...，
    header 用 X-API-KEY。跟 SWT HR 系統正式站現行做法一致（hr-system/backend/app/main.py
    的 _unifi_request()）。
- UNVR / UDM（Network Video Recorder、Dream Machine 系列）：
    base_url 帶 port 12445，路徑前綴 /api/v1/developer/...，header 用
    Authorization: Bearer <token>。這是官方 194 頁 API 文件寫的標準格式。

兩種主機的憑證都建議透過 UniFi Access 主控台介面手動建立 API Token/Key
（Access > Settings > General > Advanced > API Token），貼進本系統設定頁即可——
不在後端存放/重放管理員的 UniFi 帳號密碼去打資料 API（管理員登入本系統另外走
UniFi OS 的 SSO，見 auth.py，兩者是分開的關注點）。
"""
from __future__ import annotations

import ssl
from dataclasses import dataclass
from typing import Any
from urllib import error as urlerr
from urllib import request as urlreq
import json as _json

from fastapi import HTTPException

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE  # UniFi 主控台預設是自簽憑證


def normalize_base_url(base_url: str) -> str:
    """跟舊版一樣接受裸 IP（"192.168.1.1"），不強制使用者自己補協定。"""
    base_url = base_url.strip()
    if base_url and "://" not in base_url:
        base_url = f"https://{base_url}"
    return base_url.rstrip("/")


@dataclass
class HostSpec:
    host_type: str  # "uckp" | "unvr"
    base_url: str
    credential: str


class UnifiClient:
    """統一介面，內部依 host_type 組裝正確的 URL 跟 header。業務邏輯只認這一層。"""

    def __init__(self, spec: HostSpec):
        if spec.host_type not in ("uckp", "unvr"):
            raise ValueError(f"unknown host_type: {spec.host_type}")
        self.spec = HostSpec(
            host_type=spec.host_type,
            base_url=normalize_base_url(spec.base_url),
            credential=spec.credential,
        )

    def _root(self) -> str:
        base = self.spec.base_url.rstrip("/")
        if self.spec.host_type == "unvr" and ":12445" not in base:
            base = f"{base}:12445"
        return base

    def _prefix(self) -> str:
        return (
            "/proxy/access/integration/v1/developer"
            if self.spec.host_type == "uckp"
            else "/api/v1/developer"
        )

    def _headers(self) -> dict[str, str]:
        common = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.spec.host_type == "uckp":
            return {**common, "X-API-KEY": self.spec.credential}
        return {**common, "Authorization": f"Bearer {self.spec.credential}"}

    def _request(self, path: str, method: str = "GET", body: dict | None = None) -> Any:
        url = f"{self._root()}{self._prefix()}{path}"
        data = _json.dumps(body).encode() if body is not None else None
        req = urlreq.Request(url, data=data, method=method, headers=self._headers())
        try:
            with urlreq.urlopen(req, timeout=15, context=_INSECURE_CTX) as resp:
                return _json.loads(resp.read())
        except urlerr.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")
            raise HTTPException(status_code=502, detail=f"UniFi Access 回應錯誤（HTTP {exc.code}）：{detail[:300]}") from exc
        except Exception as exc:  # noqa: BLE001 — 對外一律包成 502，細節留 message
            raise HTTPException(status_code=502, detail=f"無法連線 UniFi Access（{self.spec.host_type}）：{exc}") from exc

    def test_connection(self) -> bool:
        self._request("/users")
        return True

    def get_users(self) -> list[dict]:
        result = self._request("/users")
        return result.get("data", [])

    def get_logs(self, since: int, until: int, topic: str = "door_openings") -> list[dict]:
        result = self._request(
            "/system/logs", method="POST",
            body={"topic": topic, "since": since, "until": until},
        )
        return result.get("data", {}).get("hits", [])


def build_client(host_type: str, base_url: str, credential: str) -> UnifiClient:
    return UnifiClient(HostSpec(host_type=host_type, base_url=base_url, credential=credential))
