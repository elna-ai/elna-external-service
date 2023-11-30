"""AI models layer

Contains all the AI model related objects, parsing logic and implementations.
"""
from .ai_services import OpenAiService, HuggingFaceService, EchoAiService


class BaseModel(object):
    model_name: str = "base_model"

    def __init__(self, event, api_key):
        self._event = event
        self.ai_service = self.get_ai_service(api_key)
        self._text_response = ""
        self._error_response = ""

    def __str__(self):
        return f"{self.model_name} - Model"

    @classmethod
    def get_model(cls):
        return cls.model_name

    def get_ai_service(self, api_key):
        raise NotImplementedError(f"Implement the API service object in {self}")

    def get_request_messages(self):
        messages = [
            {"role": "system", "content": self.get_biography()},
            {"role": "user", "content": self.get_input_prompt()},
        ]
        return messages

    def create_response(self):
        try:
            response = self.ai_service.chat_completion(
                self.get_model(), self.get_request_messages()
            )
            self._text_response = self.parse_response(response)
        except Exception as e:
            self._error_response = e
            return False
        return True

    def parse_response(self, response):
        return response["choices"][0]["message"]["content"].strip()

    def get_text_response(self):
        return self._text_response

    def get_error_response(self):
        return self._error_response

    def get_biography(self):
        try:
            bio = self._event["biography"]
        except Exception as e:
            raise Exception(f"unable to parse biography:{str(e)}")

        return bio

    def get_input_prompt(self):
        try:
            prompt = self._event["input_prompt"]
        except Exception as e:
            raise Exception(f"unable to parse input_prompt:{str(e)}")
        return prompt


class GptTurboModel(BaseModel):
    model_name = "gpt-3.5-turbo"

    def get_ai_service(self, api_key):
        service = OpenAiService(api_key)
        service.initialize()
        return service


class GptHuggingModel(BaseModel):
    model_name = "hugging_face"

    def get_ai_service(self, api_key):
        service = HuggingFaceService(api_key)
        service.initialize()
        return service


class EchoModel(BaseModel):
    model_name = "gpt-3.5-turbo"

    def get_ai_service(self, api_key):
        service = EchoAiService(api_key)
        service.initialize()
        return service

    def get_request_messages(self):
        messages = [
            self.get_biography(),
            self.get_input_prompt(),
        ]
        return messages

    def parse_response(self, response):
        return response["data"]


def choose_service_model(event, context):
    # TODO:Update model selection logic here
    return EchoModel
