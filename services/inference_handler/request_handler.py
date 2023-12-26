import json
import os
from http import HTTPStatus

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver,
    Response,
    content_types,
)
from aws_lambda_powertools.logging import correlation_paths
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

app = APIGatewayRestResolver()


@app.get("/info")
@tracer.capture_method
def info():
    response = {"id": " 1", "name": "elna"}
    return response


@app.post("/chat")
@tracer.capture_method
def chat_completion():
    body = json.loads(app.current_event.body)
    headers = app.current_event.headers

    logger.info(msg=f"event_body:{body})")
    logger.info(msg=f"event_headers:{headers})")

    if headers.get("Idempotency-Key", None) is not None:
        idempotency_value = headers.get("Idempotency-Key")
        logger.info(msg=f"Idempotency: {idempotency_value}")
    else:
        idempotency_value = "UUID-1234"

    custom_headers = {"Idempotency-Key": idempotency_value}

    queue_handler.send_message(idempotency_value, json.dumps(body))

    if not ai_model.create_response(body):
        resp = Response(
            status_code=HTTPStatus.OK.value,  # 200
            content_type=content_types.APPLICATION_JSON,
            body={
                "statusCode": HTTPStatus.HTTP_VERSION_NOT_SUPPORTED.value,
                "body": {"response": ai_model.get_error_response()},
            },
            headers=custom_headers,
        )
        return resp

    resp = Response(
        status_code=HTTPStatus.OK.value,  # 200
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "Idempotency": idempotency_value,
            "body": {"response": ai_model.get_text_response()},
        },
        headers=custom_headers,
    )

    return resp


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
