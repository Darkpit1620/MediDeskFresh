# MediDeskFresh architecture

Django server-rendered portfolio application, organized into three domain apps.

- `clinic`: `Patient` 1-to-many `Appointment`; `Appointment` 1-to-1 `Consultation`. Staff can manage patients and appointments. Only assigned clinicians or superusers can manage consultation notes.
- `billing`: `Service`, `Invoice`, `InvoiceLine`, `Payment`; records manual payments with transaction checks and stores invoice-line prices at time of billing.
- `insights`: no persistent models; reports summarize clinic and billing records, enforcing Billing group/superuser access.

Django auth users/groups provide coarse role checks; SQLite backs the local demo. `.medidesk_local.json` supplies the local Django secret and is ignored by Git. The web app is intended for `127.0.0.1` development, not public hosting.

## Trust boundaries

Unauthenticated users can access the landing page and a simple health endpoint. Staff-only pages contain fictional patient/appointment records. Clinical notes are limited to Clinician group members and superusers, with ownership checks. Reports expose aggregate financial metrics to Billing group members and superusers.

## Persistence

SQLite `db.sqlite3` is generated only on local machines. Schema migrations are committed in each app's `migrations` folder. The database is not part of GitHub. Stage upgrade backups reside in `.medidesk_backups/` and are also excluded.
