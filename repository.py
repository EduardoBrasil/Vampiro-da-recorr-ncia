import copy
import json
import os
import sqlite3


DEFAULT_APP_STATE = {
    "selected_banks": [],
    "connected_banks": [],
    "optimized_subscriptions": [],
    "failed_banks": [],
    "revoked_banks": [],
    "consent_log": None,
    "pushes": [],
    "manual_reviews": [],
}


class UserRepository:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._migrate_json_legacy()

    def _ensure_schema(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT,
                    updated_at TEXT,
                    app_state TEXT
                )
                """
            )

    def _migrate_json_legacy(self):
        json_path = os.path.splitext(self.path)[0] + ".json"
        if not os.path.exists(json_path):
            return
        with open(json_path, "r", encoding="utf-8") as file:
            legacy_users = json.load(file)
        if not legacy_users:
            return
        for email, user in legacy_users.items():
            self._upsert_user(email, user)

    def _upsert_user(self, email, user):
        user = self._with_defaults(user)
        app_state_json = json.dumps(user["app_state"], ensure_ascii=False)
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO users (email, name, password_hash, created_at, updated_at, app_state) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    email,
                    user.get("name", ""),
                    user.get("password_hash", ""),
                    user.get("created_at"),
                    user.get("updated_at"),
                    app_state_json,
                ),
            )

    def load_all(self):
        cursor = self.conn.execute("SELECT * FROM users")
        users = {}
        for row in cursor:
            users[row["email"]] = {
                "name": row["name"],
                "password_hash": row["password_hash"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "app_state": json.loads(row["app_state"] or "null") if row["app_state"] else copy.deepcopy(DEFAULT_APP_STATE),
            }
        return users

    def save_all(self, users):
        with self.conn:
            self.conn.execute("DELETE FROM users")
            for email, user in users.items():
                self._upsert_user(email, user)

    def get(self, email):
        row = self.conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return None
        return {
            "name": row["name"],
            "password_hash": row["password_hash"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "app_state": json.loads(row["app_state"] or "null") if row["app_state"] else copy.deepcopy(DEFAULT_APP_STATE),
        }

    def exists(self, email):
        row = self.conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        return row is not None

    def create(self, email, user):
        if self.exists(email):
            raise ValueError("User already exists")
        self._upsert_user(email, user)

    def replace_email(self, old_email, new_email, updates):
        user = self.get(old_email)
        if user is None:
            raise KeyError("Old email not found")
        user.update(updates)
        self.delete(old_email)
        self._upsert_user(new_email, user)

    def update(self, email, updates):
        user = self.get(email)
        if user is None:
            raise KeyError("User not found")
        user.update(updates)
        self._upsert_user(email, user)

    def delete(self, email):
        with self.conn:
            self.conn.execute("DELETE FROM users WHERE email = ?", (email,))

    def app_state(self, email):
        user = self.get(email) or {}
        current_state = copy.deepcopy(DEFAULT_APP_STATE)
        db_state = user.get("app_state")
        if db_state and isinstance(db_state, dict):
            current_state.update(db_state)
        return current_state

    def save_app_state(self, email, state):
        user = self.get(email)
        if user is None:
            return
        user["app_state"] = state
        self._upsert_user(email, user)

    def reset_app_state(self, email):
        self.save_app_state(email, copy.deepcopy(DEFAULT_APP_STATE))

    def _with_defaults(self, user):
        user = dict(user)
        user.setdefault("app_state", copy.deepcopy(DEFAULT_APP_STATE))
        return user
