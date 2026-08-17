"""Pruebas del bucle de conversación, sin llamar a la API de Anthropic.

Se reemplaza el cliente por uno falso que devuelve respuestas preparadas. Así
se comprueba la parte más delicada del sistema —que la IA pida la cotización
por herramienta y que el resultado se le devuelva bien— sin gastar tokens ni
depender de la red.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ragnar_agent import config
from ragnar_agent.ai import agent as agente_mod
from ragnar_agent.rates.base import ProveedorDeTasas, TasasVigentes
from ragnar_agent.rates.engine import MotorDeTasas
from ragnar_agent.rates.tramos import TablaTramos, Tramo

# Tramos reales de la hoja "TASAS FINALES" (15/08/2026), recortados a lo que
# usan estas pruebas.
TABLAS = {
    "BOB/PEN": ("BOB", [(0, 583, 3.49), (584, 3445, 3.47),
                        (3446, 8598, 3.45), (8599, None, 3.43)]),
    "PEN/BOB": ("PEN", [(0, 5069, 3.33), (5070, None, 3.36)]),
    "BOB/USD": ("BOB", [(0, 1155, 11.98), (1156, None, 11.59)]),
    "BOB/USD INTERNACIONAL": ("BOB", [(0, 11460, 12.45), (11461, None, 11.59)]),
}


class ProveedorFalso(ProveedorDeTasas):
    nombre = "test"

    def obtener(self) -> TasasVigentes:
        tablas = {
            nombre: TablaTramos(
                nombre=nombre, unidad=unidad,
                tramos=[Tramo(desde=d, hasta=h, tasa=t) for d, h, t in filas],
            )
            for nombre, (unidad, filas) in TABLAS.items()
        }
        return TasasVigentes(
            valores={}, fecha="8/15/2026", fuente="test", tablas=tablas
        )


def bloque_texto(texto):
    return SimpleNamespace(type="text", text=texto)


def bloque_herramienta(id_, nombre, entrada):
    return SimpleNamespace(type="tool_use", id=id_, name=nombre, input=entrada)


def respuesta(stop_reason, content):
    return SimpleNamespace(stop_reason=stop_reason, content=content)


class ClienteFalso:
    """Devuelve, en orden, las respuestas que se le carguen."""

    def __init__(self, respuestas):
        self._respuestas = list(respuestas)
        self.peticiones = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.peticiones.append(kwargs)
        if not self._respuestas:
            raise AssertionError("El agente pidió más respuestas de las previstas")
        return self._respuestas.pop(0)


@pytest.fixture
def construir(monkeypatch):
    """Devuelve una función que arma un AgenteIA con un cliente falso."""

    def _construir(respuestas):
        monkeypatch.setattr(
            agente_mod,
            "get_settings",
            lambda: SimpleNamespace(
                anthropic_model="claude-opus-5",
                require_api_key=lambda: "sk-ant-de-prueba",
            ),
        )
        cliente = ClienteFalso(respuestas)
        monkeypatch.setattr(
            agente_mod.anthropic, "Anthropic", lambda **kw: cliente
        )

        motor = MotorDeTasas(config.tasas())
        motor._proveedor = ProveedorFalso()
        motor._respaldo = None

        return agente_mod.AgenteIA(motor=motor), cliente

    return _construir


# ---------------------------------------------------------------------------


def test_respuesta_simple(construir):
    agente, cliente = construir([
        respuesta("end_turn", [bloque_texto("¡Hola! Atendemos de 8am a 5pm 🙌")]),
    ])
    r = agente.responder("hola, hasta qué hora atienden?")

    assert "8am" in r.texto
    assert r.derivar is False
    assert r.cotizaciones == []
    assert len(cliente.peticiones) == 1


def test_cotiza_llamando_a_la_herramienta(construir):
    """El caso central: la IA pide la tasa y el motor le devuelve el cálculo."""
    agente, cliente = construir([
        respuesta("tool_use", [
            bloque_herramienta("t1", "cotizar_cambio",
                               {"operacion": "bob_a_pen", "monto": 5000}),
        ]),
        respuesta("end_turn", [bloque_texto("Por 5000 Bs recibes 1457.73 soles 😊")]),
    ])
    r = agente.responder("quiero cambiar 5000 bolivianos a soles")

    assert r.derivar is False
    assert len(r.cotizaciones) == 1
    cot = r.cotizaciones[0]
    assert cot["entrega"] == "5 000 BOB"
    assert cot["recibe"] == "1 449.28 PEN"
    assert cot["tasa_aplicada"] == 3.45  # tramo 3446–8598 Bs

    # El resultado de la herramienta tiene que haber vuelto a la IA.
    segunda = cliente.peticiones[1]["messages"]
    resultado = segunda[-1]["content"][0]
    assert resultado["type"] == "tool_result"
    assert resultado["tool_use_id"] == "t1"
    assert "1449.28" in resultado["content"]


def test_derivacion_captura_telefono_y_horario(construir):
    """Lo que el cliente pidió: reservar el Meet y quedarse con el teléfono."""
    agente, _ = construir([
        respuesta("tool_use", [
            bloque_herramienta("t1", "derivar_a_asesor", {
                "motivo": "reunion",
                "telefono": "+591 71234567",
                "horario": "mañana a las 10am",
                "resumen": "Quiere un Meet para cambiar 50 mil Bs",
            }),
        ]),
        respuesta("end_turn", [bloque_texto("¡Listo! Un asesor te manda la invitación 🙌")]),
    ])
    r = agente.responder("mi numero es +591 71234567, mañana 10am me va bien")

    assert r.derivar is True
    assert r.motivo == "reunion"
    assert r.telefono == "+591 71234567"
    assert r.horario == "mañana a las 10am"


def test_derivacion_sin_telefono_no_bloquea(construir):
    """Si el cliente no lo quiere dar, se deriva igual — no se le insiste."""
    agente, cliente = construir([
        respuesta("tool_use", [
            bloque_herramienta("t1", "derivar_a_asesor", {
                "motivo": "llamada", "telefono": "", "horario": "",
                "resumen": "Prefiere no dejar su número",
            }),
        ]),
        respuesta("end_turn", [bloque_texto("Sin problema, un asesor te escribe por aquí")]),
    ])
    r = agente.responder("prefiero no dar mi numero")

    assert r.derivar is True
    assert r.telefono == ""
    # A la IA se le avisa, para que no lo dé por registrado.
    resultado = cliente.peticiones[1]["messages"][-1]["content"][0]
    assert "no quedó registrado su teléfono" in resultado["content"]


def test_la_herramienta_exige_los_campos_de_contacto(construir):
    agente, cliente = construir([respuesta("end_turn", [bloque_texto("hola")])])
    agente.responder("hola")

    derivar = next(
        t for t in cliente.peticiones[0]["tools"] if t["name"] == "derivar_a_asesor"
    )
    assert set(derivar["input_schema"]["required"]) == {
        "motivo", "telefono", "horario", "resumen"
    }


def test_monto_invalido_vuelve_como_error(construir):
    """Un monto invalido se devuelve como is_error para que la IA lo explique."""
    agente, cliente = construir([
        respuesta("tool_use", [
            bloque_herramienta("t1", "cotizar_cambio",
                               {"operacion": "bob_a_pen", "monto": 0}),
        ]),
        respuesta("end_turn", [bloque_texto("¿Cuánto querías cambiar? 😊")]),
    ])
    r = agente.responder("quiero cambiar bolivianos")

    assert r.cotizaciones == []
    resultado = cliente.peticiones[1]["messages"][-1]["content"][0]
    assert resultado.get("is_error") is True


def test_los_montos_chicos_ya_no_dan_error(construir):
    """El cliente reporto que 36 soles disparaba un aviso de minimo."""
    agente, cliente = construir([
        respuesta("tool_use", [
            bloque_herramienta("t1", "cotizar_cambio",
                               {"operacion": "pen_a_bob", "monto": 36}),
        ]),
        respuesta("end_turn", [bloque_texto("Son 119.88 bolivianos 🙌")]),
    ])
    r = agente.responder("36 soles a bolivianos")

    assert len(r.cotizaciones) == 1
    resultado = cliente.peticiones[1]["messages"][-1]["content"][0]
    assert resultado.get("is_error") is not True
    assert "mínimo" not in resultado["content"].lower()


def test_swift_ahora_cotiza_sin_derivar(construir):
    """Con la tabla BOB/USD INTERNACIONAL, SWIFT ya no necesita a un asesor."""
    agente, cliente = construir([
        respuesta("tool_use", [
            bloque_herramienta("t1", "cotizar_cambio",
                               {"operacion": "bob_a_usd_swift", "monto": 20000}),
        ]),
        respuesta("end_turn", [bloque_texto("Por 20000 Bs te llegan 1725.6 dólares")]),
    ])
    r = agente.responder("quiero mandar dolares por swift")

    assert r.derivar is False
    assert len(r.cotizaciones) == 1
    assert r.cotizaciones[0]["tasa_aplicada"] == 11.59

    resultado = cliente.peticiones[1]["messages"][-1]["content"][0]
    assert resultado.get("is_error") is not True
    assert "1725.6" in resultado["content"]


def test_rechazo_de_la_api_deriva_a_humano(construir):
    agente, _ = construir([respuesta("refusal", [])])
    r = agente.responder("algo que la API rechaza")

    assert r.rechazada is True
    assert r.derivar is True
    assert r.texto  # se le responde algo al cliente, no silencio


def test_peticion_bien_formada(construir):
    """La llamada no debe llevar parámetros que Claude Opus 5 rechaza."""
    agente, cliente = construir([
        respuesta("end_turn", [bloque_texto("hola")]),
    ])
    agente.responder("hola")
    p = cliente.peticiones[0]

    assert p["model"] == "claude-opus-5"
    # temperature / top_p / top_k y budget_tokens devuelven 400 en Opus 5
    for prohibido in ("temperature", "top_p", "top_k"):
        assert prohibido not in p
    assert p["output_config"] == {"effort": "low"}
    assert p["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert {t["name"] for t in p["tools"]} == {"cotizar_cambio", "derivar_a_asesor"}
    assert all(t["strict"] for t in p["tools"])


def test_historial_se_respeta(construir):
    agente, cliente = construir([
        respuesta("end_turn", [bloque_texto("Claro")]),
    ])
    historial = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "¡Hola! ¿En qué te ayudo?"},
    ]
    agente.responder("y a cuánto está?", historial)

    mensajes = cliente.peticiones[0]["messages"]
    assert len(mensajes) == 3
    assert mensajes[0]["content"] == "hola"
    assert "a cuánto está?" in mensajes[-1]["content"]


def test_contexto_de_horario_va_en_el_turno_no_en_el_sistema(construir):
    """Meter la hora en el prompt de sistema rompería el cacheo."""
    agente, cliente = construir([
        respuesta("end_turn", [bloque_texto("hola")]),
    ])
    agente.responder("hola")
    p = cliente.peticiones[0]

    assert "Contexto interno" in p["messages"][-1]["content"]
    assert "Contexto interno" not in p["system"][0]["text"]
