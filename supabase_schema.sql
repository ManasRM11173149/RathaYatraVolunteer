-- Ratha Yatra 2026 — Supabase schema
-- Run this once in the Supabase SQL editor (Dashboard → SQL → New query → paste → Run).

-- ---------- signups ----------
create table if not exists public.signups (
    id              text primary key,
    event_id        text not null,
    event_name      text,
    event_date      text,
    category_id     text,
    category_name   text,
    task_id         text,
    task_name       text,
    task_time       text,
    first_name      text,
    last_name       text,
    initials        text,
    email           text,
    phone           text,
    status          text,
    timestamp       text
);

create index if not exists signups_event_idx on public.signups (event_id, category_id, task_id);
create index if not exists signups_status_idx on public.signups (status);

-- ---------- flags ----------
-- kind = 'event' or 'task'; key = event_id or normalized task name
create table if not exists public.flags (
    kind     text not null,
    key      text not null,
    enabled  boolean not null default true,
    primary key (kind, key)
);

-- The Flask app uses the SUPABASE_SERVICE_ROLE_KEY (bypasses RLS).
-- If you ever expose these tables to client-side code, enable RLS and add policies.
