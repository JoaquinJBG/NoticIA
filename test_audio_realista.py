import asyncio
import os
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast

# Guion de prueba corto pero con matices para evaluar el realismo
GUION_PRUEBA = """
Álex: A ver... Santi, fíjate en esta noticia sobre la inteligencia artificial en España. Dicen que van a invertir millones, pero... no sé, yo soy escéptico.
Santi: Ya, pero Álex, ¡qué fuerte! Es que es un paso gigante. Imagínate lo que supone para las startups de aquí. Me dejas loco con tu cinismo, de verdad.
Álex: Es que es de locos, de verdad. Piénsalo bien... ¿Cuántas veces hemos oído promesas similares que luego quedan en nada? Eh... digamos que el papel lo aguanta todo, pero la realidad es otra.
Santi: Oye, pues yo creo que esta vez es distinto. Hay una infraestructura real detrás. ¿Y eso cómo nos afecta en el día a día? Pues en que tendremos servicios más rápidos, digo yo.
Álex: Fíjate Santi... el problema no es la tecnología, es quién la controla. Pero bueno, no me hagas mucho caso, que hoy me he levantado con el pie izquierdo.
Santi: ¡Claro! Como siempre, jajaja. En fin, vamos a ver qué más tenemos por aquí, que hay tela que cortar hoy.
"""

async def prueba_rapida():
    print("🧪 INICIANDO PRUEBA DE AUDIO REALISTA (2-3 min aprox)")
    
    # 1. Generar audios con la nueva configuración de src/locutor.py
    # (Ya incluye el rate -5% para Álex y los tonos ajustados)
    archivos_temp = await procesar_guion_a_audio(GUION_PRUEBA)
    
    # 2. Ensamblar con las nuevas pausas de 800ms de src/editor.py
    if archivos_temp:
        archivo_final = "output/test_realismo.mp3"
        os.makedirs("output", exist_ok=True)
        ensamblar_podcast(archivos_temp, archivo_final)
        print(f"\n✅ PRUEBA FINALIZADA: {archivo_final}")
        print("Escúchalo para verificar el tono, la velocidad y las pausas.")
    else:
        print("❌ Error: No se generaron audios.")

if __name__ == "__main__":
    asyncio.run(prueba_rapida())
