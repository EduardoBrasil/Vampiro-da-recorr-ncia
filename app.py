from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from domain import TERMS_VERSION, BANKS, BRAND_RULES, RAW_TRANSACTIONS
from services.open_finance import create_open_finance_provider
import os
import re
import uuid

import state

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vampiro-secret-dev-key-2026")

OPEN_FINANCE_PROVIDER = os.environ.get("OPEN_FINANCE_PROVIDER", "mock")
OPEN_FINANCE_BASE_URL = os.environ.get("OPEN_FINANCE_BASE_URL", "")
OPEN_FINANCE_TOKEN = os.environ.get("OPEN_FINANCE_TOKEN", "")
open_finance_provider = create_open_finance_provider(
    OPEN_FINANCE_PROVIDER,
    base_url=OPEN_FINANCE_BASE_URL,
    token=OPEN_FINANCE_TOKEN,
)

PUBLIC_ENDPOINTS = {
    "login",
    "register",
    "static",
}


def money(value):
    return f"R$ {value:.2f}".replace(".", ",")


@app.template_filter("money")
def money_filter(value):
    return money(float(value))


def load_users():
    return state.load_users()


def save_users(users):
    return state.save_users(users)


def normalize_email(email):
    return state.normalize_email(email)


def valid_email(email):
    return state.valid_email(email)


def start_user_session(email, user):
    return state.start_user_session(email, user)


def current_email():
    return state.current_email()


def current_user():
    return state.current_user()


def app_state():
    return state.app_state()


def save_app_state(state_data):
    return state.save_app_state(state_data)


def now_br():
    return state.now_br()


def bank_by_id(bank_id):
    return state.bank_by_id(bank_id)


def selected_bank_ids():
    return state.selected_bank_ids()


def connected_banks():
    return state.connected_banks()


def optimized_ids():
    return state.optimized_ids()


def failed_banks():
    return state.failed_banks()


def revoked_banks():
    return state.revoked_banks()


def consent_log():
    return state.consent_log()


def visible_subscriptions():
    return state.visible_subscriptions()


def dashboard_totals(items):
    return state.dashboard_totals(items)


def create_connection(bank_id, days_valid=365):
    return state.create_connection(bank_id, days_valid)


def scan_for_recurring_subscriptions():
    return state.scan_for_recurring_subscriptions()


def add_push(title, body, sub_id=None, kind="info"):
    return state.add_push(title, body, sub_id, kind)


def ensure_demo_pushes():
    return state.ensure_demo_pushes()


@app.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return
    if not session.get("user"):
        return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    next_url = request.args.get("next") or url_for("index")
    if request.method == "POST":
        email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "").strip()
        next_url = request.form.get("next") or url_for("index")
        users = load_users()
        user = users.get(email)
        if not valid_email(email):
            error = "Digite um e-mail valido para entrar."
        elif not user or not check_password_hash(user["password_hash"], password):
            error = "E-mail ou senha incorretos."
        else:
            start_user_session(email, user)
            return redirect(next_url)
    registered = request.args.get("registered") == "1"
    return render_template("login.html", error=error, next_url=next_url, registered=registered)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    form = {"name": "", "email": ""}
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        form = {"name": name, "email": email}
        users = load_users()
        if len(name) < 2:
            error = "Informe seu nome."
        elif not valid_email(email):
            error = "Digite um e-mail valido."
        elif email in users:
            error = "Este e-mail ja possui cadastro."
        elif len(password) < 8:
            error = "A senha precisa ter pelo menos 8 caracteres."
        elif password != confirm:
            error = "As senhas nao conferem."
        else:
            state.user_repository.create(email, {
                "name": name,
                "password_hash": generate_password_hash(password),
                "created_at": now_br(),
                "updated_at": now_br(),
            })
            return redirect(url_for("login", registered=1))
    return render_template("register.html", error=error, form=form)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if not consent_log():
        return redirect(url_for("onboarding"))
    if not connected_banks():
        return redirect(url_for("auth"))
    return redirect(url_for("dashboard"))


