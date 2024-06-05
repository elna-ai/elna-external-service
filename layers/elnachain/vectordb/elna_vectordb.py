import os
import base64


from elnachain.vectordb.vectordb import Database
from ic.agent import Agent
from ic.client import Client
from ic.identity import Identity

from ic.candid import Types, encode


class ElnaVectorDB(Database):
    """
    vector databse class

    """

    DERIVED_EMB_SIZE = 1536
    CANISTER_ID = os.environ.get("VECTOR_DB_CID")
    IDENTITY = base64.b64decode(os.getenv("IDENTITY")).decode("utf-8")

    @staticmethod
    def connect():
        iden = Identity.from_pem(pem=ElnaVectorDB.IDENTITY)
        client = Client(url="https://ic0.app")
        agent = Agent(iden, client)
        return agent

    def create_index(self):
        params = [
            {"type": Types.Text, "value": self._index_name},
            {"type": Types.Nat64, "value": self.DERIVED_EMB_SIZE},
        ]

        result = self._client.update_raw(
            self.CANISTER_ID, "create_collection", encode(params=params)
        )
        self._logger.info(msg=f"creating index: {self._index_name}\n result: {result}")

    def delete_index(self):
        pass

    def insert(self, embedding, documents, file_name=None):
        embeddings = [embedding.embed_query(doc["pageContent"]) for doc in documents]
        contents = [doc["pageContent"] for doc in documents]

        params = [
            {"type": Types.Text, "value": self._index_name},
            {"type": Types.Vec(Types.Vec(Types.Float32)), "value": embeddings},
            {"type": Types.Vec(Types.Text), "value": contents},
            {"type": Types.Text, "value": file_name},
        ]
        result = self._client.update_raw(
            self.CANISTER_ID, "insert", encode(params=params)
        )
        self._logger.info(msg=f"inserting filename: {file_name}\n result: {result}")

    def build_index(self):
        params = [{"type": Types.Text, "value": self._index_name}]
        result = self._client.update_raw(
            self.CANISTER_ID, "build_index", encode(params=params)
        )
        self._logger.info(msg=f"building index: {self._index_name}\n result: {result}")

    def create_insert(self, embedding, documents, file_name=None):
        """create a new index and insert documents to that index

        Args:
            embedding (embdding clinet): to create vector embdding
            documents (list of JSON): contents and meta data of documents
        """
        self.create_index()
        self.insert(embedding, documents, file_name)
        self.build_index()
        return None

    def search(self, embedding, query_text, k=2):
        """similarty search of a query text

        Args:
            embedding (embdding clinet): to create vector embdding
            query_text (text): query text

        Returns:
            resulr: simiarty search result
        """
        query_vector = embedding.embed_query(query_text)
        params = [
            {"type": Types.Text, "value": "test"},
            {"type": Types.Vec(Types.Float32), "value": query_vector},
            {"type": Types.Int32, "value": 1},
        ]
        results = self._client.query_raw(
            self.CANISTER_ID, "query", encode(params=params)
        )

        contents = "\n".join(results[0]["value"])
        return contents
