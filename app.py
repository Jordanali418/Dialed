from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("health.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise TEXT NOT NULL,
            sets INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def dashboard():
    conn = get_db_connection()

    medication_count = conn.execute(
        "SELECT COUNT(*) FROM medications"
    ).fetchone()[0]

    workout_count = conn.execute(
        "SELECT COUNT(*) FROM workouts"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        medication_count=medication_count,
        workout_count=workout_count
    )


@app.route("/medications")
def medications():
    conn = get_db_connection()

    medications = conn.execute(
        "SELECT * FROM medications ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "medications.html",
        medications=medications
    )


@app.route("/add-medication", methods=["POST"])
def add_medication():
    name = request.form["name"]
    dosage = request.form["dosage"]
    time = request.form["time"]

    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO medications (name, dosage, time)
        VALUES (?, ?, ?)
        """,
        (name, dosage, time)
    )

    conn.commit()
    conn.close()

    return redirect("/medications")


@app.route("/workouts")
def workouts():
    conn = get_db_connection()

    workouts = conn.execute(
        "SELECT * FROM workouts ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "workouts.html",
        workouts=workouts
    )


@app.route("/add-workout", methods=["POST"])
def add_workout():
    exercise = request.form["exercise"]
    sets = request.form["sets"]
    reps = request.form["reps"]
    weight = request.form["weight"]

    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO workouts (exercise, sets, reps, weight)
        VALUES (?, ?, ?, ?)
        """,
        (exercise, sets, reps, weight)
    )

    conn.commit()
    conn.close()

    return redirect("/workouts")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)