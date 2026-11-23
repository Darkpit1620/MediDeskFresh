# Security and privacy (portfolio demo only)

**Never enter real patient, medical, financial or contact information.** This demonstration is not a production electronic health record or clinical billing product.

The app uses Django authentication, staff/group permissions, CSRF protection, password validation, HTTP-only session and CSRF cookies, clickjacking protection, and some clinician ownership rules. These are educational measures, not full medical-data security controls.

Local secrets in `.medidesk_local.json`, `.env`, local SQLite databases, `.venv`, backup folders, logs, CSV reports and uploaded files are excluded by `.gitignore`. Before a public push, run the supplied safety scan and **manually review every tracked file**, especially source code, templates, screenshots, Git history, commit messages and examples. GitHub Actions tests use a throwaway local secret and test database.

Important gaps for real clinics include professional threat modeling, data minimization and consent workflows, field encryption and encrypted backups, access audits and monitoring, granular authorization, retention/deletion policies, disaster recovery, health-data compliance review, and controlled hosting. The default DEBUG/localhost settings are **not** suitable for production. Never expose the development server publicly.

If a secret was ever committed, removing a file from the latest commit is not sufficient. Rotate the secret and remove it from the full repository history before sharing.
