# Instalación

Guía para dejar el agente funcionando desde cero. Toma unos 15 minutos.

---

## 1. Requisitos

- **Python 3.10 o superior** — comprobar con `python --version`
  Descarga: <https://www.python.org/downloads/> (marcar *"Add Python to PATH"*)
- Conexión a internet
- La cuenta de TikTok de Ragnar Capital (usuario y contraseña, a mano)
- Una API key de Anthropic (Claude) — ver el paso 4

---

## 2. Instalar el proyecto

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
# Entorno aislado (recomendado: evita mezclar con otros programas)
python -m venv .venv

# Activarlo
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Dependencias
pip install -r requirements.txt

# Navegador que usa el bot para la bandeja de TikTok
playwright install chromium
```

> Si `playwright install chromium` falla, revisa que el antivirus o el firewall
> no esté bloqueando la descarga. Es un Chromium normal, de unos 150 MB.

---

## 3. Crear el archivo `.env`

Copia la plantilla:

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux
```

Ábrelo con el Bloc de notas y completa `ANTHROPIC_API_KEY` (paso 4).

**Deja `DRY_RUN=true` por ahora.** Con eso el bot muestra en pantalla lo que
respondería, pero no envía nada. Es la forma segura de probar.

---

## 4. API key de Claude

1. Entra a <https://console.anthropic.com>
2. *Settings* → *API keys* → *Create key*
3. Copia la key (empieza con `sk-ant-`) y pégala en `.env`:

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

> ⚠️ La API key es como una tarjeta de crédito: quien la tenga puede gastar
> con tu cuenta. Nunca la pegues en un chat, un correo ni una captura de
> pantalla. Si se expone, bórrala desde la consola y crea una nueva.

---

## 5. Probar sin TikTok

Antes de conectar la cuenta, comprueba que las tasas y la IA funcionan.

**Tasas** (no necesita API key):

```bash
python -m ragnar_agent.cli.demo --tasas
```

Debe mostrar las tasas del día leídas del Google Sheet y ejemplos de
cotización. Si esto funciona, el motor de tasas está bien conectado.

**Conversación** (necesita API key):

```bash
python -m ragnar_agent.cli.demo
```

Se abre un chat en la terminal. Escribe como si fueras un cliente:

```
Cliente > hola, a cuánto está el cambio?
Cliente > quiero cambiar 5000 bolivianos a soles
Cliente > me puedes llamar?
```

En la última debe aparecer `[⚑ DERIVADO A UN ASESOR]`.

---

## 6. Conectar la cuenta de TikTok

```bash
python -m ragnar_agent.cli.login
```

Se abre una ventana de navegador:

1. Inicia sesión con la cuenta de Ragnar Capital
2. Cuando pida el código de verificación, **elige correo**
3. Espera a ver la bandeja de mensajes
4. Vuelve a la terminal — debe decir `✓ Sesión iniciada y guardada`

Esto se hace **una sola vez**. La sesión queda guardada en `.session/tiktok/`.

> La contraseña no se guarda en ningún archivo del proyecto: se escribe
> directamente en la ventana de TikTok, igual que en cualquier navegador.

---

## 7. Probar el bot de la bandeja (sin enviar)

```bash
python -m ragnar_agent.cli.run_dm --una-vez
```

Debe listar las conversaciones y mostrar qué respondería a cada mensaje sin
leer, sin enviar nada.

**Si dice que no encontró conversaciones**, TikTok cambió su interfaz. Ejecuta:

```bash
python -m ragnar_agent.cli.run_dm --diagnostico
```

Eso guarda `diagnostico_bandeja.html` y una captura de pantalla. Con esos dos
archivos se ajustan los selectores en `src/ragnar_agent/tiktok/dm.py`
(están todos juntos al inicio del archivo) y vuelve a funcionar.

---

## 8. Activar el envío real

Cuando las respuestas de prueba se vean bien:

1. En `.env`, cambia `DRY_RUN=true` por `DRY_RUN=false`
2. Ejecuta:

```bash
python -m ragnar_agent.cli.run_dm --enviar
```

El bot queda revisando la bandeja cada 45 segundos. Se detiene con `Ctrl + C`.

Empieza con una franja corta (una o dos horas acompañadas) antes de dejarlo
todo el día. Ver [SEGURIDAD.md](SEGURIDAD.md).

---

## 9. Fase 2 — Live

Primero prueba las palabras clave sin necesidad de estar en vivo:

```bash
python -m ragnar_agent.cli.run_live --probar "yo"
python -m ragnar_agent.cli.run_live --probar "cuánto está la tasa?"
```

Luego, con un live activo:

```bash
python -m ragnar_agent.cli.run_live              # prueba, no envía
python -m ragnar_agent.cli.run_live --enviar     # envía de verdad
```

---

## Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `Falta ANTHROPIC_API_KEY` | No creaste `.env` o la key quedó vacía |
| `playwright: command not found` | Falta activar el entorno virtual (paso 2) |
| `TikTok no reconoce la sesión guardada` | Caducó. Vuelve a correr `cli.login` |
| `No se encontró la lista de conversaciones` | TikTok cambió su HTML → paso 7 |
| Las tasas salen con fecha vieja | Nadie actualizó el Google Sheet ese día |
| `Tasa de respaldo: no se pudo leer la fuente` | Sin internet, o el Sheet dejó de ser público |
