# MIGRACIÓN A GOOGLE CLOUD — IU Digital · Analítica Académica

> **Estado**: Preparación arquitectónica completa. Sin cambios destructivos en el
> ambiente actual. La versión de Emergent se preserva como respaldo operativo
> hasta que la versión productiva en Google Cloud supere pruebas funcionales,
> de seguridad y de integridad de datos.

---

## 1. Arquitectura actual (Emergent)

| Componente | Tecnología | Ambiente actual |
|---|---|---|
| Frontend | React 19 (CRA) + Tailwind + shadcn/ui | Contenedor Emergent, servido por dev-server tras el proxy Emergent |
| Backend | FastAPI + Motor (async MongoDB) + Python 3.11 | Contenedor Emergent (supervisor + uvicorn) |
| Base de datos | MongoDB (Motor async client) | Instancia MongoDB local dentro del contenedor Emergent |
| Autenticación | JWT propio (bcrypt + HS256) | Vía `POST /api/auth/login`; login por email o cédula |
| IA | Emergent Universal Key vía `emergentintegrations.llm.chat.LlmChat` | Proxy Emergent hacia OpenAI GPT-4o (default) / Gemini (opcional cliente-side) |
| Correo | SMTP Gmail (App Password) O Gmail API con Service Account | SMTP legacy activo por default; Gmail API OAuth implementado como alternativa |
| Almacenamiento | No usa Object Storage — todos los datos residen en Mongo | N/A |
| Hosting | Contenedor Kubernetes en la nube de Emergent | `*.preview.emergentagent.com` |
| Dominio | Subdominio Emergent | `university-insights.preview.emergentagent.com` |
| CI/CD | Hot-reload gestionado por Emergent | No hay pipeline formal |

### Volumen de datos actuales (referencia)

| Colección | Documentos |
|---|---|
| `students` | 16.461 |
| `historico_notas` | 169.376 |
| `matriculas` | 92.439 |
| `grupos` | 1.311 |
| `docente_materia` | 737 |
| `divipola_municipios` | 480 |
| `users` | 404 |
| `programas` | 59 |
| `facultades` | 5 |
| `periodos` | 5 |
| `system_settings` | 4 |

---

## 2. Arquitectura objetivo (Google Cloud)

```
                          ┌───────────────────────────┐
   analitica.iudigital ──►│  Cloud Run · Frontend     │  (nginx + build React)
                          └───────────────┬───────────┘
                                          │  /api/*  (proxy o llamado directo)
                          ┌───────────────▼───────────┐
    api.analitica.iud... ►│  Cloud Run · Backend      │  (FastAPI + uvicorn)
                          │  Service Account: iud-app  │
                          └───┬───────────┬───────────┘
                              │           │
                    ┌─────────▼──┐   ┌────▼─────────────┐
                    │ Secret Mgr │   │ MongoDB Atlas    │  (region: us-central1)
                    │  · jwt-sec │   │ M10+ productivo  │
                    │  · mongo   │   │ Backup diario    │
                    │  · gemini  │   └──────────────────┘
                    └─────────┬──┘
                              │
                    ┌─────────▼────────────────┐
                    │ Vertex AI Gemini          │  (via ADC del runtime SA)
                    │ Gmail API (impersonation) │
                    └───────────────────────────┘

  Google Workspace (iudigital.edu.co)
   · Superadmin autoriza Domain-Wide Delegation del SA `iud-mail-sender`
   · Users institucionales autentican vía OAuth (Fase 2, opcional)
```

### Mapeo de componentes

