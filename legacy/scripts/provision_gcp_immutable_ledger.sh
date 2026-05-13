#!/usr/bin/env bash
set -euo pipefail

# Usage:
# PROJECT_ID=misybot-ai-beta \
# REGION=us-central1 \
# TENANT_PREFIX=misybot-cali \
# ./scripts/provision_gcp_immutable_ledger.sh

PROJECT_ID="${PROJECT_ID:-misybot-ai-beta}"
REGION="${REGION:-us-central1}"
TENANT_PREFIX="${TENANT_PREFIX:-misybot-cali}"
RETENTION_DAYS="${RETENTION_DAYS:-7300}"

BUCKET_NAME="${TENANT_PREFIX}-immutable-ledger"
KEYRING_NAME="${TENANT_PREFIX}-kr"
KEY_NAME="${TENANT_PREFIX}-signing"
SA_NAME="${TENANT_PREFIX}-ledger-sa"

RETENTION_SECONDS=$((RETENTION_DAYS * 24 * 60 * 60))

echo "[1/8] Set project"
gcloud config set project "${PROJECT_ID}"

echo "[2/8] Enable required APIs"
gcloud services enable \
  cloudkms.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com

echo "[3/8] Create immutable bucket"
gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}" || true

echo "[4/8] Configure WORM retention policy (${RETENTION_DAYS} days)"
gcloud storage buckets update "gs://${BUCKET_NAME}" --retention-period="${RETENTION_SECONDS}s"

echo "[5/8] Lock retention policy (irreversible)"
# WARNING: this is irreversible. Comment out if you are still testing.
gcloud storage buckets lock-retention-policy "gs://${BUCKET_NAME}"

echo "[6/8] Create KMS keyring and asymmetric signing key"
gcloud kms keyrings create "${KEYRING_NAME}" --location="${REGION}" || true
gcloud kms keys create "${KEY_NAME}" \
  --location="${REGION}" \
  --keyring="${KEYRING_NAME}" \
  --purpose="asymmetric-signing" \
  --default-algorithm="ec-sign-p256-sha256" || true

echo "[7/8] Create service account"
gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="${TENANT_PREFIX} immutable-ledger service account" || true

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "[8/8] Grant least-privilege IAM"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudkms.signerVerifier"

cat <<EOF

Provisioning finished.

Use these .env values:
LEDGER_PROVIDER=gcp
GCP_PROJECT_ID=${PROJECT_ID}
GCP_LOCATION=${REGION}
GCP_TENANT_PREFIX=${TENANT_PREFIX}
GCP_IMMUTABLE_BUCKET=${BUCKET_NAME}
GCP_WORM_RETENTION_DAYS=${RETENTION_DAYS}
GCP_KMS_LOCATION=${REGION}
GCP_KMS_KEYRING=${KEYRING_NAME}
GCP_KMS_KEY=${KEY_NAME}

EOF
