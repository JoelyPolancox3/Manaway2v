"""Lógica: usuarios, rutas, unidades, ETA, planificador e incidencias."""
from dataclasses import replace

import random
import time

from logica import busquedas
from modelo import datos
from logica import ordenamientos
from logica import validaciones
from modelo.entidades import (Incidencia, OpcionViaje, Parada, PasoViaje, Ruta,
                       Unidad, Usuario)
from logica.utilidades import distancia_km

# Velocidad efectiva promedio en ciudad para los cálculos de ETA
VELOCIDAD_EFECTIVA_KMH = 20.0
MINUTOS_POR_PARADA = 2.5
MINUTOS_ESPERA_TRANSBORDO = 4.0


# ---------- Usuarios ----------
ROLES_VALIDOS = ("viajero", "conductor", "admin")
# Cuentas semilla del sistema: no se pueden eliminar desde la app
CUENTAS_SISTEMA = frozenset(u.usuario.lower() for u in datos.usuarios)


def _todos_los_usuarios() -> list[Usuario]:
    """Cuentas de la app: semilla + registradas en disco.

    Clave de combinación: el nombre de usuario en minúsculas. Si una
    cuenta de la semilla fue modificada (rol, contraseña o unidad), su
    copia persistida tiene prioridad, de modo que los cambios del
    administrador y la recuperación de contraseña surtan efecto de
    inmediato y no existan duplicados.
    """
    from modelo import persistencia
    por_cuenta: dict[str, Usuario] = {}
    for u in datos.usuarios:
        por_cuenta[u.usuario.lower()] = u
    for u in persistencia.cargar_usuarios_registrados():
        por_cuenta[u.usuario.lower()] = u
    return sorted(por_cuenta.values(), key=lambda x: x.id)


def listar_usuarios() -> list[Usuario]:
    return _todos_los_usuarios()


def usuario_por_nombre(usuario: str) -> Usuario | None:
    cuenta = str(usuario or "").strip().lower()
    for u in _todos_los_usuarios():
        if u.usuario.lower() == cuenta:
            return u
    return None


def usuario_por_id(usuario_id) -> Usuario | None:
    """Usuario por id con conversión defensiva (nunca lanza excepción)."""
    numero, _ = validaciones.entero_seguro(usuario_id)
    if numero is None:
        return None
    for u in _todos_los_usuarios():
        if u.id == numero:
            return u
    return None


def buscar_por_credenciales(usuario: str, contrasena: str) -> Usuario | None:
    cuenta = str(usuario or "").strip().lower()
    for u in _todos_los_usuarios():
        if u.usuario.lower() == cuenta and u.contrasena == contrasena:
            return u
    return None


def usuario_existe(usuario: str) -> bool:
    cuenta = str(usuario or "").strip().lower()
    return any(u.usuario.lower() == cuenta for u in _todos_los_usuarios())


def correo_existe(correo: str) -> bool:
    texto = str(correo or "").strip().lower()
    return any(u.correo and u.correo.lower() == texto
               for u in _todos_los_usuarios())


def buscar_cuenta(texto: str) -> Usuario | None:
    """Busca una cuenta por su nombre de usuario o por su correo.

    Acepta cualquier texto (usuario o correo), sin mayúsculas forzadas y
    sin excepciones: devuelve None si no encuentra coincidencia.
    """
    clave = str(texto or "").strip().lower()
    if not clave:
        return None
    for u in _todos_los_usuarios():
        if (u.usuario.lower() == clave
                or (u.correo and u.correo.lower() == clave)):
            return u
    return None


def registrar_usuario(nombre: str, usuario: str, contrasena: str,
                      correo: str = "", telefono: str = ""):
    """Registra un usuario nuevo. Devuelve (usuario, None) o (None, error).

    El formato de cada campo se valida con el módulo defensivo
    `validaciones.py`; aquí solo se agregan las reglas 
    (usuarios/correos duplicados y persistencia en disco).
    """
    from modelo import persistencia
    nombre, error = validaciones.validar_nombre(nombre)
    if error:
        return None, error
    usuario, error = validaciones.validar_usuario(usuario)
    if error:
        return None, error
    if usuario_existe(usuario):
        return None, "Ese nombre de usuario ya está en uso."
    contrasena, error = validaciones.validar_contrasena(contrasena)
    if error:
        return None, error
    correo, error = validaciones.validar_correo(correo)
    if error:
        return None, error
    if correo and correo_existe(correo):
        return None, "Ese correo ya está registrado."
    telefono, error = validaciones.validar_telefono(telefono)
    if error:
        return None, error
    nuevo = Usuario(persistencia.siguiente_id_usuario(), nombre, usuario,
                    contrasena, "viajero", correo=correo,
                    telefono=telefono)
    if not persistencia.registrar_usuario(nuevo):
        return None, "No se pudo guardar la cuenta. Intenta de nuevo."
    return nuevo, None


