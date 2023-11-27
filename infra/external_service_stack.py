from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    CfnOutput,
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
            handler="index.invoke",
            runtime=lambda_.Runtime.PYTHON_3_12,
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "ExternalServicePowertoolLayer", aws_power_tool_arn
                )
            ],
        )

        api = apigw.LambdaRestApi(
            self, "elna-ext-service", handler=lambda_fun, proxy=False
        )

        info = api.root.add_resource("info")
        info.add_method("GET")

        cloudfront_dist = cloudfront.Distribution(
            self,
            "elna-ext-service-cloudfront-dist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.RestApiOrigin(api)
            ),
        )

        CfnOutput(
            self,
            id="ElnaExtServiceCloudfrontDist",
            export_name="elna-ext-service-domain",
            value=cloudfront_dist.distribution_domain_name,
        )
