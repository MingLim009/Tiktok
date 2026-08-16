"""Herramientas que la IA puede llamar (tool use de la API de Claude).

Se definen con `strict: true` y `additionalProperties: false` para que los
argumentos que llegan siempre validen contra el esquema — así el bot no puede
inventarse una operación que no existe.
"""

from __future__ import annotations

from typing import Any

from ..logging_setup import get_logger
from ..rates import MotorDeTasas
from ..rates.engine import MontoInvalido, OperacionDesconocida, RequiereAsesor

log = get_logger(__name__)


def definiciones(motor: MotorDeTasas, motivos_derivacion: list[str]) -> list[dict]:
    operaciones = sorted(motor.operaciones_disponibles())
    # Las operaciones que sólo derivan igual se listan: el modelo debe poder
    # intentarlas para que la herramienta le responda "esto va a un asesor".
    todas = sorted(set(operaciones) | set(motor._ops))  # noqa: SLF001

    return [
        {
            "name": "cotizar_cambio",
            "description": (
                "Calcula cuánto recibe el cliente por un monto concreto, usando la "
                "tasa del momento y el tramo que corresponde. Úsala SIEMPRE que el "
                "cliente pregunte por precios, tasas o montos. Devuelve el cálculo "
                "exacto; nunca calcules tú mismo."
            ),
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": {
                    "operacion": {
                        "type": "string",
                        "enum": todas,
                        "description": "Dirección del cambio que pide el cliente.",
                    },
                    "monto": {
                        "type": "number",
                        "description": (
                            "Monto que ENTREGA el cliente, en la moneda de origen "
                            "de la operación (por ejemplo, bolivianos en bob_a_pen)."
                        ),
                    },
                },
                "required": ["operacion", "monto"],
                "additionalProperties": False,
            },
        },
        {
            "name": "derivar_a_asesor",
            "description": (
                "Reserva la videollamada por Google Meet y pasa el caso a un "
                "asesor. Úsala sólo cuando el cliente pida una llamada, una "
                "reunión, o hablar con una persona.\n\n"
                "IMPORTANTE: antes de usarla, pídele al cliente su número de "
                "teléfono con código de país y qué día y hora le queda mejor. "
                "Sólo llama a esta herramienta cuando ya tengas esos datos (o "
                "cuando el cliente se niegue a darlos, en cuyo caso manda "
                "cadena vacía en ese campo)."
            ),
            "strict": True,
            "input_schema": {
                "type": "object",
                "properties": {
                    "motivo": {
                        "type": "string",
                        "enum": motivos_derivacion,
                        "description": "Por qué se deriva.",
                    },
                    "telefono": {
                        "type": "string",
                        "description": (
                            "Teléfono del cliente tal cual lo escribió, con "
                            "código de país si lo dio. Cadena vacía si no lo "
                            "quiso dar."
                        ),
                    },
                    "horario": {
                        "type": "string",
                        "description": (
                            "Día y hora que prefiere para la reunión, tal cual "
                            "lo dijo. Cadena vacía si no lo indicó."
                        ),
                    },
                    "resumen": {
                        "type": "string",
                        "description": (
                            "Resumen de 1-2 frases de lo que necesita el cliente, "
                            "para que el asesor no tenga que leer todo el chat."
                        ),
                    },
                },
                "required": ["motivo", "telefono", "horario", "resumen"],
                "additionalProperties": False,
            },
        },
    ]


def ejecutar(
    nombre: str, argumentos: dict[str, Any], motor: MotorDeTasas
) -> tuple[str, bool, dict | None]:
    """Ejecuta una herramienta.

    Devuelve (contenido_para_la_ia, es_error, metadatos).
    """
    if nombre == "cotizar_cambio":
        return _cotizar(argumentos, motor)

    if nombre == "derivar_a_asesor":
        motivo = argumentos.get("motivo", "peticion_explicita")
        resumen = argumentos.get("resumen", "")
        telefono = (argumentos.get("telefono") or "").strip()
        horario = (argumentos.get("horario") or "").strip()

        log.info(
            "Derivación (%s) · tel: %s · horario: %s · %s",
            motivo, telefono or "no dio", horario or "sin preferencia", resumen,
        )
        aviso = (
            "Listo: la reunión quedó registrada y un asesor va a mandar la "
            "invitación de Google Meet. Confírmaselo con calidez y no sigas "
            "cotizando."
        )
        if not telefono:
            aviso += (
                " Nota: no quedó registrado su teléfono; si se da la ocasión "
                "de forma natural, vuelve a ofrecérselo, pero sin insistir."
            )
        return (
            aviso,
            False,
            {
                "derivar": True,
                "motivo": motivo,
                "resumen": resumen,
                "telefono": telefono,
                "horario": horario,
            },
        )

    return f"La herramienta '{nombre}' no existe.", True, None


def _cotizar(args: dict, motor: MotorDeTasas) -> tuple[str, bool, dict | None]:
    operacion = args.get("operacion", "")
    monto = args.get("monto", 0)

    try:
        cot = motor.cotizar(operacion, float(monto))
    except RequiereAsesor as exc:
        return (
            f"Esta operación sí la maneja Ragnar Capital, pero no tiene tasa "
            f"automática: {exc}. Confírmale al cliente que sí la hacemos y usa "
            f"la herramienta derivar_a_asesor con motivo '{exc.motivo}'.",
            False,
            None,
        )
    except (OperacionDesconocida, MontoInvalido) as exc:
        return str(exc), True, None
    except Exception as exc:  # noqa: BLE001
        log.exception("Error inesperado al cotizar")
        return (
            f"No se pudo obtener la tasa ahora mismo ({exc}). Dile al cliente "
            f"que hay un problema temporal para consultar la tasa y ofrécele "
            f"que un asesor se la confirme.",
            True,
            None,
        )

    log.info("Cotización: %s", cot.texto())
    partes = [
        f"Entrega: {cot.monto_entrega} {cot.entrega_moneda}",
        f"Recibe: {cot.monto_recibe} {cot.recibe_moneda}",
        f"Tasa aplicada: {cot.tasa_aplicada:g}",
        f"Tramo: {cot.tramo}",
        f"Fecha de la tasa: {cot.fecha_tasa or 'hoy'}",
    ]
    if cot.revisar:
        partes.append(
            "IMPORTANTE: esta tasa es referencial. Dile al cliente que un asesor "
            "se la confirma antes de operar."
        )
    for adv in cot.advertencias:
        partes.append(f"Aviso interno: {adv}")

    return "\n".join(partes), False, {"cotizacion": cot.to_dict()}
