"""
This is a Request handler lambda for ELNA extenral service
"""
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
from aws_lambda_powertools.event_handler.api_gateway import CORSConfig
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from data_models import AuthenticationRequest, LoginResponse, SuccessResponse
from elnachain.chat_models.openai_model import ChatOpenAI
from elnachain.embeddings import OpenAIEmbeddings
from elnachain.prompts.chat_prompt import PromptTemplate
from elnachain.vectordb.opensearch import VectorDB, os_connect
from shared import AnalyticsDataHandler, RequestDataHandler, RequestQueueHandler
from shared.auth.backends import elna_auth_backend
from shared.auth.middleware import elna_login_required

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

analytics_handler = AnalyticsDataHandler(
    os.environ["ANALYTICS_TABLE"], dynamodb_client, logger
)

os_client = os_connect()

app = APIGatewayRestResolver(
    cors=CORSConfig(
        allow_origin="*",
        allow_headers=["*"],
        max_age=300,
        allow_credentials=True,
    )
)


@app.get("/info")
@tracer.capture_method
def info():
    """this is a test get method

    Returns:
        responce: dict
    """
    response = {"id": " 1", "name": "elna"}
    return response


@app.post("/canister-chat")
@tracer.capture_method
def canister_chat_completion():
    """canister http outcall for chat

    Returns:
        response: chat response
    """
    body = json.loads(app.current_event.body)
    headers = app.current_event.headers

    if headers.get("idempotency-key", None) is not None:
        idempotency_value = headers.get("idempotency-key")
    else:
        idempotency_value = "UUID-1234"

    logger.info(msg=f"idempotency-key: {idempotency_value}")
    custom_headers = {"idempotency-key": idempotency_value}

    queue_handler.send_message(idempotency_value, json.dumps(body))

    resp = Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "Idempotency": idempotency_value,
            "body": {
                "response": request_data_handler.wait_for_response(idempotency_value)
            },
        },
        headers=custom_headers,
    )

    return resp


@app.post("/create-embedding")
@tracer.capture_method
def create_embedding():
    """generate and return vecotrs

    Returns:
        response: embedding vector
    """
    api_key = os.environ["OPEN_AI_KEY"]
    oa_embedding = OpenAIEmbeddings(api_key=api_key, logger=logger)

    body = json.loads(app.current_event.body)

    text = body.get("text")

    resp = Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "body": {"vectors": oa_embedding.embed_query(text)},
        },
    )

    return resp


@app.post("/create-index", middlewares=[elna_login_required])
@tracer.capture_method
def create_index():
    """create new index and insert vector embeddings of documents

    Returns:
        response: response
    """

    api_key = os.environ["OPEN_AI_KEY"]
    oa_embedding = OpenAIEmbeddings(api_key=api_key, logger=logger)

    body = json.loads(app.current_event.body)
    documents = body.get("documents")
    index_name = body.get("index_name")
    file_name=body.get("file_name")
    embedding = VectorDB(os_client=os_client, index_name=index_name)
    resp = embedding.create_insert(oa_embedding, documents, file_name)

    response = Response(
        status_code=resp["status"],
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "body": {"response": resp["response"]},
        },
    )

    return response


@app.post("/delete-index", middlewares=[elna_login_required])
@tracer.capture_method
def delete_index():
    """delete index from opensearch

    Returns:
        resp: Response
    """

    body = json.loads(app.current_event.body)
    index_name = body.get("index_name")
    embedding = VectorDB(os_client=os_client, index_name=index_name)
    resp = embedding.delete_index()
    response = Response(
        status_code=resp["status"],
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": resp["status"],
            "body": {"response": resp["response"]},
        },
    )

    return response


@app.post("/insert-embedding")
@tracer.capture_method
def insert_embedding():
    """insert vector embeddings to database

    Returns:
        resp: Response
    """

    api_key = os.environ["OPEN_AI_KEY"]
    oa_embedding = OpenAIEmbeddings(api_key=api_key, logger=logger)

    body = json.loads(app.current_event.body)
    documents = body.get("documents")
    index_name = body.get("index_name")
    embedding = VectorDB(os_client=os_client, index_name=index_name)
    embedding.insert(oa_embedding, documents,file_name="Title")

    resp = Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "body": {"response": "Ok"},
        },
    )

    return resp