| Componente | En Google Cloud | En Google Workspace |
|---|---|---|
| Frontend | **Cloud Run** (contenedor nginx) | — |
| Backend | **Cloud Run** (contenedor FastAPI) | — |
| Base de datos | **MongoDB Atlas en GCP** (o Firestore si se decide migrar de motor) | — |
| Secretos | **Secret Manager** | — |
| Envío de correo | **Gmail API con Service Account** + IAM impersonation | **Delegación en todo el dominio** (Admin Console) |
| Identidad institucional | OAuth 2.0 / OIDC (opcional Fase 2) | Cuentas @iudigital.edu.co |
| IA | **Vertex AI Gemini** (recomendado, usa ADC) o Gemini API con API key | — |
| Registro de imágenes | **Artifact Registry** | — |
| CI/CD | **Cloud Build** (opcional) | — |
| Monitoreo | **Cloud Logging + Monitoring** | — |
| Dominio | Cloud Load Balancer + Cloud DNS / Cloud Run mapeo directo | Dominio propiedad de IU Digital |

---

## 3. Dependencias de Emergent — Inventario y sustitución

| Dependencia | Ubicación | Sustitución en GCP |
|---|---|---|
| `EMERGENT_LLM_KEY` (env var) | `backend/.env` | Retirar. Usar Vertex AI Gemini (ADC) o `GEMINI_API_KEY` en Secret Manager |
| `emergentintegrations` (pip package) | `requirements.txt` | Reemplazar con `google-cloud-aiplatform` (Vertex) o `google-generativeai` (Gemini API directo) |
| `emergent.sh` script CDN | `frontend/public/index.html` línea 43 | Eliminar — no requerido en producción |
| Meta "A product of emergent.sh" | `frontend/public/index.html` línea 10 | Cambiar a descripción institucional IU Digital |
| `@emergentbase/visual-edits` (npm) | `frontend/package.json` | Eliminar antes de build de producción |
| URLs `*.preview.emergentagent.com` | tests + fallbacks | Reemplazar por dominio propio |
| Contenedor supervisor Emergent | Runtime | Sustituido por Cloud Run |
| MongoDB local (dentro del contenedor) | `MONGO_URL=mongodb://localhost:27017` | **MongoDB Atlas** (cluster dedicado en GCP) |

**Estado actual**: la aplicación **NO usa** almacenamiento de objetos, funciones serverless, ni servicios administrados propietarios de Emergent más allá del runtime y la clave universal LLM. La migración es **directa**.

---

## 4. Contenedorización

Se entregan Dockerfiles listos para Cloud Run:

- `backend/Dockerfile` — Python 3.11 slim + uvicorn (workers=2)
- `frontend/Dockerfile` — Multi-stage: Node 20 (build) + nginx alpine (runtime)
- `frontend/nginx.conf` — SPA routing + gzip + health `/healthz`

### Build local (verificación)

```bash
# Backend
cd backend
docker build -t iud-backend:local .
docker run --rm -p 8080:8080 \
  --env-file .env \
  iud-backend:local

# Frontend
cd frontend
docker build \
  --build-arg REACT_APP_BACKEND_URL=https://api.analitica.iudigital.edu.co \
  -t iud-frontend:local .
docker run --rm -p 8080:8080 iud-frontend:local
```

### Push a Artifact Registry

```bash
PROJECT_ID=iudigital-analitica
REGION=us-central1

gcloud auth configure-docker "${REGION}-docker.pkg.dev"

# Backend
docker tag iud-backend:local \
  "${REGION}-docker.pkg.dev/${PROJECT_ID}/iud-images/backend:$(date +%Y%m%d-%H%M)"
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/iud-images/backend:$(date +%Y%m%d-%H%M)"

# Frontend
docker tag iud-frontend:local \
  "${REGION}-docker.pkg.dev/${PROJECT_ID}/iud-images/frontend:$(date +%Y%m%d-%H%M)"
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/iud-images/frontend:$(date +%Y%m%d-%H%M)"
```

### Despliegue Cloud Run

```bash
# Backend
gcloud run deploy iud-backend \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/iud-images/backend:latest" \
  --region="$REGION" \
  --platform=managed \
  --service-account=iud-app-runtime@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars="DB_NAME=iudigital_analitica_prod,CORS_ORIGINS=https://analitica.iudigital.edu.co,APP_PUBLIC_URL=https://analitica.iudigital.edu.co" \
  --set-secrets="MONGO_URL=mongo-url:latest,JWT_SECRET=jwt-secret:latest,GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_SERVICE_ACCOUNT_JSON=gmail-sa-json:latest" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=300s

# Frontend
gcloud run deploy iud-frontend \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/iud-images/frontend:latest" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=256Mi \
  --min-instances=1
```

