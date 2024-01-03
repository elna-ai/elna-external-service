from typing import (
    List,
)
from elnachain.client import Client

class OpenAIEmbeddings:

    def __init__(self,openai_api_key : str, model : str ="text-embedding-ada-002") -> None:
        self._model=model
        self._client = Client.get_openAI(api_key=openai_api_key)


    def embed_query(self, text: str) -> List[float]:
        """Call out to OpenAI's embedding endpoint for embedding query text.

        Args:
            text: The text to embed.

        Returns:
            Embedding for the text.
        """
        text = text.replace("\n", " ")
        return self._client.embeddings.create(input = [text], model=self._model).data[0].embedding

if __name__=="__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()
    embeddings=OpenAIEmbeddings(openai_api_key=os.getenv("OPEN_AI_KEY"))
    text = "This is a test document."
    query_result = embeddings.embed_query(text)
    print(query_result[:5])