# ---------- CRUD de usuarios (panel de administración) ----------
def _guardar_copia(u: Usuario) -> tuple[Usuario | None, str | None]:
    """Persiste un cambio de cuenta (clona la semilla si hace falta)."""
    from modelo import persistencia
    if persistencia.actualizar_usuario(u):
        return u, None
    return None, "No se pudo guardar el cambio. Intenta de nuevo."


def cambiar_rol_usuario(usuario_id, rol: str) -> tuple[Usuario | None, str | None]:
    """Cambia el rol de una cuenta (CRUD «actualizar»). Devuelve (usuario, error)."""
    u = usuario_por_id(usuario_id)
    if not u:
        return None, "No existe ninguna cuenta con ese identificador."
    if rol not in ROLES_VALIDOS:
        return None, f"Rol inválido: «{rol}»."
    if u.rol == rol:
        return u, None
    if u.es_admin and len([x for x in _todos_los_usuarios()
                           if x.rol == "admin"]) <= 1:
        return None, "No se puede quitar el rol del único administrador."
    return _guardar_copia(replace(u, rol=rol))


def asignar_unidad_conductor(usuario_id,
                             unidad_id) -> tuple[Usuario | None, str | None]:
    """Asigna (o quita con 0) la unidad de trabajo de un conductor.

    Reglas de negocio: solo los conductores manejan unidad y una unidad
    no puede estar asignada a dos conductores a la vez.
    """
    u = usuario_por_id(usuario_id)
    if not u:
        return None, "No existe ninguna cuenta con ese identificador."
    if not u.es_conductor:
        return None, "Solo se puede asignar unidad a cuentas con rol conductor."
    numero, error = validaciones.entero_seguro(unidad_id, minimo=0)
    if error:
        return None, error
    if numero == 0:
        return _guardar_copia(replace(u, unidad_id=0))
    unidad = unidad_por_id(numero)
    if not unidad:
        return None, f"No existe la unidad {numero}."
    for otro in _todos_los_usuarios():
        if otro.id != u.id and otro.unidad_id == unidad.id:
            return None, (f"La unidad {unidad.placa} ya está asignada a "
                          f"{otro.nombre}.")
    return _guardar_copia(replace(u, unidad_id=unidad.id))


def eliminar_usuario(usuario_id) -> tuple[bool, str | None]:
    """Elimina una cuenta registrada (CRUD «borrar»). Devuelve (ok, error)."""
    from modelo import persistencia
    u = usuario_por_id(usuario_id)
    if not u:
        return False, "No existe ninguna cuenta con ese identificador."
    from modelo.estado import estado
    if estado.usuario and estado.usuario.id == u.id:
        return False, "No podés eliminar la cuenta con la que iniciaste sesión."
    if u.usuario.lower() in CUENTAS_SISTEMA:
        return False, ("Cuenta del sistema: puede editarse (rol, unidad o "
                       "contraseña), pero no eliminarse.")
    if (u.rol == "admin" and len([x for x in _todos_los_usuarios()
                                  if x.rol == "admin"]) <= 1):
        return False, "No se puede eliminar el único administrador."
    if not persistencia.eliminar_usuario_registrado(u.id):
        return False, "No se pudo eliminar la cuenta. Intenta de nuevo."
    return True, None


def actualizar_contrasena(usuario_id,
                          nueva_contrasena) -> tuple[Usuario | None, str | None]:
    """Guarda una contraseña nueva validada (CRUD «actualizar»)."""
    u = usuario_por_id(usuario_id)
    if not u:
        return None, "No existe ninguna cuenta con ese identificador."
    clave, error = validaciones.validar_contrasena(nueva_contrasena)
    if error:
        return None, error
    return _guardar_copia(replace(u, contrasena=clave))


def cambiar_contrasena_propia(usuario_id,
                              actual, nueva,
                              confirmar) -> tuple[Usuario | None, str | None]:
    """Cambia la contraseña de la cuenta abierta (CRUD desde el perfil).

    Pide la contraseña actual para demostrar que es la persona quien
    está haciendo el cambio, y aplica las mismas reglas del registro
    (mínimo 6 caracteres) más dos propias: la nueva no puede ser igual
    a la actual y las dos escrituras tienen que coincidir.
    """
    u = usuario_por_id(usuario_id)
    if not u:
        return None, "No existe ninguna cuenta con ese identificador."
    if not actual:
        return None, "Escribe tu contraseña actual."
    if u.contrasena != actual:
        return None, "La contraseña actual no es correcta."
    clave, error = validaciones.validar_contrasena(nueva)
    if error:
        return None, error
    if nueva == actual:
        return None, "La contraseña nueva debe ser distinto a la actual."
    if confirmar is None or nueva != confirmar:
        return None, "La confirmación no coincide con la contraseña nueva."
    return actualizar_contrasena(usuario_id, nueva)


