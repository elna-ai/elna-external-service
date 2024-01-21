"""Request queue handler"""
import boto3


class RequestQueueHandler:
    """Request queue handler class"""

    def __init__(self, sqs_name, sqs_url, client, logger):
        self._sqs_name = sqs_name
        self._sqs_url = sqs_url
        self._sqs_client = client
        self._logger = logger

    def send_message(self, uuid, message: str):
        """Send message to sqs queue"""
        response = self._sqs_client.send_message(
            QueueUrl=self._sqs_url,
            MessageBody=message,
            MessageDeduplicationId=uuid,
            MessageGroupId=uuid,
        )
        self._logger.info(msg=f"send_msg_q : {str(response)}")
