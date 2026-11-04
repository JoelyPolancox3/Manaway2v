"""Detalle de ruta: mapa con recorrido, paradas, unidades en vivo y ETA."""
import flet as ft
import flet_map as ftm

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import dialog_incidencia
from gui import theme
from gui.theme import (PESO_BOLD, PESO_SEMIBOLD, RADIO_M, TEXTO_S, TEXTO_XS,
                       color_estado, texto_estado, p)
from logica.utilidades import minutos_a_texto

CENTRO_MANAGUA = ftm.MapLatitudeLongitude(12.1364, -86.2514)


def _crear_mapa(ruta, paradas, unidades, paleta):
    """Crea el mapa de la ruta con polilínea, paradas y unidades."""
    capas = [
        ftm.TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="manaway/2.0",
        ),
        ftm.SimpleAttribution(text="© OpenStreetMap"),
    ]

    # Recorrido (geometría real calle por calle de OSM)
    geo = funciones.geometria_de_ruta(ruta)
    if len(geo) >= 2:
        coordenadas = [ftm.MapLatitudeLongitude(lat, lon)
                       for lat, lon in geo]
        capas.append(ftm.PolylineLayer(polylines=[
            ftm.PolylineMarker(coordinates=coordenadas, color=ruta.color,
                               stroke_width=4)
        ]))
        # Ajuste automático al recorrido
        lats = [pt[0] for pt in geo]
        lons = [pt[1] for pt in geo]
        ajuste = ftm.CameraFit(bounds=ftm.MapLatitudeLongitudeBounds(
            corner_1=ftm.MapLatitudeLongitude(min(lats), min(lons)),
            corner_2=ftm.MapLatitudeLongitude(max(lats), max(lons)),
        ), padding=55)
    else:
        ajuste = None

    # Paradas (proyectadas sobre el trazado: puntos siempre sobre la línea)
    capas.append(ftm.CircleLayer(circles=[
        ftm.CircleMarker(radius=7, coordinates=
                         ftm.MapLatitudeLongitude(
                             *funciones.parada_en_linea(ruta, p)),
                         color=ruta.color, border_color="#FFFFFF",
                         border_stroke_width=2)
        for p in paradas
    ]))

    # Nombres de origen y destino
    etiquetas = []
    if paradas:
        for p in (paradas[0], paradas[-1]):
            if p is paradas[0] and paradas and paradas[0] is paradas[-1]:
                continue
            etiquetas.append(ftm.Marker(
                coordinates=ftm.MapLatitudeLongitude(
                    *funciones.parada_en_linea(ruta, p)),
                content=ft.Container(
                    content=ft.Text(p.nombre, size=11,
                                    weight=PESO_SEMIBOLD, color="#FFFFFF"),
                    bgcolor=paleta.superficie,
                    padding=ft.Padding(8, 3, 8, 3),
                    border_radius=ft.RoundedRectangleBorder(radius=8),
                    shadow=paleta.sombra_suave,
                ),
                alignment=ft.Offset(0, -2.4),
            ))
    if etiquetas:
        capas.append(ftm.MarkerLayer(markers=etiquetas))

    # Unidades
    marcadores = {}
    for u in unidades:
        marcador = ftm.Marker(
            coordinates=ftm.MapLatitudeLongitude(
                *funciones.unidad_en_linea(u)),
            content=ft.Container(
                content=ft.Icon(ft.Icons.DIRECTIONS_BUS, size=20,
                                color="#0B2A33"),
                bgcolor=ruta.color,
                padding=ft.Padding(5, 5, 5, 5),
                border_radius=ft.RoundedRectangleBorder(radius=10),
                border=ft.Border.all(2, "#FFFFFF"),
                shadow=paleta.sombra_suave,
            ),
        )
        marcadores[u.id] = marcador
    if marcadores:
        capas.append(ftm.MarkerLayer(markers=list(marcadores.values())))

    mapa = ftm.Map(
        layers=capas,
        initial_center=CENTRO_MANAGUA,
        initial_zoom=12.5,
        initial_camera_fit=ajuste,
        min_zoom=10,
        max_zoom=17,
        bgcolor=paleta.superficie_2,
        height=290,
    )
    return mapa, marcadores


