#!/bin/bash
set -e

# Configuration - Load from config file or environment variables
REGION=${REGION:-"us-east-1"}
API_NAME=${API_NAME:-"auth-api"}
STAGE=${STAGE:-"dev"}
ROLE_NAME=${ROLE_NAME:-"lambda-auth-role"}
DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE_NAME:-"Users"}
VALIDATOR_FUNCTION_NAME=${VALIDATOR_FUNCTION_NAME:-"jwt-validator"}
TOKEN_MANAGER_FUNCTION_NAME=${TOKEN_MANAGER_FUNCTION_NAME:-"user-manager"}

# Load configuration from file if exists
if [ -f "./config.env" ]; then
  echo "Loading configuration from config.env..."
  source ./config.env
fi

echo "Starting deployment of infrastructure for JWT authentication system..."
echo "Using region: ${REGION}, stage: ${STAGE}"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ================================
# Create IAM Role for Lambda
# ================================
echo "Setting up IAM role for Lambda functions..."
if aws iam get-role --role-name ${ROLE_NAME} --region ${REGION} 2>/dev/null; then
  echo "Role ${ROLE_NAME} already exists."
else
  echo "Creating IAM role: ${ROLE_NAME}"
  aws iam create-role \
    --role-name ${ROLE_NAME} \
    --assume-role-policy-document file://./deployment/trust-policy.json \
    --region ${REGION}

  echo "Attaching necessary policies to IAM role..."
  aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
  aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

  echo "Waiting for IAM role to propagate..."
  sleep 10
fi

ROLE_ARN=$(aws iam get-role --role-name ${ROLE_NAME} --query Role.Arn --output text)

# ================================
# Ensure API Gateway CloudWatch Logs Role Exists
# ================================
echo "Setting up API Gateway CloudWatch Logs Role..."
CLOUDWATCH_ROLE_ARN=$(aws iam get-role --role-name APIGatewayCloudWatchLogsRole --query Role.Arn --output text --region ${REGION} || echo "")

if [ -z "$CLOUDWATCH_ROLE_ARN" ]; then
  echo "Creating API Gateway CloudWatch Logs Role..."
  aws iam create-role \
    --role-name APIGatewayCloudWatchLogsRole \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{"Effect": "Allow", "Principal": {"Service": "apigateway.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }' \
    --region ${REGION}

  aws iam attach-role-policy --role-name APIGatewayCloudWatchLogsRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs
  sleep 5
  CLOUDWATCH_ROLE_ARN=$(aws iam get-role --role-name APIGatewayCloudWatchLogsRole --query Role.Arn --output text --region ${REGION})
fi

echo "Updating API Gateway logging settings..."
aws apigateway update-account \
    --patch-operations "[{\"op\": \"replace\", \"path\": \"/cloudwatchRoleArn\", \"value\": \"${CLOUDWATCH_ROLE_ARN}\"}]" \
    --region ${REGION}

# ================================
# Deploy DynamoDB Table
# ================================
echo "Deploying DynamoDB table..."
aws cloudformation deploy \
    --template-file ./deployment/dynamodb.yaml \
    --stack-name ${DYNAMODB_TABLE_NAME}-stack \
    --capabilities CAPABILITY_IAM \
    --region ${REGION}

# ================================
# Deploy Lambda Functions
# ================================
echo "Deploying Lambda functions..."
for FUNCTION_NAME in ${VALIDATOR_FUNCTION_NAME} ${TOKEN_MANAGER_FUNCTION_NAME}; do
  if aws lambda get-function --function-name ${FUNCTION_NAME} --region ${REGION} 2>/dev/null; then
    echo "Updating existing Lambda function: ${FUNCTION_NAME}"
    aws lambda update-function-code --function-name ${FUNCTION_NAME} --zip-file fileb://${FUNCTION_NAME}.zip --region ${REGION}
  else
    echo "Creating Lambda function: ${FUNCTION_NAME}"

    # Ensure non-empty default values for environment variables
    ENV_VARS="{USER_TABLE=${DYNAMODB_TABLE_NAME},ACCESS_TOKEN_SECRET=${ACCESS_TOKEN_SECRET:-default_access_secret},REFRESH_TOKEN_SECRET=${REFRESH_TOKEN_SECRET:-default_refresh_secret}}"

    aws lambda create-function \
      --function-name ${FUNCTION_NAME} \
      --runtime nodejs18.x \
      --role ${ROLE_ARN} \
      --handler index.handler \
      --zip-file fileb://${FUNCTION_NAME}.zip \
      --environment Variables="$ENV_VARS" \
      --timeout 10 \
      --region ${REGION} \
      --tracing-config Mode=Active
  fi
done


echo "Infrastructure deployment completed successfully!"
