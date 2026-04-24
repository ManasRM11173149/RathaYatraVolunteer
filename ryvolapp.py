"""
RY 2026 — Ratha Yatra 2026 Volunteer Portal (v2)
=================================================
3 tabs:
  1. Volunteer Signup (3-step: event -> category -> task)
  2. Volunteer Statistics
  3. Admin Dashboard (password protected)

Event -> Category -> Task hierarchy with per-task slots.
Each slot shows initials (auto-generated from first+last name).
Slot states: filled / open / pending / withdrawn.
"""

from flask import (Flask, render_template, request, redirect, url_for,
                   jsonify, session, flash, Response)
from datetime import datetime
from functools import wraps
import json
import os
import csv
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = "ry2026_v2_secret_change_in_production"

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SIGNUPS_FILE = os.path.join(DATA_DIR, "signups.json")
os.makedirs(DATA_DIR, exist_ok=True)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "rathayatra2026")

# Email (SMTP) — set env vars to enable real sending
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@rathayatra2026.org")

# SMS (Twilio)
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "")

# ═══════════════════════════════════════════════════════════════════
# EVENTS → CATEGORIES → TASKS
# ═══════════════════════════════════════════════════════════════════
# Per your request: 2 default categories per event until you decide final ones.
# Each task has: id, name, time, location/type, slots
EVENTS = [
    {
        "id": "snana_purnima",
        "name": "Deva Snana Purnima",
        "date": "July 5, 2026",
        "weekday": "Sunday",
        "time": "04:30 PM",
        "color": "#378ADD", "light": "#E6F1FB", "dark": "#0C447C",
        "categories": [
            {"id": "setup_supplies", "name": "Setup & Supplies",
             "tasks": [
                 {"id": "t1", "name": "Snana Mandap Arrangement", "slots": 5},
                 {"id": "t2", "name": "Seclusion Chamber Setup", "slots": 5},
                 {"id": "t3", "name": "Seclusion Chamber Notice", "slots": 1},
                 {"id": "t4", "name": "Grocery Purchase & Delivery", "slots": 2},
                 {"id": "t5", "name": "Vegetables Purchase & Delivery", "slots": 2},
                 {"id": "t6", "name": "Water Delivery", "slots": 2},
                 {"id": "t7", "name": "Water Station", "slots": 2},
                 {"id": "t8", "name": "Snana Mandap Dismantle", "slots": 8},
             ]},
            {"id": "ritual_ceremony", "name": "Ritual & Ceremony",
             "tasks": [
                 {"id": "t9", "name": "Flower Arrangement", "slots": 1},
                 {"id": "t10", "name": "Puja Samagri Purchase", "slots": 1},
                 {"id": "t11", "name": "Vastra Arrangement & Bed Setup", "slots": 1},
                 {"id": "t12", "name": "Pahandi Volunteer", "slots": 13},
                 {"id": "t13", "name": "Coconut and Mango Leaves Purchase", "slots": 2},
             ]},
            {"id": "prasad_prep", "name": "Prasad Prep & Serving",
             "tasks": [
                 {"id": "t14", "name": "Prasad Prep at AHT Kitchen", "slots": 4},
                 {"id": "t15", "name": "Prasad Serving and Cleanup", "slots": 6},
             ]},
        ],
    },
    {
        "id": "netra_utsava",
        "name": "Netra Utsava",
        "date": "July 17, 2026",
        "weekday": "Friday",
        "time": "06:30 PM",
        "color": "#639922", "light": "#EAF3DE", "dark": "#27500A",
        "categories": [
            {"id": "setup_supplies", "name": "Setup & Supplies",
             "tasks": [
                 {"id": "t2", "name": "Seclusion Chamber Dismantle", "slots": 5},
                 {"id": "t3", "name": "Garbhalaya Cleanup", "slots": 2},
                 {"id": "t4", "name": "Grocery Purchase & Delivery", "slots": 2},
                 {"id": "t5", "name": "Vegetables Purchase & Delivery", "slots": 2},
                 {"id": "t6", "name": "Water Delivery", "slots": 2},
                 {"id": "t7", "name": "Water Station", "slots": 2},
             ]},
            {"id": "ritual_ceremony", "name": "Ritual & Ceremony",
             "tasks": [
                 {"id": "t8", "name": "Flower Arrangement", "slots": 1},
                 {"id": "t9", "name": "Puja Samagri Purchase", "slots": 1},
                 {"id": "t10", "name": "Vastra Arrangement", "slots": 1},
                 {"id": "t11", "name": "Pahandi Volunteer (Anasara → Ratnabedi)", "slots": 13},
             ]},
            {"id": "prasad_prep", "name": "Prasad Prep & Serving",
             "tasks": [
                 {"id": "t12", "name": "Prasad Prep at AHT Kitchen", "slots": 4},
                 {"id": "t13", "name": "Prasad Serving and Cleanup", "slots": 6},
             ]},
        ],
    },
    {
        "id": "ratha_yatra",
        "name": "Ratha Yatra",
        "date": "July 18, 2026",
        "weekday": "Saturday",
        "time": "05:00 PM",
        "color": "#D4537E", "light": "#FBEAF0", "dark": "#72243E",
        "categories": [
            {"id": "pre_event_setup", "name": "Pre-Event - Setup & Supplies",
             "tasks": [
                 {"id": "t1", "name": "Gundicha Mandap Arrangement", "slots": 3},
                 {"id": "t2", "name": "Tulasi Mala", "slots": 2},
                 {"id": "t3", "name": "Coconut Purchase (40)", "slots": 2},
                 {"id": "t4", "name": "Vegetable Receive & Drop @ AHT", "slots": 6},
                 {"id": "t5", "name": "Grocery Purchase & Delivery", "slots": 4},
                 {"id": "t6", "name": "Water Delivery", "slots": 1},
                 {"id": "t7", "name": "Water Station Setup", "slots": 3},
                 {"id": "t8", "name": "Water Station Serving", "slots": 8},
                 {"id": "t9", "name": "Storage Coordinator", "slots": 2},
                 {"id": "t10", "name": "Ratha Assemble & Decoration", "slots": 8},
             ]},
            {"id": "event_setup", "name": "Event - Setup & Supplies",
             "tasks": [
                 {"id": "t11", "name": "Prasad Serving Logistics", "slots": 2},
                 {"id": "t12", "name": "Water/Buttermilk Serving", "slots": 8},
                 {"id": "t13", "name": "Storage Coordinator", "slots": 2},
                 {"id": "t14", "name": "Ratha Assemble & Decoration", "slots": 8},
             ]},
            {"id": "pre_event_ritual", "name": "Pre-Event Ritual & Ceremony",
             "tasks": [
                 {"id": "t15", "name": "Flower Arrangement", "slots": 1},
                 {"id": "t16", "name": "Puja Samagri Purchase", "slots": 1},
                 {"id": "t17", "name": "Vastra Arrangement", "slots": 1},
                 {"id": "t18", "name": "Pahandi Volunteer (Anasara → Ratnabedi)", "slots": 13},
                 {"id": "t19", "name": "Kala-archana Arrangement", "slots": 1},
                 {"id": "t20", "name": "Ghanta Arrangement", "slots": 1},
             ]},
            {"id": "event_ritual", "name": "Event Ritual & Ceremony",
             "tasks": [
                 {"id": "t21", "name": "Havan Arrangement", "slots": 1},
                 {"id": "t22", "name": "Puja Samagri Purchase", "slots": 1},
                 {"id": "t23", "name": "Vastra Arrangement", "slots": 1},
                 {"id": "t24", "name": "Kala-archana Arrangement", "slots": 1},
                 {"id": "t25", "name": "Ghanta Arrangement", "slots": 1},
                 {"id": "t26", "name": "Pahandi (Ratnabedi → Ratha)", "slots": 19},
                 {"id": "t27", "name": "Deepam Arati", "slots": 1},
                 {"id": "t28", "name": "Pana", "slots": 1},
                 {"id": "t29", "name": "Pahandi (Ratha → Gundicha Temple)", "slots": 19},
                 {"id": "t30", "name": "Special Bhoga", "slots": 3},
             ]},
            {"id": "pre_event_prasad", "name": "Pre-Event Prasad Prep",
             "tasks": [
                 {"id": "t31", "name": "Prasad Prep at AHT Kitchen", "slots": 15},
                 {"id": "t32", "name": "AHT Coordination", "slots": 1},
             ]},
            {"id": "event_prasad", "name": "Event Prasad Prep",
             "tasks": [
                 {"id": "t33", "name": "Prasad Prep at AHT Kitchen", "slots": 10},
                 {"id": "t34", "name": "Prasad Serving", "slots": 15},
                 {"id": "t35", "name": "AHT Coordination", "slots": 1},
             ]},
        ],
    },
    {
        "id": "hera_panchami",
        "name": "Hera Panchami Rituals",
        "date": "July 25, 2026",
        "weekday": "Saturday",
        "time": "06:30 PM",
        "color": "#BA7517", "light": "#FAEEDA", "dark": "#633806",
        "categories": [
            {"id": "cat1", "name": "Category 1",
             "tasks": [
                 {"id": "t1", "name": "Task A", "time": "6:00pm – 7:00pm", "tag": "Ritual", "slots": 4},
                 {"id": "t2", "name": "Task B", "time": "6:30pm – 8:00pm", "tag": "Setup",  "slots": 3},
             ]},
            {"id": "cat2", "name": "Category 2",
             "tasks": [
                 {"id": "t3", "name": "Task A", "time": "6:30pm – 8:30pm", "tag": "Service","slots": 4},
             ]},
        ],
    },
    {
        "id": "bahuda_yatra",
        "name": "Bahuda Yatra",
        "date": "July 26, 2026",
        "weekday": "Sunday",
        "time": "10:00 AM",
        "color": "#534AB7", "light": "#EEEDFE", "dark": "#26215C",
        "categories": [
            {"id": "cat1", "name": "Category 1",
             "tasks": [
                 {"id": "t1", "name": "Task A", "time": "9:00am – 12:00pm", "tag": "Outdoor", "slots": 10},
                 {"id": "t2", "name": "Task B", "time": "8:00am – 10:00am", "tag": "Creative","slots": 6},
             ]},
            {"id": "cat2", "name": "Category 2",
             "tasks": [
                 {"id": "t3", "name": "Task A", "time": "10:00am – 2:00pm","tag": "Service", "slots": 8},
                 {"id": "t4", "name": "Task B", "time": "7:00am – 11:00am","tag": "Kitchen", "slots": 5},
             ]},
        ],
    },
]

