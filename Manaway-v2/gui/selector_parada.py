"""Selector de parada con buscador en un diálogo (reemplaza al menú nativo)."""
import re
import unicodedata

import flet as ft

from gui import componentes as c
from gui import theme
from gui.theme import PESO_BOLD, PESO_SEMIBOLD, RADIO_M, RADIO_L
from gui.theme import TEXTO_S, TEXTO_XS, p


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", texto.lower()).strip()


class SelectorParada:
    """Campo-selector de paradas. `.control` va en la pantalla; el valor
    se lee con `.parada_id` (int o None) o `.parada` (Parada o None)."""

    def __init__(self, page: ft.Page, etiqueta: str, paradas,
                 valor_id=None):
        self._page = page
        self._paradas = paradas
        self._id = valor_id
        self.etiqueta = etiqueta
        paleta = p()

        self._texto_valor = ft.Text(
            size=TEXTO_S, color=paleta.texto_sec, no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS)

        self.control = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=20,
                        color=paleta.texto_sec),
                ft.Column([
                    ft.Text(etiqueta, size=TEXTO_XS,
                            color=paleta.texto_sec),
                    self._texto_valor,
                ], spacing=1, expand=True),
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, size=20,
                        color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_S,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(theme.ESPACIO_L, 8, theme.ESPACIO_L, 8),
            bgcolor=paleta.superficie_2,
            border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
            border=ft.Border.all(1, paleta.borde),
            on_click=self._abrir,
            ink=True,
            ink_color=ft.Colors.with_opacity(0.08, paleta.texto),
        )
        self._pintar_campo()

    # ----- Valor -----
    @property
    def parada_id(self):
        return self._id

    @property
    def parada(self):
        return next((p_ for p_ in self._paradas
                     if p_.id == self._id), None)

    def definir(self, parada_id):
        self._id = parada_id
        self._pintar_campo()

    def _pintar_campo(self):
        paleta = p()
        parada = self.parada
        self._texto_valor.value = parada.nombre if parada else \
            "Elegí una parada…"
        self._texto_valor.color = paleta.texto if parada else paleta.texto_sec

    # ----- Diálogo con buscador -----
    def _abrir(self, ev=None):
        paleta = p()
        buscador = c.campo("Buscá por nombre…", icono=ft.Icons.SEARCH)
        lista = ft.ListView([], expand=True, spacing=0)

        def pintar_lista(ev_filtro=None):
            consulta = _normalizar(buscador.value or "")
            coincidencias = [p_ for p_ in self._paradas
                             if not consulta
                             or consulta in _normalizar(p_.nombre)]
            lista.controls = [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=18,
                                    color=paleta.primario_claro),
                    title=ft.Text(
                        p_.nombre, size=TEXTO_S,
                        weight=PESO_SEMIBOLD if p_.id == self._id else None,
                        color=paleta.texto),
                    dense=True,
                    on_click=lambda e, pid=p_.id: elegir(pid),
                )
                for p_ in coincidencias[:80]
            ]

        def elegir(pid):
            self._id = pid
            self._pintar_campo()
            self._page.pop_dialog()
            self._page.update()

        buscador.on_change = pintar_lista
        pintar_lista()

        self._page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text(self.etiqueta, size=theme.TEXTO_M,
                          weight=PESO_BOLD, color=paleta.texto),
            content=ft.Container(
                width=330, height=380,
                content=ft.Column([buscador, lista],
                                  spacing=theme.ESPACIO_M, expand=True),
            ),
            actions=[
                c.boton("Cancelar", estilo="texto",
                        on_click=lambda e: self._page.pop_dialog()),
            ],
            bgcolor=paleta.superficie,
            shape=ft.RoundedRectangleBorder(radius=RADIO_L),
            inset_padding=ft.Padding(20, 0, 20, 0),
        ))
