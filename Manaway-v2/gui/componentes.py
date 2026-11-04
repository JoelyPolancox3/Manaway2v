"""Componentes visuales reutilizables de ManaWAY."""
import flet as ft

from modelo.estado import estado
from gui import theme
from gui.theme import (PESO_BOLD, PESO_NORMAL, PESO_SEMIBOLD,
                       RADIO_L, RADIO_M, RADIO_PASTILLA, RADIO_S,
                       TEXTO_L, TEXTO_M, TEXTO_S, TEXTO_XS,
                       color_estado, texto_estado, p)


# ---------- Navegación ----------
def cerrar_sesion(page: ft.Page) -> None:
    """Cierra la sesión y vuelve al inicio de sesión.

    Lo usan los roles que no tienen pantalla de perfil (admin y
    conductor): cierran directo desde el encabezado de sus pantallas.
    """
    estado.cerrar_sesion()
    estado.navegar(page, "/login", limpiar=True)


def app_bar(titulo: str, page: ft.Page, subtitulo: str = None,
            atras: bool = True, acciones: list = None,
            salir: bool = False) -> ft.AppBar:
    paleta = p()
    leading = None
    if atras:
        leading = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=paleta.texto,
            on_click=lambda e: estado.navegar_atras(page),
            tooltip="Volver",
        )
    acciones_finales = list(acciones or [])
    if salir:
        acciones_finales.append(ft.IconButton(
            icon=ft.Icons.LOGOUT_OUTLINED,
            icon_color=paleta.texto,
            on_click=lambda e: cerrar_sesion(page),
            tooltip="Cerrar sesión",
        ))
    titulo_control = ft.Text(
        titulo, size=TEXTO_L, weight=PESO_BOLD, color=paleta.texto,
        no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)
    if subtitulo:
        titulo_control = ft.Column(
            [titulo_control,
             ft.Text(subtitulo, size=TEXTO_XS, color=paleta.texto_sec,
                     no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)],
            spacing=0)
    return ft.AppBar(
        title=titulo_control,
        leading=leading,
        automatically_imply_leading=False,
        bgcolor=paleta.superficie,
        color=paleta.texto,
        elevation=0,
        actions=acciones_finales,
        actions_padding=theme.ESPACIO_S,
        toolbar_height=64,
    )


def barra_inferior(page: ft.Page, ruta_actual: str) -> ft.NavigationBar:
    paleta = p()
    destinos = [
        ("/inicio", ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "Inicio"),
        ("/buscar", ft.Icons.SEARCH, ft.Icons.SEARCH, "Buscar"),
        ("/planificar", ft.Icons.ALT_ROUTE, ft.Icons.ALT_ROUTE, "Viaje"),
        ("/perfil", ft.Icons.PERSON_OUTLINE, ft.Icons.PERSON, "Perfil"),
    ]
    indices = {"inicio": 0, "buscar": 1, "planificar": 2, "perfil": 3}
    clave = ruta_actual.strip("/").split("/")[0]
    seleccionado = indices.get(clave, 0)
    return ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=icono_fuera, selected_icon=icono, label=etiqueta)
            for ruta, icono, icono_fuera, etiqueta in destinos
        ],
        selected_index=seleccionado,
        on_change=lambda e: estado.navegar(
            page, destinos[int(e.control.selected_index)][0]),
        bgcolor=paleta.nav,
        indicator_color=ft.Colors.with_opacity(0.25, paleta.primario),
        elevation=8,
        height=68,
    )


def barra_admin(page: ft.Page, ruta_actual: str) -> ft.NavigationBar:
    """Barra inferior exclusiva del panel de administración.

    Une sus cuatro pantallas independientes: Usuarios, Unidades,
    Rutas e Incidencias. El administrador nunca pasa por la barra
    del viajero.
    """
    paleta = p()
    destinos = [
        ("/gestion", ft.Icons.GROUP_OUTLINED, ft.Icons.GROUP, "Usuarios"),
        ("/gestion/unidades", ft.Icons.DIRECTIONS_BUS_OUTLINED,
         ft.Icons.DIRECTIONS_BUS, "Unidades"),
        ("/gestion/rutas", ft.Icons.MAP_OUTLINED, ft.Icons.MAP, "Rutas"),
        ("/gestion/incidencias", ft.Icons.WARNING_AMBER_OUTLINED,
         ft.Icons.WARNING_AMBER, "Incidencias"),
    ]
    partes = [q for q in ruta_actual.strip("/").split("/") if q]
    if len(partes) > 1:
        clave = partes[1]          # /gestion/<seccion>
    else:
        clave = partes[0] if partes else "gestion"
    indices = {"gestion": 0, "usuarios": 0, "unidades": 1,
               "rutas": 2, "incidencias": 3}
    seleccionado = indices.get(clave, 0)
    return ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=icono_fuera, selected_icon=icono, label=etiqueta)
            for ruta, icono, icono_fuera, etiqueta in destinos
        ],
        selected_index=seleccionado,
        on_change=lambda e: estado.navegar(
            page, destinos[int(e.control.selected_index)][0]),
        bgcolor=paleta.nav,
        indicator_color=ft.Colors.with_opacity(0.25, paleta.primario),
        elevation=8,
        height=68,
    )