### Configuración CORS

- Backend `CORS_ORIGINS=https://analitica.iudigital.edu.co` (múltiples separados por coma si aplica)
- El código en `server.py` ya lee esa variable

### Health check

- Backend: `GET /api/health` retorna `{status,db}` — habilitado en esta iteración
- Frontend: `GET /healthz` retorna `200 ok`

### Logs

- `stdout/stderr` de uvicorn/nginx quedan automáticamente en **Cloud Logging**
- Query recomendada: `resource.type="cloud_run_revision"`

---

## 5. Base de datos — Migración

### 5.1 Estado actual

- **Motor**: MongoDB
- **Ubicación**: Contenedor Emergent (accesible sólo vía `MONGO_URL` local)
- **Colecciones**: 14 (ver tabla de volúmenes arriba)

### 5.2 Alternativa recomendada

**MongoDB Atlas en GCP** — mantiene compatibilidad total con el código actual (Motor + BSON + índices). Cero cambios en el código.

- Tier recomendado producción: **M10** (dedicated, 10GB SSD, backup diario incluido)
- Región: `us-central1` (misma que Cloud Run para minimizar latencia)
- Backup: continuo con Point-in-Time Recovery (PITR)
- IP allowlist: rangos NAT de Cloud Run o VPC peering

### 5.3 Esquema — Colecciones e índices

Los índices se crean automáticamente al arrancar el backend (`ensure_indexes()` en `database.py`). Colecciones principales:

- `users` — {id, email, password, role, docente_id?, facultad_id?, programa_id?, active, must_change_password, download_enabled, documento, credentials_sent_at}
  - Índices: `email` (unique), `documento`, `role`, `docente_id`
- `students` — {id, cedula, nombre, apellidos, programa, facultad, periodo, estado, sisben, victima, discapacidad, ruralidad, estrato, promedio, municipio_dane, ...}
  - Índices: `cedula` (unique), `facultad`, `programa`, `municipio_dane`, `promedio`
- `historico_notas` — {estudiante_cedula, materia_codigo, materia_nombre, periodo, nota, ...}
  - Índices: `estudiante_cedula`, `periodo`, compound `(estudiante_cedula,periodo)`
- `grupos`, `matriculas`, `programas`, `facultades`, `periodos`, `docente_materia`, `divipola_municipios`, `system_settings`, `uploads`, `historico`, `materias`

### 5.4 Procedimiento de migración

**Paso 1 — Exportar del ambiente actual** (dentro del contenedor Emergent, con permiso del equipo Emergent para acceder al Mongo local):

```bash
cd /app
./scripts/export_mongodb.sh ./backup_$(date +%Y%m%d)
# Genera un dump BSON comprimido en ./backup_YYYYMMDD/
```

**Paso 2 — Provisionar Atlas** (fuera del contenedor, en la consola Atlas):

1. Crear proyecto "IU Digital"
2. Crear cluster M10 en `us-central1`
3. Crear usuario de aplicación con role `readWrite@iudigital_analitica_prod`
4. Whitelist temporal 0.0.0.0/0 SÓLO para importación; luego restringir a Cloud Run

**Paso 3 — Importar**:

```bash
./scripts/import_atlas.sh ./backup_20260215 \
  "mongodb+srv://iud_app:PASSWORD@iud-cluster.xxxxx.mongodb.net" \
  iudigital_analitica_prod
```

**Paso 4 — Guardar URI en Secret Manager**:

```bash
echo "mongodb+srv://iud_app:PASSWORD@iud-cluster.xxxxx.mongodb.net" | \
  gcloud secrets versions add mongo-url --data-file=-
```

**Paso 5 — Verificar en el backend**:

