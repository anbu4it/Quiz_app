# Project File Map

## Core Application
- `app.py` - Application factory, extension setup (DB, Migrate, CSRF, Session), security headers, auto-login test helpers.
- `wsgi.py` - Production entry point (`gunicorn wsgi:app`).
- `config.py` - Configuration class with DB URI, cookie/security settings, pool tuning.
- `models.py` - SQLAlchemy models: `User`, `Score` (UTC timestamp).

## Blueprints / Routes
- `routes/main_routes.py` - Home/index and simple pages.
- `routes/quiz_routes.py` - Quiz start (`/quiz`) and question navigation (`/question`).
- `routes/result_routes.py` - Result display and score persistence with duplicate guard.
- `routes/auth_routes.py` - Register, login, logout, profile (avatar upload), dashboard, leaderboard.

## Services
- `services/quiz_service.py` - Trivia API integration, caching, topic distribution, retry/backoff.
- `services/cloudinary_service.py` - Avatar upload/delete abstraction with fallback to local storage.
- `services/session_helper.py` - Session initialization utilities for quiz flow.

## Templates
- `templates/base.html` - Shared layout, navigation, dark mode toggle.
- `templates/index.html` - Landing page with topic selection.
- `templates/quiz.html` - Per-question view with progress bar.
- `templates/result.html` - Result summary and actions.
- `templates/auth/*.html` - Auth-related pages: register, login, profile, dashboard, leaderboard.
- `templates/404.html`, `templates/500.html` - Error pages.

## Static Assets
- `static/style.css` - Design tokens, layout, dark mode, components, utilities.
- `static/script.js` - Client-side quiz enhancements (if present).
- `static/images/` - Icons, default avatar, favicon.

## Tests
- `tests/test_app.py` - High-level integration tests (registration, login, protected routes).
- `tests/test_quiz_flow.py` - Deterministic complete quiz flow.
- `tests/test_duplicate_score_prevention.py` - Ensures result refresh doesn't duplicate scores.
- `tests/test_leaderboard_avatar.py` - Leaderboard rendering and avatar fallback.
- `tests/test_registration_csrf.py` - CSRF-enabled registration flow.
- `tests/test_registration_prefill.py` - Form prefill behavior on validation errors.
- `tests/test_trivia_service_retry.py` - Retry logic for external API calls.

## Deployment / Ops
- `render.yaml` - Render.com service definition (build & start commands, env vars).
- `build.sh` - Migration/build script.
- `requirements.txt` - Python dependencies.

## Housekeeping
- `pytest.ini` - Pytest settings & filtered warnings.
- `readme.md` - Project overview & usage.

## Key Data Flows
1. Registration -> auto-login -> dashboard redirect (cookies + session markers in test context).
2. Quiz start -> session-stored questions -> per-question POST -> result save -> redirect.
3. Avatar upload -> Cloudinary transform -> URL stored in `User.avatar` -> leaderboard/profile render via `avatar_url` filter.
4. Leaderboard aggregation -> SQL grouped queries for per-category and global stats.

## Notable Behaviors
- Duplicate score prevention: skips identical consecutive result inserts within short window heuristic.
- Multi-topic quiz distribution: base + remainder ensures consistent total question count.
- Test environment fallbacks: controlled auto-login to make CSRF registration deterministic without weakening production security.

## Potential Future Improvements
- Replace test-only auto-login fallbacks with explicit test helper mocks.
- Migrate from filesystem session to cookie or Redis in production.
- Add pagination for leaderboard categories if they grow large.
- Implement rate limiting middleware for quiz API calls.

