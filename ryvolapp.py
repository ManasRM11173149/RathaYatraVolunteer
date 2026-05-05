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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ry2026_v2_secret_change_in_production")

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SIGNUPS_FILE = os.path.join(DATA_DIR, "signups.json")
FLAGS_FILE = os.path.join(DATA_DIR, "flags.json")
os.makedirs(DATA_DIR, exist_ok=True)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "RYevent2026")

# Supabase — falls back to local JSON files when not configured
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
_supabase_client = None

def _sb():
    """Return a cached supabase client, or None if env vars are missing."""
    global _supabase_client
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        return None
    if _supabase_client is None:
        try:
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            print(f"[supabase] init failed, falling back to JSON: {e}")
            return None
    return _supabase_client

# Email — Resend (preferred) with SMTP fallback
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
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
    "whatsapp_link": "https://chat.whatsapp.com/HAPnfbZQ1Cf2WlPPzAiwRy?mode=gi_t",
    "email": "volunteers@rathayatra2026.org",
}

# ═══════════════════════════════════════════════════════════════════
# DATA HELPERS — Supabase preferred, JSON file fallback
# ═══════════════════════════════════════════════════════════════════
def _load_signups_json():
    if not os.path.exists(SIGNUPS_FILE):
        return []
    try:
        with open(SIGNUPS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def _save_signups_json(rows):
    with open(SIGNUPS_FILE, "w") as f:
        json.dump(rows, f, indent=2)

def load_signups():
    sb = _sb()
    if sb:
        try:
            res = sb.table("signups").select("*").order("timestamp", desc=False).execute()
            return res.data or []
        except Exception as e:
            print(f"[supabase] load_signups failed, using JSON: {e}")
    return _load_signups_json()

def save_signups(rows):
    """Persist the full signups list. Supabase: diff-based delete + upsert."""
    sb = _sb()
    if sb:
        try:
            existing = sb.table("signups").select("id").execute().data or []
            existing_ids = {r["id"] for r in existing}
            current_ids = {r["id"] for r in rows}
            to_delete = list(existing_ids - current_ids)
            if to_delete:
                sb.table("signups").delete().in_("id", to_delete).execute()
            if rows:
                sb.table("signups").upsert(rows).execute()
            return
        except Exception as e:
            print(f"[supabase] save_signups failed, using JSON: {e}")
    _save_signups_json(rows)

def get_task_toggle_key(event_id, task_id, task_name):
    """Generate a unique toggle key for a specific task (event_id + task_id).
    For Pahandi tasks, this allows per-event/per-variant control."""
    return f"{event_id}_{task_id}_{task_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('→', '')}"

def is_pahandi_task(task_name):
    """Check if a task is a Pahandi variant task."""
    return "pahandi" in task_name.lower()

def _initialize_pahandi_flags():
    """Initialize all Pahandi variant flags to OFF (False)."""
    pahandi_flags = {}
    for event in EVENTS:
        for category in event.get("categories", []):
            for task in category.get("tasks", []):
                if is_pahandi_task(task["name"]):
                    task_key = get_task_toggle_key(event["id"], task["id"], task["name"])
                    pahandi_flags[task_key] = False  # Default to OFF (disabled)
    return pahandi_flags

def _load_flags_json():
    if not os.path.exists(FLAGS_FILE):
        flags = {"events": {e["id"]: True for e in EVENTS}, "tasks": {}}
        _save_flags_json(flags)
        return flags
    try:
        with open(FLAGS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"events": {e["id"]: True for e in EVENTS}, "tasks": {}}

def _save_flags_json(flags):
    with open(FLAGS_FILE, "w") as f:
        json.dump(flags, f, indent=2)

def load_flags():
    """Load event and task flags. Defaults: all events enabled, no task overrides."""
    sb = _sb()
    if sb:
        try:
            res = sb.table("flags").select("*").execute()
            flags = {"events": {e["id"]: True for e in EVENTS}, "tasks": {}}
            for row in (res.data or []):
                bucket = "events" if row.get("kind") == "event" else "tasks"
                flags.setdefault(bucket, {})[row["key"]] = bool(row.get("enabled", True))
            for e in EVENTS:
                flags["events"].setdefault(e["id"], True)
            return flags
        except Exception as e:
            print(f"[supabase] load_flags failed, using JSON: {e}")
    return _load_flags_json()

def save_flags(flags):
    """Persist event and task flags."""
    sb = _sb()
    if sb:
        try:
            rows = []
            for event_id, enabled in flags.get("events", {}).items():
                rows.append({"kind": "event", "key": event_id, "enabled": bool(enabled)})
            for task_key, enabled in flags.get("tasks", {}).items():
                rows.append({"kind": "task", "key": task_key, "enabled": bool(enabled)})
            if rows:
                sb.table("flags").upsert(rows, on_conflict="kind,key").execute()
            return
        except Exception as e:
            print(f"[supabase] save_flags failed, using JSON: {e}")
    _save_flags_json(flags)

def is_event_enabled(event_id):
    """Check if event is enabled."""
    flags = load_flags()
    return flags.get("events", {}).get(event_id, True)

def is_task_enabled(task_name):
    """Check if a specific task is enabled (e.g., 'Pahandi Volunteer')."""
    flags = load_flags()
    # Create a normalized task key by converting to lowercase and replacing spaces with underscores
    task_key = task_name.lower().replace(" ", "_")
    return flags.get("tasks", {}).get(task_key, True)

def is_specific_task_enabled(event_id, task_id, task_name):
    """Check if a specific task variant is enabled (for per-event Pahandi control)."""
    # Only use per-event toggle for Pahandi tasks
    if is_pahandi_task(task_name):
        flags = load_flags()
        task_key = get_task_toggle_key(event_id, task_id, task_name)
        # Pahandi tasks default to False (disabled) unless explicitly enabled
        return flags.get("tasks", {}).get(task_key, False)
    # For non-Pahandi tasks, use regular is_task_enabled
    return is_task_enabled(task_name)

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
Event:      {event.get('name', '')}
Date:       {event.get('date', '')} ({event.get('weekday', '')})
Time:       {event.get('time', '')}
Category:   {category.get('name', '')}
Task:       {task.get('name', '')}
Shift:      {task.get('time', '')}
Initials:   {signup['initials']}

VENUE
-----
{CONTACT_INFO.get('venue', '')}
{CONTACT_INFO.get('address', '')}

WhatsApp group:
{CONTACT_INFO.get('whatsapp_link', '')}

Jai Jagannath,
The Ratha Yatra 2026 Committee
"""
    # Preferred: Resend
    if RESEND_API_KEY:
        try:
            import resend
            resend.api_key = RESEND_API_KEY
            resend.Emails.send({
                "from": FROM_EMAIL,
                "to": [signup["email"]],
                "subject": subject,
                "text": body,
            })
            return True, "Email delivered (Resend)"
        except Exception as e:
            print(f"[resend] send failed, falling back: {e}")

    # Fallback: SMTP
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
            return True, "Email delivered (SMTP)"
        except Exception as e:
            return False, f"Email error: {e}"

    # Last resort: log to console (dev mode)
    print("\n" + "=" * 60)
    print("EMAIL CONFIRMATION (Demo — no email provider configured)")
    print("=" * 60)
    print(f"To: {signup['email']}\nSubject: {subject}\n{body}")
    print("=" * 60 + "\n")
    return True, "email logged to console"

def send_sms_confirmation(signup, event, task):
    if not signup.get("phone"):
        return True, "no phone number provided (skipped)"
    body = (f"Jai Jagannath {signup['first_name']}! Signed up: "
            f"{task.get('name', '')} at {event.get('name', '')} on {event.get('date', '')}, "
            f"{task.get('time', '')}. Venue: {CONTACT_INFO.get('venue', '')}.")
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
            # For API requests, return JSON error instead of redirecting
            if request.is_json or request.path.startswith("/admin/toggle-"):
                return jsonify({"success": False, "error": "Unauthorized"}), 401
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
        task_enabled = is_specific_task_enabled(event_id, task["id"], task["name"])
        tasks_with_slots.append({**task, **st, "is_enabled": task_enabled})
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

    # Check if Pahandi task is enabled
    if is_pahandi_task(task["name"]) and not is_specific_task_enabled(event_id, task_id, task["name"]):
        flash(f"Sorry — {task['name']} is not yet available. Check back soon!", "error")
        return redirect(url_for("signup_tasks", event_id=event_id, cat_id=cat_id))

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
                    data["email"]]):
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
    flags = load_flags()
    events_with_stats = []
    
    # Collect all Pahandi task variants with their toggle status
    pahandi_tasks = []
    
    for e in EVENTS:
        st = event_stats(e["id"])
        is_enabled = flags.get("events", {}).get(e["id"], True)
        event_with_stats = {**e, "stats": st, "enabled": is_enabled}
        
        # Find Pahandi tasks in this event
        for cat in e.get("categories", []):
            for task in cat.get("tasks", []):
                if is_pahandi_task(task["name"]):
                    task_key = get_task_toggle_key(e["id"], task["id"], task["name"])
                    is_pahandi_enabled = flags.get("tasks", {}).get(task_key, False)
                    pahandi_tasks.append({
                        "event_id": e["id"],
                        "event_name": e["name"],
                        "task_id": task["id"],
                        "task_name": task["name"],
                        "task_key": task_key,
                        "enabled": is_pahandi_enabled,
                        "slots": task["slots"]
                    })
        
        events_with_stats.append(event_with_stats)
    
    total_slots = sum(e["stats"]["total"] for e in events_with_stats)
    total_filled = sum(e["stats"]["filled"] for e in events_with_stats)
    return render_template("admin_dashboard.html", active="admin",
                           events=events_with_stats, signups=signups,
                           total_slots=total_slots, total_filled=total_filled,
                           total_signups=len([s for s in signups if s["status"] != "withdrawn"]),
                           contact=CONTACT_INFO, flags=flags, pahandi_tasks=pahandi_tasks)

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

@app.route("/withdraw/<sid>", methods=["POST"])
def withdraw_signup(sid):
    """Allow a volunteer to withdraw their own signup."""
    rows = load_signups()
    signup = None
    for r in rows:
        if r["id"] == sid:
            signup = r
            r["status"] = "withdrawn"
            break
    if not signup:
        flash("Signup not found.", "error")
        return redirect(url_for("signup_events"))
    save_signups(rows)
    flash(f"✓ Successfully withdrawn from {signup['task_name']}.", "success")
    return redirect(url_for("signup_events"))

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

@app.route("/admin/toggle-event", methods=["POST"])
@admin_required
def admin_toggle_event():
    """Toggle enable/disable status for an event."""
    data = request.get_json() or {}
    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"success": False, "error": "Missing event_id"}), 400
    
    flags = load_flags()
    if "events" not in flags:
        flags["events"] = {}
    # Toggle the event flag
    current_state = flags["events"].get(event_id, True)
    flags["events"][event_id] = not current_state
    save_flags(flags)
    return jsonify({"success": True, "event_id": event_id, "enabled": flags["events"][event_id]})

@app.route("/admin/toggle-task", methods=["POST"])
@admin_required
def admin_toggle_task():
    """Toggle enable/disable status for a specific task (e.g., 'Pahandi Volunteer')."""
    data = request.get_json() or {}
    task_name = data.get("task_name")
    if not task_name:
        return jsonify({"success": False, "error": "Missing task_name"}), 400
    
    flags = load_flags()
    if "tasks" not in flags:
        flags["tasks"] = {}
    # Normalize task name
    task_key = task_name.lower().replace(" ", "_")
    # Toggle the task flag
    current_state = flags["tasks"].get(task_key, True)
    flags["tasks"][task_key] = not current_state
    save_flags(flags)
    return jsonify({"success": True, "task_name": task_name, "task_key": task_key, "enabled": flags["tasks"][task_key]})

@app.route("/admin/toggle-pahandi/<event_id>/<task_id>/<task_name>", methods=["POST"])
@admin_required
def admin_toggle_pahandi(event_id, task_id, task_name):
    """Toggle enable/disable status for a specific Pahandi task variant (per-event control)."""
    flags = load_flags()
    if "tasks" not in flags:
        flags["tasks"] = {}
    
    # Generate unique key for this Pahandi variant
    task_key = get_task_toggle_key(event_id, task_id, task_name)
    
    # Toggle the flag
    current_state = flags["tasks"].get(task_key, False)  # Pahandi defaults to OFF
    flags["tasks"][task_key] = not current_state
    save_flags(flags)
    
    return jsonify({
        "success": True,
        "event_id": event_id,
        "task_id": task_id,
        "task_name": task_name,
        "task_key": task_key,
        "enabled": flags["tasks"][task_key]
    })

@app.route("/api/stats")
def api_stats():
    return jsonify({
        "events": [{**e, "stats": event_stats(e["id"])} for e in EVENTS],
    })

# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
