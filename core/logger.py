import sqlite3
import json
from datetime import datetime
from pathlib import Path

class Logger:
    def __init__(self, db_path="logs/agent_logs.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_input TEXT,
                route TEXT,
                execution_result TEXT,
                iterations INTEGER,
                duration_seconds REAL,
                cost_rub REAL,
                success INTEGER
            )
        """)
        self.conn.commit()
    
    def log_request(self, user_input, route, execution_result, iterations, duration, cost, success):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO requests (timestamp, user_input, route, execution_result, iterations, duration_seconds, cost_rub, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            user_input,
            route,
            execution_result[:500],
            iterations,
            duration,
            cost,
            1 if success else 0
        ))
        self.conn.commit()
    
    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                AVG(iterations) as avg_iterations,
                AVG(duration_seconds) as avg_duration,
                SUM(cost_rub) as total_cost
            FROM requests
        """)
        return cursor.fetchone()

logger = Logger()