@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if request.method == "POST":
        selected = request.form.getlist("banks")[:5]
        if not selected:
            return render_template("onboarding.html", banks=BANKS, error="Selecione ao menos um banco.", terms_version=TERMS_VERSION)
        if request.form.get("network") == "offline":
            return render_template("onboarding.html", banks=BANKS, error="Sem internet. Verifique sua conexao e tente novamente.", terms_version=TERMS_VERSION, selected=selected)
        state = app_state()
        state["selected_banks"] = selected
        state["consent_log"] = {
            "timestamp": now_br(),
            "terms_version": TERMS_VERSION,
            "banks": selected,
        }
        save_app_state(state)
        return redirect(url_for("auth"))
    return render_template("onboarding.html", banks=BANKS, terms_version=TERMS_VERSION, selected=selected_bank_ids())


@app.route("/connect")
def connect():
    return redirect(url_for("onboarding"))


@app.route("/auth")
def auth():
    if not consent_log():
        return redirect(url_for("onboarding"))
    selected = selected_bank_ids()
    if not selected:
        return redirect(url_for("onboarding"))
    selected_banks = [bank_by_id(bank_id) for bank_id in selected if bank_by_id(bank_id)]
    return render_template("auth.html", banks=selected_banks, consent=consent_log())


@app.route("/auth/collect-cpf", methods=["GET", "POST"])
def auth_collect_cpf():
    """Step 1: Request user's CPF/CNPJ"""
    if not consent_log():
        return redirect(url_for("onboarding"))
    
    state = app_state()
    if request.method == "GET" and "user_cpf_cnpj" in state:
        selected = selected_bank_ids()
        if selected:
            return redirect(url_for("auth_review_consent", bank_id=selected[0]))

    if request.method == "POST":
        cpf_cnpj = request.form.get("cpf_cnpj", "").strip()
        cpf_cnpj_clean = re.sub(r"\D", "", cpf_cnpj)
        
        if not cpf_cnpj_clean or len(cpf_cnpj_clean) < 11:
            return render_template(
                "auth_cpf.html",
                selected_banks=[bank_by_id(bid) for bid in selected_bank_ids() if bank_by_id(bid)],
                error="CPF/CNPJ inválido. Informe um valor com 11 ou 14 dígitos.",
            )
        


@app.route("/auth/review-consent/<bank_id>")
def auth_review_consent(bank_id):
    """Step 2-3: Review consent details before redirecting to bank"""
    if not consent_log() or "user_cpf_cnpj" not in app_state():
        return redirect(url_for("auth_collect_cpf"))
    
    bank = bank_by_id(bank_id)
    if not bank:
        return redirect(url_for("onboarding"))
    
    return render_template(
        "auth_review.html",
        bank=bank,
        cpf_cnpj=app_state()["user_cpf_cnpj"],
        consent_validity_days=12 * 30,
    )


@app.route("/mock-bank/<bank_id>")
def mock_bank_authorize(bank_id):
    bank = bank_by_id(bank_id)
    consent_id = request.args.get("consentId")
    cpf_cnpj = request.args.get("cpf", "mock")
    if not bank or not consent_id:
        return redirect(url_for("onboarding"))

    callback_url = url_for("auth_callback", bank_id=bank_id, _external=True)
    return render_template(
        "mock_bank_authorize.html",
        bank=bank,
        consent_id=consent_id,
        cpf_cnpj=cpf_cnpj,
        callback_url=f"{callback_url}?consentId={consent_id}",
    )


@app.route("/auth/confirm-consent/<bank_id>", methods=["POST"])
def auth_confirm_consent(bank_id):
    """Step 2-3 continuation: Create consent and redirect to bank authorization"""
    state = app_state()
    if "user_cpf_cnpj" not in state:
        return redirect(url_for("auth_collect_cpf"))
    
    bank = bank_by_id(bank_id)
    if not bank:
        return redirect(url_for("onboarding"))
    
    # Create the digitally signed consent request
    consent_response = open_finance_provider.create_consent(bank_id, cpf_cnpj=state["user_cpf_cnpj"])
    consent_id = consent_response.get("consent_id")
    deep_link = consent_response.get("deep_link") or f"bankapp://{bank_id}/oauth/{consent_id}"
    
    # Save consent metadata (step 2)
    consents = state.get("oauth_consents", {})
    consents[bank_id] = {
        "consent_id": consent_id,
        "bank_id": bank_id,
        "cpf_cnpj": state["user_cpf_cnpj"],
        "status": "AWAITING_AUTHORISATION",
        "created_at": now_br(),
        "provider": open_finance_provider.name,
    }
    state["oauth_consents"] = consents
    save_app_state(state)
    
    # Redirect to bank authentication (step 3)
    return redirect(deep_link)


