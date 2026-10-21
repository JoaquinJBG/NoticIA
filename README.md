# 🎙️ NoticIA: El Podcast Autónomo Inteligente

**NoticIA** es un sistema automatizado que transforma la actualidad diaria en una tertulia de podcast profesional. Utiliza IA para la ingesta de noticias, generación de guiones dinámicos con personalidad propia y locución con voces realistas, culminando en un proceso de edición y mastering de audio automático.

## 🚀 Características

- **Ingesta Multi-fuente:** Captura noticias de RSS feeds organizados por categorías (ver la tabla de bloques más abajo).
- **Cerebro Claude:** Genera diálogos naturales entre dos locutores, **Álex** (el mentor experto) y **María** (la entusiasta tecnológica), vía el CLI headless `claude -p`.
- **Voces:** Motores enchufables: Chatterbox (GPU, si la hay), Kokoro (CPU) y `edge-tts` como último recurso (`motor_voz` en la configuración permite fijar uno).
- **Montaje:** `pydub` une los segmentos de voz con pausas y las sintonías de fondo.
- **Mastering:** `ffmpeg` (loudnorm, -16 LUFS) masteriza el MP3 final.

## 🗂️ Bloques del episodio

Orden de emisión, con los nombres que usa el código (`src/noticia/bloques.py`):

| Bloque | Nombre en el episodio |
|---|---|
| `intro` | Introducción |
| `espana` | España |
| `geopolitica` | Geopolítica |
| `ia_y_actualidad` | IA y actualidad |
| `ciencia` | Ciencia |
| `friki` | Friki |
| `futbol` | Fútbol |
| `outro` | Despedida |

---

## 🛠️ Requisitos Previos

