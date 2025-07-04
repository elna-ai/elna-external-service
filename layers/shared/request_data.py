"""Handle the request data for the service."""

import time

from boto3.dynamodb.conditions import Key


class RequestDataHandler:
    """Handle the request data for the service."""

    retry_count = 60
    retry_interval_sec = 1

    def __init__(self, table_name, client, logger):
        self._table_name = table_name
        self._logger = logger
        self.table = client.Table(self._table_name)

    def store_prompt_response(self, identifier: str, ai_response: str):
        """Store prompt response to the dynamodb table"""
        self.table.put_item(Item={"pk": identifier, "response": ai_response})

    def query_prompt_response(self, identifier: str):
        """Query prompt response from the dynamodb table using identifier"""
        response = self.table.query(KeyConditionExpression=Key("pk").eq(identifier))
        items = response["Items"]

        if not items:
            return None

        if len(items) > 1:
            raise Exception(f"More than one item found for {identifier}")

        prompt_entry = items[0]
        self._logger.info(msg=f"Prompt response: {str(prompt_entry)}")
        prompt_response = prompt_entry["response"]
        return prompt_response

    def wait_for_response(self, identifier: str):
        """Wait for prompt response to be stored in the dynamodb table by the sqs"""
        for retry in range(self.retry_count):
            self._logger.info(msg=f"Retry count {retry}!")
            response = self.query_prompt_response(identifier)
            if response is None:
                time.sleep(self.retry_interval_sec)
                continue
            return response

        raise Exception("response timeout")
