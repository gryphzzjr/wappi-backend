from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================================================
    # APPLICATION
    # =========================================================

    PORT: int = 8000
    ENVIRONMENT: str = "development"
    APP_URL: str = "http://localhost:8000"

    # =========================================================
    # SUPABASE
    # =========================================================

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SECRET_KEY: str
    SUPABASE_JWT_SECRET: str

    # =========================================================
    # EVOLUTION API
    # =========================================================

    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str

    # =========================================================
    # WEBHOOKS
    # =========================================================

    WEBHOOK_URL: str
    WEBHOOK_SECRET: str

    # =========================================================
    # GEMINI
    # =========================================================

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_API_KEYS: str = ""

    # =========================================================
    # GROQ
    # =========================================================

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_API_KEYS: str = ""

    # =========================================================
    # MEDIA
    # =========================================================

    MEDIA_SECRET_KEY: str = ""

    # =========================================================
    # MERCADO PAGO
    # =========================================================

    MP_TEST_PUBLIC_KEY: str = ""
    MP_TEST_ACCESS_TOKEN: str = ""

    MP_PROD_PUBLIC_KEY: str = ""
    MP_PROD_ACCESS_TOKEN: str = ""

    MP_CLIENT_ID: str = ""
    MP_CLIENT_SECRET: str = ""

    MP_ENVIRONMENT: str = "sandbox"
    MP_WEBHOOK_SECRET: str = ""

    # =========================================================
    # SETTINGS
    # =========================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # =========================================================
    # MERCADO PAGO HELPERS
    # =========================================================

    @property
    def mercado_pago_access_token(self) -> str:
        """
        Retorna automaticamente o Access Token correspondente
        ao ambiente configurado.
        """

        if self.MP_ENVIRONMENT.lower() == "production":
            return self.MP_PROD_ACCESS_TOKEN

        return self.MP_TEST_ACCESS_TOKEN

    @property
    def mercado_pago_public_key(self) -> str:
        """
        Retorna automaticamente a Public Key correspondente
        ao ambiente configurado.
        """

        if self.MP_ENVIRONMENT.lower() == "production":
            return self.MP_PROD_PUBLIC_KEY

        return self.MP_TEST_PUBLIC_KEY

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
