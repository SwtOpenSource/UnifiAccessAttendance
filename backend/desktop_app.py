"""
Windows 桌面單機版進入點：PyInstaller 打包成單一 .exe，雙擊即可跑，
不需要另外裝 Docker/Node/Python——資料庫跟前端靜態檔案都跟著這支執行檔走。

跟 docker-compose 部署的差異：
- docker-compose：backend/frontend 兩個容器，前端走 nginx，走 http://localhost:4000。
- 桌面版：單一 process，FastAPI 自己把 frontend/dist 端出去（見 main.py 檔尾的
  UAA_STATIC_DIR 那段），只佔一個 port（8888），啟動後自動開瀏覽器。

資料庫位置：Windows 上放在 %APPDATA%\\UnifiAccessAttendance\\data（一般使用者對
Program Files 底下沒有寫入權限，不能放在執行檔旁邊）；非 Windows 平台（開發時
直接跑這支腳本測試用）退回使用者家目錄下的 .unifi-access-attendance。
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / ".unifi-access-attendance"
    d = base / "UnifiAccessAttendance" / "data" if appdata else base
    d.mkdir(parents=True, exist_ok=True)
    return d


def _bundled_static_dir() -> Path | None:
    # PyInstaller 打包後，用 --add-data 塞進去的資料會放在 sys._MEIPASS 底下
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = base / "frontend_dist"
    return candidate if candidate.is_dir() else None


def main() -> None:
    os.environ.setdefault("UAA_DATA_DIR", str(_data_dir()))
    static_dir = _bundled_static_dir()
    if static_dir:
        os.environ.setdefault("UAA_STATIC_DIR", str(static_dir))
    os.environ.setdefault("UAA_SECRET_KEY", "local-desktop-" + os.environ["UAA_DATA_DIR"])

    import uvicorn
    from app.main import app  # noqa: E402 — 環境變數要先設好，import 才會讀到對的設定

    port = 8888

    def _open_browser() -> None:
        time.sleep(1.2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
