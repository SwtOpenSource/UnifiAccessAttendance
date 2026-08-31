import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Employee, LeaveRequest
from app import leave as leave_mod


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _employee(db) -> Employee:
    emp = Employee(username="alice", password_hash="x", display_name="Alice")
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


def test_pending_leave_not_in_approved_days(db):
    emp = _employee(db)
    db.add(LeaveRequest(employee_id=emp.id, start_date="2026-08-31", end_date="2026-08-31", status="pending"))
    db.commit()
    days = leave_mod.approved_leave_days(db, "2026-08-31", "2026-08-31")
    assert days == set()


def test_decide_approve_marks_approved_and_appears_in_range(db):
    emp = _employee(db)
    row = LeaveRequest(employee_id=emp.id, start_date="2026-08-30", end_date="2026-09-01", status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)

    leave_mod.decide(db, row, approve=True, note="ok")
    assert row.status == "approved"
    assert row.reviewed_at is not None

    days = leave_mod.approved_leave_days(db, "2026-08-31", "2026-08-31")
    assert (emp.id, "2026-08-31") in days


def test_decide_reject(db):
    emp = _employee(db)
    row = LeaveRequest(employee_id=emp.id, start_date="2026-08-31", end_date="2026-08-31", status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)

    leave_mod.decide(db, row, approve=False, note="人力不足")
    assert row.status == "rejected"
    days = leave_mod.approved_leave_days(db, "2026-08-31", "2026-08-31")
    assert days == set()


def test_approved_leave_days_clips_to_query_range(db):
    emp = _employee(db)
    row = LeaveRequest(employee_id=emp.id, start_date="2026-08-01", end_date="2026-08-31", status="approved")
    db.add(row)
    db.commit()

    days = leave_mod.approved_leave_days(db, "2026-08-30", "2026-09-05")
    assert (emp.id, "2026-08-30") in days
    assert (emp.id, "2026-08-31") in days
    assert (emp.id, "2026-09-01") not in days
