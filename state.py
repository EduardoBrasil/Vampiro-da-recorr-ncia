import copy
import json
import os
import re
import uuid
import datetime as dt
from flask import session
from domain import BANKS, BRAND_RULES, RAW_TRANSACTIONS
from repository import DEFAULT_APP_STATE, UserRepository

DATABASE_FILE = os.path.join(os.path.dirname(__file__), "users.db")
user_repository = UserRepository(DATABASE_FILE)


def now_br():
    return dt.datetime.now().strftime("%d/%m/%Y %H:%M")


def load_users():
    return user_repository.load_all()


def save_users(users):
    user_repository.save_all(users)


def normalize_email(email):
    return email.strip().lower()


def valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)


def start_user_session(email, user):
    session.clear()
    session["user"] = {
        "email": email,
        "name": user["name"],
        "logged_at": now_br(),
    }


def current_email():
    user = session.get("user") or {}
    return user.get("email")


def current_user():
    return session.get("user") or {}


def app_state():
    email = current_email()
    if not email:
        return copy.deepcopy(DEFAULT_APP_STATE)
    return user_repository.app_state(email)


def save_app_state(state):
    email = current_email()
    if email:
        user_repository.save_app_state(email, state)


def reset_app_state(email):
    user_repository.reset_app_state(email)


def bank_by_id(bank_id):
    return next((bank for bank in BANKS if bank["id"] == bank_id), None)


def selected_bank_ids():
    return app_state().get("selected_banks", [])


def connected_banks():
    return app_state().get("connected_banks", [])


def optimized_ids():
    return set(app_state().get("optimized_subscriptions", []))


def failed_banks():
    return set(app_state().get("failed_banks", []))


def revoked_banks():
    return set(app_state().get("revoked_banks", []))


def consent_log():
    return app_state().get("consent_log")


def clean_transaction(tx):
    clean = dict(tx)
    clean["clean_name"] = None
    clean["logo_class"] = "default"
    clean["initial"] = "?"
    if tx["status"] != "processing":
        for pattern, name, logo_class, initial in BRAND_RULES:
            if re.search(pattern, tx["descriptor"], re.I):
                clean["clean_name"] = name
                clean["logo_class"] = logo_class
                clean["initial"] = initial
                break
    return clean


def visible_subscriptions():
    active_banks = {bank["id"] for bank in connected_banks()} - revoked_banks()
    if not active_banks:
        active_banks = set(selected_bank_ids())
    items = []
    for tx in RAW_TRANSACTIONS:
        if tx["bank"] in active_banks and tx["id"] not in optimized_ids():
            clean = clean_transaction(tx)
            bank_info = bank_by_id(tx["bank"])
            if bank_info:
                clean["bank_id"] = tx["bank"]
                clean["bank_name"] = bank_info["name"]
                clean["bank_class"] = bank_info["class"]
                clean["bank_color"] = bank_info.get("color", "#000000")
            items.append(clean)
    return items


def dashboard_totals(items):
    monthly = sum(tx["amount"] for tx in items if tx["status"] != "processing")
    return monthly, monthly * 12


def create_connection(bank_id, days_valid=365):
    bank = bank_by_id(bank_id)
    if not bank:
        return
    state = app_state()
    connected = state.get("connected_banks", [])
    if bank_id in [item["id"] for item in connected]:
        return
    today = dt.datetime.now()
    connected.append({
        "id": bank_id,
        "name": bank["name"],
        "initials": bank["initials"],
        "class": bank["class"],
        "connected_at": today.strftime("%d/%m/%Y"),
        "valid_until": (today + dt.timedelta(days=days_valid)).strftime("%d/%m/%Y"),
        "days_valid": days_valid,
        "status": "active" if days_valid >= 30 else "expiring",
    })
    state["connected_banks"] = connected
    save_app_state(state)


def scan_for_recurring_subscriptions():
    items = visible_subscriptions()
    state = app_state()
    state["last_scan_at"] = now_br()
    state["last_scan_count"] = len(items)
    save_app_state(state)
    return items


def add_push(title, body, sub_id=None, kind="info"):
    state = app_state()
    pushes = state.setdefault("pushes", [])
    pushes.insert(0, {
        "id": f"push_{uuid.uuid4().hex[:8]}",
        "title": title,
        "body": body,
        "subscription_id": sub_id,
        "kind": kind,
        "read": False,
        "created_at": now_br(),
        "fallback": "E-mail agendado se o push for ignorado.",
    })
    state["pushes"] = pushes[:10]
    save_app_state(state)


def ensure_demo_pushes():
    state = app_state()
    if state.get("pushes"):
        return
    add_push("Canva Pro vence em 24h", "Seu teste termina amanha. Evite a cobranca de R$ 89,90.", "sub_004", "trial")
    add_push("Netflix vence em 24h", "Revise a assinatura antes da proxima cobranca.", "sub_001", "billing")