Después de deploy, `GET /api/health` debe retornar `{"status":"ok","db":true}`.

### 5.5 Respaldo y recuperación

- **Atlas Continuous Backup** — snapshots cada 6h con retención 7 días
- **Point-In-Time Recovery** — restauración a cualquier segundo dentro de las últimas 72h
- **Exportación adicional semanal** — `mongodump` scheduled a un bucket de Cloud Storage
- **Procedimiento de restauración**: Atlas UI → Backup → Restore → clonar a cluster nuevo → cambiar `MONGO_URL` en Secret Manager → redeploy backend

---

## 6. Autenticación institucional (Fase 1: JWT actual; Fase 2 opcional: Google Workspace)

### Fase 1 — Mantener JWT actual (recomendado para el corte inicial)

- Usuarios existen en `users` con email institucional (`@iudigital.edu.co`)
- Login por email o cédula → hash bcrypt → JWT firmado con `JWT_SECRET` (Secret Manager)
- Roles preservados: `superadmin`, `direccion`, `decano`, `coordinador`, `profesor`
- **Cero cambios** en el código

### Fase 2 (opcional) — Login con Google Workspace

Añadir `POST /api/auth/google-callback` que:

1. Recibe el ID Token de Google (Sign-In con `hosted_domain: iudigital.edu.co`)
2. Verifica firma con `google.auth.transport`
3. Busca usuario en `users` por email
4. Si existe → emite JWT interno (mismo formato actual)
5. Si NO existe y el email pertenece a `iudigital.edu.co` → sugerir provisión al admin

Mapeo:
```
Cuenta Google Workspace  →  users.email  →  users.role  →  scope aplicado (scope.py)
```

Implementación estimada: 2-3 horas de desarrollo + config OAuth Client en GCP Console.

---

## 7. Correo institucional — Gmail API + Service Account

Ya implementado en el código (`backend/gmail_api_service.py`).

En Cloud Run existen **dos opciones** para pasar credenciales:

### Opción A — Vía Secret Manager (JSON completo)

- Admin genera JSON del Service Account `iud-mail-sender` y lo carga como secreto
- Cloud Run monta el secreto como env var `GOOGLE_SERVICE_ACCOUNT_JSON`
- La app usa ese JSON para impersonar `sender_email` con scope `gmail.send`

### Opción B — Sin JSON, usando IAM impersonation (recomendado GCP-native)

- El SA del runtime `iud-app-runtime` tiene rol `serviceAccountTokenCreator` sobre `iud-mail-sender`
- La app usa `google.auth.impersonated_credentials` para obtener tokens sin manejar JSON
- Requiere pequeño refactor de `gmail_api_service.py` (compatible con la opción A actual)

**Setup en Workspace Admin Console** (mismo que ya documentado en la UI):

1. Consola Admin → **Seguridad → Controles de API → Delegación en todo el dominio**
2. Añadir Client ID del SA `iud-mail-sender` con scope `https://www.googleapis.com/auth/gmail.send`

---

## 8. Inteligencia Artificial — Migración a Google

### Ruta preferida: Vertex AI Gemini

Ventajas:
- Sin API key: usa **ADC** del Service Account de Cloud Run
- Cuota, facturación y logs unificados con GCP
- Region control (`us-central1`)
- Soporte enterprise

Refactor requerido en `backend/routers/ai_router.py`:

```python
from google.cloud import aiplatform_v1
from vertexai.generative_models import GenerativeModel

vertex_model = GenerativeModel("gemini-3.6-flash")
resp = vertex_model.generate_content(user_text)
```

### Ruta alternativa: Gemini API directa

- Ya implementada. `GEMINI_API_KEY` en Secret Manager, `ai_provider=gemini_google` en la BD, modelo `gemini-3.6-flash`.
- Se mantiene como respaldo o si Vertex no está aprovisionado.

### Retiro de `EMERGENT_LLM_KEY`