# ---------- Superficies ----------
def tarjeta(contenido, on_click=None, padding=theme.ESPACIO_L,
            relleno=None, radio=RADIO_L, borde=True, sombra=True) -> ft.Container:
    paleta = p()
    borde_control = None
    if borde:
        borde_control = ft.Border.all(1, paleta.borde)
    return ft.Container(
        content=contenido,
        padding=padding,
        bgcolor=relleno or paleta.superficie,
        border_radius=radio,
        border=borde_control,
        shadow=paleta.sombra_suave if sombra else None,
        on_click=on_click,
        ink=bool(on_click),
        ink_color=ft.Colors.with_opacity(0.06, paleta.texto),
        width=None,
    )


def boton(texto: str, on_click=None, icono=None, estilo="primario",
          ancho=None, habilitado=True, alto=46) -> ft.Button:
    """estilos: primario | tonal | contorneado | texto | peligro"""
    paleta = p()
    kwargs = {
        "content": ft.Text(texto, size=TEXTO_S, weight=PESO_SEMIBOLD),
        "icon": icono,
        "on_click": on_click,
        "disabled": not habilitado,
        "style": ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=RADIO_M),
            padding=ft.Padding(theme.ESPACIO_L, 10, theme.ESPACIO_L, 10),
        ),
    }
    if estilo == "primario":
        kwargs.update(bgcolor=paleta.primario, color="#FFFFFF", elevation=0)
    elif estilo == "tonal":
        kwargs.update(bgcolor=ft.Colors.with_opacity(0.16, paleta.primario),
                      color=paleta.primario_claro, elevation=0)
    elif estilo == "contorneado":
        kwargs.update(bgcolor="transparent", color=paleta.primario_claro,
                      elevation=0,
                      style=ft.ButtonStyle(
                          shape=ft.RoundedRectangleBorder(radius=RADIO_M),
                          side=ft.BorderSide(1.5, paleta.primario_claro),
                          padding=ft.Padding(theme.ESPACIO_L, 10,
                                             theme.ESPACIO_L, 10)))
    elif estilo == "peligro":
        kwargs.update(bgcolor="transparent", color=paleta.error, elevation=0,
                      style=ft.ButtonStyle(
                          shape=ft.RoundedRectangleBorder(radius=RADIO_M),
                          side=ft.BorderSide(1.5, paleta.error),
                          padding=ft.Padding(theme.ESPACIO_L, 10,
                                             theme.ESPACIO_L, 10)))
    else:  # texto
        kwargs.update(bgcolor="transparent", color=paleta.primario_claro,
                      elevation=0)
    btn = ft.Button(**kwargs)
    if ancho:
        btn.width = ancho
    btn.height = alto
    return btn


def bordes_formulario(radio=RADIO_M) -> dict:
    """Bordes de formulario (normal y con foco) sin usar propiedades obsoletas."""
    paleta = p()
    normal = ft.OutlineInputBorder(
        side=ft.BorderSide(1, paleta.borde),
        border_radius=ft.RoundedRectangleBorder(radius=radio))
    foco = ft.OutlineInputBorder(
        side=ft.BorderSide(1.5, paleta.primario),
        border_radius=ft.RoundedRectangleBorder(radius=radio))
    return {ft.ControlState.FOCUSED: foco, ft.ControlState.DEFAULT: normal}


