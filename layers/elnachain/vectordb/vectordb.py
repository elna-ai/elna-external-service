"""_summary_"""

from abc import ABC, abstractmethod


class Database(ABC):
    """_summary_

    Args:
        ABC (_type_): _description_
    """

    def __init__(self, client, index_name, logger=None) -> None:
        self._client = client
        self._index_name = index_name
        self._logger = logger

    @staticmethod
    @abstractmethod
    def connect():
        """_summary_"""

    @abstractmethod
    def create_index(self):
        """_summary_"""

    @abstractmethod
    def delete_index(self):
        """_summary_"""

    @abstractmethod
    def insert(self, embedding, documents, file_name=None):
        """_summary_

        Args:
            embedding (_type_): _description_
            documents (_type_): _description_
            file_name (_type_, optional): _description_. Defaults to None.
        """

    @abstractmethod
    def create_insert(self, embedding, documents, file_name=None):
        """_summary_

        Args:
            embedding (_type_): _description_
            documents (_type_): _description_
            file_name (_type_, optional): _description_. Defaults to None.
        """

    @abstractmethod
    def search(self, embedding, query_text, k=2):
        """_summary_

        Args:
            embedding (_type_): _description_
            query_text (_type_): _description_
            k (int, optional): _description_. Defaults to 2.
        """
