# Flask Quiz App

## Run locally

Windows PowerShell:

1. python -m venv venv
2. .\venv\Scripts\Activate.ps1
3. python -m pip install -r requirements.txt
4. Remove-Item Env:DATABASE_URL   # ensure local SQLite is used
5. python app.py
6. Open http://127.0.0.1:5000

Notes:
- If you ever see "no such table" locally, delete the SQLite file and restart:
	- if (Test-Path "instance/quiz.db") { Remove-Item "instance/quiz.db" -Force }
- Clear browser cookies for localhost if a stale login causes errors.

## Deploy on Render

This repo includes `render.yaml` and `build.sh` for automated deploys and DB migrations.

Minimal setup in Render dashboard (Environment tab):
- SECRET_KEY=<your-random-secret>
- DATABASE_URL=<Render Postgres Internal Database URL>
- SESSION_COOKIE_SECURE=1
- REMEMBER_COOKIE_SECURE=1
- SESSION_COOKIE_SAMESITE=Strict
- PREFERRED_URL_SCHEME=https

Build Command:
- pip install -r requirements.txt && bash build.sh

Start Command:
- gunicorn app:app

Tip: On Render Free plan the service sleeps after ~15 minutes. First request may take 30–60s to wake up (cold start).

### One-time DB initialization on Render

Render runs `bash build.sh` on deploy, which executes `flask db upgrade` automatically. If needed, you can also run it manually from the Render Shell:

```
flask db upgrade
```

Troubleshooting:
- Ensure DATABASE_URL is set to the Internal Database URL of your Render Postgres
- Check Logs tab for build/start errors
- Health check is available at `/healthz`

## Tests

Run tests (optional):

1. .\venv\Scripts\Activate.ps1
2. python -m pip install -r requirements.txt
3. python -m pytest -q

## Configuration (Trivia Fetch)

Environment variables to tune trivia question fetching and caching:

- QUIZ_CACHE_TTL: Cache duration in seconds for fetched questions. Default: 120
- TRIVIA_TIMEOUT_SECONDS: HTTP timeout per request to OpenTDB. Default: 5
- TRIVIA_MAX_RETRIES: Number of attempts with simple linear backoff. Default: 3

Backoff pattern is linear at 0.4s increments per attempt (e.g., 0.0s, 0.4s, 0.8s for 3 retries).

