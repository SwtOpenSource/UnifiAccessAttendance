from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HostConfigIn(BaseModel):
    host_type: str  # "uckp" | "unvr"
    base_url: str
    credential: str


class HostConfigOut(BaseModel):
    host_type: str
    base_url: str
    configured: bool


class AdminLoginBody(BaseModel):
    username: str
    password: str


class EmployeeLoginBody(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    role: str  # "admin" | "employee"
    display_name: str


class DutySet(BaseModel):
    start_work: str
    get_off: str


class EmployeeCreate(BaseModel):
    username: str
    password: str
    display_name: str
    unifi_user_id: str = ""
    department: str = ""


class EmployeeUnifiBind(BaseModel):
    unifi_user_id: str = ""


class EmployeeOut(BaseModel):
    id: str
    username: str
    display_name: str
    unifi_user_id: str
    department: str
    is_active: bool

    class Config:
        from_attributes = True


class LeaveCreate(BaseModel):
    leave_type: str = "事假"
    start_date: str
    end_date: str
    reason: str = ""


class LeaveDecision(BaseModel):
    approve: bool
    note: str = ""


class LeaveOut(BaseModel):
    id: str
    employee_id: str
    employee_name: str = ""
    leave_type: str
    start_date: str
    end_date: str
    reason: str
    status: str
    reviewer_note: str
    created_at: datetime
    reviewed_at: datetime | None = None


class PublicBoardToggle(BaseModel):
    enabled: bool
