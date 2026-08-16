"""FASE 1 — Bot de la bandeja de mensajes de TikTok.

    python -m ragnar_agent.cli.run_dm                  # modo prueba (no envía)
    python -m ragnar_agent.cli.run_dm --enviar         # envía de verdad
    python -m ragnar_agent.cli.run_dm --diagnostico    # guarda HTML + captura
    python -m ragnar_agent.cli.run_dm --ver            # con navegador visible

Lee las conversaciones sin responder, genera la respuesta con la IA (usando
las tasas del momento) y la envía respetando los límites anti-bloqueo.
"""

from __future__ import annotations

import argparse
import sys
import time

from .. import config
from ..ai import AgenteIA
from ..config import ROOT, get_settings
from ..logging_setup import get_logger, setup
from ..safety import Limitador
from ..store import get_store
from ..tiktok.dm import Bandeja
from ..tiktok.session import SesionEnUso, SesionNoIniciada, SesionTikTok

log = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bot de DMs de TikTok — Ragnar Capital")
    p.add_argument("--enviar", action="store_true",
                   help="Envía de verdad (por defecto sólo muestra qué enviaría)")
    p.add_argument("--ver", action="store_true", help="Muestra el navegador")
    p.add_argument("--intervalo", type=int, default=45,
                   help="Segundos entre revisiones de la bandeja (default: 45)")
    p.add_argument("--una-vez", action="store_true",
                   help="Revisa la bandeja una sola vez y termina")
    p.add_argument("--diagnostico", action="store_true",
                   help="Guarda captura y HTML de la bandeja y termina")
    args = p.parse_args(argv)

    s = get_settings()
    setup(s.log_level)

    enviar_real = args.enviar and not s.dry_run
    if args.enviar and s.dry_run:
        log.warning("DRY_RUN=true en .env — no se enviará nada. "
                    "Pon DRY_RUN=false para enviar de verdad.")

    store = get_store()
    limitador = Limitador(store, config.live().get("limites", {}))
    agente = AgenteIA()

    log.info("Modo: %s", "ENVÍO REAL" if enviar_real else "PRUEBA (no envía)")
    log.info("Límites: %s", limitador.resumen())

    try:
        with SesionTikTok(headless=not args.ver) as sesion:
            page = sesion.abrir_mensajes()
            bandeja = Bandeja(page)

            if args.diagnostico:
                from ..tiktok.diagnostico import informe

                texto = informe(page)
                print("\n" + texto)
                destino = ROOT / "diagnostico_bandeja.txt"
                destino.write_text(texto, encoding="utf-8")

                sesion.guardar_captura(page, "diagnostico_bandeja")
                bandeja.volcar_diagnostico(str(ROOT / "diagnostico_bandeja.html"))

                convs = bandeja.conversaciones()
                print(f"  Conversaciones detectadas: {len(convs)}")
                for c in convs:
                    print(f"    [{'•' if c.no_leido else ' '}] @{c.usuario} — "
                          f"{c.preview[:60]}")
                print(f"\n  Informe guardado en {destino}\n")
                return 0

            while True:
                _ciclo(bandeja, agente, store, limitador, enviar_real)
                if args.una_vez:
                    return 0
                log.debug("Esperando %d s…", args.intervalo)
                time.sleep(args.intervalo)

    except SesionEnUso as exc:
        log.error("%s", exc)
        return 3
    except SesionNoIniciada as exc:
        log.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        log.info("Detenido por el usuario.")
        return 0


def _ciclo(bandeja: Bandeja, agente: AgenteIA, store, limitador, enviar_real: bool):
    conversaciones = bandeja.conversaciones()
    pendientes = [c for c in conversaciones if c.no_leido]

    if not conversaciones:
        log.warning("No se detectó ninguna conversación en la bandeja.")
        return
    log.info("%d conversaciones · %d sin leer", len(conversaciones), len(pendientes))

    for conv in pendientes:
        estado = store.asegurar_conversacion(conv.thread_id, conv.usuario)
        if estado == "humano":
            log.info("@%s está atendido por una persona; el bot no interviene.",
                     conv.usuario)
            continue

        if not bandeja.abrir(conv):
            continue

        entrante = bandeja.ultimo_entrante()
        if not entrante:
            log.debug("@%s: no hay mensaje nuevo del cliente.", conv.usuario)
            continue

        if store.ya_respondido(conv.thread_id, entrante):
            log.debug("@%s: ese mensaje ya se procesó.", conv.usuario)
            continue

        log.info("@%s dice: %r", conv.usuario, entrante[:120])
        historial = store.historial(conv.thread_id, limite=16)
        store.agregar_mensaje(conv.thread_id, "user", entrante)

        respuesta = agente.responder(entrante, historial)
        # .strip(): una respuesta de sólo espacios es verdadera en Python y
        # se enviaría como un mensaje en blanco al cliente.
        if not (respuesta.texto or "").strip():
            log.warning("@%s: la IA no devolvió texto.", conv.usuario)
            continue

        log.info("→ respuesta: %r", respuesta.texto[:200])
        for cot in respuesta.cotizaciones:
            log.info("   cotización usada: %s → %s (tasa %s)",
                     cot["entrega"], cot["recibe"], cot["tasa_aplicada"])

        if respuesta.derivar:
            store.registrar_derivacion(
                conv.thread_id, conv.usuario,
                respuesta.motivo or "peticion_explicita", respuesta.resumen or "",
                telefono=respuesta.telefono, horario=respuesta.horario,
            )
            store.marcar_estado(conv.thread_id, "humano")
            log.info(
                "   ⚑ REUNIÓN AGENDADA (%s) · tel: %s · %s",
                respuesta.motivo,
                respuesta.telefono or "no lo dio",
                respuesta.horario or "sin horario preferido",
            )

        if not enviar_real:
            log.info("   [PRUEBA] no se envió nada.")
            store.agregar_mensaje(conv.thread_id, "assistant", respuesta.texto)
            continue

        decision = limitador.evaluar(conv.usuario)
        if not decision.permitido:
            log.warning("   No se envía a @%s: %s", conv.usuario, decision.detalle)
            continue

        limitador.esperar_turno()
        if bandeja.enviar(respuesta.texto):
            limitador.registrar_envio(conv.usuario, origen="inbox")
            store.agregar_mensaje(conv.thread_id, "assistant", respuesta.texto)
            log.info("   ✓ enviado (%s)", limitador.resumen())
        else:
            log.error("   ✗ no se pudo enviar a @%s", conv.usuario)


if __name__ == "__main__":
    sys.exit(main())
