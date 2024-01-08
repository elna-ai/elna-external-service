"""AI models layer

Contains all the AI model related objects, parsing logic and implementations.
"""


class BaseModel:
    """Base class for all AI models"""

    model_name: str = "base_model"

    def __init__(self, client, logger=None):
        self._logger = logger
        self._client = client
        self._event = None
        self._text_response = ""
        self._error_response = ""

    def __str__(self):
        return f"{self.model_name} - Model"

    def get_request_messages(self) -> list:
        """Get the request msg"""
        messages = [
            {"role": "system", "content": self.get_biography()},
            {"role": "user", "content": self.get_input_prompt()},
        ]
        return messages

    def create_response(self, event) -> bool:
        """Create the response message"""
        self._event = event
        try:
            response = self._client.chat.completions.create(
                model=self.model_name, messages=self.get_request_messages()
            )
            self._text_response = self.parse_response(response)
        except Exception as e:
            self._error_response = e
            return False
        return True

    def parse_response(self, response):
        """Parse the response"""

        self._logger.info(msg=f"ai raw response:{str(response)})")
        result = response.choices[0].message.content.strip()
        return result

    def get_text_response(self):
        """Get the text response"""
        return self._text_response

    def get_error_response(self):
        """Get the error response"""
        return self._error_response

    def get_biography(self) -> str:
        """Get the biography"""
        try:
            bio = self._event["biography"]
        except Exception as e:
            raise Exception(f"unable to parse biography {str(e)}")

        return bio

    def get_input_prompt(self) -> str:
        """Get the input prompt"""
        try:
            prompt = self._event["input_prompt"]
        except Exception as e:
            raise Exception(f"unable to parse input_prompt {str(e)}")
        return prompt


class GptTurboModel(BaseModel):
    """GptTurboModel class"""

    model_name = "gpt-3.5-turbo"
