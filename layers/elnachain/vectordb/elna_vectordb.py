import base64
import os

from elnachain.vectordb.vectordb import Database
from ic.agent import Agent
from ic.candid import Types, encode
from ic.client import Client
from ic.identity import Identity


class ElnaVectorDB(Database):
    """
    vector databse class

    """

    DERIVED_EMB_SIZE = 1536
    CANISTER_ID = os.environ.get("VECTOR_DB_CID")
    RAG_CANISTER_ID = os.environ.get("RAG_CID")
    # IDENTITY = base64.b64decode(os.getenv("IDENTITY")).decode("utf-8")

    @staticmethod
    def _get_identity():
        encoded = os.getenv("IDENTITY")
        if not encoded:
            raise ValueError("IDENTITY environment variable not set")

        # Remove whitespace/newlines (common when copying PEMs)
        encoded = encoded.strip()

        # Add padding if missing (base64 requires length divisible by 4)
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += "=" * (4 - missing_padding)

        return base64.b64decode(encoded).decode("utf-8")

    IDENTITY = _get_identity.__func__()

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
            embedding (embedding client): to create vector embedding
            documents (list of JSON): contents and meta data of documents
        """
        self.create_index()
        self.insert(embedding, documents, file_name)
        self.build_index()
        return None

    # def upload(self, embedding, documents, file_name=None):
    #     """create a new index and insert documents to that index

    #     Args:
    #         embedding (embedding client): to create vector embedding
    #         documents (list of JSON): contents and meta data of documents
    #     """
    #     embeddings = [embedding.embed_query(doc["pageContent"]) for doc in documents]
    #     contents = [doc["pageContent"] for doc in documents]

    #     params = [
    #         {"type": Types.Text, "value": self._index_name},
    #         {"type": Types.Nat64, "value": self.DERIVED_EMB_SIZE},
    #         {"type": Types.Vec(Types.Text), "value": contents},
    #         {"type": Types.Vec(Types.Vec(Types.Float32)), "value": embeddings},
    #         {"type": Types.Text, "value": file_name},
    #     ]
    #     result = self._client.update_raw(
    #         self.RAG_CANISTER_ID, "create_index", encode(params=params)
    #     )
    #     self._logger.info(msg=f"uploading filename: {file_name}\n result: {result}")

    def upload_batch(
        self, embedding, documents, is_first_chunk, is_last_chunk, file_name=None
    ):
        """Insert documents in batches through RAG canister"""

        # Extract pageContent from documents
        contents = [doc["pageContent"] for doc in documents]

        # Generate embeddings using the embedding client
        embeddings = [embedding.embed_query(text) for text in contents]

        if is_first_chunk:
            # Create collection through RAG canister
            params = [
                {"type": Types.Text, "value": self._index_name},
                {"type": Types.Nat64, "value": self.DERIVED_EMB_SIZE},
            ]
            result = self._client.update_raw(
                self.RAG_CANISTER_ID, "create_collection", encode(params=params)
            )
            self._logger.info(f"Created collection: {result}")

        # Prepare insert parameters matching RAG canister's expected format
        params = [
            {"type": Types.Text, "value": self._index_name},
            {"type": Types.Vec(Types.Text), "value": contents},  # Documents text
            {
                "type": Types.Vec(Types.Vec(Types.Float32)),
                "value": embeddings,
            },  # Embeddings
            {"type": Types.Text, "value": file_name},
        ]

        # Call insert_data on RAG canister
        result = self._client.update_raw(
            self.RAG_CANISTER_ID, "insert_data", encode(params=params)
        )
        self._logger.info(f"Inserted {len(documents)} documents: {result}")

        if is_last_chunk:
            # Build index through RAG canister
            params = [{"type": Types.Text, "value": self._index_name}]
            result = self._client.update_raw(
                self.RAG_CANISTER_ID, "build_index", encode(params=params)
            )
            self._logger.info(f"Built index: {result}")
            self._logger.info(f"Total documents processed: {len(contents)}")

        return None

    def upload_batch_optimized(
        self,
        embedding,
        documents,
        session_id,
        file_name=None,
        chunk_index=0,
        total_chunks=1,
        total_files=1,
    ):
        """Optimized batch upload with session-based state management"""

        # Extract pageContent from documents
        contents = [doc["pageContent"] for doc in documents]

        # Generate embeddings using the embedding client
        embeddings = [embedding.embed_query(text) for text in contents]

        # Parameters for insert_batch_with_state_management (updated with total_files)
        params = [
            {"type": Types.Text, "value": session_id},  # session_id: String
            {"type": Types.Text, "value": self._index_name},  # index_name: String
            {
                "type": Types.Vec(Types.Text),
                "value": contents,
            },  # documents: Vec<String>
            {
                "type": Types.Vec(Types.Vec(Types.Float32)),
                "value": embeddings,
            },  # embeddings: Vec<Vec<f32>>
            {"type": Types.Text, "value": file_name or ""},  # file_name: String
            {"type": Types.Nat64, "value": chunk_index},  # chunk_index: usize
            {"type": Types.Nat64, "value": total_chunks},  # total_chunks: usize
            {"type": Types.Nat64, "value": total_files},  # total_files: usize (NEW)
        ]

        # Call the state management method on RAG canister
        result = self._client.update_raw(
            self.RAG_CANISTER_ID,
            "insert_batch_with_state_management",
            encode(params=params),
        )

        self._logger.info(
            f"Processed chunk {chunk_index + 1}/{total_chunks} for file '{file_name}' in session {session_id} (total files: {total_files}): {result}"
        )
        return result

    # def upload_batch_optimized(self, embedding, documents, is_first_chunk, is_last_chunk, file_name=None, chunk_index=0, total_chunks=1):
    #     """Optimized batch upload with single canister call per chunk"""

    #     # Extract pageContent from documents
    #     contents = [doc["pageContent"] for doc in documents]

    #     # Generate embeddings using the embedding client
    #     embeddings = [embedding.embed_query(text) for text in contents]

    #     # Single canister call with all metadata
    #     params = [
    #         {"type": Types.Text, "value": self._index_name},
    #         {"type": Types.Vec(Types.Text), "value": contents},
    #         {"type": Types.Vec(Types.Vec(Types.Float32)), "value": embeddings},
    #         {"type": Types.Text, "value": file_name},
    #         {"type": Types.Bool, "value": is_first_chunk},
    #         {"type": Types.Bool, "value": is_last_chunk},
    #         {"type": Types.Nat64, "value": total_chunks},
    #         {"type": Types.Nat64, "value": chunk_index},
    #     ]

    #     # Call the optimized method on RAG canister
    #     result = self._client.update_raw(
    #         self.RAG_CANISTER_ID,
    #         "insert_batch_optimized",
    #         encode(params=params)
    #     )

    #     self._logger.info(f"Processed chunk {chunk_index + 1}/{total_chunks}: {result}")
    #     return None

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
