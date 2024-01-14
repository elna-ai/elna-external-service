"""
Opensearch Service class - VectorDB

"""
import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


def os_connect():
    """connect the opensearch service

    Returns:
        os_client: opensearch client
    """

    os_host = "search-elna-test-6y2ixgct47xr5dco6vik6yvztm.aos.eu-north-1.on.aws"  # cluster endpoint
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


class VectorDB:
    """
    vector databse class

    """

    DERIVED_EMB_SIZE = 1536

    def __init__(self, os_client, index_name) -> None:
        self._os_client = os_client
        self._index_name = index_name

    def create_index(self):
        """create a new index in opensearch

        Returns:
            response: created
        """
        index_body = {
            "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 100}},
            "mappings": {
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
                    }
                }
            },
        }
        response = self._os_client.indices.create(self._index_name, body=index_body,ignore=[400, 404])

        if "error" in response:
            return {"status":response["status"],"response":response["error"]}
        
        return  {"status":200,"response":"acknowledged"}

    def delete_index(self):
        """delete index if exist

        Returns:
            response: _description_
        """
        response = self._os_client.indices.delete(self._index_name, ignore=[400, 404])
        
        if "error" in response:
            return {"status":response["status"],"response":response["error"]}
        
        return  {"status":200,"response":"acknowledged"}

    def insert(self, embedding, documents):
        """insert vector embdding to a index

        Args:
            embedding (embdding object): to create vector embdding
            documents (list of JSON): contents and meta data of documents
        """
        embeddings = [embedding.embed_query(doc["pageContent"]) for doc in documents]
        for index, _ in enumerate(documents):
            my_doc = {
                "id": index,
                "text": documents[index],
                "vector": embeddings[index],
            }

            response = self._os_client.index(
                index=self._index_name, body=my_doc, id=str(index), refresh=True
            )
            print(f"Ingesting {index} data")
            print(f"Data sent to your OpenSearch with response: {response}")

    def create_insert(self, embedding, documents):
        """create a new index and insert documents to that index

        Args:
            embedding (embdding clinet): to create vector embdding
            documents (list of JSON): contents and meta data of documents
        """
        response = self.create_index()
        self.insert(embedding, documents)
        return response

    def search(self, embedding, query_text):
        """similarty search of a query text

        Args:
            embedding (embdding clinet): to create vector embdding
            query_text (text): query text

        Returns:
            resulr: simiarty search result
        """
        query_vector = embedding.embed_query(query_text)
        query = {
            "size": 1,
            "query": {"knn": {"vector": {"vector": query_vector, "k": 1}}},
        }

        response = self._os_client.search(body=query, index=self._index_name)
        return response["hits"]["hits"][0]["_source"]["text"]