@app.route("/auth/callback/<bank_id>")
def auth_callback(bank_id):
    """Step 5: Handle secure callback from bank with access token"""
    state = app_state()
    
    # Get callback parameters from bank
    consent_id = request.args.get("consentId")
    access_token = request.args.get("accessToken")
    error = request.args.get("error")
    
    # Handle errors from bank
    if error:
        state["oauth_consents"][bank_id]["status"] = "REJECTED"
        save_app_state(state)
        add_push(
            "Autorização rejeitada",
            f"A autorização no {bank_by_id(bank_id)['name']} foi rejeitada ou expirou.",
            None,
            "warning",
        )
        return redirect(url_for("connection_error", bank_id=bank_id))
    
    # Verify consent status with provider (step 5 - get token)
    if consent_id and access_token:
        consents = state.get("oauth_consents", {})
        if bank_id in consents:
            # Save the access token securely (step 5)
            consents[bank_id]["consent_id"] = consent_id
            consents[bank_id]["access_token"] = access_token
            consents[bank_id]["status"] = "AUTHORISED"
            consents[bank_id]["authorized_at"] = now_br()
            state["oauth_consents"] = consents
            save_app_state(state)
            
            # Create connection with the token
            create_connection(bank_id)
            add_push(
                "Banco conectado com sucesso",
                f"{bank_by_id(bank_id)['name']} foi autorizado para compartilhar seus dados.",
                None,
                "success",
            )
            
            # Check if there are more banks to authorize
            selected = selected_bank_ids()
            authorized = [bid for bid, c in consents.items() if c.get("status") == "AUTHORISED"]
            pending = [bid for bid in selected if bid not in authorized and bid != bank_id]
            
            if pending:
                # Redirect to next bank authorization
                return redirect(url_for("auth_review_consent", bank_id=pending[0]))
            else:
                # All banks authorized, proceed to processing
                ensure_demo_pushes()
                return redirect(url_for("processing"))
    
    # Token not received or invalid
    add_push(
        "Erro na autorização",
        "Não conseguimos obter o token de acesso. Tente novamente.",
        None,
        "error",
    )
    return redirect(url_for("connection_error", bank_id=bank_id))


@app.route("/auth/start", methods=["POST"])
def auth_start():
    """Legacy route: Redirect to new CPF/CNPJ collection flow"""
    return redirect(url_for("auth_collect_cpf"))


@app.route("/connect/callback/<bank_id>")
def connect_callback(bank_id):
    create_connection(bank_id)
    ensure_demo_pushes()
    return redirect(url_for("processing"))


@app.route("/connect/simulate/<bank_id>")
def simulate_connect(bank_id):
    return redirect(url_for("connect_callback", bank_id=bank_id))


@app.route("/error/<bank_id>")
def connection_error(bank_id):
    bank = bank_by_id(bank_id) or BANKS[0]
    return render_template("error.html", bank=bank)


@app.route("/retry/<bank_id>", methods=["POST"])
def retry_connection(bank_id):
    state = app_state()
    failed = failed_banks()
    failed.discard(bank_id)
    state["failed_banks"] = list(failed)
    save_app_state(state)
    create_connection(bank_id)
    ensure_demo_pushes()
    return redirect(url_for("processing"))


@app.route("/processing")
def processing():
    return render_template("processing.html")


