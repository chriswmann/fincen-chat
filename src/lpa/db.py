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


def setup_db(
    db_config: DBConfig,
) -> None:
    uri = f"neo4j://{db_config.neo4j_uri}:{db_config.neo4j_port}"
    auth = (
        db_config.neo4j_username,
        db_config.neo4j_password.get_secret_value(),
    )
    with GraphDatabase.driver(uri=uri, auth=auth) as driver:
        print(driver.verify_connectivity())
        print(type(driver))

    print(db_config)
