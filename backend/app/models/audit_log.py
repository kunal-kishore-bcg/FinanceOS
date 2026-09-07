from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func

from app.database import Base


class AuditLog(Base):
    """
    Matches brief minimum schema (section 3.3) exactly: id, user_id,
    entity_type, entity_id, action, old_value, new_value, timestamp.

    user_id is nullable — an AI-generated recommendation is itself an
    auditable event (section 6.2: "Log every AI decision") and has no
    human user attached. NULL user_id = system/AI action; populated
    user_id = human action. Whatever writes to this table later must
    make that explicit, not leave it implied by a null.

    old_value / new_value use SQLAlchemy's JSON type, which serializes
    to TEXT under the hood on SQLite — fine for this DB, flagged here
    in case the target database ever changes.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = system/AI-generated event
    entity_type = Column(String, nullable=False)  # e.g. "invoice"
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # e.g. "ai_recommendation", "human_override", "status_change"
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
