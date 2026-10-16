"""Reusable activity suggestions, distinct from scheduled care_activity events."""
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models import ID, Times


class ActivityTemplate(Times, Base):
    __tablename__ = 'activity'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(50))
    intensity: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    duration_hint: Mapped[str | None] = mapped_column(String(100))
    rules: Mapped[str | None] = mapped_column(String(1000))
    contraindications: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[int] = mapped_column(Integer, default=1)
