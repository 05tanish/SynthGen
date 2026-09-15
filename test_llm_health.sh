#!/bin/bash

# Test script to check LLM health on Railway deployment

BACKEND_URL="https://synthetix-backend-production-43d0.up.railway.app"

echo "================================================"
echo "Testing LLM Health Check"
echo "================================================"
echo ""

echo "1. Testing Simple Health Check..."
curl -s "${BACKEND_URL}/api/health/simple" | jq '.'
echo ""
echo ""

echo "2. Testing LLM Health Check..."
curl -s "${BACKEND_URL}/api/health/llm" | jq '.'
echo ""
echo ""

echo "3. Testing Detailed Health Check..."
curl -s "${BACKEND_URL}/api/health" | jq '.'
echo ""
echo ""

echo "================================================"
echo "Test Complete"
echo "================================================"
echo ""
echo "If LLM health check shows an error, you need to:"
echo "1. Go to Railway dashboard"
echo "2. Select your backend service"
echo "3. Go to Variables tab"
echo "4. Ensure these variables are set:"
echo "   - LLM_PROVIDER=groq"
echo "   - LLM_API_KEY=<your-groq-api-key>"
echo "   - LLM_MODEL=llama-3.3-70b-versatile"
echo "5. Redeploy the service"
