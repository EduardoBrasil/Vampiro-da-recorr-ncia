# Vampiro da Recorrência

Aplicativo Flask para visualizar e gerenciar assinaturas recorrentes, conexões bancárias e notificações de renovação. O projeto simula um painel financeiro com varredura de gastos e ações de leitura de alertas.

## Funcionalidades

- Autenticação de usuário com login e registro
- Onboarding com seleção de bancos e conexão via open finance fictício
- Dashboard com notificações, varredura de assinaturas e totais de economia
- Página de notificações com marcação de alertas como lidos
- Perfil do usuário com edição de nome e e-mail
- Reset de estado do aplicativo para reiniciar onboarding

## Instalação

1. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```powershell
pip install -r requirements.txt
```

3. Execute o aplicativo:

```powershell
python app.py
```

4. Acesse no navegador:

```
http://127.0.0.1:5000
```

## Observações

- O projeto usa um banco de dados SQLite local (`users.db`) para armazenar usuários e estado do aplicativo.
- O arquivo `.gitignore` já exclui o ambiente virtual, logs, arquivos de banco e caches.
- Se quiser limpar o estado do aplicativo, use a rota `/reset` após login.