CONTACT_INFO = {
    "venue": "Austin Hindu Temple",
    "address": "Decker Lake Road, Austin, TX 78724",
    "whatsapp_name": "RathaYatra 2026 Volunteers",
    "whatsapp_link": "https://chat.whatsapp.com/BQKNR4eLV3K6lhNIMOv0Yi",
    "email": "volunteers@rathayatra2026.org",
}

# ═══════════════════════════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════════════════════════
def load_signups():
    if not os.path.exists(SIGNUPS_FILE):
        return []
    try:
        with open(SIGNUPS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_signups(rows):
    with open(SIGNUPS_FILE, "w") as f:
        json.dump(rows, f, indent=2)

def get_event(event_id):
    return next((e for e in EVENTS if e["id"] == event_id), None)

def get_category(event, cat_id):
    if not event:
        return None
    return next((c for c in event["categories"] if c["id"] == cat_id), None)

def get_task(category, task_id):
    if not category:
        return None
    return next((t for t in category["tasks"] if t["id"] == task_id), None)

def make_initials(first, last):
    """Auto-generate initials from first+last name, e.g. 'Manas Mishra' -> 'MM'."""
    a = first.strip()[:1].upper() if first.strip() else "?"
    b = last.strip()[:1].upper() if last.strip() else "?"
    return a + b

def task_slots(event_id, cat_id, task_id):
    """Return list of slot dicts with status: filled/pending/withdrawn/open."""
    event = get_event(event_id)
    cat = get_category(event, cat_id)
    task = get_task(cat, task_id)
    if not task:
        return []
    signups = [s for s in load_signups()
               if s["event_id"] == event_id
               and s["category_id"] == cat_id
               and s["task_id"] == task_id
               and s["status"] in ("filled", "pending", "withdrawn")]
    slots = []
    # Each active signup occupies one slot position
    for s in signups:
        slots.append({
            "status": s["status"],
            "initials": s["initials"],
            "signup_id": s["id"],
            "name": f"{s['first_name']} {s['last_name']}",
        })
    # Pad with open slots up to task's capacity
    while len(slots) < task["slots"]:
        slots.append({"status": "open", "initials": "+", "signup_id": None, "name": "Open slot"})
    return slots

def task_stats(event_id, cat_id, task_id):
    slots = task_slots(event_id, cat_id, task_id)
    filled = sum(1 for s in slots if s["status"] == "filled")
    pending = sum(1 for s in slots if s["status"] == "pending")
    open_count = sum(1 for s in slots if s["status"] == "open")
    total = len(slots)
    return {
        "slots": slots,
        "filled": filled,
        "pending": pending,
        "open": open_count,
        "total": total,
        "pct": int(100 * (filled + pending) / max(1, total)),
    }

def event_stats(event_id):
    """Aggregate stats for an event across all categories and tasks."""
    event = get_event(event_id)
    if not event:
        return None
    filled_total, open_total, task_count, slot_total = 0, 0, 0, 0
    for cat in event["categories"]:
        for task in cat["tasks"]:
            st = task_stats(event_id, cat["id"], task["id"])
            filled_total += st["filled"] + st["pending"]
            open_total += st["open"]
            task_count += 1
            slot_total += st["total"]
    pct = int(100 * filled_total / max(1, slot_total))
    # Urgency label
    if pct >= 80:
        urgency = "almost_full"
    elif pct >= 50:
        urgency = "filling"
    else:
        urgency = "needs_help"
    return {
        "event_id": event_id,
        "filled": filled_total,
        "open": open_total,
        "total": slot_total,
        "pct": pct,
        "task_count": task_count,
        "urgency": urgency,
    }

# ═══════════════════════════════════════════════════════════════════
# CONFIRMATION MESSAGES
# ═══════════════════════════════════════════════════════════════════
def send_email_confirmation(signup, event, category, task):
    subject = f"Signed up: {task['name']} — {event['name']}"
    body = f"""Jai Jagannath, {signup['first_name']}!

Your volunteer slot is confirmed.

YOUR SIGNUP
-----------
Event:      {event['name']}
Date:       {event['date']} ({event['weekday']})
Time:       {event['time']}
Category:   {category['name']}
Task:       {task['name']}
Shift:      {task['time']}
Initials:   {signup['initials']}

VENUE
-----
{CONTACT_INFO['venue']}
{CONTACT_INFO['address']}

WhatsApp group:
{CONTACT_INFO['whatsapp_link']}

Jai Jagannath,
The Ratha Yatra 2026 Committee
"""
    if SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEMultipart()
            msg["From"] = FROM_EMAIL
            msg["To"] = signup["email"]
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            return True, "Email delivered"
        except Exception as e:
            return False, f"Email error: {e}"
    else:
        print("\n" + "=" * 60)
        print("EMAIL CONFIRMATION (Demo — SMTP not configured)")
        print("=" * 60)
        print(f"To: {signup['email']}\nSubject: {subject}\n{body}")
        print("=" * 60 + "\n")
        return True, "email logged to console"

def send_sms_confirmation(signup, event, task):
    body = (f"Jai Jagannath {signup['first_name']}! Signed up: "
            f"{task['name']} at {event['name']} on {event['date']}, "
            f"{task['time']}. Venue: {CONTACT_INFO['venue']}.")
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            client.messages.create(body=body, from_=TWILIO_FROM, to=signup["phone"])
            return True, "SMS delivered"
        except ImportError:
            return False, "twilio not installed"
        except Exception as e:
            return False, f"SMS error: {e}"
    else:
        print("\n" + "=" * 60)
        print("SMS CONFIRMATION (Demo — Twilio not configured)")
        print("=" * 60)
        print(f"To: {signup['phone']}\nMessage: {body}")
        print("=" * 60 + "\n")
        return True, "SMS logged to console"

def send_confirmation(signup, event, category, task):
    eo, em = send_email_confirmation(signup, event, category, task)
    so, sm = send_sms_confirmation(signup, event, task)
    return (eo and so), f"Email: {em} · SMS: {sm}"

# ═══════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════════════════════
# ROUTES — SIGNUP FLOW
# ═══════════════════════════════════════════════════════════════════
@app.route("/")
def home():
    return redirect(url_for("signup_events"))

# Step 1: Choose event
@app.route("/signup")
def signup_events():
    events_with_stats = []
    for e in EVENTS:
        st = event_stats(e["id"])
        events_with_stats.append({**e, "stats": st})
    return render_template("signup_step1.html", active="signup",
                           events=events_with_stats, contact=CONTACT_INFO)

# Step 2: Choose category within an event
@app.route("/signup/<event_id>")
def signup_categories(event_id):
    event = get_event(event_id)
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("signup_events"))
    cats_with_stats = []
    for cat in event["categories"]:
        total, filled = 0, 0
        for task in cat["tasks"]:
            st = task_stats(event_id, cat["id"], task["id"])
            total += st["total"]
            filled += st["filled"] + st["pending"]
        pct = int(100 * filled / max(1, total))
        cats_with_stats.append({**cat, "total": total, "filled": filled, "pct": pct})
    event_with_stats = {**event, "stats": event_stats(event_id)}
    return render_template("signup_step2.html", active="signup",
                           event=event_with_stats, categories=cats_with_stats,
                           contact=CONTACT_INFO)

