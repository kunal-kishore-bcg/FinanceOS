from sqlalchemy import Column, Integer, String, DateTime, func

from app.database import Base


class User(Base):
    """
    Brief minimum schema (section 3.3): id, email, role, created_at.

    Added beyond the brief: password_hash. "Basic user login" (section
    3.1) isn't implementable without storing a credential — this is a
    required addition, not scope creep. See docs/design-decisions-draft.md.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="analyst")  # analyst | manager | admin
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
