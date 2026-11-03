# Voces más naturales para NoticIA y camino a la voz propia (2026-11-03)

Coste: 0 €. No puedo escuchar audio: lo que diga de "suena mejor/peor" lo decide el usuario de oído.
Lo marcado **(verificado)** sale de la ficha/página oficial que abrí; **(sin verificar)** es conocimiento general o de terceros.

## Resumen

1. **Las bases públicas en español sirven para entrenar, pero casi ninguna para "poner la voz de alguien en un podcast"**. Las voces son personas reales (lectores de LibriVox, voluntarios de Common Voice) que no consintieron que se clone su voz como personaje. Lo más defendible: usar voces públicas solo como *referencia de prueba* y, para el producto final, **la voz propia del usuario** (con su permiso, que da él).
2. **Lo que más reduce lo robótico, por orden de coste**: (a) referencia mejor (limpia, expresiva, 10-30 s, de un hablante natural), (b) guion escrito para el oído, (c) modelo de diálogo (MOSS-TTSD) que genera la conversación entera, (d) fine-tuning/LoRA con 30-60 min de voz propia.
3. **Recomendación**: que el usuario grabe ~15 min (guion en `docs/guion-grabacion-voz.md`). Con eso: clonado zero-shot inmediato (Chatterbox/Qwen3-TTS/MOSS) y, si no basta, LoRA de Chatterbox con 30-60 min más.

## 1. Bases de datos de voz en español