# ---------- Recuperación de contraseña  ----------
# El proyecto es una demostración académica: no hay servidor de correo,
# así que el código se genera aquí y se muestra en pantalla como si se
# hubiera enviado al correo registrado. La vigencia y los intentos se
# controlan igual que en un flujo real.
CODIGOS_RECUPERACION: dict[str, dict] = {}
VIGENCIA_CODIGO_MIN = 10
MAX_INTENTOS_CODIGO = 5


def solicitar_recuperacion(cuenta: str) -> tuple[bool, str | None, str | None]:
    """Paso 1: identifica la cuenta y emite un código de 6 dígitos.

    Acepta el nombre de usuario o el correo electrónico.

    Returns:
        (ok, error, codigo_demo). El código solo se devuelve para poder
        mostrarlo en pantalla: en un sistema real viajaría por correo.
    """
    u = buscar_cuenta(cuenta)
    if not u:
        return False, ("No encontramos ninguna cuenta con ese usuario o "
                       "correo."), None
    codigo = f"{random.randint(0, 999999):06d}"
    CODIGOS_RECUPERACION[u.usuario.lower()] = {
        "codigo": codigo,
        "expira": time.time() + VIGENCIA_CODIGO_MIN * 60,
        "intentos": 0,
    }
    return True, None, codigo


def verificar_codigo(cuenta: str, codigo: str) -> tuple[bool, str | None]:
    """Paso 2: valida el código recibido (formato, vigencia y intentos)."""
    u = buscar_cuenta(cuenta)
    if not u:
        return False, "Solicitá primero el código de recuperación."
    clave = u.usuario.lower()
    registro = CODIGOS_RECUPERACION.get(clave)
    if not registro:
        return False, "Solicitá primero el código de recuperación."
    if time.time() > registro["expira"]:
        CODIGOS_RECUPERACION.pop(clave, None)
        return False, f"El código venció (vigencia de {VIGENCIA_CODIGO_MIN} "\
                      "minutos). Solicitá uno nuevo."
    limpio = str(codigo or "").strip()
    if not limpio.isdigit() or len(limpio) != 6:
        return False, "El código tiene 6 dígitos."
    registro["intentos"] += 1
    if registro["intentos"] > MAX_INTENTOS_CODIGO:
        CODIGOS_RECUPERACION.pop(clave, None)
        return False, "Demasiados intentos fallidos. Solicitá un código nuevo."
    if limpio != registro["codigo"]:
        return False, "El código no coincide. Revisá los 6 dígitos."
    return True, None


def restablecer_contrasena(cuenta: str, codigo: str,
                           nueva_contrasena: str) -> tuple[bool, str | None]:
    """Paso 3: con el código verificado, guarda la contraseña nueva."""
    u = buscar_cuenta(cuenta)
    if not u:
        return False, "La cuenta ya no existe."
    ok, error = verificar_codigo(u.usuario, codigo)
    if not ok:
        return False, error
    _, error = actualizar_contrasena(u.id, nueva_contrasena)
    if error:
        return False, error
    CODIGOS_RECUPERACION.pop(u.usuario.lower(), None)
    return True, None


# ---------- Rutas ----------
def listar_rutas() -> list[Ruta]:
    return list(datos.rutas)


def ruta_por_id(ruta_id: int) -> Ruta | None:
    """Ruta por id usando el índice en diccionario de datos (O(1)).

    Manejo defensivo: devuelve None si el id no existe o si el valor
    recibido no se puede convertir a número (nunca lanza excepción).
    """
    numero, _ = validaciones.entero_seguro(ruta_id)
    if numero is None:
        return None
    return datos.rutas_por_id.get(numero)


def ruta_por_numero(numero: str) -> Ruta | None:
    numero = numero.strip()
    for r in datos.rutas:
        if r.numero == numero:
            return r
    return None


def rutas_ordenadas() -> list[Ruta]:
    """Rutas ordenadas por número: precondición de la búsqueda binaria.

    El orden lo aplica el algoritmo de inserción (ordenamientos.py),
    integrando los algoritmos del curso en el flujo real de la app.
    """
    ordenadas, _ = ordenamientos.ordenar_insercion(
        datos.rutas, clave=lambda r: r.numero)
    return ordenadas


