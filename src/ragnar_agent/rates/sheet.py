"""Lee las tasas desde el Google Sheet publicado de Ragnar Capital.

El sheet tiene dos filas de títulos antes de la fila real de encabezados
(la que empieza con "Fecha"), y muchas celdas vacías: no todos los días
tienen todas las columnas cargadas. Por eso, para cada columna se busca
el último valor NO vacío, que no necesariamente está en la última fila.
"""

from __future__ import annotations

import csv
import io
import time

import requests

from ..logging_setup import get_logger
from .base import ProveedorDeTasas, TasasVigentes

log = get_logger(__name__)


class SheetProvider(ProveedorDeTasas):
    nombre = "google_sheet"

    def __init__(self, cfg: dict) -> None:
        self._url: str = cfg["csv_url"]
        self._marca_encabezado: str = cfg.get("fila_encabezado_contiene", "Fecha")
        self._col_fecha: str = cfg.get("columna_fecha", "Fecha")
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
        tasas = self._parsear(resp.text)

        self._cache = tasas
        self._cache_ts = ahora
        log.info(
            "Tasas leídas del Google Sheet (fecha en hoja: %s): %s",
            tasas.fecha,
            {k: v for k, v in tasas.valores.items()},
        )
        return tasas

    def _parsear(self, texto: str) -> TasasVigentes:
        filas = list(csv.reader(io.StringIO(texto)))

        idx_encabezado = next(
            (
                i
                for i, fila in enumerate(filas)
                if fila and fila[0].strip() == self._marca_encabezado
            ),
            None,
        )
        if idx_encabezado is None:
            raise ValueError(
                f"No se encontró la fila de encabezados (la que empieza con "
                f"'{self._marca_encabezado}') en el Google Sheet."
            )

        encabezados = [c.strip() for c in filas[idx_encabezado]]
        datos = filas[idx_encabezado + 1 :]

        # Para cada nombre de columna, el último valor numérico no vacío.
        valores: dict[str, float] = {}
        fecha: str | None = None

        for idx, nombre in enumerate(encabezados):
            if not nombre or nombre == self._col_fecha:
                continue
            for fila in reversed(datos):
                if idx >= len(fila):
                    continue
                num = _a_float(fila[idx])
                # 0.0 en este sheet significa "sin dato", no una tasa real.
                if num is not None and num > 0:
                    valores[nombre] = num
                    break

        # Fecha de la última fila que tenga algún dato.
        try:
            i_fecha = encabezados.index(self._col_fecha)
            for fila in reversed(datos):
                if len(fila) > i_fecha and fila[i_fecha].strip():
                    fecha = fila[i_fecha].strip()
                    break
        except ValueError:
            pass

        if not valores:
            raise ValueError("El Google Sheet no devolvió ninguna tasa utilizable.")

        return TasasVigentes(valores=valores, fecha=fecha, fuente=self.nombre)


def _a_float(celda: str) -> float | None:
    celda = (celda or "").strip().replace(",", "")
    if not celda:
        return None
    try:
        return float(celda)
    except ValueError:
        return None
