import asyncio
import os
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast

# Guion de prueba con la nueva química carismática y amena
GUION_CARISMATICO = """
Santi: ¡Álex, no te lo vas a creer! Acabo de ver que en Japón han diseñado un robot que no solo cocina, ¡sino que te cuenta chistes mientras lo hace!
Álex: ¡Oye, pues qué maravilla, Santi! Jajaja. Fíjate que al final la tecnología nos va a salvar de la soledad, aunque sea con chistes malos. Pero lo fascinante aquí no es el robot, sino la IA que gestiona el sentido del humor. ¿Te imaginas?
Santi: ¡Es que es increíble! Yo me imagino a ese bicho en mi cocina y ya me veo discutiendo con él por si le falta sal a la paella.
Álex: Te lo juro, Santi... es que la robótica doméstica está llegando a un punto que parece de película de los 80. Pero piénsalo, si conseguimos que las máquinas empaticen así, el impacto social va a ser brutal. ¡Qué época nos ha tocado vivir, compañero!
Santi: ¡Desde luego! Yo estoy deseando ver qué es lo siguiente. ¡Vamos a darle caña al resto de noticias que hoy vengo a tope!
"""

async def prueba_carismatica():
    print("🧪 PRUEBA: QUÍMICA CARISMÁTICA (Álex apasionado + Santi a tope)")
    
    archivos_temp = await procesar_guion_a_audio(GUION_CARISMATICO)
    
    if archivos_temp:
        archivo_final = "output/test_carismatico.mp3"
        os.makedirs("output", exist_ok=True)
        ensamblar_podcast(archivos_temp, archivo_final)
        print(f"\n✅ PRUEBA FINALIZADA: {archivo_final}")
    else:
        print("❌ Error: No se generaron audios.")

if __name__ == "__main__":
    asyncio.run(prueba_carismatica())
