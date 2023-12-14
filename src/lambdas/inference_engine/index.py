from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from http import HTTPStatus
import json
from datetime import datetime
from boto3.dynamodb.conditions import Key

import boto3
import time


from packages.ai_models import choose_service_model

import os

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


dynamodb = boto3.resource('dynamodb') 
table_name=os.environ['AI_RESPONSE_TABLE']
table = dynamodb.Table(table_name)


@app.get("/info")
@tracer.capture_method
def info():
    response = {"id": " 1", "name": "elna"}
    return response


def get_api_key():
    return os.environ["openai_api_key"]

# dynamo env var : AI_RESPONSE_TABLE


@app.post("/chat")
@tracer.capture_method
def chat_completion():
    event = app.current_event
    body = json.loads(app.current_event.body)
    headers = app.current_event.headers

    logger.info(msg=f"event_body:{body})")
    logger.info(msg=f"event_headers:{headers})")


    uuid=headers.get("idempotency-key")

    
    # result=table.get_item(Key={"uuid": uuid})
    

    result = table.query(
            KeyConditionExpression=Key('uuid').eq(uuid)
        )
    
    items=result['Items']
    
    if len(items):
        
        row=items[0]
        
        if row['is_processed'] =='True':
            logger.info(msg="Item alredy exist in the table")
            
            return  {"statusCode": 200, "body": {"response": row['response']}}
            
        else:
            while True:
                logger.info(msg="waiting...")
                time.sleep(1)
                    
                result = table.query(
                        KeyConditionExpression=Key('uuid').eq(uuid)
                    )

                row=result["Items"][0]

                if row['is_processed'] =='True':

                    logger.info(msg="response got after waiting")

                    return {"statusCode": 200, "body": {"response": row['response']}}
                else:
                    continue
             
        

    else:
        timestamp=str(datetime.now())
        table.put_item(Item={'uuid':uuid,'timestamp':timestamp,'is_processed':'False'})
        
        logger.info(msg="there is no item in db")

        selected_model_cls = choose_service_model(event, event.request_context)
        ai_model = selected_model_cls(body, get_api_key())
        
        if not ai_model.create_response():
            return {"statusCode": 505, "body": {"response": ai_model.get_error_response()}}
            
        row={'uuid':uuid,'timestamp':timestamp,'is_processed':'True','response':ai_model.get_text_response()}
        table.put_item(Item=row)
        
        return {"statusCode": 200, "body": {"response": row['response']}}



@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
