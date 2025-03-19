#!/bin/bash
set -e

# Configuration
# Load environment variables
if [ -f "./config.env" ]; then
  source ./config.env
fi

if [ -f "./secrets.env" ]; then
  source ./secrets.env
fi

# API_NAME="auth-api"
# VALIDATOR_FUNCTION_NAME="jwt-validator"
# TOKEN_MANAGER_FUNCTION_NAME="user-manager"

echo "Preparing code for JWT authentication system deployment..."

# Create directories for Lambda functions if not already present
mkdir -p ./deployment/jwt-validator
mkdir -p ./deployment/user-manager

# Install dependencies for JWT validator
echo "Installing dependencies for jwt-validator..."
cd ./deployment/jwt-validator
npm install
cd ../..

# Install dependencies for token manager
echo "Installing dependencies for user-manager..."
cd ./deployment/user-manager
npm install
cd ../..

# Create ZIP files for Lambda deployment
echo "Creating deployment packages..."
cd ./deployment/jwt-validator
zip -r ../../jwt-validator.zip .
cd ../..
cd ./deployment/user-manager
zip -r ../../user-manager.zip .
cd ../..

echo "Code preparation completed. Lambda packages are ready for deployment."
