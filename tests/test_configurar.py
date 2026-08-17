"""Pruebas del paso de la clave, que es donde se trabó el cliente.

El fallo original: el programa sólo ofrecía crear el .env si el archivo NO
existía. En cuanto se creaba una vez —aunque el editor se abriera detrás de la
Terminal y no lo viera— el paso se saltaba en silencio para siempre y quedaba
sin forma de avanzar. Ahora se mira si la CLAVE está puesta, no el archivo.
"""

from __future__ import annotations

import pytest

from ragnar_agent.cli import configurar

CLAVE = "sk-ant-api03-" + "x" * 40


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Aísla .env y .env.example en una carpeta temporal."""
    plantilla = tmp_path / ".env.example"
    plantilla.write_text(
        "# comentario\nANTHROPIC_API_KEY=sk-ant-api03-REEMPLAZAR\n"
        "ANTHROPIC_MODEL=claude-opus-5\nDRY_RUN=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(configurar, "PLANTILLA", plantilla)
    monkeypatch.setattr(configurar, "DESTINO", tmp_path / ".env")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


# -- detectar si hay clave --------------------------------------------------


def test_sin_archivo_no_hay_clave(entorno):
    assert configurar.clave_actual() == ""


def test_el_marcador_de_ejemplo_no_cuenta_como_clave(entorno):
    (entorno / ".env").write_text(
        "ANTHROPIC_API_KEY=sk-ant-api03-REEMPLAZAR\n", encoding="utf-8"
    )
    assert configurar.clave_actual() == "", (
        "El valor de ejemplo no puede darse por una clave puesta"
    )


def test_reconoce_una_clave_de_verdad(entorno):
    (entorno / ".env").write_text(f"ANTHROPIC_API_KEY={CLAVE}\n", encoding="utf-8")
    assert configurar.clave_actual() == CLAVE


def test_tolera_comillas_y_espacios(entorno):
    (entorno / ".env").write_text(
        f'  ANTHROPIC_API_KEY = "{CLAVE}"  \n', encoding="utf-8"
    )
    assert configurar.clave_actual() == CLAVE


def test_ignora_las_lineas_comentadas(entorno):
    (entorno / ".env").write_text(
        f"# ANTHROPIC_API_KEY={CLAVE}\n", encoding="utf-8"
    )
    assert configurar.clave_actual() == ""


# -- guardar ----------------------------------------------------------------


def test_guardar_conserva_el_resto_del_archivo(entorno):
    configurar.guardar_clave(CLAVE)
    texto = (entorno / ".env").read_text(encoding="utf-8")

    assert f"ANTHROPIC_API_KEY={CLAVE}" in texto
    assert "ANTHROPIC_MODEL=claude-opus-5" in texto, "No debe borrar lo demás"
    assert "DRY_RUN=true" in texto


def test_guardar_sirve_en_la_misma_ejecucion(entorno, monkeypatch):
    """Sin esto habría que cerrar y volver a abrir para que tome efecto."""
    import os

    configurar.guardar_clave(CLAVE)
    assert os.environ["ANTHROPIC_API_KEY"] == CLAVE


# -- pedirla en la ventana --------------------------------------------------


def test_si_ya_hay_clave_no_pregunta_nada(entorno, monkeypatch):
    (entorno / ".env").write_text(f"ANTHROPIC_API_KEY={CLAVE}\n", encoding="utf-8")

    def no_preguntar(_):
        raise AssertionError("No debería pedir la clave si ya está puesta")

    monkeypatch.setattr("builtins.input", no_preguntar)
    assert configurar.asegurar_clave() is True


def test_la_pide_y_la_guarda(entorno, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: CLAVE)

    assert configurar.asegurar_clave() is True
    assert configurar.clave_actual() == CLAVE


def test_rechaza_algo_que_no_es_una_clave_y_reintenta(entorno, monkeypatch):
    respuestas = iter(["hola", "", CLAVE])
    monkeypatch.setattr("builtins.input", lambda _: next(respuestas))

    assert configurar.asegurar_clave() is True
    assert configurar.clave_actual() == CLAVE


def test_se_rinde_despues_de_tres_intentos(entorno, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "esto no es una clave")

    assert configurar.asegurar_clave() is False
    assert configurar.clave_actual() == ""


def test_limpia_comillas_al_pegar(entorno, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: f'"{CLAVE}"')

    assert configurar.asegurar_clave() is True
    assert configurar.clave_actual() == CLAVE


def test_si_cancela_no_rompe(entorno, monkeypatch):
    def cancelar(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", cancelar)
    assert configurar.asegurar_clave() is False


# -- el comando completo ----------------------------------------------------


def test_el_comando_crea_el_archivo_desde_la_plantilla(entorno, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: CLAVE)

    assert configurar.main([]) == 0
    assert (entorno / ".env").exists()
    assert configurar.clave_actual() == CLAVE


def test_el_comando_es_repetible(entorno, monkeypatch):
    """Volver a abrirlo con la clave ya puesta no debe romper ni borrarla."""
    (entorno / ".env").write_text(f"ANTHROPIC_API_KEY={CLAVE}\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _: "")

    assert configurar.main([]) == 0
    assert configurar.clave_actual() == CLAVE