- **Fase transición**: mantener `EMERGENT_LLM_KEY` como fallback durante 2-4 semanas.
- **Fase producción**: eliminar de env vars y de `requirements.txt` (quitar `emergentintegrations`).
- Reemplazo: instalar `google-generativeai>=0.8.0` o `google-cloud-aiplatform>=1.60.0`.

---

## 9. Secretos y variables de entorno — Inventario

| Variable | Categoría | Origen actual | Origen en GCP |
|---|---|---|---|
| `MONGO_URL` | Base de datos | `backend/.env` | **Secret Manager** `mongo-url` |
| `DB_NAME` | Base de datos | `backend/.env` | Env var (no sensible) |
| `CORS_ORIGINS` | Configuración | `backend/.env` | Env var |
| `APP_PUBLIC_URL` | Configuración | `backend/.env` (nuevo) | Env var |
| `JWT_SECRET` | Autenticación | `backend/.env` | **Secret Manager** `jwt-secret` |
| `JWT_ALGORITHM` | Autenticación | `backend/.env` | Env var |
| `JWT_EXPIRE_MINUTES` | Autenticación | `backend/.env` | Env var |
| `EMERGENT_LLM_KEY` | IA (retirar) | `backend/.env` | **Retirar en producción final** |
| `GEMINI_API_KEY` | IA | (nuevo) | **Secret Manager** `gemini-api-key` (o usar Vertex AI + ADC, no requerido) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Correo | (nuevo) | **Secret Manager** `gmail-sa-json` (o usar impersonation, no requerido) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Correo | (nuevo) | Ruta a secreto montado (alternativa a JSON en env) |
| `SEED_DEMO_DATA` | Configuración | `backend/.env` | Env var (`false` en prod) |
| `REACT_APP_BACKEND_URL` | Frontend | `frontend/.env` | Build arg del Dockerfile frontend |

**Regla**: los valores marcados como Secret Manager NUNCA se colocan en imagen docker ni en env vars planas; se inyectan con `--set-secrets` en el deploy de Cloud Run.

---

## 10. Configuración del dominio

**Opción recomendada**: Cloud Load Balancer + Cloud DNS.

1. IU Digital delega subdominios `analitica.iudigital.edu.co` y `api.analitica.iudigital.edu.co` en Cloud DNS
2. Certificados SSL gestionados automáticamente por Google
3. Mapeo:
   - `analitica.iudigital.edu.co` → Cloud Run frontend
   - `api.analitica.iudigital.edu.co` → Cloud Run backend
4. `CORS_ORIGINS` del backend = `https://analitica.iudigital.edu.co`
5. `REACT_APP_BACKEND_URL` del frontend build = `https://api.analitica.iudigital.edu.co`

**Alternativa simple** (para MVP): mapeo directo de Cloud Run al dominio (sin Load Balancer).

---

## 11. Pruebas — Plan mínimo antes del corte

1. **Smoke tests backend** — `GET /api/health` retorna `ok`; `POST /api/auth/login` con superadmin retorna JWT
2. **Integridad de datos** — comparar `db.students.count()` y `db.historico_notas.count()` entre Emergent y Atlas (deben coincidir)
3. **Dashboards** — cargar Ejecutivo, Académico, Territorial con superadmin: totales deben coincidir con producción actual
4. **Login por cédula** — profesor `1128441439` → debe pedir cambio de contraseña
5. **Envío de correo** — botón "Enviar prueba" en Configuración debe funcionar (con SA delegado)
6. **IA** — `POST /api/ai/insights` con provider `gemini_google` debe retornar texto > 500 chars
7. **RBAC** — profesor no debe ver estudiantes fuera de sus grupos (endpoint `/docente/mis-estudiantes` vs `/caracterizacion/*`)
8. **Regresión** — correr `pytest backend/tests/` (todos los tests deben pasar)

---

## 12. Paso a producción y rollback

### Estrategia de corte

- Semana 0: infraestructura provisionada, imágenes buildeadas, base de datos poblada en Atlas
- Semana 1: **canary** con 5 usuarios internos apuntando al dominio GCP (Emergent sigue operativo)
- Semana 2: switchover DNS completo a GCP; Emergent en modo lectura solamente
- Semana 3: monitoreo intensivo; si estable → Emergent se apaga

