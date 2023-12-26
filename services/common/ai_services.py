"""AI Service layer

Container of all external AI service objects and low level implementation
"""
import openai


class AiServiceBase:
    """Base class for AI Service"""

    name = "base_ai_service"

    def __init__(self, apikey):
        self.apikey = apikey
        self._service = None

    def initialize(self):
        """Initialize the AI Service"""
        raise NotImplementedError("Implement the initialization")

    def chat_completion(self, model, messages):
        """Chat completion placeholder"""
        return {}


class OpenAiService(AiServiceBase):
    """Open AI Service"""

    name = "openai_service"

    def initialize(self):
        """Initialize the AI Service"""

        self._service = openai
        self._service.api_key = self.apikey

    def chat_completion(self, model, messages):
        """Chat Completion"""

        response = self._service.ChatCompletion.create(model=model, messages=messages)
        return response


class EchoAiService(AiServiceBase):
    """Echo AI Service for unit test"""

    name = "echo_service"

    def initialize(self):
        """Initialize the Echo AI Service"""
        pass

    def chat_completion(self, model, messages):
        """Chat Completion, return the same msg"""
        response = {"data": messages}
        return response
