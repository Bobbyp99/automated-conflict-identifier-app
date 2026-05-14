from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ScanJob(Base):
    """Tracks the state of one background conflict scan."""
    __tablename__ = "scan_jobs"

    id           = Column(String, primary_key=True)   # UUID
    status       = Column(String, default="pending")   # pending / running / done / error
    total        = Column(Integer, default=0)          # unique matter URLs to scan
    processed    = Column(Integer, default=0)          # matters fetched so far
    flagged      = Column(Integer, default=0)          # conflicts written so far
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_msg    = Column(Text, nullable=True)


class ConflictResult(Base):
    """One flagged conflict — mirrors the columns in flagged_conflicts.csv."""
    __tablename__ = "conflict_results"

    id                = Column(Integer, primary_key=True)
    job_id            = Column(String, index=True)
    official_name     = Column(String)
    vote_outcome      = Column(String)
    file_number       = Column(String)
    subject           = Column(Text)
    vote_date         = Column(String)
    meeting_type      = Column(String)
    overall_result    = Column(String)
    entity_matched    = Column(String)
    interest_schedule = Column(String)
    interest_year     = Column(String)
    link              = Column(String)


def get_engine(db_url: str = "sqlite:///./fppc.db"):
    return create_engine(db_url, connect_args={"check_same_thread": False})


def init_db(engine):
    Base.metadata.create_all(engine)