def vista_detalle_ruta(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    ruta_id = int(args[0]) if args else None
    ruta = funciones.ruta_por_id(ruta_id)
    if not ruta:
        return ft.View(
            route=page.route,
            bgcolor=paleta.fondo,
            appbar=c.app_bar("Ruta no encontrada", page),
            controls=[c.estado_vacio(ft.Icons.ERROR_OUTLINE,
                                     "Ruta no encontrada",
                                     "Puede que haya sido eliminada.",
                                     accion_texto="Volver al inicio",
                                     on_accion=lambda e: estado.navegar(
                                         page, "/inicio", limpiar=True))],
        )

    paradas = funciones.paradas_de_ruta(ruta)
    unidades = funciones.unidades_de_ruta(ruta.id)

    # ----- Mapa y referencias de actualización en vivo -----
    mapa, marcadores_unidad = _crear_mapa(ruta, paradas, unidades, paleta)
    textos_llegadas: dict[int, list[ft.Text]] = {}

    def al_mover(ev=None):
        if page.route != f"/ruta/{ruta.id}":
            return
        # Posiciones de unidades en el mapa
        for u in unidades:
            marcador = marcadores_unidad.get(u.id)
            if marcador is not None:
                marcador.coordinates = ftm.MapLatitudeLongitude(
                    *funciones.unidad_en_linea(u))
        # ETA por parada
        for p in paradas:
            llegadas = funciones.proximas_llegadas(p.id)
            textos = textos_llegadas.get(p.id, [])
            for i, texto in enumerate(textos):
                if i < len(llegadas):
                    u, minutos = llegadas[i]
                    texto.value = f"{u.placa} · {minutos_a_texto(minutos)}"
                    texto.color = paleta.texto
                else:
                    texto.value = "—"
                    texto.color = paleta.texto_sec
        page.update()

    estado.registrar_tick(al_mover)

    # ----- Encabezado de información -----
    unidades_activas = len([u for u in unidades if u.estado == "en ruta"])
    info = ft.Row([
        _info_card(ft.Icons.DIRECTIONS_BUS, str(unidades_activas), "Unidades"),
        _info_card(ft.Icons.STOP_CIRCLE_OUTLINED, str(len(paradas)), "Paradas"),
        _info_card(ft.Icons.SCHEDULE, f"{ruta.frecuencia_min} min", "Frecuencia"),
        _info_card(ft.Icons.ACCESS_TIME, ruta.horario.split(" – ")[0], "Salida"),
    ], spacing=theme.ESPACIO_S)

    # ----- Estado del servicio -----
    def cambiar_estado(nombre_estado):
        def handler(ev):
            funciones.cambiar_estado_ruta(ruta.id, nombre_estado)
            for clave, chip_ctrl in chips_estado.items():
                chip_ctrl.selected = clave == nombre_estado
            estado.snack(page,
                         f"Ruta {ruta.numero}: estado «{texto_estado(nombre_estado)}»",
                         "exito" if nombre_estado == "normal" else "aviso")
        return handler

    chips_estado = {}
    fila_estado = []
    for clave in ("normal", "retraso", "suspendido"):
        chip_ctrl = c.chip(texto_estado(clave), seleccionado=(ruta.estado == clave))
        chips_estado[clave] = chip_ctrl
        fila_estado.append(chip_ctrl)

    fila_estado[0].on_click = cambiar_estado("normal")
    fila_estado[1].on_click = cambiar_estado("retraso")
    fila_estado[2].on_click = cambiar_estado("suspendido")

    elementos_estado = [
        ft.Row([
            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, size=18,
                    color=color_estado(ruta.estado)),
            ft.Text("Estado del servicio", size=TEXTO_S,
                    weight=PESO_SEMIBOLD, color=paleta.texto),
        ], spacing=theme.ESPACIO_S),
        ft.Row(fila_estado, spacing=theme.ESPACIO_S,
               scroll=ft.ScrollMode.AUTO),
    ]
    if estado.usuario and estado.usuario.es_admin:
        elementos_estado.append(
            ft.Text("Como administrador podés cambiar el estado de la ruta.",
                    size=TEXTO_XS, color=paleta.texto_sec))

    tarjeta_estado = c.tarjeta(
        ft.Column(elementos_estado, spacing=theme.ESPACIO_S),
        padding=theme.ESPACIO_M,
    )

    # ----- Próximas llegadas por parada -----
    filas_paradas = []
    for idx, par in enumerate(paradas):
        llegadas = funciones.proximas_llegadas(par.id)
        textos = []
        mini_lista = []
        for i in range(2):
            if i < len(llegadas):
                u, minutos = llegadas[i]
                valor, color = f"{u.placa} · {minutos_a_texto(minutos)}", paleta.texto
            else:
                valor, color = "—", paleta.texto_sec
            texto_ctrl = ft.Text(valor, size=TEXTO_XS, color=color,
                                 weight=PESO_SEMIBOLD)
            textos.append(texto_ctrl)
            mini_lista.append(texto_ctrl)
        textos_llegadas[par.id] = textos

        etiqueta = ("Inicio" if idx == 0 else
                    "Fin" if idx == len(paradas) - 1 else
                    f"Parada {idx}")
        def alternar_parada(pid=par.id):
            def handler(ev):
                nuevo = estado.alternar_favorito_parada(pid)
                estado.snack(
                    page,
                    f"Parada «{funciones.parada_por_id(pid).nombre}» "
                    f"{'añadida a' if nuevo else 'quitada de'} favoritos",
                    "exito" if nuevo else "info")
            return handler

        filas_paradas.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(str(idx + 1), size=TEXTO_XS,
                                        weight=PESO_BOLD, color="#0B2A33"),
                        width=28, height=28,
                        bgcolor=ruta.color,
                        border_radius=ft.RoundedRectangleBorder(radius=14),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(par.nombre, size=TEXTO_S, weight=PESO_SEMIBOLD,
                                color=paleta.texto),
                        ft.Row(mini_lista, spacing=theme.ESPACIO_S),
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=(ft.Icons.STAR if estado.es_favorita_parada(par.id)
                              else ft.Icons.STAR_BORDER),
                        icon_size=20,
                        icon_color=(paleta.acento if estado.es_favorita_parada(par.id)
                                    else paleta.texto_sec),
                        on_click=alternar_parada(),
                        tooltip="Favorito",
                    ),
                ], spacing=theme.ESPACIO_M,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_M,
                bgcolor=paleta.superficie,
                border_radius=RADIO_M,
                border=ft.Border.all(1, paleta.borde),
            ))

    # ----- Acciones -----
    acciones_fila = ft.Row([
        c.boton("Navegar", on_click=lambda e: estado.navegar(
            page, f"/navegar/{ruta.id}"),
            icono=ft.Icons.NAVIGATION, estilo="primario"),
        c.boton("Ver unidades", on_click=lambda e: (
            setattr(estado, "filtro_unidades", ruta.id),
            estado.navegar(page, f"/unidades/{ruta.id}")),
            icono=ft.Icons.MAP_OUTLINED, estilo="tonal", ancho=None),
        c.boton("Favorito" if not estado.es_favorita_ruta(ruta.id) else "Quitar favorito",
                on_click=lambda e: (estado.alternar_favorito_ruta(ruta.id),
                                    estado.navegar(page, f"/ruta/{ruta.id}")),
                icono=ft.Icons.STAR_BORDER, estilo="contorneado"),
    ], spacing=theme.ESPACIO_S, scroll=ft.ScrollMode.AUTO)

    contenido = ft.ListView([
        ft.Column([
            mapa,
            ft.Container(height=theme.ESPACIO_XS),
            info,
            tarjeta_estado,
            c.seccion_titulo("Recorrido y próximas llegadas"),
            ft.Column(filas_paradas, spacing=theme.ESPACIO_S),
            acciones_fila,
            ft.Container(height=theme.ESPACIO_XL),
        ], spacing=theme.ESPACIO_M,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True, padding=ft.Padding(0, 0, 0, theme.ESPACIO_L),
        scroll=ft.Scrollbar(thumb_visibility=True, track_visibility=True,
                            thickness=4, radius=8))

    estrella_ctrl = c.estrella(
        estado.es_favorita_ruta(ruta.id),
        on_click=lambda e: (estado.alternar_favorito_ruta(ruta.id),
                            estado.navegar(page, f"/ruta/{ruta.id}")))

    reportar_ctrl = ft.IconButton(
        icon=ft.Icons.FLAG_OUTLINED,
        icon_color=paleta.texto,
        on_click=lambda e: dialog_incidencia.abrir(
            page, ruta_preseleccionada=ruta.id),
        tooltip="Reportar incidencia en esta ruta",
    )

    return ft.View(
        route=f"/ruta/{ruta.id}",
        bgcolor=paleta.fondo,
        appbar=c.app_bar(f"Ruta {ruta.numero}", page,
                         subtitulo=ruta.nombre,
                         acciones=[reportar_ctrl, estrella_ctrl]),
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )


def _info_card(icono: str, valor: str, etiqueta: str) -> ft.Container:
    paleta = p()
    return ft.Container(
        content=ft.Column([
            ft.Icon(icono, size=17, color=paleta.primario_claro),
            ft.Text(valor, size=TEXTO_S, weight=PESO_BOLD, color=paleta.texto,
                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(etiqueta, size=TEXTO_XS, color=paleta.texto_sec),
        ], spacing=1, horizontal_alignment=ft.CrossAxisAlignment.START),
        padding=theme.ESPACIO_M,
        bgcolor=paleta.superficie,
        border_radius=RADIO_M,
        border=ft.Border.all(1, paleta.borde),
        expand=True,
    )
