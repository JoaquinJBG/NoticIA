import asyncio
import os
from src.locutor import procesar_guion_a_audio
from src.editor import ensamblar_podcast

# Guion de prueba limpio, enfocado en el debate real
GUION_PRUEBA_LIMPIO = """
Álex: He estado revisando los informes sobre la inversión en IA en España y, sinceramente, me preocupa la falta de transparencia en la adjudicación de los fondos. 
Santi: Ya... entiendo tu punto, Álex. Pero hay que reconocer que es la primera vez que se pone una cifra tan seria sobre la mesa. 
Álex: La cifra es seria, sí. Pero si no hay un control real, corremos el riesgo de que ese dinero acabe diluido en proyectos que no aportan valor tecnológico real. 
Santi: Claro, el riesgo está ahí. Pero si sale bien, esto podría cambiar el tejido productivo del país en menos de una década. 
Álex: Es una visión optimista. Veremos si la ejecución está a la altura de la ambición. 
"""

async def prueba_limpia():
    print("🧪 INICIANDO PRUEBA DE AUDIO LIMPIA (Sin exceso de muletillas)")
    
    archivos_temp = await procesar_guion_a_audio(GUION_PRUEBA_LIMPIO)
    
    if archivos_temp:
        archivo_final = "output/test_limpio.mp3"
        os.makedirs("output", exist_ok=True)
        ensamblar_podcast(archivos_temp, archivo_final)
        print(f"\n✅ PRUEBA FINALIZADA: {archivo_final}")
    else:
        print("❌ Error: No se generaron audios.")

if __name__ == "__main__":
    asyncio.run(prueba_limpia())
