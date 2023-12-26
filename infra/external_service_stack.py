from os import environ, path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct


class ExternalServiceStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, stage_name="dev", **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._stage_name = stage_name
        aws_tool_layer_arn = "arn:aws:lambda:eu-north-1:017000801446:layer:AWSLambdaPowertoolsPythonV2:50"

        layer_common = PythonLayerVersion(
            self,
            "CommonLayer",
            entry="layers",
            layer_version_name=f"{stage_name}-elna-ext-common-layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            removal_policy=RemovalPolicy.DESTROY,
        )

        lambda_layers = [
            layer_common,
            lambda_.LayerVersion.from_layer_version_arn(
                self, "ExternalServicePowertoolLayer", aws_tool_layer_arn
            ),
        ]

        envs = {"OPEN_AI_KEY": environ["OPEN_AI_KEY"]}

        inference_lambda = self._create_lambda_function(
            f"{self._stage_name}-elna-ext-lambda",
            "services/inference_handler",
            lambda_layers,
            envs,
            "request_handler.invoke",
        )
        queue_processor_lambda = self._create_lambda_function(
            f"{self._stage_name}-elna-q-processor-lambda",
            "services/inference_handler",
            lambda_layers,
            envs,
            "queue_handler.invoke",
        )

        request_queue = sqs.Queue(
            self,
            f"{self._stage_name}-elna-ext-queue-fifo",
            content_based_deduplication=True,
            # deduplication_scope="messageGroup", #enable if high throughput is required
            # fifo_throughput_limit="perMessageGroupId", #enable if high throughput is required
            queue_name=f"{self._stage_name}-elna-ext-queue.fifo",
            visibility_timeout=Duration.seconds(300),
        )

        request_queue.grant_send_messages(inference_lambda)
        request_queue.grant_consume_messages(queue_processor_lambda)
        request_event_source = SqsEventSource(request_queue)
        queue_processor_lambda.add_event_source(request_event_source)

        api_gateway = self._create_api_gw(
            f"{self._stage_name}-elna-ext-service", inference_lambda
        )
        cloudfront_dist = cloudfront.Distribution(
            self,
            f"{self._stage_name}-elna-ext-service-cloudfront-dist",
            comment=f"{self._stage_name}-elna-ext-service-cloudfront-dist",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.RestApiOrigin(api_gateway),
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
            contributor_insights=True,
            table_class=dynamodb.TableClass.STANDARD,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
            if stage_name in ["prod"]
            else RemovalPolicy.DESTROY,
        )

        ai_response_table.grant_full_access(inference_lambda)
        ai_response_table.grant_full_access(queue_processor_lambda)
        inference_lambda.add_environment(
            "AI_RESPONSE_TABLE", ai_response_table.table_name
        )
        inference_lambda.add_environment("REQUEST_QUEUE_NAME", request_queue.queue_name)
        inference_lambda.add_environment("REQUEST_QUEUE_URL", request_queue.queue_url)
        queue_processor_lambda.add_environment(
            "AI_RESPONSE_TABLE", ai_response_table.table_name
        )
        queue_processor_lambda.add_environment(
            "REQUEST_QUEUE_NAME", request_queue.queue_name
        )

    def _create_lambda_function(
        self,
        identifier: str,
        source: str,
        lambda_layers: list,
        envs: dict,
        function_handler: str,
    ):
        _lambda_function = lambda_.Function(
            self,
            identifier,
            function_name=identifier,
            code=lambda_.Code.from_asset(path.join(source)),
            handler=function_handler,
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(300),
            layers=lambda_layers,
            environment=envs,
        )
        return _lambda_function

    def _create_api_gw(self, identifier: str, handler_function):
        api_gateway_resource = apigw.LambdaRestApi(
            self,
            identifier,
            handler=handler_function,
            proxy=False,
        )

        info = api_gateway_resource.root.add_resource("info")
        info.add_method("GET")
        chat = api_gateway_resource.root.add_resource("chat")
        chat.add_method("POST")
        return api_gateway_resource
