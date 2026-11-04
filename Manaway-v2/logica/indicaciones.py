"""Generador de indicaciones de navegación a partir del rumbo entre paradas."""
import math

from modelo import datos
from modelo.entidades import Parada, Unidad
from logica.utilidades import distancia_km


def rumbo(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Rumbo geográfico (0–360°, 0 = norte) del punto 1 al punto 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    x = math.sin(delta_lon) * math.cos(phi2)
    y = (math.cos(phi1) * math.sin(phi2)
         - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lon))
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def clasificar_giro(delta_grados: float) -> str:
    """Clasifica la diferencia de rumbos (-180..180) en un tipo de giro."""
    d = (delta_grados + 180.0) % 360.0 - 180.0
    absoluto = abs(d)
    if absoluto < 25:
        return "recto"
    if absoluto > 135:
        return "quiebro"
    return "derecha" if d > 0 else "izquierda"


def _texto_paso(giro: str, metros: int, lugar: str, es_ultimo: bool,
                origen: str = "") -> str:
    if es_ultimo:
        return f"En {metros} m llegás a {lugar}"
    if giro == "inicio":
        return f"Salí de {origen} y continuá {metros} m"
    if giro == "recto":
        return f"Continuá {metros} m hasta {lugar}"
    if giro == "izquierda":
        return f"En {metros} m gira a la izquierda en {lugar}"
    if giro == "derecha":
        return f"En {metros} m gira a la derecha en {lugar}"
    return f"En {metros} m hacé el quiebro en {lugar}"


def _instruccion_corta(giro: str, lugar: str) -> str:
    """Instrucción sin la distancia (para el banner «En X m / …»)."""
    if giro == "inicio":
        return f"continuá hasta {lugar}"
    if giro == "recto":
        return f"continuá recto hasta {lugar}"
    if giro == "izquierda":
        return f"gira a la izquierda en {lugar}"
    if giro == "derecha":
        return f"gira a la derecha en {lugar}"
    if giro == "destino":
        return f"llegás a {lugar}"
    return f"hacé el quiebro en {lugar}"


def generar_indicaciones(paradas: list[Parada],
                         rumbo_inicial: float | None = None) -> list[dict]:
    """Genera los pasos de navegación para una secuencia de paradas.

    Args:
        paradas: secuencia en orden de recorrido.
        rumbo_inicial: rumbo con el que se llega a la primera parada
            (para clasificar el primer giro); si es None el primer paso
            se marca como salida («inicio»).

    Returns:
        Lista de pasos con: indice, distancia_m, giro, lugar y texto.
    """
    pasos = []
    n = len(paradas)
    if n == 0:
        return pasos

    rumbo_previo = rumbo_inicial
    for i in range(n - 1):
        a, b = paradas[i], paradas[i + 1]
        km = distancia_km(a.latitud, a.longitud, b.latitud, b.longitud)
        metros = max(5, int(round(km * 1000)))
        actual = rumbo(a.latitud, a.longitud, b.latitud, b.longitud)
        if rumbo_previo is None:
            giro = "inicio"
        else:
            giro = clasificar_giro(actual - rumbo_previo)
        es_ultimo = (i == n - 2)
        giro_final = "destino" if es_ultimo else giro
        pasos.append({
            "indice": i,
            "distancia_m": metros,
            "giro": giro_final,
            "lugar": b.nombre,
            "texto": _texto_paso(giro_final, metros, b.nombre, es_ultimo,
                                 origen=a.nombre),
            "instruccion": _instruccion_corta(giro_final, b.nombre),
        })
        rumbo_previo = actual
    return pasos


def recorrido_restante(paradas: list[Parada],
                       unidad: Unidad) -> list[Parada]:
    """Paradas que la unidad aún va a visitar (según parada objetivo)."""
    if not paradas:
        return []
    if unidad.sentido == -1:
        indice = min(max(unidad.indice_parada, 0), len(paradas) - 1)
        return list(reversed(paradas[:indice + 1]))
    indice = min(max(unidad.indice_parada, 0), len(paradas) - 1)
    return paradas[indice:]


