"""Pantalla de bienvenida (splash) de ManaWAY."""
import asyncio

import flet as ft

from modelo.estado import estado
from gui import theme
from gui.theme import PESO_BOLD, TEXTO_S, TEXTO_XS, TEXTO_XL, p


def vista_splash(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()

    def _contenido_logo():
        return ft.Container(
            content=ft.Icon(ft.Icons.DIRECTIONS_BUS,
                            size=64, color="#FFFFFF"),
            width=124, height=124,
            bgcolor=paleta.profundo,
            border_radius=ft.RoundedRectangleBorder(radius=32),
            alignment=ft.Alignment.CENTER,
            shadow=paleta.sombra,
        )

    vista = ft.View(
        route="/",
        bgcolor=paleta.fondo,
        padding=theme.ESPACIO_XL,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column([
                ft.AnimatedSwitcher(
                    content=ft.Container(
                        content=_contenido_logo(),
                        key="logo-splash",
                    ),
                    duration=ft.Duration(milliseconds=900),
                    transition=ft.AnimatedSwitcherTransition.SCALE,
                    switch_in_curve=ft.AnimationCurve.EASE_OUT,
                ),
                ft.Text("ManaWAY", size=TEXTO_XL, weight=PESO_BOLD,
                        color=paleta.texto,
                        font_family=theme.FUENTE_TITULOS),
                ft.Text("Muévete por Managua en tiempo real",
                        size=TEXTO_S, color=paleta.texto_sec),
                ft.Container(height=theme.ESPACIO_XXL),
                ft.ProgressRing(width=30, height=30, stroke_width=3,
                                color=paleta.primario),
            ], alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=theme.ESPACIO_L),
            ft.Container(
                content=ft.Text("Datos de demostración · OpenStreetMap",
                                size=TEXTO_XS, color=paleta.texto_sec),
                padding=ft.Padding(0, theme.ESPACIO_XL, 0, 0),
            ),
        ],
    )

    # Salto automático a la siguiente pantalla (cada rol a la suya)
    async def _ir_adelante():
        await asyncio.sleep(2.2)
        if page.route == "/":
            destino = "/login"
            if estado.hay_sesion():
                u = estado.usuario
                destino = ("/gestion" if u and u.es_admin
                           else "/conductor" if u and u.es_conductor
                           else "/inicio")
            estado.historial.clear()
            page.navigate(destino)

    corutina_salto = _ir_adelante()
    try:
        asyncio.create_task(corutina_salto)
    except RuntimeError:
        # Sin event loop (p. ej. en pruebas): descartar la corrutina
        corutina_salto.close()

    return vista
