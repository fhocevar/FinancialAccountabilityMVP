# Financial Accountability MVP

MVP local para transformar reuniões em compromissos rastreáveis, com revisão humana, clientes, dashboard, login e auditoria.

## Recursos
- Login e sessão local; perfis preparados no modelo de usuário.
- Reuniões por texto, TXT e áudio.
- Áudio via comando Whisper configurável (`WHISPER_COMMAND`).
- Extração por regras com contexto; Ollama opcional (`USE_OLLAMA=true`).
- Clientes consolidados e timeline.
- Revisão, aprovação, rejeição, fechamento e reabertura.
- Dashboard RAG: Green <=7 dias, Yellow 8-21, Red >21.
- Auditoria por usuário.
- SQLite local ou PostgreSQL via Docker Compose.

## Execução rápida no Windows
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Acesse http://localhost:8000

Conta inicial: `admin@local` / `Admin123!` (troque antes de uso real).

## PostgreSQL
```powershell
docker compose up --build
```

## Ollama
Defina no ambiente:
```powershell
$env:USE_OLLAMA="true"
$env:OLLAMA_URL="http://localhost:11434"
$env:OLLAMA_MODEL="llama3.1:8b"
```

## Whisper
A integração é intencionalmente desacoplada. `WHISPER_COMMAND` deve apontar para um comando local que recebe o caminho do áudio e escreve a transcrição em stdout. Exemplo de wrapper:
```powershell
$env:WHISPER_COMMAND="python scripts/transcribe.py"
```
Sem configuração, o sistema continua operando por transcrição colada ou TXT.

## Segurança
Esta entrega é um MVP técnico. Antes da produção: TLS, segredo forte, redefinição de senha, RBAC completo, Alembic, backups, antivírus de upload, limites de arquivo, CSRF, logs estruturados e hardening do host.
