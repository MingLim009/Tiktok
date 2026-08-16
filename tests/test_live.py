"""Pruebas de la detección de palabras clave en comentarios del Live."""

from __future__ import annotations

import pytest

from ragnar_agent import config
from ragnar_agent.tiktok.live import cargar_reglas, evaluar, identificar, normalizar


@pytest.fixture
def reglas():
    return cargar_reglas(config.live())


# -- normalización ----------------------------------------------------------


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("YO", "yo"), ("¡Yo!", "yo"), ("yo...", "yo"),
        ("Yó", "yo"), ("  yo  ", "yo"), ("Información", "informacion"),
    ],
)
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


# -- coincidencias esperadas ------------------------------------------------


@pytest.mark.parametrize("comentario", ["yo", "YO", "¡Yo!", "yoo", "Yo!!!", "interesada"])
def test_detecta_interes(reglas, comentario):
    regla = evaluar(comentario, reglas)
    assert regla is not None and regla.id == "interes_general"


@pytest.mark.parametrize(
    "comentario",
    ["cuánto está la tasa?", "a que precio esta hoy", "quiero saber el cambio"],
)
def test_detecta_tasa(reglas, comentario):
    regla = evaluar(comentario, reglas)
    assert regla is not None and regla.id == "tasa"


# -- falsos positivos (lo que NO debe disparar) -----------------------------


@pytest.mark.parametrize(
    "comentario",
    [
        "yo ya cambié con ustedes la semana pasada y todo bien",
        "ayer yo estuve viendo el live completo y me gustó",
        "hola buenas noches",
        "",
        "   ",
        "😍😍😍",
    ],
)
def test_no_dispara_de_mas(reglas, comentario):
    assert evaluar(comentario, reglas) is None


def test_regla_desactivada_no_carga(reglas):
    # 'dolares' está con activa: false en config/live.yaml
    assert all(r.id != "dolares" for r in reglas)
    assert evaluar("tienen dolares?", reglas) is None


# -- plantillas -------------------------------------------------------------


def test_plantilla_reemplaza_nombre(reglas):
    regla = next(r for r in reglas if r.id == "interes_general")
    mensaje = regla.mensaje_para("Ana")
    assert "Ana" in mensaje
    assert "{nombre}" not in mensaje


def test_hay_varias_plantillas_por_regla(reglas):
    """Mensajes idénticos en masa son lo que más rápido marca TikTok."""
    for regla in reglas:
        assert len(regla.plantillas) >= 2, f"la regla '{regla.id}' tiene una sola"


# -- identificación del comentarista ---------------------------------------
#
# Sin el handle no se le puede abrir el chat a nadie, así que si estos tests
# fallan el bot de Live queda mudo SIN dar ningún error. Por eso se prueba
# contra el objeto real de la librería y no contra uno inventado.


class UsuarioFalso:
    def __init__(self, **campos):
        for k, v in campos.items():
            setattr(self, k, v)


def test_identificar_usa_display_id():
    handle, nombre = identificar(UsuarioFalso(display_id="ragnarfan", nickname="Ana"))
    assert handle == "ragnarfan"
    assert nombre == "Ana"


def test_identificar_quita_la_arroba():
    handle, _ = identificar(UsuarioFalso(display_id="@ragnarfan"))
    assert handle == "ragnarfan"


def test_identificar_sin_nickname_usa_el_handle():
    handle, nombre = identificar(UsuarioFalso(display_id="ragnarfan", nickname=""))
    assert handle == nombre == "ragnarfan"


def test_identificar_sin_handle_devuelve_vacio():
    """Sin handle el bot debe abstenerse, no inventar un destinatario."""
    handle, _ = identificar(UsuarioFalso(nickname="Ana"))
    assert handle == ""


def test_identificar_tolera_user_none():
    assert identificar(None) == ("", "")


def test_el_campo_real_de_la_libreria_sigue_existiendo():
    """Guarda contra un cambio de nombre de campo al actualizar TikTokLive.

    En la 6.6.6 el handle vive en `display_id`; `unique_id` NO existe. Si una
    versión futura lo renombra, este test avisa antes de que el bot de Live
    deje de enviar DMs en silencio.
    """
    proto = pytest.importorskip("TikTokLive.proto")

    usuario = proto.User()
    usuario.display_id = "ragnarfan"
    usuario.nickname = "Ana"

    handle, nombre = identificar(usuario)
    assert handle == "ragnarfan", (
        "El campo del handle cambió en TikTokLive. "
        "Actualiza la lista de campos en live.identificar()."
    )
    assert nombre == "Ana"
