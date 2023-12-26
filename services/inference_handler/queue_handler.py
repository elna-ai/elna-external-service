import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from shared import GptTurboModel, RequestDataHandler, RequestQueueHandler

tracer = Tracer()
logger = Logger()

sqs_client = boto3.client("sqs")
dynamodb_client = boto3.resource("dynamodb")

queue_handler = RequestQueueHandler(
    os.environ["REQUEST_QUEUE_NAME"],
    os.environ["REQUEST_QUEUE_URL"],
    sqs_client,
    logger,
)

request_data_handler = RequestDataHandler(
    os.environ["AI_RESPONSE_TABLE"], dynamodb_client, logger
)

ai_model = GptTurboModel(logger, os.environ["OPEN_AI_KEY"])


def handle_chat_prompt(uuid: str, payload: str):
    if not ai_model.create_response(payload):
        # TODO: Handle failure
        logger.info(msg=f"ai response failure, {str(ai_model.get_error_response())}")
        pass

    response = ai_model.get_text_response()
    logger.info(msg=f"ai response, {str(response)}")
    request_data_handler.store_prompt_response(uuid, payload, response)


@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext):
    print("New event:", str(event))
    for record in event["Records"]:
        payload = json.loads(record["body"])
        uuid = record["attributes"]["MessageGroupId"]
        handle_chat_prompt(uuid, payload)
