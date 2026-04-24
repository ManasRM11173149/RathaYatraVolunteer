# Ratha Yatra Volunteer Portal (v2)

A Flask web app for the Austin Hindu Temple's Ratha Yatra 2026 festival.
Only **3 tabs**, event-based, with individual task slot signup.

## The 3 Tabs

1. **🙋 Volunteer Signup** — 3-step flow: choose event → choose category → click an open slot → register
2. **📊 Volunteer Statistics** — Live fill rates per event, critical task alerts, recent signups
3. **🔒 Admin Dashboard** — Password-protected. Manage signups, change status (filled/pending/withdrawn), delete, export CSV

## Event Structure

**Event → Category → Task → Slots**

Each event has 2 default categories (rename them later as you decide).
Each category has tasks. Each task has a fixed number of slots.
Each slot shows **initials** auto-generated from the volunteer's first + last name.

Slot colors:
- 🟢 **Green** with initials = filled
- ⬜ **White dashed +** = open (clickable to register)
- 🟡 **Amber** = pending confirmation
- 🔴 **Pink** = withdrawn

## Sacred Dates (from 2026 flier)

| Date | Event | Time |
|---|---|---|
| July 5 (Sunday) | Deva Snana Purnima | 04:30 PM |
| July 17 (Friday) | Netra Utsava | 06:30 PM |
| July 18 (Saturday) | Ratha Yatra | 05:00 PM |
| July 25 (Saturday) | Hera Panchami Rituals | 06:30 PM |
| July 26 (Sunday) | Bahuda Yatra | 10:00 AM |

**Venue:** Austin Hindu Temple · Decker Lake Road, Austin, TX 78724

## Quick Start (Mac)

```bash
unzip RY_2026_v2.zip
cd RY_2026_v2
python3 -m pip install -r requirements.txt
python3 "RY 2026.py"
```

Visit **http://localhost:5000**

⚠️ Remember: quotes around `"RY 2026.py"` because of the space in the filename.

## Admin

- Username: `admin`
- Password: `rathayatra2026`

Change via env vars: `ADMIN_USERNAME`, `ADMIN_PASSWORD`

## Signup Form Fields

- First name (required)
- Last name (required)
- Email (required)
- Phone (required)

That's it. Initials auto-generate from first + last name (e.g., "Manas Mishra" → `MM`).

## Confirmation Messages

Both **email** and **SMS** are sent on every signup.

**Demo mode** (no env vars) → both print to terminal so you can see what would be sent.

**Production:**
```bash
# Email
export SMTP_USER="you@gmail.com"
export SMTP_PASS="your-app-password"
# SMS
pip install twilio
export TWILIO_SID="ACxxx"
export TWILIO_TOKEN="xxx"
export TWILIO_FROM="+15551234567"
```

Jai Jagannath 🚩
