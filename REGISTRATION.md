# Registration Steps Summary

The Ratha Yatra Volunteer Portal uses a **4-step registration flow**. A volunteer drills down from event → category → task → personal details before being confirmed in a slot.

---

## Step 1 — Pick an RY Event

**Route:** `GET /signup` → `signup_events()` → `templates/signup_step1.html`

The volunteer lands on the Events page and sees a card for each event in the 2026 festival.

| Date | Event | Time |
|---|---|---|
| July 5 (Sunday) | Deva Snana Purnima | 04:30 PM |
| July 17 (Friday) | Netra Utsava | 06:30 PM |
| July 18 (Saturday) | Ratha Yatra | 05:00 PM |
| July 26 (Sunday) | Bahuda Yatra | 10:00 AM |

Each card shows a live progress bar (`% filled`), filled/total slots, and an urgency badge:

- 🟢 `filling` — healthy
- 🟡 `almost_full`
- 🔴 `needs_help`
- ✅ `100% filled`

Clicking a card advances to Step 2.

---

## Step 2 — Pick a Category

**Route:** `GET /signup/<event_id>` → `signup_categories()` → `templates/signup_step2.html`

Within the chosen event, the volunteer sees that event's categories (e.g., the two default categories per event). Each category card shows:

- Category name (color-coded per event)
- Optional date
- Task count
- Fill bar + `filled / total` slots + `% filled`

Clicking a category advances to Step 3.

---

## Step 3 — Pick a Task / Slot

**Route:** `GET /signup/<event_id>/<cat_id>` → `signup_tasks()` → `templates/signup_step3.html`

The volunteer sees every task in the category as a row. Each task lists its individual slots, rendered as colored chips:

| Chip | Meaning |
|---|---|
| 🟢 Green with initials | Filled |
| ⬜ White dashed `+` | Open — clickable to register |
| 🟡 Amber | Pending confirmation |
| 🔴 Pink | Withdrawn |
| ⭐ Gold ring | Coordinator (DRI) |

Per-task stats on the right show `% filled` (color-graded low/mid/high) and `filled · open · total`. Pahandi tasks that are not yet enabled display a **"Coming Soon"** badge and a 🔒 locked state instead of slots.

Clicking an open `+` slot advances to Step 4.

---

## Step 4 — Register (Personal Details)

**Route:** `GET/POST /signup/<event_id>/<cat_id>/<task_id>/register` → `signup_form()` → `templates/signup_form.html`

The volunteer fills in:

- **First name** (required)
- **Last name** (required)
- **Email** (required)

A live preview shows the **initials badge** auto-generated from first + last name (e.g., "Manas Mishra" → `MM`) — this is what will appear in the slot chip after submission.

On submit, the server:

1. Creates a signup record in the database.
2. Sends an email and SMS confirmation (demo mode prints to terminal; production uses SMTP + Twilio).
3. Redirects to the success page.

---

## Confirmation

**Route:** `GET /signup/success/<sid>` → `signup_success()` → `templates/signup_success.html`

The success page shows:

- A green check, the volunteer's name, and where confirmation was sent.
- A recap card with their initials, task name, category, event, date, time, and venue.
- A WhatsApp group invite link.
- Buttons to **sign up for another task**, **withdraw**, or **go back to events**.

Withdrawals post to `/withdraw/<sid>` and flip the slot back to open (chip turns pink/red until reclaimed).

---

## Stepper at a Glance

Every signup template renders the same 4-step progress indicator at the top:

```
[1 RY Event] ─ [2 Category] ─ [3 Task(s)] ─ [4 Register]
```

Completed steps are marked with `✓`, the current step is highlighted, and breadcrumbs above the stepper let the volunteer jump back to any earlier step.

---

## Field Validation & Edge Cases

- All four form fields are required at Step 4; empty submissions re-render the form with the previously entered values preserved (`form_data`).
- If a slot is filled by another volunteer between Steps 3 and 4, the registration fails gracefully and the user is bounced back to the task list.
- Pahandi (chariot pulling) tasks remain locked until the admin toggles them on via `/admin/toggle-pahandi/...`.
- The admin can reassign status (filled / pending / withdrawn), promote a volunteer to **Coordinator (DRI)**, or delete a signup from the admin dashboard.
