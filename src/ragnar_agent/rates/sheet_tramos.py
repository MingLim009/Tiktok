"""Proveedor de tasas basado en las tablas de tramos de la hoja de Ragnar."""

from __future__ import annotations

import time

import requests

from ..logging_setup import get_logger
from .base import ProveedorDeTasas, TasasVigentes
from .tramos import TablaTramos, parsear

log = get_logger(__name__)


class SheetTramosProvider(ProveedorDeTasas):
    nombre = "google_sheet_tramos"

    def __init__(self, cfg: dict) -> None:
        self._url: str = cfg["csv_url"]
        self._nombres: list[str] = list(cfg.get("tablas") or [])
        self._ttl: int = int(cfg.get("cache_segundos", 300))
        self._cache: TasasVigentes | None = None
        self._cache_ts: float = 0.0

    def obtener(self) -> TasasVigentes:
        ahora = time.monotonic()
        if self._cache is not None and (ahora - self._cache_ts) < self._ttl:
            return self._cache

        resp = requests.get(self._url, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"

        tablas = parsear(resp.text, self._nombres)
        if not tablas:
            raise ValueError(
                "No se pudo leer ninguna tabla de tramos de la hoja. "
                "Revisa que siga publicada y que los títulos de los bloques "
                "no hayan cambiado (config/tasas.yaml → sheet_tramos.tablas)."
            )

        tasas = TasasVigentes(
            valores={f"{n}:min": t.tramos[0].tasa for n, t in tablas.items()},
            fecha=_fecha(resp.text),
            fuente=self.nombre,
            tablas=tablas,
        )
        self._cache = tasas
        self._cache_ts = ahora
        log.info(
            "Tramos leídos de la hoja (%s): %s",
            tasas.fecha or "sin fecha",
            ", ".join(f"{n}={len(t)} tramos" for n, t in tablas.items()),
        )
        return tasas


def _fecha(texto: str) -> str | None:
    """La hoja pone la fecha suelta en la primera columna de algunas filas."""
    import re

    m = re.search(r"^(\d{1,2}/\d{1,2}/\d{4})", texto, re.MULTILINE)
    return m.group(1) if m else None


def tabla_de(tasas: TasasVigentes, nombre: str) -> TablaTramos:
    tablas = tasas.tablas or {}
    if nombre not in tablas:
        raise KeyError(
            f"La hoja no trae la tabla '{nombre}'. "
            f"Disponibles: {', '.join(sorted(tablas)) or 'ninguna'}"
        )
    return tablas[nombre]
