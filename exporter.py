"""
DocsGuards – Excel Export Engine
Generates a beautifully formatted .xlsx schedule using openpyxl.
"""
from __future__ import annotations

import calendar
from typing import List

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment, Border, Font, GradientFill, PatternFill, Side
)
from openpyxl.utils import get_column_letter

from models import ScheduleRow


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

C = {
    "header_bg":   "0D1B2E",   # Dark navy  – column headers
    "title_bg":    "071428",   # Darker     – title row
    "weekday_a":   "FFFFFF",   # Pure white – alternating weekday row A
    "weekday_b":   "F7FAFF",   # Off-white  – alternating weekday row B
    "weekend_a":   "EDE9FE",   # Soft violet weekend A
    "weekend_b":   "DDD6FE",   # Slightly deeper violet B
    "holiday":     "FEF9C3",   # Light amber – holiday rows
    "legend_hdr":  "1E293B",   # Legend header bg
    "border":      "CBD5E1",   # Light slate border
    "accent":      "06B6D4",   # Cyan accent (top stripe)
    "weekend_hdr": "7C3AED",   # Purple strip for weekends
    "holiday_hdr": "D97706",   # Amber strip for holidays
    "white":       "FFFFFF",
    "black":       "0F172A",
    "muted":       "64748B",
    "assigned_fg": "1E3A5F",   # Dark navy text for assigned doctor
}


def _thin_border(color: str = "CBD5E1") -> Border:
    s = Side(style="thin", color=color)
    return Border(left=s, right=s, top=s, bottom=s)


def _fill(hex_color: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=hex_color)


def _font(
    bold: bool = False,
    size: int = 10,
    color: str = "0F172A",
    name: str = "Calibri",
    italic: bool = False,
) -> Font:
    return Font(name=name, bold=bold, size=size, color=color, italic=italic)


def _center(wrap: bool = False) -> Alignment:
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)


