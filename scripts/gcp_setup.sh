#!/usr/bin/env bash
# =============================================================================
# Bootstrap de infraestructura GCP para IU Digital Analítica Académica
# =============================================================================
# EJECUTA UN ADMINISTRADOR con permisos de Owner o Project Creator sobre el
# proyecto/organización de IU Digital.
#
# Uso: revisar/ajustar variables y ejecutar paso a paso (NO ejecutar todo el
# archivo de una vez la primera vez).
# =============================================================================

# ---------- Variables ----------
PROJECT_ID="iudigital-analitica"
REGION="us-central1"
BACKEND_SVC="iud-backend"
FRONTEND_SVC="iud-frontend"
SA_APP="iud-app-runtime"
SA_MAIL="iud-mail-sender"

# ---------- 1. Crear proyecto ----------
gcloud projects create "$PROJECT_ID" --name="IU Digital Analítica"
gcloud config set project "$PROJECT_ID"

# ---------- 2. Habilitar APIs necesarias ----------
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
  monitoring.googleapis.com

# ---------- 3. Artifact Registry (repo de imágenes docker) ----------
gcloud artifacts repositories create iud-images \
  --repository-format=docker \
  --location="$REGION" \
  --description="IU Digital Analítica images"

# ---------- 4. Service Accounts ----------
# 4.1 Runtime del backend (usado por Cloud Run)
gcloud iam service-accounts create "$SA_APP" \
  --display-name="IU Digital App Runtime"

# 4.2 Envío de correo institucional (Domain-Wide Delegation en Workspace)
gcloud iam service-accounts create "$SA_MAIL" \
  --display-name="IU Digital Mail Sender"

# ---------- 5. Permisos IAM ----------
APP_SA="${SA_APP}@${PROJECT_ID}.iam.gserviceaccount.com"

# Acceder a Secret Manager
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${APP_SA}" \
  --role="roles/secretmanager.secretAccessor"

# Escribir logs
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${APP_SA}" \
  --role="roles/logging.logWriter"

# Usar Vertex AI Gemini
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${APP_SA}" \
  --role="roles/aiplatform.user"

# Impersonar al mail sender (para no requerir el JSON en Cloud Run)
gcloud iam service-accounts add-iam-policy-binding \
  "${SA_MAIL}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --member="serviceAccount:${APP_SA}" \
  --role="roles/iam.serviceAccountTokenCreator"

# ---------- 6. Secretos ----------
# JWT (generar nuevo, no reutilizar el de Emergent)
openssl rand -hex 64 | gcloud secrets create jwt-secret \
  --replication-policy="automatic" \
  --data-file=-

# MongoDB Atlas URI (pegar el valor cuando se pida)
gcloud secrets create mongo-url --replication-policy="automatic"
echo "→ Pegue MONGO_URL de Atlas y presione Ctrl+D:"
gcloud secrets versions add mongo-url --data-file=-

# Service Account JSON del mail sender (para delegación de Workspace)
# Solo si el admin de Workspace lo requiere en JSON en lugar de impersonación IAM
# gcloud secrets create gmail-sa-json --replication-policy="automatic"
# gcloud secrets versions add gmail-sa-json --data-file=./mail-sa-key.json

# Gemini API key (fallback si no se usa Vertex AI)
# gcloud secrets create gemini-api-key --replication-policy="automatic"
# echo "AQ.Ab...." | gcloud secrets versions add gemini-api-key --data-file=-

# Dar acceso al backend a los secretos
for SECRET in jwt-secret mongo-url; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${APP_SA}" \
    --role="roles/secretmanager.secretAccessor"
done

echo ""
echo "✓ Infraestructura base creada."
echo "→ Siguiente paso: seguir MIGRACION_GOOGLE_CLOUD.md sección 'Despliegue Cloud Run'."
