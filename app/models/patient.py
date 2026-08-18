"""SQLite persistence seam for future patient-management routes."""
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3


@dataclass(frozen=True)
class Patient:
    name: str
    age: int | None = None
    sex: str | None = None
    height: float | None = None
    height_unit: str | None = None
    weight: float | None = None
    weight_unit: str | None = None
    activity_level: str | None = None
    goal: str | None = None
    allergies: str = ""
    dietary_preferences: str = ""
    medical_notes: str = ""
    id: int | None = None


class PatientRepository:
    """Uses parameterised SQL; swap this interface for an ORM/database later."""
    def __init__(self, database_path):
        self.database_path = database_path

    def initialise(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER, sex TEXT,
                height REAL, height_unit TEXT, weight REAL, weight_unit TEXT,
                activity_level TEXT, goal TEXT, allergies TEXT NOT NULL DEFAULT '',
                dietary_preferences TEXT NOT NULL DEFAULT '', medical_notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")

    def create(self, patient: Patient) -> int:
        if not patient.name or len(patient.name.strip()) > 120:
            raise ValueError("Patient name must contain 1–120 characters.")
        now = datetime.now(timezone.utc).isoformat()
        values = tuple(patient.__dict__.values())
        # Explicit ordered values keep personal data out of SQL string interpolation.
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.execute("""INSERT INTO patients
                (name,age,sex,height,height_unit,weight,weight_unit,activity_level,goal,allergies,dietary_preferences,medical_notes,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*values[:12], now, now))
            return cursor.lastrowid
