"""Motor de cotización: convierte tasas crudas + tramos por monto en una
cotización concreta para el cliente.

Reglas de signo (lo más fácil de equivocar, por eso está centralizado aquí):

  modo = dividir      recibe = entrega / tasa
                      -> una tasa MÁS BAJA le da MÁS al cliente
  modo = multiplicar  recibe = entrega * tasa
                      -> una tasa MÁS ALTA le da MÁS al cliente

`mejora_cliente` siempre es un número positivo que significa "mejor para el
cliente"; el motor decide si eso implica sumar o restar. `margen_absoluto` es
lo contrario: siempre a favor de la casa de cambio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .. import config
from ..logging_setup import get_logger
from .base import ProveedorDeTasas, TasasVigentes
from .manual import ManualProvider

log = get_logger(__name__)


class OperacionDesconocida(Exception):
    """La operación pedida no existe o está desactivada."""


class MontoInvalido(Exception):
    """El monto es cero, negativo o está por debajo del mínimo."""


class RequiereAsesor(Exception):
    """La operación existe pero no se cotiza automáticamente (ej. SWIFT)."""

    def __init__(self, mensaje: str, motivo: str) -> None:
        super().__init__(mensaje)
        self.motivo = motivo


@dataclass
class Cotizacion:
    operacion: str
    etiqueta: str
    entrega_moneda: str
    recibe_moneda: str
    monto_entrega: float
    monto_recibe: float
    tasa_aplicada: float
    tasa_base: float
    modo: str
    tramo: str
    fuente: str
    fecha_tasa: str | None
    revisar: bool = False
    advertencias: list[str] = field(default_factory=list)

    def texto(self) -> str:
        """Resumen en una línea, pensado para que la IA lo use tal cual."""
        base = (
            f"{_fmt(self.monto_entrega)} {self.entrega_moneda} "
            f"= {_fmt(self.monto_recibe)} {self.recibe_moneda} "
            f"(tasa {self.tasa_aplicada:g})"
        )
        if self.revisar:
            base += " [sujeto a confirmación de un asesor]"
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "operacion": self.operacion,
            "etiqueta": self.etiqueta,
            "entrega": f"{_fmt(self.monto_entrega)} {self.entrega_moneda}",
            "recibe": f"{_fmt(self.monto_recibe)} {self.recibe_moneda}",
            "tasa_aplicada": round(self.tasa_aplicada, 4),
            "tramo": self.tramo,
            "fecha_de_la_tasa": self.fecha_tasa,
            "fuente": self.fuente,
            "requiere_confirmacion": self.revisar,
            "advertencias": self.advertencias,
        }


class MotorDeTasas:
    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        self._cfg = cfg if cfg is not None else config.tasas()
        self._ops: dict[str, dict] = self._cfg.get("operaciones", {}) or {}
        self._ref_usd: dict[str, float] = self._cfg.get("referencia_usd", {}) or {}
        self._proveedor = _construir_proveedor(self._cfg)
        self._respaldo = _construir_respaldo(self._cfg)

    # -- información ------------------------------------------------------
    def operaciones_disponibles(self) -> dict[str, str]:
        return {
            nombre: op.get("etiqueta", nombre)
            for nombre, op in self._ops.items()
            if op.get("activa", True)
        }

    def tasas_crudas(self) -> TasasVigentes:
        try:
            return self._proveedor.obtener()
        except Exception as exc:  # noqa: BLE001 - queremos degradar, no caer
            if self._respaldo is None:
                raise
            log.warning(
                "Falló la fuente de tasas '%s' (%s). Usando respaldo manual.",
                self._proveedor.nombre,
                exc,
            )
            return self._respaldo.obtener()

    # -- cotización -------------------------------------------------------
    def cotizar(self, operacion: str, monto: float) -> Cotizacion:
        op = self._ops.get(operacion)
        if op is None or not op.get("activa", True):
            disponibles = ", ".join(self.operaciones_disponibles()) or "ninguna"
            raise OperacionDesconocida(
                f"La operación '{operacion}' no existe. Disponibles: {disponibles}"
            )

        if op.get("solo_derivar"):
            raise RequiereAsesor(
                f"{op.get('etiqueta', operacion)} se coordina con un asesor.",
                motivo=op.get("motivo_derivacion", "peticion_explicita"),
            )

        monto = float(monto)
        if monto <= 0:
            raise MontoInvalido("El monto tiene que ser mayor que cero.")

        # Mínimo sobre lo que ENTREGA el cliente (en la moneda de origen).
        minimo = float(op.get("monto_minimo", 0) or 0)
        if minimo and monto < minimo:
            raise MontoInvalido(
                f"El mínimo para {op.get('etiqueta', operacion)} es "
                f"{_fmt(minimo)} {op['entrega']}."
            )

        tasas = self.tasas_crudas()
        modo = op.get("modo", "dividir")
        if modo not in {"dividir", "multiplicar"}:
            raise ValueError(f"Modo inválido '{modo}' en la operación '{operacion}'.")

        # Signo: +1 si subir la tasa favorece a la casa; -1 si la favorece bajarla.
        signo_casa = 1 if modo == "dividir" else -1

        if op.get("tabla"):
            # Fuente actual: la hoja trae la tabla de tramos completa y el
            # intervalo ya está en la moneda que entrega el cliente.
            tabla = (tasas.tablas or {}).get(op["tabla"])
            if tabla is None:
                raise OperacionDesconocida(
                    f"La hoja no trae la tabla '{op['tabla']}' que necesita "
                    f"la operación '{operacion}'."
                )
            tramo = tabla.buscar(monto)
            tasa_base = tasa = tramo.tasa
            tramo_nombre = tramo.etiqueta(tabla.unidad or op["entrega"])
        else:
            # Fuente antigua: una tasa suelta por columna + ajustes en el YAML.
            tasa_base = tasas.get(op["columna"])
            tasa = tasa_base + signo_casa * float(op.get("margen_absoluto", 0) or 0)
            usd = self._a_usd(monto, op["entrega"])
            tramo_cfg, tramo_nombre = self._elegir_tramo(op, usd)
            tasa -= signo_casa * float(tramo_cfg.get("mejora_cliente", 0) or 0)

        if tasa <= 0:
            raise ValueError(
                f"La tasa calculada para '{operacion}' quedó en {tasa}. "
                f"Revisa 'margen_absoluto' y 'mejora_cliente' en config/tasas.yaml."
            )

        recibe = monto / tasa if modo == "dividir" else monto * tasa
        decimales = int(op.get("decimales", 2))

        # Mínimo sobre lo que RECIBE el cliente. Va aquí y no arriba porque
        # sólo se conoce después de aplicar la tasa. Es el caso de SWIFT: el
        # mínimo son 1.000 dólares de salida, no una cantidad de bolivianos
        # de entrada — ese equivalente cambia cada vez que se mueve la tasa.
        minimo_recibe = float(op.get("monto_minimo_recibe", 0) or 0)
        if minimo_recibe and recibe < minimo_recibe:
            # El equivalente se calcula con la tasa del tramo al que caeria ese
            # minimo, no con la del monto rechazado: si no, se quedaria corto y
            # el cliente volveria con una cifra que tampoco alcanza.
            if op.get("tabla") and (tasas.tablas or {}).get(op["tabla"]):
                tabla_min = tasas.tablas[op["tabla"]]
                objetivo = minimo_recibe * tasa if modo == "dividir" else minimo_recibe / tasa
                for _ in range(4):  # converge en una o dos vueltas
                    t2 = tabla_min.buscar(objetivo).tasa
                    nuevo = minimo_recibe * t2 if modo == "dividir" else minimo_recibe / t2
                    if abs(nuevo - objetivo) < 0.01:
                        break
                    objetivo = nuevo
                equivalente = objetivo
            else:
                equivalente = (
                    minimo_recibe * tasa if modo == "dividir" else minimo_recibe / tasa
                )
            raise MontoInvalido(
                f"El mínimo para {op.get('etiqueta', operacion)} es "
                f"{_fmt(minimo_recibe)} {op['recibe']}. "
                f"Con la tasa de hoy hacen falta unos "
                f"{_fmt(round(equivalente, decimales))} {op['entrega']}."
            )

        advertencias: list[str] = []
        if tasas.fuente == "manual":
            advertencias.append(
                "Tasa de respaldo: no se pudo leer la fuente en vivo."
            )

        return Cotizacion(
            operacion=operacion,
            etiqueta=op.get("etiqueta", operacion),
            entrega_moneda=op["entrega"],
            recibe_moneda=op["recibe"],
            monto_entrega=round(monto, decimales),
            monto_recibe=round(recibe, decimales),
            tasa_aplicada=tasa,
            tasa_base=tasa_base,
            modo=modo,
            tramo=tramo_nombre,
            fuente=tasas.fuente,
            fecha_tasa=tasas.fecha,
            revisar=bool(op.get("revisar", False)),
            advertencias=advertencias,
        )

    # -- internos ---------------------------------------------------------
    def _a_usd(self, monto: float, moneda: str) -> float:
        factor = float(self._ref_usd.get(moneda, 0) or 0)
        if factor <= 0:
            log.warning(
                "Sin referencia USD para %s; se asume tramo base.", moneda
            )
            return 0.0
        return monto / factor

    def _elegir_tramo(self, op: dict, usd: float) -> tuple[dict, str]:
        tramos = op.get("tramos") or [{}]
        for tramo in tramos:
            desde = float(tramo.get("desde_usd", 0) or 0)
            hasta = tramo.get("hasta_usd")
            if usd >= desde and (hasta is None or usd < float(hasta)):
                etiqueta = (
                    f"{_fmt(desde)}–{_fmt(float(hasta))} USD"
                    if hasta is not None
                    else f"más de {_fmt(desde)} USD"
                )
                return tramo, etiqueta
        return tramos[-1], "tramo por defecto"


# ---------------------------------------------------------------------------


def _construir_proveedor(cfg: dict) -> ProveedorDeTasas:
    fuente = (cfg.get("fuente") or "sheet").lower()

    if fuente == "sheet_tramos":
        from .sheet_tramos import SheetTramosProvider

        return SheetTramosProvider(cfg["sheet_tramos"])

    if fuente == "sheet":
        from .sheet import SheetProvider

        return SheetProvider(cfg["sheet"])

    if fuente == "odoo":
        from ..config import get_settings
        from .odoo import OdooProvider

        s = get_settings()
        return OdooProvider(
            url=s.odoo_url or "",
            db=s.odoo_db or "",
            username=s.odoo_username or "",
            api_key=s.odoo_api_key or "",
            campos=(cfg.get("odoo") or {}).get("campos", {}),
        )

    if fuente == "manual":
        return ManualProvider(cfg.get("manual", {}))

    raise ValueError(
        f"Fuente de tasas desconocida: '{fuente}'. "
        f"Usa sheet_tramos, sheet, odoo o manual."
    )


def _construir_respaldo(cfg: dict) -> ProveedorDeTasas | None:
    if (cfg.get("fuente") or "sheet").lower() == "manual":
        return None
    try:
        return ManualProvider(cfg.get("manual", {}))
    except ValueError:
        return None


def _fmt(valor: float) -> str:
    """Formatea sin decimales inútiles: 1000.0 -> '1000', 291.55 -> '291.55'."""
    if valor == int(valor):
        return f"{int(valor):,}".replace(",", " ")
    return f"{valor:,.2f}".replace(",", " ")


@lru_cache(maxsize=1)
def get_motor() -> MotorDeTasas:
    return MotorDeTasas()
