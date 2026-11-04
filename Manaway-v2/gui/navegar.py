"""Navegación de una ruta con indicaciones estilo Waze en tiempo real."""
import asyncio
from datetime import datetime, timedelta

import flet as ft
import flet_map as ftm

from logica import funciones
from logica import indicaciones as ind
from modelo.estado import estado, SEGUNDOS_POR_TICK
from gui import componentes as c
from gui import theme
from gui.theme import (PESO_BOLD, PESO_SEMIBOLD, TEXTO_S, TEXTO_XS,
                       p)
from logica.utilidades import minutos_a_texto

ZOOM_SEGUIMIENTO = 15.5

# Fondo fijo estilo Waze (siempre oscuro, aun en tema claro)
FONDO_BANNER = "#16222E"

ICONOS_GIRO = {
    "inicio": ft.Icons.LOCATION_ON_OUTLINED,
    "recto": ft.Icons.STRAIGHT,
    "derecha": ft.Icons.TURN_RIGHT,
    "izquierda": ft.Icons.TURN_LEFT,
    "quiebro": ft.Icons.SUBDIRECTORY_ARROW_RIGHT,
    "destino": ft.Icons.FLAG,
}

COLORES_GIRO = {
    "inicio": "#4AB3D2",
    "recto": "#8FB3C7",
    "derecha": "#F2B159",
    "izquierda": "#4AB3D2",
    "quiebro": "#F1706E",
    "destino": "#03C09C",
}


def _proyectar_unidad(ruta, unidad, hechos, pendientes):
    """Une los trazos y el icono a la unidad proyectada sobre la línea.

    `indicaciones.trayectoria()` devuelve los trazos terminando en la
    posición lógica (y a veces lejos) de la unidad; aquí se recoloca
    esa punta sobre el trazado real para que el icono quede siempre
    encima de la línea. Devuelve la posición proyectada.
    """
    u_xy = funciones.punto_en_linea(ruta, unidad.latitud, unidad.longitud)
    crudo = (unidad.latitud, unidad.longitud)
    if hechos:
        if tuple(hechos[-1]) == crudo:
            hechos[-1] = u_xy
        elif tuple(hechos[0]) == crudo:
            hechos[0] = u_xy
    if pendientes and tuple(pendientes[0]) == crudo:
        pendientes[0] = u_xy
    return u_xy


