import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent


def _load_env_files() -> None:
    for env_path in (
        PROJECT_DIR / ".env",
        BACKEND_DIR / ".env",
        APP_DIR / ".env",
    ):
        if env_path.exists():
            load_dotenv(env_path, override=False)


@dataclass(frozen=True)
class Settings:
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str | None
    llm_temperature: float
    llm_json_mode: bool

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and self.llm_model)


@lru_cache
def get_settings() -> Settings:
    _load_env_files()
    return Settings(
        llm_api_key=_first_env("LLM_API_KEY", "OPENAI_API_KEY"),
        llm_base_url=_first_env("LLM_BASE_URL", "OPENAI_BASE_URL"),
        llm_model=_first_env("LLM_MODEL_ID", "LLM_MODEL", "MODEL_NAME", "OPENAI_MODEL"),
        llm_temperature=_float_env("LLM_TEMPERATURE", 0.2),
        llm_json_mode=_bool_env("LLM_JSON_MODE", True),
    )


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
