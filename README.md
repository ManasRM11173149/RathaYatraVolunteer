# Austin Ratha Yatra 2026 — Volunteer Portal

A Flask-based volunteer management system for **Austin Ratha Yatra 2026**, a festival celebrating Lord Jagannath, Lord Balabhadra, and Devi Subhadra.

**Three core features:** volunteer signup, live statistics dashboard, and admin management.

---

## 🎯 Quick Overview

| Feature | Description |
|---------|-------------|
| **Volunteer Signup** | 3-step form: select event → select category → choose task slot → register with email & phone |
| **Statistics Dashboard** | Real-time view of slot fill rates, critical task status, and recent registrations per event |
| **Admin Dashboard** | Password-protected management: approve/reject signups, assign coordinators, toggle events/tasks, export CSV |

---

## 🗓️ Event Calendar 2026

| Date | Event | Time | Venue |
|---|---|---|---|
| July 5 (Sun) | **Deva Snana Purnima** | 10:30 AM | Austin Hindu Temple |
| July 17 (Fri) | **Netra Utsava** | 6:30 PM | Austin Hindu Temple |
| July 18 (Sat) | **Ratha Yatra** | 5:00 PM | Austin Hindu Temple |
| July 25 (Sat) | **Hera Panchami Rituals** | (Morning) | Austin Hindu Temple |

**Venue:** Austin Hindu Temple, Decker Lake Road, Austin, TX 78724

---

## 🏗️ Architecture

```
Event → Category → Task → Slots

Each event contains multiple categories (Setup, Ritual, Prasad, etc.)
Each category contains tasks (Flower Arrangement, Pahandi Volunteer, etc.)
Each task has a fixed number of slots
Each slot displays volunteer initials (auto-generated from first+last name)
```

### Slot States & Colors

- 🟢 **Filled** — Green badge with initials
- ⬜ **Open** — White dashed (+) button
- 🟡 **Pending** — Amber badge (awaiting confirmation)
- 🔴 **Withdrawn** — Pink badge (volunteer withdrew)

---

## 🚀 Local Development

### Prerequisites
- Python 3.8+
- pip or conda

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ManasRM11173149/RathaYatraVolunteer.git
   cd RathaYatraVolunteer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally:**
   ```bash
   python ryvolapp.py
   ```
   Visit **http://localhost:8080**

---

## ⚙️ Configuration

### Admin Credentials

Default credentials can be overridden via environment variables:

```bash
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="RYAustin@2026"
```

Or in a `.env` file:
```
ADMIN_USERNAME=admin
ADMIN_PASSWORD=RYAustin@2026
```

### Database

**Local Development:** JSON files (`data/signups.json`, `data/flags.json`)

**Production:** Supabase (optional)
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

When Supabase env vars are missing, the app falls back to JSON storage.

---

## 📧 Email & SMS Notifications

### Email

**Primary:** Resend API (recommended)
```bash
export RESEND_API_KEY="re_xxxxxxxx"
```

**Fallback:** SMTP (Gmail, Office 365, etc.)
```bash
export SMTP_USER="your-email@gmail.com"
export SMTP_PASS="your-app-password"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export FROM_EMAIL="noreply@rathayatra2026.org"
```

### SMS

Uses Twilio (optional):
```bash
export TWILIO_SID="ACxxxxxxxx"
export TWILIO_TOKEN="your-auth-token"
export TWILIO_FROM="+15551234567"
```

**Demo Mode** (no env vars set): Email and SMS content prints to terminal.

---

## 📋 Signup Form Fields

- **First Name** (required)
- **Last Name** (required)
- **Email** (required)
- **Phone** (required)
- **Event** (required)
- **Category** (required)
- **Task & Slot** (required)

Initials auto-generate from first + last name (e.g., "Manas Mishra" → `MM`).

---

## 🔐 Admin Dashboard

Access at **http://localhost:8080/admin**

### Capabilities

| Action | Description |
|--------|-------------|
| **View Signups** | See all registrations with status |
| **Change Status** | Mark as filled, pending, or withdrawn |
| **Assign Coordinator** | Flag key volunteers with ⭐ |
| **Toggle Events** | Enable/disable signup for entire events |
| **Toggle Tasks** | Enable/disable specific tasks (e.g., "Pahandi Volunteer") |
| **Delete Signup** | Remove registrations |
| **Export CSV** | Download all signups with metadata |
| **View Statistics** | Live fill rates and critical task status |

---

## 📊 Volunteer Statistics

Public page at **http://localhost:8080/stats**

