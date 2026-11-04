"""Mapa y lista de unidades en vivo."""
import flet as ft
import flet_map as ftm

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import (PESO_BOLD, PESO_SEMIBOLD, TEXTO_S, TEXTO_XS,
                       color_estado, texto_estado, p)
from logica.utilidades import minutos_a_texto

CENTRO_MANAGUA = ftm.MapLatitudeLongitude(12.1364, -86.2514)


def vista_unidades(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    # Filtro inicial por argumento de ruta (/unidades/<ruta_id>)
    if args and args[0].isdigit():
        estado.filtro_unidades = int(args[0])
    filtro = estado.filtro_unidades

    rutas = funciones.listar_rutas()
    ruta_filtrada = funciones.ruta_por_id(filtro) if filtro else None

    opciones = [ft.DropdownOption(key="todas", text="Todas las rutas")]
    for r in rutas:
        opciones.append(ft.DropdownOption(key=str(r.id),
                                          text=f"{r.numero} · {r.nombre}"))
    selector = ft.Dropdown(
        label="Filtrar por ruta",
        value=str(filtro) if filtro else "todas",
        options=opciones,
        text_size=TEXTO_S,
        color=paleta.texto,
        label_style=ft.TextStyle(color=paleta.texto_sec),
        bgcolor=paleta.superficie_2,
        border=c.bordes_formulario(),
        enable_filter=True,
        on_select=lambda e: aplicar_filtro(e.data or e.control.value),
    )

    def aplicar_filtro(clave):
        if clave in (None, "todas"):
            estado.filtro_unidades = None
        else:
            estado.filtro_unidades = int(clave)
        # Reconstruir la vista actual en el sitio, sin tocar el historial
        estado.desregistrar_ticks()
        vista_nueva = vista_unidades(page, [])
        vista_nueva.route = page.route
        page.views[-1] = vista_nueva
        page.update()

    # ----- Unidades visibles -----
    unidades = ([u for u in funciones.listar_unidades()
                 if u.ruta_id == filtro] if filtro
                else funciones.listar_unidades())

    # ----- Mapa -----
    capas = [
        ftm.TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="manaway/2.0",
        ),
        ftm.SimpleAttribution(text="© OpenStreetMap"),
    ]

    rutas_visibles = {u.ruta_id for u in unidades}
    for r in rutas:
        if filtro and r.id != filtro:
            continue
        if not filtro and r.id not in rutas_visibles:
            continue
        paradas = funciones.paradas_de_ruta(r)
        geo = funciones.geometria_de_ruta(r)
        if len(geo) >= 2:
            coordenadas = [ftm.MapLatitudeLongitude(lat, lon)
                           for lat, lon in geo]
            capas.append(ftm.PolylineLayer(polylines=[
                ftm.PolylineMarker(coordinates=coordenadas, color=r.color,
                                   stroke_width=3)
            ]))
            capas.append(ftm.CircleLayer(circles=[
                ftm.CircleMarker(
                    radius=5,
                    coordinates=ftm.MapLatitudeLongitude(
                        *funciones.parada_en_linea(r, p)),
                    color=r.color, border_color="#FFFFFF",
                    border_stroke_width=1.5)
                for p in paradas
            ]))

    marcadores: dict[int, ftm.Marker] = {}
    for u in unidades:
        r = funciones.ruta_por_id(u.ruta_id)
        activa = u.estado == "en ruta"
        marcador = ftm.Marker(
            coordinates=ftm.MapLatitudeLongitude(
                *funciones.unidad_en_linea(u)),
            content=ft.Container(
                content=ft.Icon(
                    ft.Icons.DIRECTIONS_BUS if activa
                    else ft.Icons.BUS_ALERT,
                    size=20, color="#0B2A33"),
                bgcolor=(r.color if r else paleta.primario) if activa
                        else color_estado(u.estado),
                padding=ft.Padding(5, 5, 5, 5),
                border_radius=ft.RoundedRectangleBorder(radius=10),
                border=ft.Border.all(2, "#FFFFFF"),
                shadow=paleta.sombra_suave,
            ),
        )
        marcadores[u.id] = marcador
    if marcadores:
        capas.append(ftm.MarkerLayer(markers=list(marcadores.values())))

    ajuste = None
    if ruta_filtrada:
        paradas = funciones.paradas_de_ruta(ruta_filtrada)
        if paradas:
            lats = [p.latitud for p in paradas]
            lons = [p.longitud for p in paradas]
            ajuste = ftm.CameraFit(bounds=ftm.MapLatitudeLongitudeBounds(
                corner_1=ftm.MapLatitudeLongitude(min(lats), min(lons)),
                corner_2=ftm.MapLatitudeLongitude(max(lats), max(lons)),
            ), padding=55)

    mapa = ftm.Map(
        layers=capas,
        initial_center=CENTRO_MANAGUA,
        initial_zoom=12.5,
        initial_camera_fit=ajuste,
        min_zoom=10,
        max_zoom=17,
        bgcolor=paleta.superficie_2,
        height=300,
    )

    # ----- Lista de unidades -----
    lista = ft.Column(spacing=theme.ESPACIO_S,
                      horizontal_alignment=ft.CrossAxisAlignment.START)
    referencias: dict[int, tuple[ft.Text, ft.Text]] = {}

    def construir_lista():
        lista.controls.clear()
        referencias.clear()
        if not unidades:
            lista.controls.append(c.estado_vacio(
                ft.Icons.DIRECTIONS_BUS, "No hay unidades",
                "No hay unidades registradas con este filtro."))
            return
        for u in unidades:
            r = funciones.ruta_por_id(u.ruta_id)
            proxima = funciones.proxima_parada_de(u)
            eta = funciones.eta_minutos(
                u, proxima.id) if proxima and u.estado == "en ruta" else None
            texto_destino = ft.Text(
                (f"Rumbo a {proxima.nombre}" if proxima else "En mantenimiento")
                + (f" · {minutos_a_texto(eta)}" if eta else ""),
                size=TEXTO_XS, color=paleta.texto_sec)
            texto_estado_ctrl = ft.Text(texto_estado(u.estado), size=TEXTO_XS,
                                        weight=PESO_SEMIBOLD,
                                        color=color_estado(u.estado))
            referencias[u.id] = (texto_destino, texto_estado_ctrl)
            lista.controls.append(
                c.tarjeta(
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.DIRECTIONS_BUS, size=20,
                                            color="#0B2A33"),
                            width=42, height=42,
                            bgcolor=(r.color if r else paleta.primario)
                                    if u.estado == "en ruta"
                                    else color_estado(u.estado),
                            border_radius=ft.RoundedRectangleBorder(radius=12),
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column([
                            ft.Row([
                                ft.Text(u.placa, size=TEXTO_S,
                                        weight=PESO_BOLD, color=paleta.texto),
                                texto_estado_ctrl,
                            ], spacing=theme.ESPACIO_S),
                            ft.Text(f"Ruta {r.numero if r else '—'}",
                                    size=TEXTO_XS, color=paleta.texto_sec),
                            texto_destino,
                        ], spacing=2, expand=True),
                        ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=18,
                                color=paleta.primario_claro),
                    ], spacing=theme.ESPACIO_M,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=theme.ESPACIO_M,
                    on_click=lambda e, uid=u.id: centrar_en(uid),
                ))

    def centrar_en(unidad_id):
        u = funciones.unidad_por_id(unidad_id)
        if not u:
            return
        proxima = funciones.proxima_parada_de(u)
        destino = proxima.nombre if proxima else "—"
        estado.snack(page, f"{u.placa}: rumbo a {destino}", "info")

    construir_lista()

    def al_mover(ev=None):
        if not page.route.startswith("/unidades"):
            return
        for u in unidades:
            marcador = marcadores.get(u.id)
            if marcador is not None:
                marcador.coordinates = ftm.MapLatitudeLongitude(
                    *funciones.unidad_en_linea(u))
            refs = referencias.get(u.id)
            if refs:
                texto_destino, texto_estado_ctrl = refs
                proxima = funciones.proxima_parada_de(u)
                eta = (funciones.eta_minutos(u, proxima.id)
                       if proxima and u.estado == "en ruta" else None)
                texto_destino.value = (
                    (f"Rumbo a {proxima.nombre}" if proxima
                     else "En mantenimiento")
                    + (f" · {minutos_a_texto(eta)}" if eta else ""))
                texto_estado_ctrl.value = texto_estado(u.estado)
                texto_estado_ctrl.color = color_estado(u.estado)
        page.update()

    estado.registrar_tick(al_mover)

    contenido = ft.ListView([
        ft.Column([
            selector,
            mapa,
            c.seccion_titulo(
                f"Unidades ({len(unidades)})"),
            lista,
            ft.Container(height=theme.ESPACIO_XL),
        ], spacing=theme.ESPACIO_M,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True, padding=ft.Padding(0, 0, 0, theme.ESPACIO_L))

    return ft.View(
        route="/unidades",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Unidades en vivo", page,
                         subtitulo=(ruta_filtrada.nombre if ruta_filtrada
                                    else "Todas las rutas")),
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )
