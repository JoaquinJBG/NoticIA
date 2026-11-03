# Guion de grabación de tu voz para NoticIA

Tu voz se guarda **solo** en `voces/propia/` (ignorada por git). No se sube a ningún sitio.

## Antes de empezar (5 min)
- Habitación con cortinas, sofá o ropa alrededor; cierra ventanas; apaga ventilador/nevera/aire.
- Micro: el del móvil a unos 20 cm de la boca vale; mejor auriculares con micro o un micro USB. Ligeramente de lado para evitar los golpes de "p".
- Grábate 10 s de prueba y escúchala con auriculares: no debe haber zumbido, eco ni saturación.
- Formato: **WAV, mono, 24-48 kHz, 16 o 24 bit**. Nada de música de fondo, ni filtros de voz, ni reducción de ruido del móvil. Un archivo por clip, 20-40 s cada uno.
- Nombres: `voces/propia/clip01.wav`, `clip02.wav`...
- Habla como charlando con un amigo, no como leyendo un telediario. Deja respirar entre frases; no recortes respiraciones ni dudas pequeñas.

## Fase A: ~5 minutos (suficiente para clonar)
Lee cada texto una vez; si te equivocas, repite desde el inicio de la frase (se corta luego).

**clip01 — neutro, tranquilo**
Buenos días. Hoy vamos a repasar lo que ha pasado en las últimas horas, sin prisas y sin dramatismos. Hay cosas importantes, otras menos, y alguna que seguramente ya has visto en el móvil antes de desayunar.

**clip02 — entusiasmado (sube la energía, sonríe)**
¡No me lo puedo creer! Ha ganado en el último minuto, con un gol de rebote que nadie esperaba. Te lo juro, me he levantado del sofá y casi tiro el café. ¡Qué locura de partido!

**clip03 — indignado (más rápido, con mala leche)**
A ver, que alguien me lo explique, porque yo no lo entiendo. Suben el precio otra vez, dicen que es por nuestro bien, y encima nos piden que lo agradezcamos. Es un chiste, pero de los malos.

**clip04 — dudando, pensando en voz alta (pausas, "ehh", "bueno")**
Pues no sé, bueno, depende. Si lo miras por un lado, tiene sentido, ¿no? Pero por otro... mmm, no estoy seguro. A ver, déjame pensarlo un segundo. Sí, creo que tengo una idea.

**clip05 — cercano y bajito (como contando un secreto)**
Te cuento una cosa, pero que quede entre nosotros. Cuando lo vi por primera vez, pensé que era broma. Luego me di cuenta de que iba completamente en serio, y ya no pude parar de reírme.

**clip06 — datos y cifras (claro, ritmo constante)**
El Ibex cerró en once mil doscientos puntos, un cero coma ocho por ciento más que ayer. El euro se mantiene a uno coma cero nueve frente al dólar, y el barril de Brent baja a setenta y cuatro dólares.

**clip07 — reacción corta y risas (frases sueltas, cada una distinta)**
¡Ja! No me digas. ¿En serio? Madre mía. Vaya tela. Ay, por favor. Bueno, bueno, bueno. Eso sí que no me lo esperaba. Uf, qué cansancio.

**clip08 — dos tonos (pregunta y respuesta tú solo, cambia de actitud)**
¿Tú crees que van a llegar a un acuerdo? Hombre, yo no apostaría mucho. Pero ¿y si lo hacen? Pues entonces me callo y me tomo una caña a vuestra salud.

**clip09 — presentación de podcast (energía de radio)**
¡Muy buenas, gente! Esto es NoticIA, el podcast donde la actualidad se cuenta como la contaría un amigo en el bar. Siéntate, ponte cómodo, y vamos allá.

**clip10 — despedida (cálido, relajado, bajando el ritmo al final)**
Y hasta aquí el episodio de hoy. Gracias por escucharnos, de verdad. Mañana volvemos con más noticias, más opiniones y, con suerte, menos disgustos. Cuídate mucho, y hasta pronto.

## Fase B: 25-40 min (solo si con la Fase A no basta)
Para afinar el modelo (LoRA) hacen falta muchas frases de 3-12 s. Cuando quieras hacerla, dímelo y te preparo un guion largo con frases de diario (política, deporte, ciencia, tecnología) y una hoja de cotejo. Graba en una sola sesión, mismo sitio y misma distancia al micro.

## Después de grabar
1. Copia los WAV a `voces/propia/`.
2. Valídalos: `uv run python scripts/preparar_voz_propia.py voces/propia`
3. Avísame y pruebo tu voz como referencia (A/B contra la actual).
