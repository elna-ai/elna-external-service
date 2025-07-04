"""AI models layer

Contains all the AI model related objects, parsing logic and implementations.
"""


from elnachain.chat_models.messages import format_message


class BaseModel:
    """Base class for all AI models"""

    model_name: str = "base_model"

    def __init__(self, client, logger):
        self._logger = logger
        self._client = client
        self._messages = None
        self._text_response = ""
        self._error_response = ""

    def __str__(self):
        return f"{self.model_name} - Model"

    def __call__(self, messages) -> bool:
        """Create the response message"""
        try:
            response = self._client.chat.completions.create(
                model=self.model_name, messages=format_message(messages)
            )
            self._text_response = self.parse_response(response)
        except Exception as e:
            self._error_response = e
            return None
        return self._text_response

    def parse_response(self, response):
        """Parse the response"""
        if self._logger:
            self._logger.info(msg=f"ai raw response:{str(response)})")
        result = response.choices[0].message.content.strip()
        return result

    def get_text_response(self):
        """Get the text response"""
        return self._text_response

    def get_error_response(self):
        """Get the error response"""
        return self._error_response
