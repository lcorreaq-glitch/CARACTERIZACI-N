# CHECKLIST — Administrador institucional Google Workspace / Google Cloud
## Aplicativo de Caracterización y Analítica Académica · IU Digital

Este documento lista **únicamente** las acciones que dependen de cuentas con
permisos institucionales. El equipo de desarrollo NO puede ejecutarlas por
usted, aunque sí lo asistirá con comandos y capturas.

---

## Leyenda

| Marca | Significado |
|:-:|---|
| 🅐 | Puede ejecutarlo el equipo de desarrollo con acceso al proyecto GCP |
| 🅑 | Requiere **Superadministrador de Google Workspace** de `iudigital.edu.co` |
| 🅒 | Requiere rol IAM `Owner` u `Organization Admin` en Google Cloud |

---

## 1. Proyecto Google Cloud (🅒)

- [ ] Crear proyecto GCP: nombre `iudigital-analitica` (o el que apruebe TI)
- [ ] Asociar una **billing account** institucional al proyecto
- [ ] Confirmar región primaria: `us-central1` (recomendado por proximidad y disponibilidad de servicios)
- [ ] Delegar acceso al equipo de desarrollo con roles mínimos:
  - `roles/run.admin` (deploy de Cloud Run)
  - `roles/artifactregistry.writer` (push de imágenes)
  - `roles/secretmanager.admin` (rotar secretos)
  - `roles/iam.serviceAccountUser` (usar SAs)

## 2. APIs a habilitar (🅐 con permisos delegados)

Ejecutar (una sola vez):

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  gmail.googleapis.com \
  aiplatform.googleapis.com \
  generativelanguage.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  dns.googleapis.com
```

- [ ] Confirmar que todas las APIs quedan en estado ENABLED

## 3. Cuentas de servicio (🅐)

- [ ] Crear SA `iud-app-runtime` (identidad del backend en Cloud Run)
- [ ] Crear SA `iud-mail-sender` (impersona al remitente de correo en Workspace)
- [ ] Anotar el **numeric Client ID** del SA `iud-mail-sender` — se usa en el paso 6

## 4. Permisos IAM (🅒)

Asignar al SA `iud-app-runtime`:

- [ ] `roles/secretmanager.secretAccessor` — leer secretos
- [ ] `roles/logging.logWriter` — escribir logs
- [ ] `roles/aiplatform.user` — invocar Vertex AI Gemini
- [ ] `roles/iam.serviceAccountTokenCreator` **sobre `iud-mail-sender`** — impersonar para enviar correos

## 5. Secret Manager (🅐 con roles del paso 1)

Crear los siguientes secretos y cargar sus valores:

- [ ] `jwt-secret` — generar nuevo con `openssl rand -hex 64`. **NO reutilizar el actual de Emergent.**
- [ ] `mongo-url` — connection string del cluster MongoDB Atlas (paso 7)
- [ ] `gemini-api-key` — API key de Google AI Studio (opcional si se usa Vertex AI + ADC)
- [ ] `gmail-sa-json` — JSON del SA `iud-mail-sender` (opcional si se usa impersonation IAM)

## 6. Google Workspace Admin Console (🅑)

⚠️ **SOLO EL SUPERADMINISTRADOR** de `iudigital.edu.co` puede hacer esto.

1. Ir a **[admin.google.com](https://admin.google.com)** con la cuenta superadmin
2. Menú → **Seguridad → Control de acceso y datos → Controles de API → Delegación en todo el dominio**
3. Clic en **Añadir nuevo**
4. Rellenar:
   - **ID de cliente**: el numeric Client ID del SA `iud-mail-sender` (paso 3)
   - **Alcances de OAuth**: pegar exactamente:
     ```
     https://www.googleapis.com/auth/gmail.send
     ```
5. Clic en **Autorizar**

- [ ] Confirmar que la delegación aparece en la lista con el Client ID correcto
- [ ] Confirmar el correo remitente institucional que se impersonará (ej: `gestion.cienciasyhumanidades@iudigital.edu.co`) tiene la cuenta activa

**Si el aplicativo también implementará login OAuth con Workspace** (Fase 2 opcional):

- [ ] Adicionalmente en Admin Console → **Seguridad → Autenticación → OAuth 2.0** → añadir el OAuth Client ID del app (se genera en GCP Console → APIs & Services → Credentials)

## 7. Base de datos — MongoDB Atlas en GCP (🅐 con billing)

- [ ] Crear cuenta Atlas o usar existente institucional
- [ ] Crear organización "IU Digital"
- [ ] Crear proyecto "Analitica"
- [ ] Provisionar cluster **M10** en `us-central1` (misma región que Cloud Run)
- [ ] Configurar **Continuous Backup** con retención mínima 7 días
- [ ] Crear usuario aplicación:
  - Username: `iud_app`
  - Role: `readWrite@iudigital_analitica_prod`
- [ ] Guardar la connection string en Secret Manager como `mongo-url` (paso 5)
- [ ] IP Access List:
  - Temporalmente `0.0.0.0/0` para la importación inicial (ver script `scripts/import_atlas.sh`)
  - Luego restringir a los rangos NAT de Cloud Run o configurar **VPC peering** entre GCP y Atlas

## 8. Dominio y DNS (🅑 + 🅒)

- [ ] Confirmar propiedad del dominio `iudigital.edu.co`
- [ ] Delegar subdominios `analitica.iudigital.edu.co` y `api.analitica.iudigital.edu.co` a Cloud DNS **o** crear registros CNAME directamente hacia Cloud Run
- [ ] Solicitar certificados SSL gestionados (automático con Cloud Run + custom domain mapping)

## 9. Vertex AI (recomendado para IA productiva) (🅒)

Sólo si se desea eliminar `GEMINI_API_KEY` y usar identidad IAM en lugar de key:

- [ ] Habilitar Vertex AI en la región `us-central1`
- [ ] Confirmar que el SA `iud-app-runtime` tiene `roles/aiplatform.user`

## 10. Registro de imágenes Docker (🅐)

- [ ] Crear repositorio Artifact Registry: `iud-images` (Docker, `us-central1`)
- [ ] Configurar acceso desde Cloud Build al repositorio

## 11. Despliegue Cloud Run (🅐)

Con todo lo anterior listo, el equipo de desarrollo puede ejecutar:

- [ ] `docker build` + `docker push` del backend
- [ ] `docker build` + `docker push` del frontend (con `REACT_APP_BACKEND_URL` como build arg)
- [ ] `gcloud run deploy iud-backend …` (ver comandos en `MIGRACION_GOOGLE_CLOUD.md`)
- [ ] `gcloud run deploy iud-frontend …`

## 12. Verificación end-to-end (🅐 con soporte 🅑 para prueba de correo)

- [ ] `curl https://api.analitica.iudigital.edu.co/api/health` retorna `{status:"ok"}`
- [ ] Ingresar como superadmin — dashboards muestran datos idénticos a la versión Emergent
- [ ] Enviar correo de prueba desde Configuración → Correo Gmail API
- [ ] Generar insight IA en dashboard Ejecutivo — respuesta > 500 chars
- [ ] Ingresar como profesor `1128441439` — pide cambio de contraseña
- [ ] Ver mapa territorial — 573 municipios cargados

