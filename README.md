# Vampiro da Recorrência

Aplicativo Flask para visualizar e gerenciar assinaturas recorrentes, conexões bancárias e notificações de renovação. O projeto simula um painel financeiro com varredura de gastos e ações de leitura de alertas.

## Funcionalidades

- ✅ Autenticação de usuário com login e registro
- ✅ Onboarding com seleção de bancos e conexão via open finance fictício
- ✅ Dashboard com notificações, varredura de assinaturas e totais de economia
- ✅ Página de notificações com marcação de alertas como lidos
- ✅ Perfil do usuário com edição de nome e e-mail
- ✅ Reset de estado do aplicativo para reiniciar onboarding
- ✅ Proteção CSRF com Flask-WTF
- ✅ Security headers com Flask-Talisman
- ✅ Rate limiting com Flask-Limiter
- ✅ Logging estruturado
- ✅ Health check endpoint
- ✅ Suporte a Docker e docker-compose
- ✅ Nginx reverse proxy
- ✅ Testes automatizados com pytest

## Arquitetura

### Fases de Produção Implementadas

#### **Fase 1: Segurança** ✅
- CSRF Protection (Flask-WTF)
- Security Headers (Flask-Talisman)
- Session cookies seguros
- Variáveis de ambiente (.env)
- Error handlers customizados
- Debug mode desativado em produção

#### **Fase 2: Database** ✅
- SQLAlchemy ORM
- Modelos de usuário
- Suporte a SQLite (dev) e PostgreSQL (prod)
- Configuração centralizada

#### **Fase 3: Infraestrutura** ✅
- Logging estruturado com rotating files
- Gunicorn configuration
- Nginx reverse proxy com rate limiting
- Application factory pattern

#### **Fase 4: Containerização** ✅
- Dockerfile multi-stage
- docker-compose com PostgreSQL
- Volumes para dados persistentes
- Health checks

#### **Fase 5: Robustez** ✅
- Rate limiting (global e por rota)
- Testes unitários com pytest
- Monitoramento com health check
- WSGI server (Gunicorn)

## Stack Técnico

- **Framework**: Flask 3.1.3
- **ORM**: SQLAlchemy
- **Segurança**: Flask-WTF, Flask-Talisman, Flask-Limiter
- **Server**: Gunicorn + Nginx
- **Database**: PostgreSQL (prod), SQLite (dev)
- **Containerização**: Docker, docker-compose
- **Testes**: pytest, pytest-flask
- **Logging**: Python logging com rotating handlers

## Instalação

### Desenvolvimento Local

1. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```powershell
pip install -r requirements.txt
```

3. Configure variáveis de ambiente:

```powershell
cp .env.example .env
# Edite .env conforme necessário
```

4. Execute o aplicativo:

```powershell
python app.py
```

5. Acesse no navegador:

```
http://127.0.0.1:5000
```

### Production com Docker

1. Configure variáveis de ambiente:

```bash
cp .env.example .env
# Edite .env com valores de produção seguros
```

2. Inicie os containers:

```bash
docker-compose up -d
```

3. Acesse:

```
http://localhost:80  (via Nginx)
```

4. Pare os containers:

```bash
docker-compose down
```

## Configuração

### Variáveis de Ambiente

```bash
# Segurança
SECRET_KEY=your-secret-key-here (mín. 32 chars)
FLASK_ENV=development|production

# Open Finance
OPEN_FINANCE_PROVIDER=mock|sandbox|real
OPEN_FINANCE_BASE_URL=https://api.example.com
OPEN_FINANCE_TOKEN=your-api-token

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
DB_USER=vampiro_user
DB_PASSWORD=secure_password
DB_NAME=vampiro_db

# Server
HOST=0.0.0.0
PORT=5000
GUNICORN_WORKERS=4

# SSL (opcional)
SSL_KEY_FILE=/path/to/key.pem
SSL_CERT_FILE=/path/to/cert.pem
```

## Testes

Executar suite de testes:

```bash
pytest tests.py -v
```

Com coverage:

```bash
pytest tests.py --cov=. --cov-report=html
```

## Estrutura de Diretórios

```
vampiro-recorrenciaApp/
├── app.py                  # Application factory e routes
├── models.py              # SQLAlchemy models
├── config.py              # Configuration classes
├── domain.py              # Business data (banks, transactions)
├── repository.py          # Data access layer
├── state.py               # State management
├── logging_config.py      # Logging configuration
├── wsgi.py               # WSGI entry point (Gunicorn)
├── gunicorn_config.py    # Gunicorn configuration
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Multi-container orchestration
├── nginx.conf           # Nginx reverse proxy config
├── init_db.py           # Database initialization
├── tests.py             # Test suite (pytest)
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Environment variables (local)
├── .gitignore          # Git ignore rules
├── .dockerignore       # Docker build ignore
├── services/
│   └── open_finance/
│       ├── __init__.py
│       ├── base.py      # Abstract provider
│       ├── client.py    # HTTP clients
│       ├── mock_provider.py
│       ├── real_provider.py
│       └── sandbox_provider.py
├── templates/          # Jinja2 templates
├── static/             # CSS, JS, images
└── logs/              # Application logs (created at runtime)
```

## Segurança

### Implementado

✅ CSRF token protection em formulários  
✅ Session cookies com HttpOnly e SameSite  
✅ Security headers (CSP, HSTS, X-Frame-Options)  
✅ Rate limiting (200 req/dia global, 50/hora)  
✅ Input validation e sanitização  
✅ HTTPS em produção  
✅ Logging de eventos de segurança  
✅ Senha hasheada com werkzeug  
✅ Environment variables para secrets  
✅ Error handlers customizados sem exposição técnica  

### Recomendações Futuras

- Implementar TOTP/2FA
- Audit logging para ações críticas
- DDoS protection (via cloud provider)
- Web Application Firewall (WAF)
- Implementar API keys para endpoints
- Rate limiting por usuário

## Deployment

### Heroku

```bash
git push heroku main
heroku config:set SECRET_KEY=your-secret
heroku addons:create heroku-postgresql:hobby-dev
```

### AWS

```bash
# ECR push
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag vampiro-app:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/vampiro:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/vampiro:latest

# ECS deployment
aws ecs create-service --cluster my-cluster --service-name vampiro --task-definition vampiro-task
```

### GCP Cloud Run

```bash
gcloud run deploy vampiro --source . --platform managed --region us-central1
```

## Monitoramento

### Health Check

```bash
curl http://localhost:5000/health
# {"status": "healthy", "app": "vampiro-recorrencia"}
```

### Logs

```bash
# Aplicação
tail -f logs/app.log

# Erros
tail -f logs/error.log

# Docker
docker logs vampiro-app
docker logs vampiro-db
```

## Observações

- O projeto usa um banco de dados SQLite local (`users.db`) para desenvolvimento
- Em produção, use PostgreSQL com backups regulares
- O arquivo `.gitignore` já exclui env, logs, banco e caches
- Para limpar o estado, use a rota `/reset` após login (desenvolvimento apenas)
- Sempre altere `SECRET_KEY` em produção
- Configure HTTPS com certificados válidos

## Roadmap

- [ ] Integração real com Open Finance Brasil
- [ ] Sistema de notificações por email/SMS
- [ ] Dashboard analytics avançado
- [ ] Integração com serviços de pagamento
- [ ] App mobile (React Native/Flutter)
- [ ] Machine learning para detecção de fraude
- [ ] API pública com autenticação OAuth2

## Suporte

Para dúvidas ou problemas, abra uma issue no repositório.

## Licença

Proprietary - Todos os direitos reservados

