"""Imprime el texto plano de un rango de tiempo de un .srt: extracto.py fichero ini_s fin_s"""

import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ts = re.compile(r"(\d+):(\d+):(\d+),\d+ -->")
lineas = open(sys.argv[1], encoding="utf-8").read().splitlines()
ini, fin = float(sys.argv[2]), float(sys.argv[3])
t = None
out = []
for linea in lineas:
    m = ts.match(linea)
    if m:
        t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
    elif t is not None and ini <= t <= fin and linea.strip() and not linea.strip().isdigit():
        out.append(linea.strip())
print(" ".join(out))