| Base | Tipo | Hablantes | Horas (es) | Licencia | ¿En un podcast? |
|---|---|---|---|---|---|
| [MLS](https://huggingface.co/datasets/facebook/multilingual_librispeech) (OpenSLR 94) | leída (audiolibros LibriVox) | 86 train + 20 dev + 20 test | 917,7 + 10 + 10 h | CC BY-4.0 (la ficha cita también dominio público) **(verificado)** | Sí con atribución, pero son lectores reales: no clonar a una persona identificable como "tu presentador" sin su consentimiento. Sirve para entrenar/afinar un modelo genérico |
| [Common Voice es](https://datacollective.mozillafoundation.org/datasets/cmn4z1n52000knv07h01532dd) (v25) | leída (frases) | 26 896 | 2 275 h grabadas, 593 h validadas | CC0-1.0 **(verificado)**, pero los [términos](https://commonvoice.mozilla.org/en/terms) prohíben identificar a hablantes, redistribuir el dataset **y crear clones o suplantaciones de voz** **(verificado, sin detalle)** | **No para clonar voces.** Útil solo como datos de entrenamiento agregados |
| [VoxPopuli](https://huggingface.co/datasets/facebook/voxpopuli) | oratoria parlamentaria (Parlamento Europeo) | 305 | 166 h transcritas | La ficha dice CC0 "y ver aviso legal del Parlamento Europeo para los datos en bruto" **(verificado)**; un artículo de 2025 afirma CC BY-NC 4.0 ([arXiv](https://arxiv.org/pdf/2506.17525)) → **licencia dudosa** | Evitar para producto |
| [CSS10 es](https://github.com/Kyubyong/css10) | leída, 1 hablante ("Tux", LibriVox, Galdós) | 1 | 23,8 h | repo Apache-2.0; el audio es LibriVox (dominio público) **(verificado; la licencia del audio no la declara el repo)** | Es el mejor candidato de "una sola voz pública" para afinar un modelo; voz de narrador clásico, no conversacional |
| M-AILABS es | leída (LibriVox) | 21 | ~108 h (cifra de [terceros](https://mfa-models.readthedocs.io/en/latest/_sources/acoustic/Spanish/Spanish%20MFA%20acoustic%20model%20v2_0_0.md.txt)) | textos y audio en dominio público según [la descripción](https://cs.paperswithcode.com/dataset/m-ailabs-speech-dataset); la licencia propia no pude leerla **(sin verificar)** | Igual que CSS10 |
| [OpenSLR 73](https://www.openslr.org/73/) y hermanas (es de Perú, Chile, Colombia…) | leída, estudio, voluntarios | no consta | no consta | **CC BY-SA 4.0** **(verificado)** | Acento latinoamericano y share-alike: poco útil para un podcast de España |
| [TEDx es (OpenSLR 67)](https://www.openslr.org/67/) | **espontánea** (charlas) | no consta | ~24 h | **CC BY-NC-ND 4.0** **(verificado)** | No: no comercial y sin derivadas |

Notas:
- **Conversacional abierta y de España con licencia clara no he encontrado** (lo conversacional es CC BY-NC o cerrado). Por eso la voz propia es la vía realista.
- Las voces que ya están en `voces/candidatas/` (lombardi, mpinedag…) provienen de LibriVox: dominio público como obra, pero siguen siendo la voz de una persona real. Úsense como prueba interna, no como identidad del podcast sin decidirlo a conciencia.
- Cláusula "clonar voces": Common Voice la prohíbe expresamente; MLS/LibriVox no la tienen, lo que no la hace éticamente neutra.

## 2. Qué hace que suene natural

- **Zero-shot (clonado sin entrenar)**: el modelo imita timbre y estilo de una referencia de 3-30 s. Rápido, pero hereda la prosodia del modelo base (de ahí lo "plano"). XTTS-v2 admite 6 s ([ficha](https://huggingface.co/coqui/XTTS-v2)); Qwen3-TTS "3 s" ([ficha](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)); MOSS-TTSD 3-10 s por hablante ([ficha](https://huggingface.co/OpenMOSS-Team/MOSS-TTSD-v1.0)).
- **Calidad de la referencia** manda más que el modelo: sala sin eco, micro cerca, lectura expresiva con ritmo de charla (no de audiolibro), 10-30 s sin silencios largos. (Práctica habitual, sin verificar en estudio.)
- **Fine-tuning / LoRA**: ajusta el modelo a una voz concreta y a su prosodia. Cifras orientativas **(sin verificar, de la experiencia general)**: LoRA de una voz decente con 30-60 min limpios; mejores resultados con 2-3 h. Con menos de 15 min mejor zero-shot.
- **Diálogo en una pasada** (MOSS-TTSD): da coherencia entre turnos que ningún modelo "frase a frase" consigue.

| Modelo | Español | Licencia | Clonado | Fine-tuning | 12 GB |
|---|---|---|---|---|---|
| Chatterbox multilingüe (actual) | sí, hay [finetunes es-ES/es-LatAm](https://huggingface.co/ResembleAI/chatterbox) | MIT **(verificado)** | zero-shot | LoRA con repos de terceros: [Ahmed-Ezzat20](https://gh.hhj520.top/Ahmed-Ezzat20/chatterbox-finetuning-multilingual) (rank 32, alpha 64), [gokhaneraslan](https://huggingface.co/ibibek/train_chatterbox) | sí |
| Qwen3-TTS 1.7B Base | sí (10 idiomas) | Apache-2.0 **(verificado)** | 3 s + transcripción | "se puede usar para FT" **(verificado)**, sin guía en la ficha | sí |
| MOSS-TTSD v1.0 (8B) | sí (20 idiomas) | Apache-2.0 **(verificado)** | 1-5 hablantes, 3-10 s | no | solo cuantizado; en la prueba falló (ver §4) |
| CosyVoice 2/3 (0,5 B) | sí (9 idiomas) | Apache-2.0 **(verificado)** | zero-shot cross-lingual | scripts de entrenamiento en el repo | sí; instalación en Windows incierta |
| F5-TTS | no declarado en la ficha | **CC BY-NC 4.0** **(verificado)** | zero-shot | sí, con notebooks | sí, pero **no comercial** |
| XTTS-v2 | sí | CPML (Coqui, no comercial **sin verificar**) | 6 s | sí | sí; proyecto abandonado |
| StyleTTS2 | solo inglés de serie | MIT (sin verificar) | difícil | requiere dataset grande | — |

Descartados por licencia/estado: F5-TTS, XTTS-v2 (no comercial). Si el podcast fuera monetizado, quedan Chatterbox, Qwen3-TTS, MOSS-TTSD y CosyVoice (todos MIT/Apache).

## 3. Plan con la voz propia

Condiciones: voz solo en `voces/propia/` (carpeta ignorada por git: `git check-ignore -v voces/propia/x.wav` → `.gitignore:38:voces/`), nunca subida a servicios ni modelos en la nube. Todo se procesa en local.

**Qué grabar** (guion completo en [`guion-grabacion-voz.md`](guion-grabacion-voz.md)):
- Fase A, **~5 min**: 10 clips de 20-40 s en tono charla, con emociones variadas. Suficiente para zero-shot y para escoger la mejor referencia.
- Fase B, **~25-40 min** (opcional, si A no basta): frases cortas conversacionales para LoRA.
- Formato: WAV mono, 24-48 kHz, 16/24 bit, sin música ni compresión, sin recortar las respiraciones.
- Micro: el del móvil a 20 cm sirve; mejor un micro USB o auriculares con micro cerca de la boca. Sala: habitación con cortinas/ropa, sin ventilador ni nevera, ventanas cerradas. Prueba de 10 s antes: no debe oírse zumbido ni eco.

**Cómo se usa**:
1. Zero-shot: `scripts/preparar_voz_propia.py` valida los WAV (formato, nivel, silencios) y elige el mejor clip de 10-30 s → `voces/propia/ref_*.wav`. Se prueba como referencia de Santi (o de ambos) en Chatterbox, Qwen3-TTS y MOSS-TTSD.
2. Si suena parecido pero plano: LoRA de Chatterbox con la Fase B (trabajo de una sesión aparte; descarga de dependencias a confirmar antes).
3. Resultado esperable (juicio mío, no medido): con 5 min, timbre muy parecido y prosodia "de modelo"; con LoRA y 30-60 min, la cadencia mejora, pero no se garantiza que desaparezca lo robótico del todo. Una sola voz propia cubre a un presentador; el otro seguiría necesitando una referencia (otra persona con su permiso o una de LibriVox).

## 4. Pruebas A/B (estado)

- Referencia para comparar: `output/muestras-mejoras-2026-11-02/nat1_parametros-por-defecto.wav` (Chatterbox por defecto), mismo diálogo `textos2.DIALOGO`.
- Candidato intentado: **MOSS-TTSD** (referencias públicas lombardi / pablocrdz de LibriVox, solo prueba interna) con `C:\Users\dotoy\ttsp\moss\moss_gen_ab.py`. **No se pudo generar ninguna muestra**:
  - 4 bits: *segmentation fault* al cargar pesos (bitsandbytes en Windows); log `ab_moss4b.log` en esa carpeta.
  - 8 bits: `CUDA out of memory` con ~3,3 GB cargados, porque otras apps ya ocupan ~6,5 GB de los 12 GB; log `ab_moss8.log`.
  - Siguiente intento razonable: cerrar apps que usen GPU y repetir en 8 bits; si falla, MOSS-TTSD queda descartado en esta máquina.
- `output/muestras-voces-naturales/` está vacía: no hay A/B todavía. La primera comparación real será Chatterbox/Qwen3-TTS con la voz propia cuando el usuario grabe.
- No he escuchado nada; el orden de preferencia lo da el usuario.

## Fuentes
[MLS](https://huggingface.co/datasets/facebook/multilingual_librispeech) · [Common Voice 25 es](https://datacollective.mozillafoundation.org/datasets/cmn4z1n52000knv07h01532dd) · [términos Common Voice](https://commonvoice.mozilla.org/en/terms) · [VoxPopuli](https://huggingface.co/datasets/facebook/voxpopuli) · [calidad de datasets (licencia VoxPopuli)](https://arxiv.org/pdf/2506.17525) · [CSS10](https://github.com/Kyubyong/css10) · [M-AILABS](https://cs.paperswithcode.com/dataset/m-ailabs-speech-dataset) · [OpenSLR 73](https://www.openslr.org/73/) · [OpenSLR 67](https://www.openslr.org/67/) · [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) · [F5-TTS](https://huggingface.co/SWivid/F5-TTS) · [XTTS-v2](https://huggingface.co/coqui/XTTS-v2) · [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) · [MOSS-TTSD](https://huggingface.co/OpenMOSS-Team/MOSS-TTSD-v1.0) · [CosyVoice](https://github.com/FunAudioLLM/CosyVoice) · informe previo `output/muestras-mejoras-2026-11-02/INFORME-naturalidad.md`.
