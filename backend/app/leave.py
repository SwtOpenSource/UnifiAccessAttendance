"""
簡易請假：單一層級（員工送出 → 管理員核准/駁回），不做 HR 系統那套
manager→owner 兩階段審批——這個系統沒有主管層級的概念，只有「員工」跟「管理員」兩種角色。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import LeaveRequest


def leave_days_between(start_date: str, end_date: str) -> set[str]:
    from datetime import date, timedelta
    d0, d1 = date.fromisoformat(start_date), date.fromisoformat(end_date)
    out = set()
    cur = d0
    while cur <= d1:
        out.add(cur.isoformat())
        cur += timedelta(days=1)
    return out


def approved_leave_days(db: Session, start_date: str, end_date: str) -> set[tuple[str, str]]:
    """回傳 {(employee_id, date)} 涵蓋查詢區間、且已核准的請假日集合，供 attendance.build_ledger 用。"""
    rows = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.status == "approved")
        .filter(LeaveRequest.start_date <= end_date)
        .filter(LeaveRequest.end_date >= start_date)
        .all()
    )
    out: set[tuple[str, str]] = set()
    for r in rows:
        for d in leave_days_between(max(r.start_date, start_date), min(r.end_date, end_date)):
            out.add((r.employee_id, d))
    return out


def decide(db: Session, leave: LeaveRequest, approve: bool, note: str) -> LeaveRequest:
    leave.status = "approved" if approve else "rejected"
    leave.reviewer_note = note
    leave.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(leave)
    return leave
