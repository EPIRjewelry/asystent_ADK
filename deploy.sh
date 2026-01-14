#!/bin/bash
# Deployment script dla Cloud Run
# Używaj w Cloud Shell: bash deploy.sh

set -e  # Exit on error

PROJECT_ID="epir-adk-agent-v2-48a86e6f"
SERVICE_NAME="bq-analyst-agent"
REGION="us-central1"  # Cloud Run region (nie global!)
VERTEX_LOCATION="global"  # Vertex AI location (model)
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:3000,http://localhost:8080}"  # Domyślne Origins

echo "🚀 Deploying EPIR BigQuery Analyst Agent to Cloud Run..."

# Build kontenera
echo "📦 Building container..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy na Cloud Run
echo "🌐 Deploying to Cloud Run (region: ${REGION})..."
echo "⚠️  UWAGA: Upewnij się, że secret 'langchain-api-key' istnieje w Secret Manager!"
echo "   Jeśli nie: gcloud secrets create langchain-api-key --data-file=- <<< 'YOUR_KEY'"
echo ""

gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --env-vars-file .env.deploy \
  --update-secrets LANGCHAIN_API_KEY=langchain-api-key:latest \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --service-account=580145215562-compute@developer.gserviceaccount.com

echo ""
echo "✅ Deployment complete!"
echo "🔗 Service URL:"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo "${SERVICE_URL}"
echo ""
echo "📝 Next steps:"
echo "1. Jeśli nie istnieje, utwórz secret:"
echo "   gcloud secrets create langchain-api-key --data-file=- <<< 'YOUR_KEY'"
echo "2. Test health check:"
echo "   curl ${SERVICE_URL}/health"
