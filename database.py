import sqlite3
from typing import List, Dict, Optional


class Database:
    def __init__(self, db_path: str = "intrusion_detection.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        return conn

    def init_db(self):
        conn = self.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    sensor_name TEXT NOT NULL,
                    description TEXT,
                    "from" TEXT DEFAULT 'sensors',
                    card_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Check if description column exists (migration for existing dbs)
            cursor = conn.execute("PRAGMA table_info(events)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'description' not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN description TEXT")
                
            conn.commit()
        finally:
            conn.close()

    def add_event(self, timestamp: str, sensor_name: str, description: str = None, from_source: str = 'sensors', card_name: str = None) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                'INSERT INTO events (timestamp, sensor_name, description, "from", card_name) VALUES (?, ?, ?, ?, ?)',
                (timestamp, sensor_name, description, from_source, card_name)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_all_events(self, limit: Optional[int] = None, from_source: Optional[str] = None) -> List[Dict]:
        conn = self.get_connection()
        try:
            if from_source:
                if limit:
                    cursor = conn.execute(
                        'SELECT timestamp, sensor_name, description, "from", card_name FROM events WHERE "from" = ? ORDER BY timestamp DESC LIMIT ?',
                        (from_source, limit)
                    )
                else:
                    cursor = conn.execute(
                        'SELECT timestamp, sensor_name, description, "from", card_name FROM events WHERE "from" = ? ORDER BY timestamp DESC',
                        (from_source,)
                    )
            else:
                if limit:
                    cursor = conn.execute(
                        'SELECT timestamp, sensor_name, description, "from", card_name FROM events ORDER BY timestamp DESC LIMIT ?',
                        (limit,)
                    )
                else:
                    cursor = conn.execute(
                        'SELECT timestamp, sensor_name, description, "from", card_name FROM events ORDER BY timestamp DESC'
                    )

            events = []
            for row in cursor.fetchall():
                event = {
                    'timestamp': row['timestamp'],
                    'sensor_name': row['sensor_name'],
                    'description': row['description'],
                    'from_source': row['from']
                }
                if row['card_name']:
                    event['card_name'] = row['card_name']
                events.append(event)
            return events
        finally:
            conn.close()

    def get_events_by_sensor(self, sensor_name: str, limit: Optional[int] = None) -> List[Dict]:
        conn = self.get_connection()
        try:
            if limit:
                cursor = conn.execute(
                    'SELECT timestamp, sensor_name, description, "from", card_name FROM events WHERE sensor_name = ? ORDER BY timestamp DESC LIMIT ?',
                    (sensor_name, limit)
                )
            else:
                cursor = conn.execute(
                    'SELECT timestamp, sensor_name, description, "from", card_name FROM events WHERE sensor_name = ? ORDER BY timestamp DESC',
                    (sensor_name,)
                )

            events = []
            for row in cursor.fetchall():
                event = {
                    'timestamp': row['timestamp'],
                    'sensor_name': row['sensor_name'],
                    'description': row['description'],
                    'from_source': row['from']
                }
                if row['card_name']:
                    event['card_name'] = row['card_name']
                events.append(event)
            return events
        finally:
            conn.close()

    def get_event_count(self) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) as count FROM events")
            return cursor.fetchone()['count']
        finally:
            conn.close()

    def clear_all_events(self):
        """Delete all events from the database."""
        conn = self.get_connection()
        try:
            conn.execute("DELETE FROM events")
            conn.commit()
        finally:
            conn.close()


# Global instance for easy usage
db = Database()
