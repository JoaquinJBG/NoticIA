import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

class Config:
    # Credenciales
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # Voces
    VOZ_ALEX = os.getenv("VOZ_ALEX", "es-ES-AlvaroNeural")
    VOZ_SANTI = os.getenv("VOZ_SANTI", "es-ES-XimenaNeural")
    
    # Rutas y Sintonías por Categoría
    RUTA_SINTONIA = os.getenv("RUTA_SINTONIA", "sintonias/sintonia1.mp3")
    SINTONIAS = {
        "espana": "sintonias/serio.mp3",
        "geopolitica": "sintonias/serio.mp3",
        "ia_y_actualidad": "sintonias/animado.mp3",
        "ciencia": "sintonias/neutro.mp3",
        "friki": "sintonias/animado.mp3",
        "futbol": "sintonias/neutro.mp3",
        "intro": "sintonias/sintonia1.mp3",
        "outro": "sintonias/sintonia1.mp3"
    }
    
    CARPETA_OUTPUT = os.getenv("CARPETA_OUTPUT", "output")
    CARPETA_TEMP = os.getenv("CARPETA_TEMP", "temp")
    
    # Carga de Reglas desde archivos markdown
    @staticmethod
    def get_prompt_sistema():
        ruta_reglas = os.path.join("reglas", "instrucciones.md")
        if os.path.exists(ruta_reglas):
            with open(ruta_reglas, "r", encoding="utf-8") as f:
                return f.read()
        return "Eres el equipo de producción de NoticIA." # Fallback

    @staticmethod
    def get_contexto():
        ruta_contexto = os.path.join("reglas", "contexto.md")
        if os.path.exists(ruta_contexto):
            with open(ruta_contexto, "r", encoding="utf-8") as f:
                return f.read()
        return ""
