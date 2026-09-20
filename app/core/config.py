from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PORT: int = 3000
    NODE_ENV: str = "development"

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SECRET_KEY: str
    SUPABASE_JWT_SECRET: str

    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_API_KEYS: str = ""

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEYS: str = ""

    WEBHOOK_URL: str
    WEBHOOK_SECRET: str

    MEDIA_SECRET_KEY: str = ""

    MP_TEST_PUBLIC_KEY: str = ""
    MP_TEST_ACCESS_TOKEN: str = ""

    MP_PROD_PUBLIC_KEY: str = ""
    MP_PROD_ACCESS_TOKEN: str = ""

    MP_CLIENT_ID: str = ""
    MP_CLIENT_SECRET: str = ""

    MP_ENVIRONMENT: str = "sandbox"

    APP_URL: str = "http://localhost:3000"

    MP_WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
