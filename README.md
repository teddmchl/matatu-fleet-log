# Matatu Fleet Log

A Django web app for matatu owners and SACCOs to record each vehicle's daily returns: trips made, fares collected, fuel and other expenses, and the net for the day. Owners see their own fleet, log one return per vehicle per day, and get per-vehicle totals for the last 7 days, 30 days or all time. The same data is available as a small JSON API.

BBT 3101 Application Programming for the Internet, semester project.

## Features by course topic
| Topic | Where it shows up |
|---|---|
| HTML5 & CSS3 | Semantic layout in `templates/base.html` (header, nav, main, footer); responsive stylesheet `static/css/style.css` (mobile-first, tables scroll on phones) |
| Python | Form validation (`fleet/forms.py`), plate normalisation with a regex, `net` computed property, settings read from the environment |
| Django fundamentals | Project `config` plus three apps (`accounts`, `fleet`, `reports`), namespaced URLs, views, template inheritance |
| Forms & user input | `VehicleForm` and `DailyReturnForm` are ModelForms with `clean_<field>()` and `clean()` rules; GET shows a form, POST validates and saves |
| Databases & ORM | `Vehicle` and `DailyReturn` models with foreign keys, a unique constraint, migrations; reports use `annotate()` and `Sum()` in the database. SQLite locally, PostgreSQL through `DATABASE_URL` |
| CRUD | Create, list, edit and delete for vehicles and daily returns; deletes need a confirm page and a POST |
| Authentication & authorisation | Sign-up, login, logout, password change with Django's auth; every query is filtered by the logged-in user, so other users' records give a 404 |
| Sessions | Database-backed session lasting one 8-hour shift and ending when the browser closes; remembers the last vehicle you logged |
| Security | CSRF tokens on every form and the API POST, template auto-escaping (XSS), ORM queries (no raw SQL), hashed passwords, secrets from the environment, HTTPS-only cookies and HSTS in production; `check --deploy` is clean |
| Web APIs & JSON | `fleet/api.py`: JSON endpoints with proper status codes (200, 201, 400, 401, 404, 405) |
| Integration & deployment | Automated tests (`python manage.py test`), `.env.example`, gunicorn, WhiteNoise, `Procfile` and `build.sh` |

## Apps
| App | Owns |
|---|---|
| `accounts` | sign-up, login/logout templates, profile page showing the current session, security tests |
| `fleet` | `Vehicle` and `DailyReturn` models, their forms, CRUD pages and the JSON API |
| `reports` | read-only per-vehicle totals for the last 7 days, 30 days or all time |

## Models
```
User 1 ──< Vehicle 1 ──< DailyReturn >── 1 User (recorded_by)
```
Deleting a vehicle deletes its daily returns (`CASCADE`). A user who has logged returns can't be deleted (`PROTECT`), so the record of who logged what is kept.

## Run it locally
Needs Python 3.12 or newer (Django 6.1).

```bash
git clone https://github.com/teddmchl/matatu-fleet-log.git
cd matatu-fleet-log
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # for /admin/
python manage.py runserver
```
Open http://127.0.0.1:8000/, sign up, add a vehicle, then log a return.

No `.env` file is needed for local development: the defaults run in debug mode on SQLite.

## Tests
```bash
python manage.py test
```
Covers models, form rules, access control, sessions, CRUD including deletes, the JSON API, CSRF, XSS escaping, password hashing and the production settings.

## Configuration
Settings that differ between a laptop and a server come from environment variables. Copy `.env.example` to `.env` to set them locally; on a server set them in the host's dashboard.

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `1` for development, `0` for production (turns on HTTPS redirect, secure cookies, HSTS) |
| `DJANGO_SECRET_KEY` | dev-only key | Required when `DJANGO_DEBUG=0`; the app refuses to start without it |
| `DJANGO_ALLOWED_HOSTS` | empty | Comma-separated host names, e.g. `matatu-fleet-log.onrender.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` + each allowed host | Origins allowed to POST forms |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | e.g. `postgres://user:pass@host:5432/matatu` |

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Check the production settings:
```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY='<your key>' DJANGO_ALLOWED_HOSTS=example.com python manage.py check --deploy
```

## Pages
| URL | Page |
|---|---|
| `/` | Home, with your totals once logged in |
| `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/` | Accounts |
| `/vehicles/`, `/vehicles/new/`, `/vehicles/<id>/edit/`, `/vehicles/<id>/delete/` | Vehicles |
| `/returns/`, `/returns/new/`, `/returns/<id>/edit/`, `/returns/<id>/delete/` | Daily returns |
| `/reports/?period=7\|30\|all` | Reports |
| `/admin/` | Django admin |

## JSON API
The API uses the same login session as the website. Anonymous requests get `401 {"error": "Authentication required."}`. You only ever see your own vehicles and returns.

| Method | URL | Returns |
|---|---|---|
| GET | `/api/csrf/` | `{"csrfToken": "..."}` and sets the `csrftoken` cookie |
| GET | `/api/vehicles/` | `{"vehicles": [...]}` |
| GET | `/api/vehicles/<id>/` | one vehicle, or 404 |
| GET | `/api/returns/?vehicle=<id>&date=YYYY-MM-DD` | `{"returns": [...]}` (both filters optional; bad values give 400) |
| POST | `/api/returns/` | the new return with `201`, or `400 {"errors": {...}}` |

Money is sent as strings (`"9500.00"`) so no cents are lost to rounding.

POST is CSRF-protected like every form on the site. A client fetches a token and sends it back in the `X-CSRFToken` header. The body is validated by the same `DailyReturnForm` as the web page, so the same rules apply.

Example with curl, against `runserver`:
```bash
# 1. log in and keep the session cookie
curl -c jar.txt -b jar.txt -s http://127.0.0.1:8000/accounts/login/ > /dev/null
TOKEN=$(grep csrftoken jar.txt | awk '{print $7}')
curl -c jar.txt -b jar.txt -s -X POST http://127.0.0.1:8000/accounts/login/ \
  -H "Referer: http://127.0.0.1:8000/accounts/login/" \
  -d "csrfmiddlewaretoken=$TOKEN&username=wanjiku&password=<your password>" > /dev/null

# 2. read
curl -b jar.txt -s http://127.0.0.1:8000/api/vehicles/
curl -b jar.txt -s "http://127.0.0.1:8000/api/returns/?date=2026-11-28"

# 3. create (login rotates the CSRF token, so read it again)
TOKEN=$(curl -c jar.txt -b jar.txt -s http://127.0.0.1:8000/api/csrf/ | python3 -c "import sys, json; print(json.load(sys.stdin)['csrfToken'])")
curl -b jar.txt -s -X POST http://127.0.0.1:8000/api/returns/ \
  -H "Content-Type: application/json" -H "X-CSRFToken: $TOKEN" \
  -d '{"vehicle": 1, "date": "2026-11-28", "trips": 8, "collections": "9500", "fuel": "3500", "other_expenses": "800"}'
```

## Deploy (Render or any similar host)
1. Push the repo to GitHub and create a new **Web Service** from it.
2. Build command: `./build.sh` (installs requirements, runs `collectstatic` and `migrate`).
3. Start command: `gunicorn config.wsgi` (the same as the `Procfile`).
4. Environment variables: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<generated key>`, and `DATABASE_URL` from a Postgres database. On Render the host name is added to `ALLOWED_HOSTS` automatically; elsewhere set `DJANGO_ALLOWED_HOSTS`.
5. Create an admin account from the host's shell: `python manage.py createsuperuser`.

In production WhiteNoise serves the CSS from gunicorn with compression and hashed file names, so no separate static file server is needed.