@app.route("/dashboard")
def dashboard():
    if not consent_log():
        return redirect(url_for("onboarding"))
    if not connected_banks() and not failed_banks():
        return redirect(url_for("auth"))
    items = visible_subscriptions()
    monthly, annual = dashboard_totals(items)

    ensure_demo_pushes()
    state = app_state()
    saved_monthly = sum(abs(tx["amount"]) for tx in RAW_TRANSACTIONS if tx["id"] in optimized_ids())
    saved_annual = round(saved_monthly * 12, 2)
    dashboard_pushes = [
        push for push in state.get("pushes", [])
        if not push.get("read") and push["title"] != "Autorização revogada"
    ]
    return render_template(
        "dashboard.html",
        subscriptions=items,
        total_monthly=monthly,
        total_annual=annual,
        connected_banks=connected_banks(),
        failed_banks=failed_banks(),
        revoked_banks=revoked_banks(),
        pushes=dashboard_pushes,
        optimized_count=len(optimized_ids()),
        saved_monthly=saved_monthly,
        saved_annual=saved_annual,
        last_scan_at=state.get("last_scan_at"),
        last_scan_count=state.get("last_scan_count"),
    )


@app.route("/subscription/<sub_id>")
def subscription_detail(sub_id):
    tx = next((item for item in RAW_TRANSACTIONS if item["id"] == sub_id), None)
    if not tx:
        return redirect(url_for("dashboard"))
    sub = clean_transaction(tx)
    sheet = request.args.get("sheet")
    link_error = request.args.get("link_error") == "1"
    saved_monthly = request.args.get("saved_monthly")
    saved_annual = request.args.get("saved_annual")
    try:
        saved_monthly = float(saved_monthly) if saved_monthly is not None else None
    except (TypeError, ValueError):
        saved_monthly = None
    try:
        saved_annual = float(saved_annual) if saved_annual is not None else None
    except (TypeError, ValueError):
        saved_annual = None
    return render_template(
        "detail.html",
        sub=sub,
        sheet=sheet,
        link_error=link_error,
        saved_monthly=saved_monthly,
        saved_annual=saved_annual,
    )


@app.route("/subscription/<sub_id>/optimize", methods=["POST"])
def optimize_subscription(sub_id):
    state = app_state()
    optimized = optimized_ids()
    optimized.add(sub_id)
    state["optimized_subscriptions"] = list(optimized)
    save_app_state(state)
    tx = next((item for item in RAW_TRANSACTIONS if item["id"] == sub_id), None)
    monthly_saved = abs(tx["amount"]) if tx else 0
    annual_saved = monthly_saved * 12
    add_push(
        "Gasto removido",
        f"Você economizou R$ {monthly_saved:.2f} por mês e R$ {annual_saved:.2f} por ano com essa recorrência.",
        sub_id,
        "success",
    )
    return redirect(
        url_for(
            "subscription_detail",
            sub_id=sub_id,
            sheet="success",
            saved_monthly=monthly_saved,
            saved_annual=annual_saved,
        )
    )


@app.route("/subscription/<sub_id>/external")
def external_cancel(sub_id):
    tx = next((item for item in RAW_TRANSACTIONS if item["id"] == sub_id), None)
    if not tx:
        return redirect(url_for("dashboard"))
    if tx["cancel_url"] == "broken":
        return redirect(url_for("subscription_detail", sub_id=sub_id, sheet="cancel", link_error=1))
    return redirect(tx["cancel_url"])


@app.route("/manual/<sub_id>", methods=["GET", "POST"])
def manual_review(sub_id):
    tx = next((item for item in RAW_TRANSACTIONS if item["id"] == sub_id), None)
    if not tx:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        state = app_state()
        reviews = state.get("manual_reviews", [])
        reviews.append({
            "subscription_id": sub_id,
            "suggested_name": request.form.get("service_name", "").strip(),
            "points": 120,
            "submitted_at": now_br(),
        })
        state["manual_reviews"] = reviews
        save_app_state(state)
        add_push("Obrigado pela ajuda", "Voce ganhou 120 pontos de fidelidade pela identificacao.", sub_id, "success")
        return redirect(url_for("dashboard"))
    return render_template("manual.html", sub=clean_transaction(tx))


