#!/bin/bash
set -e

# Master deployment script that coordinates the entire deployment process

# Default configuration
REGION="us-east-1"
STAGE="dev"
API_NAME="auth-api"
VALIDATOR_FUNCTION_NAME="jwt-validator"
TOKEN_MANAGER_FUNCTION_NAME="user-manager"
ROLE_NAME="lambda-auth-role"
DYNAMODB_TABLE_NAME="Users"
ENABLE_CORS="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --region)
      REGION="$2"
      shift
      shift
      ;;
    --stage)
      STAGE="$2"
      shift
      shift
      ;;
    --api-name)
      API_NAME="$2"
      shift
      shift
      ;;
    --enable-cors)
      ENABLE_CORS="true"
      shift
      ;;
    --help)
      echo "Usage: ./deploy.sh [OPTIONS]"
      echo "Options:"
      echo "  --region REGION          AWS region to deploy to (default: us-east-1)"
      echo "  --stage STAGE            Stage name for API Gateway (default: dev)"
      echo "  --api-name NAME          Name for the API Gateway (default: auth-api)"
      echo "  --enable-cors            Enable CORS support for API endpoints"
      echo "  --help                   Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information."
      exit 1
      ;;
  esac
done

# Generate config file with deployment parameters
echo "Generating config file with deployment parameters..."
cat > ./config.env << EOF
REGION=${REGION}
STAGE=${STAGE}
API_NAME=${API_NAME}
VALIDATOR_FUNCTION_NAME=${VALIDATOR_FUNCTION_NAME}
TOKEN_MANAGER_FUNCTION_NAME=${TOKEN_MANAGER_FUNCTION_NAME}
ROLE_NAME=${ROLE_NAME}
DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE_NAME}
ENABLE_CORS=${ENABLE_CORS}
EOF

echo "Starting deployment with the following configuration:"
echo "Region: ${REGION}"
echo "Stage: ${STAGE}"
echo "API Name: ${API_NAME}"
echo "CORS Enabled: ${ENABLE_CORS}"
echo

# Step 1: Prepare code
echo "=== Step 1: Preparing code ==="
chmod +x ./prepare-code.sh
./prepare-code.sh
echo

# Step 2: Deploy infrastructure
echo "=== Step 2: Deploying infrastructure ==="
chmod +x ./deploy-infrastructure.sh
./deploy-infrastructure.sh
echo

# Step 3: Deploy API Gateway
echo "=== Step 3: Deploying API Gateway ==="
chmod +x ./deploy-api.sh
./deploy-api.sh
echo

# Print summary of deployment
if [ -f "./deploy-info.env" ]; then
  source ./deploy-info.env
  echo "=== Deployment Summary ==="
  echo "Region: ${REGION}"
  echo "Stage: ${STAGE}"
  echo "API URL: ${API_URL}"
  echo "Endpoints:"
  echo "  POST ${API_URL}/tokens - Generate tokens"
  echo "  POST ${API_URL}/refresh - Refresh access token"
  echo "  GET ${API_URL}/user - Get user data (requires authorization)"
  
  if [ -f "./secrets.env" ]; then
    echo
    echo "JWT Secrets (saved in ./secrets.env):"
    cat ./secrets.env
    echo
    echo "IMPORTANT: Keep these secrets secure and don't commit them to version control!"
  fi
  
  echo
  echo "Example usage:"
  echo "curl -X POST ${API_URL}/tokens -H 'Content-Type: application/json' -d '{\"publicKey\":\"user123\"}'"
  echo "curl -X POST ${API_URL}/refresh -H 'Content-Type: application/json' -d '{\"refreshToken\":\"YOUR_REFRESH_TOKEN\"}'"
  echo "curl -X GET ${API_URL}/user -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'"
fi

echo
echo "Deployment completed successfully!"
