#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run Deployment Script for GitHub Roast & Rescue
# ==============================================================================
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-roast-and-rescue}"
REGION="${REGION:-us-central1}"
PORT="${PORT:-8080}"

echo "=========================================================="
echo "  Deploying ${SERVICE_NAME} to Google Cloud Run"
echo "  Region: ${REGION} | Port: ${PORT}"
echo "=========================================================="

# Check if user wants local docker testing instead
if [[ "${1:-}" == "--local" ]]; then
    echo "🐳 Building and running container locally with Docker..."
    docker build -t "${SERVICE_NAME}" .
    echo "🚀 Starting container on http://localhost:${PORT}..."
    docker run --rm -p "${PORT}:${PORT}" -e PORT="${PORT}" "${SERVICE_NAME}"
    exit 0
fi

# Check for gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: 'gcloud' CLI is not installed or not in PATH."
    echo "💡 To test container locally, run: ./deploy-cloudrun.sh --local"
    echo "💡 Or install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "📦 Submitting build and deploying service to Cloud Run..."
ENV_VARS=""
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    ENV_VARS="--set-env-vars GITHUB_TOKEN=${GITHUB_TOKEN}"
fi

gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --region "${REGION}" \
    --allow-unauthenticated \
    --port "${PORT}" \
    ${ENV_VARS}

echo "✅ Deployment complete! Service URL retrieved from Google Cloud Run."