@app.route("/connections")
def connections():
    connected_ids = {bank["id"] for bank in connected_banks()}
    available_banks = [bank for bank in BANKS if bank["id"] not in connected_ids]
    return render_template(
        "connections.html",
        connected_banks=connected_banks(),
        failed_banks=failed_banks(),
        available_banks=available_banks,
        consent=consent_log(),
    )


@app.route("/connections/add", methods=["POST"])
def connections_add():
    bank_ids = request.form.getlist("banks")[:5]
    if not bank_ids:
        add_push("Sem banco selecionado", "Selecione ao menos um banco para conectar e buscar novas recorrências.", None, "warning")
        return redirect(url_for("connections"))

    state = app_state()
    state["selected_banks"] = bank_ids
    state["consent_log"] = {
        "timestamp": now_br(),
        "terms_version": TERMS_VERSION,
        "banks": bank_ids,
    }
    save_app_state(state)

    if "user_cpf_cnpj" in state:
        return redirect(url_for("auth_review_consent", bank_id=bank_ids[0]))
    return redirect(url_for("auth_collect_cpf"))


@app.route("/connections/revoke/<bank_id>", methods=["POST"])
def revoke_connection(bank_id):
    state = app_state()
    connected = [item for item in connected_banks() if item["id"] != bank_id]
    state["connected_banks"] = connected
    revoked = revoked_banks()
    revoked.add(bank_id)
    state["revoked_banks"] = list(revoked)
    if state.get("oauth_consents") and bank_id in state["oauth_consents"]:
        state["oauth_consents"].pop(bank_id, None)
    save_app_state(state)
    bank = bank_by_id(bank_id)
    bank_name = bank["name"] if bank else "O banco"
    add_push("Autorização revogada", f"A autorização do {bank_name} foi revogada. Você pode adicionar o banco novamente em Conexões.", None, "warning")
    return redirect(url_for("connections"))


