"""
Opensearch Service class - VectorDB

"""

import os

import boto3
from elnachain.vectordb.vectordb import Database
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


class OpenSearchDB(Database):
    """
    vector databse class

    """

    DERIVED_EMB_SIZE = 1536

    @staticmethod
    def connect():
        """connect the opensearch service

        Returns:
            os_client: opensearch client
        """

        os_host = os.environ.get("OPEN_SEARCH_INSTANCE", None)
        if os_host is None:
            raise Exception("OpenSearch instance not available")

        region = "eu-north-1"
        service = "es"

        credentials = boto3.Session().get_credentials()
        os_auth = AWSV4SignerAuth(credentials, region, service)

        os_client = OpenSearch(
            hosts=[{"host": os_host, "port": 443}],
            http_auth=os_auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
        )

        return os_client

    def create_index(self):
        """create a new index in opensearch

        Returns:
            response: created
        """
        index_body = {
            "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 100}},
            "mappings": {
                "_meta": {"filename": "keyword"},
                "properties": {
                    "vector": {
                        "type": "knn_vector",
                        "dimension": self.DERIVED_EMB_SIZE,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "nmslib",
                            "parameters": {"ef_construction": 128, "m": 24},
                        },
                    },
                },
            },
        }
        response = self._client.indices.create(
            self._index_name, body=index_body, ignore=[400, 404]
        )

        if "error" in response:
            return {"status": response["status"], "response": response["error"]}

        return {"status": 200, "response": "acknowledged"}

    def delete_index(self):
        """delete index if exist

        Returns:
            response: _description_
        """
        response = self._client.indices.delete(self._index_name, ignore=[400, 404])

        if "error" in response:
            return {"status": response["status"], "response": response["error"]}

        return {"status": 200, "response": "acknowledged"}

    def insert(self, embedding, documents, file_name=None):
        """insert vector embdding to a index

        Args:
            embedding (embdding object): to create vector embdding
            documents (list of JSON): contents and meta data of documents
        """
        for index, doc in enumerate(documents):
            info = doc["metadata"]["pdf"]["info"]
            self._logger.info(msg=f"doc_info:{info}")
            my_doc = {
                "_meta": {"filename": info.get("Title", file_name)},
                "id": index,
                "text": documents[index],
                "vector": embedding.embed_query(doc["pageContent"]),
            }

            response = self._client.index(
                index=self._index_name, body=my_doc, id=str(index), refresh=True
            )
            print(f"Ingesting {index} data")
            print(f"Data sent to your OpenSearch with response: {response}")

    def create_insert(self, embedding, documents, file_name=None):
        """create a new index and insert documents to that index

        Args:
            embedding (embdding clinet): to create vector embdding
            documents (list of JSON): contents and meta data of documents
        """
        response = self.create_index()
        self.insert(embedding, documents, file_name)
        return response

    def search(self, embedding, query_text, k=2):
        """similarty search of a query text

        Args:
            embedding (embdding clinet): to create vector embdding
            query_text (text): query text

        Returns:
            resulr: simiarty search result
        """
        query_vector = embedding.embed_query(query_text)
        query = {
            "size": k,
            "query": {"knn": {"vector": {"vector": query_vector, "k": k}}},
        }
        response = self._client.search(
            body=query, index=self._index_name, ignore=[400, 404]
        )
        if "error" in response:
            return (True, {"status": response["status"], "response": response["error"]})

        results = [text["_source"]["text"] for text in response["hits"]["hits"]]
        if self._logger:
            self._logger.info(msg=f"search result: {results}")
        page_contents = [result["pageContent"] for result in results]
        return (False, "\n".join(page_contents))

    def get_filenames(self):
        """get filenames under a index

        Returns:
            list: list of unique filenames
        """
        search_result = self._client.search(
            index=self._index_name,
            body={"query": {"match_all": {}}, "_source": ["_meta.filename"]},
        )
        filename = set(
            [
                hit["_source"]["_meta"]["filename"]
                for hit in search_result["hits"]["hits"]
            ]
        )
        return list(filename)
