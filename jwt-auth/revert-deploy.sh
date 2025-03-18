#!/bin/bash
set -e

# Configuration (must match the configuration in the deploy script)
REGION="us-east-1"  # Change to your preferred region
STAGE="dev"
API_NAME="auth-api"
VALIDATOR_FUNCTION_NAME="jwt-validator"
TOKEN_MANAGER_FUNCTION_NAME="user-manager"
ROLE_NAME="lambda-auth-role"
DYNAMODB_TABLE_NAME="Users"

echo "Starting cleanup of JWT authentication system..."

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete API Gateway
echo "Deleting API Gateway..."
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${API_NAME}'].id" --output text --region ${REGION})
if [ -n "$API_ID" ]; then
  echo "Deleting API Gateway with ID: ${API_ID}"
  aws apigateway delete-rest-api --rest-api-id ${API_ID} --region ${REGION}
  echo "API Gateway deleted."
else
  echo "No API Gateway found with name: ${API_NAME}"
fi

# Delete Lambda functions
echo "Deleting Lambda functions..."

# Delete validator function
if aws lambda get-function --function-name ${VALIDATOR_FUNCTION_NAME} --region ${REGION} 2>/dev/null; then
  echo "Deleting function: ${VALIDATOR_FUNCTION_NAME}"
  aws lambda delete-function --function-name ${VALIDATOR_FUNCTION_NAME} --region ${REGION}
  echo "Function deleted: ${VALIDATOR_FUNCTION_NAME}"
else
  echo "Function not found: ${VALIDATOR_FUNCTION_NAME}"
fi

# Delete token manager function
if aws lambda get-function --function-name ${TOKEN_MANAGER_FUNCTION_NAME} --region ${REGION} 2>/dev/null; then
  echo "Deleting function: ${TOKEN_MANAGER_FUNCTION_NAME}"
  aws lambda delete-function --function-name ${TOKEN_MANAGER_FUNCTION_NAME} --region ${REGION}
  echo "Function deleted: ${TOKEN_MANAGER_FUNCTION_NAME}"
else
  echo "Function not found: ${TOKEN_MANAGER_FUNCTION_NAME}"
fi

# Delete IAM role
echo "Deleting IAM role and policies..."
if aws iam get-role --role-name ${ROLE_NAME} 2>/dev/null; then
  # First detach policies
  echo "Detaching managed policies from role: ${ROLE_NAME}"
  
  # Get all attached managed policies
  MANAGED_POLICIES=$(aws iam list-attached-role-policies --role-name ${ROLE_NAME} --query "AttachedPolicies[].PolicyArn" --output text)
  
  # Detach each managed policy
  for POLICY_ARN in $MANAGED_POLICIES; do
    echo "Detaching policy: ${POLICY_ARN}"
    aws iam detach-role-policy --role-name ${ROLE_NAME} --policy-arn ${POLICY_ARN}
  done
  
  # Delete inline policies
  echo "Deleting inline policies from role: ${ROLE_NAME}"
  INLINE_POLICIES=$(aws iam list-role-policies --role-name ${ROLE_NAME} --query "PolicyNames" --output text)
  
  for POLICY_NAME in $INLINE_POLICIES; do
    echo "Deleting inline policy: ${POLICY_NAME}"
    aws iam delete-role-policy --role-name ${ROLE_NAME} --policy-name ${POLICY_NAME}
  done
  
  # Now delete the role
  echo "Deleting role: ${ROLE_NAME}"
  aws iam delete-role --role-name ${ROLE_NAME}
  echo "Role deleted: ${ROLE_NAME}"
else
  echo "Role not found: ${ROLE_NAME}"
fi

# Delete DynamoDB table using CloudFormation
echo "Deleting DynamoDB table..."
if aws cloudformation describe-stacks --stack-name ${DYNAMODB_TABLE_NAME}-stack --region ${REGION} 2>/dev/null; then
  echo "Deleting CloudFormation stack: ${DYNAMODB_TABLE_NAME}-stack"
  aws cloudformation delete-stack --stack-name ${DYNAMODB_TABLE_NAME}-stack --region ${REGION}
  echo "Waiting for stack deletion to complete..."
  aws cloudformation wait stack-delete-complete --stack-name ${DYNAMODB_TABLE_NAME}-stack --region ${REGION}
  echo "CloudFormation stack deleted: ${DYNAMODB_TABLE_NAME}-stack"
else
  echo "CloudFormation stack not found: ${DYNAMODB_TABLE_NAME}-stack"
  
  # As a fallback, try to delete the table directly
  if aws dynamodb describe-table --table-name ${DYNAMODB_TABLE_NAME} --region ${REGION} 2>/dev/null; then
    echo "Deleting DynamoDB table directly: ${DYNAMODB_TABLE_NAME}"
    aws dynamodb delete-table --table-name ${DYNAMODB_TABLE_NAME} --region ${REGION}
    echo "DynamoDB table deletion initiated: ${DYNAMODB_TABLE_NAME}"
    echo "Waiting for table deletion to complete..."
    aws dynamodb wait table-not-exists --table-name ${DYNAMODB_TABLE_NAME} --region ${REGION}
    echo "DynamoDB table deleted: ${DYNAMODB_TABLE_NAME}"
  else
    echo "DynamoDB table not found: ${DYNAMODB_TABLE_NAME}"
  fi
fi

echo "Cleanup completed successfully!"
echo "You can now run the deployment script again without conflicts."
