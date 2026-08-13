# IU Digital · Analítica y Caracterización Académica

Aplicación de analítica académica institucional para la IU Digital de Antioquia.
Stack: **React 19 + Tailwind + shadcn/ui** (frontend) · **FastAPI + Motor + MongoDB**
(backend) · IA vía Google Gemini.

---

## Arquitectura rápida

```
frontend/    → React CRA — dashboards ejecutivo, académico, territorial, docente
backend/     → FastAPI — routers/, models, RBAC scope, integración IA + email
scripts/     → Migración: export/import Mongo, bootstrap GCP
```

## Ambientes

- **Actual (Emergent)** — preview URL, MongoDB local. Ver `frontend/.env` y `backend/.env`.
- **Objetivo (Google Cloud)** — Cloud Run + MongoDB Atlas + Secret Manager. Ver `MIGRACION_GOOGLE_CLOUD.md`.

## Documentación de migración

- 📘 [`MIGRACION_GOOGLE_CLOUD.md`](./MIGRACION_GOOGLE_CLOUD.md) — plan completo de migración
- ✅ [`CHECKLIST_ADMIN_INSTITUCIONAL.md`](./CHECKLIST_ADMIN_INSTITUCIONAL.md) — acciones para admin Workspace/GCP
- 🐳 [`backend/Dockerfile`](./backend/Dockerfile), [`frontend/Dockerfile`](./frontend/Dockerfile) — imágenes productivas
- 🛠 [`cloudbuild.yaml`](./cloudbuild.yaml) — pipeline CI/CD para Cloud Build
- 📦 [`scripts/export_mongodb.sh`](./scripts/export_mongodb.sh), [`scripts/import_atlas.sh`](./scripts/import_atlas.sh), [`scripts/gcp_setup.sh`](./scripts/gcp_setup.sh)

## Documentación funcional

- `memory/PRD.md` — requerimientos del producto
- `memory/test_credentials.md` — credenciales de prueba
- `design_guidelines.md` — lineamientos UI/UX

## Ejecutar localmente

Ver [`backend/.env.example`](./backend/.env.example) y [`frontend/.env.example`](./frontend/.env.example).

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn server:app --reload --port 8001

# Frontend
cd frontend && yarn install && yarn start
```

## Endpoints clave

- `GET /api/health` — liveness (Cloud Run probe)
- `POST /api/auth/login` — login por email o cédula
- Dashboards: `/api/dashboards/ejecutivo`, `/academico`, `/territorial`, etc.
- IA: `/api/ai/insights`, `/api/ai/docente/alerta-estudiante`
- Config: `/api/config/overview`, `/api/config/smtp`, `/api/config/gmail-api`, `/api/config/ai`
