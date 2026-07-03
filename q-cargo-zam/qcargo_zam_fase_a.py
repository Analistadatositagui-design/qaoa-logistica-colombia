"""
Q-CARGO-ZAM v1.0 - Fase A: Referencia Clasica del RCSPP
China -> Medellin | carga ~500 kg | modos maritimo / aereo / terrestre
Autor: Alber Mauricio Marquez Gutierrez

RCSPP (Resource-Constrained Shortest Path Problem):
minimizar COSTO sujeto a TIEMPO <= deadline (T_MAX).

DATOS ILUSTRATIVOS (orden de magnitud) para 500 kg.
NO son cotizaciones reales. Se reemplazan por tarifas verificadas en v2.
"""

import json
from datetime import datetime

AUTOR = "Alber Mauricio Marquez Gutierrez"
PROYECTO = "Q-CARGO-ZAM v1.0"

NODOS = {
    "SZX": "Shenzhen (origen)",
    "YAN": "Yantian (puerto maritimo China)",
    "CAN": "Guangzhou (aeropuerto China)",
    "CTG": "Cartagena (puerto Caribe)",
    "BUN": "Buenaventura (puerto Pacifico)",
    "BOG": "Bogota (aeropuerto Colombia)",
    "MDE": "Medellin (destino)",
}
ORIGEN = "SZX"
DESTINO = "MDE"

# (origen, destino, modo, costo_usd, tiempo_dias) - ILUSTRATIVO, 500 kg
ARCOS = [
    ("SZX", "YAN", "terrestre",    80,  1),
    ("SZX", "CAN", "terrestre",   100,  1),
    ("YAN", "CTG", "mar-std",     900, 34),
    ("YAN", "CTG", "mar-exp",    1300, 28),
    ("YAN", "BUN", "mar-std",     850, 28),
    ("YAN", "BUN", "mar-exp",    1200, 23),
    ("CAN", "BOG", "aire-std",   4500,  4),
    ("CAN", "BOG", "aire-exp",   6000,  2),
    ("CTG", "MDE", "terrestre",   250,  2),
    ("BUN", "MDE", "terrestre",   300,  2),
    ("BOG", "MDE", "terrestre",   150,  1),
    ("BOG", "MDE", "aire-dom",    400,  1),
]

# Deadline elegido para el experimento (dias). Ver sensibilidad abajo.
T_MAX = 28


def enumerar_rutas(origen, destino):
    rutas = []
    def dfs(actual, camino, visitados):
        if actual == destino:
            rutas.append(list(camino))
            return
        for arco in ARCOS:
            if arco[0] != actual:
                continue
            if arco[1] in visitados:
                continue
            camino.append(arco)
            visitados.add(arco[1])
            dfs(arco[1], camino, visitados)
            camino.pop()
            visitados.remove(arco[1])
    dfs(origen, [], {origen})
    return rutas


def costo(ruta):
    return sum(a[3] for a in ruta)


def tiempo(ruta):
    return sum(a[4] for a in ruta)


def describir(ruta):
    partes = [ruta[0][0]]
    for a in ruta:
        partes.append("-[" + a[2] + "]->" + a[1])
    return "".join(partes)


print("=" * 70)
print("  " + PROYECTO + " - FASE A: REFERENCIA CLASICA DEL RCSPP")
print("  Autor: " + AUTOR)
print("  Ruta: China -> Medellin | carga ~500 kg")
fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
print("  Fecha: " + fecha)
print("=" * 70)

rutas = enumerar_rutas(ORIGEN, DESTINO)
print("\n[CONFIGURACION]")
print("  Nodos: " + str(len(NODOS)))
print("  Arcos: " + str(len(ARCOS)))
print("  Rutas multimodales factibles: " + str(len(rutas)))

print("\n[TODAS LAS RUTAS FACTIBLES]")
print("  #   Costo(USD)  Tiempo(d)  Ruta")
print("  " + "-" * 62)
tabla = []
for i, r in enumerate(rutas):
    c = costo(r)
    t = tiempo(r)
    tabla.append((i, c, t, r))
    print("  " + str(i + 1).rjust(2) + "   " +
          str(c).rjust(7) + "    " + str(t).rjust(5) +
          "     " + describir(r))

opt_libre = min(tabla, key=lambda x: x[1])
print("\n[OPTIMO SIN RESTRICCION - equivalente a Dijkstra por costo]")
print("  Costo: " + str(opt_libre[1]) + " USD")
print("  Tiempo: " + str(opt_libre[2]) + " dias")
print("  Ruta: " + describir(opt_libre[3]))

factibles = [x for x in tabla if x[2] <= T_MAX]
print("\n[OPTIMO CON DEADLINE T_MAX = " + str(T_MAX) + " dias - RCSPP]")
if not factibles:
    print("  INFACTIBLE: ninguna ruta cumple el deadline")
    opt_rcspp = None
else:
    opt_rcspp = min(factibles, key=lambda x: x[1])
    print("  Costo: " + str(opt_rcspp[1]) + " USD")
    print("  Tiempo: " + str(opt_rcspp[2]) + " dias")
    print("  Ruta: " + describir(opt_rcspp[3]))

