"""
Vampiro da Recorrência Flask Application
Main application factory and route definitions.
"""

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from domain import TERMS_VERSION, BANKS, BRAND_RULES, RAW_TRANSACTIONS
from services.open_finance import create_open_finance_provider
from models import db, User
from config import config
from logging_config import setup_logging
import os
import re
import uuid
from dotenv import load_dotenv

import state

# Load environment variables from .env file
load_dotenv()

# Initialize extensions
csrf = CSRFProtect()
talisman = Talisman()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)


def create_app(config_name=None):
    """Application factory function."""
    
    # Get configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    
    app_config = config.get(config_name, config["development"])
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(app_config)
    
    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    talisman.init_app(app,
        force_https=app_config.FLASK_ENV == "production",
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data: https:",
        }
    )
    limiter.init_app(app)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize Open Finance Provider
    open_finance_provider = create_open_finance_provider(
        os.environ.get("OPEN_FINANCE_PROVIDER", "mock"),
        base_url=os.environ.get("OPEN_FINANCE_BASE_URL", ""),
        token=os.environ.get("OPEN_FINANCE_TOKEN", ""),
    )
    
    # Store provider in app context
    app.open_finance_provider = open_finance_provider
    
    # Template filters
    @app.template_filter("money")
    def money_filter(value):
        return f"R$ {float(value):.2f}".replace(".", ",")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f"404 error: {request.path}")
        return render_template('error.html', error="Página não encontrada"), 404
    
    @app.errorhandler(500)
    def server_error(error):
        app.logger.error(f"500 error: {str(error)}")
        return render_template('error.html', error="Erro interno do servidor"), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        app.logger.warning(f"403 error: {request.path}")
        return render_template('error.html', error="Acesso negado"), 403
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        app.logger.warning(f"Rate limit exceeded: {get_remote_address()}")
        return render_template('error.html', error="Muitas requisições. Tente novamente mais tarde."), 429
    
    # Request handlers
    @app.before_request
    def log_request():
        app.logger.debug(f"{request.method} {request.path}")
    
    @app.after_request
    def log_response(response):
        app.logger.debug(f"Response: {response.status_code}")
        return response
    
    # Setup request context for routes
    public_endpoints = {
        "login",
        "register",
        "static",
        "health",
    }
    
    @app.before_request
    def require_login():
        if request.endpoint in public_endpoints or request.endpoint is None:
            return
        if not session.get("user"):
            return redirect(url_for("login", next=request.path))
    
    # ==================== ROUTES ====================
    
    @app.route("/health", methods=["GET"])
    @limiter.exempt
    def health():
        """Health check endpoint for monitoring."""
        return jsonify({"status": "healthy", "app": "vampiro-recorrencia"}), 200
    
    # Auth Routes
    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("5 per minute")
    def login():
        error = None
        next_url = request.args.get("next") or url_for("index")
        if request.method == "POST":
            email = state.normalize_email(request.form.get("email", ""))
            password = request.form.get("password", "").strip()
            next_url = request.form.get("next") or url_for("index")
            users = state.load_users()
            user = users.get(email)
            if not state.valid_email(email):
                error = "Digite um e-mail valido para entrar."
            elif not user or not check_password_hash(user["password_hash"], password):
                error = "E-mail ou senha incorretos."
                app.logger.warning(f"Failed login attempt for {email}")
            else:
                state.start_user_session(email, user)
                app.logger.info(f"User logged in: {email}")
                return redirect(next_url)
        registered = request.args.get("registered") == "1"
        return render_template("login.html", error=error, next_url=next_url, registered=registered)
    
    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("3 per minute")
    def register():
        error = None
        form = {"name": "", "email": ""}
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = state.normalize_email(request.form.get("email", ""))
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            form = {"name": name, "email": email}
            users = state.load_users()
            if len(name) < 2:
                error = "Informe seu nome."
            elif not state.valid_email(email):
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
                    "created_at": state.now_br(),
                    "updated_at": state.now_br(),
                })
                app.logger.info(f"New user registered: {email}")
                return redirect(url_for("login", registered=1))
        return render_template("register.html", error=error, form=form)
    
    @app.route("/logout")
    def logout():
        email = session.get("user", {}).get("email")
        if email:
            app.logger.info(f"User logged out: {email}")
        session.clear()
        return redirect(url_for("login"))
    
    # Main Routes
    @app.route("/")
    def index():
        if not state.consent_log():
            return redirect(url_for("onboarding"))
        if not state.connected_banks():
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
            user_state = state.app_state()
            user_state["selected_banks"] = selected
            user_state["consent_log"] = {
                "timestamp": state.now_br(),
                "terms_version": TERMS_VERSION,
                "banks": selected,
            }
            state.save_app_state(user_state)
            app.logger.info(f"User selected banks: {selected}")
            return redirect(url_for("auth"))
        return render_template("onboarding.html", banks=BANKS, terms_version=TERMS_VERSION, selected=state.selected_bank_ids())
    
    @app.route("/connect")
    def connect():
        return redirect(url_for("onboarding"))
    
    @app.route("/auth")
    def auth():
        if not state.consent_log():
            return redirect(url_for("onboarding"))
        selected = state.selected_bank_ids()
        if not selected:
            return redirect(url_for("onboarding"))
        selected_banks = [state.bank_by_id(bank_id) for bank_id in selected if state.bank_by_id(bank_id)]
        return render_template("auth.html", banks=selected_banks, consent=state.consent_log())
    
    @app.route("/auth/collect-cpf", methods=["GET", "POST"])
    def auth_collect_cpf():
        """Step 1: Request user's CPF/CNPJ"""
        if not state.consent_log():
            return redirect(url_for("onboarding"))
        
        user_state = state.app_state()
        if request.method == "GET" and user_state and "user_cpf_cnpj" in user_state:
            selected = state.selected_bank_ids()
            if selected:
                return redirect(url_for("auth_review_consent", bank_id=selected[0]))
    
        if request.method == "POST":
            cpf_cnpj = request.form.get("cpf_cnpj", "").strip()
            cpf_cnpj_clean = re.sub(r"\D", "", cpf_cnpj)
            
            if not cpf_cnpj_clean or len(cpf_cnpj_clean) < 11:
                return render_template(
                    "auth_cpf.html",
                    selected_banks=[state.bank_by_id(bid) for bid in state.selected_bank_ids() if state.bank_by_id(bid)],
                    error="CPF/CNPJ inválido. Informe um valor com 11 ou 14 dígitos.",
                )
    
            user_state["user_cpf_cnpj"] = cpf_cnpj_clean
            state.save_app_state(user_state)
            selected = state.selected_bank_ids()
            if selected:
                return redirect(url_for("auth_review_consent", bank_id=selected[0]))
            return redirect(url_for("auth"))
    
        return render_template(
            "auth_cpf.html",
            selected_banks=[state.bank_by_id(bid) for bid in state.selected_bank_ids() if state.bank_by_id(bid)],
        )
    
    @app.route("/auth/review-consent/<bank_id>")
    def auth_review_consent(bank_id):
        """Step 2-3: Review consent details before redirecting to bank"""
        if not state.consent_log() or "user_cpf_cnpj" not in state.app_state():
            return redirect(url_for("auth_collect_cpf"))
        
        bank = state.bank_by_id(bank_id)
        if not bank:
            return redirect(url_for("onboarding"))
        
        return render_template(
            "auth_review.html",
            bank=bank,
            cpf_cnpj=state.app_state()["user_cpf_cnpj"],
            consent_validity_days=12 * 30,
        )
    
    @app.route("/mock-bank/<bank_id>")
    def mock_bank_authorize(bank_id):
        bank = state.bank_by_id(bank_id)
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
        user_state = state.app_state()
        if "user_cpf_cnpj" not in user_state:
            return redirect(url_for("auth_collect_cpf"))
        
        bank = state.bank_by_id(bank_id)
        if not bank:
            return redirect(url_for("onboarding"))
        
        # Create the digitally signed consent request
        consent_response = app.open_finance_provider.create_consent(bank_id, cpf_cnpj=user_state["user_cpf_cnpj"])
        consent_id = consent_response.get("consent_id")
        deep_link = consent_response.get("deep_link") or f"bankapp://{bank_id}/oauth/{consent_id}"
        
        # Save consent metadata (step 2)
        consents = user_state.get("oauth_consents", {})
        consents[bank_id] = {
            "consent_id": consent_id,
            "bank_id": bank_id,
            "cpf_cnpj": user_state["user_cpf_cnpj"],
            "status": "AWAITING_AUTHORISATION",
            "created_at": state.now_br(),
            "provider": app.open_finance_provider.name,
        }
        user_state["oauth_consents"] = consents
        state.save_app_state(user_state)
        app.logger.info(f"Consent created for bank {bank_id}")
        
        # Redirect to bank authentication (step 3)
        return redirect(deep_link)
    
    @app.route("/auth/callback/<bank_id>")
    def auth_callback(bank_id):
        """Step 5: Handle secure callback from bank with access token"""
        user_state = state.app_state()
        
        # Get callback parameters from bank
        consent_id = request.args.get("consentId")
        access_token = request.args.get("accessToken")
        error = request.args.get("error")
        
        # Handle errors from bank
        if error:
            user_state["oauth_consents"][bank_id]["status"] = "REJECTED"
            state.save_app_state(user_state)
            state.add_push(
                "Autorização rejeitada",
                f"A autorização no {state.bank_by_id(bank_id)['name']} foi rejeitada ou expirou.",
                None,
                "warning",
            )
            app.logger.warning(f"Authorization rejected for bank {bank_id}")
            return redirect(url_for("connection_error", bank_id=bank_id))
        
        # Verify consent status with provider (step 5 - get token)
        if consent_id and access_token:
            consents = user_state.get("oauth_consents", {})
            if bank_id in consents:
                # Save the access token securely (step 5)
                consents[bank_id]["consent_id"] = consent_id
                consents[bank_id]["access_token"] = access_token
                consents[bank_id]["status"] = "AUTHORISED"
                consents[bank_id]["authorized_at"] = state.now_br()
                user_state["oauth_consents"] = consents
                state.save_app_state(user_state)
                
                # Create connection with the token
                state.create_connection(bank_id)
                state.add_push(
                    "Banco conectado com sucesso",
                    f"{state.bank_by_id(bank_id)['name']} foi autorizado para compartilhar seus dados.",
                    None,
                    "success",
                )
                app.logger.info(f"Bank {bank_id} successfully authorized")
                
                # Check if there are more banks to authorize
                selected = state.selected_bank_ids()
                authorized = [bid for bid, c in consents.items() if c.get("status") == "AUTHORISED"]
                pending = [bid for bid in selected if bid not in authorized and bid != bank_id]
                
                if pending:
                    # Redirect to next bank authorization
                    return redirect(url_for("auth_review_consent", bank_id=pending[0]))
                else:
                    # All banks authorized, proceed to processing
                    state.ensure_demo_pushes()
                    return redirect(url_for("processing"))
        
        # Token not received or invalid
        state.add_push(
            "Erro na autorização",
            "Não conseguimos obter o token de acesso. Tente novamente.",
            None,
            "error",
        )
        app.logger.error(f"Failed to get authorization token for bank {bank_id}")
        return redirect(url_for("connection_error", bank_id=bank_id))
    
    @app.route("/auth/start", methods=["POST"])
    def auth_start():
        """Legacy route: Redirect to new CPF/CNPJ collection flow"""
        return redirect(url_for("auth_collect_cpf"))
    
    @app.route("/connect/callback/<bank_id>")
    def connect_callback(bank_id):
        state.create_connection(bank_id)
        state.ensure_demo_pushes()
        return redirect(url_for("processing"))
    
    @app.route("/connect/simulate/<bank_id>")
    def simulate_connect(bank_id):
        return redirect(url_for("connect_callback", bank_id=bank_id))
    
    @app.route("/error/<bank_id>")
    def connection_error(bank_id):
        bank = state.bank_by_id(bank_id) or BANKS[0]
        return render_template("error.html", bank=bank)
    
    @app.route("/retry/<bank_id>", methods=["POST"])
    def retry_connection(bank_id):
        user_state = state.app_state()
        failed = state.failed_banks()
        failed.discard(bank_id)
        user_state["failed_banks"] = list(failed)
        state.save_app_state(user_state)
        state.create_connection(bank_id)
        state.ensure_demo_pushes()
        return redirect(url_for("processing"))
    
    @app.route("/processing")
    def processing():
        state.scan_for_recurring_subscriptions()
        return render_template("processing.html")
    
    @app.route("/dashboard")
    @limiter.limit("30 per minute")
    def dashboard():
        if not state.consent_log():
            return redirect(url_for("onboarding"))
        if not state.connected_banks() and not state.failed_banks():
            return redirect(url_for("auth"))
        items = state.visible_subscriptions()
        monthly, annual = state.dashboard_totals(items)
    
        state.ensure_demo_pushes()
        user_state = state.app_state()
        saved_monthly, saved_annual = state.total_economy()
        dashboard_pushes = [
            push for push in user_state.get("pushes", [])
            if not push.get("read") and push["title"] != "Autorização revogada"
        ]
        return render_template(
            "dashboard.html",
            subscriptions=items,
            total_monthly=monthly,
            total_annual=annual,
            connected_banks=state.connected_banks(),
            failed_banks=state.failed_banks(),
            revoked_banks=state.revoked_banks(),
            pushes=dashboard_pushes,
            optimized_count=len(state.optimized_ids()),
            saved_monthly=saved_monthly,
            saved_annual=saved_annual,
            last_scan_at=user_state.get("last_scan_at"),
            last_scan_count=user_state.get("last_scan_count"),
        )
    
    @app.route("/subscription/<sub_id>")
    @limiter.limit("30 per minute")
    def subscription_detail(sub_id):
        tx = next((item for item in RAW_TRANSACTIONS if item["id"] == sub_id), None)
        if not tx:
            return redirect(url_for("dashboard"))
        sub = state.clean_transaction(tx)
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
    @limiter.limit("10 per minute")
    def optimize_subscription(sub_id):
        user_state = state.app_state()
        optimized = state.optimized_ids()
        optimized.add(sub_id)
        user_state["optimized_subscriptions"] = list(optimized)
        state.save_app_state(user_state)
        tx = next((item for item in RAW_TRANSACTIONS if item["id"] == sub_id), None)
        monthly_saved = abs(tx["amount"]) if tx else 0
        annual_saved = monthly_saved * 12
        state.add_push(
            "Gasto removido",
            f"Você economizou R$ {monthly_saved:.2f} por mês e R$ {annual_saved:.2f} por ano com essa recorrência.",
            sub_id,
            "success",
        )
        app.logger.info(f"Subscription optimized: {sub_id}")
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
            user_state = state.app_state()
            reviews = user_state.get("manual_reviews", [])
            reviews.append({
                "subscription_id": sub_id,
                "suggested_name": request.form.get("service_name", "").strip(),
                "points": 120,
                "submitted_at": state.now_br(),
            })
            user_state["manual_reviews"] = reviews
            state.save_app_state(user_state)
            state.add_push("Obrigado pela ajuda", "Voce ganhou 120 pontos de fidelidade pela identificacao.", sub_id, "success")
            app.logger.info(f"Manual review submitted for {sub_id}")
            return redirect(url_for("dashboard"))
        return render_template("manual.html", sub=state.clean_transaction(tx))
    
    @app.route("/connections")
    def connections():
        connected_ids = {bank["id"] for bank in state.connected_banks()}
        available_banks = [bank for bank in BANKS if bank["id"] not in connected_ids]
        return render_template(
            "connections.html",
            connected_banks=state.connected_banks(),
            failed_banks=state.failed_banks(),
            available_banks=available_banks,
            consent=state.consent_log(),
        )
    
    @app.route("/connections/add", methods=["POST"])
    @limiter.limit("10 per minute")
    def connections_add():
        bank_ids = request.form.getlist("banks")[:5]
        if not bank_ids:
            state.add_push("Sem banco selecionado", "Selecione ao menos um banco para conectar e buscar novas recorrências.", None, "warning")
            return redirect(url_for("connections"))
    
        s = state.app_state()
        s["selected_banks"] = bank_ids
        s["consent_log"] = {
            "timestamp": state.now_br(),
            "terms_version": TERMS_VERSION,
            "banks": bank_ids,
        }
        state.save_app_state(s)
        app.logger.info(f"Added banks: {bank_ids}")
    
        if "user_cpf_cnpj" in s:
            return redirect(url_for("auth_review_consent", bank_id=bank_ids[0]))
        return redirect(url_for("auth_collect_cpf"))
    
    @app.route("/connections/revoke/<bank_id>", methods=["POST"])
    @limiter.limit("10 per minute")
    def revoke_connection(bank_id):
        s = state.app_state()
        connected = [item for item in state.connected_banks() if item["id"] != bank_id]
        s["connected_banks"] = connected
        revoked = state.revoked_banks()
        revoked.add(bank_id)
        s["revoked_banks"] = list(revoked)
        if s.get("oauth_consents") and bank_id in s["oauth_consents"]:
            s["oauth_consents"].pop(bank_id, None)
        state.save_app_state(s)
        bank = state.bank_by_id(bank_id)
        bank_name = bank["name"] if bank else "O banco"
        state.add_push("Autorização revogada", f"A autorização do {bank_name} foi revogada. Você pode adicionar o banco novamente em Conexões.", None, "warning")
        app.logger.info(f"Connection revoked: {bank_id}")
        return redirect(url_for("connections"))
    
    @app.route("/connections/reauthorize/<bank_id>", methods=["POST"])
    def reauthorize_connection(bank_id):
        s = state.app_state()
        connected = [item for item in state.connected_banks() if item["id"] != bank_id]
        s["connected_banks"] = connected
        revoked = state.revoked_banks()
        revoked.discard(bank_id)
        s["revoked_banks"] = list(revoked)
        s["selected_banks"] = [bank_id]
        s["consent_log"] = {
            "timestamp": state.now_br(),
            "terms_version": TERMS_VERSION,
            "banks": [bank_id],
        }
        state.save_app_state(s)
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
            email = state.normalize_email(request.form.get("email", ""))
            users = state.load_users()
            old_email = current_user.get("email")
            if not state.valid_email(email):
                error = "E-mail mal formatado. Corrija para salvar."
            elif email != old_email and email in users:
                error = "Este e-mail ja esta em uso."
            else:
                profile_data = {"name": name, "email": email, "updated_at": state.now_br()}
                if old_email in users and email != old_email:
                    state.user_repository.replace_email(old_email, email, {"name": name, "updated_at": profile_data["updated_at"]})
                elif old_email in users:
                    state.user_repository.update(old_email, {"name": name, "updated_at": profile_data["updated_at"]})
                session["user"] = {"email": email, "name": name, "logged_at": current_user.get("logged_at", state.now_br())}
                saved = True
                app.logger.info(f"Profile updated for {email}")
        return render_template("profile.html", profile=profile_data, error=error, saved=saved)
    
    @app.route("/notifications")
    @limiter.limit("30 per minute")
    def notifications():
        state.ensure_demo_pushes()
        s = state.app_state()
        pushes = [push for push in s.get("pushes", []) if not push.get("read")]
        return render_template("notifications.html", pushes=pushes)
    
    @app.route("/notifications/<push_id>/read", methods=["POST"])
    @limiter.limit("20 per minute")
    def read_notification(push_id):
        s = state.app_state()
        pushes = s.get("pushes", [])
        for push in pushes:
            if push["id"] == push_id:
                push["read"] = True
        s["pushes"] = pushes
        state.save_app_state(s)
        return redirect(url_for("notifications"))
    
    @app.route("/notifications/read-all", methods=["POST"])
    @limiter.limit("20 per minute")
    def read_all_notifications():
        s = state.app_state()
        pushes = s.get("pushes", [])
        for push in pushes:
            push["read"] = True
        s["pushes"] = pushes
        state.save_app_state(s)
        return redirect(url_for("notifications"))
    
    # API Routes
    @app.route("/api/connect/initiate", methods=["POST"])
    @limiter.limit("10 per minute")
    def initiate_connection():
        data = request.get_json(silent=True) or {}
        bank_id = data.get("bank_id")
        bank = state.bank_by_id(bank_id)
        if not bank:
            app.logger.warning(f"Invalid bank_id: {bank_id}")
            return jsonify({"error": "Banco nao encontrado"}), 404
        consent_response = app.open_finance_provider.create_consent(bank_id)
        consent_id = consent_response.get("consent_id")
        deep_link = consent_response.get("deep_link") or f"bankapp://{bank_id}/oauth/{consent_id}"
        user_state = state.app_state()
        consents = user_state.get("oauth_consents", {})
        consents[bank_id] = {
            "consent_id": consent_id,
            "bank_id": bank_id,
            "created_at": state.now_br(),
            "provider": app.open_finance_provider.name,
        }
        user_state["oauth_consents"] = consents
        state.save_app_state(user_state)
        return redirect(deep_link)
    
    @app.route("/api/connect/bulk-initiate", methods=["POST"])
    @limiter.limit("5 per minute")
    def bulk_initiate_connection():
        data = request.get_json(silent=True) or {}
        bank_ids = data.get("bank_ids") or state.selected_bank_ids()
        payloads = []
        first_deep_link = None
        for bank_id in bank_ids[:5]:
            bank = state.bank_by_id(bank_id)
            if not bank:
                continue
            consent_response = app.open_finance_provider.create_consent(bank_id)
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
        user_state = state.app_state()
        consents = user_state.get("oauth_consents", {})
        for payload in payloads:
            consents[payload["bank_id"]] = {
                "consent_id": payload["consent_id"],
                "bank_id": payload["bank_id"],
                "created_at": state.now_br(),
                "provider": app.open_finance_provider.name,
            }
        user_state["oauth_consents"] = consents
        state.save_app_state(user_state)
        if first_deep_link:
            return redirect(first_deep_link)
        return redirect(url_for("processing"))
    
    @app.route("/api/dashboard-state")
    @limiter.limit("20 per minute")
    def dashboard_state():
        user_state = state.app_state()
        items = state.visible_subscriptions()
        monthly, annual = state.dashboard_totals(items)
        saved_amount = sum(abs(tx["amount"]) for tx in RAW_TRANSACTIONS if tx["id"] in state.optimized_ids())
    
        return jsonify({
            "monthly_total": round(monthly, 2),
            "annual_total": round(annual, 2),
            "saved_amount": round(saved_amount, 2),
            "last_scan_at": user_state.get("last_scan_at"),
            "last_scan_count": user_state.get("last_scan_count", 0),
            "subscriptions": items,
            "connections": state.connected_banks(),
            "failed_banks": list(state.failed_banks()),
            "revoked_banks": list(state.revoked_banks()),
            "alerts": user_state.get("pushes", []),
        })
    
    @app.route("/api/notifications/fallback", methods=["POST"])
    @limiter.limit("5 per minute")
    def notification_fallback():
        data = request.get_json(silent=True) or {}
        sub_id = data.get("subscription_id")
        state.add_push("Fallback por e-mail agendado", "Se o push for ignorado, enviaremos um e-mail no vencimento.", sub_id, "email")
        return jsonify({"ok": True, "channel": "email", "scheduled_at": state.now_br()})
    
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
        email = state.current_email()
        if email:
            state.reset_app_state(email)
            app.logger.info(f"App state reset for {email}")
        return redirect(url_for("onboarding"))
    
    # Database init commands
    @app.cli.command()
    def init_db():
        """Initialize the database."""
        db.create_all()
        app.logger.info("Database initialized!")
    
    @app.cli.command()
    def drop_db():
        """Drop all database tables."""
        db.drop_all()
        app.logger.info("Database dropped!")
    
    return app


if __name__ == "__main__":
    flask_env = os.environ.get("FLASK_ENV", "development")
    app_instance = create_app(flask_env)
    debug_mode = flask_env == "development"
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    
    if debug_mode:
        print(f"⚠️  DEBUG MODE ENABLED - Development only!")
    else:
        print(f"🔒 PRODUCTION MODE - Debug disabled")
    
    app_instance.run(debug=debug_mode, host=host, port=port)
