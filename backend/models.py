from sqlalchemy import Column, Integer, String
from backend.database import Base

class Official(Base):
    __tablename__ = "officials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
