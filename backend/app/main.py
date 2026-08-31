from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from . import auth, leave as leave_mod, schemas
from .attendance import build_ledger, build_leaderboard
from .db import get_db, init_db
from .models import DutyTime, Employee, HostConfig, LeaveRequest, PublicBoardSetting
from .unifi_client import build_client, normalize_base_url

app = FastAPI(title="UnifiAccessAttendance")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ── 主機設定 ──────────────────────────────────────────────────────────
def _get_host_config(db: Session) -> HostConfig | None:
    return db.query(HostConfig).first()


def _require_host_config(db: Session) -> HostConfig:
    cfg = _get_host_config(db)
    if not cfg:
        raise HTTPException(status_code=400, detail="尚未設定 UniFi Access 主機，請先在設定頁完成設定")
    return cfg


@app.get("/host")
def get_host(db: Session = Depends(get_db)) -> schemas.HostConfigOut:
    cfg = _get_host_config(db)
    if not cfg:
        return schemas.HostConfigOut(host_type="", base_url="", configured=False)
    return schemas.HostConfigOut(host_type=cfg.host_type, base_url=cfg.base_url, configured=True)


@app.post("/host")
def set_host(body: schemas.HostConfigIn, db: Session = Depends(get_db)) -> dict:
    if body.host_type not in ("uckp", "unvr"):
        raise HTTPException(status_code=400, detail="host_type 必須是 uckp 或 unvr")

    base_url = normalize_base_url(body.base_url)
    client = build_client(body.host_type, base_url, body.credential)
    try:
        client.test_connection()
    except HTTPException as exc:
        raise HTTPException(status_code=400, detail=f"連線測試失敗，請確認主機類型/IP/憑證：{exc.detail}") from exc

    cfg = _get_host_config(db)
    if not cfg:
        cfg = HostConfig(host_type=body.host_type, base_url=base_url, credential=body.credential)
        db.add(cfg)
    else:
        cfg.host_type = body.host_type
        cfg.base_url = base_url
        cfg.credential = body.credential
    db.commit()
    return {"detail": "設定成功"}