## 13. Migración de datos (🅐)

- [ ] Ejecutar `./scripts/export_mongodb.sh` desde el ambiente Emergent (con acceso local a Mongo)
- [ ] Transferir el dump por canal seguro (Google Drive institucional, o `gsutil cp` a un bucket privado)
- [ ] Ejecutar `./scripts/import_atlas.sh <dump> <atlas_uri> iudigital_analitica_prod`
- [ ] Confirmar conteos de documentos (comparar con tabla de referencia en `MIGRACION_GOOGLE_CLOUD.md`)

## 14. Retiro de dependencias Emergent (🅐)

Ejecutar **solo cuando la versión GCP ya esté aprobada** y en producción estable:

- [ ] Eliminar `EMERGENT_LLM_KEY` de env vars y Secret Manager
- [ ] Retirar `emergentintegrations` de `backend/requirements.txt` (reemplazar por `google-generativeai` o `google-cloud-aiplatform`)
- [ ] Refactorizar `backend/routers/ai_router.py` — cambiar `LlmChat` por `GenerativeModel` de Vertex/Gemini
- [ ] Retirar `@emergentbase/visual-edits` de `frontend/package.json`
- [ ] Retirar `<script src="https://assets.emergent.sh/…">` de `frontend/public/index.html`
- [ ] Retirar meta description "A product of emergent.sh"

## 15. Cutover y respaldo (🅐 + 🅒)

- [ ] Semana 0: infraestructura lista, cluster Atlas poblado, deploys hechos
- [ ] Semana 1: canary (5 usuarios apuntando a dominio GCP; Emergent sigue operativo en paralelo)
- [ ] Semana 2: switchover DNS al ambiente GCP (Emergent en modo lectura-solo o apagado)
- [ ] Semana 3: monitoreo intensivo; confirmar métricas normales
- [ ] Semana 4: apagar el contenedor Emergent (**no eliminar el proyecto hasta día 60 mínimo**)

## 16. Contactos requeridos

| Rol | Función | Persona/área a definir |
|---|---|---|
| Superadmin Workspace | Autorizar delegación Gmail API | TI IU Digital |
| Owner GCP | Crear proyecto + billing | TI IU Digital |
| DBA / Atlas admin | Provisionar cluster | TI IU Digital |
| DNS admin | Delegar subdominios | TI IU Digital |
| Equipo desarrollo | Build + deploy | Emergent / interno |

---

## Notas finales

- **La versión actual en Emergent NO se apaga** hasta que la versión GCP haya
  pasado 14 días en producción estable.
- Todos los secretos deben rotarse antes del cutover (JWT, DB password).
- Backup verificado antes del cutover: importar snapshot a un cluster de test y
  correr la app contra él para confirmar integridad.
- Documento vivo: cualquier ajuste al plan debe reflejarse en este archivo.