1.  **[uv](https://docs.astral.sh/uv/)** — instala Python y las dependencias:
    `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  **Python 3.13** (uv lo instala solo si no lo tienes).
3.  **FFmpeg** — necesario para leer y escribir MP3 (lo usa `pydub`) y para el masterizado.
    - **Linux / WSL:** `sudo apt install ffmpeg`
    - **macOS:** `brew install ffmpeg`
    - **Windows:** descargar de [ffmpeg.org](https://ffmpeg.org/download.html) y añadir al `PATH`.
4.  **[Claude Code](https://claude.ai/download) con una sesión de Claude Max iniciada (obligatoria)** — es el cerebro
    que escribe el guion, vía el CLI headless `claude -p`. Sin ella `make guion` y `make episodio` no generan guion.

> **No hacen falta API keys.** El guion usa tu suscripción de Claude Max, no una API de pago.
> La sesión vive en `~/.claude` (tu carpeta de usuario), **no en el repositorio**: al clonar el
> proyecto en otra máquina tendrás que ejecutar `claude` una vez e iniciar sesión allí.

### Límites y dependencias de riesgo

- **Proyecto personal, sin hosting.** Se lanza desde tu PC con tu sesión de Claude Max (decisión D-01 y D-14).
  El feed (`feed.xml`) y el audio se generan en `output/publicacion/` y solo se sirven en local con
  `make servir`. No hay ningún alojamiento público: Spotify, Apple o cualquier otra app no pueden leerlo
  mientras el equipo no esté encendido y sirviendo la carpeta.
- **Equipo encendido a diario.** La generación depende de la sesión de Claude del equipo donde corre.
- **Sintonías no incluidas.** Los MP3 de `sintonias/` no están en git (`.gitignore`). Un clon nuevo sale
  sin música: el bloque sigue, pero sin sintonía, y el log avisa por cada fichero que falta. `make preparar`
  los lista. Los nombres esperados son `serio.mp3`, `animado.mp3`, `neutro.mp3` y `sintonia1.mp3`
  (definidos en `Settings.sintonias`, `src/noticia/config.py`).
- **`edge-tts` es una dependencia de riesgo.** Usa el servicio de lectura de Microsoft Edge, sin API
  oficial ni garantía de uso. Puede cambiar o dejar de funcionar sin aviso. Es el último recurso de la
  cadena automática: si Kokoro o Chatterbox no cargan, se usa `edge-tts`, y si este también falla no hay
  otro motor.
- **Coste.** El único coste previsto es la suscripción de Claude Max; cada guion consume cuota de esa suscripción.

---

## 📦 Puesta en marcha

```bash
git clone https://github.com/JoaquinJBG/NoticIA.git
cd NoticIA
make preparar
```

`make preparar` instala las dependencias y comprueba que ffmpeg, el CLI de Claude y la GPU (si la hay)
están donde deben. Si falta algo bloqueante, te lo dice y sale con error.

---

## 🎮 Uso

```bash
make ayuda      # ver todos los atajos
```

| Comando | Qué hace |
|---|---|
| `make guion` | Genera **solo el guion** con Claude, sin audio → `output/guion_<fecha>.md` |
| `make audio` | Locuta y masteriza un guion **ya escrito**, sin regenerarlo |
| `make episodio` | Pipeline completo: ingesta → guion → locución → mastering |
| `make publicar` | Pipeline completo + publicación local (feed.xml, ID3, portada) |
| `make modelos-voz` | Descarga los pesos del motor de voz Kokoro |
| `make muestras-voz` | Genera una muestra de cada motor de voz y locutor, para escuchar |
| `make servir` | Sirve `output/publicacion/` en `http://localhost:8000` |
| `make test` | Ejecuta la suite de tests |
| `make lint` | `ruff check` + comprobación de formato |
| `make formato` | Aplica `ruff format` |
| `make limpiar` | Borra los fragmentos temporales de audio |

`make audio` toma por defecto el guion más reciente de `output/`. Para elegir otro:

```bash
make audio GUION=output/guion_2026-07-10.md SALIDA=output/prueba.mp3
```

Iterar sobre el audio con `make audio` cuesta segundos; regenerar el guion cuesta ~14 minutos y consume
cuota de Claude Max. Por eso están separados.

El resultado final se guarda en `output/`.

---

## 📂 Estructura del Proyecto

- `src/noticia/cli.py`: Punto de entrada principal (comando `uv run noticia`).
- `src/noticia/orquestador.py`: Orquesta el episodio diario (guion → locución → montaje →
  publicación), con lock e idempotencia.
- `src/noticia/`: Lógica del sistema (config, ingesta, generador, locutor, editor,
  masterizado, seleccion, publicador, bloques, fechas).
- `src/noticia/voz/`: Motores de voz (edge-tts, Kokoro, Chatterbox), selector por GPU y
  utilidades de texto para locución.
- `reglas/`: Prompts de sistema y contexto que definen la personalidad de los locutores.
- `sintonias/`: Archivos MP3 con la música de fondo para cada bloque (no se versionan; ver [Límites](#límites-y-dependencias-de-riesgo)).
- `output/`: Carpeta donde se generan los podcasts finales y `output/publicacion/` (feed
  RSS, ID3, portada).
- `temp/`: Carpeta temporal para fragmentos de audio (se limpia automáticamente).
- `tests/`: Pruebas automatizadas con pytest.

---

## 🎙️ Personajes

- **Álex:** El veterano carismático. Aporta el contexto histórico y la reflexión profunda. Fanático del cine de culto.
- **María:** El motor de energía. Experta en gadgets, Nintendo y Pokémon VGC. Siempre busca cómo la tecnología afecta al día a día.

---

## ⚖️ Licencia

Este proyecto está bajo la licencia **Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional (CC BY-NC-SA 4.0)**.

**Esto significa que:**
- ✅ **Puedes:** Copiar, modificar y compartir el código.
- ❌ **No puedes:** Usar este material para fines comerciales o venderlo.
- 🔄 **Compartir Igual:** Si alteras o transformas este código, debes distribuir tu contribución bajo la misma licencia que el original.
- 👤 **Atribución:** Debes dar crédito de manera adecuada al autor original.
