from aws_cdk import (
    # Duration,
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
)
from constructs import Construct

from os import path


class ExternalServiceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        aws_power_tool_arn = "arn:aws:lambda:eu-north-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:50"

        lambda_fun = lambda_.Function(
            self,
            "elna-ext-lambda",
            function_name="elna-ext-lambda",
            code=lambda_.Code.from_asset(path.join("src/lambdas/ai_service")),
            handler="index.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "ExternalServicePowertoolLayer", aws_power_tool_arn
                )
            ],
        )

        # lambda_fun.add_function_url()

        api = apigateway.LambdaRestApi(
            self, "elna-ext-service", handler=lambda_fun, proxy=False
        )

        info = api.root.add_resource("info")
        info.add_method("GET")
