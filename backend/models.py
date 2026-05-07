from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, Session
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    """Represents an uploaded CSV file (interests or votes)."""
    __tablename__ = "datasets"

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False)       # original filename
    kind        = Column(String, nullable=False)       # "interests" or "votes"
    row_count   = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    interests = relationship("Interest", back_populates="dataset", cascade="all, delete-orphan")
    votes     = relationship("Vote",     back_populates="dataset", cascade="all, delete-orphan")


class Interest(Base):
    """One row from a disclosed-interests (Form 700) CSV."""
    __tablename__ = "interests"

    id         = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    employee   = Column(String, index=True)   # normalised employee name
    entity     = Column(String)               # NAME OF BUSINESS ENTITY
    inv_type   = Column(String)               # nature of investment
    fmv        = Column(String)               # fair market value range
    raw_json   = Column(Text)                 # full original row as JSON

    dataset = relationship("Dataset", back_populates="interests")


class Vote(Base):
    """One row from a voting / board-minutes CSV."""
    __tablename__ = "votes"

    id         = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    employee   = Column(String, index=True)   # normalised voter name
    subject    = Column(Text)                 # agenda item / vote subject
    vote_date  = Column(String)
    raw_json   = Column(Text)                 # full original row as JSON

    dataset = relationship("Dataset", back_populates="votes")


class ConflictResult(Base):
    """Persisted conflict match between one Interest and one Vote."""
    __tablename__ = "conflict_results"

    id          = Column(Integer, primary_key=True)
    run_id      = Column(String, index=True)        # UUID grouping one analysis run
    employee    = Column(String)
    entity      = Column(String)
    entity_type = Column(String)
    subject     = Column(Text)
    vote_date   = Column(String)
    score       = Column(Integer)                   # 0-100
    likelihood  = Column(String)                    # High / Medium / Low
    created_at  = Column(DateTime, default=datetime.utcnow)


def get_engine(db_url: str = "sqlite:///./fppc.db"):
    return create_engine(db_url, connect_args={"check_same_thread": False})


def init_db(engine):
    Base.metadata.create_all(engine)