if opt_rcspp is not None:
    sobrecosto = opt_rcspp[1] - opt_libre[1]
    pct = (sobrecosto / opt_libre[1]) * 100 if opt_libre[1] else 0
    print("\n[TENSION DEL DEADLINE]")
    if opt_libre[2] <= T_MAX:
        print("  El optimo libre YA cumple el deadline.")
        print("  El deadline NO muerde: colapsa a costo minimo (facil).")
    else:
        print("  El optimo libre (" + str(opt_libre[2]) +
              "d) NO cumple el deadline.")
        print("  Hay que pagar por velocidad.")
        print("  Sobrecosto por cumplir deadline: " +
              str(sobrecosto) + " USD (" +
              "{:.1f}".format(pct) + "%)")

print("\n[ANALISIS DE SENSIBILIDAD - optimo vs deadline]")
print("  Breakpoints donde el deadline cambia la decision.")
print("  T_max(d)   Costo optimo(USD)   Ruta")
print("  " + "-" * 58)
ultimo = None
for tmax in range(4, 41, 2):
    fs = [x for x in tabla if x[2] <= tmax]
    if not fs:
        costo_txt = "INFACTIBLE"
        ruta_txt = "-"
    else:
        best = min(fs, key=lambda x: x[1])
        costo_txt = str(best[1])
        ruta_txt = describir(best[3])
    if costo_txt != ultimo:
        print("  " + str(tmax).rjust(5) + "      " +
              costo_txt.rjust(10) + "      " + ruta_txt)
        ultimo = costo_txt

print("\n[FRONTERA DE PARETO - rutas no dominadas costo/tiempo]")
pareto = []
for x in tabla:
    dominada = False
    for y in tabla:
        mejor_o_igual = y[1] <= x[1] and y[2] <= x[2]
        estrictamente = y[1] < x[1] or y[2] < x[2]
        if mejor_o_igual and estrictamente:
            dominada = True
            break
    if not dominada:
        pareto.append(x)
pareto.sort(key=lambda x: x[2])
print("  Tiempo(d)   Costo(USD)   Ruta")
print("  " + "-" * 58)
for x in pareto:
    print("  " + str(x[2]).rjust(5) + "      " +
          str(x[1]).rjust(8) + "     " + describir(x[3]))

resultados = {
    "proyecto": PROYECTO,
    "fase": "A - Referencia Clasica RCSPP",
    "autor": AUTOR,
    "ruta": "China -> Medellin",
    "carga_kg": 500,
    "fecha": datetime.now().isoformat(),
    "advertencia_datos": (
        "Costos y tiempos ILUSTRATIVOS (orden de magnitud), no "
        "cotizaciones reales. Reemplazar por tarifas verificadas en v2."
    ),
    "nodos": NODOS,
    "arcos": [
        {"origen": a[0], "destino": a[1], "modo": a[2],
         "costo_usd": a[3], "tiempo_dias": a[4]}
        for a in ARCOS
    ],
    "deadline_experimento_dias": T_MAX,
    "rutas_factibles": [
        {"id": i, "costo_usd": c, "tiempo_dias": t, "descripcion": describir(r)}
        for (i, c, t, r) in tabla
    ],
    "optimo_sin_restriccion": {
        "costo_usd": opt_libre[1],
        "tiempo_dias": opt_libre[2],
        "ruta": describir(opt_libre[3]),
        "metodo": "minimo costo (Dijkstra-equivalente)"
    },
    "optimo_rcspp": None if opt_rcspp is None else {
        "costo_usd": opt_rcspp[1],
        "tiempo_dias": opt_rcspp[2],
        "ruta": describir(opt_rcspp[3]),
        "deadline_dias": T_MAX
    },
    "frontera_pareto": [
        {"tiempo_dias": x[2], "costo_usd": x[1], "ruta": describir(x[3])}
        for x in pareto
    ]
}

ARCHIVO = "qcargo_zam_fase_a_resultados.json"
with open(ARCHIVO, "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print("\n[VERIFICACION DEL NOMBRE Y PROYECTO EN EL JSON]")
with open(ARCHIVO, "r", encoding="utf-8") as f:
    contenido = f.read()
nombre_ok = "Alber Mauricio" in contenido and "Alberto" not in contenido
proyecto_ok = "Q-CARGO-ZAM v1.0" in contenido
if nombre_ok:
    print("  [OK] Nombre correcto: 'Alber Mauricio Marquez Gutierrez'")
elif "Alberto" in contenido:
    print("  [ERROR] Aparece 'Alberto'")
else:
    print("  [WARNING] Nombre no encontrado")
if proyecto_ok:
    print("  [OK] Proyecto correcto: 'Q-CARGO-ZAM v1.0'")
else:
    print("  [ERROR] Nombre de proyecto no encontrado")

print("\n[REGISTRO]")
print("  Guardado en: " + ARCHIVO)
print("  Entrada para Fase B (QAOA-RCSPP)")
print("=" * 70)