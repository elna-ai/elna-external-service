"""Request queue handler"""


class RequestQueueHandler:
    def __init__(self, queue_name, client, logger):
        self._sqs_name = queue_name
        self._sqs_client = client
        self._logger = logger
