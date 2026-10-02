#!/usr/bin/env bash
# Mint a fresh Cognito access token (valid ~1 hour) for the A2A bearer auth.
aws cognito-idp initiate-auth --region us-east-1 \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$COGNITO_CLIENT_ID" \
  --auth-parameters USERNAME="$COGNITO_USER",PASSWORD="$COGNITO_PASS" \
  --query 'AuthenticationResult.AccessToken' --output text