# Step 3: See task slot view and register for a task
@app.route("/signup/<event_id>/<cat_id>")
def signup_tasks(event_id, cat_id):
    event = get_event(event_id)
    cat = get_category(event, cat_id)
    if not event or not cat:
        flash("Invalid path.", "error")
        return redirect(url_for("signup_events"))
    tasks_with_slots = []
    for task in cat["tasks"]:
        st = task_stats(event_id, cat_id, task["id"])
        tasks_with_slots.append({**task, **st})
    event_with_stats = {**event, "stats": event_stats(event_id)}
    return render_template("signup_step3.html", active="signup",
                           event=event_with_stats, category=cat,
                           tasks=tasks_with_slots, contact=CONTACT_INFO)

# Click a "+" slot → signup form for that specific task
@app.route("/signup/<event_id>/<cat_id>/<task_id>/register", methods=["GET", "POST"])
def signup_form(event_id, cat_id, task_id):
    event = get_event(event_id)
    cat = get_category(event, cat_id)
    task = get_task(cat, task_id)
    if not task:
        flash("Task not found.", "error")
        return redirect(url_for("signup_events"))

    st = task_stats(event_id, cat_id, task_id)
    if st["open"] <= 0:
        flash(f"Sorry — {task['name']} is fully booked.", "error")
        return redirect(url_for("signup_tasks", event_id=event_id, cat_id=cat_id))

    if request.method == "POST":
        data = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "event_id": event_id, "event_name": event["name"],
            "event_date": event["date"],
            "category_id": cat_id, "category_name": cat["name"],
            "task_id": task_id, "task_name": task["name"],
            "task_time": task.get("time", ""),
            "first_name": request.form.get("first_name", "").strip(),
            "last_name": request.form.get("last_name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "status": "filled",  # default to filled on signup
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if not all([data["first_name"], data["last_name"],
                    data["email"], data["phone"]]):
            flash("Please fill in all fields.", "error")
            return render_template("signup_form.html", active="signup",
                                   event=event, category=cat, task=task,
                                   form_data=data, contact=CONTACT_INFO)
        data["initials"] = make_initials(data["first_name"], data["last_name"])
        # Save and confirm
        rows = load_signups()
        rows.append(data)
        save_signups(rows)
        ok, msg = send_confirmation(data, event, cat, task)
        flash(f"✓ Signed up for {task['name']}! {msg}", "success")
        return redirect(url_for("signup_success", sid=data["id"]))

    return render_template("signup_form.html", active="signup",
                           event=event, category=cat, task=task,
                           form_data={}, contact=CONTACT_INFO)

@app.route("/signup/success/<sid>")
def signup_success(sid):
    row = next((r for r in load_signups() if r["id"] == sid), None)
    if not row:
        return redirect(url_for("signup_events"))
    event = get_event(row["event_id"])
    cat = get_category(event, row["category_id"])
    task = get_task(cat, row["task_id"])
    return render_template("signup_success.html", active="signup",
                           row=row, event=event, category=cat, task=task,
                           contact=CONTACT_INFO)

# ═══════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════
@app.route("/statistics")
def statistics():
    signups = load_signups()
    events_with_stats = []
    critical_tasks = []
    for e in EVENTS:
        st = event_stats(e["id"])
        events_with_stats.append({**e, "stats": st})
        for cat in e["categories"]:
            for task in cat["tasks"]:
                ts = task_stats(e["id"], cat["id"], task["id"])
                if ts["pct"] < 50 and ts["open"] > 0:
                    critical_tasks.append({
                        "event_name": e["name"], "event_color": e["color"],
                        "category_name": cat["name"], "task_name": task["name"],
                        "open": ts["open"], "total": ts["total"], "pct": ts["pct"],
                    })
    # Sort critical by most open
    critical_tasks.sort(key=lambda t: -t["open"])
    total_slots = sum(e["stats"]["total"] for e in events_with_stats)
    total_filled = sum(e["stats"]["filled"] for e in events_with_stats)
    return render_template("statistics.html", active="statistics",
                           events=events_with_stats, signups=signups,
                           critical_tasks=critical_tasks,
                           total_slots=total_slots, total_filled=total_filled,
                           total_signups=len([s for s in signups if s["status"] != "withdrawn"]),
                           contact=CONTACT_INFO)

# ═══════════════════════════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════════════════════════
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USERNAME
                and request.form.get("password") == ADMIN_PASSWORD):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Invalid credentials."
    return render_template("admin_login.html", active="admin", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("signup_events"))

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    signups = load_signups()
    events_with_stats = []
    for e in EVENTS:
        st = event_stats(e["id"])
        events_with_stats.append({**e, "stats": st})
    total_slots = sum(e["stats"]["total"] for e in events_with_stats)
    total_filled = sum(e["stats"]["filled"] for e in events_with_stats)
    return render_template("admin_dashboard.html", active="admin",
                           events=events_with_stats, signups=signups,
                           total_slots=total_slots, total_filled=total_filled,
                           total_signups=len([s for s in signups if s["status"] != "withdrawn"]),
                           contact=CONTACT_INFO)