def campo(label: str, valor: str = "", icono=None, **kwargs) -> ft.TextField:
    paleta = p()
    kwargs.setdefault("text_size", TEXTO_S)
    kwargs.setdefault("color", paleta.texto)
    kwargs.setdefault("filled", True)
    kwargs.setdefault("bgcolor", paleta.superficie_2)
    kwargs.setdefault("border", bordes_formulario())
    kwargs.setdefault("label_style", ft.TextStyle(color=paleta.texto_sec))
    kwargs.setdefault("hint_style", ft.TextStyle(color=paleta.texto_sec))
    kwargs.setdefault("content_padding",
                      ft.Padding(theme.ESPACIO_L, 12, theme.ESPACIO_L, 12))
    return ft.TextField(label=label, value=valor, prefix_icon=icono, **kwargs)


def buscador(page: ft.Page, texto="Buscar rutas, paradas o números…") -> ft.Container:
    """Campo de búsqueda decorativo que navega a la pantalla de búsqueda."""
    paleta = p()
    return ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.SEARCH, color=paleta.texto_sec, size=20),
            ft.Text(texto, size=TEXTO_S, color=paleta.texto_sec),
        ], spacing=theme.ESPACIO_M),
        padding=ft.Padding(theme.ESPACIO_L, 13, theme.ESPACIO_L, 13),
        bgcolor=paleta.superficie_2,
        border_radius=RADIO_M,
        border=ft.Border.all(1, paleta.borde),
        on_click=lambda e: estado.navegar(page, "/buscar"),
        ink=True,
        ink_color=ft.Colors.with_opacity(0.08, paleta.texto),
        url=None,
    )


# ---------- Elementos pequeños ----------
def badge(texto: str, fondo: str, color_texto: str = "#FFFFFF",
          padding=(4, 9)) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto, size=TEXTO_XS, weight=PESO_SEMIBOLD,
                        color=color_texto),
        bgcolor=fondo,
        border_radius=RADIO_PASTILLA,
        padding=ft.Padding(padding[0], 2, padding[1], 2),
    )


def chip_estado(estado_servicio: str) -> ft.Container:
    color = color_estado(estado_servicio)
    return badge(texto_estado(estado_servicio),
                 fondo=ft.Colors.with_opacity(0.18, color),
                 color_texto=color)


def chip(texto: str, icono=None, seleccionado=False, on_click=None) -> ft.Chip:
    paleta = p()
    return ft.Chip(
        label=ft.Text(texto, size=TEXTO_S,
                      weight=PESO_SEMIBOLD if seleccionado else PESO_NORMAL,
                      color=paleta.texto if seleccionado else paleta.texto_sec),
        leading=ft.Icon(icono, size=17, color=paleta.texto if seleccionado
                        else paleta.texto_sec) if icono else None,
        selected=seleccionado,
        on_click=on_click,
        show_checkmark=False,
        selected_color=ft.Colors.with_opacity(0.22, paleta.primario),
        bgcolor=paleta.superficie_2,
        border_side=ft.BorderSide(1, paleta.borde),
        label_padding=ft.Padding(2, 0, 6, 0),
    )


def estrella(es_favorita: bool, on_click=None) -> ft.IconButton:
    paleta = p()
    return ft.IconButton(
        icon=ft.Icons.STAR if es_favorita else ft.Icons.STAR_BORDER,
        icon_color=paleta.acento if es_favorita else paleta.texto_sec,
        selected=es_favorita,
        selected_icon=ft.Icons.STAR,
        selected_icon_color=paleta.acento,
        on_click=on_click,
        tooltip="Favorito",
        icon_size=24,
    )


def avatar(iniciales: str, radio=22, color=None) -> ft.CircleAvatar:
    paleta = p()
    return ft.CircleAvatar(
        content=ft.Text(iniciales, size=TEXTO_S, weight=PESO_BOLD,
                        color="#FFFFFF"),
        bgcolor=color or paleta.primario,
        radius=radio,
    )


def divisor() -> ft.Divider:
    return ft.Divider(height=1, thickness=1, color=p().borde,
                      leading_indent=0, trailing_indent=0)


def seccion_titulo(texto: str, page: ft.Page = None, ruta: str = None,
                   accion: str = None) -> ft.Row:
    paleta = p()
    elementos = [ft.Text(texto, size=TEXTO_M, weight=PESO_BOLD,
                         color=paleta.texto)]
    if accion and ruta:
        elementos.append(ft.TextButton(
            accion,
            style=ft.ButtonStyle(color=paleta.primario_claro,
                                 padding=ft.Padding(4, 0, 4, 0)),
            on_click=lambda e: estado.navegar(page, ruta),
        ))
    return ft.Row(elementos, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                  vertical_alignment=ft.CrossAxisAlignment.CENTER)


