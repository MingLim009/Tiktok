"""FASE 2 — Captación de leads en TikTok Live (keyword → DM).

    python -m ragnar_agent.cli.run_live               # modo prueba (no envía)
    python -m ragnar_agent.cli.run_live --enviar      # envía DMs de verdad
    python -m ragnar_agent.cli.run_live --probar "yo" # prueba las keywords sin live

Escucha los comentarios del live, detecta las palabras clave de
config/live.yaml y envía el DM correspondiente respetando los límites.
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading

from .. import config
from ..config import get_settings
from ..logging_setup import get_logger, setup
from ..safety import Limitador
from ..store import get_store
from ..tiktok.dm import abrir_chat_con
from ..tiktok.live import Coincidencia, MonitorLive, cargar_reglas, evaluar
from ..tiktok.session import SesionEnUso, SesionNoIniciada, SesionTikTok

log = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bot de Live de TikTok — Ragnar Capital")
    p.add_argument("--enviar", action="store_true", help="Envía los DMs de verdad")
    p.add_argument("--ver", action="store_true", help="Muestra el navegador")
    p.add_argument("--cuenta", default=None, help="Cuenta a monitorear (sin @)")
    p.add_argument("--probar", metavar="COMENTARIO",
                   help="Evalúa un comentario contra las keywords y termina")
    args = p.parse_args(argv)

    s = get_settings()
    setup(s.log_level)

    cfg = config.live()
    reglas = cargar_reglas(cfg)
    if not reglas:
        log.error("No hay reglas activas en config/live.yaml")
        return 1

    # -- modo prueba de keywords (no necesita live ni sesión) -------------
    if args.probar is not None:
        regla = evaluar(args.probar, reglas)
        if regla is None:
            print(f"\n  {args.probar!r} → no coincide con ninguna keyword.\n")
        else:
            print(f"\n  {args.probar!r} → regla '{regla.id}'")
            print(f"  DM que se enviaría:\n    {regla.mensaje_para('María')}\n")
        return 0

    cuenta = args.cuenta or cfg.get("cuenta", "")
    if not cuenta:
        log.error("Falta la cuenta a monitorear (config/live.yaml → cuenta).")
        return 1

    enviar_real = args.enviar and not s.dry_run
    if args.enviar and s.dry_run:
        log.warning("DRY_RUN=true en .env — no se enviará nada.")

    store = get_store()
    limitador = Limitador(store, cfg.get("limites", {}))

    log.info("Modo: %s", "ENVÍO REAL" if enviar_real else "PRUEBA (no envía)")
    log.info("Reglas activas: %s", ", ".join(r.id for r in reglas))
    log.info("Límites: %s", limitador.resumen())

    # El monitor del live corre en su propio hilo (asyncio) y deja las
    # coincidencias en una cola; el navegador vive en el hilo principal,
    # porque Playwright en modo síncrono no se puede compartir entre hilos.
    pendientes: queue.Queue[Coincidencia] = queue.Queue()
    detener = threading.Event()

    def al_detectar(c: Coincidencia) -> None:
        pendientes.put(c)

    monitor = MonitorLive(cuenta, reglas, al_detectar)

    hilo = threading.Thread(target=_correr_monitor, args=(monitor, detener), daemon=True)
    hilo.start()

    try:
        if not enviar_real:
            _bucle_prueba(pendientes, limitador, detener)
            return 0

        entregar = bool((cfg.get("seguimiento") or {}).get("entregar_al_bot_de_dms", True))
        log.info(
            "Si el lead responde, %s",
            "el bot de bandeja continúa la conversación."
            if entregar else "queda marcado para que lo atienda una persona.",
        )
        with SesionTikTok(headless=not args.ver) as sesion:
            page = sesion.abrir_mensajes()
            _bucle_envio(page, pendientes, limitador, store, detener, entregar)
        return 0

    except SesionEnUso as exc:
        log.error("%s", exc)
        return 3
    except SesionNoIniciada as exc:
        log.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        log.info("Detenido por el usuario.")
        return 0
    finally:
        detener.set()


def _correr_monitor(monitor: MonitorLive, detener: threading.Event) -> None:
    try:
        monitor.ejecutar()
    except Exception:  # noqa: BLE001
        log.exception("El monitor del live se detuvo.")
    finally:
        detener.set()


def _bucle_prueba(pendientes, limitador, detener) -> None:
    log.info("Modo prueba: se mostrará el DM que se enviaría, sin enviarlo.")
    while not detener.is_set():
        try:
            c = pendientes.get(timeout=1.0)
        except queue.Empty:
            continue
        decision = limitador.evaluar(c.usuario)
        estado = "OK" if decision.permitido else f"BLOQUEADO ({decision.detalle})"
        log.info("[PRUEBA] @%s (%s) → %s", c.usuario, estado,
                 c.regla.mensaje_para(c.nombre))


def _bucle_envio(page, pendientes, limitador, store, detener, entregar=True) -> None:
    while not detener.is_set():
        try:
            c = pendientes.get(timeout=1.0)
        except queue.Empty:
            continue

        decision = limitador.evaluar(c.usuario)
        if not decision.permitido:
            log.info("No se escribe a @%s: %s", c.usuario, decision.detalle)
            continue

        mensaje = c.regla.mensaje_para(c.nombre)
        limitador.esperar_turno()

        bandeja = abrir_chat_con(page, c.usuario)
        if bandeja is None:
            continue

        if bandeja.enviar(mensaje):
            limitador.registrar_envio(c.usuario, origen="live", regla_id=c.regla.id)
            thread_id = f"tiktok:{c.usuario}"
            store.asegurar_conversacion(thread_id, c.usuario)
            store.agregar_mensaje(thread_id, "assistant", mensaje)
            if not entregar:
                # config/live.yaml → seguimiento.entregar_al_bot_de_dms: false
                # Marcarla como 'humano' hace que el bot de bandeja la ignore.
                store.marcar_estado(thread_id, "humano")
            log.info("✓ DM enviado a @%s (%s)", c.usuario, limitador.resumen())
        else:
            log.error("✗ no se pudo enviar el DM a @%s", c.usuario)


if __name__ == "__main__":
    sys.exit(main())
