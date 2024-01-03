
from elnachain.chat_models.base import BaseModel
from elnachain.client import Client



class GptTurboModel(BaseModel,Client):
    """GptTurboModel class"""

    model_name = "gpt-3.5-turbo"
    
    def __init__(self,api_key,logger):
        client=Client.get_openAI(api_key=api_key)
        super().__init__(logger,client)

    
