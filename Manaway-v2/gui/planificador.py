"""Planificador de viajes A→B con detección de transbordos."""
import flet as ft
import flet_map as ftm

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import selector_parada
from gui import theme
from gui.theme import PESO_BOLD, RADIO_M, TEXTO_S, TEXTO_XS, p
from logica.utilidades import minutos_a_texto

ICONOS_PASO = {
    "sube": ft.Icons.LOGIN,
    "transbordo": ft.Icons.SWAP_HORIZ,
    "baja": ft.Icons.LOGOUT,
}

CENTRO_MANAGUA = ftm.MapLatitudeLongitude(12.1364, -86.2514)


def _mapa_opciones(opciones, origen, destino, paleta) -> ft.Container:
    """Mapa con los recorridos de todas las opciones + origen/destino."""
    capas = [
        ftm.TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="manaway/2.0",
        ),
        ftm.SimpleAttribution(text="© OpenStreetMap"),
    ]

    # Recorridos de cada opción (la mejor más gruesa); la línea sigue
    # el trazado real de cada ruta descargado de OpenStreetMap
    polilineas = []
    usados = {}   # id de parada → parada, para calcular el encuadre
    lat_geo, lon_geo = [], []
    for i, op in enumerate(opciones):
        grosor = 5 if i == 0 else 3
        for rid in op.rutas_ids:
            r = funciones.ruta_por_id(rid)
            if not r:
                continue
            paradas_r = funciones.paradas_de_ruta(r)
            for par in paradas_r:
                usados.setdefault(par.id, par)
            geo = funciones.geometria_de_ruta(r)
            if len(geo) >= 2:
                lat_geo.extend(pt[0] for pt in geo)
                lon_geo.extend(pt[1] for pt in geo)
                polilineas.append(ftm.PolylineMarker(
                    coordinates=[ftm.MapLatitudeLongitude(pt[0], pt[1])
                                 for pt in geo],
                    color=r.color, stroke_width=grosor))
    for par in (origen, destino):
        usados.setdefault(par.id, par)
    if polilineas:
        capas.append(ftm.PolylineLayer(polylines=polilineas))

    # Marcadores de origen y destino
    def marcador(par, icono, color):
        return ftm.Marker(
            coordinates=ftm.MapLatitudeLongitude(par.latitud, par.longitud),
            content=ft.Container(
                content=ft.Icon(icono, size=14, color="#FFFFFF"),
                bgcolor=color,
                padding=ft.Padding(4, 4, 4, 4),
                border_radius=ft.RoundedRectangleBorder(radius=10),
                border=ft.Border.all(2, "#FFFFFF"),
                shadow=paleta.sombra_suave,
            ),
            alignment=ft.Offset(0, -1.4),
        )
    capas.append(ftm.MarkerLayer(markers=[
        marcador(origen, ft.Icons.LOCATION_ON, "#03C09C"),
        marcador(destino, ft.Icons.FLAG, "#F1706E"),
    ]))

    # Encuadre automático al viaje completo (paradas + geometría real)
    lats = [par.latitud for par in usados.values()] + lat_geo
    lons = [par.longitud for par in usados.values()] + lon_geo
    ajuste = ftm.CameraFit(
        bounds=ftm.MapLatitudeLongitudeBounds(
            corner_1=ftm.MapLatitudeLongitude(min(lats), min(lons)),
            corner_2=ftm.MapLatitudeLongitude(max(lats), max(lons))),
        padding=45)

    mapa = ftm.Map(
        layers=capas,
        initial_center=CENTRO_MANAGUA,
        initial_zoom=12.5,
        initial_camera_fit=ajuste,
        min_zoom=10,
        max_zoom=17,
        bgcolor=paleta.superficie_2,
    )
    return ft.Container(
        content=mapa,
        height=200,
        border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
        border=ft.Border.all(1, paleta.borde),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def vista_planificador(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    # Pantalla del viajero: otros roles vuelven a su interfaz propia.
    u_rol = estado.usuario
    if u_rol and (u_rol.es_admin or u_rol.es_conductor):
        estado.navegar(page, "/gestion" if u_rol.es_admin else "/conductor",
                       limpiar=True)
        return ft.View(route="/planificar", bgcolor=paleta.fondo, controls=[])
    paradas = funciones.listar_paradas()

    sel_origen = selector_parada.SelectorParada(
        page, "Desde", paradas, valor_id=paradas[0].id if paradas else None)
    sel_destino = selector_parada.SelectorParada(page, "Hasta", paradas)

    resultados = ft.Column(spacing=theme.ESPACIO_M,
                           horizontal_alignment=ft.CrossAxisAlignment.START)

    def intercambiar(ev):
        a, b = sel_origen.parada_id, sel_destino.parada_id
        sel_origen.definir(b)
        sel_destino.definir(a)
        page.update()

    def buscar(ev):
        resultados.controls.clear()
        origen, destino = sel_origen.parada, sel_destino.parada
        if not origen or not destino:
            resultados.controls.append(c.estado_vacio(
                ft.Icons.ALT_ROUTE, "Elegí origen y destino",
                "Tocá cada campo y buscá la parada de inicio y la de fin."))
            page.update()
            return
        if origen.id == destino.id:
            resultados.controls.append(c.estado_vacio(
                ft.Icons.REPEAT, "Origen y destino iguales",
                "Elegí paradas diferentes para planificar el viaje."))
            page.update()
            return
        opciones = funciones.planificar_viaje(origen.id, destino.id)
        if not opciones:
            resultados.controls.append(c.estado_vacio(
                ft.Icons.SEARCH_OFF, "Sin rutas disponibles",
                "No encontramos un viaje entre esas paradas. Probá con "
                "paradas de la misma zona."))
            page.update()
            return
        resultados.controls.append(ft.Text(
            f"{len(opciones)} opción(es) · de {origen.nombre} a "
            f"{destino.nombre}", size=TEXTO_S, weight=PESO_BOLD,
            color=paleta.texto))
        resultados.controls.append(_mapa_opciones(opciones, origen, destino,
                                                  paleta))
        for i, op in enumerate(opciones, start=1):
            resultados.controls.append(_tarjeta_opcion(page, op, i, paleta))
        page.update()

    # ----- Tarjeta de selección -----
    seleccion = c.tarjeta(
        ft.Column([
            sel_origen.control,
            ft.Row([
                ft.Container(expand=True, height=1, bgcolor=paleta.borde),
                ft.IconButton(icon=ft.Icons.SWAP_VERT,
                              icon_color=paleta.primario_claro,
                              on_click=intercambiar,
                              tooltip="Intercambiar origen y destino"),
                ft.Container(expand=True, height=1, bgcolor=paleta.borde),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            sel_destino.control,
            c.boton("Buscar viaje", on_click=buscar,
                    icono=ft.Icons.DIRECTIONS, alto=48),
        ], spacing=theme.ESPACIO_M),
        padding=theme.ESPACIO_L,
    )

    contenido = ft.ListView([
        ft.Container(
            content=ft.Column([
                ft.Text("¿A dónde vas?", size=theme.TEXTO_L,
                        weight=PESO_BOLD, color=paleta.texto),
                ft.Text("Elegí el punto de partida y el destino: te "
                        "mostramos las rutas, transbordos y el tiempo "
                        "estimado.", size=TEXTO_S, color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_S),
            padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_L,
                               theme.ESPACIO_L, 0),
        ),
        ft.Container(
            content=seleccion,
            padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                               theme.ESPACIO_L, 0),
        ),
        ft.Container(
            content=resultados,
            padding=ft.Padding(theme.ESPACIO_L, 0, theme.ESPACIO_L,
                               theme.ESPACIO_L),
        ),
    ], spacing=0, expand=True)

    return ft.View(
        route="/planificar",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Planificar viaje", page),
        padding=ft.Padding(0, 0, 0, 0),
        controls=[contenido],
    )


def _tarjeta_opcion(page: ft.Page, op, numero: int, paleta) -> ft.Container:
    pasos_ctrl = []
    for paso in op.pasos:
        r = paso.ruta
        fila = [
            ft.Icon(ICONOS_PASO.get(paso.accion, ft.Icons.CHEVRON_RIGHT),
                    size=18, color=paleta.primario_claro),
            ft.Text(paso.texto, size=TEXTO_S, color=paleta.texto,
                    expand=True),
        ]
        if paso.accion != "baja":
            fila.append(ft.Container(
                content=ft.Text(r.numero, size=TEXTO_XS, weight=PESO_BOLD,
                                color="#0B2A33"),
                bgcolor=r.color,
                padding=ft.Padding(7, 2, 7, 2),
                border_radius=ft.RoundedRectangleBorder(radius=8),
            ))
        pasos_ctrl.append(ft.Row(
            fila, spacing=theme.ESPACIO_S,
            vertical_alignment=ft.CrossAxisAlignment.CENTER))

    filas_rutas = []
    for rid in op.rutas_ids:
        r = funciones.ruta_por_id(rid)
        if r:
            filas_rutas.append(c.chip(f"{r.numero} · {r.origen} → {r.destino}",
                                      icono=ft.Icons.DIRECTIONS_BUS))

    etiqueta_tipo = ("Viaje directo" if op.tipo == "directa"
                     else "1 transbordo")

    botones = []
    for rid in op.rutas_ids:
        r = funciones.ruta_por_id(rid)
        if r:
            botones.append(c.boton(
                f"Ver ruta {r.numero}",
                on_click=lambda e, rid=rid: estado.navegar(page, f"/ruta/{rid}"),
                estilo="tonal"))

    # Quitar Nones de la lista de pasos
    pasos_ctrl = [p for p in pasos_ctrl if p is not None]

    return c.tarjeta(
        ft.Column([
            ft.Row([
                c.badge(etiqueta_tipo, fondo=paleta.primario),
                ft.Text(f"≈ {minutos_a_texto(op.minutos)}",
                        size=TEXTO_S, weight=PESO_BOLD, color=paleta.exito),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(filas_rutas, spacing=theme.ESPACIO_S,
                   scroll=ft.ScrollMode.AUTO),
            ft.Divider(height=1, color=paleta.borde),
            ft.Column(pasos_ctrl, spacing=theme.ESPACIO_S),
            ft.Text(f"{op.paradas_total} paradas de distancia",
                    size=TEXTO_XS, color=paleta.texto_sec),
            ft.Row(botones, spacing=theme.ESPACIO_S),
        ], spacing=theme.ESPACIO_S),
        padding=theme.ESPACIO_L,
    )