@app.post("/search")
@tracer.capture_method
def similarity_search():
    """similarity search of the query vecotr

    Returns:
        Response: Response
    """

    api_key = os.environ["OPEN_AI_KEY"]
    oa_embedding = OpenAIEmbeddings(api_key=api_key, logger=logger)

    body = json.loads(app.current_event.body)
    query_text = body.get("query_text")
    index_name = body.get("index_name")
    embedding = VectorDB(os_client=os_client, index_name=index_name, logger=logger)
    is_error, results = embedding.search(oa_embedding, query_text)

    if is_error:
        resp = Response(
            status_code=results["status"],
            content_type=content_types.APPLICATION_JSON,
            body={
                "statusCode": HTTPStatus.OK.value,
                "body": {"response": results["response"]},
            },
        )

    else:
        resp = Response(
            status_code=HTTPStatus.OK.value,
            content_type=content_types.APPLICATION_JSON,
            body={
                "statusCode": HTTPStatus.OK.value,
                "body": {"response": results},
            },
        )

    return resp


@app.get("/get-filenames", middlewares=[elna_login_required])
@tracer.capture_method
def get_filenames():
    """_summary_

    Returns:
        _type_: _description_
    """
    index_name = app.current_event.query_string_parameters.get("index", None)
    if index_name:
        db = VectorDB(os_client=os_client, index_name=index_name)
        filenames = db.get_filenames()
        resp = Response(
            status_code=HTTPStatus.OK.value,
            content_type=content_types.APPLICATION_JSON,
            body={
                "statusCode": HTTPStatus.OK.value,
                "body": {"response": "OK", "data": filenames},
            },
        )

        return resp

    resp = Response(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.UNPROCESSABLE_ENTITY.value,
            "body": {"message": "index not found"},
        },
    )
    return resp


@app.post("/chat")
@tracer.capture_method
def chat_completion():
    """chat completion using LLM model

    Returns:
        Response: chat responce from LLM
    """

    body = json.loads(app.current_event.body)
    analytics_handler.put_data(body.get("index_name"))
    api_key = os.environ["OPEN_AI_KEY"]
    llm = ChatOpenAI(api_key=api_key, logger=logger)
    oa_embedding = OpenAIEmbeddings(api_key=api_key, logger=logger)

    template = PromptTemplate(
        os_client=os_client,
        chat_client=llm,
        embedding=oa_embedding,
        body=body,
        logger=logger,
    )
    chat_prompt = template.get_prompt()
    # if is_error:
    #     resp = Response(
    #         status_code=chat_prompt["status"],
    #         content_type=content_types.APPLICATION_JSON,
    #         body={
    #             "statusCode": HTTPStatus.OK.value,
    #             "body": {"response": chat_prompt["response"]},
    #         },
    #     )

    # else:
    resp = Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body={
            "statusCode": HTTPStatus.OK.value,
            "body": {"response": llm(chat_prompt)},
        },
    )

    return resp


@app.post("/login")
@tracer.capture_method
def login():
    """Login API to generate JWT

    Returns:
        Response: JWT access token
    """

    request_body = app.current_event.body

    if request_body is None:
        raise BadRequestError("No request body provided")

    request = AuthenticationRequest(**json.loads(request_body))

    try:
        user = elna_auth_backend.authenticate(request)
    except Exception as e:
        logger.info(msg=f"Login failed: {e}")
        return Response(
            status_code=HTTPStatus.BAD_REQUEST.value,
            content_type=content_types.APPLICATION_JSON,
            body={"message": str(e)},
        )

    return Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body=LoginResponse(
            access_token=elna_auth_backend.get_access_token(user)
        ).json(),
    )


@app.post("/login-required", middlewares=[elna_login_required])
@tracer.capture_method
def login_required():
    """Login Required API"""

    resp = Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body=SuccessResponse(message="Successfully logged in").json(),
    )
    return resp


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
