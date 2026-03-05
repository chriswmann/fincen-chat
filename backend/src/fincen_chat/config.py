from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model: str


class Neo4jConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    neo4j_username: str
    neo4j_password: SecretStr
    neo4j_uri: str
    neo4j_port: int


class LangfuseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    langfuse_public_key: str = Field(
        validation_alias=AliasChoices(
            "langfuse_public_key", "langfuse_init_project_public_key"
        ),
    )
    langfuse_secret_key: SecretStr = Field(
        validation_alias=AliasChoices(
            "langfuse_secret_key", "langfuse_init_project_secret_key"
        ),
    )
    langfuse_host: str = "http://localhost:3000"


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_schema: str = "fincen"
    postgres_port: int = 5432

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}"
            f":{self.postgres_password.get_secret_value()}"
            f"@localhost:{self.postgres_port}/{self.postgres_db}"
        )
