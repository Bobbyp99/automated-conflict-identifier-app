from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base

class Officials(Base):
    __tablename__ = "officials"

    #id = Column(Integer, primary_key=True, index=True)
    #first_name = Column(String)
    id: Mapped[int] = mapped_column(primary_key = True) # do once for each table

    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    middle_name: Mapped[str] = mapped_column(String)



class Jurisdictions(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(primary_key = True) 

    jurisdiction_name: Mapped[str] = mapped_column(String)





