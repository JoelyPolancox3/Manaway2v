from dataclasses import dataclass, field


@dataclass
class Usuario:
    id: int
    nombre: str
    usuario: str
    contrasena: str
    rol: str  # "viajero" | "conductor" | "admin"
    correo: str = ""
    telefono: str = ""
    # Unidad asignada cuando el rol es "conductor" 
    unidad_id: int = 0

    @property
    def iniciales(self) -> str:
        partes = [p for p in self.nombre.strip().split() if p]
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"

    @property
    def es_conductor(self) -> bool:
        return self.rol == "conductor"


@dataclass
class Ruta:
    id: int
    numero: str
    nombre: str
    origen: str
    destino: str
    color: str = "#4AB3D2"
    paradas_ids: list[int] = field(default_factory=list)
    estado: str = "normal"  # "normal" | "retraso" | "suspendido"
    frecuencia_min: int = 8
    horario: str = "05:00 – 21:30"
    # Cooperativa u operador que cubre la ruta (datos reales de Managua)
    cooperativa: str = ""
    # Categoría del mapa oficial de mapanica: "Centro/UCA", "Sur",
    # "Oeste", "Este", "Norte", "Internas" o "Ciudad Sandino"
    categoria: str = ""


@dataclass
class Parada:
    id: int
    nombre: str
    latitud: float
    longitud: float


@dataclass
class Unidad:
    id: int
    ruta_id: int
    placa: str
    latitud: float
    longitud: float
    estado: str = "en ruta"  # "en ruta" | "mantenimiento" | "fuera de servicio"
    velocidad_kmh: float = 22.0
    # Estado de la simulación: parada hacia la que avanza y sentido del recorrido
    indice_parada: int = 0
    sentido: int = 1


# ---------- Entidades compuestas (relaciones anidadas) ----------
@dataclass
class PasoViaje:
    """Un paso de la secuencia de un viaje planificado.

    Entidad compuesta: referencia la Ruta completa a tomar (no solo su
    id), de modo que la GUI y el asistente pueden leer número, color y
    nombre sin consultas adicionales.
    """
    accion: str  # "sube" | "transbordo" | "baja"
    texto: str
    ruta: Ruta


@dataclass
class OpcionViaje:
    """Opción de viaje A→B calculada por el planificador.

    Compuesta por una lista de PasoViaje (relación anidada) más el
    resumen de paradas, minutos y rutas involucradas. Las listas usan
    field(default_factory=...) para que cada opción tenga las suyas.
    """
    tipo: str  # "directa" | "1 transbordo"
    pasos: list[PasoViaje] = field(default_factory=list)
    paradas_total: int = 0
    minutos: float = 0.0
    rutas_ids: list[int] = field(default_factory=list)


@dataclass
class Incidencia:
    """Reporte de un incidente sobre una ruta (entidad compuesta).

    Contiene la Ruta afectada completa y, si el viajero la indicó, la
    Parada exacta donde ocurrió el suceso.
    """
    tipo: str
    ruta: Ruta
    descripcion: str
    reportado_por: str = "anónimo"
    hora: str = ""
    resuelta: bool = False
    parada: Parada | None = None