Shows:
- Per-event fill rate (filled slots / total slots)
- Critical tasks (marked in dashboard)
- Recent signup activity
- Color-coded event status

---

## 🎫 QR Code Generation

Auto-generated QR codes link to the volunteer signup portal:
- **http://localhost:8080/qr** — Display QR code
- **http://localhost:8080/qr.png** — Download as PNG with caption

Use for fliers, social media, or printed materials.

---

## 📁 Project Structure

```
RathaYatraVolunteer/
├── ryvolapp.py                 # Main Flask application
├── requirements.txt            # Python dependencies
├── data/
│   ├── signups.json           # Volunteer registrations (local storage)
│   └── flags.json             # Event/task toggle states
├── templates/
│   ├── base.html              # Base template
│   ├── signup_*.html          # Multi-step signup forms
│   ├── admin_dashboard.html   # Admin panel
│   ├── statistics.html        # Public statistics view
│   ├── qrcode.html            # QR code display
│   └── admin_login.html       # Login page
├── static/
│   └── AustinRYImage.jpg      # Festival banner image
├── supabase_schema.sql         # Optional Supabase schema
├── Procfile                    # Heroku deployment config
├── README.md                   # This file
└── REGISTRATION.md             # Detailed signup form documentation
```

---

## 🌐 Deployment

### Heroku

1. **Install Heroku CLI** and authenticate:
   ```bash
   heroku login
   ```

2. **Create app:**
   ```bash
   heroku create ratha-yatra-volunteer
   ```

3. **Set environment variables:**
   ```bash
   heroku config:set ADMIN_PASSWORD="secure_password"
   heroku config:set RESEND_API_KEY="re_xxxxx"
   heroku config:set SUPABASE_URL="https://xxxxx.supabase.co"
   heroku config:set SUPABASE_SERVICE_ROLE_KEY="xxxxx"
   ```

4. **Deploy:**
   ```bash
   git push heroku main
   ```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-b", "0.0.0.0:8080", "ryvolapp:app"]
```

Build and run:
```bash
docker build -t ratha-yatra-volunteer .
docker run -p 8080:8080 \
  -e ADMIN_PASSWORD="your_password" \
  -e RESEND_API_KEY="your_key" \
  ratha-yatra-volunteer
```

---

## 📝 Scope & Limitations

This portal is designed for **small-scale, community-based use:**

- **Users:** Less than 10 concurrent users
- **Capacity:** Supports up to 100 total volunteers
- **Storage:** JSON files (local) or Supabase (cloud)
- **Notifications:** Email and SMS to limited audience only
- **Use Case:** Learning, experimentation, and small festivals

For larger-scale events (1000+ volunteers), consider enterprise volunteer management platforms.

---

## 🔧 Customization

### Add/Edit Events

Edit the `EVENTS` list in `ryvolapp.py` (lines 83–266). Each event has:
- `id` — Unique identifier
- `name` — Display name
- `date` & `weekday` — Event date
- `time` — Event start time
- `color`, `light`, `dark` — Brand colors
- `categories` — Nested categories with tasks

### Modify Admin Password

```bash
export ADMIN_PASSWORD="MyNewPassword@2026"
```

### Change From Email

```bash
export FROM_EMAIL="custom-email@domain.org"
```

---

## 🆘 Troubleshooting

### Email Not Sending

- **Check env vars:** Ensure `SMTP_USER`, `SMTP_PASS`, and `FROM_EMAIL` are set
- **App Password:** Gmail requires an [app-specific password](https://support.google.com/accounts/answer/185833), not your regular password
- **Demo mode:** If no env vars are set, emails print to terminal

### QR Code Not Loading

- Ensure `qrcode[pil]` is installed: `pip install qrcode[pil]`
- Verify the app is running on the correct port (default: 8080)

### Admin Login Fails

- Default credentials: Username `admin`, Password `RYAustin@2026`
- Check env var overrides: `echo $ADMIN_PASSWORD`

### Signups Not Persisting

- JSON files must be in `data/` directory (auto-created)
- Check file permissions: `data/signups.json` should be readable/writable
- For production, use Supabase instead of JSON

---

## 📚 Additional Resources

- **Event Details:** See `REGISTRATION.md` for signup flow and form validation
- **Supabase Schema:** See `supabase_schema.sql` for database structure
- **Flask Docs:** https://flask.palletsprojects.com/
- **Resend Email API:** https://resend.com/docs
- **Twilio SMS:** https://www.twilio.com/docs/sms

---

## 🙏 Acknowledgments

Built for the Austin Hindu Temple community.

**Jai Jagannath 🚩**