def indicaciones_para_unidad(paradas: list[Parada],
                             unidad: Unidad) -> list[dict]:
    """Pasos restantes de una unidad: desde su posición hasta el final."""
    restantes = recorrido_restante(paradas, unidad)
    if not restantes:
        return []
    p0 = restantes[0]
    km = distancia_km(unidad.latitud, unidad.longitud,
                      p0.latitud, p0.longitud)
    metros = max(5, int(round(km * 1000)))
    if km <= 0.05:
        # Ya está en (o muy cerca de) la primera parada restante
        return generar_indicaciones(restantes)
    r0 = rumbo(unidad.latitud, unidad.longitud, p0.latitud, p0.longitud)
    pasos = [{
        "indice": -1,
        "distancia_m": metros,
        "giro": "inicio",
        "lugar": p0.nombre,
        "texto": f"Seguí {metros} m hasta {p0.nombre}",
        "instruccion": f"continuá hasta {p0.nombre}",
    }]
    if len(restantes) >= 2:
        pasos.extend(generar_indicaciones(restantes, rumbo_inicial=r0))
    return pasos


def distancia_total(pasos: list[dict]) -> int:
    """Suma de las distancias de los pasos, en metros."""
    return sum(p.get("distancia_m", 0) for p in pasos)


def _geometria_de(unidad: Unidad) -> list[tuple[float, float]]:
    """Trazado real (OSM) de la ruta de la unidad; lista vacía si no hay."""
    for r in datos.rutas:
        if r.id == unidad.ruta_id:
            geo = datos.geometrias.get(r.numero)
            if geo:
                return [(p[0], p[1]) for p in geo["puntos"]]
            break
    return []


def _indice_mas_cerca(geo: list, pt: tuple) -> int:
    return min(range(len(geo)),
               key=lambda k: (geo[k][0] - pt[0]) ** 2
               + (geo[k][1] - pt[1]) ** 2)


def _segmento(geo: list, a: tuple, b: tuple) -> list[tuple]:
    """Puntos del trazado real entre a y b (extremos exactos a y b)."""
    if not geo or a == b:
        return [a] if a == b else [a, b]
    ia, ib = _indice_mas_cerca(geo, a), _indice_mas_cerca(geo, b)
    if ia <= ib:
        seg = geo[ia:ib + 1]
    else:
        seg = list(reversed(geo[ib:ia + 1]))
    if len(seg) >= 2:
        return [a] + seg[1:-1] + [b]
    return [a, b]


def _trazar(geo: list, inicio: tuple, claves: list) -> list[tuple]:
    """Camino desde `inicio` visitando cada clave en orden.

    Con geometría disponible el camino sigue las calles reales; sin
    ella degrada a líneas rectas entre puntos (comportamiento previo).
    """
    salida = [inicio]
    previo = inicio
    for k in claves:
        seg = _segmento(geo, previo, k)
        if salida and seg and seg[0] == salida[-1]:
            seg = seg[1:]
        salida.extend(seg)
        previo = k
    return salida


def trayectoria(paradas: list[Parada],
                unidad: Unidad) -> tuple[list[tuple], list[tuple]]:
    """Divide el recorrido de una unidad en (hecho, pendiente).

    Cada elemento es una tupla (latitud, longitud); la posición actual de
    la unidad aparece como primer punto del tramo pendiente (y como último
    del tramo hecho), de modo que ambas polilíneas se unen en el bus. El
    camino sigue el trazado real de la ruta (OpenStreetMap) siempre que
    esté disponible, no líneas rectas entre paradas.
    """
    if not paradas:
        return [], []
    i = min(max(unidad.indice_parada, 0), len(paradas) - 1)
    pos = (unidad.latitud, unidad.longitud)
    puntos = [(p.latitud, p.longitud) for p in paradas]
    geo = _geometria_de(unidad)
    if unidad.sentido == -1:
        pendientes = _trazar(geo, pos, list(reversed(puntos[:i + 1])))
        hechos = _trazar(geo, pos, puntos[i + 1:])
    else:
        pendientes = _trazar(geo, pos, puntos[i:])
        hechos = ([pos] if i == 0
                  else _trazar(geo, puntos[0], puntos[1:i] + [pos]))
    return hechos, pendientes