def tarjeta_ruta(page: ft.Page, ruta, unidades_activas: int = None,
                 mostrar_estrella: bool = True) -> ft.Container:
    """Tarjeta reutilizable para mostrar una ruta (home, búsqueda, favoritos)."""
    from logica import funciones as fn
    paleta = p()
    if unidades_activas is None:
        unidades_activas = len(fn.unidades_de_ruta(ruta.id, solo_activas=True))

    def alternar_favorito(ev):
        nuevo = estado.alternar_favorito_ruta(ruta.id)
        estado.snack(
            page,
            f"Ruta {ruta.numero} {'añadida a' if nuevo else 'quitada de'} favoritos",
            "exito" if nuevo else "info")

    estrella_ctrl = (estrella(estado.es_favorita_ruta(ruta.id),
                              on_click=alternar_favorito)
                     if mostrar_estrella else None)

    contenido_hijos = [
        ft.Container(
            content=ft.Text(ruta.numero, size=TEXTO_M, weight=PESO_BOLD,
                            color="#0B2A33"),
            width=52, height=52,
            bgcolor=ruta.color,
            border_radius=ft.RoundedRectangleBorder(radius=RADIO_S),
            alignment=ft.Alignment.CENTER,
        ),
        ft.Column([
            ft.Text(ruta.nombre, size=TEXTO_S, weight=PESO_SEMIBOLD,
                    color=paleta.texto, no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS),
            ft.Row([
                ft.Icon(ft.Icons.DIRECTIONS_BUS, size=14,
                        color=paleta.texto_sec),
                ft.Text(f"{unidades_activas} unidades · {ruta.origen} → "
                        f"{ruta.destino}",
                        size=TEXTO_XS, color=paleta.texto_sec, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS, expand=True),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                chip_estado(ruta.estado),
                badge(f"Cada {ruta.frecuencia_min} min",
                      fondo=ft.Colors.with_opacity(0.14, paleta.primario_claro),
                      color_texto=paleta.primario_claro),
            ], spacing=theme.ESPACIO_S),
        ], spacing=4, expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ]
    if estrella_ctrl is not None:
        contenido_hijos.append(estrella_ctrl)
    contenido = ft.Row(contenido_hijos, spacing=theme.ESPACIO_M,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER)

    return tarjeta(
        contenido,
        on_click=lambda e: estado.navegar(page, f"/ruta/{ruta.id}"),
        padding=theme.ESPACIO_M,
    )


def fuerza_clave(clave: str) -> tuple[int, str, str]:
    """Fuerza de una contraseña: (puntos 0-4, etiqueta, color).

    Lo comparten el registro y la recuperación de contraseña para
    mostrar el mismo medidor en ambos formularios.
    """
    if not clave:
        return 0, "", ""
    puntos = 0
    if len(clave) >= 6:
        puntos += 1
    if len(clave) >= 8:
        puntos += 1
    if any(ch.isupper() for ch in clave) and any(ch.islower() for ch in clave):
        puntos += 1
    if any(ch.isdigit() for ch in clave) or not clave.isalnum():
        puntos += 1
    if puntos <= 1:
        return puntos, "Débil", "#F1706E"
    if puntos <= 2:
        return puntos, "Media", "#F2B159"
    return puntos, "Fuerte", "#03C09C"


def estado_vacio(icono: str, titulo: str, mensaje: str,
                 accion_texto: str = None, on_accion=None) -> ft.Container:
    paleta = p()
    controles = [
        ft.Icon(icono, size=44, color=paleta.texto_sec),
        ft.Text(titulo, size=TEXTO_M, weight=PESO_BOLD, color=paleta.texto,
                text_align=ft.TextAlign.CENTER),
        ft.Text(mensaje, size=TEXTO_S, color=paleta.texto_sec,
                text_align=ft.TextAlign.CENTER),
    ]
    if accion_texto:
        controles.append(boton(accion_texto, on_click=on_accion,
                               estilo="tonal"))
    return ft.Container(
        content=ft.Column(controles,
                          alignment=ft.MainAxisAlignment.CENTER,
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          spacing=theme.ESPACIO_M),
        expand=True,
        padding=theme.ESPACIO_XL,
        alignment=ft.Alignment.CENTER,
    )