def buscar_rutas(texto: str) -> list[Ruta]:
    texto = texto.lower().strip()
    if not texto:
        return listar_rutas()

    # 1) Coincidencia exacta de número → búsqueda binaria sobre la lista
    #    ordenada de números de ruta (descarta la mitad en cada paso).
    ordenadas = rutas_ordenadas()
    indice, _ = busquedas.busqueda_binaria(
        ordenadas, texto, clave=lambda r: r.numero.lower())
    if indice >= 0:
        return [ordenadas[indice]]

    # 2) Cualquier otro texto (nombre, paradas, origen/destino o número
    #    parcial) → búsqueda lineal elemento por elemento.
    resultados = []
    for r in datos.rutas:
        coincidencias = (
            texto in r.numero.lower()
            or texto in r.nombre.lower()
            or texto in r.origen.lower()
            or texto in r.destino.lower()
            or any(texto in parada_por_id(pid).nombre.lower()
                   for pid in r.paradas_ids if parada_por_id(pid))
        )
        if coincidencias:
            resultados.append(r)
    return resultados


def comparar_busquedas(texto: str) -> dict:
    """Ejecuta búsqueda lineal y binaria sobre el mismo texto.

    Ambos algoritmos se aplican a la lista de rutas ordenada por número,
    comparando el número de forma exacta, para poder comparar la cantidad
    de pasos (comparaciones) que realiza cada uno.
    """
    texto = (texto or "").strip().lower()
    ordenadas = rutas_ordenadas()
    if not texto:
        return {"total": len(ordenadas), "lineal": None, "binaria": None}
    return busquedas.comparar(
        ordenadas, texto, clave=lambda r: r.numero.lower())


# ---------- Ordenamiento de rutas (algoritmos del curso) ----------
# Criterios disponibles en la pantalla de búsqueda: clave de comparación
# y etiqueta visible para cada uno.
CLAVES_ORDEN = {
    "numero": lambda r: r.numero,
    "nombre": lambda r: r.nombre,
    "frecuencia": lambda r: r.frecuencia_min,
    "categoria": lambda r: (r.categoria or "ZZ"),
}
ETIQUETAS_ORDEN = {
    "numero": "Número",
    "nombre": "Nombre",
    "frecuencia": "Frecuencia (min)",
    "categoria": "Categoría",
}


def ordenar_rutas(criterio: str = "numero", algoritmo: str = "insercion",
                  rutas: list[Ruta] = None) -> tuple[list[Ruta], int]:
    """Ordena rutas con un algoritmo clásico del curso.

    Args:
        criterio: clave de CLAVES_ORDEN ("numero", "nombre", ...).
        algoritmo: clave de ordenamientos.ALGORITMOS ("burbuja",
            "insercion" o "seleccion").
        rutas: lista a ordenar; por defecto, toda la red.

    Returns:
        (copia ordenada de la lista, comparaciones realizadas).
    """
    base = list(rutas) if rutas is not None else list(datos.rutas)
    clave = CLAVES_ORDEN.get(criterio, CLAVES_ORDEN["numero"])
    funcion = ordenamientos.ALGORITMOS.get(
        algoritmo, ordenamientos.ordenar_insercion)
    return funcion(base, clave=clave)


def comparar_ordenamientos_rutas(criterio: str = "numero",
                                 rutas: list[Ruta] = None) -> dict:
    """Pasos de burbuja, inserción y selección sobre la misma lista."""
    base = list(rutas) if rutas is not None else list(datos.rutas)
    clave = CLAVES_ORDEN.get(criterio, CLAVES_ORDEN["numero"])
    return ordenamientos.comparar_ordenamientos(base, clave=clave)


def paradas_de_ruta(ruta: Ruta) -> list[Parada]:
    """Paradas de la ruta en orden de recorrido."""
    resultado = []
    for pid in ruta.paradas_ids:
        p = parada_por_id(pid)
        if p:
            resultado.append(p)
    return resultado


def geometria_de_ruta(ruta: Ruta) -> list[tuple[float, float]]:
    """Recorrido real calle por calle de la ruta (OpenStreetMap).

    Usa la geometría de las relaciones route=bus de OSM (la misma
    fuente del mapa de mapanica.net). Si la ruta no existe en OSM,
    devuelve las coordenadas de sus paradas como respaldo.
    """
    geo = datos.geometrias.get(ruta.numero)
    if geo:
        return [(p[0], p[1]) for p in geo["puntos"]]
    return [(p.latitud, p.longitud) for p in paradas_de_ruta(ruta)]


