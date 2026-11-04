"""Chat con el asistente local de ManaWAY (IA de reglas, sin internet)."""
import asyncio

import flet as ft

from logica import asistente as ia
from gui import componentes as c
from gui import theme
from gui.theme import TEXTO_S, p


def vista_asistente(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()

    def burbuja(texto: str, es_usuario: bool) -> ft.Row:
        if es_usuario:
            alineacion = ft.MainAxisAlignment.END
            color_fondo = paleta.primario
            color_texto = "#FFFFFF"
        else:
            alineacion = ft.MainAxisAlignment.START
            color_fondo = paleta.superficie_2
            color_texto = paleta.texto
        largo = max((len(l) for l in texto.split("\n")), default=0)
        return ft.Row([
            ft.Container(
                content=ft.Text(texto, size=TEXTO_S, color=color_texto),
                bgcolor=color_fondo,
                padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_S,
                                   theme.ESPACIO_M, theme.ESPACIO_S),
                border_radius=ft.RoundedRectangleBorder(radius=theme.RADIO_L),
                # Tope de ancho: sin él, las respuestas largas se salen
                # del borde derecho de la ventana.
                width=(300 if largo > 36 else None),
            ),
        ], alignment=alineacion)

    filas: list[ft.Row] = [
        burbuja("¡Hola! Soy el asistente de ManaWAY 🚌\n"
                "Preguntame por rutas, paradas o viajes de la red de "
                "Managua.", False),
    ]

    contenedor_chips = ft.Row([], spacing=theme.ESPACIO_S,
                              scroll=ft.ScrollMode.AUTO)

    def actualizar_chips(sugerencias: list):
        contenedor_chips.controls = [
            c.chip(s, icono=ft.Icons.CHEVRON_RIGHT,
                   on_click=lambda e, t=s: enviar(texto_libre=t))
            for s in (sugerencias or ia.EJEMPLOS_PREGUNTAS)[:3]
        ]

    actualizar_chips(ia.EJEMPLOS_PREGUNTAS)

    chat = ft.ListView(filas, spacing=theme.ESPACIO_S, expand=True,
                       padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                                          theme.ESPACIO_L, theme.ESPACIO_M))

    campo = c.campo("Preguntá por rutas, paradas o viajes…",
                    icono=ft.Icons.CHAT_BUBBLE_OUTLINE)

    def enviar(ev=None, texto_libre=None):
        texto = ((texto_libre if texto_libre is not None else campo.value)
                 or "").strip()
        if not texto:
            return
        campo.value = ""
        filas.append(burbuja(texto, True))
        respuesta = ia.responder(texto)
        filas.append(burbuja(respuesta["texto"], False))
        actualizar_chips(respuesta.get("sugerencias"))
        page.update()
        try:
            asyncio.get_running_loop().create_task(
                chat.scroll_to(offset=len(filas) * 120.0, duration=200))
        except Exception:
            pass

    campo.on_submit = enviar

    barra_envio = ft.Row([
        campo,
        ft.Container(
            content=ft.Icon(ft.Icons.SEND, size=20, color="#FFFFFF"),
            width=44, height=44,
            bgcolor=paleta.primario,
            border_radius=ft.RoundedRectangleBorder(radius=22),
            alignment=ft.Alignment.CENTER,
            on_click=enviar,
            tooltip="Enviar pregunta",
        ),
    ], spacing=theme.ESPACIO_S,
        vertical_alignment=ft.CrossAxisAlignment.CENTER)

    contenido = ft.Column([
        chat,
        contenedor_chips,
        ft.Container(height=theme.ESPACIO_XS),
        barra_envio,
        ft.Container(height=theme.ESPACIO_M),
    ], spacing=theme.ESPACIO_S, expand=True)

    return ft.View(
        route="/asistente",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Asistente", page,
                         subtitulo="IA local · funciona sin internet"),
        padding=ft.Padding(0, 0, 0, 0),
        controls=[contenido],
    )
