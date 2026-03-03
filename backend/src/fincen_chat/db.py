from neo4j import GraphDatabase
from fincen_agent.config import Neo4jConfig


class Neo4jConnection:
    """Context manager that wraps a Neo4j driver using DBConfig credentials."""

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver = None

    def __enter__(self):
        uri = f"neo4j://{self._config.neo4j_uri}:{self._config.neo4j_port}"
        auth = (
            self._config.neo4j_username,
            self._config.neo4j_password.get_secret_value(),
        )
        self._driver = GraphDatabase.driver(uri=uri, auth=auth)

        self._driver.verify_connectivity()
        return self._driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._driver is not None:
            self._driver.close()

        return False  # don't suppress exceptions