def _left(wrap: bool = False) -> Alignment:
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_schedule_to_excel(
    schedule: List[ScheduleRow],
    month: int,
    year: int,
    output_path: str,
) -> str:
    """
    Write the schedule to an Excel workbook.

    Returns the output_path for convenience.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = f"{calendar.month_abbr[month]} {year}"

    # ── Row 1 : Big title ──────────────────────────────────────────────────
    ws.merge_cells("A1:G1")
    t = ws["A1"]
    t.value = f"  🏥  Medical On-Call Guard Schedule  ·  {calendar.month_name[month]} {year}"
    t.fill      = _fill(C["title_bg"])
    t.font      = Font(name="Calibri", bold=True, size=15, color=C["white"])
    t.alignment = _center()
    ws.row_dimensions[1].height = 38

    # ── Row 2 : Accent stripe ─────────────────────────────────────────────
    ws.merge_cells("A2:G2")
    stripe = ws["A2"]
    stripe.fill = PatternFill(
        fill_type="solid",
        fgColor=C["accent"],
    )
    ws.row_dimensions[2].height = 4

    # ── Row 3 : Column headers ────────────────────────────────────────────
    HEADERS = ["Date", "Day", "Shift Type", "Time Slot",
               "Assigned Doctor", "Replacement 1", "Replacement 2"]
    HDR_ROW = 3

    for col, h in enumerate(HEADERS, 1):
        cell          = ws.cell(row=HDR_ROW, column=col, value=h.upper())
        cell.fill     = _fill(C["header_bg"])
        cell.font     = Font(name="Calibri", bold=True, size=10, color=C["white"])
        cell.alignment = _center(wrap=True)
        cell.border   = _thin_border(C["header_bg"])
    ws.row_dimensions[HDR_ROW].height = 28

    # ── Data rows ─────────────────────────────────────────────────────────
    row_num = HDR_ROW + 1
    prev_date_str = ""
    alt_toggle = False   # alternating row colour within same category

    for srow in schedule:
        date_str = srow.date.isoformat()
        if date_str != prev_date_str:
            prev_date_str = date_str
            alt_toggle = not alt_toggle   # flip on each new calendar date

        # Determine background
        if srow.is_holiday:
            bg = C["holiday"]
        elif srow.is_weekend:
            bg = C["weekend_a"] if alt_toggle else C["weekend_b"]
        else:
            bg = C["weekday_a"] if alt_toggle else C["weekday_b"]

        # Left colour-tab in column A (gives a coloured edge feel)
        tab_color = (
            C["holiday_hdr"] if srow.is_holiday
            else C["weekend_hdr"] if srow.is_weekend
            else C["header_bg"]
        )

        # Shift type label + icon
        shift_label = srow.shift_type
        if "Night" in srow.shift_type:
            shift_label = "🌙 " + shift_label
        elif "Day 1" in srow.shift_type:
            shift_label = "🌅 " + shift_label
        elif "Day 2" in srow.shift_type:
            shift_label = "☀️ " + shift_label

        # Holiday badge append
        holiday_suffix = f"  🎉 {srow.holiday_name}" if srow.is_holiday else ""

        values = [
            srow.date.strftime("%d/%m/%Y") + holiday_suffix,
            srow.day_name,
            shift_label,
            srow.time_slot,
            srow.assigned_doctor or "UNASSIGNED",
            srow.replacement_1 or "UNASSIGNED",
            srow.replacement_2 or "UNASSIGNED",
        ]

        for col, val in enumerate(values, 1):
            cell            = ws.cell(row=row_num, column=col, value=val)
            cell.fill       = _fill(bg)
            cell.border     = _thin_border(C["border"])
            cell.alignment  = _center() if col != 5 else _left()

            # Font styling
            if col == 1:                        # Date column
                cell.font = Font(name="Calibri", size=10, bold=True,
                                 color=tab_color)
            elif col == 5:                      # Assigned doctor – prominent
                cell.font = Font(name="Calibri", size=10, bold=True,
                                 color=C["assigned_fg"])
            elif col in (6, 7):                 # Replacements – subtle
                cell.font = Font(name="Calibri", size=10, color=C["muted"],
                                 italic=True)
            else:
                cell.font = _font(size=10, color=C["black"])

        ws.row_dimensions[row_num].height = 20
        row_num += 1

    # ── Column widths ──────────────────────────────────────────────────────
    COL_WIDTHS = [20, 12, 22, 18, 26, 26, 26]
    for i, w in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── Freeze panes (keep headers visible while scrolling) ───────────────
    ws.freeze_panes = ws.cell(row=HDR_ROW + 1, column=1)

    # ── Legend block ──────────────────────────────────────────────────────
    row_num += 2

    ws.cell(row=row_num, column=1, value="Legend:").font = Font(
        name="Calibri", bold=True, size=10, color=C["muted"]
    )
    row_num += 1

    legend_items = [
        (C["weekday_a"],  "Regular Weekday (Sunday – Thursday)"),
        (C["weekend_a"],  "Weekend (Friday or Saturday)"),
        (C["holiday"],    "Public / National Holiday"),
    ]
    for bg_hex, label in legend_items:
        cell_a = ws.cell(row=row_num, column=1, value=f"   {label}")
        cell_a.fill      = _fill(bg_hex)
        cell_a.border    = _thin_border(C["border"])
        cell_a.font      = Font(name="Calibri", size=9, color=C["black"])
        cell_a.alignment = _left()
        ws.row_dimensions[row_num].height = 18
        row_num += 1

    # ── Summary statistics ─────────────────────────────────────────────────
    row_num += 1
    total_shifts = len(schedule)
    unassigned   = sum(1 for r in schedule if r.assigned_doctor == "UNASSIGNED")
    holidays_cnt = len({r.date for r in schedule if r.is_holiday})

    summary_lines = [
        f"Total shift slots : {total_shifts}",
        f"Unassigned slots  : {unassigned}",
        f"Holiday dates     : {holidays_cnt}",
        f"Generated for     : {calendar.month_name[month]} {year}",
    ]
    for line in summary_lines:
        c = ws.cell(row=row_num, column=1, value=line)
        c.font      = Font(name="Calibri", size=9, color=C["muted"], italic=True)
        c.alignment = _left()
        row_num += 1

    # ── Save ───────────────────────────────────────────────────────────────
    wb.save(output_path)
    return output_path
