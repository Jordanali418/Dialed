# Dialed

Dialed is a health and fitness tracking web application built with Python, Flask, SQLite, HTML, and CSS. The goal is to create one place for users to manage medications, workouts, daily health habits, and long-term progress.

## Current Features

- Daily overview with sleep, hydration, mood, today's workout, and reminders
- Daily health check-ins with dated history and editable notes
- Reusable Monday–Sunday exercise plans with sets, reps, and weight
- Record planned exercises as completed, or log an exercise separately
- Dated workout history; existing entries retain their original data and show an unknown date
- Daily or weekly in-app reminders with per-day completion and undo
- Medication schedule tracking
- Responsive layout and server-side input validation
- Persistent SQLite storage with automatic, additive schema migration

## Reminder behavior

Reminders appear on the overview on their scheduled day, ordered by the entered time. Completion resets for each new date. This version does not deliver push, email, or background notifications. Dates follow the local time of the computer running the app. Medication schedules are tracked separately; add a reminder if you want a corresponding daily checklist item.

## Planned Features

- Push notifications and user-specific time zones
- Workout plan editing, cardio tracking, and progress charts
- User registration and private per-user accounts
- Medication completion tracking

This version is a local, single-user app; it has no account isolation and is not ready for public hosting.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Tests cover health-log updates, validation, weekday plans, dated workout logging, daily reminder completion, and preservation of legacy workout data.

## Tech Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- Git/GitHub

## Run Locally

1. Clone the repository:

```bash
git clone https://github.com/Jordanali418/Dialed.git
```

2. Enter the project folder:

```bash
cd Dialed
```

3. Create a virtual environment:

```bash
python3 -m venv .venv
```

4. Activate the virtual environment on macOS/Linux:

```bash
source .venv/bin/activate
```

5. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

6. Start the application:

```bash
python3 app.py
```

7. Open in your browser:

```text
http://127.0.0.1:5000
```

## Project Status

Dialed is currently in active development. New features are being added incrementally as the project grows.