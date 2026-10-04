"""Database classes for the Online Voting System.

Database opens MySQL connections and runs parameterized queries.
The other classes each handle the SQL for one table, so app.py
contains routing and validation but no SQL.
"""
import os

import mysql.connector


class Database:
    """Opens a MySQL connection for each query and closes it afterwards."""

    def _config(self):
        # Read at call time so the values from .env are already loaded.
        return {
            "host": os.environ.get("MYSQL_HOST", "localhost"),
            "port": int(os.environ.get("MYSQL_PORT", "3306")),
            "user": os.environ.get("MYSQL_USER", ""),
            "password": os.environ.get("MYSQL_PASSWORD", ""),
            "database": os.environ.get("MYSQL_DATABASE", "voting_system"),
        }

    def connect(self):
        return mysql.connector.connect(**self._config())

    def fetch_one(self, sql, params=()):
        """Return the first row as a dictionary, or None."""
        connection = self.connect()
        try:
            cursor = connection.cursor(dictionary=True, buffered=True)
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            connection.close()

    def fetch_all(self, sql, params=()):
        """Return all rows as a list of dictionaries."""
        connection = self.connect()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            connection.close()

    def execute(self, sql, params=()):
        """Run an INSERT, UPDATE or DELETE and commit it."""
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()
            return cursor.rowcount
        finally:
            connection.close()


class UserModel:
    """Voter records (users table)."""

    def __init__(self, db):
        self.db = db

    def create(self, full_name, username, email, password_hash):
        self.db.execute(
            "INSERT INTO users (full_name, username, email, password_hash) "
            "VALUES (%s, %s, %s, %s)",
            (full_name, username, email, password_hash),
        )

    def find_by_login(self, login):
        """Find a voter by username or email."""
        return self.db.fetch_one(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (login, login),
        )

    def find_by_id(self, user_id):
        return self.db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))

    def find_duplicates(self, username, email):
        return self.db.fetch_all(
            "SELECT username, email FROM users WHERE username = %s OR email = %s",
            (username, email),
        )

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS total FROM users")
        return row["total"]


class AdminModel:
    """Administrator accounts (admins table)."""

    def __init__(self, db):
        self.db = db

    def create(self, username, password_hash):
        self.db.execute(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
            (username, password_hash),
        )

    def find_by_username(self, username):
        return self.db.fetch_one(
            "SELECT * FROM admins WHERE username = %s", (username,)
        )


class CandidateModel:
    """Candidate records (candidates table)."""

    def __init__(self, db):
        self.db = db

    def get_all(self):
        return self.db.fetch_all("SELECT * FROM candidates ORDER BY name")

    def find(self, candidate_id):
        return self.db.fetch_one(
            "SELECT * FROM candidates WHERE id = %s", (candidate_id,)
        )

    def create(self, name, party, description):
        self.db.execute(
            "INSERT INTO candidates (name, party, description) VALUES (%s, %s, %s)",
            (name, party, description),
        )

    def update(self, candidate_id, name, party, description):
        self.db.execute(
            "UPDATE candidates SET name = %s, party = %s, description = %s "
            "WHERE id = %s",
            (name, party, description, candidate_id),
        )

    def delete(self, candidate_id):
        self.db.execute("DELETE FROM candidates WHERE id = %s", (candidate_id,))

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS total FROM candidates")
        return row["total"]


class VoteModel:
    """Votes (votes table). One row per voter, enforced by a UNIQUE key."""

    def __init__(self, db):
        self.db = db

    def cast(self, user_id, candidate_id):
        """Store a vote. MySQL raises a duplicate-entry error on a second vote."""
        self.db.execute(
            "INSERT INTO votes (user_id, candidate_id) VALUES (%s, %s)",
            (user_id, candidate_id),
        )

    def get_vote(self, user_id):
        """Return the voter's vote row, or None if they have not voted."""
        return self.db.fetch_one(
            "SELECT id, voted_at FROM votes WHERE user_id = %s", (user_id,)
        )

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS total FROM votes")
        return row["total"]

    def results(self):
        """Vote count for every candidate, including candidates with zero votes."""
        return self.db.fetch_all(
            "SELECT c.id, c.name, c.party, COUNT(v.id) AS vote_count "
            "FROM candidates c "
            "LEFT JOIN votes v ON v.candidate_id = c.id "
            "GROUP BY c.id, c.name, c.party "
            "ORDER BY vote_count DESC, c.name"
        )
