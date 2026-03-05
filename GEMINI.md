# NoticIA - Automated Podcast Generator

NoticIA is an automated system that transforms real-time news from RSS feeds into a dialogue-based podcast. It uses Google Gemini for script generation, Microsoft Edge TTS for voice synthesis, and `pydub` for final audio assembly with background music.

## Project Overview

The project follows a modular pipeline:
1.  **Ingestion:** Scrapes news from a list of RSS feeds across various categories (Spain, Geopolitics, AI, Science, etc.).
2.  **Generation:** Uses `gemini-1.5-flash` to create a conversational script between two characters:
    -   **Álex:** Senior, analytical, skeptical, and cynical.
    -   **Santi:** Practical, tech-focused, passionate, and curious.
3.  **Locution:** Converts the script into individual audio fragments using `edge-tts`.
4.  **Editing:** Assembles the fragments, adds background music (sintonía), and applies audio effects like fade-in/out and volume normalization.

## Tech Stack

-   **Language:** Python 3.10+
-   **AI Model:** Google Gemini (`google-generativeai`)
-   **TTS Engine:** Microsoft Edge TTS (`edge-tts`)
-   **Audio Processing:** `pydub` (requires **FFmpeg** installed on the system)
-   **RSS Parsing:** `feedparser`
-   **Environment Management:** `python-dotenv`

## Project Structure

-   `main.py`: The main entry point that orchestrates the entire production process.
-   `src/`: Core logic of the application.
    -   `ingesta.py`: RSS feed fetching and cleaning.
    -   `generador.py`: LLM-based script generation.
    -   `locutor.py`: Text-to-speech conversion.
    -   `editor.py`: Audio assembly and music mixing.
    -   `config.py`: Centralized configuration and environment variable loading.
-   `reglas/`: Markdown files defining the LLM's personality and rules.
    -   `instrucciones.md`: System prompt for character roles and style.
    -   `contexto.md`: Additional context for the LLM.
-   `documentacion/`: Detailed technical documentation.
-   `sintonias/`: Background music tracks.
-   `output/`: Directory where the final `.mp3` podcasts are saved.
-   `temp/`: Temporary directory for intermediate audio fragments.

## Building and Running

### Prerequisites

-   Python 3.10 or higher.
-   **FFmpeg** installed and accessible in your system's PATH (required by `pydub`).

### Setup

1.  **Clone the repository and install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment Variables:**
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_api_key_here
    VOZ_ALEX=es-ES-AlvaroNeural
    VOZ_SANTI=es-ES-XimenaNeural
    RUTA_SINTONIA=sintonias/sintonia1.mp3
    ```

### Execution

To generate a new podcast episode, simply run:
```bash
python main.py
```
The final file will be generated in the `output/` directory as `noticIA_final.mp3`.

## Development Conventions

-   **Asynchronous I/O:** The project heavily uses `asyncio` for fetching news and generating audio to ensure efficiency.
-   **Prompt Engineering:** LLM behavior is managed via `reglas/instrucciones.md`. Modify this file to change the podcast's tone or character personalities.
-   **Audio Constants:** Silences and music volume levels are managed within `src/editor.py`.
-   **No Hallucinations:** A core rule (defined in `reglas/instrucciones.md`) is that the AI must not invent news; it must strictly adhere to the provided RSS content.