# ── 登入 ──────────────────────────────────────────────────────────────
@app.post("/auth/admin/login")
def admin_login(body: schemas.AdminLoginBody, db: Session = Depends(get_db)) -> schemas.TokenOut:
    cfg = _require_host_config(db)
    if not auth.verify_unifi_admin(cfg.base_url, body.username, body.password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    auth.record_admin_seen(db, body.username)
    token = auth.make_token(sub=body.username, role="admin", display_name=body.username)
    return schemas.TokenOut(token=token, role="admin", display_name=body.username)


@app.post("/auth/employee/login")
def employee_login(body: schemas.EmployeeLoginBody, db: Session = Depends(get_db)) -> schemas.TokenOut:
    emp = db.query(Employee).filter(Employee.username == body.username, Employee.is_active.is_(True)).first()
    if not emp or not auth.verify_password(body.password, emp.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    token = auth.make_token(sub=emp.id, role="employee", display_name=emp.display_name)
    return schemas.TokenOut(token=token, role="employee", display_name=emp.display_name)


# ── 上下班時間 ────────────────────────────────────────────────────────
@app.get("/duty")
def get_duty(db: Session = Depends(get_db)) -> schemas.DutySet:
    row = db.query(DutyTime).first()
    if not row:
        return schemas.DutySet(start_work="", get_off="")
    return schemas.DutySet(start_work=row.start_work, get_off=row.get_off)


@app.post("/duty")
def set_duty(body: schemas.DutySet, _: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> dict:
    row = db.query(DutyTime).first()
    if not row:
        row = DutyTime(start_work=body.start_work, get_off=body.get_off)
        db.add(row)
    else:
        row.start_work = body.start_work
        row.get_off = body.get_off
    db.commit()
    return {"detail": "設定成功"}


# ── 員工帳號（管理員維護） ────────────────────────────────────────────
@app.get("/employees")
def list_employees(_: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> list[schemas.EmployeeOut]:
    return db.query(Employee).order_by(Employee.created_at).all()


@app.post("/employees")
def create_employee(body: schemas.EmployeeCreate, _: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> schemas.EmployeeOut:
    if db.query(Employee).filter(Employee.username == body.username).first():
        raise HTTPException(status_code=400, detail="帳號已存在")
    emp = Employee(
        username=body.username,
        password_hash=auth.hash_password(body.password),
        display_name=body.display_name,
        unifi_user_id=body.unifi_user_id,
        department=body.department,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@app.post("/employees/{employee_id}/bind-unifi")
def bind_unifi(employee_id: str, body: schemas.EmployeeUnifiBind, _: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> schemas.EmployeeOut:
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="找不到員工")
    if body.unifi_user_id:
        prev = db.query(Employee).filter(Employee.unifi_user_id == body.unifi_user_id, Employee.id != employee_id).first()
        if prev:
            prev.unifi_user_id = ""
    emp.unifi_user_id = body.unifi_user_id
    db.commit()
    db.refresh(emp)
    return emp


@app.get("/unifi/users")
def unifi_users(_: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> list[dict]:
    """代理列出 UniFi Access 門禁使用者，供員工資料綁定參考（不落地）。"""
    cfg = _require_host_config(db)
    client = build_client(cfg.host_type, cfg.base_url, cfg.credential)
    return client.get_users()


# ── 請假 ──────────────────────────────────────────────────────────────
@app.post("/leaves")
def submit_leave(body: schemas.LeaveCreate, emp: Employee = Depends(auth.current_employee), db: Session = Depends(get_db)) -> schemas.LeaveOut:
    if body.end_date < body.start_date:
        raise HTTPException(status_code=400, detail="結束日期不可早於起始日期")
    row = LeaveRequest(
        employee_id=emp.id, leave_type=body.leave_type,
        start_date=body.start_date, end_date=body.end_date, reason=body.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _leave_out(row, emp.display_name)


@app.get("/leaves/mine")
def my_leaves(emp: Employee = Depends(auth.current_employee), db: Session = Depends(get_db)) -> list[schemas.LeaveOut]:
    rows = db.query(LeaveRequest).filter(LeaveRequest.employee_id == emp.id).order_by(LeaveRequest.created_at.desc()).all()
    return [_leave_out(r, emp.display_name) for r in rows]


@app.get("/leaves")
def list_leaves(status: str | None = None, _: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> list[schemas.LeaveOut]:
    q = db.query(LeaveRequest)
    if status:
        q = q.filter(LeaveRequest.status == status)
    rows = q.order_by(LeaveRequest.created_at.desc()).all()
    names = {e.id: e.display_name for e in db.query(Employee).all()}
    return [_leave_out(r, names.get(r.employee_id, "")) for r in rows]


@app.post("/leaves/{leave_id}/decision")
def decide_leave(leave_id: str, body: schemas.LeaveDecision, _: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> schemas.LeaveOut:
    row = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="找不到請假申請")
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="這筆申請已經處理過了")
    leave_mod.decide(db, row, body.approve, body.note)
    emp = db.query(Employee).filter(Employee.id == row.employee_id).first()
    return _leave_out(row, emp.display_name if emp else "")


def _leave_out(row: LeaveRequest, employee_name: str) -> schemas.LeaveOut:
    return schemas.LeaveOut(
        id=row.id, employee_id=row.employee_id, employee_name=employee_name,
        leave_type=row.leave_type, start_date=row.start_date, end_date=row.end_date,
        reason=row.reason, status=row.status, reviewer_note=row.reviewer_note,
        created_at=row.created_at, reviewed_at=row.reviewed_at,
    )


# ── 考勤排行榜 ────────────────────────────────────────────────────────
def _employees_dicts(db: Session) -> list[dict]:
    return [
        {"id": e.id, "display_name": e.display_name, "department": e.department, "unifi_user_id": e.unifi_user_id}
        for e in db.query(Employee).filter(Employee.is_active.is_(True)).all()
    ]


def _fetch_ledger(db: Session, start_date: str, end_date: str):
    cfg = _require_host_config(db)
    client = build_client(cfg.host_type, cfg.base_url, cfg.credential)

    import time as _time
    since = int(_time.mktime(_time.strptime(start_date, "%Y-%m-%d")))
    until = int(_time.mktime(_time.strptime(end_date, "%Y-%m-%d"))) + 86399
    logs = client.get_logs(since=since, until=until)

    duty = db.query(DutyTime).first()
    duty_start = duty.start_work if duty else ""
    duty_end = duty.get_off if duty else ""

    leave_days = leave_mod.approved_leave_days(db, start_date, end_date)
    employees = _employees_dicts(db)
    return build_ledger(employees, logs, leave_days, start_date, end_date, duty_start, duty_end)


@app.get("/attendance/ledger")
def attendance_ledger(start_date: str, end_date: str, _: dict = Depends(auth.require_employee), db: Session = Depends(get_db)) -> dict:
    ledgers = _fetch_ledger(db, start_date, end_date)
    return {
        eid: {
            "employee_id": l.employee_id, "display_name": l.display_name, "department": l.department,
            "days": {d: vars(rec) for d, rec in l.days.items()},
        }
        for eid, l in ledgers.items()
    }


@app.get("/attendance/leaderboard")
def attendance_leaderboard(start_date: str, end_date: str, _: dict = Depends(auth.require_employee), db: Session = Depends(get_db)) -> list[dict]:
    ledgers = _fetch_ledger(db, start_date, end_date)
    return [vars(row) for row in build_leaderboard(ledgers)]


# ── 公開唯讀排行榜 ────────────────────────────────────────────────────
@app.get("/public-board/setting")
def get_public_board_setting(_: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> dict:
    row = db.query(PublicBoardSetting).first()
    if not row:
        row = PublicBoardSetting(enabled=False)
        db.add(row)
        db.commit()
        db.refresh(row)
    return {"enabled": row.enabled, "slug": row.slug}


@app.post("/public-board/setting")
def set_public_board_setting(body: schemas.PublicBoardToggle, _: dict = Depends(auth.require_admin), db: Session = Depends(get_db)) -> dict:
    row = db.query(PublicBoardSetting).first()
    if not row:
        row = PublicBoardSetting(enabled=body.enabled)
        db.add(row)
    else:
        row.enabled = body.enabled
    db.commit()
    db.refresh(row)
    return {"enabled": row.enabled, "slug": row.slug}


@app.get("/public-board/{slug}")
def public_board(slug: str, start_date: str, end_date: str, db: Session = Depends(get_db)) -> list[dict]:
    """免登入唯讀排行榜——只回排名/統計，不含請假明細或任何個資以外的內容。"""
    row = db.query(PublicBoardSetting).filter(PublicBoardSetting.slug == slug).first()
    if not row or not row.enabled:
        raise HTTPException(status_code=404, detail="Not found")
    ledgers = _fetch_ledger(db, start_date, end_date)
    return [
        {"display_name": r.display_name, "department": r.department, "on_time_rate": r.on_time_rate, "streak": r.streak}
        for r in build_leaderboard(ledgers)
    ]


# ── 桌面單一執行檔模式：同一個 process 順便把前端靜態檔案端出去 ──────────
# 一般 docker-compose 部署是前後端兩個容器（nginx 端前端），這段只在
# UAA_STATIC_DIR 有設定時才啟用（桌面版 desktop_app.py 會設），docker 部署
# 完全不會碰到這段路由。放在檔案最後，確保不會搶在任何 API 路由前面比對到。
_static_dir = os.environ.get("UAA_STATIC_DIR")
if _static_dir and Path(_static_dir).is_dir():
    _static_path = Path(_static_dir)
    app.mount("/assets", StaticFiles(directory=_static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def _spa_fallback(full_path: str) -> FileResponse:
        candidate = _static_path / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static_path / "index.html")
