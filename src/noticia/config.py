from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/noticia/config.py -> parents[2] es la raíz del proyecto
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    modelo_claude: str = "sonnet"

    # Reparto: dos presentadores fijos (Álex y Santi) y, cada N episodios, una
    # invitada que sustituye a uno de los dos solo ese episodio. Los ajustes de
    # voz de cada motor van por "ranura": alex, santi e invitada.
    # N = 0: nunca hay invitada. La fecha decide el reparto (determinista).
    invitada_cada_n_episodios: int = 3
    invitada_sustituye: Literal["alterna", "aleatorio", "alex", "santi"] = "alterna"
    invitada_nombre: str = "Lucía"

    # Voces edge-tts. En es-ES solo hay un hombre (Álvaro): Santi usa la misma
    # voz con otro rate y un pitch más grave para distinguirse. Para una voz
    # claramente distinta cambia VOZ_SANTI en .env (p.ej. es-MX-JorgeNeural).
    # La invitada usa Ximena (elegida de oído por el usuario); alternativa: Elvira.
    voz_alex: str = "es-ES-AlvaroNeural"
    voz_santi: str = "es-ES-AlvaroNeural"
    voz_invitada: str = "es-ES-XimenaNeural"

    # Prosodia: Álex más pausado, Santi más ágil y grave, la invitada neutra.
    rate_alex: str = "-4%"
    rate_santi: str = "+6%"
    rate_invitada: str = "+0%"
    pitch_alex: str = "+0Hz"
    pitch_santi: str = "-12Hz"
    pitch_invitada: str = "+0Hz"

    # Silencio entre turnos. El crossfade solapaba sílabas.
    pausa_entre_turnos_ms: int = 350

    carpeta_output: str = "output"
    carpeta_temp: str = "temp"

    # Pronunciación: pares palabra -> grafía fonética que se añaden a
    # `noticia.voz.texto.PRONUNCIACION` para el motor de voz. Solo afecta al
    # audio (no al guion.md ni a las notas del feed). Vía env: JSON en
    # PRONUNCIACION_EXTRA, p.ej. PRONUNCIACION_EXTRA='{"ia": "i a"}'.
    pronunciacion_extra: dict[str, str] = {}

    # Selección de motor de voz y control de la locución en paralelo.
    motor_voz: Literal["auto", "edge", "kokoro", "chatterbox"] = "auto"
    concurrencia_locucion: int = 6
    reintentos_locucion: int = 2
    max_fraccion_fallos_locucion: float = 0.10

    # Kokoro (motor CPU).
    kokoro_dir: Path = ROOT / "modelos" / "kokoro"
    kokoro_voz_alex: str = "em_alex"
    kokoro_voz_santi: str = "em_santa"
    kokoro_voz_invitada: str = "ef_dora"
    kokoro_velocidad_alex: float = 0.96
    kokoro_velocidad_santi: float = 1.02
    kokoro_velocidad_invitada: float = 1.05
    kokoro_concurrencia: int = 2

    # Chatterbox Multilingual es-ES (motor GPU).
    chatterbox_ref_alex: Path = ROOT / "voces" / "alex_ref.wav"
    chatterbox_ref_santi: Path = ROOT / "voces" / "santi_ref.wav"
    chatterbox_ref_invitada: Path = ROOT / "voces" / "invitada_ref.wav"
    chatterbox_exageracion_alex: float = 0.5
    chatterbox_exageracion_santi: float = 0.55
    chatterbox_exageracion_invitada: float = 0.6
    chatterbox_cfg: float = 0.4
    chatterbox_temperatura: float = 0.8

    # Mastering: ffmpeg loudnorm en 2 pasadas.
    objetivo_lufs: float = -16.0
    true_peak_dbtp: float = -1.5  # margen para que el MP3 quede <= -1.0
    bitrate_mp3: str = "192k"

    # Guion.
    noticias_por_bloque: int = 8
    reintentos_guion: int = 1
    espera_reintento_guion_s: float = 30.0

    # Publicación.
    publicacion_url_base: str = "http://localhost:8000"
    carpeta_publicacion: Path = ROOT / "output" / "publicacion"
    podcast_titulo: str = "NoticIA"
    podcast_descripcion: str = (
        "La actualidad del día convertida en una tertulia entre amigos: Álex, Santi y, "
        "de vez en cuando, una invitada. Guion y voces generados con IA."
    )
    podcast_autor: str = "NoticIA"
    podcast_email: str = ""  # vacío => se omiten itunes:owner y podcast:locked
    podcast_idioma: str = "es-ES"
    podcast_explicito: bool = False
    max_items_feed: int = 300

    @property
    def ruta_output(self) -> Path:
        """`carpeta_output` como ruta absoluta, resuelta desde ROOT si es relativa."""
        ruta = Path(self.carpeta_output)
        return ruta if ruta.is_absolute() else ROOT / ruta

    @property
    def ruta_temp(self) -> Path:
        """`carpeta_temp` como ruta absoluta, resuelta desde ROOT si es relativa."""
        ruta = Path(self.carpeta_temp)
        return ruta if ruta.is_absolute() else ROOT / ruta

    @property
    def carpeta_episodios(self) -> Path:
        return ROOT / "output" / "episodios"

    @property
    def ruta_sintonia(self) -> str:
        return str(ROOT / "sintonias" / "vintage.mp3")

    @property
    def sintonias(self) -> dict[str, str]:
        """Música de fondo por bloque: una única pista ("Vintage", HoliznaCC0, CC0)."""
        pista = self.ruta_sintonia
        return {
            "espana": pista,
            "geopolitica": pista,
            "ia_y_actualidad": pista,
            "ciencia": pista,
            "friki": pista,
            "futbol": pista,
            "intro": pista,
            "outro": pista,
        }


settings = Settings()


def _leer_regla(nombre: str, fallback: str = "") -> str:
    ruta = ROOT / "reglas" / nombre
    if ruta.exists():
        return ruta.read_text(encoding="utf-8")
    return fallback


def get_prompt_sistema(reparto=None) -> str:
    """Instrucciones generales + perfil de cada personaje del episodio.

    `reparto` (noticia.personajes.Reparto) decide qué perfiles se incluyen; sin
    él se usa el de los dos presentadores habituales.
    """
    from noticia.personajes import Reparto, nombre_personaje

    reparto = reparto or Reparto.habitual()
    partes = [_leer_regla("instrucciones.md", "Eres el equipo de producción de NoticIA.")]
    for locutor in reparto.locutores:
        perfil = _leer_regla(f"personaje_{locutor}.md")
        if perfil:
            partes.append(perfil.replace("{nombre}", nombre_personaje(locutor)))
    return "\n\n".join(partes)


def get_contexto() -> str:
    return _leer_regla("contexto.md", "")
