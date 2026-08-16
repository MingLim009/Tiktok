"""Carga de configuración: archivos YAML de `config/` + variables de entorno."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Raíz del proyecto: .../src/ragnar_agent/config.py -> subir 3 niveles
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

load_dotenv(ROOT / ".env")


def _read_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración: {path}\n"
            f"Revisa que la carpeta 'config/' esté junto al proyecto."
        )
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "sí", "y"}


@dataclass(frozen=True)
class Settings:
    """Valores que vienen del entorno (.env), no de los YAML."""

    anthropic_api_key: str | None
    anthropic_model: str
    tiktok_username: str
    tiktok_profile_dir: Path
    odoo_url: str | None
    odoo_db: str | None
    odoo_username: str | None
    odoo_api_key: str | None
    dry_run: bool
    log_level: str

    @property
    def db_path(self) -> Path:
        return ROOT / "ragnar_agent.sqlite3"

    def require_api_key(self) -> str:
        """Devuelve la API key o explica exactamente qué falta."""
        if not self.anthropic_api_key:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY.\n"
                "  1. Copia .env.example como .env\n"
                "  2. Pega la key de https://console.anthropic.com\n"
                "La key nunca debe escribirse dentro del código ni compartirse por chat."
            )
        return self.anthropic_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    profile = os.getenv("TIKTOK_PROFILE_DIR", ".session/tiktok")
    profile_path = Path(profile)
    if not profile_path.is_absolute():
        profile_path = ROOT / profile_path

    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
        tiktok_username=os.getenv("TIKTOK_USERNAME", ""),
        tiktok_profile_dir=profile_path,
        odoo_url=os.getenv("ODOO_URL") or None,
        odoo_db=os.getenv("ODOO_DB") or None,
        odoo_username=os.getenv("ODOO_USERNAME") or None,
        odoo_api_key=os.getenv("ODOO_API_KEY") or None,
        dry_run=_env_bool("DRY_RUN", True),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


@lru_cache(maxsize=1)
def negocio() -> dict[str, Any]:
    return _read_yaml("negocio.yaml")


@lru_cache(maxsize=1)
def tasas() -> dict[str, Any]:
    return _read_yaml("tasas.yaml")


@lru_cache(maxsize=1)
def live() -> dict[str, Any]:
    return _read_yaml("live.yaml")


def reload_all() -> None:
    """Vuelve a leer los YAML sin reiniciar el proceso."""
    negocio.cache_clear()
    tasas.cache_clear()
    live.cache_clear()
