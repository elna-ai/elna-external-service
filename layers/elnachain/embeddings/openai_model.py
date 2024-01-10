from typing import List

from openai import OpenAI


class OpenAIEmbeddings:
    """
    generate vector embddings using Openai's model

    """

    def __init__(
        self,
        api_key,
        logger=None,
        model: str = "text-embedding-ada-002",
    ) -> None:
        self._model = model
        self._logger = logger
        self._client = OpenAI(api_key=api_key)

    def embed_query(self, text: str) -> List[float]:
        """Call out to OpenAI's embedding endpoint for embedding query text.

        Args:
            text: The text to embed.

        Returns:
            Embedding for the text.
        """
        text = text.replace("\n", " ")
        return (
            self._client.embeddings.create(input=[text], model=self._model)
            .data[0]
            .embedding
        )


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()
    openai_api_key = os.getenv("OPEN_AI_KEY")
    embeddings = OpenAIEmbeddings(api_key=openai_api_key)
    TEXT = "This is a test document."
    query_result = embeddings.embed_query(TEXT)
    print(query_result[:5])
