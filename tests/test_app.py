import os
import tempfile
import unittest
from datetime import date
import sqlite3
from app import app, init_db, get_db_connection


class DialedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, DATABASE=os.path.join(self.temp.name, 'test.db'))
        init_db()
        self.client = app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def test_pages(self):
        for path in ['/', '/health', '/workouts', '/reminders', '/medications']:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_checkin_upsert_and_validation(self):
        data = dict(day=date.today().isoformat(), sleep='7.5', water='8', mood='Good', notes='Feeling good')
        self.assertEqual(self.client.post('/health', data=data).status_code, 302)
        data['water'] = '9'
        self.client.post('/health', data=data)
        with get_db_connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM health_logs').fetchone()[0], 1)
            self.assertEqual(conn.execute('SELECT water FROM health_logs').fetchone()[0], 9)
        data['sleep'] = 'nan'
        self.assertEqual(self.client.post('/health', data=data).status_code, 400)

    def test_weekly_plan_and_log_are_separate(self):
        data = dict(kind='plan', exercise='Squat', sets=3, reps=8, weight=95, weekday=date.today().weekday())
        self.client.post('/add-workout', data=data)
        with get_db_connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workouts').fetchone()[0], 0)
        self.assertIn(b'Squat', self.client.get('/').data)
        self.assertEqual(self.client.post('/routine/1/log').status_code, 302)
        self.client.post('/routine/1/delete')
        with get_db_connection() as conn:
            row = conn.execute('SELECT * FROM workouts').fetchone()
            self.assertEqual(row['day'], date.today().isoformat())
            self.assertEqual(row['exercise'], 'Squat')
        self.assertEqual(self.client.post('/routine/999/log').status_code, 404)

    def test_reminder_schedule_and_daily_completion(self):
        self.client.post('/reminders', data=dict(title='Check in', time='09:00', weekday=''))
        self.client.post('/reminders', data=dict(title='Other day', time='09:00', weekday=(date.today().weekday()+1)%7))
        self.assertNotIn(b'Other day', self.client.get('/').data)
        with get_db_connection() as conn:
            conn.execute("INSERT INTO reminder_completions VALUES(1,'2020-01-01')")
        self.assertIn(b'Mark done', self.client.get('/').data)
        self.client.post('/reminders/1/toggle')
        self.assertIn(b'Done for today', self.client.get('/').data)
        self.client.post('/reminders/1/toggle')
        self.assertNotIn(b'Done for today', self.client.get('/').data)
        self.assertEqual(self.client.post('/reminders/2/toggle').status_code, 404)
        self.client.post('/reminders/1/delete')
        with get_db_connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM reminder_completions').fetchone()[0], 0)

    def test_legacy_migration_preserves_records(self):
        legacy = os.path.join(self.temp.name, 'legacy.db')
        with sqlite3.connect(legacy) as conn:
            conn.execute('CREATE TABLE workouts(id INTEGER PRIMARY KEY, exercise TEXT, sets INTEGER, reps INTEGER, weight REAL)')
            conn.execute("INSERT INTO workouts VALUES(1,'Old squat',3,5,100)")
        app.config['DATABASE'] = legacy
        init_db()
        init_db()
        with get_db_connection() as conn:
            row = conn.execute('SELECT * FROM workouts').fetchone()
            self.assertEqual(row['exercise'], 'Old squat')
            self.assertIsNone(row['day'])
        self.assertIn(b'date unknown', self.client.get('/workouts').data)

    def test_water_ounces_migration_runs_once(self):
        with get_db_connection() as conn:
            conn.execute("DELETE FROM schema_migrations WHERE name='water_ounces'")
            conn.execute("INSERT INTO health_logs(day,sleep,water,mood,notes) VALUES('2020-01-01',8,8,'Good','')")
        init_db()
        init_db()
        with get_db_connection() as conn:
            self.assertEqual(conn.execute('SELECT water FROM health_logs').fetchone()[0], 64)
        self.assertIn(b'64 oz of water', self.client.get('/health').data)
        data = dict(day=date.today().isoformat(), sleep=8, water=120, mood='Good')
        self.assertEqual(self.client.post('/health', data=data).status_code, 302)
        self.assertIn(b'120 oz of water', self.client.get('/health').data)

    def test_invalid_workout_is_not_saved(self):
        response = self.client.post('/add-workout', data=dict(exercise=' ', sets=-1, reps=0, weight=-5))
        self.assertEqual(response.status_code, 400)
        with get_db_connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workouts').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
