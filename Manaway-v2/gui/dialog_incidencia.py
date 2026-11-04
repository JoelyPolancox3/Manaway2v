"""Formulario modal para reportar una incidencia."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import PESO_BOLD, TEXTO_S, TEXTO_XS, p


def abrir(page: ft.Page, ruta_preseleccionada=None) -> None:
    """Abre el diálogo con el formulario de reporte de incidencias.

    Args:
        page: página actual.
        ruta_preseleccionada: id de la ruta a marcar en el selector
            (por ejemplo al reportar desde el detalle de una ruta).
    """
    paleta = p()

    selector_tipo = ft.Dropdown(
        label="Tipo de incidencia",
        options=[ft.DropdownOption(key=t, text=t)
                 for t in funciones.TIPOS_INCIDENCIA],
        value=funciones.TIPOS_INCIDENCIA[0],
        text_size=TEXTO_S,
        color=paleta.texto,
        bgcolor=paleta.superficie_2,
        border=c.bordes_formulario(),
        label_style=ft.TextStyle(color=paleta.texto_sec),
        menu_width=250,
    )

    selector_ruta = ft.Dropdown(
        label="Ruta afectada",
        options=[ft.DropdownOption(key=str(r.id),
                                   text=f"{r.numero} · {r.nombre}")
                 for r in funciones.listar_rutas()],
        value=str(ruta_preseleccionada) if ruta_preseleccionada else None,
        hint_text="Elegí una ruta…",
        text_size=TEXTO_S,
        color=paleta.texto,
        bgcolor=paleta.superficie_2,
        border=c.bordes_formulario(),
        label_style=ft.TextStyle(color=paleta.texto_sec),
        hint_style=ft.TextStyle(color=paleta.texto_sec),
        menu_width=250,
        on_select=lambda e: (setattr(selector_ruta, "error_text", None),
                             page.update()),
    )

    # Punto de la ruta donde ocurrió (opcional, para marcarlo en el mapa)
    selector_parada = ft.Dropdown(
        label="Punto en la ruta (opcional)",
        options=[],
        value="",
        hint_text="Elegí la parada más cercana…",
        text_size=TEXTO_S,
        color=paleta.texto,
        bgcolor=paleta.superficie_2,
        border=c.bordes_formulario(),
        label_style=ft.TextStyle(color=paleta.texto_sec),
        hint_style=ft.TextStyle(color=paleta.texto_sec),
        menu_width=250,
        disabled=True,
        on_select=lambda e: (setattr(selector_parada, "error_text", None),
                             page.update()),
    )

    def repoblar_paradas(ruta_id):
        """Rellena el selector de paradas según la ruta elegida.

        `funciones.ruta_por_id` ya es defensivo: devuelve None ante ids
        vacíos o no numéricos, sin necesidad de try-except aquí.
        """
        ruta = funciones.ruta_por_id(ruta_id) if ruta_id else None
        paradas = funciones.paradas_de_ruta(ruta) if ruta else []
        selector_parada.options = (
            [ft.DropdownOption(key="",
                               text="Sin parada específica")]
            + [ft.DropdownOption(key=str(p.id), text=p.nombre)
               for p in paradas])
        selector_parada.value = ""
        selector_parada.disabled = not paradas
        if not paradas:
            selector_parada.hint_text = "Elegí primero una ruta…"

    def al_cambiar_ruta(ev):
        repoblar_paradas(ev.control.value)
        selector_ruta.error_text = None
        page.update()

    # En Flet 1.0 el Dropdown expone on_select (no on_change)
    selector_ruta.on_select = al_cambiar_ruta
    repoblar_paradas(selector_ruta.value)

    campo_descripcion = c.campo(
        "Descripción",
        icono=ft.Icons.DESCRIPTION_OUTLINED,
        hint_text="Contá qué pasó y en qué punto de la ruta…",
        max_lines=3,
        min_lines=2,
        on_change=lambda e: (setattr(campo_descripcion, "error", None),
                             page.update()),
    )

    def enviar(ev):
        campo_descripcion.error = None
        selector_ruta.error_text = None
        selector_parada.error_text = None
        incidencia, error = funciones.registrar_incidencia(
            selector_tipo.value,
            selector_ruta.value,
            campo_descripcion.value,
            reportado_por=(estado.usuario.nombre if estado.usuario
                           else "anónimo"),
            parada_id=selector_parada.value,
        )
        if error:
            e = error.lower()
            if "ruta afectada" in e:
                selector_ruta.error_text = error
            elif "parada" in e:
                selector_parada.error_text = error
            else:
                campo_descripcion.error = error
            page.update()
            return
        estado.incidencias.insert(0, incidencia)
        funciones.guardar_incidencias()
        page.pop_dialog()
        ruta = incidencia.ruta
        estado.snack(
            page,
            f"Incidencia «{incidencia.tipo}» reportada en la ruta "
            f"{ruta.numero}.",
            "exito")

    dialogo = ft.AlertDialog(
        modal=True,
        icon=ft.Icon(ft.Icons.FLAG, color=paleta.advertencia, size=28),
        title=ft.Text("Reportar incidencia", size=theme.TEXTO_M,
                      weight=PESO_BOLD, color=paleta.texto,
                      text_align=ft.TextAlign.CENTER),
        content=ft.Container(
            width=330,
            content=ft.Column([
                ft.Text("Ayudanos a mantener el servicio: contanos qué está "
                        "pasando en ruta.",
                        size=TEXTO_XS, color=paleta.texto_sec,
                        text_align=ft.TextAlign.CENTER),
                selector_tipo,
                selector_ruta,
                selector_parada,
                campo_descripcion,
            ], spacing=theme.ESPACIO_L, tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        ),
        actions=[
            c.boton("Cancelar", estilo="texto",
                    on_click=lambda e: page.pop_dialog()),
            c.boton("Enviar reporte", icono=ft.Icons.SEND, on_click=enviar),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=paleta.superficie,
        shape=ft.RoundedRectangleBorder(radius=theme.RADIO_L),
        inset_padding=ft.Padding(20, 0, 20, 0),
    )
    page.show_dialog(dialogo)
