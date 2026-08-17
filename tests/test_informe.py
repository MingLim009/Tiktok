"""Pruebas del informe que el cliente manda por chat.

Es su único canal para mostrar qué contestaría el bot, así que tiene que ser
legible sin la terminal delante y no debe dar a entender que algo se envió.
"""

from __future__ import annotations

from ragnar_agent.ai.agent import Respuesta
from ragnar_agent.cli.run_dm import _Informe


def test_incluye_lo_que_escribio_el_cliente_y_la_respuesta(tmp_path):
    inf = _Informe()
    inf.agregar("maria_lp", "a cuanto esta el cambio?",
                Respuesta(texto="Depende del monto 🙌 ¿Cuánto querías cambiar?"))

    texto = inf.guardar(tmp_path / "r.txt").read_text(encoding="utf-8")

    assert "@maria_lp" in texto
    assert "a cuanto esta el cambio?" in texto
    assert "¿Cuánto querías cambiar?" in texto


def test_deja_claro_que_no_se_envio_nada(tmp_path):
    """Lo más importante: que no crea que sus clientes recibieron algo."""
    inf = _Informe()
    inf.agregar("ana", "hola", Respuesta(texto="¡Hola!"))

    texto = inf.guardar(tmp_path / "r.txt").read_text(encoding="utf-8")

    assert "No se envió nada" in texto or "no se envió nada" in texto
    assert "ningún cliente recibió" in texto


def test_muestra_la_cotizacion_con_su_tramo(tmp_path):
    inf = _Informe()
    inf.agregar("ana", "5000 bolivianos a soles", Respuesta(
        texto="Te llegarían 1449.28 soles",
        cotizaciones=[{
            "entrega": "5 000 BOB", "recibe": "1 449.28 PEN",
            "tasa_aplicada": 3.45, "tramo": "3 446–8 598 BOB",
        }],
    ))

    texto = inf.guardar(tmp_path / "r.txt").read_text(encoding="utf-8")

    assert "5 000 BOB" in texto and "1 449.28 PEN" in texto
    assert "3.45" in texto and "3 446–8 598 BOB" in texto


def test_marca_las_derivaciones_con_el_telefono(tmp_path):
    inf = _Informe()
    inf.agregar("ana", "me pueden llamar?", Respuesta(
        texto="¡Listo! Un asesor te contacta",
        derivar=True, motivo="llamada", telefono="+591 71234567",
    ))

    texto = inf.guardar(tmp_path / "r.txt").read_text(encoding="utf-8")

    assert "PASARÍA A UN ASESOR" in texto
    assert "llamada" in texto
    assert "+591 71234567" in texto


def test_sin_mensajes_lo_dice_en_vez_de_quedar_vacio(tmp_path):
    """Un archivo en blanco parecería un error del programa."""
    texto = _Informe().guardar(tmp_path / "r.txt").read_text(encoding="utf-8")

    assert "no había mensajes nuevos" in texto
    assert "REVISIÓN DE LA BANDEJA" in texto


def test_junta_varias_conversaciones(tmp_path):
    inf = _Informe()
    inf.agregar("ana", "hola", Respuesta(texto="¡Hola!"))
    inf.agregar("luis", "hacen swift?", Respuesta(texto="Sí, claro"))

    texto = inf.guardar(tmp_path / "r.txt").read_text(encoding="utf-8")

    assert "@ana" in texto and "@luis" in texto
