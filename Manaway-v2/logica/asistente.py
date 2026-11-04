"""Asistente local de reglas: consultas sobre la red de rutas, sin internet."""
import difflib
import re
import unicodedata

from modelo import datos
from logica import funciones
from modelo.estado import estado


# ---------- Utilidades de lenguaje ----------
def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios simples."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


SALUDOS = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
           "que tal", "hey", "saludos")

EJEMPLOS_PREGUNTAS = [
    "¿Qué rutas pasan por Mercado Mayoreo?",
    "¿Cómo llego de Ciudad Sandino a Metrocentro?",
    "Paradas de la 117",
    "¿Cuánto cuesta el pasaje?",
]

_TEXTO_ESTADO = {
    "normal": "Normal (sin novedades)",
    "retraso": "Con retrasos",
    "suspendido": "Suspendida temporalmente",
}


def paradas_mencionadas(texto: str) -> list:
    """Paradas cuyo nombre aparece en la pregunta.

    Reglas (de mayor a menor confianza):
    1. Prefijo completo del nombre («mercado oriental»).
    2. Token suelto de 3+ caracteres («oriental», «unan»).
    3. Tolerancia a errores de escritura con difflib («metrocentr»).

    Devuelve las paradas ordenadas de mejor a peor coincidencia.
    """
    consulta = normalizar(texto)
    if not consulta:
        return []
    # Palabras de la consulta sin puntuación (evita que «UCA?» no case)
    palabras_consulta = set(re.findall(r"[a-z0-9]+", consulta))
    coincidencias = []  # (puntaje, longitud_nombre, parada)
    for p in datos.paradas:
        nombre = normalizar(p.nombre)
        tokens = nombre.split()
        # 1) Prefijo del nombre presente en la consulta
        puntaje = 0
        for k in range(len(tokens), 0, -1):
            prefijo = " ".join(tokens[:k])
            if len(prefijo) >= 4 and prefijo in consulta:
                puntaje = k
                break
        # 2) Token suelto significativo de la consulta
        if puntaje == 0 and any(len(t) >= 3 and t in palabras_consulta
                                for t in tokens):
            puntaje = 1
        if puntaje:
            coincidencias.append((puntaje, len(nombre), p))
    if not coincidencias:
        # 3) Tolerancia a errores de escritura (difflib)
        nombres = {normalizar(p.nombre): p for p in datos.paradas}
        for palabra in palabras_consulta:
            if len(palabra) < 5:
                continue
            for parecido in difflib.get_close_matches(
                    palabra, nombres.keys(), n=2, cutoff=0.8):
                p = nombres[parecido]
                coincidencias.append((1, len(parecido), p))
    coincidencias.sort(key=lambda c: (-c[0], -c[1]))
    vistas, resultado = set(), []
    for _, _, p in coincidencias:
        if p.id not in vistas:
            vistas.add(p.id)
            resultado.append(p)
    return resultado


def sugerencias_parecidas(consulta: str, maximo: int = 2) -> list:
    """Paradas con nombre parecido a lo escrito (para el fallback)."""
    nombres = {normalizar(p.nombre): p for p in datos.paradas}
    sugeridas, vistas = [], set()
    for palabra in re.findall(r"[a-z0-9]{5,}", consulta):
        for parecido in difflib.get_close_matches(
                palabra, nombres.keys(), n=1, cutoff=0.6):
            p = nombres[parecido]
            if p.id not in vistas:
                vistas.add(p.id)
                sugeridas.append(p)
        if len(sugeridas) >= maximo:
            break
    return sugeridas


def rutas_mencionadas(texto: str) -> list:
    """Rutas cuyo número aparece en la pregunta (p. ej. «la 117»)."""
    consulta = normalizar(texto)
    encontradas = []
    for numero in re.findall(r"\b\d{1,3}\b", consulta):
        r = funciones.ruta_por_numero(str(int(numero)))
        if r and r not in encontradas:
            encontradas.append(r)
    return encontradas


def rutas_de_parada(parada) -> list:
    return [r for r in datos.rutas if parada.id in r.paradas_ids]


# ---------- Respuestas por intención ----------
def _responder_saludo(saludo: str) -> dict:
    if saludo.startswith("gracias"):
        return {
            "texto": "¡De nada! Cuando quieras consultame por rutas, "
                     "paradas o viajes.",
            "sugerencias": EJEMPLOS_PREGUNTAS,
        }
    return {
        "texto": ("¡Hola! Soy el asistente de ManaWAY 🚌\n"
                  "Conozco las 43 rutas urbanas de Managua: preguntame qué "
                  "rutas pasan por un lugar, cómo llegar de un punto a "
                  "otro, paradas, estados, cooperativas y horarios."),
        "sugerencias": EJEMPLOS_PREGUNTAS,
    }