def _crear_mapa(ruta, paradas, unidad, paleta, incidencias):
    """Mapa de navegación: recorrido hecho y pendiente sobre las calles."""
    capas = [
        ftm.TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="manaway/2.0",
        ),
        ftm.SimpleAttribution(text="© OpenStreetMap"),
    ]

    # Recorrido: hecho (tenue) y pendiente (color de la ruta); ambos
    # siguen el trazado real de la ruta descargado de OpenStreetMap
    hechos, pendientes = ind.trayectoria(paradas, unidad)
    u_xy = _proyectar_unidad(ruta, unidad, hechos, pendientes)
    poly_hecho = ftm.PolylineMarker(
        coordinates=[ftm.MapLatitudeLongitude(*pt) for pt in hechos]
        if len(hechos) >= 2 else [],
        color="#93A7BB", stroke_width=5)
    poly_pendiente = ftm.PolylineMarker(
        coordinates=[ftm.MapLatitudeLongitude(*pt) for pt in pendientes]
        if len(pendientes) >= 2 else [],
        color=ruta.color, stroke_width=6,
        border_color="#FFFFFF", border_stroke_width=2)
    capas.append(ftm.PolylineLayer(polylines=[poly_hecho, poly_pendiente]))

    # Paradas
    capas.append(ftm.CircleLayer(circles=[
        ftm.CircleMarker(radius=6,
                         coordinates=ftm.MapLatitudeLongitude(
                             *funciones.parada_en_linea(ruta, p)),
                         color=ruta.color, border_color="#FFFFFF",
                         border_stroke_width=2)
        for p in paradas
    ]))

    # Incidencias reportadas en esta ruta (estilo Waze)
    marcas_inc = []
    for inc in incidencias:
        punto = funciones.incidencia_en_linea(inc)
        if not punto:
            continue
        marcas_inc.append(ftm.Marker(
            coordinates=ftm.MapLatitudeLongitude(*punto),
            content=ft.Container(
                content=ft.Icon(ft.Icons.FLAG, size=15, color="#FFFFFF"),
                bgcolor="#F1706E",
                padding=ft.Padding(4, 4, 4, 4),
                border_radius=ft.RoundedRectangleBorder(radius=8),
                border=ft.Border.all(2, "#FFFFFF"),
                shadow=paleta.sombra_suave,
            ),
            alignment=ft.Offset(0, -1.6),
        ))
    if marcas_inc:
        capas.append(ftm.MarkerLayer(markers=marcas_inc))

    # La unidad que se sigue (proyectada sobre la línea)
    marcador_unidad = ftm.Marker(
        coordinates=ftm.MapLatitudeLongitude(*u_xy),
        content=ft.Container(
            content=ft.Icon(ft.Icons.NAVIGATION, size=20, color="#FFFFFF"),
            bgcolor="#03C09C",
            padding=ft.Padding(5, 5, 5, 5),
            border_radius=ft.RoundedRectangleBorder(radius=12),
            border=ft.Border.all(2, "#FFFFFF"),
            shadow=paleta.sombra_suave,
        ),
    )
    capas.append(ftm.MarkerLayer(markers=[marcador_unidad]))

    mapa = ftm.Map(
        layers=capas,
        initial_center=ftm.MapLatitudeLongitude(*u_xy),
        initial_zoom=ZOOM_SEGUIMIENTO,
        min_zoom=11,
        max_zoom=18,
        bgcolor=paleta.superficie_2,
    )
    return mapa, poly_hecho, poly_pendiente, marcador_unidad


