from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
