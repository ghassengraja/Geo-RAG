from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    VECTOR_DIM: int = 768
    
    # Spark & GeoMesa
    SPARK_MASTER: str = "spark://172.18.0.3:7077"
    SPARK_DRIVER_HOST: Optional[str] = None
    SPARK_DRIVER_PORT: int = 7078
    HADOOP_CONF_DIR: str = "/opt/hbase-2.2.6/conf/"
    GEOMESA_JARS_PATH: str = "/opt/geomesa-hbase_2.12-3.5.2/lib"
    SPARK_JARS_PATH: str = "/spark/jars"
    
    # LLM
    GOOGLE_API_KEY: str

    # Redis (Memory Checkpointing)
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings()
