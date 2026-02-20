
# app/models.py

from sqlalchemy import Column, String, LargeBinary, Integer, DateTime, Boolean, ForeignKey
from .db import Base
from datetime import datetime
import pytz
from sqlalchemy.orm import relationship


def current_time_ist():
    """Return current datetime in IST (naive, no timezone info)."""
    ist_tz = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist_tz).replace(tzinfo=None)


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    club_code = Column(String, unique=True, nullable=False)
    club_name = Column(String, nullable=False)
    url = Column(String, unique=True)
    logs = relationship(
        "RecognitionLog",
        backref="club",
        passive_deletes=True
    )

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)  # store hashed passwords ideally
    mobile = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    
    # A user can belong to one club or None
    
    assigned_to = Column(Integer, ForeignKey("clubs.id"), nullable=True, default=None)
    
    # For delete constraint on FK    
    # assigned_to = Column(Integer, ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True, default=None)

        
class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    member_code = Column(String, nullable=True, index=True)
    embedding = Column(LargeBinary, nullable=False)
    image_path = Column(String, nullable=True)


class RecognitionLog(Base):
    __tablename__ = "recognition_log"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String)
    name = Column(String)
    member_code = Column(String)
    recognized_at = Column(DateTime, default=current_time_ist)
    source = Column(String, default="live_recognize_api")
    club_id = Column(Integer, ForeignKey("clubs.id", ondelete="SET NULL"), nullable=True)