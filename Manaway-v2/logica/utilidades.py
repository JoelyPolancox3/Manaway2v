"""Utilidades generales: distancias, formatos y colores de estado."""
import math


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en kilómetros entre dos puntos geográficos (haversine)."""
    radio_tierra = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * radio_tierra * math.asin(math.sqrt(a))


def minutos_a_texto(minutos) -> str:
    """Formato amigable para tiempos de llegada."""
    if minutos is None:
        return "—"
    m = int(round(minutos))
    if m <= 0:
        return "Ahora"
    if m == 1:
        return "1 min"
    if m < 60:
        return f"{m} min"
    h, resto = divmod(m, 60)
    return f"{h} h {resto:02d} min"


def nombre_rol(rol: str) -> str:
    return ("Administrador" if rol == "admin"
            else "Conductor" if rol == "conductor"
            else "Viajero")
