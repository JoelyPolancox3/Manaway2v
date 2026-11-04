"""Validación defensiva de las entradas del usuario."""
import re

# Patrones de formato
CORREO_RE = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
USUARIO_RE = re.compile(r"[A-Za-z0-9_]+")


def entero_seguro(valor, minimo: int = None,
                  maximo: int = None) -> tuple[int | None, str | None]:
    """Convierte `valor` a entero sin dejar que la app se caiga.

    Protege contra strings vacíos, texto sin sentido, None o tipos
    inesperados que lleguen desde un campo de la interfaz.

    Args:
        valor: entrada cruda del usuario (str, int, None…).
        minimo: cota inferior opcional.
        maximo: cota superior opcional.

    Returns:
        (número, None) si es válido; (None, mensaje) si no.
    """
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None, "Ingresá un número entero válido."
    if minimo is not None and numero < minimo:
        return None, f"El valor mínimo permitido es {minimo}."
    if maximo is not None and numero > maximo:
        return None, f"El valor máximo permitido es {maximo}."
    return numero, None


def texto_minimo(valor, minimo: int,
                 mensaje: str = None) -> tuple[str | None, str | None]:
    """Texto sin espacios extra y con al menos `minimo` caracteres."""
    texto = str(valor).strip() if valor is not None else ""
    if len(texto) < minimo:
        return None, mensaje or f"Ingresá al menos {minimo} caracteres."
    return texto, None


def validar_nombre(nombre) -> tuple[str | None, str | None]:
    """Nombre completo: mínimo 3 caracteres."""
    return texto_minimo(
        nombre, 3, "El nombre debe tener al menos 3 caracteres.")


def validar_usuario(usuario) -> tuple[str | None, str | None]:
    """Nombre de usuario: 3 a 15 caracteres, sin espacios ni símbolos."""
    texto = str(usuario).strip() if usuario is not None else ""
    if not (3 <= len(texto) <= 15) or " " in texto:
        return None, ("El usuario debe tener de 3 a 15 caracteres "
                      "y sin espacios.")
    if not USUARIO_RE.fullmatch(texto):
        return None, ("El usuario solo puede contener letras, números "
                      "y guion bajo.")
    return texto, None


def validar_contrasena(contrasena) -> tuple[str | None, str | None]:
    """Contraseña: mínimo 6 caracteres."""
    clave = str(contrasena) if contrasena is not None else ""
    if len(clave) < 6:
        return None, "La contraseña debe tener al menos 6 caracteres."
    return clave, None


def validar_correo(correo) -> tuple[str | None, str | None]:
    """Correo electrónico opcional con formato usuario@dominio.xx."""
    texto = str(correo).strip() if correo is not None else ""
    if not texto:
        return "", None  # el campo es opcional
    if not CORREO_RE.fullmatch(texto):
        return None, "El correo no tiene un formato válido."
    return texto, None


def validar_telefono(telefono) -> tuple[str | None, str | None]:
    """Teléfono opcional: 7 u 8 dígitos (se ignoran espacios, guiones y paréntesis)."""
    texto = str(telefono).strip() if telefono is not None else ""
    if not texto:
        return "", None  # el campo es opcional
    digitos = re.sub(r"[\s\-()]", "", texto)
    if not digitos.isdigit() or not (7 <= len(digitos) <= 8):
        return None, "El teléfono debe tener 7 u 8 dígitos (ej. 8888-8888)."
    return texto, None
