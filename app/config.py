from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ocr_lang: str = "uzb"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
