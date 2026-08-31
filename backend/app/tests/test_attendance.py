from app.attendance import build_ledger, build_leaderboard

EMPLOYEES = [
    {"id": "e1", "display_name": "Alice", "department": "Eng", "unifi_user_id": "u1"},
    {"id": "e2", "display_name": "Bob", "department": "Eng", "unifi_user_id": "u2"},
]


def _hit(actor_id: str, ts_iso: str, direction: str = "entry") -> dict:
    from datetime import datetime
    ts_ms = int(datetime.fromisoformat(ts_iso).timestamp() * 1000)
    return {
        "_source": {
            "actor": {"id": actor_id},
            "target": [{"type": "device_config", "display_name": direction}],
            "@timestamp": ts_ms,
        }
    }


def test_on_leave_short_circuits_even_with_no_punches():
    leave_days = {("e1", "2026-08-31")}
    ledgers = build_ledger(EMPLOYEES, logs=[], leave_days=leave_days,
                            start_date="2026-08-31", end_date="2026-08-31",
                            duty_start="09:00", duty_end="18:00")
    assert ledgers["e1"].days["2026-08-31"].status == "請假"
    # 沒請假、沒打卡 → 無紀錄，不是自動變請假
    assert ledgers["e2"].days["2026-08-31"].status == "無紀錄"


def test_on_time_punch_is_normal():
    logs = [_hit("u1", "2026-08-31T08:55:00"), _hit("u1", "2026-08-31T18:05:00")]
    ledgers = build_ledger(EMPLOYEES, logs, leave_days=set(),
                            start_date="2026-08-31", end_date="2026-08-31",
                            duty_start="09:00", duty_end="18:00")
    rec = ledgers["e1"].days["2026-08-31"]
    assert rec.first_punch == "08:55"
    assert rec.status == "正常"


def test_late_punch():
    # 兩筆打卡（進+出）才能單獨驗證「只遲到、沒早退」——只有一筆打卡的話，
    # 只要現在時間已經過了下班時間，_check_status 會因為「看不到出門紀錄」
    # 一併標早退（這是刻意的行為，見 test_single_punch_after_duty_end_also_flags_early_leave）。
    logs = [_hit("u1", "2026-08-31T09:15:00"), _hit("u1", "2026-08-31T18:10:00")]
    ledgers = build_ledger(EMPLOYEES, logs, leave_days=set(),
                            start_date="2026-08-31", end_date="2026-08-31",
                            duty_start="09:00", duty_end="18:00")
    assert ledgers["e1"].days["2026-08-31"].status == "遲到"


def test_single_punch_after_duty_end_also_flags_early_leave():
    # 只有一筆打卡、且已經過了下班時間 → 看不出有沒有離開，跟舊版邏輯一樣保守標早退
    logs = [_hit("u1", "2026-08-31T09:15:00")]
    ledgers = build_ledger(EMPLOYEES, logs, leave_days=set(),
                            start_date="2026-08-31", end_date="2026-08-31",
                            duty_start="09:00", duty_end="18:00")
    assert ledgers["e1"].days["2026-08-31"].status == "遲到 早退"


def test_leave_excluded_from_leaderboard_denominator():
    # e1: 一天請假、一天正常。e2: 兩天都無紀錄。
    leave_days = {("e1", "2026-08-31")}
    logs = [_hit("u1", "2026-09-01T08:55:00")]
    ledgers = build_ledger(EMPLOYEES, logs, leave_days=leave_days,
                            start_date="2026-08-31", end_date="2026-09-01",
                            duty_start="09:00", duty_end="18:00")
    board = {row.employee_id: row for row in build_leaderboard(ledgers)}

    # e1 只有 1 個「應計」天（請假天不算），且那天正常 → 100%
    assert board["e1"].total_days == 1
    assert board["e1"].on_time_rate == 100.0
    # e2 兩天都無紀錄，應計天數 2，正常 0 天 → 0%
    assert board["e2"].total_days == 2
    assert board["e2"].on_time_rate == 0.0


def test_streak_skips_leave_days_without_breaking():
    # 8/29 正常、8/30 請假、8/31 正常 → streak 應該是 2（請假天跳過不算中斷）
    leave_days = {("e1", "2026-08-30")}
    logs = [
        _hit("u1", "2026-08-29T08:55:00"), _hit("u1", "2026-08-29T18:05:00"),
        _hit("u1", "2026-08-31T08:55:00"), _hit("u1", "2026-08-31T18:05:00"),
    ]
    ledgers = build_ledger(EMPLOYEES, logs, leave_days=leave_days,
                            start_date="2026-08-29", end_date="2026-08-31",
                            duty_start="09:00", duty_end="18:00")
    board = {row.employee_id: row for row in build_leaderboard(ledgers)}
    assert board["e1"].streak == 2


def test_no_duty_time_configured_is_always_normal():
    logs = [_hit("u1", "2026-08-31T23:00:00")]
    ledgers = build_ledger(EMPLOYEES, logs, leave_days=set(),
                            start_date="2026-08-31", end_date="2026-08-31",
                            duty_start="", duty_end="")
    assert ledgers["e1"].days["2026-08-31"].status == "正常"
