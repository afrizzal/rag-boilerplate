from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Database MySQL
    db_name: str = 'rag_db'
    db_user: str = 'root'
    db_password: str = ''
    db_host: str = 'localhost'
    db_port: int = 3306

    # Gemini API
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-1.5-flash'

    # RAG Settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_chunks: int = 5
    embedding_model: str = 'all-MiniLM-L6-v2'

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()
