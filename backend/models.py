from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from backend.database import Base

class Officials(Base):
    __tablename__ = "officials"

    #id = Column(Integer, primary_key=True, index=True)
    #first_name = Column(String)
    id: Mapped[int] = mapped_column(primary_key = True) # do once for each table
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"))

    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    middle_name: Mapped[str] = mapped_column(String)
    name_suffix: Mapped[str] = mapped_column(String)

    cleaned_name: Mapped[str] = mapped_column(String)  # this will be all lowercase for easier fuzzy search implementation

    #Relationships
    jurisdiction: Mapped["Jurisdictions"] = relationship(back_populates = "officials")




class Jurisdictions(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(primary_key = True) 


    jurisdiction_name: Mapped[str] = mapped_column(String)

    #Relationships
    officials: Mapped[List["Officials"]] = relationship(back_populates = "jurisdictions")


#class Flags(Base):
  #  __tablename__ = "flags"

   # id: Mapped[int] = mapped_column(primary_key = True)


    





