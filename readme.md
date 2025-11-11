# BrainRush

Modern, theme-aware quiz platform built with Flask, Bootstrap 5, and SQLAlchemy.

Highlights:
- Light/dark themes with smooth gradients and soft shadows
- Polished home, quiz, and result flows with animations
- Shareable results, confetti for high scores, and subtle micro-interactions
- Secure auth, CSRF protection, and production-ready deployment on Render

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
3. $env:PYTEST_CURRENT_TEST="1"; python -m pytest -q

Note: Setting PYTEST_CURRENT_TEST before collection prevents accidental server startup during imports.

## Design overview

Pages refreshed for a cohesive look-and-feel:
- Base layout: theme toggle, refined navbar, sticky flash area, and footer
- Home: orb accent, topic chips with All/Clear controls, better micro-interactions
- Quiz: sleeker options UI and animated progress
- Result: modern score card with animated percentage, share button, and confetti on high scores
- Errors: friendly 404/500 pages with quick actions
- Profile: clearer avatar upload with guidelines and improved layout

Styling uses CSS variables defined in `static/style.css` for easy theme customization.

Screenshots (optional placeholders):
```
static/images/screenshots/
	home.png
	quiz.png
	result.png
```

## Configuration (Trivia Fetch)

Environment variables to tune trivia question fetching and caching:

- QUIZ_CACHE_TTL: Cache duration in seconds for fetched questions. Default: 120
- TRIVIA_TIMEOUT_SECONDS: HTTP timeout per request to OpenTDB. Default: 5
- TRIVIA_MAX_RETRIES: Number of attempts with simple linear backoff. Default: 3

Backoff pattern is linear at 0.4s increments per attempt (e.g., 0.0s, 0.4s, 0.8s for 3 retries).

