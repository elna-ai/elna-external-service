from os import environ, path
import aws_cdk.aws_iam as iam
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sqs as sqs
from aws_cdk.aws_apigateway import Cors, CorsOptions
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct

# Move all these to config yml
OPEN_SEARCH_INSTANCE_DEV = (
    "search-elna-dev-t23lgqbyj66tqg6dfe6l6ptj4q.aos.eu-north-1.on.aws"
)
OPEN_SEARCH_INSTANCE_TEST = (
    "search-elna-test-6y2ixgct47xr5dco6vik6yvztm.aos.eu-north-1.on.aws"
)
OPEN_SEARCH_INSTANCE_PROD = (
    "search-elna-prod-ni2recovy3e7p5hjm5rvkx52di.aos.eu-north-1.on.aws"
)

DEV_CANISTER_ID = "e6r43-cqaaa-aaaak-quhtq-cai"
PROD_CANISTER_ID = "ev7jo-jaaaa-aaaah-adthq-cai"
VECTOR_DB_PROD_CANISTER_ID = "wm3tr-wyaaa-aaaah-adxyq-cai"
VECTOR_DB_DEV_CANISTER_ID = "bxnxt-iqaaa-aaaak-quhpq-cai"
RAG_PROD_CANISTER_ID = "bpsjh-6yaaa-aaaah-adyjq-cai"
RAG_DEV_CANISTER_ID = "eqtrt-zaaaa-aaaak-quhsq-cai"
WIZARD_DEV_DETAILS_ID = "efua6-yiaaa-aaaak-quhra-cai"
WIZARD_PROD_DETAILS_ID = "gichg-2iaaa-aaaah-adtia-cai"


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

        envs = {
            "OPEN_AI_KEY": environ["OPEN_AI_KEY"],
            "SERP_API_KEY": environ["SERP_API_KEY"],
            "OPEN_SEARCH_INSTANCE": self.get_open_search_instance(),
            "CANISTER_ID": self.get_canister_id(),
            "IDENTITY": environ["IDENTITY"],
            "VECTOR_DB_CID": self.get_vector_db_cid(),
            "RAG_CID": self.get_rag_cid(),
            "WIZARD_DETAILS_CID": self.get_wizard_cid(),
        }

        inference_lambda = self._create_lambda_function(
            f"{self._stage_name}-elna-ext-lambda",
            "services/elna_handler",
            lambda_layers,
            envs,
            "request_handler.invoke",
        )

        queue_processor_lambda = self._create_lambda_function(
            f"{self._stage_name}-elna-q-processor-lambda",
            "services/elna_handler",
            lambda_layers,
            envs,
            "queue_handler.invoke",
        )

        request_queue = sqs.Queue(
            self,
            f"{self._stage_name}-elna-ext-queue-fifo",
            content_based_deduplication=False,
            deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
            fifo_throughput_limit=sqs.FifoThroughputLimit.PER_MESSAGE_GROUP_ID,
            queue_name=f"{self._stage_name}-elna-ext-queue.fifo",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.seconds(60),
        )

        request_queue.grant_send_messages(inference_lambda)
        request_queue.grant_consume_messages(queue_processor_lambda)

        request_event_source = SqsEventSource(request_queue, batch_size=1)
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

        # AI response table
        ai_response_table = dynamodb.TableV2(
            self,
            f"{self._stage_name}-elna-ext-service-ai-response-table",
            table_name=f"{self._stage_name}-elna-ext-service-ai-response-table",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            contributor_insights=False,
            table_class=dynamodb.TableClass.STANDARD,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.RETAIN
                if stage_name in ["prod"]
                else RemovalPolicy.DESTROY
            ),
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
        queue_processor_lambda.add_environment(
            "REQUEST_QUEUE_URL", request_queue.queue_url
        )

        # ELNA analytics table
        analytycs_table = dynamodb.TableV2(
            self,
            f"{self._stage_name}-elna-ext-service-analytycs-table",
            table_name=f"{self._stage_name}-elna-ext-service-analytycs-table",
            partition_key=dynamodb.Attribute(
                name="bot-id", type=dynamodb.AttributeType.STRING
            ),
            contributor_insights=False,
            table_class=dynamodb.TableClass.STANDARD,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.RETAIN
                if stage_name in ["prod"]
                else RemovalPolicy.DESTROY
            ),
        )

        analytycs_table.grant_full_access(inference_lambda)
        inference_lambda.add_environment("ANALYTICS_TABLE", analytycs_table.table_name)

        # Agent details table - for storing agent/wizard details
        agent_details_table = dynamodb.TableV2(
            self,
            f"{self._stage_name}-agent-details-table",
            table_name=f"{self._stage_name}-agent-details-table",
            partition_key=dynamodb.Attribute(
                name="agent_id", type=dynamodb.AttributeType.STRING
            ),
            contributor_insights=False,
            table_class=dynamodb.TableClass.STANDARD,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.RETAIN
                if stage_name in ["prod"]
                else RemovalPolicy.DESTROY
            ),
        )

        # Grant access to Lambda functions
        agent_details_table.grant_full_access(inference_lambda)
        agent_details_table.grant_full_access(queue_processor_lambda)

        # Add environment variables
        inference_lambda.add_environment("AGENT_DETAILS_TABLE", agent_details_table.table_name)
        queue_processor_lambda.add_environment("AGENT_DETAILS_TABLE", agent_details_table.table_name)

        # Chat history table with correct partition key name
        chat_history_table = dynamodb.TableV2(
            self,
            f"{self._stage_name}-chat-history-table",
            table_name=f"{self._stage_name}-chat-history-table",
            partition_key=dynamodb.Attribute(
                name="user_agent_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
            contributor_insights=False,
            table_class=dynamodb.TableClass.STANDARD,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.RETAIN
                if stage_name in ["prod"]
                else RemovalPolicy.DESTROY
            ),
        )

        # Grant access to corrected table
        chat_history_table.grant_full_access(inference_lambda)
        chat_history_table.grant_full_access(queue_processor_lambda)

        # Update environment variables to use corrected table
        inference_lambda.add_environment("CHAT_HISTORY_TABLE", chat_history_table.table_name)
        queue_processor_lambda.add_environment("CHAT_HISTORY_TABLE", chat_history_table.table_name)

        # Opensearch
        inference_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonOpenSearchServiceFullAccess"
            )
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
            default_cors_preflight_options=CorsOptions(
                allow_origins=Cors.ALL_ORIGINS,
                allow_methods=Cors.ALL_METHODS,
                allow_credentials=True,
                allow_headers=Cors.DEFAULT_HEADERS,
            ),
        )

        # Existing endpoints
        info = api_gateway_resource.root.add_resource("info")
        info.add_method("GET")

        canister_chat = api_gateway_resource.root.add_resource("canister-chat")
        canister_chat.add_method("POST")

        create_embedding = api_gateway_resource.root.add_resource("create-embedding")
        create_embedding.add_method("POST")

        create_index = api_gateway_resource.root.add_resource("create-index")
        create_index.add_method("POST")

        create_elna_index = api_gateway_resource.root.add_resource("create-elna-index")
        create_elna_index.add_method("POST")

        delete_index = api_gateway_resource.root.add_resource("delete-index")
        delete_index.add_method("POST")

        insert_embedding = api_gateway_resource.root.add_resource("insert-embedding")
        insert_embedding.add_method("POST")

        similarity_search = api_gateway_resource.root.add_resource("search")
        similarity_search.add_method("POST")

        get_filenames = api_gateway_resource.root.add_resource("get-filenames")
        get_filenames.add_method("GET")

        # Main chat endpoint
        chat = api_gateway_resource.root.add_resource("chat")
        chat.add_method("POST")

        # Health check endpoint
        health = api_gateway_resource.root.add_resource("health")
        health.add_method("GET")

        # Chat history endpoints - Updated to match Lambda function patterns
        # Pattern: GET /chat/history/{agent_id} and DELETE /chat/history/{agent_id}
        chat_history = chat.add_resource("history")
        chat_history_agent = chat_history.add_resource("{agent_id}")
        
        # GET /chat/history/{agent_id} - Get chat history for specific agent
        chat_history_agent.add_method("GET")
        
        # DELETE /chat/history/{agent_id} - Clear chat history for specific agent
        chat_history_agent.add_method("DELETE")

        # Authentication endpoints
        login = api_gateway_resource.root.add_resource("login")
        login.add_method("POST")

        login_required = api_gateway_resource.root.add_resource("login-required")
        login_required.add_method("POST")

        return api_gateway_resource

    def get_open_search_instance(self):
        """get opensearch instance url
        Returns:
            string: url
        """
        if self._stage_name == "prod":
            return OPEN_SEARCH_INSTANCE_PROD
        if self._stage_name == "dev":
            return OPEN_SEARCH_INSTANCE_DEV
        return OPEN_SEARCH_INSTANCE_TEST

    def get_canister_id(self):
        if self._stage_name == "prod":
            return PROD_CANISTER_ID
        return DEV_CANISTER_ID

    def get_vector_db_cid(self):
        if self._stage_name == "prod":
            return VECTOR_DB_PROD_CANISTER_ID
        return VECTOR_DB_DEV_CANISTER_ID

    def get_rag_cid(self):
        if self._stage_name == "prod":
            return RAG_PROD_CANISTER_ID
        return RAG_DEV_CANISTER_ID

    def get_wizard_cid(self):
        if self._stage_name == "prod":
            return WIZARD_PROD_DETAILS_ID
        return WIZARD_DEV_DETAILS_ID