from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

tracer = Tracer()
logger = Logger()


@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext):
    print("new event: ", str(event))
    for record in event["Records"]:
        payload = record["body"]
        print(str(payload))