def punto_en_linea(ruta: Ruta, latitud: float,
                   longitud: float) -> tuple[float, float]:
    """Proyecta un punto sobre el recorrido real de la ruta.

    Devuelve el punto más cercano del trazado; sirve para dibujar
    las unidades siempre encima de la línea de su ruta.
    """
    geo = geometria_de_ruta(ruta)
    if not geo:
        return (latitud, longitud)
    return min(geo, key=lambda pt: (pt[0] - latitud) ** 2
               + (pt[1] - longitud) ** 2)


def parada_en_linea(ruta: Ruta, parada: Parada) -> tuple[float, float]:
    """Parada proyectada sobre el trazado real de la ruta.

    Permite dibujar los puntos siempre encima de la línea (estilo
    mapanica.net) sin mover la coordenada lógica de la parada.
    """
    if not datos.geometrias.get(ruta.numero):
        return (parada.latitud, parada.longitud)
    return punto_en_linea(ruta, parada.latitud, parada.longitud)


def unidad_en_linea(unidad: Unidad) -> tuple[float, float]:
    """Posición de la unidad proyectada sobre el trazado de su ruta."""
    r = ruta_por_id(unidad.ruta_id)
    if not r or not datos.geometrias.get(r.numero):
        return (unidad.latitud, unidad.longitud)
    return punto_en_linea(r, unidad.latitud, unidad.longitud)


def incidencia_en_linea(inc: Incidencia) -> tuple[float, float] | None:
    """Ubicación de la incidencia proyectada sobre el trazado de su ruta."""
    punto = ubicacion_incidencia(inc)
    if not punto:
        return None
    r = inc.ruta
    if not r or not datos.geometrias.get(r.numero):
        return punto
    return punto_en_linea(r, punto[0], punto[1])


def unidades_de_ruta(ruta_id: int, solo_activas: bool = False) -> list[Unidad]:
    resultado = []
    for u in datos.unidades:
        if u.ruta_id != int(ruta_id):
            continue
        if solo_activas and u.estado != "en ruta":
            continue
        resultado.append(u)
    return resultado


def cambiar_estado_ruta(ruta_id: int, estado: str) -> bool:
    if estado not in ("normal", "retraso", "suspendido"):
        return False
    r = ruta_por_id(ruta_id)
    if not r:
        return False
    r.estado = estado
    return True


def resumen_servicio() -> dict:
    """Totales para el panel de estado del servicio."""
    unidades_activas = sum(1 for u in datos.unidades if u.estado == "en ruta")
    con_retraso = [r for r in datos.rutas if r.estado == "retraso"]
    suspendidas = [r for r in datos.rutas if r.estado == "suspendido"]
    return {
        "rutas": len(datos.rutas),
        "unidades_activas": unidades_activas,
        "con_retraso": con_retraso,
        "suspendidas": suspendidas,
    }


# ---------- Paradas ----------
def listar_paradas() -> list[Parada]:
    return list(datos.paradas)


def parada_por_id(parada_id: int) -> Parada | None:
    """Parada por id usando el índice en diccionario (O(1), defensivo)."""
    numero, _ = validaciones.entero_seguro(parada_id)
    if numero is None:
        return None
    return datos.paradas_por_id.get(numero)


def rutas_de_parada(parada_id: int) -> list[Ruta]:
    parada_id = int(parada_id)
    return [r for r in datos.rutas if parada_id in r.paradas_ids]


# ---------- Unidades ----------
def listar_unidades() -> list[Unidad]:
    return list(datos.unidades)


def unidad_por_id(unidad_id: int) -> Unidad | None:
    """Unidad por id usando el índice en diccionario (O(1), defensivo)."""
    numero, _ = validaciones.entero_seguro(unidad_id)
    if numero is None:
        return None
    return datos.unidades_por_id.get(numero)


def cambiar_estado_unidad(unidad_id: int, estado: str) -> bool:
    if estado not in ("en ruta", "mantenimiento", "fuera de servicio"):
        return False
    u = unidad_por_id(unidad_id)
    if not u:
        return False
    u.estado = estado
    return True


