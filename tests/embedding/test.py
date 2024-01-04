from elnachain.embeddings.openai_model import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

embeddings=OpenAIEmbeddings(os.getenv('OPEN_AI_KEY'))
text = "This is a test document."
query_result = embeddings.embed_query(text)
print(query_result[:5])
