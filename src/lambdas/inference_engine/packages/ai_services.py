"""AI Service layer

Container of all external AI service objects and low level implementation
"""
import openai


class AiServiceBase(object):
    name = "base_ai_service"

    def __init__(self, apikey):
        self.apikey = apikey
        self._service = None

    def initialize(self):
        raise NotImplementedError("Implement the initialization")

    def chat_completion(self, model, messages):
        response = {}
        return response


class OpenAiService(AiServiceBase):
    name = "openai_service"

    def initialize(self):

        self._service = openai
        self._service.api_key = self.apikey

    def chat_completion(self, model, messages):
        response = self._service.ChatCompletion.create(model=model, messages=messages)
        return response


class HuggingFaceService(AiServiceBase):
    name = "hugging_face_service"


class EchoAiService(AiServiceBase):
    name = "echo_service"

    def initialize(self):
        pass

    def chat_completion(self, model, messages):
        response = {"data": messages}
        return response
