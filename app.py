from datetime import date, datetime
from pathlib import Path
import math
import sqlite3
from flask import Flask, render_template, request, redirect, abort

app = Flask(__name__)
app.config['DATABASE'] = str(Path(__file__).with_name('health.db'))
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS medications (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, dosage TEXT NOT NULL, time TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, exercise TEXT NOT NULL, sets INTEGER NOT NULL, reps INTEGER NOT NULL, weight REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS health_logs (id INTEGER PRIMARY KEY, day TEXT UNIQUE NOT NULL, sleep REAL NOT NULL, water INTEGER NOT NULL, mood TEXT NOT NULL, notes TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS routine_exercises (id INTEGER PRIMARY KEY, weekday INTEGER NOT NULL, exercise TEXT NOT NULL, sets INTEGER NOT NULL, reps INTEGER NOT NULL, weight REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, title TEXT NOT NULL, time TEXT NOT NULL, weekday INTEGER);
        CREATE TABLE IF NOT EXISTS reminder_completions (reminder_id INTEGER NOT NULL, day TEXT NOT NULL, PRIMARY KEY(reminder_id, day));
        ''')
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)')
        if not conn.execute("SELECT 1 FROM schema_migrations WHERE name='water_ounces'").fetchone():
            conn.execute('UPDATE health_logs SET water = water * 8')
            conn.execute("INSERT INTO schema_migrations(name) VALUES('water_ounces')")
        columns = {row['name'] for row in conn.execute('PRAGMA table_info(workouts)')}
        if 'day' not in columns:
            conn.execute('ALTER TABLE workouts ADD COLUMN day TEXT')


@app.context_processor
def shared():
    return dict(days=DAYS, today=date.today().isoformat(), current_day=date.today().weekday())


def text_field(name, limit=200):
    value = request.form.get(name, '').strip()
    if not value or len(value) > limit:
        raise ValueError(f'Please enter {name.replace("_", " ")} (up to {limit} characters).')
    return value


def number(name, low, high, integer=False):
    try:
        value = (int if integer else float)(request.form.get(name, ''))
    except (ValueError, TypeError):
        raise ValueError(f'Please enter a valid {name}.')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name.capitalize()} must be between {low} and {high}.')
    return value


def log_day():
    value = date.fromisoformat(request.form.get('day', date.today().isoformat()))
    if value > date.today():
        raise ValueError('Choose today or a past date for a log.')
    return value.isoformat()


def clock_time():
    value = text_field('time')
    return datetime.strptime(value, '%H:%M').strftime('%H:%M')


@app.errorhandler(ValueError)
def invalid(error):
    return render_template('error.html', message=str(error)), 400


@app.route('/')
def dashboard():
    today = date.today()
    with get_db_connection() as conn:
        health = conn.execute('SELECT * FROM health_logs WHERE day=?', (today.isoformat(),)).fetchone()
        plan = conn.execute('SELECT * FROM routine_exercises WHERE weekday=? ORDER BY id', (today.weekday(),)).fetchall()
        reminders = conn.execute('''SELECT r.*, c.day IS NOT NULL AS done FROM reminders r LEFT JOIN reminder_completions c ON c.reminder_id=r.id AND c.day=? WHERE weekday IS NULL OR weekday=? ORDER BY time''', (today.isoformat(), today.weekday())).fetchall()
        recent = conn.execute('SELECT * FROM workouts ORDER BY day DESC, id DESC LIMIT 5').fetchall()
    return render_template('dashboard.html', health=health, plan=plan, reminders=reminders, recent=recent)


@app.route('/health', methods=['GET', 'POST'])
def health():
    if request.method == 'POST':
        mood = text_field('mood')
        if mood not in ['Great', 'Good', 'Okay', 'Low', 'Rough']:
            raise ValueError('Choose a mood from the list.')
        values = (log_day(), number('sleep', 0, 24), number('water', 0, 800, True), mood, request.form.get('notes', '').strip()[:2000])
        with get_db_connection() as conn:
            conn.execute('''INSERT INTO health_logs(day,sleep,water,mood,notes) VALUES(?,?,?,?,?) ON CONFLICT(day) DO UPDATE SET sleep=excluded.sleep,water=excluded.water,mood=excluded.mood,notes=excluded.notes''', values)
        return redirect('/health')
    with get_db_connection() as conn:
        logs = conn.execute('SELECT * FROM health_logs ORDER BY day DESC').fetchall()
        entry = conn.execute('SELECT * FROM health_logs WHERE day=?', (request.args.get('day', date.today().isoformat()),)).fetchone()
    return render_template('health.html', logs=logs, entry=entry)


@app.route('/medications')
def medications():
    with get_db_connection() as conn:
        rows = conn.execute('SELECT * FROM medications ORDER BY time').fetchall()
    return render_template('medications.html', medications=rows)


@app.route('/add-medication', methods=['POST'])
def add_medication():
    values = (text_field('name'), text_field('dosage'), clock_time())
    with get_db_connection() as conn:
        conn.execute('INSERT INTO medications(name,dosage,time) VALUES(?,?,?)', values)
    return redirect('/medications')


@app.route('/workouts')
def workouts():
    with get_db_connection() as conn:
        logs = conn.execute('SELECT * FROM workouts ORDER BY day DESC,id DESC').fetchall()
        plan = conn.execute('SELECT * FROM routine_exercises ORDER BY weekday,id').fetchall()
    return render_template('workouts.html', workouts=logs, plan=plan)


@app.route('/add-workout', methods=['POST'])
def add_workout():
    values = (text_field('exercise'), number('sets', 1, 100, True), number('reps', 1, 1000, True), number('weight', 0, 2000))
    with get_db_connection() as conn:
        if request.form.get('kind') == 'plan':
            conn.execute('INSERT INTO routine_exercises(exercise,sets,reps,weight,weekday) VALUES(?,?,?,?,?)', (*values, number('weekday', 0, 6, True)))
        else:
            conn.execute('INSERT INTO workouts(exercise,sets,reps,weight,day) VALUES(?,?,?,?,?)', (*values, log_day()))
    return redirect('/workouts')


@app.route('/routine/<int:item_id>/log', methods=['POST'])
def log_routine(item_id):
    day = log_day()
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM routine_exercises WHERE id=?', (item_id,)).fetchone()
        if row is None:
            abort(404)
        conn.execute('INSERT INTO workouts(exercise,sets,reps,weight,day) VALUES(?,?,?,?,?)', (row['exercise'], row['sets'], row['reps'], row['weight'], day))
    return redirect('/workouts')


@app.route('/routine/<int:item_id>/delete', methods=['POST'])
def delete_routine(item_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM routine_exercises WHERE id=?', (item_id,))
    return redirect('/workouts')


@app.route('/reminders', methods=['GET', 'POST'])
def reminders():
    with get_db_connection() as conn:
        if request.method == 'POST':
            weekday = None if request.form.get('weekday') == '' else number('weekday', 0, 6, True)
            conn.execute('INSERT INTO reminders(title,time,weekday) VALUES(?,?,?)', (text_field('title'), clock_time(), weekday))
            return redirect('/reminders')
        rows = conn.execute('SELECT * FROM reminders ORDER BY time').fetchall()
    return render_template('reminders.html', reminders=rows)


@app.route('/reminders/<int:item_id>/toggle', methods=['POST'])
def toggle_reminder(item_id):
    today = date.today()
    with get_db_connection() as conn:
        row = conn.execute('SELECT * FROM reminders WHERE id=?', (item_id,)).fetchone()
        if row is None or row['weekday'] not in (None, today.weekday()):
            abort(404)
        values = (item_id, today.isoformat())
        deleted = conn.execute('DELETE FROM reminder_completions WHERE reminder_id=? AND day=?', values)
        if not deleted.rowcount:
            conn.execute('INSERT INTO reminder_completions VALUES(?,?)', values)
    return redirect('/')


@app.route('/reminders/<int:item_id>/delete', methods=['POST'])
def delete_reminder(item_id):
    with get_db_connection() as conn:
        conn.execute('DELETE FROM reminders WHERE id=?', (item_id,))
        conn.execute('DELETE FROM reminder_completions WHERE reminder_id=?', (item_id,))
    return redirect('/reminders')


init_db()

if __name__ == '__main__':
    app.run(debug=True)
