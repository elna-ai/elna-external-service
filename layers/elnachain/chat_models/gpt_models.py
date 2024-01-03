
from elnachain.chat_models.base import BaseModel
from elnachain.client import Client



class GptTurboModel(BaseModel,Client):
    """GptTurboModel class"""

    model_name = "gpt-3.5-turbo"
    
    def __init__(self,api_key,logger):
        super().__init__(logger,api_key)

    
