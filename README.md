# elna-external-service

[![Prod AWS Service CI/CD](https://github.com/elna-ai/elna-external-service/actions/workflows/deploy-prod.yml/badge.svg)](https://github.com/elna-ai/elna-external-service/actions/workflows/deploy-prod.yml)
[![Dev AWS Service CI/CD](https://github.com/elna-ai/elna-external-service/actions/workflows/deploy-dev.yml/badge.svg)](https://github.com/elna-ai/elna-external-service/actions/workflows/deploy-dev.yml)
[![CI/CD AWS Deployment](https://github.com/elna-ai/elna-external-service/actions/workflows/deploy-ci.yml/badge.svg)](https://github.com/elna-ai/elna-external-service/actions/workflows/deploy-ci.yml)
[![Pylint](https://github.com/elna-ai/elna-external-service/actions/workflows/pylint.yml/badge.svg)](https://github.com/elna-ai/elna-external-service/actions/workflows/pylint.yml)

***ELNA AWS Console*** [http://elna.awsapps.com/start/](http://elna.awsapps.com/start/)

Notes:
* There are two environments for development and production. We will only do the dev work and testing in the dev account. 
Prod environment is reserved for the production use only, we will automate the process using ci/cl in the later stage.
Means do all the Jury rigging in the ```dev``` account.
* Always do the stuff in code, any changes made using the aws console/gui will be deleted on every new deployment.

## Prerequisites

* [golang](https://go.dev/)
* [Node](https://nodejs.org/en/)
* [cdk](https://aws.amazon.com/cdk/)  ```npm install -g aws-cdk```
* [mage](https://magefile.org/)  ```brew install mage``` on mac
* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* AWS sso login and related setup (Check next step). [Docs](https://medium.com/@pushkarjoshi0410/how-to-set-up-aws-cli-with-aws-single-sign-on-sso-acf4dd88e056)

## AWS sso setup

create a new folder file called ```config``` inside ``` ~/.aws``` then copy paste the content below; save exit;

```
[profile elna-dev]
sso_start_url = http://***.awsapps.com/start#
sso_region = eu-north-1
sso_account_id = *******
sso_role_name = AdministratorAccess
region = eu-north-1
output = json

[profile elna-prod]
sso_start_url = http://***.awsapps.com/start#
sso_region = eu-north-1
sso_account_id = *****
sso_role_name = AdministratorAccess
region = eu-north-1
output = json
```

## Login to aws

firstly, open your terminal and export the environment as below;
For ```dev``` environment,
```shell
export AWS_PROFILE=elna-dev
```

For ```prod``` environment,

```shell
export AWS_PROFILE=elna-prod
```

Now we can login to aws as below;

```shell
aws sso login
```
This will auto direct to your default browser and ask for the aws login credentials, plus you have to allow some permission. thats all about it.
There is some time limt to the access token, most probably 8 hours.


## Magefile (Makefile alternative)

We are using a tool similar to ```makefile``` called ```mage``` for the automation and scripting. It is similar to ```Makefile``` only 
difference is in the syntax, we can write targets in simple go functions instead of Makefile syntax. Most of the time we do not need to update it. Every commands will life inside a file called ```magefile.go```. Only rule is to give Capcase for the functions to be available for usage.
So all the private function will not be exported.

For listing all available commands just type mage in the project root as follows;

```shell
mage
```

## Usage

First step is to bootstrap. for that type the command below from the root directory.

```shell
go mod tidy
mage bootstrap
```

Export the openai key

```shell
export OPEN_API_KEY=elna-key
```

## Architecture

All the apis calls will first goes to a ```cloudfront``` cdn endpoint. Then the event will be routed to ```AWS API Gateway```. The ```Api gateway``` is responsible for all the REST API configs. Finally the event will be passed to the ```AWS lambda```. In ```AWS Lambda``` a python
handler function will be involed with the necessary arguments. We are using the cloudfront only because the APIGateway does not support the ipv6
currently. 

## Lambda functions

All of our lambda function endpoints can be located ```src/lambdas```.

## Workflow

Most of the time the developer will be making changes  the lambda function and deploy using the command below.

```shell
mage deploy
```

## Tests

Always runs tests before deployment. Example Test case for the ECHO Model class can be found at ```tests/inference_engine/test_ai_models.py```

```shell
mage test
```
