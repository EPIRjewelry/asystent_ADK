#!/bin/bash
# Deployment script dla Cloud Run
# Używaj w Cloud Shell: bash deploy.sh

PROJECT_ID="epir-adk-agent-v2-48a86e6f"
SERVICE_NAME="bq-analyst-agent"
REGION="us-central1"  # Cloud Run region (nie global!)
VERTEX_LOCATION="global"  # Vertex AI location (model)
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying EPIR BigQuery Analyst Agent to Cloud Run..."

# Build kontenera
echo "📦 Building container..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy na Cloud Run
echo "🌐 Deploying to Cloud Run (region: ${REGION})..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},MODEL_NAME=publishers/google/models/gemini-3-flash-preview \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10

echo "✅ Deployment complete!"
echo "🔗 Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
