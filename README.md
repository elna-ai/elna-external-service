# elna-external-service

## Prerequisite

* [golang](https://go.dev/)
* [Node](https://nodejs.org/en/)
* [cdk](https://aws.amazon.com/cdk/) | ```npm install -g aws-cdk```
* [mage](https://magefile.org/) | just ```brew install mage``` in mac
* AWS sso login and related setup. [Docs](https://medium.com/@pushkarjoshi0410/how-to-set-up-aws-cli-with-aws-single-sign-on-sso-acf4dd88e056)

## Magefile

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