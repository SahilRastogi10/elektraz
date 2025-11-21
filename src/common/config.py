from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import yaml, os

class AppSettings(BaseSettings):
    NREL_API_KEY: str | None = None
    CENSUS_API_KEY: str | None = None
    NREL_API_BASE: str = "https://developer.nrel.gov"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class HydraConfig(BaseModel):
    cfg: dict

def load_yaml(path: str | Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def resolve_paths(cfg: dict) -> dict:
    # ensure directories exist
    for k in ["raw", "interim", "processed", "artifacts"]:
        Path(cfg["paths"][k]).mkdir(parents=True, exist_ok=True)
    return cfg
