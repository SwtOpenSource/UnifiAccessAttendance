# 🏆 打卡英雄榜 · UnifiAccessAttendance

把 UniFi Access 門禁 log 變成好玩的打卡排行榜，順手補上簡易請假——沒有請假資料，「無紀錄」
會誤判成缺勤，排行榜就失真了，所以請假是排行榜站得住腳的前提，不是附加功能。

## 快速開始

### Windows：免裝 Docker，下載單一執行檔就能跑

到 [Releases](https://github.com/SwtOpenSource/UnifiAccessAttendance/releases) 下載
`UnifiAccessAttendance.exe`（x64），雙擊執行——不用裝 Docker、Node 或 Python，
會自動開瀏覽器連到 `http://127.0.0.1:8888`。資料庫存在
`%APPDATA%\UnifiAccessAttendance\data`，關掉程式資料還在，下次開啟延續使用。

這支 exe 由 GitHub Actions 在 `windows-latest` 上自動建置（`.github/workflows/build-windows.yml`），
推新版標籤（`vX.Y.Z`）會自動編一份新的附到 Release。

### Docker（Mac / Linux / Windows 都適用）

先裝 [Docker Desktop](https://www.docker.com/products/docker-desktop)（Mac/Windows）或
[Docker Engine](https://docs.docker.com/engine/install/)（Linux）。

```shell
git clone https://github.com/SwtOpenSource/UnifiAccessAttendance.git
cd UnifiAccessAttendance
docker compose up
```

打開瀏覽器輸入 [localhost:4000](http://localhost:4000)。

## 第一次使用

1. **設定 UniFi Access 主機**：選擇主機類型（UCKP 或 UNVR/UDM，兩者 API 路徑不同，
   系統會自動組出正確的連線方式），填入主機 IP 與 API Token/Key。
   API Token 於 UniFi Access 主控台「Settings → General → Advanced → API Token」建立。
2. **管理員登入**：用 UniFi Access 帳號登入（需要 FullManagement 權限）。
3. 到「管理設定」建立員工本地帳號、綁定對應的 UniFi Access 使用者、設定上下班時間。
4. 員工用管理員建立的帳號登入即可看排行榜、送請假申請。
5. 想拿排行榜打廣告的話，「管理設定」開啟免登入公開連結，可以直接分享截圖。

## 支援的 UniFi 主機類型

| | UCKP（Cloud Key Gen2 Plus） | UNVR / UDM（Dream Machine 系列） |
|---|---|---|
| Base URL | `https://<ip>`（443） | `https://<ip>:12445` |
| 路徑前綴 | `/proxy/access/integration/v1/developer` | `/api/v1/developer` |
| 認證 | `X-API-KEY` header | `Authorization: Bearer` |

系統設定頁選好類型、填 IP 跟憑證即可，不用自己拼路徑。

## 技術棧

- 前端：Vue 3 + TypeScript + Vite
- 後端：FastAPI + SQLAlchemy + SQLite（單一 volume，`docker compose up` 就能用，不用另外架資料庫）
- Windows 桌面版：`backend/desktop_app.py` 用 PyInstaller 打包成單一 .exe，
  同一個 process 用 `main.py` 檔尾的 `UAA_STATIC_DIR` 機制直接把前端 build 出來的
  靜態檔案端出去（不用另外跑 nginx），docker-compose 部署完全不受影響。

## 開發

```shell
# 後端
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest app/tests -q

# 前端
cd frontend
npm install
npm run dev       # http://localhost:4000（vite dev server）
npm run typecheck
```

## Notes

* UniFi Access 版本需 v1.9.1 或更高
* 管理員登入需要 UniFi Access FullManagement 權限
