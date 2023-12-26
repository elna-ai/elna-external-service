"""Request queue handler"""
import boto3


class RequestQueueHandler:
    def __init__(self, sqs_name, sqs_url, client, logger):
        self._sqs_name = sqs_name
        self._sqs_url = sqs_url
        self._sqs_client = client
        self._logger = logger

    def send_message(self, uuid, message):
        response = self._sqs_client.send_message(
            QueueUrl=self._sqs_url,
            MessageBody=str(message),
            MessageDeduplicationId=uuid,
            MessageGroupId=uuid
        )
        self._logger.info(msg=f"queue response:{str(response)})")
