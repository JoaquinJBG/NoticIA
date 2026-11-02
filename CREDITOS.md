# Créditos

## Música de fondo

- **"Vintage"** — HoliznaCC0, álbum *Lo-fi And Chill*.
  Fuente: https://freemusicarchive.org/music/holiznacc0/lo-fi-and-chill/vintagemp3/
- Licencia: **CC0 1.0** (dominio público), https://creativecommons.org/publicdomain/zero/1.0/ — no exige atribución; se apunta por cortesía.
- Uso: única pista de fondo de todos los bloques (intro, outro y contenido).

### Cómo colocar el fichero

Los `.mp3` están en `.gitignore`, así que la pista **no va en git**. Descárgala de la URL
de arriba y guárdala como `sintonias/vintage.mp3` (esa es la ruta que usa
`Settings.sintonias`). Sin ella, el montaje sigue pero los bloques salen sin música
(`scripts/preparar.sh` y el editor avisan de la sintonía que falta).
