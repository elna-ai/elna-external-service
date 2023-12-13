from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from http import HTTPStatus
import json

from packages.ai_models import choose_service_model

import os

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


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

    Idempotency = False

    if headers.get("Idempotency-Key", None) is not None:
        id_value = headers.get("Idempotency-Key")
        logger.info(msg=f"Idempotency: {id_value}")
        Idempotency = True

    selected_model_cls = choose_service_model(event, event.request_context)
    ai_model = selected_model_cls(body, get_api_key())

    custom_headers = {
        "Idempotency-Key": "UUID-123456789"
    }

    if not ai_model.create_response():
        resp = Response(
            status_code=HTTPStatus.OK.value,  # 200
            content_type=content_types.APPLICATION_JSON,
            body={
                "statusCode": HTTPStatus.HTTP_VERSION_NOT_SUPPORTED.value,
                "body": {"response": ai_model.get_error_response()}
            },
            headers=custom_headers,
        )
        return resp

    resp = Response(
        status_code=HTTPStatus.OK.value,  # 200
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "Idempotency": Idempotency,
            "body": {"response": ai_model.get_text_response()}
        },
        headers=custom_headers,
    )

    return resp


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
