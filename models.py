"""
DocsGuards – Data Models
Defines Doctor, LeaveWindow, and ScheduleRow data structures.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


# ---------------------------------------------------------------------------
# Leave Window
# ---------------------------------------------------------------------------

@dataclass
class LeaveWindow:
    """Represents an absence period for a doctor."""
    start: date
    end: date
    reason: str = ""

    def covers(self, d: date) -> bool:
        """Return True if this leave window covers the given date."""
        return self.start <= d <= self.end

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LeaveWindow":
        return cls(
            start=date.fromisoformat(data["start"]),
            end=date.fromisoformat(data["end"]),
            reason=data.get("reason", ""),
        )


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------

@dataclass
class Doctor:
    """
    A single doctor entry.

    type   : 'Standard'       → weekday night shifts only
             'Weekend Worker' → weekend shifts only
    status : 'Active' | 'Inactive'
    """
    id: str
    name: str
    type: str          # 'Standard' | 'Weekend Worker'
    status: str        # 'Active'  | 'Inactive'
    leave_windows: List[LeaveWindow] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def is_available(self, d: date) -> bool:
        """Return True only if Active and not on leave on date d."""
        if self.status != "Active":
            return False
        for lw in self.leave_windows:
            if lw.covers(d):
                return False
        return True

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "leave_windows": [lw.to_dict() for lw in self.leave_windows],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Doctor":
        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            status=data["status"],
            leave_windows=[LeaveWindow.from_dict(lw) for lw in data.get("leave_windows", [])],
        )


# ---------------------------------------------------------------------------
# Schedule Row  (one row in the output table)
# ---------------------------------------------------------------------------

@dataclass
class ScheduleRow:
    """One shift slot in the generated schedule."""
    date: date
    day_name: str
    shift_type: str          # e.g. 'Weekday Night', 'Weekend Day 1', …
    time_slot: str           # e.g. '19:00 – 08:00'
    assigned_doctor: Optional[str]
    replacement_1: Optional[str]
    replacement_2: Optional[str]
    is_weekend: bool = False
    is_holiday: bool = False
    holiday_name: str = ""

    def to_dict(self) -> dict:
        return {
            "date": self.date.strftime("%d/%m/%Y"),
            "day_name": self.day_name,
            "shift_type": self.shift_type,
            "time_slot": self.time_slot,
            "assigned_doctor": self.assigned_doctor or "UNASSIGNED",
            "replacement_1": self.replacement_1 or "UNASSIGNED",
            "replacement_2": self.replacement_2 or "UNASSIGNED",
            "is_weekend": self.is_weekend,
            "is_holiday": self.is_holiday,
            "holiday_name": self.holiday_name,
            "date_iso": self.date.isoformat(),
        }
