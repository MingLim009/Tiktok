"""Tablas de tramos por monto, leídas del Google Sheet de Ragnar Capital.

La hoja trae bloques con esta forma:

    BOB/PEN
    Intervalos en Bolivianos,,Tasa
    0,583,3.49
    584,1155,3.48
    ...
    17186,Superiores,3.43

Cada bloque es una tabla completa: desde, hasta y la tasa de ese tramo. El
intervalo está en la moneda que ENTREGA el cliente, que es justamente lo que
se necesita para elegir el tramo sin convertir nada a dólares.

Que los tramos salgan de aquí y no del archivo de configuración significa que
Ragnar Capital cambia la hoja y el bot la sigue, sin tocar nada más.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from ..logging_setup import get_logger

log = get_logger(__name__)

# Palabras que en la hoja significan "sin tope"
SIN_TOPE = {"superior", "superiores", "mas", "más", "en adelante", ""}


@dataclass(frozen=True)
class Tramo:
    desde: float
    hasta: float | None  # None = sin tope
    tasa: float

    def contiene(self, monto: float) -> bool:
        if monto < self.desde:
            return False
        return self.hasta is None or monto <= self.hasta

    def etiqueta(self, moneda: str) -> str:
        if self.hasta is None:
            return f"más de {_num(self.desde)} {moneda}"
        return f"{_num(self.desde)}–{_num(self.hasta)} {moneda}"


@dataclass
class TablaTramos:
    nombre: str
    unidad: str  # moneda en la que están los intervalos
    tramos: list[Tramo]

    def buscar(self, monto: float) -> Tramo:
        for t in self.tramos:
            if t.contiene(monto):
                return t
        # Por debajo del primer tramo (montos mínimos los valida el motor)
        return self.tramos[0]

    @property
    def minimo(self) -> float:
        return self.tramos[0].desde

    def __len__(self) -> int:
        return len(self.tramos)


def _num(valor: float) -> str:
    if valor == int(valor):
        return f"{int(valor):,}".replace(",", " ")
    return f"{valor:,.2f}".replace(",", " ")


def _a_float(celda: str) -> float | None:
    celda = (celda or "").strip().replace("$", "").replace(",", "").replace(" ", "")
    if not celda:
        return None
    try:
        return float(celda)
    except ValueError:
        return None


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").strip()).upper()


def parsear(texto_csv: str, nombres: list[str]) -> dict[str, TablaTramos]:
    """Extrae las tablas pedidas del CSV de la hoja publicada.

    `nombres` son las etiquetas tal cual aparecen en la hoja, por ejemplo
    ["PEN/BOB", "BOB/PEN", "BOB/USD", "BOB/USD INTERNACIONAL"].
    """
    filas = list(csv.reader(io.StringIO(texto_csv)))
    buscados = {_normalizar(n): n for n in nombres}
    tablas: dict[str, TablaTramos] = {}

    i = 0
    while i < len(filas):
        etiqueta = _normalizar(filas[i][0] if filas[i] else "")

        # Un título de bloque ocupa la primera celda y deja el resto vacío.
        if etiqueta not in buscados or any(c.strip() for c in filas[i][1:]):
            i += 1
            continue

        nombre = buscados[etiqueta]
        unidad = _unidad(filas[i + 1] if i + 1 < len(filas) else [])
        tramos, i = _leer_tramos(filas, i + 2)

        if tramos:
            tablas[nombre] = TablaTramos(nombre=nombre, unidad=unidad, tramos=tramos)
            log.debug("Tabla '%s': %d tramos en %s", nombre, len(tramos), unidad)
        else:
            log.warning("El bloque '%s' no traía tramos utilizables.", nombre)

    faltan = [n for n in nombres if n not in tablas]
    if faltan:
        log.warning("No se encontraron estas tablas en la hoja: %s", ", ".join(faltan))
    return tablas


def _unidad(fila_encabezado: list[str]) -> str:
    """De 'Intervalos en Bolivianos' saca 'BOB'."""
    texto = _normalizar(fila_encabezado[0] if fila_encabezado else "")
    if "SOL" in texto:
        return "PEN"
    if "BOLIVIANO" in texto:
        return "BOB"
    if "DOLAR" in texto or "DÓLAR" in texto:
        return "USD"
    return ""


def _leer_tramos(filas: list[list[str]], inicio: int) -> tuple[list[Tramo], int]:
    tramos: list[Tramo] = []
    i = inicio
    while i < len(filas):
        fila = filas[i]
        if not fila or not (fila[0] or "").strip():
            break  # línea en blanco: se acabó el bloque

        desde = _a_float(fila[0])
        if desde is None:
            break

        crudo_hasta = (fila[1] if len(fila) > 1 else "").strip()
        hasta = _a_float(crudo_hasta)
        if hasta is None and _normalizar(crudo_hasta).lower() not in SIN_TOPE:
            break
        tasa = _a_float(fila[2] if len(fila) > 2 else "")
        if tasa is None or tasa <= 0:
            break

        tramos.append(Tramo(desde=desde, hasta=hasta, tasa=tasa))
        i += 1

    return tramos, i
