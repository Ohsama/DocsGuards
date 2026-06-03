"""
DocsGuards – Flask Web Application
Full CRUD for doctors, holidays, history, and schedule generation + export.
"""
from __future__ import annotations

import calendar
import json
import os
import uuid
from datetime import datetime, date

from flask import (
    Flask, flash, jsonify, redirect, render_template,
    request, send_file, url_for,
)

from models import Doctor, LeaveWindow
from scheduler import generate_monthly_schedule
from exporter import export_schedule_to_excel

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# ── Jinja2 globals ────────────────────────────────────────────────────────
app.jinja_env.globals['enumerate'] = enumerate

@app.context_processor
def inject_globals():
    return {'now': datetime.now()}

# Secure secret key handling
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24).hex())

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(DATA_DIR,    exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

DOCTORS_FILE  = os.path.join(DATA_DIR, "doctors.json")
HOLIDAYS_FILE = os.path.join(DATA_DIR, "holidays.json")
HISTORY_FILE  = os.path.join(DATA_DIR, "holiday_history.json")


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_doctors() -> list[Doctor]:
    if not os.path.exists(DOCTORS_FILE):
        return []
    with open(DOCTORS_FILE, "r", encoding="utf-8") as f:
        return [Doctor.from_dict(d) for d in json.load(f)]

def _save_doctors(docs: list[Doctor]) -> None:
    with open(DOCTORS_FILE, "w", encoding="utf-8") as f:
        json.dump([d.to_dict() for d in docs], f, indent=2, ensure_ascii=False)

def _load_holidays() -> dict:
    if not os.path.exists(HOLIDAYS_FILE):
        return {}
    with open(HOLIDAYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_holidays(h: dict) -> None:
    with open(HOLIDAYS_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2, ensure_ascii=False)

def _load_history() -> dict:
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_history(h: dict) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    doctors = _load_doctors()
    std_active  = sum(1 for d in doctors if d.type == "Standard"       and d.status == "Active")
    wkd_active  = sum(1 for d in doctors if d.type == "Weekend Worker" and d.status == "Active")
    inactive    = sum(1 for d in doctors if d.status == "Inactive")
    on_leave    = sum(
        1 for d in doctors
        if any(lw.covers(date.today()) for lw in d.leave_windows)
    )
    return render_template(
        "index.html",
        active_page="dashboard",
        total=len(doctors),
        std_active=std_active,
        wkd_active=wkd_active,
        inactive=inactive,
        on_leave=on_leave,
        doctors=doctors,
    )


# ---------------------------------------------------------------------------
# Doctors
# ---------------------------------------------------------------------------

@app.route("/doctors")
def doctors_page():
    doctors = _load_doctors()
    return render_template("doctors.html", active_page="doctors", doctors=doctors)


@app.route("/doctors/add", methods=["POST"])
def add_doctor():
    doctors = _load_doctors()
    doc_id  = f"DR{len(doctors)+1:03d}"

    # Handle potential ID collision
    existing_ids = {d.id for d in doctors}
    while doc_id in existing_ids:
        doc_id = "DR" + str(uuid.uuid4())[:6].upper()

    new_doc = Doctor(
        id=doc_id,
        name=request.form["name"].strip(),
        type=request.form["type"],
        status=request.form["status"],
        leave_windows=[],
    )
    doctors.append(new_doc)
    _save_doctors(doctors)
    flash(f"✅  Dr. {new_doc.name} added successfully (ID: {doc_id}).", "success")
    return redirect(url_for("doctors_page"))


@app.route("/doctors/update", methods=["POST"])
def update_doctor():
    doctors = _load_doctors()
    doc_id  = request.form["id"]
    for d in doctors:
        if d.id == doc_id:
            d.name   = request.form["name"].strip()
            d.type   = request.form["type"]
            d.status = request.form["status"]
            break
    _save_doctors(doctors)
    flash("✅  Doctor record updated.", "success")
    return redirect(url_for("doctors_page"))


@app.route("/doctors/delete/<doc_id>", methods=["POST"])
def delete_doctor(doc_id):
    doctors = [d for d in _load_doctors() if d.id != doc_id]
    _save_doctors(doctors)
    flash("🗑️  Doctor removed.", "info")
    return redirect(url_for("doctors_page"))


@app.route("/doctors/<doc_id>/leave/add", methods=["POST"])
def add_leave(doc_id):
    doctors = _load_doctors()
    for d in doctors:
        if d.id == doc_id:
            lw = LeaveWindow(
                start=date.fromisoformat(request.form["start"]),
                end=date.fromisoformat(request.form["end"]),
                reason=request.form.get("reason", "").strip(),
            )
            d.leave_windows.append(lw)
            break
    _save_doctors(doctors)
    flash("📅  Leave window added.", "success")
    return redirect(url_for("doctors_page"))


@app.route("/doctors/<doc_id>/leave/delete/<int:leave_idx>", methods=["POST"])
def delete_leave(doc_id, leave_idx):
    doctors = _load_doctors()
    for d in doctors:
        if d.id == doc_id:
            if 0 <= leave_idx < len(d.leave_windows):
                d.leave_windows.pop(leave_idx)
            break
    _save_doctors(doctors)
    flash("🗑️  Leave window removed.", "info")
    return redirect(url_for("doctors_page"))


# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------

@app.route("/schedule")
def schedule_page():
    now = datetime.now()
    return render_template(
        "schedule.html",
        active_page="schedule",
        current_month=now.month,
        current_year=now.year,
        months=[(i, calendar.month_name[i]) for i in range(1, 13)],
        years=list(range(2024, 2031)),
    )


@app.route("/schedule/generate", methods=["POST"])
def generate():
    month = int(request.form["month"])
    year  = int(request.form["year"])

    doctors  = _load_doctors()
    history  = _load_history()
    holidays = _load_holidays()

    schedule = generate_monthly_schedule(month, year, doctors, history, holidays)
    rows = [r.to_dict() for r in schedule]

    return render_template(
        "schedule_view.html",
        active_page="schedule",
        schedule=rows,
        month=month,
        year=year,
        month_name=calendar.month_name[month],
    )


@app.route("/schedule/export", methods=["POST"])
def export_schedule():
    month = int(request.form["month"])
    year  = int(request.form["year"])

    doctors  = _load_doctors()
    history  = _load_history()
    holidays = _load_holidays()

    schedule = generate_monthly_schedule(month, year, doctors, history, holidays)

    fname = f"Schedule_{calendar.month_name[month]}_{year}.xlsx"
    path  = os.path.join(EXPORTS_DIR, fname)
    export_schedule_to_excel(schedule, month, year, path)

    return send_file(path, as_attachment=True, download_name=fname)


@app.route("/schedule/save_history", methods=["POST"])
def save_to_history():
    """
    After generating a schedule the user can commit holiday assignments
    to the holiday_history so next year those doctors won't repeat.
    """
    month = int(request.form["month"])
    year  = int(request.form["year"])

    doctors  = _load_doctors()
    history  = _load_history()
    holidays = _load_holidays()

    schedule = generate_monthly_schedule(month, year, doctors, history, holidays)

    doctor_map = {d.name: d.id for d in doctors}
    updated = 0

    for row in schedule:
        if not row.is_holiday or not row.holiday_name:
            continue
        if row.assigned_doctor == "UNASSIGNED":
            continue
        doc_id = doctor_map.get(row.assigned_doctor)
        if not doc_id:
            continue
        hname = row.holiday_name
        if doc_id not in history:
            history[doc_id] = {}
        if hname not in history[doc_id]:
            history[doc_id][hname] = []
        if year not in history[doc_id][hname]:
            history[doc_id][hname].append(year)
            updated += 1

    _save_history(history)
    flash(f"📜  Holiday history updated with {updated} new record(s).", "success")
    return redirect(url_for("schedule_page"))


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------

@app.route("/holidays")
def holidays_page():
    holidays = _load_holidays()
    sorted_h = dict(sorted(holidays.items()))
    return render_template("holidays.html", active_page="holidays", holidays=sorted_h)


@app.route("/holidays/add", methods=["POST"])
def add_holiday():
    holidays = _load_holidays()
    key  = request.form["date"]
    name = request.form["name"].strip()
    holidays[key] = name
    _save_holidays(holidays)
    flash(f"🎉  Holiday '{name}' saved.", "success")
    return redirect(url_for("holidays_page"))


@app.route("/holidays/delete", methods=["POST"])
def delete_holiday():
    holidays = _load_holidays()
    key = request.form["date"]
    removed = holidays.pop(key, None)
    _save_holidays(holidays)
    if removed:
        flash(f"🗑️  Holiday '{removed}' removed.", "info")
    return redirect(url_for("holidays_page"))


# ---------------------------------------------------------------------------
# Holiday history
# ---------------------------------------------------------------------------

@app.route("/history")
def history_page():
    history = _load_history()
    doctors = _load_doctors()
    doc_map = {d.id: d.name for d in doctors}
    return render_template(
        "history.html",
        active_page="history",
        history=history,
        doc_map=doc_map,
        doctors=doctors,
    )


@app.route("/history/add", methods=["POST"])
def add_history():
    history  = _load_history()
    doc_id   = request.form["doctor_id"]
    hol_name = request.form["holiday_name"].strip()
    year     = int(request.form["year"])

    history.setdefault(doc_id, {}).setdefault(hol_name, [])
    if year not in history[doc_id][hol_name]:
        history[doc_id][hol_name].append(year)

    _save_history(history)
    flash("📜  Record added to holiday history.", "success")
    return redirect(url_for("history_page"))


@app.route("/history/delete", methods=["POST"])
def delete_history():
    history  = _load_history()
    doc_id   = request.form["doctor_id"]
    hol_name = request.form["holiday_name"]
    year     = int(request.form["year"])

    try:
        history[doc_id][hol_name].remove(year)
        if not history[doc_id][hol_name]:
            del history[doc_id][hol_name]
        if not history[doc_id]:
            del history[doc_id]
    except (KeyError, ValueError):
        pass

    _save_history(history)
    flash("🗑️  History record removed.", "info")
    return redirect(url_for("history_page"))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  DocsGuards Medical Scheduling System  ")
    print("=" * 55)
    print("  -> Open your browser at:  http://localhost:5000")
    print("  -> Press  Ctrl + C  to stop the server.")
    print("=" * 55 + "\n")
    app.run(debug=True, port=5000)
