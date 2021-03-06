"""UserChangePasswordHandlerFunction

Handles requests to change a user's password.

"""

from __future__ import print_function

import os
import json
import time
import boto3
import botocore
from apigateway_helpers.exception import APIGatewayException
from apigateway_helpers.headers import get_response_headers
from cognito_helpers import generate_cognito_sign_up_secret_hash

cognito_idp_client = boto3.client("cognito-idp")
cognito_sync_client = boto3.client("cognito-sync")

def lambda_handler(event, context):
    
    print("Event: {}".format(json.dumps(event)))
    
    if "warming" in event and "{}".format(event["warming"]).lower() == "true":
        return {
            "message": "Warmed!"
        }
    
    event["request-body"] = json.loads(event["body"])
    
    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    user_pool_client_id = os.environ["COGNITO_USER_POOL_CLIENT_ID"]
    user_pool_client_secret = os.environ["COGNITO_USER_POOL_CLIENT_SECRET"]
    user_profile_dataset_name = os.environ["COGNITO_USER_PROFILE_DATASET_NAME"]
    
    new_password = event["request-body"].get("password")
    
    if new_password is None:
        raise APIGatewayException("Value for \"password\" must be specified in request body.", 400)
    
    
    user_id = None
    password_change_method = None
    old_password = None
    password_reset_code = None
    
    if event["resource"] == "/user/password":
        print("Authenticated user password change request.")
        
        password_change_method = "Authenticated"
        
        identity_id = event["requestContext"]["identity"]["cognitoIdentityId"]
        identity_pool_id = event["requestContext"]["identity"]["cognitoIdentityPoolId"]
        
        response = cognito_sync_client.list_records(
            IdentityPoolId = identity_pool_id,
            IdentityId = identity_id,
            DatasetName = user_profile_dataset_name
        )
        
        for each_record in response["Records"]:
            if each_record["Key"] == "user-id":
                user_id = each_record["Value"]
                break
        
        # We require the user's current password in addition to the new password.
        
        old_password = event["request-body"].get("old-password")
    
        if old_password is None:
            raise APIGatewayException("Value for \"old-password\" must be specified in request body.", 400)
    
    elif event["resource"] == "/user/forgot/password":
        print("Unathenticated (forgotten) user password change request.")
        
        password_change_method = "Unauthenticated"
        
        user_id = event["request-body"].get("email-address")
    
        if user_id is None:
            raise APIGatewayException("Value for \"email-address\" must be specified in request body.", 400)
        
        # We require the a password reset code in addition to the new password.
        
        password_reset_code = event["request-body"].get("token")
    
        if password_reset_code is None:
            raise APIGatewayException("Value for \"token\" must be specified in request body.", 400)
    
    if password_change_method is None:
        raise APIGatewayException("Unsure how to process request.")
    
        
    
    secret_hash = generate_cognito_sign_up_secret_hash(user_id, user_pool_client_id, user_pool_client_secret)
    
    if password_change_method == "Authenticated":
        
        response = cognito_sync_client.list_records(
            IdentityPoolId = identity_pool_id,
            IdentityId = identity_id,
            DatasetName = user_profile_dataset_name
        )
        
        idp_credentials = None
        
        for each_record in response.get("Records", []):
            if each_record["Key"] == "idp-credentials":
                idp_credentials = json.loads(each_record["Value"])
                break
        
        if idp_credentials is None or idp_credentials.get("expires", 0) < int(time.time()):
            raise APIGatewayException("Identity provider credentials expired. Please log in and try again.", 400)
        
        access_token = idp_credentials["access-token"]
        
        try:
            cognito_idp_client.change_password(
                PreviousPassword = old_password,
                ProposedPassword = new_password,
                AccessToken = access_token
            )
        except botocore.exceptions.ParamValidationError as e:
            raise APIGatewayException("Password does not meet complexity requirements.", 400)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidPasswordException':
                raise APIGatewayException("Password does not meet complexity requirements.", 400)
            elif e.response['Error']['Code'] == 'LimitExceededException':
                raise APIGatewayException("Password change attempt limit reached. Please wait a while and try again.", 400)
            elif e.response['Error']['Code'] == 'NotAuthorizedException':
                raise APIGatewayException("Existing password entered is not correct.", 400)
            else:
                raise
        
        
    elif password_change_method == "Unauthenticated":
        
        try:
            cognito_idp_client.confirm_forgot_password(
                ClientId = user_pool_client_id,
                SecretHash = secret_hash,
                Username = user_id,
                ConfirmationCode = password_reset_code,
                Password = new_password
            )
        except botocore.exceptions.ParamValidationError as e:
            raise APIGatewayException("New password does not meet password requirements.", 400)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] in ['CodeMismatchException', 'ExpiredCodeException']:
                raise APIGatewayException("Invalid password reset code.", 400)
            elif e.response['Error']['Code'] == 'ParamValidationError':
                raise APIGatewayException("New password does not meet password requirements.", 400)
            elif e.response['Error']['Code'] == 'InvalidPasswordException':
                raise APIGatewayException("New password does not meet password requirements.", 400)
            else:
                raise
    
    return {
        "message": "Password changed successfully."
    }

def proxy_lambda_handler(event, context):
    
    response_headers = get_response_headers(event, context)
    
    try:
        return_dict = lambda_handler(event, context)
    except APIGatewayException as e:
        return {
            "statusCode": e.http_status_code,
            "headers": response_headers,
            "body": json.dumps({
                "message": e.http_status_message
            })
        }
    
    return {
        "statusCode": 200,
        "headers": response_headers,
        "body": json.dumps(return_dict)
    }