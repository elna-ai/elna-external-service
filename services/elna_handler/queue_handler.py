"""Queue handler for the Canister HTTP outcall"""

import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from elnachain import SERPAPI, ChatOpenAI, PromptTemplate
from shared import RequestDataHandler

tracer = Tracer()
logger = Logger()

dynamodb_client = boto3.resource("dynamodb")


request_data_handler = RequestDataHandler(
    os.environ["AI_RESPONSE_TABLE"], dynamodb_client, logger
)

# openai_client = OpenAI(api_key=api_key)
# ai_model = GptTurboModel(client=openai_client, logger=logger)


def handle_chat_prompt(uuid: str, payload: str):
    """generate response from OpenAI

    Args:
        uuid (str): uuid
        payload (str): body of the message
    """
    api_key = os.environ["OPEN_AI_KEY"]

    llm = SERPAPI(api_key=api_key, logger=logger)
    template = PromptTemplate(
        body=payload,
        logger=logger,
    )
    chat_prompt = template.format_message()
    response = llm(chat_prompt)
    logger.info(msg=f"ai response, {str(response)}")
    request_data_handler.store_prompt_response(uuid, response)


@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext):
    """Lambda Invoke function

    Args:
        event (dict): _description_
        context (LambdaContext): _description_
    """
    records = event["Records"]
    logger.info(msg=f"New event: {len(records)} records found for event ->{str(event)}")
    # There will be only one item most of the time
    for record in records:
        payload = json.loads(record["body"])
        uuid = record["attributes"]["MessageGroupId"]
        handle_chat_prompt(uuid, payload)
