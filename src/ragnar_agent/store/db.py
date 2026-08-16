"""Persistencia en SQLite.

Guarda el historial de cada conversación (para que el bot no repita cosas ni
pierda el hilo), las derivaciones a un asesor, y el registro de DMs enviados
(que es lo que permite respetar los límites anti-bloqueo entre reinicios).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import get_settings

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS conversaciones (
    thread_id     TEXT PRIMARY KEY,
    usuario       TEXT NOT NULL,
    estado        TEXT NOT NULL DEFAULT 'bot',   -- 'bot' | 'humano'
    creado_en     TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mensajes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id  TEXT NOT NULL,
    rol        TEXT NOT NULL,                    -- 'user' | 'assistant'
    contenido  TEXT NOT NULL,
    creado_en  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mensajes_thread ON mensajes(thread_id, id);

CREATE TABLE IF NOT EXISTS derivaciones (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    usuario   TEXT NOT NULL,
    motivo    TEXT NOT NULL,
    resumen   TEXT,
    telefono  TEXT,
    horario   TEXT,
    creado_en TEXT NOT NULL,
    atendido  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dm_enviados (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario   TEXT NOT NULL,
    origen    TEXT NOT NULL,                     -- 'live' | 'inbox'
    regla_id  TEXT,
    creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dm_usuario ON dm_enviados(usuario, creado_en);
CREATE INDEX IF NOT EXISTS idx_dm_fecha ON dm_enviados(creado_en);
"""


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_ESQUEMA)
        self._migrar()
        self._conn.commit()

    def _migrar(self) -> None:
        """Agrega columnas nuevas a bases creadas por versiones anteriores."""
        existentes = {
            f["name"]
            for f in self._conn.execute("PRAGMA table_info(derivaciones)").fetchall()
        }
        for columna in ("telefono", "horario"):
            if columna not in existentes:
                self._conn.execute(
                    f"ALTER TABLE derivaciones ADD COLUMN {columna} TEXT"
                )

    # -- conversaciones ---------------------------------------------------
    def asegurar_conversacion(self, thread_id: str, usuario: str) -> str:
        """Crea la conversación si no existe. Devuelve su estado actual."""
        with self._lock:
            fila = self._conn.execute(
                "SELECT estado FROM conversaciones WHERE thread_id = ?", (thread_id,)
            ).fetchone()
            if fila:
                return fila["estado"]
            ahora = _ahora()
            self._conn.execute(
                "INSERT INTO conversaciones (thread_id, usuario, estado, creado_en, actualizado_en)"
                " VALUES (?, ?, 'bot', ?, ?)",
                (thread_id, usuario, ahora, ahora),
            )
            self._conn.commit()
            return "bot"

    def estado(self, thread_id: str) -> str:
        with self._lock:
            fila = self._conn.execute(
                "SELECT estado FROM conversaciones WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return fila["estado"] if fila else "bot"

    def marcar_estado(self, thread_id: str, estado: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE conversaciones SET estado = ?, actualizado_en = ? WHERE thread_id = ?",
                (estado, _ahora(), thread_id),
            )
            self._conn.commit()

    # -- mensajes ---------------------------------------------------------
    def agregar_mensaje(self, thread_id: str, rol: str, contenido: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO mensajes (thread_id, rol, contenido, creado_en) VALUES (?, ?, ?, ?)",
                (thread_id, rol, contenido, _ahora()),
            )
            self._conn.execute(
                "UPDATE conversaciones SET actualizado_en = ? WHERE thread_id = ?",
                (_ahora(), thread_id),
            )
            self._conn.commit()

    def historial(self, thread_id: str, limite: int = 20) -> list[dict[str, str]]:
        """Últimos mensajes en formato de la API de Claude, en orden cronológico."""
        with self._lock:
            filas = self._conn.execute(
                "SELECT rol, contenido FROM mensajes WHERE thread_id = ?"
                " ORDER BY id DESC LIMIT ?",
                (thread_id, limite),
            ).fetchall()
        return [{"role": f["rol"], "content": f["contenido"]} for f in reversed(filas)]

    def ya_respondido(self, thread_id: str, contenido: str) -> bool:
        """¿Este mensaje del cliente ya se procesó antes?

        Se compara contra el último mensaje DEL CLIENTE, no contra el último
        de la conversación. Mirar el último a secas no sirve: después de
        responder, el último es el del bot, así que el guardia nunca saltaba
        y el mismo mensaje se contestaba en cada pasada del bucle.
        """
        with self._lock:
            fila = self._conn.execute(
                "SELECT contenido FROM mensajes WHERE thread_id = ? AND rol = 'user'"
                " ORDER BY id DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
        return bool(fila and fila["contenido"] == contenido)

    # -- derivaciones -----------------------------------------------------
    def registrar_derivacion(
        self, thread_id: str, usuario: str, motivo: str, resumen: str,
        telefono: str = "", horario: str = "",
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO derivaciones"
                " (thread_id, usuario, motivo, resumen, telefono, horario, creado_en)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (thread_id, usuario, motivo, resumen, telefono, horario, _ahora()),
            )
            self._conn.commit()

    def derivaciones_pendientes(self) -> list[dict[str, Any]]:
        with self._lock:
            filas = self._conn.execute(
                "SELECT * FROM derivaciones WHERE atendido = 0 ORDER BY id DESC"
            ).fetchall()
        return [dict(f) for f in filas]

    # -- DMs enviados (límites anti-bloqueo) ------------------------------
    def registrar_dm(self, usuario: str, origen: str, regla_id: str | None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO dm_enviados (usuario, origen, regla_id, creado_en)"
                " VALUES (?, ?, ?, ?)",
                (usuario, origen, regla_id, _ahora()),
            )
            self._conn.commit()

    def dms_desde(self, desde: datetime) -> int:
        with self._lock:
            fila = self._conn.execute(
                "SELECT COUNT(*) AS n FROM dm_enviados WHERE creado_en >= ?",
                (desde.isoformat(timespec="seconds"),),
            ).fetchone()
        return int(fila["n"])

    def escrito_recientemente(self, usuario: str, horas: int) -> bool:
        limite = datetime.now() - timedelta(hours=horas)
        with self._lock:
            fila = self._conn.execute(
                "SELECT 1 FROM dm_enviados WHERE usuario = ? AND creado_en >= ? LIMIT 1",
                (usuario, limite.isoformat(timespec="seconds")),
            ).fetchone()
        return fila is not None

    def cerrar(self) -> None:
        with self._lock:
            self._conn.close()


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store(get_settings().db_path)