def _responder_capacidades() -> dict:
    return {
        "texto": ("Puedo ayudarte con:\n"
                  "• «¿Qué rutas pasan por Mercado Mayoreo?»\n"
                  "• «¿Cómo llego de Ciudad Sandino a Metrocentro?»\n"
                  "• «Paradas de la 117»\n"
                  "• «¿Qué cooperativa opera la 117?»\n"
                  "• «Estado y horarios de la 110»\n"
                  "• «¿Cuánto cuesta el pasaje?»\n"
                  "• «¿Qué rutas hay en Managua?» (lista completa)\n"
                  "• «¿Hay incidencias reportadas?»\n"
                  "También entendés saludos y agradecimientos 😉"),
        "sugerencias": EJEMPLOS_PREGUNTAS,
    }


def _responder_viaje(origen, destino) -> dict:
    opciones = funciones.planificar_viaje(origen.id, destino.id)
    sugerencias = [f"¿Qué rutas pasan por {origen.nombre}?",
                   f"Paradas de la {rutas_de_parada(destino)[0].numero}"
                   if rutas_de_parada(destino) else
                   "¿Qué rutas pasan por el centro?"]
    if not opciones:
        return {
            "texto": (f"No encontré un viaje de {origen.nombre} a "
                      f"{destino.nombre} con las rutas actuales.\n"
                      "Probá con paradas más cercanas o consultame «¿Qué "
                      "rutas pasan por ...?» para ver alternativas."),
            "sugerencias": EJEMPLOS_PREGUNTAS,
        }
    lineas = [f"Para ir de {origen.nombre} a {destino.nombre} "
              f"encontré {len(opciones)} opción(es):"]
    for i, op in enumerate(opciones[:3], start=1):
        numeros = " → ".join(funciones.ruta_por_id(rid).numero
                             for rid in op.rutas_ids)
        lineas.append(f"\n{i}. {op.tipo.capitalize()} · ruta(s) {numeros} · "
                      f"~{op.minutos} min ({op.paradas_total} paradas)")
        for paso in op.pasos:
            lineas.append(f"   • {paso.texto}")
    return {"texto": "\n".join(lineas), "sugerencias": sugerencias}


def _responder_rutas_por_paradas(paradas: list) -> dict:
    lineas = []
    sugerencias = []
    for p in paradas[:2]:
        rutas = rutas_de_parada(p)
        if not rutas:
            lineas.append(f"Por «{p.nombre}» no pasa ninguna ruta "
                          "registrada ahora mismo.")
            continue
        lineas.append(f"Por «{p.nombre}» pasan {len(rutas)} ruta(s):")
        for r in rutas:
            cooperativa = f" · op. {r.cooperativa}" if r.cooperativa else ""
            lineas.append(f"  • {r.numero} · {r.nombre} "
                          f"[{_TEXTO_ESTADO.get(r.estado, r.estado)}]"
                          f"{cooperativa}")
        sugerencias.append(f"¿Cómo llego de {p.nombre} a ...?")
    if paradas:
        sugerencias.append("¿En qué estado está la "
                           f"{rutas_de_parada(paradas[0])[0].numero}"
                           if rutas_de_parada(paradas[0]) else
                           "Paradas de la 117")
    return {"texto": "\n".join(lineas), "sugerencias": sugerencias[:3]}


def _responder_paradas_ruta(ruta) -> dict:
    paradas = funciones.paradas_de_ruta(ruta)
    unidades = funciones.unidades_de_ruta(ruta.id)
    lineas = [f"La ruta {ruta.numero} — {ruta.nombre} tiene "
              f"{len(paradas)} paradas:"]
    for i, p in enumerate(paradas, start=1):
        lineas.append(f"  {i}. {p.nombre}")
    lineas.append(f"\nHorario: {ruta.horario} · cada ~{ruta.frecuencia_min} "
                  f"min · {len(unidades)} unidad(es).")
    if ruta.cooperativa:
        lineas.append(f"Opera: {ruta.cooperativa}.")
    return {
        "texto": "\n".join(lineas),
        "sugerencias": [f"¿En qué estado está la {ruta.numero}?",
                        "¿Cómo llego a "
                        f"{paradas[-1].nombre if paradas else 'ahí'}?"],
    }


def _responder_estado_ruta(rutas: list) -> dict:
    lineas = []
    for r in rutas[:3]:
        unidades = funciones.unidades_de_ruta(r.id)
        activas = [u for u in unidades if u.estado == "en ruta"]
        lineas.append(f"Ruta {r.numero} ({r.nombre}): "
                      f"{_TEXTO_ESTADO.get(r.estado, r.estado)}.")
        lineas.append(f"  {len(activas)} de {len(unidades)} unidades en "
                      "ruta · horario " + r.horario + ".")
    return {
        "texto": "\n".join(lineas),
        "sugerencias": [f"Paradas de la {rutas[0].numero}" if rutas else
                        "Paradas de la 117",
                        "¿Hay incidencias reportadas?"],
    }


