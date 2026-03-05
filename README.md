# 🎙️ NoticIA: El Podcast Autónomo Inteligente

**NoticIA** es un sistema automatizado que transforma la actualidad diaria en una tertulia de podcast profesional. Utiliza IA para la ingesta de noticias, generación de guiones dinámicos con personalidad propia y locución con voces realistas, culminando en un proceso de edición y mastering de audio automático.

## 🚀 Características

- **Ingesta Multi-fuente:** Captura noticias de RSS feeds organizados por categorías (España, Geopolítica, Ciencia, Tecnología, Friki, Fútbol).
- **Cerebro Groq/Gemini:** Genera diálogos naturales entre dos locutores, **Álex** (el mentor experto) y **Santi** (el entusiasta tecnológico).
- **Voces Realistas:** Integración con `edge-tts` para una locución fluida con acento de España.
- **Edición Pro:** Montaje automático con sintonías de fondo, transiciones dinámicas y una cadena de mastering (compresión, EQ y normalización) usando `pydub`.

---

## 🛠️ Requisitos Previos

Antes de instalar, asegúrate de tener:

1.  **Python 3.10 o superior.**
2.  **FFmpeg:** Crucial para el procesamiento de audio.
    - **Linux:** `sudo apt install ffmpeg`
    - **macOS:** `brew install ffmpeg`
    - **Windows:** Descargar de [ffmpeg.org](https://ffmpeg.org/download.html) y añadir a la variable de entorno PATH.
3.  **API Keys:**
    - Una cuenta en [Groq Cloud](https://console.groq.com/) para obtener una `GROQ_API_KEY`.
    - (Opcional) `GEMINI_API_KEY` si se desea alternar el modelo.

---

## 📦 Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/NoticIA.git
    cd NoticIA
    ```

2.  **Crea un entorno virtual:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configura las variables de entorno:**
    Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:
    ```env
    GROQ_API_KEY=tu_api_key_aqui
    GEMINI_API_KEY=tu_api_key_opcional
    VOZ_ALEX=es-ES-AlvaroNeural
    VOZ_SANTI=es-ES-XimenaNeural
    ```

---

## 🎮 Uso

### Producción Completa
Para generar un podcast completo con todas las noticias del día (la duración dependerá de la cantidad de noticias):
```bash
python main.py
```

### Prueba Rápida (5 minutos)
Para verificar que todo funciona correctamente (API, audio, FFmpeg) sin gastar muchos tokens ni tiempo:
```bash
python test_5min.py
```

El resultado final se guardará en la carpeta `output/`.

---

## 📂 Estructura del Proyecto

- `main.py`: Punto de entrada principal.
- `src/`: Lógica del sistema (ingesta, generador, locutor, editor).
- `reglas/`: Prompts de sistema y contexto que definen la personalidad de los locutores.
- `sintonias/`: Archivos MP3 con la música de fondo para cada bloque.
- `output/`: Carpeta donde se generan los podcasts finales.
- `temp/`: Carpeta temporal para fragmentos de audio (se limpia automáticamente).

---

## 🎙️ Personajes

- **Álex:** El veterano carismático. Aporta el contexto histórico y la reflexión profunda. Fanático del cine de culto.
- **Santi:** El motor de energía. Experto en gadgets, Nintendo y Pokémon VGC. Siempre busca cómo la tecnología afecta al día a día.

---

## ⚖️ Licencia

Este proyecto está bajo la licencia **Creative Commons Atribución-NoComercial-CompartirIgual 4.0 Internacional (CC BY-NC-SA 4.0)**.

**Esto significa que:**
- ✅ **Puedes:** Copiar, modificar y compartir el código.
- ❌ **No puedes:** Usar este material para fines comerciales o venderlo.
- 🔄 **Compartir Igual:** Si alteras o transformas este código, debes distribuir tu contribución bajo la misma licencia que el original.
- 👤 **Atribución:** Debes dar crédito de manera adecuada al autor original.
