from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from packages.ai_models import choose_service_model

import os

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver()


@app.get("/info")
@tracer.capture_method
def get_todos():
    response = {"id": " 1", "name": "elna"}
    return response


def get_api_key():
    return os.environ["openai_api_key"]


@app.post("/chat")
@tracer.capture_method
def chat_completion():
    # TODO
    event = None
    context = None
    # logger.info(msg=event)
    # logger.info(msg=context)
    selected_model_cls = choose_service_model(event, context)

    ai_model = selected_model_cls(event, get_api_key())

    if not ai_model.create_response():
        return {"statusCode": 505, "body": {"response": ai_model.get_error_response()}}

    return {"statusCode": 200, "body": {"response": ai_model.get_text_response()}}


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
