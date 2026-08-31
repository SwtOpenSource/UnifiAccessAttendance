"""
考勤排行榜的核心邏輯：把 UniFi Access 門禁 log 整理成「每人每天最早/最晚打卡」，
再跟核准的請假記錄比對算出狀態，最後彙整成排行榜。

跟請假比對的優先順序抄 HR 系統 `_build_attendance_ledger`（hr-system/backend/app/main.py:1233-1315）
的作法：**先查當天有沒有核准的假單，有就直接判定為請假、完全不看有沒有打卡**——
不然請假的人當天當然不會刷卡，會被誤判成缺勤，排行榜就失真了。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable


@dataclass
class DayRecord:
    date: str
    first_punch: str | None = None   # "HH:MM"
    last_punch: str | None = None
    status: str = "無紀錄"            # 正常 | 遲到 | 早退 | 遲到 早退 | 請假 | 無紀錄


@dataclass
class EmployeeLedger:
    employee_id: str
    display_name: str
    department: str
    days: dict[str, DayRecord] = field(default_factory=dict)


def _daterange(start: str, end: str) -> Iterable[str]:
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    cur = d0
    while cur <= d1:
        yield cur.isoformat()
        cur += timedelta(days=1)


def _ts_to_hms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M")


def _ts_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def _check_status(day_date: str, first_hm: str | None, last_hm: str | None,
                   duty_start: str, duty_end: str) -> str:
    if not duty_start and not duty_end:
        return "正常"

    now = datetime.now()
    parts: list[str] = []

    if duty_start:
        check_start = datetime.fromisoformat(f"{day_date}T{duty_start}")
        actual_start = datetime.fromisoformat(f"{day_date}T{first_hm}") if first_hm else None
        if actual_start is None or actual_start > check_start:
            parts.append("遲到")

    if duty_end:
        check_end = datetime.fromisoformat(f"{day_date}T{duty_end}")
        if now > check_end:
            actual_end = datetime.fromisoformat(f"{day_date}T{last_hm}") if last_hm else None
            if actual_end is None or actual_end < check_end:
                parts.append("早退")

    return " ".join(parts) if parts else "正常"


def build_ledger(
    employees: list[dict],           # [{id, display_name, department, unifi_user_id}]
    logs: list[dict],                # raw UniFi Access door_openings hits
    leave_days: set[tuple[str, str]],  # {(employee_id, "YYYY-MM-DD")} — 已核准的請假日
    start_date: str,
    end_date: str,
    duty_start: str,
    duty_end: str,
) -> dict[str, EmployeeLedger]:
    by_unifi_id = {e["unifi_user_id"]: e for e in employees if e.get("unifi_user_id")}

    ledgers: dict[str, EmployeeLedger] = {
        e["id"]: EmployeeLedger(employee_id=e["id"], display_name=e["display_name"], department=e.get("department", ""))
        for e in employees
    }
    for ledger in ledgers.values():
        for d in _daterange(start_date, end_date):
            ledger.days[d] = DayRecord(date=d)

    # 整理打卡：每人每天最早/最晚一筆
    for hit in logs:
        src = hit.get("_source", {})
        actor_id = (src.get("actor") or {}).get("id", "")
        emp = by_unifi_id.get(actor_id)
        if not emp:
            continue
        ledger = ledgers.get(emp["id"])
        if not ledger:
            continue

        ts_ms = src.get("@timestamp")
        if ts_ms is None:
            continue
        day = _ts_to_date(ts_ms)
        rec = ledger.days.get(day)
        if rec is None:
            continue
        hm = _ts_to_hms(ts_ms)

        target = next((t for t in src.get("target", []) if t.get("type") == "device_config"), None)
        direction = target.get("display_name") if target else None

        if rec.first_punch is None or hm < rec.first_punch:
            rec.first_punch = hm
        if rec.last_punch is None or hm > rec.last_punch:
            rec.last_punch = hm
        # entry/exit 沒有明確方向資訊時，仍靠「最早/最晚」推算上下班——單一主要出入口場景下這樣就夠準

    # 套用請假 + 算狀態
    for ledger in ledgers.values():
        for d, rec in ledger.days.items():
            if (ledger.employee_id, d) in leave_days:
                rec.status = "請假"
            elif rec.first_punch is None:
                rec.status = "無紀錄"
            else:
                rec.status = _check_status(d, rec.first_punch, rec.last_punch, duty_start, duty_end)

    return ledgers


@dataclass
class LeaderboardRow:
    employee_id: str
    display_name: str
    department: str
    total_days: int          # 排除請假天數後，理論應到天數
    normal_days: int
    on_time_rate: float      # normal_days / total_days，避免除0
    streak: int               # 從最後一天往回算，連續「正常」天數


def build_leaderboard(ledgers: dict[str, EmployeeLedger]) -> list[LeaderboardRow]:
    rows: list[LeaderboardRow] = []
    for ledger in ledgers.values():
        sorted_days = sorted(ledger.days.items())
        countable = [rec for _, rec in sorted_days if rec.status != "請假"]
        normal = [rec for rec in countable if rec.status == "正常"]

        streak = 0
        for _, rec in reversed(sorted_days):
            if rec.status == "請假":
                continue
            if rec.status == "正常":
                streak += 1
            else:
                break

        total = len(countable)
        rows.append(LeaderboardRow(
            employee_id=ledger.employee_id,
            display_name=ledger.display_name,
            department=ledger.department,
            total_days=total,
            normal_days=len(normal),
            on_time_rate=round((len(normal) / total * 100), 1) if total else 0.0,
            streak=streak,
        ))

    rows.sort(key=lambda r: (-r.on_time_rate, -r.streak, r.display_name))
    return rows
