from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    CfnOutput,
    aws_dynamodb as dynamodb,
)
from aws_cdk import Duration
from constructs import Construct
from os import path, environ


def get_api_key():
    return environ["OPEN_API_KEY"]


class ExternalServiceStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, stage_name="dev", **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._stage_name = stage_name
        aws_tool_layer_arn = "arn:aws:lambda:eu-north-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:50"
        openai_layer_arn = "arn:aws:lambda:eu-north-1:931987803788:layer:openai:1"

        envs = {"openai_api_key": get_api_key()}

        inference_lambda = lambda_.Function(
            self,
            f"{self._stage_name}-elna-ext-lambda",
            function_name=f"{self._stage_name}-elna-ext-lambda",
            code=lambda_.Code.from_asset(path.join("src/lambdas/inference_engine")),
            handler="index.invoke",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(300),
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "ExternalServicePowertoolLayer", aws_tool_layer_arn
                ),
                lambda_.LayerVersion.from_layer_version_arn(
                    self, "OpenAiLayer", openai_layer_arn
                ),
            ],
            environment=envs,
        )

        api = apigw.LambdaRestApi(
            self,
            f"{self._stage_name}-elna-ext-service",
            handler=inference_lambda,
            proxy=False,
        )

        info = api.root.add_resource("info")
        info.add_method("GET")
        chat = api.root.add_resource("chat")
        chat.add_method("POST")

        cloudfront_dist = cloudfront.Distribution(
            self,
            f"{self._stage_name}-elna-ext-service-cloudfront-dist",
            comment=f"{self._stage_name}-elna-ext-service-cloudfront-dist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.RestApiOrigin(api),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
            ),
        )

        CfnOutput(
            self,
            id=f"{self._stage_name}-ElnaExtServiceCloudfrontDist",
            export_name=f"{self._stage_name}-elna-ext-service-domain",
            value=cloudfront_dist.distribution_domain_name,
        )

        ai_response_table = dynamodb.TableV2(
            self,
            f"{self._stage_name}-elna-ext-service-ai-response-table",
            table_name=f"{self._stage_name}-elna-ext-service-ai-response-table",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            contributor_insights=True,
            table_class=dynamodb.TableClass.STANDARD_INFREQUENT_ACCESS,
            point_in_time_recovery=True,
        )

        ai_response_table.grant_full_access(inference_lambda)
        inference_lambda.add_environment(
            "AI_RESPONSE_TABLE", ai_response_table.table_name
        )
