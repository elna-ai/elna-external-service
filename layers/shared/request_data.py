"""Handle the request data for the service."""


class RequestDataHandler:
    def __init__(self, table_name, client, logger):
        self._table_name = table_name
        self._logger = logger
        self.table = client.Table(self._table_name)

    def store_prompt_response(self, identifier: str, input_prompt: str, ai_response: str):
        self.table.put_item(
            Item={
                "pk": identifier,
                "input_prompt": input_prompt,
                "response": ai_response
            }
        )

    def get_input_prompt(self, identifier: str):
        pass
