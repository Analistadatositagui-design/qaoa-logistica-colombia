#!/usr/bin/env python3
"""
verificar_paquete.py - Auditor del paquete de registro QAOA v1.0
Autor: Alber Mauricio Marquez Gutierrez

Ejecutar desde la raiz del paquete:  python verificar_paquete.py

Comprueba, SIN incrustar ningun secreto en este archivo:
  1) Que todos los archivos esperados esten presentes.
  2) Que ningun script contenga un token real (solo TU_TOKEN_AQUI).
  3) Que no se haya colado ningun archivo de credenciales por su nombre.
  4) Que ambos Job ID de hardware esten en sus JSON.
  5) Que el nombre del autor sea correcto en todo el paquete.

No sube nada: solo lee y reporta. Si ve "PAQUETE COMPLETO Y LIMPIO",
el paquete es seguro para publicar.
"""
import os
import re
import sys
import json

RAIZ = os.path.dirname(os.path.abspath(__file__))
AUTOR_OK = "Alber Mauricio Marquez Gutierrez"
PLACEHOLDER = "TU_TOKEN_AQUI"

ARCHIVOS_ESPERADOS = [
    "README.md", "CITATION.cff", ".zenodo.json",
    ".gitignore", "verificar_paquete.py",
    "q-coffee-maxcut/README.md",
    "q-coffee-maxcut/qcoffee_maxcut_fase_a.py",
    "q-coffee-maxcut/qcoffee_maxcut_fase_a_resultados.json",
    "q-coffee-maxcut/qcoffee_maxcut_fase_b.py",
    "q-coffee-maxcut/qcoffee_maxcut_fase_b_resultados.json",
    "q-coffee-maxcut/qcoffee_maxcut_fase_c.py",
    "q-coffee-maxcut/qcoffee_maxcut_fase_c_resultados.json",
    "q-cargo-zam/README.md",
    "q-cargo-zam/qcargo_zam_fase_a.py",
    "q-cargo-zam/qcargo_zam_fase_a_resultados.json",
    "q-cargo-zam/qcargo_zam_fase_b_v3.py",
    "q-cargo-zam/qcargo_zam_fase_b_v3_resultados.json",
    "q-cargo-zam/qcargo_zam_fase_c.py",
    "q-cargo-zam/qcargo_zam_fase_c_resultados.json",
]

JOB_IDS = {
    "q-coffee-maxcut/qcoffee_maxcut_fase_c_resultados.json": "d918bteu9n7c73am5nmg",
    "q-cargo-zam/qcargo_zam_fase_c_resultados.json": "d92tk17d07jc73dvpnt0",
}

NOMBRES_PROHIBIDOS = re.compile(
    r"(clave|token|password|gmail.?pass|api.?key|anthropic|gemini|cloudflare|\.env$|\.pem$|\.key$)",
    re.IGNORECASE,
)

ASIGNACION_SECRETO = re.compile(
    r"""(TOKEN|API_KEY|APIKEY|SECRET|PASSWORD)\s*=\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

problemas = []
avisos = []


def leer(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def main():
    print("=" * 66)
    print("  AUDITOR DEL PAQUETE DE REGISTRO QAOA v1.0")
    print("  Autor esperado: " + AUTOR_OK)
    print("=" * 66)

    print("\n[1/5] Manifiesto de archivos")
    for rel in ARCHIVOS_ESPERADOS:
        p = os.path.join(RAIZ, rel)
        if os.path.isfile(p):
            print("  [OK]   " + rel)
        else:
            print("  [FALTA] " + rel)
            problemas.append("Falta archivo: " + rel)

    # La licencia puede llamarse LICENSE, LICENSE.txt o LICENSE.md (todas validas en GitHub)
    lic = [n for n in ("LICENSE", "LICENSE.txt", "LICENSE.md")
           if os.path.isfile(os.path.join(RAIZ, n))]
    if lic:
        print("  [OK]   " + lic[0] + " (licencia)")
    else:
        print("  [FALTA] LICENSE / LICENSE.txt / LICENSE.md")
        problemas.append("Falta archivo de licencia")

    print("\n[2/5] Escaneo de tokens/secretos en el contenido")
    hallado_secreto = False
    for dirpath, dirnames, filenames in os.walk(RAIZ):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, RAIZ).replace("\\", "/")
            if NOMBRES_PROHIBIDOS.search(fn):
                print("  [SECRETO?] nombre sospechoso: " + rel)
                problemas.append("Archivo de credenciales en el paquete: " + rel)
            if fn.lower().endswith((".py", ".json", ".md", ".txt", ".cff", ".yml", ".yaml")):
                try:
                    txt = leer(full)
                except Exception:
                    continue
                for m in ASIGNACION_SECRETO.finditer(txt):
                    valor = m.group(2)
                    if valor != PLACEHOLDER and len(valor) >= 12:
                        print("  [SECRETO!] " + rel + " -> " + m.group(1) +
                              ' = "' + valor[:4] + '...(' + str(len(valor)) + ' chars)"')
                        problemas.append("Posible token real en: " + rel)
                        hallado_secreto = True
    if not hallado_secreto:
        print("  [OK] Ningun token real en el contenido (solo TU_TOKEN_AQUI)")

    print("\n[3/5] Job IDs de hardware presentes")
    for rel, jid in JOB_IDS.items():
        p = os.path.join(RAIZ, rel)
        if os.path.isfile(p) and jid in leer(p):
            print("  [OK] " + jid + "  en  " + rel)
        else:
            print("  [FALTA] " + jid + "  en  " + rel)
            problemas.append("Job ID ausente: " + jid)

    print("\n[4/5] Nombre del autor en scripts y JSON")
    for rel in ARCHIVOS_ESPERADOS:
        if not (rel.endswith(".py") or rel.endswith(".json")):
            continue
        p = os.path.join(RAIZ, rel)
        if not os.path.isfile(p):
            continue
        txt = leer(p)
        nombre_ok = (AUTOR_OK in txt) or ("Alber Mauricio" in txt and "Marquez Gutierrez" in txt)
        if nombre_ok:
            print("  [OK] " + rel)
        else:
            avisos.append("Autor no hallado (revisar): " + rel)
            print("  [aviso] autor no explicito en " + rel)

    print("\n[5/5] JSON validos")
    for rel in ARCHIVOS_ESPERADOS:
        if not rel.endswith(".json"):
            continue
        p = os.path.join(RAIZ, rel)
        if not os.path.isfile(p):
            continue
        try:
            json.loads(leer(p))
            print("  [OK] " + rel)
        except Exception as e:
            print("  [ERROR] JSON invalido: " + rel + " (" + str(e) + ")")
            problemas.append("JSON invalido: " + rel)

    print("\n" + "=" * 66)
    if problemas:
        print("  RESULTADO: " + str(len(problemas)) + " PROBLEMA(S) - NO PUBLICAR AUN")
        for x in problemas:
            print("    - " + x)
        if avisos:
            print("  Avisos:")
            for x in avisos:
                print("    - " + x)
        print("=" * 66)
        return 1
    else:
        print("  PAQUETE COMPLETO Y LIMPIO - seguro para publicar")
        if avisos:
            print("  (avisos menores, no bloquean:)")
            for x in avisos:
                print("    - " + x)
        print("=" * 66)
        return 0


if __name__ == "__main__":
    sys.exit(main())
