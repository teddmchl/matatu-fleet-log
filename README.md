# Matatu Fleet Log

A Django app for matatu owners to record each vehicle's daily returns: trips, fare collections, fuel and other expenses, and the net for the day.

BBT 3101 Application Programming for the Internet, semester project.

## Apps
The project (`config`) holds settings and the root URLs. The work is split into three apps:

| App | Owns |
|---|---|
| `accounts` | sign-up, login/logout templates, profile page showing the current session |
| `fleet` | `Vehicle` and `DailyReturn` models, their forms and create/edit pages |
| `reports` | read-only per-vehicle totals for the last 7 days, 30 days or all time |

## What it does
- **Accounts:** sign up, log in and log out using Django's built-in authentication. Passwords are hashed and checked by Django's password validators.
- **Sessions:** a login is kept in a database-backed session that lasts one 8-hour shift and ends when the browser closes. The app also remembers the last vehicle you logged a return for.
- **Vehicles:** add and edit your matatus. Plates are checked and normalised (`kdb456c` becomes `KDB 456C`).
- **Daily returns:** log and edit one return per vehicle per day. The form rejects future dates, negative amounts and collections with zero trips.
- **Access control:** every page except home, login and sign-up requires a login. You only see your own vehicles and returns; anyone else's give a 404.
- **Reports:** per-vehicle trips, collections, expenses and net for a chosen period, worked out in the database with `annotate()` and `Sum()`.
- **Admin:** both models are registered at `/admin/` with search and filters.

## Models
```
User 1 ──< Vehicle 1 ──< DailyReturn >── 1 User (recorded_by)
```

## Run it
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # for /admin/
python manage.py runserver
```
Open http://127.0.0.1:8000/, sign up, add a vehicle, then log a return.

## Tests
```bash
python manage.py test
```

## Pages
| URL | Page |
|---|---|
| `/` | Home, with your totals once logged in |
| `/accounts/signup/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/` | Accounts |
| `/vehicles/`, `/vehicles/new/`, `/vehicles/<id>/edit/` | Vehicles |
| `/returns/`, `/returns/new/`, `/returns/<id>/edit/` | Daily returns |
| `/reports/?period=7\|30\|all` | Reports |
| `/admin/` | Django admin |
