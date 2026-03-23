from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Database RAG (internal)
    db_name: str = 'rag_db'
    db_user: str = 'root'
    db_password: str = ''
    db_host: str = 'localhost'
    db_port: int = 3306

    # Database MIS (read-only — gunakan user dengan hak SELECT saja)
    mis_db_enabled: bool = False
    mis_db_name: str = 'mis_db'
    mis_db_user: str = 'mis_readonly'
    mis_db_password: str = ''
    mis_db_host: str = 'localhost'
    mis_db_port: int = 3306
    mis_query_timeout: int = 10   # detik, batas waktu eksekusi query
    mis_query_max_rows: int = 500  # batas baris hasil query

    # Gemini API
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-1.5-flash'

    # JWT Auth
    jwt_secret_key: str = 'ganti-dengan-secret-key-yang-kuat-di-production'
    jwt_algorithm: str = 'HS256'
    jwt_expire_hours: int = 24

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

    @property
    def mis_database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mis_db_user}:{self.mis_db_password}"
            f"@{self.mis_db_host}:{self.mis_db_port}/{self.mis_db_name}?charset=utf8mb4"
        )


settings = Settings()
