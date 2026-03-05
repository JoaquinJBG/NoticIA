import asyncio
import os
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast_dinamico

# Guion de prueba con dos categorías para probar el cambio de música
BLOQUE_GEOPOLITICA = """
Álex: La situación en el Mar Rojo está escalando a una velocidad preocupante. No es solo un tema de aranceles, es la seguridad de las rutas comerciales globales.
Santi: Ya, pero fíjate Álex que esto está obligando a las empresas a replantearse toda su cadena de suministro. ¡Es un cambio de paradigma!
"""

BLOQUE_FRIKI = """
Santi: ¡Álex! ¡Que ha salido el tráiler de la nueva serie de ciencia ficción y se ve espectacular! Dicen que han usado efectos prácticos en lugar de tanto CGI.
Álex: ¡Oye, pues qué buena noticia! Jajaja. Ya era hora de volver a lo artesanal, que a veces el digital se siente un poco frío, ¿verdad?
"""

async def prueba_diseno_sonoro():
    print("🧪 PROBANDO DISEÑO SONORO DINÁMICO")
    
    # 1. Generar audios por separado
    print("🎙️ Generando audios de Geopolítica...")
    audios_geo = await procesar_guion_a_audio(BLOQUE_GEOPOLITICA)
    
    print("🎙️ Generando audios Friki...")
    audios_friki = await procesar_guion_a_audio(BLOQUE_FRIKI)
    
    # 2. Organizar por bloques
    fragmentos_por_bloque = {
        "geopolitica": audios_geo,
        "friki": audios_friki
    }
    
    # 3. Ensamblar con música dinámica
    archivo_final = "output/test_sonido_pro.mp3"
    os.makedirs("output", exist_ok=True)
    
    ensamblar_podcast_dinamico(fragmentos_por_bloque, archivo_final)
    print(f"\n✅ PRUEBA FINALIZADA: {archivo_final}")
    print("Deberías escuchar música seria en el primer bloque y música animada en el segundo, con una ráfaga en la transición.")

if __name__ == "__main__":
    asyncio.run(prueba_diseno_sonoro())
