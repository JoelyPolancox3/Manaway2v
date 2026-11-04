"""Paleta de colores, espaciados y tipografía de ManaWAY."""
from dataclasses import dataclass

import flet as ft


@dataclass(frozen=True)
class Paleta:
    # Fondos y superficies
    fondo: str
    superficie: str
    superficie_2: str
    borde: str
    # Texto
    texto: str
    texto_sec: str
    # Acentos
    primario: str
    primario_claro: str
    acento: str
    exito: str
    error: str
    advertencia: str
    # Azul profundo del logotipo (identidad ManaWAY)
    profundo: str
    # Barra de navegación
    nav: str

    @property
    def sombra(self) -> list:
        return [ft.BoxShadow(
            color=ft.Colors.with_opacity(0.30, "#000000"),
            blur_radius=18,
            offset=ft.Offset(0, 4),
        )]

    @property
    def sombra_suave(self) -> list:
        return [ft.BoxShadow(
            color=ft.Colors.with_opacity(0.18, "#000000"),
            blur_radius=10,
            offset=ft.Offset(0, 2),
        )]


# Paletas basadas en la Identidad Visual del informe ManaWAY:
#   #243545 fondo · #253544 superficies · #4586A4 botones · #004A75/#4AB3D2
#   azules del logotipo · #03C09C verde menta (flora de Nicaragua).
# Las superficies y bordes son tonos derivados de #243545/#253544 para
# conservar el contraste necesario entre capas.
OSCURA = Paleta(
    fondo="#243545",
    superficie="#2B3D51",
    superficie_2="#33475E",
    borde="#3F5570",
    texto="#EAF1F8",
    texto_sec="#9CB2C9",
    primario="#4586A4",
    primario_claro="#4AB3D2",
    acento="#03C09C",
    exito="#03C09C",
    error="#F1706E",
    advertencia="#F2B159",
    profundo="#004A75",
    nav="#1E2C3B",
)

CLARA = Paleta(
    fondo="#EEF3F8",
    superficie="#FFFFFF",
    superficie_2="#F4F8FC",
    borde="#DCE6F0",
    texto="#16222F",
    texto_sec="#5F7488",
    primario="#4586A4",
    primario_claro="#004A75",
    acento="#028A70",
    exito="#028A70",
    error="#D9524F",
    advertencia="#C9801F",
    profundo="#004A75",
    nav="#FFFFFF",
)

_ACTUAL: Paleta = OSCURA
_NOMBRE_ACTUAL: str = "oscuro"


def fijar_tema(nombre: str) -> None:
    """Cambia la paleta activa ('oscuro' | 'claro')."""
    global _ACTUAL, _NOMBRE_ACTUAL
    _NOMBRE_ACTUAL = "claro" if nombre == "claro" else "oscuro"
    _ACTUAL = CLARA if _NOMBRE_ACTUAL == "claro" else OSCURA


def es_oscuro() -> bool:
    return _NOMBRE_ACTUAL == "oscuro"


def p() -> Paleta:
    """Paleta activa."""
    return _ACTUAL


# ---------- Espaciados ----------
ESPACIO_XS = 4
ESPACIO_S = 8
ESPACIO_M = 12
ESPACIO_L = 16
ESPACIO_XL = 20
ESPACIO_XXL = 24

# ---------- Radios ----------
RADIO_S = 10
RADIO_M = 14
RADIO_L = 18
RADIO_XL = 24
RADIO_PASTILLA = 999

# ---------- Tipografía ----------
# Identidad visual: Rubik SemiBold (texto general) y Alata (logotipo).
FUENTE = "Rubik"
FUENTE_TITULOS = "Alata"

TEXTO_XL = 26
TEXTO_L = 20
TEXTO_M = 16
TEXTO_S = 14
TEXTO_XS = 12
TEXTO_XXS = 11

PESO_NORMAL = ft.FontWeight.W_400
PESO_MEDIO = ft.FontWeight.W_500
PESO_SEMIBOLD = ft.FontWeight.W_600
PESO_BOLD = ft.FontWeight.W_700

# ---------- Colores por estado de servicio ----------
def color_estado(estado: str) -> str:
    paleta = p()
    return {
        "normal": paleta.exito,
        "en ruta": paleta.exito,
        "retraso": paleta.advertencia,
        "mantenimiento": paleta.advertencia,
        "suspendido": paleta.error,
        "fuera de servicio": paleta.error,
    }.get(estado, paleta.texto_sec)


def texto_estado(estado: str) -> str:
    return {
        "normal": "Normal",
        "en ruta": "En ruta",
        "retraso": "Con retraso",
        "mantenimiento": "Mantenimiento",
        "suspendido": "Suspendido",
        "fuera de servicio": "Fuera de servicio",
    }.get(estado, estado.title())
