# Riesgos, límites y buenas prácticas

Este documento dice las cosas como son, para que las decisiones se tomen con
la información completa.

---

## 1. Riesgo de restricción de la cuenta de TikTok

**TikTok no ofrece una API oficial de mensajes directos, y sus términos de
servicio no permiten el acceso automatizado a la plataforma.** Todo lo que
hace la Fase 1 (leer y responder la bandeja) funciona controlando un navegador
real, y el envío masivo de DMs es exactamente el patrón que TikTok busca
detectar.

Consecuencias posibles, de menor a mayor:

1. Los mensajes dejan de entregarse silenciosamente (shadow-limit)
2. Bloqueo temporal del envío de DMs (horas o días)
3. Suspensión o cierre de la cuenta

**Este riesgo no se puede eliminar. Sólo se puede reducir.** No existe una
configuración "segura" — quien afirme lo contrario está vendiendo humo.

### Lo que hace el sistema para reducirlo

| Medida | Dónde se configura |
|---|---|
| Tope de 25 DMs por hora y 150 por día | `config/live.yaml → limites` |
| Espera aleatoria de 35–95 s entre envíos | `espera_entre_dm` |
| Nunca se escribe dos veces al mismo usuario en 72 h | `no_repetir_horas` |
| Varias plantillas distintas, elegidas al azar | `reglas → plantillas` |
| El texto se escribe carácter por carácter, no se pega de golpe | código |
| Navegador real, con user-agent y perfil persistente | código |
| Los contadores sobreviven a los reinicios (SQLite) | automático |

### Lo que conviene hacer además

- **Empieza despacio.** La primera semana, 2–3 horas al día acompañadas.
  Sube el volumen sólo si no aparece ninguna señal rara.
- **No lo dejes 24/7.** Una cuenta que responde a las 4 de la mañana todos los
  días no parece una persona.
- **Revisa los logs a diario** la primera semana.
- **Si aparece un CAPTCHA o los envíos empiezan a fallar, para.** Espera 24–48
  horas antes de volver, con límites más bajos.
- **Considera una cuenta secundaria** para las pruebas iniciales, en vez de
  arriesgar la cuenta principal del negocio.

### Decisión que corresponde al cliente

Esto es una decisión de negocio, no técnica: hay que sopesar el valor de
automatizar la atención contra la posibilidad de perder la cuenta y sus
seguidores. El sistema está construido para minimizar el riesgo, pero la
elección de usarlo es de Ragnar Capital.

---

## 2. Credenciales

### API key de Anthropic

La API key da acceso a gastar con la cuenta de Anthropic. Reglas:

- Vive **sólo** en el archivo `.env`, que está en `.gitignore`
- Nunca se escribe dentro del código
- Nunca se manda por chat, correo ni captura de pantalla
- Los logs la censuran automáticamente si aparece

> ⚠️ **Una API key compartida por chat debe considerarse comprometida.** Los
> chats de las plataformas de freelance quedan almacenados, son accesibles al
> soporte de la plataforma y no son un canal seguro. Si una key se envió por
> ahí: entra a <https://console.anthropic.com> → *Settings* → *API keys*,
> **elimina esa key**, crea una nueva y ponla en `.env`. Conviene además
> configurar un límite de gasto mensual en la consola.

### Contraseña de TikTok

El sistema **no guarda ni necesita la contraseña**. El login se hace una vez a
mano en una ventana de navegador (`cli.login`) y a partir de ahí sólo se
conserva la sesión (cookies).

> ⚠️ Si la contraseña de TikTok se envió por chat, hay que **cambiarla** y
> activar la verificación en dos pasos. Después de cambiarla, volver a correr
> `python -m ragnar_agent.cli.login` una vez.

### La carpeta `.session/`

Esa carpeta contiene la sesión activa de TikTok. **Quien la copie entra a la
cuenta sin necesitar la contraseña ni el código de verificación.** Tratarla
igual que una contraseña: no subirla a ningún repositorio, no mandarla, no
dejarla en una carpeta compartida. Ya está en `.gitignore`.

---

## 3. Costo de la IA

Cada respuesta consume tokens de la API de Anthropic. Referencias:

- El prompt del negocio se cachea, así que a partir del segundo mensaje cada
  respuesta cuesta una fracción
- Una conversación típica de 4–5 mensajes está en el orden de centavos de dólar
- El modelo se configura en `.env` con `ANTHROPIC_MODEL`

Si el volumen crece y el costo importa, cambiar `ANTHROPIC_MODEL` a
`claude-sonnet-5` reduce el precio por token sin tocar el código. Conviene
además fijar un **límite de gasto mensual** en la consola de Anthropic:
protege ante un bucle inesperado o un uso anómalo.

---

## 4. Qué datos se guardan

En `ragnar_agent.sqlite3`, en la máquina donde corre el bot:

- Usuario de TikTok de cada persona que escribe
- El texto de los mensajes intercambiados
- Las derivaciones a asesores
- El registro de DMs enviados (para respetar los límites)

No se guardan datos bancarios ni documentos: el prompt le prohíbe al bot
pedirlos por chat. Esa base de datos contiene datos personales de clientes —
conviene respaldarla y no dejarla en un equipo compartido.

---

## 5. Límites conocidos del sistema

Cosas que **no** hace, para que no haya sorpresas:

- **No lee mensajes con imágenes, audios o videos.** Sólo texto. Si un cliente
  manda un audio, el bot no lo entiende y probablemente pedirá que lo escriba.
- **No confirma pagos ni depósitos.** Está expresamente prohibido en el prompt:
  eso lo valida siempre una persona.
- **Las tasas dependen de la hoja "TASAS FINALES".** Si alguien renombra un
  bloque (`BOB/PEN`, `PEN/BOB`, `BOB/USD`, `BOB/USD INTERNACIONAL`) o deja de
  publicarla, el bot pasa a la tasa de respaldo y lo avisa en el log. Conviene
  revisarlo con `python -m ragnar_agent.cli.estado`.
- **Depende del HTML de TikTok.** Cuando TikTok cambie su interfaz, la lectura
  de la bandeja dejará de funcionar hasta ajustar los selectores. Es
  mantenimiento esperable, no una falla del sistema. El comando
  `--diagnostico` está para eso.
- **Un solo navegador a la vez.** No corras `run_dm` y `run_live --enviar` en
  paralelo: comparten la misma sesión y se pisan.

---

## 6. Antes de activar el envío real — lista de comprobación

- [ ] `python -m ragnar_agent.cli.demo --tasas` muestra las tasas correctas
- [ ] Las cotizaciones de ida y vuelta dejan margen a favor de la casa
- [ ] Se confirmó con el cliente la dirección de `RC. BOB/PEN` / `RC. PEN/BOB`
- [ ] `python -m ragnar_agent.cli.demo` responde con el tono deseado
- [ ] Pedir una llamada o un Meet dispara la derivación
- [ ] `run_dm --una-vez` (en prueba) muestra respuestas correctas a mensajes reales
- [ ] La API key del `.env` es nueva, no una que haya circulado por chat
- [ ] Hay un límite de gasto configurado en la consola de Anthropic
- [ ] Se acordó con el cliente quién revisa las derivaciones y cada cuánto
- [ ] Se entendió y aceptó el riesgo de restricción de la cuenta (sección 1)
