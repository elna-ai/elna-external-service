"""Handle the request data for the service."""


class RequestDataHandler:
    def __init__(self, table_name, client, logger):
        self._dynamo_client = client
        self._table_name = table_name
        self._logger = logger

    def store_input_prompt(self, identifier: str, input_prompt: str):
        pass

    def get_input_prompt(self, identifier: str):
        pass
