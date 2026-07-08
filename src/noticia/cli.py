import asyncio
import os

from noticia.config import settings
from noticia.editor import ensamblar_podcast_dinamico
from noticia.generador import construir_guion
from noticia.ingesta import obtener_noticias
from noticia.locutor import procesar_guion_a_audio


async def producir_episodio():
    print("--- 🎙️ INICIANDO PRODUCCIÓN DE NOTICIA: PROFESSIONAL EDITION ---")

    os.makedirs(settings.carpeta_output, exist_ok=True)
    os.makedirs(settings.carpeta_temp, exist_ok=True)

    print("📡 Capturando noticias de todas las fuentes...")
    noticias = obtener_noticias()

    print("🧠 Generando guion inteligente por bloques (esto puede tardar unos minutos)...")
    guion_por_bloques = construir_guion(noticias)

    print("🎙️ Iniciando locución de voces realistas...")
    fragmentos_audio_por_bloque = {}
    for categoria, lineas in guion_por_bloques.items():
        if not lineas:
            continue
        print(f"🎬 Procesando locución del bloque: {categoria}...")
        texto_bloque = "\n".join(lineas)
        fragmentos_audio_por_bloque[categoria] = await procesar_guion_a_audio(texto_bloque)

    if fragmentos_audio_por_bloque:
        archivo_final = os.path.join(settings.carpeta_output, "NoticIA_PRO_Final.mp3")
        print("🎬 Iniciando montaje dinámico y mastering final...")
        ensamblar_podcast_dinamico(fragmentos_audio_por_bloque, archivo_final)
        print(f"\n--- ✨ PODCAST PROFESIONAL FINALIZADO: {archivo_final} ---")
    else:
        print("❌ Error: No se generaron audios para ensamblar.")


def main():
    asyncio.run(producir_episodio())


if __name__ == "__main__":
    main()