### Rollback

Ventaja: mientras Emergent no se apague, el rollback es solo **cambio de DNS**.

1. Volver `analitica.iudigital.edu.co` al proxy Emergent
2. Backend Emergent nunca se apaga hasta día D+14 mínimo
3. Datos: si hubo escrituras en Atlas post-corte, replicar de vuelta con `mongodump/mongorestore` en dirección inversa

---

## 13. Costos estimados (orden de magnitud, USD/mes)

| Servicio | Estimado |
|---|---|
| Cloud Run backend (1 vCPU, 1Gi, min=1) | 20-40 |
| Cloud Run frontend (256Mi, min=1) | 5-10 |
| MongoDB Atlas M10 | ~57 |
| Artifact Registry | 1-3 |
| Secret Manager | <1 |
| Cloud Logging + Monitoring | 5-15 |
| Vertex AI Gemini (uso moderado) | 20-60 |
| **Total mensual** | **~110-180 USD** |

Excluye: dominios (existentes en IU Digital), workspace admin (existente).

---

## 14. Archivos entregados en esta preparación

```
/app
├── backend/
│   ├── Dockerfile              ← NUEVO
│   ├── .dockerignore           ← NUEVO
│   ├── .env.example            ← NUEVO (inventario sin secretos)
│   └── (código sin cambios)
├── frontend/
│   ├── Dockerfile              ← NUEVO
│   ├── .dockerignore           ← NUEVO
│   ├── nginx.conf              ← NUEVO
│   ├── .env.example            ← NUEVO
│   └── (código sin cambios)
├── scripts/
│   ├── export_mongodb.sh       ← NUEVO
│   ├── import_atlas.sh         ← NUEVO
│   └── gcp_setup.sh            ← NUEVO
├── MIGRACION_GOOGLE_CLOUD.md   ← ESTE DOCUMENTO
└── CHECKLIST_ADMIN_INSTITUCIONAL.md ← Acciones para admin Workspace/GCP
```

### Cambios no destructivos en código

- `backend/server.py` — añadido endpoint `GET /api/health` (necesario para Cloud Run probes)
- `frontend/public/index.html` — el meta "emergent.sh" y el script CDN se dejan en preview; en el build de producción hay que quitarlos manualmente antes de `docker build` (ver checklist)

---

## 15. Descarga y auto-contención

El proyecto ya está listo para ser descargado como ZIP desde la plataforma
Emergent. Al desplegarse fuera de Emergent, verificar:

- ✅ Reemplazar valores del `.env.example` con secretos reales (en Secret Manager)
- ✅ Retirar `EMERGENT_LLM_KEY` cuando esté probado Gemini/Vertex
- ✅ Retirar `emergentintegrations` de `requirements.txt` en la fase final
- ✅ Retirar `@emergentbase/visual-edits` de `package.json`
- ✅ Retirar `<script src="https://assets.emergent.sh/…">` de `frontend/public/index.html`
- ✅ Retirar meta "A product of emergent.sh"
- ✅ Reemplazar URLs de tests apuntando a `preview.emergentagent.com`

---

## 16. Contacto y siguientes pasos

1. Entregar este documento + `CHECKLIST_ADMIN_INSTITUCIONAL.md` al equipo de TI de IU Digital
2. Solicitar la aprobación de:
   - Proyecto GCP + billing account
   - Delegación DNS del subdominio `analitica.iudigital.edu.co`
   - Delegación en todo el dominio para el SA `iud-mail-sender`
3. Ejecutar `scripts/gcp_setup.sh` (después de revisarlo)
4. Ejecutar `scripts/export_mongodb.sh` desde el contenedor Emergent
5. Ejecutar `scripts/import_atlas.sh` hacia el cluster Atlas nuevo
6. Deploy Cloud Run
7. Smoke tests → cutover DNS → observabilidad 14 días → apagar Emergent
