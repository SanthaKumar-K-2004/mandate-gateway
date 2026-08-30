# Staging & Production Deployment Checklist

## Pre-Flight Checklist

- [ ] **Environment Classification**: Verify `APP_ENV=production` is set in process environment.
- [ ] **Secret Sanitization**: Ensure `POSTGRES_PASSWORD`, `APP_SECRET`, `PROVIDER_API_KEY`, and `WEBHOOK_SECRET` are randomly generated and non-default.
- [ ] **Log Level**: Verify `LOG_LEVEL` is set to `INFO` or `WARNING` (never `DEBUG`).
- [ ] **Database Migration Head**: Run `alembic upgrade head` and verify schema version matches latest head revision.
- [ ] **Worker Process Topology**: Ensure `api`, `outbox_worker`, and `recovery_worker` containers are running independently.
- [ ] **Health & Readiness Validation**: Query `/health` and `/health/ready` to verify 200 OK responses.
- [ ] **Quality Gate Certification**: Verify `make check` passes 100% cleanly (0 lint, 0 type errors, 0 secret leaks).
- [ ] **Context Integrity**: Verify `sha256sum PROJECT_CONTEXT.md` equals `2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a`.
