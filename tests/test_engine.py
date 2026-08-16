"""Pruebas del motor de cotización sobre las tablas de tramos de la hoja.

La más importante es `test_sin_arbitraje`: protege la dirección de las tablas.
Si alguien intercambia BOB/PEN con PEN/BOB, la casa de cambio pierde dinero en
cada ida y vuelta y este test falla antes de que eso llegue a producción.
"""

from __future__ import annotations

import pytest

from ragnar_agent import config
from ragnar_agent.rates.base import ProveedorDeTasas, TasasVigentes
from ragnar_agent.rates.engine import (
    Cotizacion,
    MontoInvalido,
    MotorDeTasas,
    OperacionDesconocida,
)
from ragnar_agent.rates.tramos import TablaTramos, Tramo

# Tablas reales de la hoja "TASAS FINALES" del 15/08/2026.
TABLAS_REALES = {
    "BOB/PEN": ("BOB", [(0, 583, 3.49), (584, 1155, 3.48), (1156, 2300, 3.47),
                        (2301, 3445, 3.46), (3446, 8598, 3.45), (8599, 17185, 3.44),
                        (17186, None, 3.43)]),
    "PEN/BOB": ("PEN", [(0, 5069, 3.33), (5070, 16892, 3.34),
                        (16893, 33782, 3.35), (33783, None, 3.36)]),
    "BOB/USD": ("BOB", [(0, 583, 12.05), (584, 1155, 11.98), (1156, 2300, 11.91),
                        (2301, 3445, 11.84), (3446, 5735, 11.77), (5736, 8598, 11.74),
                        (8599, 11460, 11.67), (11461, 17185, 11.64),
                        (17186, 57260, 11.63), (57261, 114510, 11.60),
                        (114511, None, 11.59)]),
    "BOB/USD INTERNACIONAL": ("BOB", [(0, 11460, 12.45), (11461, 17185, 11.92),
                                      (17186, 57260, 11.78), (57261, None, 11.59)]),
}

MERCADO_BOB_POR_PEN = 3.39  # referencia Binance del mismo día


def _tablas():
    return {
        nombre: TablaTramos(
            nombre=nombre,
            unidad=unidad,
            tramos=[Tramo(desde=d, hasta=h, tasa=t) for d, h, t in filas],
        )
        for nombre, (unidad, filas) in TABLAS_REALES.items()
    }


class ProveedorFalso(ProveedorDeTasas):
    nombre = "test"

    def obtener(self) -> TasasVigentes:
        return TasasVigentes(
            valores={}, fecha="8/15/2026", fuente=self.nombre, tablas=_tablas()
        )


@pytest.fixture
def motor():
    m = MotorDeTasas(config.tasas())
    m._proveedor = ProveedorFalso()
    m._respaldo = None
    return m


# -- cotizaciones básicas ---------------------------------------------------


def test_bob_a_pen(motor):
    c = motor.cotizar("bob_a_pen", 1000)
    assert (c.entrega_moneda, c.recibe_moneda) == ("BOB", "PEN")
    assert c.tasa_aplicada == pytest.approx(3.48)
    assert c.monto_recibe == pytest.approx(287.36, abs=0.01)


def test_pen_a_bob(motor):
    c = motor.cotizar("pen_a_bob", 1000)
    assert c.tasa_aplicada == pytest.approx(3.33)
    assert c.monto_recibe == pytest.approx(3330.0, abs=0.01)


def test_bob_a_usd_peru(motor):
    c = motor.cotizar("bob_a_usd_peru", 1000)
    assert c.tasa_aplicada == pytest.approx(11.98)
    assert c.monto_recibe == pytest.approx(83.47, abs=0.01)


def test_swift_ahora_cotiza_solo(motor):
    """Antes derivaba a un asesor; la hoja nueva ya trae su tabla."""
    c = motor.cotizar("bob_a_usd_swift", 5000)
    assert c.tasa_aplicada == pytest.approx(12.45)
    assert c.monto_recibe == pytest.approx(401.61, abs=0.01)


# -- la invariante que protege el negocio -----------------------------------


def test_sin_arbitraje(motor):
    inicial = 10_000.0
    en_soles = motor.cotizar("bob_a_pen", inicial).monto_recibe
    de_vuelta = motor.cotizar("pen_a_bob", en_soles).monto_recibe
    assert de_vuelta < inicial, (
        f"Arbitraje: {inicial} BOB -> {en_soles} PEN -> {de_vuelta} BOB. "
        "Revisa qué tabla usa cada operación en config/tasas.yaml."
    )


