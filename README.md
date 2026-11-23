# MediDeskFresh — Clinic Management Portfolio Demo

**Portfolio demonstration. Use fictional patient information only.** MediDeskFresh is not authorized or hardened for live medical records, patient care, real payments, or production healthcare deployment.

## Features

- Patient directory and appointment scheduling
- Clinician-only consultations, vital signs, draft editing and sign-off
- Clinic service catalogue, invoices and manually recorded payments (no payment gateway)
- Staff-restricted monthly clinic activity and financial summary reports with aggregate CSV export
- Django admin, automated Django tests, and a role-based access demonstration

## Technology

Python 3.12 (recommended), Django 5.2, SQLite for local development, Django templates, CSS.

## Install from a fresh GitHub clone (Windows PowerShell)

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -c 'import json,secrets,pathlib; pathlib.Path(".medidesk_local.json").write_text(json.dumps({"SECRET_KEY":secrets.token_urlsafe(56),"DEBUG":True}))'
& '.\.venv\Scripts\python.exe' manage.py migrate --noinput
& '.\.venv\Scripts\python.exe' manage.py setup_roles
& '.\.venv\Scripts\python.exe' manage.py setup_billing_role
& '.\.venv\Scripts\python.exe' manage.py createsuperuser
& '.\.venv\Scripts\python.exe' manage.py runserver 8005
```

Visit `http://127.0.0.1:8005/`. The generated `.medidesk_local.json` is intentionally excluded from Git. Use `python manage.py seed_demo` **only** for fictional demo records.

## Checks

```powershell
& '.\.venv\Scripts\python.exe' manage.py check
& '.\.venv\Scripts\python.exe' manage.py makemigrations --check --dry-run
& '.\.venv\Scripts\python.exe' manage.py test --noinput
& '.\.venv\Scripts\python.exe' check_medidesk_github_safety.py
```

The project has a GitHub Actions CI workflow which repeats checks on new commits.

## Code map

- `clinic/`: patient, appointment, consultation models, views, forms and tests
- `billing/`: service catalogue, invoice lines, payments and tests
- `insights/`: permission-restricted read-only reports and summary CSV exports
- `config/`: Django project settings and URL routing
- `docs/`: architecture, security guidance and release checklist

## Important limitations

No encryption-at-rest or field-level encryption, comprehensive security audit, consent management, clinical governance, regulatory compliance certification, backups/restore orchestration, HIPAA-compliant hosting, production deployment hardening or live payment integration is provided. For production deployment, undertake a separate expert security, privacy, operational and legal review. See `docs/SECURITY_AND_PRIVACY.md`.
