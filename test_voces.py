import asyncio
import edge_tts
import os

async def test_all_spanish_voices():
    # Buscamos todas las voces de España (es-ES)
    voices = await edge_tts.VoicesManager.create()
    es_voices = voices.find(Locale="es-ES")
    
    os.makedirs("test_voces", exist_ok=True)
    
    print(f"🔊 Probando {len(es_voices)} voces de España...")
    
    for v in es_voices:
        short_name = v["ShortName"]
        file_path = f"test_voces/{short_name}.mp3"
        texto = f"Hola, soy la voz {short_name}. ¿Qué te parece cómo sueno para el podcast?"
        
        print(f"Generando: {short_name}...")
        communicate = edge_tts.Communicate(texto, short_name)
        await communicate.save(file_path)

if __name__ == "__main__":
    asyncio.run(test_all_spanish_voices())