def vista_navegar(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    ruta_id = int(args[0]) if args else None
    ruta = funciones.ruta_por_id(ruta_id)
    if not ruta:
        return ft.View(
            route=page.route,
            bgcolor=paleta.fondo,
            appbar=c.app_bar("Navegación", page),
            controls=[c.estado_vacio(ft.Icons.ERROR_OUTLINE,
                                     "Ruta no encontrada",
                                     "Puede que haya sido eliminada.",
                                     accion_texto="Volver al inicio",
                                     on_accion=lambda e: estado.navegar(
                                         page, "/inicio", limpiar=True))],
        )

    paradas = funciones.paradas_de_ruta(ruta)
    unidad, es_virtual = funciones.unidad_para_navegacion(ruta)
    if unidad is None:
        return ft.View(
            route=page.route,
            bgcolor=paleta.fondo,
            appbar=c.app_bar("Navegación", page),
            controls=[c.estado_vacio(ft.Icons.DIRECTIONS_BUS_OUTLINED,
                                     "Sin unidades para navegar",
                                     f"La ruta {ruta.numero} no tiene "
                                     "paradas configuradas.")],
        )

    incidencias = funciones.incidencias_de_ruta(ruta.id)
    mapa, poly_hecho, poly_pendiente, marcador_unidad = _crear_mapa(
        ruta, paradas, unidad, paleta, incidencias)

    # ----- Banner de indicaciones -----
    icono_giro = ft.Icon(ft.Icons.LOCATION_ON_OUTLINED, size=32,
                         color="#FFFFFF")
    texto_distancia = ft.Text("En … m", size=24, weight=PESO_BOLD,
                              color="#FFFFFF", no_wrap=True,
                              overflow=ft.TextOverflow.ELLIPSIS)
    texto_instruccion = ft.Text("", size=TEXTO_S, color="#C7D3DE",
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS)
    texto_info = ft.Text("", size=TEXTO_XS, color="#9FB2C2")

    badge_ruta = ft.Container(
        content=ft.Text(ruta.numero, size=TEXTO_S, weight=PESO_BOLD,
                        color="#10202B", no_wrap=True),
        bgcolor=ruta.color,
        padding=ft.Padding(9, 4, 9, 4),
        border_radius=ft.RoundedRectangleBorder(radius=9),
    )

    banner = ft.Container(
        content=ft.Row([
            ft.Container(
                content=icono_giro, width=46, height=46,
                bgcolor=ft.Colors.with_opacity(0.18, "#FFFFFF"),
                border_radius=ft.RoundedRectangleBorder(radius=12),
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column([texto_distancia, texto_instruccion], spacing=2,
                      expand=True),
            badge_ruta,
        ], spacing=theme.ESPACIO_M,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=FONDO_BANNER,
        padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_M,
                           theme.ESPACIO_M, theme.ESPACIO_M),
        border_radius=ft.RoundedRectangleBorder(radius=theme.RADIO_L),
        shadow=ft.BoxShadow(blur_radius=14, color="#66000000"),
    )

    # ----- Lógica de seguimiento -----
    seguir = {"activo": True}

    def _info_viaje(pasos) -> str:
        km = ind.distancia_total(pasos) / 1000
        destino = pasos[-1] if pasos else None
        minutos = None
        if destino:
            psig = ind.recorrido_restante(paradas, unidad)
            if psig:
                minutos = funciones.eta_minutos(unidad, psig[-1].id)
        partes = [f"Faltan {km:.1f} km"]
        if minutos is not None:
            llegada = datetime.now() + timedelta(minutes=minutos)
            partes.append(f"llegás {llegada.strftime('%H:%M')}")
            partes.append(minutos_a_texto(minutos))
        partes.append(unidad.placa)
        return " · ".join(partes)

    def _centrar():
        if not seguir["activo"]:
            return
        destino = ftm.MapLatitudeLongitude(
            *funciones.punto_en_linea(ruta, unidad.latitud, unidad.longitud))
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(mapa.move_to(
            destino, zoom=ZOOM_SEGUIMIENTO,
            animation_duration=ft.Duration(milliseconds=800)))

    def al_mover(ev=None, _primera=False):
        if page.route != f"/navegar/{ruta.id}":
            return
        if es_virtual:
            funciones.avanzar_unidad_virtual(unidad,
                                             SEGUNDOS_POR_TICK / 3600)
        hechos, pendientes = ind.trayectoria(paradas, unidad)
        u_xy = _proyectar_unidad(ruta, unidad, hechos, pendientes)
        if len(hechos) >= 2:
            poly_hecho.coordinates = [
                ftm.MapLatitudeLongitude(*pt) for pt in hechos]
        if len(pendientes) >= 2:
            poly_pendiente.coordinates = [
                ftm.MapLatitudeLongitude(*pt) for pt in pendientes]
        marcador_unidad.coordinates = ftm.MapLatitudeLongitude(*u_xy)

        pasos = ind.indicaciones_para_unidad(paradas, unidad)
        if pasos:
            paso = pasos[0]
            icono_giro.name = ICONOS_GIRO.get(paso["giro"],
                                              ft.Icons.ARROW_UPWARD)
            texto_distancia.value = f"En {paso['distancia_m']} m"
            texto_instruccion.value = (paso["instruccion"][:1].upper()
                                       + paso["instruccion"][1:])
            texto_info.value = _info_viaje(pasos)
        else:
            icono_giro.name = ft.Icons.CHECK_CIRCLE
            icono_giro.color = "#03C09C"
            texto_distancia.value = "¡Llegaste!"
            texto_instruccion.value = (f"Terminaste el recorrido en "
                                       f"{ruta.destino}.")
            texto_info.value = f"{unidad.placa} · Ruta {ruta.numero}"
        if not _primera:
            _centrar()
        page.update()

    estado.registrar_tick(al_mover)

    # ----- Controles inferiores -----
    def abrir_resumen(ev):
        pasos = ind.indicaciones_para_unidad(paradas, unidad)
        if not pasos:
            pasos = ind.generar_indicaciones(paradas)
        filas = []
        for paso in pasos:
            giro = paso["giro"]
            filas.append(ft.Row([
                ft.Container(
                    content=ft.Icon(ICONOS_GIRO.get(giro,
                                                    ft.Icons.ARROW_UPWARD),
                                    size=18, color=COLORES_GIRO.get(giro)),
                    width=36, height=36,
                    bgcolor=ft.Colors.with_opacity(0.14,
                                                   COLORES_GIRO.get(giro)),
                    border_radius=ft.RoundedRectangleBorder(radius=18),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column([
                    ft.Text(paso["texto"], size=TEXTO_S,
                            color=paleta.texto),
                    ft.Text(f"{paso['distancia_m']} m", size=TEXTO_XS,
                            color=paleta.texto_sec),
                ], spacing=1, expand=True),
            ], spacing=theme.ESPACIO_M,
                vertical_alignment=ft.CrossAxisAlignment.CENTER))
        dialogo = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Indicaciones · Ruta {ruta.numero}",
                          size=theme.TEXTO_M, weight=PESO_SEMIBOLD,
                          color=paleta.texto),
            content=ft.Container(
                width=320, height=360,
                content=ft.ListView(filas, spacing=theme.ESPACIO_M,
                                    expand=True),
            ),
            actions=[
                c.boton("Cerrar", estilo="texto",
                        on_click=lambda e: page.pop_dialog()),
            ],
            bgcolor=paleta.superficie,
            shape=ft.RoundedRectangleBorder(radius=theme.RADIO_L),
        )
        page.show_dialog(dialogo)

    def recentrar(ev):
        seguir["activo"] = True
        texto_seguir.value = "Siguiendo"
        btn_seguir.bgcolor = "#03C09C"
        _centrar()
        page.update()

    def alternar_seguir(ev):
        seguir["activo"] = not seguir["activo"]
        texto_seguir.value = "Siguiendo" if seguir["activo"] else "Libre"
        btn_seguir.bgcolor = "#03C09C" if seguir["activo"] else "#3C4E5F"
        if seguir["activo"]:
            _centrar()
        page.update()

    def salir(ev):
        estado.navegar_atras(page)

    texto_seguir = ft.Text("Siguiendo", size=TEXTO_XS, weight=PESO_SEMIBOLD,
                           color="#FFFFFF")
    btn_seguir = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.GPS_FIXED, size=15, color="#FFFFFF"),
            texto_seguir,
        ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#03C09C",
        padding=ft.Padding(12, 8, 12, 8),
        border_radius=ft.RoundedRectangleBorder(radius=20),
        on_click=alternar_seguir,
    )

    barra_inferior = ft.Container(
        content=ft.Row([
            c.boton("Resumen", estilo="tonal", icono=ft.Icons.LIST_ALT,
                    on_click=abrir_resumen, alto=42),
            btn_seguir,
            c.boton("Salir", estilo="contorneado",
                    icono=ft.Icons.CLOSE, on_click=salir, alto=42),
        ], spacing=theme.ESPACIO_S,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.Padding(theme.ESPACIO_S, theme.ESPACIO_S,
                           theme.ESPACIO_S, theme.ESPACIO_S),
        bgcolor=ft.Colors.with_opacity(0.92, paleta.superficie),
        border_radius=ft.RoundedRectangleBorder(radius=theme.RADIO_L),
        shadow=ft.BoxShadow(blur_radius=12, color="#33000000"),
    )

    # Los controles de una Stack se posicionan con left/top/right/bottom
    banner.left = theme.ESPACIO_M
    banner.right = theme.ESPACIO_M
    banner.top = theme.ESPACIO_M + 28  # deja espacio al attribution
    barra_inferior.left = theme.ESPACIO_M
    barra_inferior.right = theme.ESPACIO_M
    barra_inferior.bottom = theme.ESPACIO_M + 8

    contenido = ft.Stack(
        expand=True,
        controls=[
            mapa,
            banner,
            barra_inferior,
        ],
    )

    # Pinta el estado inicial del banner antes del primer tick
    al_mover(_primera=True)

    return ft.View(
        route=f"/navegar/{ruta.id}",
        bgcolor=paleta.fondo,
        padding=0,
        controls=[contenido],
    )
