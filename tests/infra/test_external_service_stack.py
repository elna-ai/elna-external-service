import aws_cdk as core
import aws_cdk.assertions as assertions

from infra.external_service_stack import ExternalServiceStack


def test_sqs_queue_created():
    app = core.App()
    stack = ExternalServiceStack(app, "src")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