def _responder_cooperativa(rutas: list) -> dict:
    lineas = []
    for r in rutas[:3]:
        operador = r.cooperativa or "operador no registrado"
        unidades = funciones.unidades_de_ruta(r.id)
        lineas.append(f"La ruta {r.numero} ({r.nombre}) la opera "
                      f"{operador}.")
        lineas.append(f"  Tiene {len(unidades)} unidad(es) y cubre "
                      f"{len(r.paradas_ids)} paradas.")
    return {
        "texto": "\n".join(lineas),
        "sugerencias": [f"Paradas de la {rutas[0].numero}" if rutas else
                        "Paradas de la 117",
                        "¿Cuánto cuesta el pasaje?"],
    }


def _responder_tarifa(rutas: list) -> dict:
    if rutas:
        r = rutas[0]
        return {
            "texto": (f"La ruta {r.numero} ({r.nombre}) cobra el pasaje "
                      "urbano usual de Managua: ~C$2.50 – C$3.00 por "
                      "tramo, en efectivo al subir al bus."),
            "sugerencias": [f"Paradas de la {r.numero}",
                            f"¿Qué cooperativa opera la {r.numero}?"],
        }
    return {
        "texto": ("El pasaje urbano en Managua anda entre C$2.50 y C$3.00 "
                  "por tramo, según la cooperativa. Se paga en efectivo "
                  "al subir (no hay boleto electrónico todavía)."),
        "sugerencias": ["¿Qué rutas pasan por Mercado Mayoreo?",
                        "¿Cómo llego de Mercado Oriental a UCA?"],
    }


def _responder_todas_las_rutas() -> dict:
    ordenadas = funciones.rutas_ordenadas()
    numeros = " · ".join(r.numero for r in ordenadas)
    return {
        "texto": (f"La red de Managua tiene {len(ordenadas)} rutas "
                  f"urbanas:\n{numeros}.\n"
                  "Consultame por cualquiera: sus paradas, estado, "
                  "cooperativa o cómo llegar a algún lugar."),
        "sugerencias": ["Paradas de la 106",
                        "¿Qué cooperativa opera la 117?",
                        "¿Cómo llego de Ciudad Sandino a UCA?"],
    }


def _responder_incidencias() -> dict:
    activas = [i for i in estado.incidencias if not i.resuelta]
    if not activas:
        return {
            "texto": "No hay incidencias activas reportadas en este "
                     "momento. ¡La red está funcionando bien! 🚦",
            "sugerencias": ["¿Qué rutas pasan por el centro?",
                            "Paradas de la 106"],
        }
    lineas = [f"Hay {len(activas)} incidencia(s) activa(s):"]
    for inc in activas[:5]:
        numero = inc.ruta.numero if inc.ruta else "?"
        lineas.append(f"  • {inc.tipo} en la {numero} ({inc.hora}): "
                      f"{inc.descripcion}")
    return {
        "texto": "\n".join(lineas),
        "sugerencias": ["¿Qué rutas pasan por el centro?"],
    }


def _responder_unidades(ruta) -> dict:
    unidades = funciones.unidades_de_ruta(ruta.id)
    activas = [u for u in unidades if u.estado == "en ruta"]
    if not unidades:
        return {"texto": f"La ruta {ruta.numero} no tiene unidades "
                         "registradas.",
                "sugerencias": EJEMPLOS_PREGUNTAS}
    lineas = [f"Unidades de la ruta {ruta.numero}:"]
    for u in unidades:
        parada = funciones.proxima_parada_de(u)
        detalle = f" (hacia {parada.nombre})" if parada else ""
        lineas.append(f"  • {u.placa} — {u.estado}{detalle}")
    if activas:
        u = activas[0]
        lineas.append(f"\n{u.placa} va a {u.velocidad_kmh:.0f} km/h.")
    return {"texto": "\n".join(lineas),
            "sugerencias": [f"¿En qué estado está la {ruta.numero}?",
                            "¿Hay incidencias?"]}


# ---------- Intérprete principal ----------
_PATRON_VIAJE = re.compile(
    r"(?:de|desde)\s+(.+?)\s+(?:a|hasta|para)\s+(.+?)(?:\?|\.|,|$)",
    re.IGNORECASE)


