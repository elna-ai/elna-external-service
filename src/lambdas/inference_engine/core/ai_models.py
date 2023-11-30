from .ai_services import OpenAiService, HuggingFaceService


class BaseModel(object):
    model_name: str = "base_model"

    def __init__(self, event, api_key):
        self._event = event
        self.ai_service = self.get_ai_service(api_key)
        self._text_response = ""
        self._error_response = ""

    @classmethod
    def get_model(cls):
        return cls.model_name

    @staticmethod
    def get_ai_service(api_key):
        raise NotImplementedError("Implement the API service object")

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
            self._text_response = response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            self._error_response = e
            return False
        return True

    def get_text_response(self):
        return self._text_response

    def get_error_response(self):
        return self._error_response

    def get_biography(self):
        return self._event["biography"]

    def get_input_prompt(self):
        return self._event["input_prompt"]


class GptTurbo(BaseModel):
    model_name = "gpt-3.5-turbo"

    @staticmethod
    def get_api_service(api_key):
        service = OpenAiService(api_key)
        service.initialize()
        return service


class GptHuggingFace(BaseModel):
    model_name = "hugging_face"

    @staticmethod
    def get_api_service(api_key):
        service = HuggingFaceService(api_key)
        service.initialize()
        return service


def choose_service_model(event, context):
    # TODO:Update model selection logic here
    return GptTurbo