@pytest.mark.parametrize("operacion,monto", [("bob_a_pen", 1000), ("pen_a_bob", 1000)])
def test_margen_a_favor_de_la_casa(motor, operacion, monto):
    c = motor.cotizar(operacion, monto)
    a_mercado = (monto / MERCADO_BOB_POR_PEN if operacion == "bob_a_pen"
                 else monto * MERCADO_BOB_POR_PEN)
    assert c.monto_recibe < a_mercado, "El cliente recibiría más que el mercado"
    margen = abs(a_mercado - c.monto_recibe) / a_mercado
    assert 0 < margen < 0.06, f"Margen fuera de rango: {margen:.2%}"


# -- escalonado por monto ---------------------------------------------------


def test_la_tasa_mejora_al_subir_el_monto(motor):
    montos = [500, 1000, 2000, 3000, 5000, 10000, 20000]
    rendimientos = [
        motor.cotizar("bob_a_pen", m).monto_recibe / m for m in montos
    ]
    for antes, despues in zip(rendimientos, rendimientos[1:]):
        assert despues >= antes, "Un monto mayor debe rendir igual o más por unidad"
    assert rendimientos[-1] > rendimientos[0]


@pytest.mark.parametrize(
    "monto,tasa_esperada",
    [(100, 3.49), (583, 3.49), (584, 3.48), (1155, 3.48),
     (1156, 3.47), (17185, 3.44), (17186, 3.43), (999999, 3.43)],
)
def test_bordes_exactos_de_los_tramos(motor, monto, tasa_esperada):
    """Los límites son inclusivos en ambos extremos, como en la hoja."""
    assert motor.cotizar("bob_a_pen", monto).tasa_aplicada == pytest.approx(tasa_esperada)


def test_el_tramo_se_nombra_en_la_moneda_que_entrega(motor):
    assert "BOB" in motor.cotizar("bob_a_pen", 1000).tramo
    assert "PEN" in motor.cotizar("pen_a_bob", 1000).tramo


# -- validaciones -----------------------------------------------------------


@pytest.mark.parametrize("monto", [0, -50, 10])
def test_montos_invalidos(motor, monto):
    with pytest.raises(MontoInvalido):
        motor.cotizar("bob_a_pen", monto)


def test_operacion_inexistente(motor):
    with pytest.raises(OperacionDesconocida):
        motor.cotizar("bob_a_euros", 100)


def test_tabla_ausente_en_la_hoja(motor):
    """Si la hoja pierde un bloque, se avisa en vez de cotizar cualquier cosa."""

    class SinTablas(ProveedorDeTasas):
        nombre = "incompleta"

        def obtener(self):
            return TasasVigentes(valores={}, fuente="incompleta", tablas={})

    motor._proveedor = SinTablas()
    with pytest.raises(OperacionDesconocida, match="BOB/PEN"):
        motor.cotizar("bob_a_pen", 1000)


# -- respaldo ---------------------------------------------------------------


def test_respaldo_manual_sigue_cotizando():
    """Si la hoja se cae, el bot cotiza con la tasa conservadora y lo avisa."""
    from ragnar_agent.rates.manual import ManualProvider

    class Rota(ProveedorDeTasas):
        nombre = "rota"

        def obtener(self):
            raise ConnectionError("sin internet")

    m = MotorDeTasas(config.tasas())
    m._proveedor = Rota()
    m._respaldo = ManualProvider(config.tasas()["manual"])

    c = m.cotizar("bob_a_pen", 1000)
    assert c.fuente == "manual"
    assert c.tasa_aplicada == pytest.approx(3.49)  # la menos favorable
    assert c.advertencias, "Debe avisar que está usando el respaldo"


def test_el_respaldo_no_es_mejor_que_la_hoja(motor):
    """El respaldo nunca debe prometer más de lo que daría la hoja real."""
    from ragnar_agent.rates.manual import ManualProvider

    real = motor.cotizar("bob_a_pen", 1000).monto_recibe

    m = MotorDeTasas(config.tasas())
    m._proveedor = ManualProvider(config.tasas()["manual"])
    m._respaldo = None
    respaldo = m.cotizar("bob_a_pen", 1000).monto_recibe

    assert respaldo <= real


# -- salida legible ---------------------------------------------------------


def test_texto_legible(motor):
    c: Cotizacion = motor.cotizar("bob_a_pen", 1000)
    texto = c.texto()
    assert "BOB" in texto and "PEN" in texto and "3.48" in texto
