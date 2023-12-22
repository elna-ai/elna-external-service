#!/usr/bin/env python3
import os
import getpass

import aws_cdk as cdk

from infra.external_service_stack import ExternalServiceStack

app = cdk.App()

deployment_stage = getpass.getuser()

ExternalServiceStack(app, f"{deployment_stage}-AiStack",
                     # If you don't specify 'env', this stack will be environment-agnostic.
                     # Account/Region-dependent features and context lookups will not work,
                     # but a single synthesized template can be deployed anywhere.

                     # Uncomment the next line to specialize this stack for the AWS Account
                     # and Region that are implied by the current CLI configuration.

                     # env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv(
                     # 'CDK_DEFAULT_REGION')),

                     # Uncomment the next line if you know exactly what Account and Region you
                     # want to deploy the stack to. */

                     env=cdk.Environment(account='931987803788', region='eu-north-1'),
                     stage_name="github"

                     # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
                     )

app.synth()
