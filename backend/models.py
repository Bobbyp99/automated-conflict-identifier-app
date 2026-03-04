from sqlalchemy import String, Float, ForeignKey
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

    # Relationships
    jurisdiction: Mapped["Jurisdictions"] = relationship(back_populates = "officials")


class Jurisdictions(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[int] = mapped_column(primary_key = True) 


    jurisdiction_name: Mapped[str] = mapped_column(String)

    # Relationships
    officials: Mapped[List["Officials"]] = relationship(back_populates = "jurisdiction")


class Decisions(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key = True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"))

    decision_date: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    decision_url: Mapped[str] = mapped_column(String)  # client mentioned we might want to include the URL in output 

    # Relationships


class DecisionParticipants(Base):
     __tablename__ = "decision_participants"

     id: Mapped[int] = mapped_column(primary_key = True)

     name_raw: Mapped[str] = mapped_column(String)



# This table will actually estimate whether or not a participant is an official 
# dedicated folder of python files for this, but only after ingestion of data into database
class ParticipantMatch(Base):
    __tablename__ = "participant_matches"
	 
    id: Mapped[int] = mapped_column(primary_key = True)
    match_score: Mapped[float] = mapped_column(Float)


class ConflictFlag(Base):
    __tablename__ = "conflict_flags"

    id: Mapped[int] = mapped_column(primary_key = True)
    officials_id: Mapped[int] = mapped_column(ForeignKey("officials.id"))

    # we will store the explanation of the match (x official, y decision on date, z source of income year))
    explanation: Mapped[str] = mapped_column(String)

    





