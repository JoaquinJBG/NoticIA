import asyncio
import edge_tts

async def prueba_voces():
    # Texto de prueba para cada uno
    test_alex = "Hola, soy Álex. Me encargo de analizar los sesgos de la prensa española y la geopolítica china. Hoy el ambiente está tenso."
    test_santi = "¡Qué pasa! Aquí Santi. Olvidaos de los servidores, lo que mola es esta nueva IA que ha salido en Xataka. ¡Es una locura!"

    # Generar audio de Álex
    print("Grabando a Álex...")
    communicate_alex = edge_tts.Communicate(test_alex, "es-ES-AlvaroNeural")
    await communicate_alex.save("test_alex.mp3")

    # Generar audio de Santi
    print("Grabando a Santi...")
    communicate_santi = edge_tts.Communicate(test_santi, "es-ES-EliasNeural")
    await communicate_santi.save("test_santi.mp3")

    print("✅ ¡Prueba terminada! Busca los archivos test_alex.mp3 y test_santi.mp3 en tu carpeta.")

if __name__ == "__main__":
    asyncio.run(prueba_voces())