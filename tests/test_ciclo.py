"""Prueba el ciclo de producción del bot de bandeja.

Es el bucle que corre en vivo: lee la bandeja, decide a quién responder,
llama a la IA, envía y registra. Los errores aquí no son cosméticos —
responderle dos veces a alguien, o escribirle encima a un asesor que ya
está atendiendo, se ven directamente en el chat del cliente.

Se usa una bandeja y una IA de mentira, y la base de datos real (temporal).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from ragnar_agent.ai.agent import Respuesta
from ragnar_agent.cli.run_dm import _ciclo
from ragnar_agent.safety import Limitador
from ragnar_agent.store.db import Store
from ragnar_agent.tiktok.dm import Conversacion, Mensaje

SIN_ESPERAS = {"dm_por_hora": 100, "dm_por_dia": 500,
               "espera_entre_dm": [0, 0], "no_repetir_horas": 0}


# -- dobles de prueba -------------------------------------------------------


@dataclass
class BandejaFalsa:
    convs: list[Conversacion]
    entrantes: dict[str, str | None]
    abierta: str | None = None
    enviados: list[tuple[str, str]] = field(default_factory=list)
    fallar_envio: bool = False

    def conversaciones(self, limite: int = 20):
        return self.convs

    def abrir(self, conversacion: Conversacion) -> bool:
        self.abierta = conversacion.usuario
        return True

    def ultimo_entrante(self) -> str | None:
        return self.entrantes.get(self.abierta or "")

    def mensajes(self, ultimos: int = 12):
        texto = self.entrantes.get(self.abierta or "")
        return [Mensaje(texto=texto, entrante=True)] if texto else []

    def enviar(self, texto: str) -> bool:
        if self.fallar_envio:
            return False
        self.enviados.append((self.abierta or "?", texto))
        return True


@dataclass
class AgenteFalso:
    respuesta: Respuesta
    llamadas: list[str] = field(default_factory=list)

    def responder(self, mensaje: str, historial=None) -> Respuesta:
        self.llamadas.append(mensaje)
        return self.respuesta


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "prueba.sqlite3")
    yield s
    s.cerrar()


@pytest.fixture
def limitador(store):
    return Limitador(store, SIN_ESPERAS)


def conv(usuario: str, no_leido: bool = True, indice: int = 0) -> Conversacion:
    return Conversacion(indice=indice, usuario=usuario,
                        preview="...", no_leido=no_leido)


# -- a quién responde -------------------------------------------------------


def test_responde_a_las_no_leidas(store, limitador):
    bandeja = BandejaFalsa(
        convs=[conv("ana", True, 0), conv("luis", True, 1)],
        entrantes={"ana": "a cuanto esta?", "luis": "hacen swift?"},
    )
    agente = AgenteFalso(Respuesta(texto="¡Hola! Te cuento 🙌"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert [u for u, _ in bandeja.enviados] == ["ana", "luis"]


def test_ignora_las_ya_leidas(store, limitador):
    bandeja = BandejaFalsa(
        convs=[conv("ana", no_leido=False)],
        entrantes={"ana": "hola"},
    )
    agente = AgenteFalso(Respuesta(texto="hola"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert bandeja.enviados == []
    assert agente.llamadas == []


def test_no_le_escribe_encima_a_un_asesor(store, limitador):
    """Si la conversación ya está en manos de una persona, el bot no toca."""
    store.asegurar_conversacion("tiktok:ana", "ana")
    store.marcar_estado("tiktok:ana", "humano")

    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "sigo esperando"})
    agente = AgenteFalso(Respuesta(texto="no debería enviarse"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert bandeja.enviados == []
    assert agente.llamadas == []


def test_no_responde_dos_veces_el_mismo_mensaje(store, limitador):
    """El bucle corre cada 45 s: la segunda pasada no debe duplicar."""
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "a cuanto esta?"})
    agente = AgenteFalso(Respuesta(texto="Está 3.48 🙌"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)
    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert len(bandeja.enviados) == 1, "Respondió dos veces al mismo mensaje"


def test_si_el_cliente_escribe_de_nuevo_si_responde(store, limitador):
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "a cuanto esta?"})
    agente = AgenteFalso(Respuesta(texto="Está 3.48"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)
    bandeja.entrantes["ana"] = "y si son 5000?"
    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert len(bandeja.enviados) == 2


def test_sin_mensaje_entrante_no_hace_nada(store, limitador):
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": None})
    agente = AgenteFalso(Respuesta(texto="algo"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert bandeja.enviados == []


# -- modo prueba ------------------------------------------------------------


def test_en_modo_prueba_no_envia_nada(store, limitador):
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "hola"})
    agente = AgenteFalso(Respuesta(texto="respuesta"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=False)

    assert bandeja.enviados == []
    assert agente.llamadas, "En modo prueba sí debe generar la respuesta"


# -- derivación -------------------------------------------------------------


def test_la_derivacion_guarda_telefono_y_bloquea_al_bot(store, limitador):
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "me llaman?"})
    agente = AgenteFalso(Respuesta(
        texto="¡Listo! Un asesor te contacta 🙌",
        derivar=True, motivo="llamada",
        telefono="+591 71234567", horario="mañana 10am",
        resumen="Quiere coordinar por teléfono",
    ))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    pendientes = store.derivaciones_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0]["telefono"] == "+591 71234567"
    assert pendientes[0]["horario"] == "mañana 10am"

    # Y a partir de acá la conversación es del asesor.
    assert store.estado("tiktok:ana") == "humano"


def test_tras_derivar_el_bot_ya_no_responde(store, limitador):
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "me llaman?"})
    agente = AgenteFalso(Respuesta(texto="Listo", derivar=True, motivo="llamada",
                                   telefono="+591 7", horario="", resumen="x"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)
    bandeja.entrantes["ana"] = "hola? siguen ahi?"
    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert len(bandeja.enviados) == 1


# -- fallos -----------------------------------------------------------------


def test_si_falla_el_envio_no_lo_da_por_enviado(store, limitador):
    """Si no se registra el fallo, el bot creería que ya respondió."""
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "hola"},
                           fallar_envio=True)
    agente = AgenteFalso(Respuesta(texto="respuesta"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    historial = store.historial("tiktok:ana")
    assert not any(m["role"] == "assistant" for m in historial), (
        "Un envío fallido no debe quedar como respondido"
    )


def test_respuesta_vacia_no_se_envia(store, limitador):
    bandeja = BandejaFalsa(convs=[conv("ana")], entrantes={"ana": "hola"})
    agente = AgenteFalso(Respuesta(texto="   "))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert bandeja.enviados == []


def test_bandeja_vacia_no_revienta(store, limitador):
    bandeja = BandejaFalsa(convs=[], entrantes={})
    agente = AgenteFalso(Respuesta(texto="x"))

    _ciclo(bandeja, agente, store, limitador, enviar_real=True)

    assert bandeja.enviados == []


# -- límites ----------------------------------------------------------------


def test_respeta_el_limite_de_envios(store):
    limitado = Limitador(store, {**SIN_ESPERAS, "dm_por_hora": 1})
    bandeja = BandejaFalsa(
        convs=[conv("ana", True, 0), conv("luis", True, 1)],
        entrantes={"ana": "hola", "luis": "hola"},
    )
    agente = AgenteFalso(Respuesta(texto="respuesta"))

    _ciclo(bandeja, agente, store, limitado, enviar_real=True)

    assert len(bandeja.enviados) == 1, "Debió frenarse al llegar al límite"
