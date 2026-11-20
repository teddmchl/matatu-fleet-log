# Matatu Fleet Log

A Django app for matatu owners to record each vehicle's daily returns: trips, fare collections, fuel and other expenses, and the net for the day.

BBT 3101 Application Programming for the Internet, semester project.

## What it does
- **Accounts:** sign up, log in and log out using Django's built-in authentication. Passwords are hashed and checked by Django's password validators.
- **Sessions:** a login is kept in a database-backed session that lasts one 8-hour shift and ends when the browser closes. The app also remembers the last vehicle you logged a return for.
- **Vehicles:** add and edit your matatus. Plates are checked and normalised (`kdb456c` becomes `KDB 456C`).
- **Daily returns:** log and edit one return per vehicle per day. The form rejects future dates, negative amounts and collections with zero trips.
- **Access control:** every page except home, login and sign-up requires a login. You only see your own vehicles and returns; anyone else's give a 404.
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
| `/signup/`, `/accounts/login/`, `/accounts/logout/` | Accounts |
| `/vehicles/`, `/vehicles/new/`, `/vehicles/<id>/edit/` | Vehicles |
| `/returns/`, `/returns/new/`, `/returns/<id>/edit/` | Daily returns |
| `/admin/` | Django admin |
