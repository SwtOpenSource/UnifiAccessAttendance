import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HostConfig(Base):
    """單一列設定：目前這個部署要連的 UniFi Access 主機。"""
    __tablename__ = "host_config"

    id = Column(String(32), primary_key=True, default=_id)
    host_type = Column(String(16), nullable=False)   # "uckp" | "unvr"
    base_url = Column(String(255), nullable=False)     # e.g. https://192.168.1.1
    credential = Column(String(255), nullable=False)   # UCKP: API key (X-API-KEY) / UNVR: Bearer token
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class AdminSession(Base):
    """管理員是用 UniFi Access 帳密即時登入驗證的（不落地密碼），這裡只記住「誰驗證過」方便顯示。"""
    __tablename__ = "admins_seen"

    id = Column(String(32), primary_key=True, default=_id)
    username = Column(String(120), unique=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class Employee(Base):
    """本地帳號，跟 UniFi Access 帳號完全分開，只用來讓員工送請假／看自己的紀錄。"""
    __tablename__ = "employees"

    id = Column(String(32), primary_key=True, default=_id)
    username = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(120), nullable=False)
    unifi_user_id = Column(String(120), nullable=False, default="")  # 綁定 UniFi Access 門禁使用者 ID，比對打卡用
    department = Column(String(120), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    leave_requests = relationship("LeaveRequest", back_populates="employee")


class DutyTime(Base):
    """全公司統一的上下班時間（跟舊版一樣，單一設定，不分部門/排班）。"""
    __tablename__ = "duty_time"

    id = Column(String(32), primary_key=True, default=_id)
    start_work = Column(String(8), nullable=False, default="")  # "HH:MM"
    get_off = Column(String(8), nullable=False, default="")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(String(32), primary_key=True, default=_id)
    employee_id = Column(String(32), ForeignKey("employees.id"), nullable=False)
    leave_type = Column(String(40), nullable=False, default="事假")
    start_date = Column(String(10), nullable=False)  # "YYYY-MM-DD"
    end_date = Column(String(10), nullable=False)
    reason = Column(Text, nullable=False, default="")
    status = Column(String(16), nullable=False, default="pending")  # pending | approved | rejected
    reviewer_note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=_now)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    employee = relationship("Employee", back_populates="leave_requests")


class PublicBoardSetting(Base):
    """免登入公開排行榜連結的開關。單一列。"""
    __tablename__ = "public_board_setting"

    id = Column(String(32), primary_key=True, default=_id)
    enabled = Column(Boolean, nullable=False, default=False)
    slug = Column(String(64), nullable=False, unique=True, default=lambda: uuid.uuid4().hex[:12])
