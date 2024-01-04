# import sys
# sys.path.append('~/root/gravitas/aws/elna-external-service/layers')

from elnachain.chat_models.openai_model import ChatOpenAI
from elnachain.chat_models.messages import SystemMessage,HumanMessage,AiMessage

from dotenv import load_dotenv
import os

load_dotenv()

chat=ChatOpenAI(os.getenv('OPEN_AI_KEY'))

messages = [
    SystemMessage(content="You are a helpful assistant"),
    HumanMessage(content="Say this is a test"),
]

response=chat(messages)
print(response)