def _avanzar_hacia_destino(u: Unidad, paradas: list[Parada],
                           paso_horas: float) -> None:
    """Mueve una unidad un paso hacia su parada objetivo (con rebote)."""
    indice = u.indice_parada % len(paradas)
    destino = paradas[indice]
    d = distancia_km(u.latitud, u.longitud, destino.latitud, destino.longitud)
    avance = max(u.velocidad_kmh * paso_horas, 0.001)
    if d <= avance or d == 0:
        # Llega a la parada y avanza hacia la siguiente (con rebote en los extremos)
        u.latitud, u.longitud = destino.latitud, destino.longitud
        if indice + u.sentido >= len(paradas) or indice + u.sentido < 0:
            u.sentido *= -1
        u.indice_parada = indice + u.sentido
    else:
        factor = avance / d
        u.latitud += (destino.latitud - u.latitud) * factor
        u.longitud += (destino.longitud - u.longitud) * factor


def avanzar_unidades(paso_horas: float) -> None:
    """Mueve cada unidad activa hacia su siguiente parada (simulación)."""
    for u in datos.unidades:
        if u.estado != "en ruta":
            continue
        ruta = ruta_por_id(u.ruta_id)
        if not ruta or not ruta.paradas_ids:
            continue
        paradas = paradas_de_ruta(ruta)
        if not paradas:
            continue
        _avanzar_hacia_destino(u, paradas, paso_horas)


def unidad_para_navegacion(ruta) -> tuple[Unidad | None, bool]:
    """Unidad a seguir en el modo navegación: (unidad, ¿es_virtual?).

    Usa la primera unidad activa de la ruta; si la ruta no tiene ninguna
    (mantenimiento o suspendida), crea una unidad virtual que arranca en
    la primera parada para poder simular el recorrido.
    """
    activas = [u for u in unidades_de_ruta(ruta.id)
               if u.estado == "en ruta"]
    if activas:
        return activas[0], False
    paradas = paradas_de_ruta(ruta)
    if not paradas:
        return None, False
    virtual = Unidad(
        id=-1,
        ruta_id=ruta.id,
        placa=f"SIM-{ruta.numero}",
        latitud=paradas[0].latitud,
        longitud=paradas[0].longitud,
        estado="en ruta",
        velocidad_kmh=20.0,
        indice_parada=1 if len(paradas) > 1 else 0,
        sentido=1,
    )
    return virtual, True


def avanzar_unidad_virtual(u: Unidad, paso_horas: float) -> bool:
    """Avanza una unidad que no pertenece a datos.unidades (navegación)."""
    ruta = ruta_por_id(u.ruta_id)
    if not ruta:
        return False
    paradas = paradas_de_ruta(ruta)
    if not paradas:
        return False
    _avanzar_hacia_destino(u, paradas, paso_horas)
    return True


def proxima_parada_de(u: Unidad) -> Parada | None:
    ruta = ruta_por_id(u.ruta_id)
    if not ruta:
        return None
    paradas = paradas_de_ruta(ruta)
    if not paradas:
        return None
    return paradas[u.indice_parada % len(paradas)]


def proximas_paradas_de_unidad(u: Unidad,
                               cantidad: int = 5) -> list[tuple[Parada, int | None]]:
    """Próximas paradas del recorrido de una unidad, con su ETA.

    Lo usa el panel del conductor: parte de la parada hacia la que avanza
    la unidad y toma las siguientes del trazado. Si la unidad no está «en
    ruta», el ETA de cada parada viene None (mantenimiento o fuera de
    servicio).
    """
    ruta = ruta_por_id(u.ruta_id) if u else None
    paradas = paradas_de_ruta(ruta) if ruta else []
    if not paradas:
        return []
    inicio = u.indice_parada % len(paradas)
    return [(paradas[(inicio + i) % len(paradas)],
             eta_minutos(u, paradas[(inicio + i) % len(paradas)].id))
            for i in range(max(1, cantidad))]


# ---------- Tiempos de llegada ----------
def eta_minutos(u: Unidad, parada_id: int) -> int | None:
    """Minutos estimados para que la unidad llegue a la parada."""
    if u.estado != "en ruta":
        return None
    ruta = ruta_por_id(u.ruta_id)
    if not ruta:
        return None
    paradas = paradas_de_ruta(ruta)
    if not paradas:
        return None
    # Distancia desde la posición actual hasta la parada hacia la que avanza
    indice = u.indice_parada % len(paradas)
    sentido = u.sentido if u.sentido in (1, -1) else 1
    total_km = distancia_km(u.latitud, u.longitud,
                            paradas[indice].latitud, paradas[indice].longitud)
    visitados = set()
    for _ in range(len(paradas) * 2):
        actual = paradas[indice]
        if actual.id == int(parada_id):
            minutos = (total_km / VELOCIDAD_EFECTIVA_KMH) * 60
            return max(1, int(round(minutos)))
        if (indice, sentido) in visitados:
            break
        visitados.add((indice, sentido))
        siguiente_indice = indice + sentido
        if siguiente_indice >= len(paradas) or siguiente_indice < 0:
            sentido *= -1
            siguiente_indice = indice + sentido
        siguiente = paradas[siguiente_indice]
        total_km += distancia_km(actual.latitud, actual.longitud,
                                 siguiente.latitud, siguiente.longitud)
        indice = siguiente_indice
    return None


