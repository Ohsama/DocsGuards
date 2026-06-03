"""
DocsGuards – Scheduling Engine
Implements Round-Robin queues and the monthly schedule generator.
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Dict, List, Optional, Set

from models import Doctor, ScheduleRow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_weekend(d: date) -> bool:
    """
    Weekend = Friday (weekday 4) or Saturday (weekday 5) in the Middle-East
    work-week where the weekend is Fri-Sat.
    Python's date.weekday(): Mon=0 … Fri=4, Sat=5, Sun=6
    """
    return d.weekday() in (4, 5)


def _get_day_name(d: date) -> str:
    return d.strftime("%A")


# ---------------------------------------------------------------------------
# Fair Round-Robin Queue
# ---------------------------------------------------------------------------

class RotationQueue:
    """
    Keeps a fair rotation list.

    Rule: a doctor must not receive a second assignment until every other
    currently active & available doctor in the same pool has had one.

    Implementation: maintain an ordered list.  When a doctor is selected,
    they are moved to the *end* of the list so they are last in line next.
    Doctors who are unavailable on a given day are simply skipped (they keep
    their position so they don't fall behind).
    """

    def __init__(self, doctors: List[Doctor]):
        self._queue: List[Doctor] = list(doctors)

    def get_next_available(
        self,
        d: date,
        exclude_ids: Optional[Set[str]] = None,
        holiday_name: Optional[str] = None,
        holiday_history: Optional[Dict] = None,
    ) -> Optional[Doctor]:
        """
        Return the next eligible doctor and rotate them to the back.

        exclude_ids     : doctors already assigned today (to avoid duplicates)
        holiday_name    : name of the holiday on date d (or None)
        holiday_history : {doctor_id: {holiday_name: [years_list]}}
        """
        if exclude_ids is None:
            exclude_ids = set()

        # 1. Filter for doctors who are active, available, and not already assigned today
        eligible_indices = []
        for idx, doctor in enumerate(self._queue):
            if doctor.id not in exclude_ids and doctor.is_available(d):
                eligible_indices.append(idx)

        if not eligible_indices:
            return None

        selected_idx = None

        # 2. Holiday logic: Pick the doctor who has worked this specific holiday the least
        if holiday_name and holiday_history is not None:
            counts = []
            for idx in eligible_indices:
                doc_id = self._queue[idx].id
                worked_years = holiday_history.get(doc_id, {}).get(holiday_name, [])
                counts.append(len(worked_years))
            
            min_count = min(counts)
            
            # Find the first doctor in our Round-Robin queue that matches the min_count
            for i, idx in enumerate(eligible_indices):
                if counts[i] == min_count:
                    selected_idx = idx
                    break
        else:
            # Normal day: just pick the first eligible doctor in the queue
            selected_idx = eligible_indices[0]

        # 3. Rotate them to the back of the queue and return
        if selected_idx is not None:
            doctor = self._queue.pop(selected_idx)
            self._queue.append(doctor)
            return doctor

        return None


# ---------------------------------------------------------------------------
# Main Schedule Generator
# ---------------------------------------------------------------------------

def generate_monthly_schedule(
    month: int,
    year: int,
    doctors: List[Doctor],
    holiday_history: Dict,
    holidays: Dict[str, str],       # {"YYYY-MM-DD": "Holiday Name"}
) -> List[ScheduleRow]:
    """
    Generate every shift slot for every day in the requested month.

    Weekday (Sun-Thu):   1 shift  → Night  19:00-08:00
    Weekend (Fri-Sat):   3 shifts → Day1 08:00-14:00 | Day2 14:00-20:00 | Night 20:00-08:00
    Every day:           2 Replacement doctors (global, from all-active pool)

    Fairness: Round-Robin queues are shared across the whole month, so no
    doctor gets a second shift before everyone else has had one.
    """

    # ── Split doctor pools ─────────────────────────────────────────────────
    std_pool  = [d for d in doctors if d.type == "Standard"       and d.status == "Active"]
    wkd_pool  = [d for d in doctors if d.type == "Weekend Worker" and d.status == "Active"]
    all_active = [d for d in doctors if d.status == "Active"]

    # ── Create persistent rotation queues (carry across entire month) ──────
    std_queue  = RotationQueue(std_pool)
    wkd_queue  = RotationQueue(wkd_pool)
    repl_queue = RotationQueue(all_active)

    schedule: List[ScheduleRow] = []
    num_days = calendar.monthrange(year, month)[1]

    for day_num in range(1, num_days + 1):
        current_date = date(year, month, day_num)
        day_name     = _get_day_name(current_date)
        weekend      = _is_weekend(current_date)
        holiday_name = holidays.get(current_date.isoformat())

        # Define shifts for the day
        if weekend:
            shifts = [
                ("Weekend Day 1", "08:00 – 14:00"),
                ("Weekend Day 2", "14:00 – 20:00"),
                ("Weekend Night", "20:00 – 08:00"),
            ]
            active_queue = wkd_queue
        else:
            shifts = [
                ("Weekday Night", "19:00 – 08:00"),
            ]
            active_queue = std_queue

        # ── Assign shift doctors ───────────────────────────────────────────
        assigned_today: Set[str] = set()
        shift_doctors: List[Optional[Doctor]] = []

        for _ in shifts:
            doc = active_queue.get_next_available(
                current_date,
                exclude_ids=assigned_today,
                holiday_name=holiday_name,
                holiday_history=holiday_history,
            )
            shift_doctors.append(doc)
            if doc:
                assigned_today.add(doc.id)

        # ── Assign 2 replacement doctors (global pool, anyone available) ───
        repl1 = repl_queue.get_next_available(
            current_date,
            exclude_ids=assigned_today,
            holiday_name=holiday_name,
            holiday_history=holiday_history,
        )
        if repl1:
            assigned_today.add(repl1.id)

        repl2 = repl_queue.get_next_available(
            current_date,
            exclude_ids=assigned_today,
            holiday_name=holiday_name,
            holiday_history=holiday_history,
        )

        repl1_name = repl1.name if repl1 else "UNASSIGNED"
        repl2_name = repl2.name if repl2 else "UNASSIGNED"

        # ── Build schedule rows ────────────────────────────────────────────
        for i, (shift_type, time_slot) in enumerate(shifts):
            doc = shift_doctors[i]
            schedule.append(
                ScheduleRow(
                    date=current_date,
                    day_name=day_name,
                    shift_type=shift_type,
                    time_slot=time_slot,
                    assigned_doctor=doc.name if doc else "UNASSIGNED",
                    replacement_1=repl1_name,
                    replacement_2=repl2_name,
                    is_weekend=weekend,
                    is_holiday=bool(holiday_name),
                    holiday_name=holiday_name or "",
                )
            )

    return schedule
