"""Pruebas del prompt que se le arma al agente.

El cliente reporto que el bot le decia a un cliente suyo que NO tenian
oficina fisica, cuando tienen dos. La informacion falsa salia de una FAQ que
yo redacte de borrador sin que el la hubiera dado. Estas pruebas evitan que
algo asi vuelva a llegar al prompt.
"""

from __future__ import annotations

import pytest

from ragnar_agent import config
from ragnar_agent.ai.prompts import construir_sistema

OPERACIONES = {"bob_a_pen": "Bolivianos → Soles"}


@pytest.fixture
def sistema():
    return construir_sistema(config.negocio(), OPERACIONES)


# -- oficinas ---------------------------------------------------------------


def test_las_direcciones_estan_en_el_prompt(sistema):
    assert "Av. Panamericana 287" in sistema
    assert "Calle Saphy 808" in sistema


def test_nombra_las_dos_ciudades(sistema):
    assert "Desaguadero" in sistema
    assert "Cusco" in sistema


def test_prohibe_decir_que_no_hay_oficina(sistema):
    """Era exactamente la respuesta equivocada que dio."""
    assert "NUNCA digas que no tenemos oficina" in sistema


def test_no_afirma_que_operan_solo_remoto(sistema):
    """La frase original decia 'Operamos de forma remota', que era falso."""
    assert "Operamos de forma remota" not in sistema


def test_las_oficinas_salen_de_la_configuracion():
    """Agregar una sucursal debe ser editar el YAML, no tocar codigo."""
    cfg = dict(config.negocio())
    cfg["oficinas"] = [{"ciudad": "La Paz", "direccion": "Calle Falsa 123"}]
    cfg["faq"] = []  # las FAQ tambien nombran ciudades; se aislan

    sistema = construir_sistema(cfg, OPERACIONES)
    assert "La Paz" in sistema and "Calle Falsa 123" in sistema
    assert "Cusco" not in sistema, "El bloque debe salir de 'oficinas', no fijo"


def test_sin_oficinas_no_rompe():
    """Un negocio sin local no debe generar un bloque vacio raro."""
    cfg = dict(config.negocio())
    cfg["oficinas"] = []

    sistema = construir_sistema(cfg, OPERACIONES)
    assert "## Oficinas" not in sistema
    assert "Horario de atención" in sistema


# -- aviso de horario -------------------------------------------------------


def test_acota_cuando_avisar_del_horario(sistema):
    """Colgaba 'estamos fuera de horario' hasta en preguntas de direccion."""
    assert "NO lo agregues a preguntas que respondes tú igual de bien" in sistema


# -- lo que ya estaba ------------------------------------------------------


def test_sigue_prohibiendo_inventar_tasas(sistema):
    assert "NUNCA las inventes" in sistema


def test_sigue_pidiendo_los_datos_antes_de_derivar(sistema):
    assert "derivar_a_asesor" in sistema
    assert "teléfono" in sistema