def proximas_llegadas(parada_id: int) -> list[tuple[Unidad, int]]:
    """Unidades rumbo a la parada ordenadas por ETA (incluye rutas distintas)."""
    resultado = []
    for u in datos.unidades:
        ruta = ruta_por_id(u.ruta_id)
        if not ruta or int(parada_id) not in ruta.paradas_ids:
            continue
        minutos = eta_minutos(u, parada_id)
        if minutos is not None:
            resultado.append((u, minutos))
    resultado.sort(key=lambda x: x[1])
    return resultado


# ---------- Incidencias ----------
TIPOS_INCIDENCIA = (
    "Accidente",
    "Desvío",
    "Falla mecánica",
    "Tráfico pesado",
    "Otra",
)


def registrar_incidencia(tipo: str, ruta_id, descripcion: str,
                         reportado_por: str = "",
                         parada_id=None) -> tuple:
    """Valida y crea una incidencia reportada desde el formulario.

    Args:
        parada_id: parada opcional donde ocurrió el suceso (para marcarlo
            en el mapa estilo Waze); si no se indica, la ubicación se
            aproxima al punto medio de la ruta.

    Returns:
        (Incidencia, None) si es válida, o (None, mensaje_de_error).
    """
    from datetime import datetime
    descripcion = (descripcion or "").strip()
    if not tipo or tipo not in TIPOS_INCIDENCIA:
        return None, "Seleccioná el tipo de incidencia."
    # Las conversiones de la entrada usan validaciones.entero_seguro:
    # un id no numérico no lanza excepción, se trata como ausente.
    ruta = None
    if ruta_id not in (None, ""):
        numero_ruta, _ = validaciones.entero_seguro(ruta_id)
        ruta = ruta_por_id(numero_ruta) if numero_ruta is not None else None
    if ruta is None:
        return None, "Seleccioná la ruta afectada."
    if len(descripcion) < 10:
        return None, "Describí el suceso con al menos 10 caracteres."
    parada = None
    if parada_id not in (None, ""):
        numero_parada, _ = validaciones.entero_seguro(parada_id)
        parada = (parada_por_id(numero_parada)
                  if numero_parada is not None else None)
        if parada is None:
            return None, "La parada indicada no existe."
        if parada.id not in ruta.paradas_ids:
            return None, "La parada indicada no pertenece a esa ruta."
    return Incidencia(
        tipo=tipo,
        ruta=ruta,
        descripcion=descripcion,
        reportado_por=reportado_por or "anónimo",
        hora=datetime.now().strftime("%H:%M"),
        resuelta=False,
        parada=parada,
    ), None


