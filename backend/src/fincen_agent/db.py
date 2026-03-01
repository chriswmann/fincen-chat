from neo4j import GraphDatabase
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    neo4j_username: str
    neo4j_password: SecretStr
    neo4j_uri: str
    neo4j_port: int


class Neo4jConnection:
    """Context manager that wraps a Neo4j driver using DBConfig credentials."""

    def __init__(self, config: DBConfig) -> None:
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
