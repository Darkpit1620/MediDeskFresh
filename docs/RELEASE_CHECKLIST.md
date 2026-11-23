# Release checklist — MediDeskFresh

- [ ] Stage 1, 2 and 3 have installed successfully with local test results.
- [ ] `python manage.py check` passes.
- [ ] `python manage.py makemigrations --check --dry-run` passes; committed migrations exist for `clinic` and `billing`.
- [ ] `python manage.py test --noinput` passes.
- [ ] `python -m pip check` passes.
- [ ] `check_medidesk_github_safety.py` passes on staged Git files.
- [ ] Manual review confirms no actual patient names, contacts, clinical records, financial data, keys, tokens, credentials or backups exist anywhere in tracked files or Git history.
- [ ] `.medidesk_local.json`, `.venv`, `db.sqlite3`, backup and build log directories are untracked.
- [ ] `git diff --cached --name-only` lists only intended public files.
- [ ] Commit and push to a dedicated public `MediDeskFresh` repository.
- [ ] Check GitHub Actions results after upload; investigate any failure before describing the release as verified.

This check is for a portfolio demo, **not** a production healthcare release.