@app.route("/admin/status/<sid>/<new_status>", methods=["POST"])
@admin_required
def admin_change_status(sid, new_status):
    if new_status not in ("filled", "pending", "withdrawn"):
        flash("Invalid status.", "error")
        return redirect(url_for("admin_dashboard"))
    rows = load_signups()
    for r in rows:
        if r["id"] == sid:
            r["status"] = new_status
            break
    save_signups(rows)
    flash("Status updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<sid>", methods=["POST"])
@admin_required
def admin_delete(sid):
    rows = [r for r in load_signups() if r["id"] != sid]
    save_signups(rows)
    flash("Signup deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/export.csv")
@admin_required
def admin_export_csv():
    rows = load_signups()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Event", "Event Date", "Category", "Task", "Shift",
                     "First Name", "Last Name", "Initials", "Email", "Phone",
                     "Status", "Registered"])
    for r in rows:
        writer.writerow([r.get("id", ""), r.get("event_name", ""),
                         r.get("event_date", ""), r.get("category_name", ""),
                         r.get("task_name", ""), r.get("task_time", ""),
                         r.get("first_name", ""), r.get("last_name", ""),
                         r.get("initials", ""), r.get("email", ""),
                         r.get("phone", ""), r.get("status", ""),
                         r.get("timestamp", "")])
    filename = f"ry2026_signups_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@app.route("/api/stats")
def api_stats():
    return jsonify({
        "events": [{**e, "stats": event_stats(e["id"])} for e in EVENTS],
    })

# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
