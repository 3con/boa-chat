"""UserLoginHandlerFunction

Validates user login credentials and returns API access credentials if 
successful.

"""

from __future__ import print_function

import os
import json
import copy
import datetime
import calendar
import time
import boto3
import botocore
from apigateway_helpers.exception import APIGatewayException
from cognito_helpers import generate_cognito_sign_up_secret_hash

cognito_idp_client = boto3.client("cognito-idp")
cognito_identity_client = boto3.client("cognito-identity")

def lambda_handler(event, context):
    
    event_for_logging = copy.deepcopy(event)
    
    if "request-body" in event_for_logging and "password" in event_for_logging["request-body"]:
        event_for_logging["request-body"]["password"] = "********"
    
    print("Event: {}".format(json.dumps(event_for_logging)))
    
    if "warming" in event and "{}".format(event["warming"]).lower() == "true":
        return {
            "message": "Warmed!"
        }
    
    user_pool_id = event["cognito-user-pool-id"]
    user_pool_client_id = event["cognito-user-pool-client-id"]
    user_pool_client_secret = event["cognito-user-pool-client-secret"]
    
    email_address = event["request-body"].get("email-address", "")
    
    if email_address == "":
        raise APIGatewayException("Value for \"email-address\" must be specified in request body.", 400)
    
    submitted_password = event["request-body"].get("password", "")
    
    if submitted_password == "":
        raise APIGatewayException("Value for \"password\" must be specified in request body.", 400)
    
    secret_hash = generate_cognito_sign_up_secret_hash(email_address, user_pool_client_id, user_pool_client_secret)
    
    print("Initiating auth.")
    
    try:
        response = cognito_idp_client.admin_initiate_auth(
            UserPoolId = user_pool_id,
            ClientId = user_pool_client_id,
            AuthFlow = "ADMIN_NO_SRP_AUTH",
            AuthParameters = {
                "USERNAME": email_address,
                "PASSWORD": submitted_password,
                "SECRET_HASH": secret_hash
            }
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            raise APIGatewayException("User with e-mail address ({}) not found.".format(email_address), 404)
        elif e.response['Error']['Code'] == 'NotAuthorizedException':
            raise APIGatewayException("Password entered is not correct.", 403)
        raise
    
    cognito_id_token = response["AuthenticationResult"]["IdToken"]
    cognito_refresh_token = response["AuthenticationResult"]["RefreshToken"]
    cognito_access_token = response["AuthenticationResult"]["AccessToken"]
    cognito_access_token_type = response["AuthenticationResult"]["TokenType"]
    
    cognito_user_pool_provider_name = "cognito-idp.{}.amazonaws.com/{}".format(
        os.environ["AWS_DEFAULT_REGION"],
        user_pool_id
    )
    
    identity_pool_id = event["cognito-identity-pool-id"]
    
    print("Fetching identity id.")
    
    response = cognito_identity_client.get_id(
        IdentityPoolId = identity_pool_id,
        Logins = {
            cognito_user_pool_provider_name: cognito_id_token
        }
    )
    
    identity_id = response["IdentityId"]
    
    print("Fetching credentials.")
    
    response = cognito_identity_client.get_credentials_for_identity(
        IdentityId = identity_id,
        Logins = {
            cognito_user_pool_provider_name: cognito_id_token
        }
    )
    
    aws_access_key_id = response["Credentials"]["AccessKeyId"]
    aws_secret_access_key = response["Credentials"]["SecretKey"]
    aws_session_token = response["Credentials"]["SessionToken"]
    expiration_timestamp_seconds = calendar.timegm(response["Credentials"]["Expiration"].timetuple())
    
    return {
        "access-key-id": aws_access_key_id,
        "secret-access-key": aws_secret_access_key,
        "aws-session-token": aws_session_token,
        "expiration": expiration_timestamp_seconds - int(time.time())
    }