def responder(pregunta: str) -> dict:
    """Interpreta una pregunta y devuelve {'texto': str, 'sugerencias': [..]}"""
    consulta = normalizar(pregunta)
    if not consulta:
        return {
            "texto": "Escribí tu consulta, por ejemplo «¿Qué rutas pasan "
                     "por UCA?».",
            "sugerencias": EJEMPLOS_PREGUNTAS,
        }

    # Saludos, agradecimientos y ayuda
    if any(consulta.startswith(s) or consulta == s for s in SALUDOS):
        return _responder_saludo(consulta)
    if consulta in ("gracias", "gracias!", "gracias."):
        return _responder_saludo(consulta)
    if any(k in consulta for k in ("que puedes", "que sabes hacer",
                                   "ayuda", "help", "comandos",
                                   "que sabes")):
        return _responder_capacidades()

    # Incidencias
    if any(k in consulta for k in ("incidencia", "incidente", "reporte",
                                   "reportaron", "accidente", "accidentes",
                                   "problema en ruta")):
        return _responder_incidencias()

    rutas = rutas_mencionadas(consulta)
    paradas = paradas_mencionadas(consulta)

    # Viaje de A a B («¿Cómo llego de X a Y?», «de X hasta Y»,
    # «qué rutas salen de X para Y»…)
    m = _PATRON_VIAJE.search(consulta)
    if m:
        origen_cand = paradas_mencionadas(m.group(1))
        destino_cand = paradas_mencionadas(m.group(2))
        if origen_cand and destino_cand:
            return _responder_viaje(origen_cand[0], destino_cand[0])

    # Paradas de una ruta («¿por dónde pasa la 115?», «recorrido de…»)
    if rutas and any(k in consulta for k in ("paradas", "recorrido",
                                             "donde para", "itinerario",
                                             "parada", "por donde pasa",
                                             "por donde va", "recorre",
                                             "camino")):
        return _responder_paradas_ruta(rutas[0])

    # Estado de una ruta
    if rutas and any(k in consulta for k in ("estado", "servicio",
                                             "como esta", "retraso",
                                             "suspendid", "normal")):
        return _responder_estado_ruta(rutas)

    # Unidades / ETA
    if rutas and any(k in consulta for k in ("unidad", "unidades", "bus",
                                             "falta", "eta", "donde esta",
                                             "placa")):
        return _responder_unidades(rutas[0])

    # Horarios y frecuencia
    if rutas and any(k in consulta for k in ("horario", "hora", "frecuencia",
                                             "cada cuanto", "abre", "cierra",
                                             "pasa")):
        r = rutas[0]
        activas = [u for u in funciones.unidades_de_ruta(r.id)
                   if u.estado == "en ruta"]
        return {
            "texto": (f"La ruta {r.numero} opera de {r.horario} con buses "
                      f"cada ~{r.frecuencia_min} minutos.\n"
                      f"Estado: {_TEXTO_ESTADO.get(r.estado, r.estado)}. "
                      f"Unidades en ruta: {len(activas)}."),
            "sugerencias": [f"Paradas de la {r.numero}",
                            f"¿En qué estado está la {r.numero}?"],
        }

    # Cooperativa / operador de una ruta
    if rutas and any(k in consulta for k in ("cooperativa", "opera",
                                             "operada", "operan", "empresa",
                                             "quien maneja", "quien la maneja",
                                             "quien la opera")):
        return _responder_cooperativa(rutas)

    # Tarifa / pasaje
    if any(k in consulta for k in ("cuanto cuesta", "cuanto vale", "tarifa",
                                   "pasaje", "boleto", "precio del bus")):
        return _responder_tarifa(rutas)

    # Lista completa de la red («¿qué rutas hay en Managua?»)
    listar_red = (
        any(k in consulta for k in ("todas las rutas", "lista de rutas",
                                    "listado de rutas", "cuantas rutas hay",
                                    "que rutas existen",
                                    "cuales rutas hay"))
        or ("que rutas hay" in consulta
            and "por " not in consulta and "pasan" not in consulta))
    if listar_red and not rutas:
        return _responder_todas_las_rutas()

    # Rutas que pasan por una parada (incluye «estoy en X»)
    if paradas:
        return _responder_rutas_por_paradas(paradas)

    # Ruta mencionada sin intención clara → resumen
    if rutas:
        return _responder_paradas_ruta(rutas[0])

    # Fallback: sugiere paradas parecidas a lo escrito
    sugerencias = list(EJEMPLOS_PREGUNTAS)
    lineas = [f"No entendí «{pregunta.strip()}» 😅"]
    parecidas = sugerencias_parecidas(consulta)
    for p in parecidas:
        lineas.append(f"¿Quisiste decir «{p.nombre}»?")
        sugerencias.insert(0, f"¿Qué rutas pasan por {p.nombre}?")
    lineas.append("Probá preguntar por una parada, una ruta o un viaje de "
                  "un lugar a otro.")
    return {"texto": "\n".join(lineas), "sugerencias": sugerencias[:4]}
