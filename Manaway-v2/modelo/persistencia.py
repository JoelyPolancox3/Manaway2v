"""Persistencia en JSON dentro de datos_persistidos/ (tolerante a errores)."""
import json
from pathlib import Path
from typing import Optional

from modelo import datos
from modelo.entidades import Usuario

CARPETA = Path(__file__).resolve().parent.parent / "datos_persistidos"
ARCHIVO_USUARIOS = CARPETA / "usuarios.json"
ARCHIVO_SESION = CARPETA / "sesion.json"
ARCHIVO_FAVORITOS = CARPETA / "favoritos.json"
ARCHIVO_PREFERENCIAS = CARPETA / "preferencias.json"
ARCHIVO_INCIDENCIAS = CARPETA / "incidencias.json"


def _leer_json(ruta: Path, defecto):
    try:
        if ruta.exists():
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return defecto


def _escribir_json(ruta: Path, contenido) -> bool:
    try:
        CARPETA.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(contenido, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _usuario_desde_dict(d: dict) -> Usuario:
    """Deserializa un usuario con tolerancia a campos faltantes.

    Los JSON escritos por versiones anteriores no incluyen `unidad_id`:
    en ese caso se usa 0 (sin unidad asignada), sin lanzar excepción.
    """
    try:
        unidad_id = int(d.get("unidad_id", 0) or 0)
    except (TypeError, ValueError):
        unidad_id = 0
    return Usuario(
        id=int(d.get("id", 0)),
        nombre=d.get("nombre", ""),
        usuario=d.get("usuario", ""),
        contrasena=d.get("contrasena", ""),
        rol=d.get("rol", "viajero"),
        correo=d.get("correo", ""),
        telefono=d.get("telefono", ""),
        unidad_id=unidad_id,
    )


def _usuario_a_dict(u: Usuario) -> dict:
    return {
        "id": u.id, "nombre": u.nombre, "usuario": u.usuario,
        "contrasena": u.contrasena, "rol": u.rol,
        "correo": u.correo, "telefono": u.telefono,
        "unidad_id": u.unidad_id,
    }


# ---------- Usuarios ----------
def cargar_usuarios_registrados() -> list[Usuario]:
    registros = _leer_json(ARCHIVO_USUARIOS, [])
    usuarios = []
    for d in registros if isinstance(registros, list) else []:
        try:
            usuarios.append(_usuario_desde_dict(d))
        except Exception:
            continue
    return usuarios


def guardar_usuarios_registrados(usuarios: list[Usuario]) -> bool:
    return _escribir_json(ARCHIVO_USUARIOS, [_usuario_a_dict(u) for u in usuarios])


def siguiente_id_usuario() -> int:
    """Id siguiente considerando la semilla y los registrados."""
    base = datos.siguiente_id_usuario
    registrados = cargar_usuarios_registrados()
    if registrados:
        base = max([base] + [u.id for u in registrados])
    return base + 1


def registrar_usuario(u: Usuario) -> bool:
    registrados = cargar_usuarios_registrados()
    registrados.append(u)
    return guardar_usuarios_registrados(registrados)


def actualizar_usuario(u: Usuario) -> bool:
    """Actualiza un usuario registrado; si era de la semilla, lo clona en el archivo."""
    registrados = cargar_usuarios_registrados()
    for i, existente in enumerate(registrados):
        if existente.id == u.id:
            registrados[i] = u
            return guardar_usuarios_registrados(registrados)
    registrados.append(u)
    return guardar_usuarios_registrados(registrados)


def eliminar_usuario_registrado(usuario_id: int) -> bool:
    """Elimina del archivo a un usuario registrado (CRUD «borrar»).

    Devuelve False si la cuenta no estaba en el archivo (por ejemplo las
    cuentas de la semilla, que viven solo en `datos.py`).
    """
    registrados = cargar_usuarios_registrados()
    restantes = [u for u in registrados if u.id != usuario_id]
    if len(restantes) == len(registrados):
        return False
    return guardar_usuarios_registrados(restantes)


# ---------- Incidencias ----------
# Una incidencia guarda los ids de su ruta y parada (no los objetos):
# al cargar se vuelven a resolver contra los datos en memoria.
def incidencia_a_dict(inc) -> dict:
    return {
        "tipo": inc.tipo,
        "ruta_id": inc.ruta.id if inc.ruta else None,
        "descripcion": inc.descripcion,
        "reportado_por": inc.reportado_por,
        "hora": inc.hora,
        "resuelta": bool(inc.resuelta),
        "parada_id": inc.parada.id if inc.parada else None,
    }


def cargar_incidencias() -> list[dict]:
    """Registros crudos de incidencias (tolerante a campos faltantes)."""
    registros = _leer_json(ARCHIVO_INCIDENCIAS, [])
    salida = []
    for d in registros if isinstance(registros, list) else []:
        if isinstance(d, dict):
            salida.append(d)
    return salida


def guardar_incidencias(registros: list[dict]) -> bool:
    return _escribir_json(ARCHIVO_INCIDENCIAS, registros)


# ---------- Sesión ----------
def guardar_sesion(usuario: str) -> bool:
    return _escribir_json(ARCHIVO_SESION, {"usuario": usuario})


def cargar_sesion() -> Optional[str]:
    datos_sesion = _leer_json(ARCHIVO_SESION, None)
    if isinstance(datos_sesion, dict):
        return datos_sesion.get("usuario")
    return None


def borrar_sesion() -> bool:
    try:
        if ARCHIVO_SESION.exists():
            ARCHIVO_SESION.unlink()
        return True
    except Exception:
        return False


# ---------- Favoritos ----------
def cargar_favoritos(usuario_id: int) -> dict:
    todos = _leer_json(ARCHIVO_FAVORITOS, {})
    if not isinstance(todos, dict):
        return {"rutas": [], "paradas": []}
    fav = todos.get(str(usuario_id), {"rutas": [], "paradas": []})
    return {
        "rutas": list(fav.get("rutas", [])),
        "paradas": list(fav.get("paradas", [])),
    }


def guardar_favoritos(usuario_id: int, rutas_ids, paradas_ids) -> bool:
    todos = _leer_json(ARCHIVO_FAVORITOS, {})
    if not isinstance(todos, dict):
        todos = {}
    todos[str(usuario_id)] = {
        "rutas": sorted(set(int(i) for i in rutas_ids)),
        "paradas": sorted(set(int(i) for i in paradas_ids)),
    }
    return _escribir_json(ARCHIVO_FAVORITOS, todos)


# ---------- Preferencias ----------
def cargar_preferencias() -> dict:
    pref = _leer_json(ARCHIVO_PREFERENCIAS, {})
    if not isinstance(pref, dict):
        pref = {}
    return {
        "tema": pref.get("tema", "oscuro"),
        "recordar_sesion": bool(pref.get("recordar_sesion", True)),
    }


def guardar_preferencias(tema: str, recordar_sesion: bool) -> bool:
    return _escribir_json(ARCHIVO_PREFERENCIAS, {
        "tema": tema,
        "recordar_sesion": bool(recordar_sesion),
    })
