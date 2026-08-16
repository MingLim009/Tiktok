"""Pruebas del diagnóstico de selectores.

Su valor está en un momento concreto: TikTok cambió la interfaz, el bot dejó
de leer la bandeja y hay un cliente esperando en la llamada. El informe tiene
que decir QUÉ se rompió y CUÁL es el reemplazo, no volcar HTML.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ragnar_agent.tiktok.diagnostico import (
    descubrir_data_e2e,
    descubrir_editables,
    informe,
    probar_selectores,
)

FIXTURE = Path(__file__).parent / "fixtures" / "bandeja_falsa.html"

# Una bandeja rediseñada: misma estructura, atributos distintos.
BANDEJA_CAMBIADA = """
<html><body>
  <div data-e2e="im-conversation-row"><p data-e2e="im-nickname">ana</p></div>
  <div data-e2e="im-conversation-row"><p data-e2e="im-nickname">luis</p></div>
  <div data-e2e="im-bubble">hola</div>
  <div data-e2e="im-composer" contenteditable="true"></div>
  <button data-e2e="im-send">Enviar</button>
</body></html>
"""


@pytest.fixture(scope="module")
def navegador():
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="playwright no instalado"
    ).sync_playwright
    with sync_playwright() as pw:
        try:
            nav = pw.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"no se pudo abrir Chromium: {exc}")
        yield nav
        nav.close()


@pytest.fixture
def pagina(navegador):
    p = navegador.new_page(viewport={"width": 1360, "height": 900})
    yield p
    p.close()


# -- cuando todo funciona ---------------------------------------------------


def test_con_la_bandeja_buena_no_reporta_nada_roto(pagina):
    pagina.goto(FIXTURE.as_uri())
    pagina.wait_for_selector("[data-e2e='chat-list-item']")

    rotos = [r for r in probar_selectores(pagina) if not r.ok]
    assert rotos == [], f"No debería haber grupos rotos: {[r.grupo for r in rotos]}"

    texto = informe(pagina)
    assert "HAY" not in texto or "GRUPO(S) SIN RESULTADOS" not in texto
    assert "Todos los selectores encuentran algo" in texto


def test_cuenta_cuantos_elementos_encuentra(pagina):
    pagina.goto(FIXTURE.as_uri())
    pagina.wait_for_selector("[data-e2e='chat-list-item']")

    lista = next(r for r in probar_selectores(pagina) if "Lista" in r.grupo)
    assert max(n for _, n in lista.encontrados) == 3  # las 3 conversaciones


# -- cuando TikTok cambia la interfaz ---------------------------------------


def test_detecta_que_los_selectores_se_rompieron(pagina):
    pagina.set_content(BANDEJA_CAMBIADA)
    rotos = [r.grupo for r in probar_selectores(pagina) if not r.ok]
    assert "Lista de conversaciones" in rotos
    assert "Burbujas del chat" in rotos


def test_propone_los_atributos_nuevos_de_la_pagina(pagina):
    """Lo importante: el informe trae el selector de reemplazo listo."""
    pagina.set_content(BANDEJA_CAMBIADA)
    encontrados = dict(descubrir_data_e2e(pagina))

    assert encontrados["im-conversation-row"] == 2
    assert "im-nickname" in encontrados
    assert "im-send" in encontrados


def test_el_informe_dice_que_constante_editar(pagina):
    pagina.set_content(BANDEJA_CAMBIADA)
    texto = informe(pagina)

    assert "SEL_LISTA_CONVERSACIONES" in texto
    assert "tiktok/dm.py" in texto
    # Y el candidato, escrito tal cual hay que pegarlo:
    assert "[data-e2e='im-conversation-row']" in texto


def test_sugiere_para_que_sirve_cada_candidato(pagina):
    pagina.set_content(BANDEJA_CAMBIADA)
    texto = informe(pagina)
    assert "¿enviar?" in texto or "¿nombre?" in texto


def test_encuentra_donde_se_puede_escribir(pagina):
    pagina.set_content(BANDEJA_CAMBIADA)
    assert "[data-e2e='im-composer']" in descubrir_editables(pagina)


# -- degradación ------------------------------------------------------------


def test_pagina_vacia_no_revienta(pagina):
    pagina.set_content("<html><body></body></html>")
    texto = informe(pagina)
    assert "DIAGNÓSTICO" in texto
    assert descubrir_data_e2e(pagina) == []
