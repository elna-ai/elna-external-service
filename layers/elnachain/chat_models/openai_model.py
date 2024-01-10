"""chat models
"""
from elnachain.chat_models.base import BaseModel
from openai import OpenAI


class ChatOpenAI(BaseModel):
    """ChatOpenAI

    Args:
        BaseModel (Base Chat model)
    """

    model_name = "gpt-3.5-turbo"

    def __init__(self, api_key, logger=None) -> None:
        client = OpenAI(api_key=api_key)
        super().__init__(client, logger)