@app.route("/connections/reauthorize/<bank_id>", methods=["POST"])
def reauthorize_connection(bank_id):
    state = app_state()
    connected = [item for item in connected_banks() if item["id"] != bank_id]
    state["connected_banks"] = connected
    revoked = revoked_banks()
    revoked.discard(bank_id)
    state["revoked_banks"] = list(revoked)
    state["selected_banks"] = [bank_id]
    state["consent_log"] = {
        "timestamp": now_br(),
        "terms_version": TERMS_VERSION,
        "banks": [bank_id],
    }
    save_app_state(state)
    return redirect(url_for("auth_collect_cpf"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    current_user = session.get("user", {})
    stored_user = state.user_repository.get(current_user.get("email", "")) or {}
    profile_data = {
        "name": stored_user.get("name", current_user.get("name", "")),
        "email": current_user.get("email", ""),
        "updated_at": stored_user.get("updated_at"),
    }
    error = None
    saved = False
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = normalize_email(request.form.get("email", ""))
        users = load_users()
        old_email = current_user.get("email")
        if not valid_email(email):
            error = "E-mail mal formatado. Corrija para salvar."
        elif email != old_email and email in users:
            error = "Este e-mail ja esta em uso."
        else:
            profile_data = {"name": name, "email": email, "updated_at": now_br()}
            if old_email in users and email != old_email:
                state.user_repository.replace_email(old_email, email, {"name": name, "updated_at": profile_data["updated_at"]})
            elif old_email in users:
                state.user_repository.update(old_email, {"name": name, "updated_at": profile_data["updated_at"]})
            session["user"] = {"email": email, "name": name, "logged_at": current_user.get("logged_at", now_br())}
            saved = True
    return render_template("profile.html", profile=profile_data, error=error, saved=saved)


@app.route("/notifications")
def notifications():
    ensure_demo_pushes()
    state = app_state()
    pushes = [push for push in state.get("pushes", []) if not push.get("read")]
    return render_template("notifications.html", pushes=pushes)


@app.route("/notifications/<push_id>/read", methods=["POST"])
def read_notification(push_id):
    state = app_state()
    pushes = state.get("pushes", [])
    for push in pushes:
        if push["id"] == push_id:
            push["read"] = True
    state["pushes"] = pushes
    save_app_state(state)
    return redirect(url_for("notifications"))


@app.route("/notifications/read-all", methods=["POST"])
def read_all_notifications():
    state = app_state()
    pushes = state.get("pushes", [])
    for push in pushes:
        push["read"] = True
    state["pushes"] = pushes
    save_app_state(state)
    return redirect(url_for("notifications"))


@app.route("/api/connect/initiate", methods=["POST"])
def initiate_connection():
    data = request.get_json(silent=True) or {}
    bank_id = data.get("bank_id")
    bank = bank_by_id(bank_id)
    if not bank:
        return jsonify({"error": "Banco nao encontrado"}), 404
    consent_response = open_finance_provider.create_consent(bank_id)
    consent_id = consent_response.get("consent_id")
    deep_link = consent_response.get("deep_link") or f"bankapp://{bank_id}/oauth/{consent_id}"
    state = app_state()
    consents = state.get("oauth_consents", {})
    consents[bank_id] = {
        "consent_id": consent_id,
        "bank_id": bank_id,
        "created_at": now_br(),
        "provider": open_finance_provider.name,
    }
    state["oauth_consents"] = consents
    save_app_state(state)
    # Redirect to bank authorization flow
    return redirect(deep_link)


@app.route("/api/connect/bulk-initiate", methods=["POST"])
def bulk_initiate_connection():
    data = request.get_json(silent=True) or {}
    bank_ids = data.get("bank_ids") or selected_bank_ids()
    payloads = []
    first_deep_link = None
    for bank_id in bank_ids[:5]:
        bank = bank_by_id(bank_id)
        if not bank:
            continue
        consent_response = open_finance_provider.create_consent(bank_id)
        consent_id = consent_response.get("consent_id")
        deep_link = consent_response.get("deep_link") or f"bankapp://{bank_id}/oauth/{consent_id}"
        if not first_deep_link:
            first_deep_link = deep_link
        payloads.append({
            "bank_id": bank_id,
            "bank_name": bank["name"],
            "consent_id": consent_id,
            "deep_link": deep_link,
            "status": consent_response.get("status", "AWAITING_AUTHORISATION"),
        })
    state = app_state()
    consents = state.get("oauth_consents", {})
    for payload in payloads:
        consents[payload["bank_id"]] = {
            "consent_id": payload["consent_id"],
            "bank_id": payload["bank_id"],
            "created_at": now_br(),
            "provider": open_finance_provider.name,
        }
    state["oauth_consents"] = consents
    save_app_state(state)
    # Redirect to first bank authorization flow
    if first_deep_link:
        return redirect(first_deep_link)
    return redirect(url_for("processing"))


@app.route("/api/dashboard-state")
def dashboard_state():
    state = app_state()
    items = visible_subscriptions()
    monthly, annual = dashboard_totals(items)
    saved_amount = sum(abs(tx["amount"]) for tx in RAW_TRANSACTIONS if tx["id"] in optimized_ids())

    return jsonify({
        "monthly_total": round(monthly, 2),
        "annual_total": round(annual, 2),
        "saved_amount": round(saved_amount, 2),
        "last_scan_at": state.get("last_scan_at"),
        "last_scan_count": state.get("last_scan_count", 0),
        "subscriptions": items,
        "connections": connected_banks(),
        "failed_banks": list(failed_banks()),
        "revoked_banks": list(revoked_banks()),
        "alerts": state.get("pushes", []),
    })


@app.route("/api/notifications/fallback", methods=["POST"])
def notification_fallback():
    data = request.get_json(silent=True) or {}
    sub_id = data.get("subscription_id")
    add_push("Fallback por e-mail agendado", "Se o push for ignorado, enviaremos um e-mail no vencimento.", sub_id, "email")
    return jsonify({"ok": True, "channel": "email", "scheduled_at": now_br()})


@app.route("/api/error-simulation")
def error_simulation():
    return jsonify({
        "error": "SERVICE_UNAVAILABLE",
        "message": "API bancaria indisponivel. Ultimos dados sincronizados continuam visiveis.",
        "cached_data_available": True,
        "retry_after": 300,
    }), 503


@app.route("/reset")
def reset():
    email = current_email()
    if email:
        state.reset_app_state(email)
    return redirect(url_for("onboarding"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
