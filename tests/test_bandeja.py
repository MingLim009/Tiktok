"""Ejercita el código que lee y responde la bandeja, contra una página local.

Estas pruebas NO validan los selectores de tiktok.com — eso sólo se puede
comprobar con una cuenta real. Lo que validan es todo lo que viene después:
detectar conversaciones sin leer, distinguir quién escribió cada burbuja,
saber cuándo ya respondimos, y el flujo de escritura y envío.

Sin esto, esa lógica llegaría a la primera sesión con el cliente sin haberse
ejecutado nunca.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ragnar_agent.tiktok.dm import Bandeja

FIXTURE = Path(__file__).parent / "fixtures" / "bandeja_falsa.html"

pytestmark = pytest.mark.skipif(
    not FIXTURE.exists(), reason="falta la bandeja de prueba"
)


@pytest.fixture(scope="module")
def pagina():
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="playwright no instalado"
    ).sync_playwright

    with sync_playwright() as pw:
        try:
            navegador = pw.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"no se pudo abrir Chromium: {exc}")
        pag = navegador.new_page(viewport={"width": 1360, "height": 900})
        pag.goto(FIXTURE.as_uri())
        pag.wait_for_selector("[data-e2e='chat-list-item']")
        yield pag
        navegador.close()


@pytest.fixture
def bandeja(pagina):
    pagina.reload()
    pagina.wait_for_selector("[data-e2e='chat-list-item']")
    return Bandeja(pagina)


# -- lectura de la lista ----------------------------------------------------


def test_lee_las_conversaciones(bandeja):
    convs = bandeja.conversaciones()
    assert [c.usuario for c in convs] == [
        "maria_lp", "jorge.andia", "cliente_atendido"
    ]


def test_detecta_cuales_estan_sin_leer(bandeja):
    sin_leer = [c.usuario for c in bandeja.conversaciones() if c.no_leido]
    assert sin_leer == ["maria_lp", "jorge.andia"]


def test_el_thread_id_identifica_al_usuario(bandeja):
    assert bandeja.conversaciones()[0].thread_id == "tiktok:maria_lp"


def test_trae_el_ultimo_mensaje_como_vista_previa(bandeja):
    assert "5000 bolivianos" in bandeja.conversaciones()[0].preview


# -- lectura del chat abierto -----------------------------------------------


def test_distingue_quien_escribio_cada_burbuja(bandeja):
    """Lo más frágil del módulo: se deduce por la posición horizontal."""
    convs = bandeja.conversaciones()
    assert bandeja.abrir(convs[0])

    mensajes = bandeja.mensajes()
    assert len(mensajes) == 3
    assert [m.entrante for m in mensajes] == [True, False, True]
    assert "a cuanto esta el cambio" in mensajes[0].texto
    assert "Depende del monto" in mensajes[1].texto


def test_ultimo_entrante_cuando_falta_responder(bandeja):
    convs = bandeja.conversaciones()
    bandeja.abrir(convs[0])
    assert "5000 bolivianos" in bandeja.ultimo_entrante()


def test_ultimo_entrante_es_none_si_ya_respondimos(bandeja):
    """Si la última burbuja es nuestra, no hay nada que contestar."""
    convs = bandeja.conversaciones()
    bandeja.abrir(convs[2])  # cliente_atendido
    assert bandeja.ultimo_entrante() is None


# -- envío ------------------------------------------------------------------


def test_envia_y_el_mensaje_aparece_como_propio(bandeja):
    convs = bandeja.conversaciones()
    bandeja.abrir(convs[1])  # jorge.andia
    antes = len(bandeja.mensajes())

    assert bandeja.enviar("¡Hola! Sí, manejamos SWIFT 🙌")

    mensajes = bandeja.mensajes()
    assert len(mensajes) == antes + 1
    ultimo = mensajes[-1]
    assert "SWIFT" in ultimo.texto
    assert ultimo.entrante is False, "El mensaje enviado debe quedar como propio"


def test_despues_de_enviar_no_hay_nada_pendiente(bandeja):
    """Evita que el bot se responda a sí mismo en la siguiente pasada."""
    convs = bandeja.conversaciones()
    bandeja.abrir(convs[1])
    bandeja.enviar("Respuesta de prueba")
    assert bandeja.ultimo_entrante() is None


def test_enviar_respeta_tildes_y_emojis(bandeja):
    convs = bandeja.conversaciones()
    bandeja.abrir(convs[1])
    texto = "El tipo de cambio de hoy es 3.48 — ¿te sirve? 🙌"
    assert bandeja.enviar(texto)
    assert bandeja.mensajes()[-1].texto == texto


# -- degradación ------------------------------------------------------------


def test_si_cambia_la_interfaz_no_revienta(pagina):
    """Con selectores que no encuentran nada, devuelve vacío en vez de fallar."""
    pagina.set_content("<html><body><p>otra cosa</p></body></html>")
    vacia = Bandeja(pagina)
    assert vacia.conversaciones() == []
    assert vacia.mensajes() == []
    assert vacia.ultimo_entrante() is None
    assert vacia.enviar("hola") is False