def ubicacion_incidencia(inc: Incidencia) -> tuple[float, float] | None:
    """Coordenadas (lat, lon) para marcar la incidencia en el mapa."""
    if inc.parada:
        return inc.parada.latitud, inc.parada.longitud
    paradas = paradas_de_ruta(inc.ruta)
    if paradas:
        p = paradas[len(paradas) // 2]
        return p.latitud, p.longitud
    return None


def incidencias_de_ruta(ruta_id: int,
                        solo_activas: bool = True) -> list[Incidencia]:
    """Incidencias reportadas (en memoria) para una ruta."""
    from modelo.estado import estado
    resultado = []
    for inc in estado.incidencias:
        if inc.ruta.id != ruta_id:
            continue
        if solo_activas and inc.resuelta:
            continue
        resultado.append(inc)
    return resultado


def incidencias_de_usuario(nombre: str) -> list[Incidencia]:
    """Todas las incidencias reportadas por esa persona (panel conductor)."""
    from modelo.estado import estado
    return [inc for inc in estado.incidencias
            if inc.reportado_por == nombre]


def _incidencia_desde_dict(d: dict) -> Incidencia | None:
    """Reconstruye una incidencia desde su registro persistido.

    Devuelve None si la ruta ya no existe (datos de una versión anterior),
    para no romper el arranque con registros huérfanos.
    """
    ruta = ruta_por_id(d.get("ruta_id"))
    if ruta is None:
        return None
    parada = None
    parada_id = d.get("parada_id")
    if parada_id is not None:
        parada = parada_por_id(parada_id)
    return Incidencia(
        tipo=d.get("tipo", "Otra"),
        ruta=ruta,
        descripcion=d.get("descripcion", ""),
        reportado_por=d.get("reportado_por", "anónimo"),
        hora=d.get("hora", ""),
        resuelta=bool(d.get("resuelta", False)),
        parada=parada,
    )


def cargar_incidencias() -> None:
    """Restaura las incidencias guardadas en datos_persistidos/incidencias.json."""
    from modelo import persistencia
    from modelo.estado import estado
    restauradas = []
    for d in persistencia.cargar_incidencias():
        inc = _incidencia_desde_dict(d)
        if inc is not None:
            restauradas.append(inc)
    estado.incidencias = restauradas


def guardar_incidencias() -> bool:
    """Persiste la lista actual de incidencias en el JSON."""
    from modelo import persistencia
    from modelo.estado import estado
    return persistencia.guardar_incidencias(
        [persistencia.incidencia_a_dict(inc) for inc in estado.incidencias])


# ---------- Planificador de viajes ----------
# OpcionViaje y PasoViaje son dataclasses compuestas definidas en
# entidades.py; aquí solo se construyen con los datos del viaje.
def planificar_viaje(origen_id: int, destino_id: int) -> list[OpcionViaje]:
    """Busca viajes de la parada origen a la parada destino.

    Considera rutas directas (en cualquier sentido, ya que las unidades
    recorren el camino de ida y vuelta) y viajes con un transbordo en una
    parada compartida entre dos rutas.
    """
    origen_id, destino_id = int(origen_id), int(destino_id)
    if origen_id == destino_id:
        return []
    opciones = []

    # 1) Rutas directas
    for r in datos.rutas:
        ids = r.paradas_ids
        if origen_id in ids and destino_id in ids:
            paradas_total = abs(ids.index(destino_id) - ids.index(origen_id))
            if paradas_total == 0:
                continue
            opciones.append(OpcionViaje(
                tipo="directa",
                pasos=[
                    PasoViaje(
                        accion="sube",
                        texto=f"Sube a la ruta {r.numero} en "
                              f"{parada_por_id(origen_id).nombre}",
                        ruta=r,
                    ),
                    PasoViaje(
                        accion="baja",
                        texto=f"Baja en {parada_por_id(destino_id).nombre}",
                        ruta=r,
                    ),
                ],
                paradas_total=paradas_total,
                minutos=paradas_total * MINUTOS_POR_PARADA + 1,
                rutas_ids=[r.id],
            ))

    # 2) Viajes con un transbordo
    for r1 in datos.rutas:
        if origen_id not in r1.paradas_ids:
            continue
        i_o = r1.paradas_ids.index(origen_id)
        for r2 in datos.rutas:
            if r2.id == r1.id or destino_id not in r2.paradas_ids:
                continue
            i_d2 = r2.paradas_ids.index(destino_id)
            compartidas = [
                s for s in r1.paradas_ids
                if s in r2.paradas_ids and s not in (origen_id, destino_id)
            ]
            for s in compartidas:
                i_s1 = r1.paradas_ids.index(s)
                i_s2 = r2.paradas_ids.index(s)
                paradas_total = abs(i_s1 - i_o) + abs(i_d2 - i_s2)
                opciones.append(OpcionViaje(
                    tipo="1 transbordo",
                    pasos=[
                        PasoViaje(
                            accion="sube",
                            texto=f"Sube a la ruta {r1.numero} en "
                                  f"{parada_por_id(origen_id).nombre}",
                            ruta=r1,
                        ),
                        PasoViaje(
                            accion="transbordo",
                            texto=f"Baja en {parada_por_id(s).nombre} y toma "
                                  f"la ruta {r2.numero}",
                            ruta=r2,
                        ),
                        PasoViaje(
                            accion="baja",
                            texto=f"Baja en {parada_por_id(destino_id).nombre}",
                            ruta=r2,
                        ),
                    ],
                    paradas_total=paradas_total,
                    minutos=(paradas_total * MINUTOS_POR_PARADA
                             + MINUTOS_ESPERA_TRANSBORDO),
                    rutas_ids=[r1.id, r2.id],
                ))

    # Mejor opción por cada par de rutas, ordenadas por paradas recorridas
    # Primero viajes directos (sin transbordos), luego menos paradas de
    # distancia y después menor tiempo.
    opciones.sort(key=lambda o: (len(o.rutas_ids), o.paradas_total,
                                 o.minutos))
    mejores, vistas = [], set()
    for o in opciones:
        clave = tuple(o.rutas_ids)
        if clave in vistas:
            continue
        vistas.add(clave)
        mejores.append(o)
        if len(mejores) >= 4:
            break
    return mejores
