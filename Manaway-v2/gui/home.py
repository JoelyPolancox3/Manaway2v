"""Panel principal: mapa de Managua con unidades en vivo y accesos rápidos."""
import asyncio

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

ALTO_PANEL_CERRADO = 60
ALTO_PANEL_ABIERTO = 380


def vista_home(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    # El inicio es pantalla del viajero: admin y conductor viven en
    # sus propias pantallas y jamás caen aquí.
    u_rol = estado.usuario
    if u_rol and (u_rol.es_admin or u_rol.es_conductor):
        estado.navegar(page, "/gestion" if u_rol.es_admin else "/conductor",
                       limpiar=True)
        return ft.View(route="/inicio", bgcolor=paleta.fondo, controls=[])
    rutas = funciones.listar_rutas()

    # ================= Mapa =================
    capas = [
        ftm.TileLayer(
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            user_agent_package_name="manaway/2.0",
        ),
        ftm.SimpleAttribution(text="© OpenStreetMap"),
    ]

    # Capa de la ruta seleccionada desde el riel (una sola, bien visible)
    capa_sel_linea = ftm.PolylineLayer(polylines=[])
    capa_sel_paradas = ftm.MarkerLayer(markers=[])
    capas.extend([capa_sel_linea, capa_sel_paradas])

    # Favoritas destacadas con su color (recorrido real de OSM)
    favoritas = [r for r in rutas if estado.es_favorita_ruta(r.id)]
    if favoritas:
        capas.append(ftm.PolylineLayer(polylines=[
            ftm.PolylineMarker(
                coordinates=[ftm.MapLatitudeLongitude(lat, lon)
                             for lat, lon in funciones.geometria_de_ruta(r)],
                color=r.color, stroke_width=4,
                border_color="#FFFFFF", border_stroke_width=1.5)
            for r in favoritas if len(funciones.geometria_de_ruta(r)) >= 2
        ]))

    # Unidades en ruta (marcadores de bus por color de ruta)
    marcadores: dict[int, ftm.Marker] = {}
    ruta_de_unidad: dict[int, int] = {}
    for u in funciones.listar_unidades():
        if u.estado != "en ruta":
            continue
        r = funciones.ruta_por_id(u.ruta_id)
        # el bus se dibuja sobre el recorrido real de su ruta
        lat_b, lon_b = (funciones.punto_en_linea(r, u.latitud, u.longitud)
                        if r else (u.latitud, u.longitud))
        marcador = ftm.Marker(
            coordinates=ftm.MapLatitudeLongitude(lat_b, lon_b),
            content=ft.Container(
                content=ft.Icon(ft.Icons.DIRECTIONS_BUS, size=18,
                                color="#0B2A33"),
                bgcolor=r.color if r else paleta.primario,
                padding=ft.Padding(4, 4, 4, 4),
                border_radius=ft.RoundedRectangleBorder(radius=9),
                border=ft.Border.all(2, "#FFFFFF"),
                shadow=paleta.sombra_suave,
            ),
        )
        marcadores[u.id] = marcador
        ruta_de_unidad[u.id] = u.ruta_id
    capa_unidades = ftm.MarkerLayer(markers=list(marcadores.values()))
    capas.append(capa_unidades)

    # Incidencias reportadas (estilo Waze)
    def marcas_incidencias() -> list:
        marcas = []
        for inc in estado.incidencias:
            if inc.resuelta:
                continue
            punto = funciones.incidencia_en_linea(inc)
            if not punto:
                continue
            marcas.append(ftm.Marker(
                coordinates=ftm.MapLatitudeLongitude(*punto),
                content=ft.Container(
                    content=ft.Icon(ft.Icons.FLAG, size=14, color="#FFFFFF"),
                    bgcolor="#F1706E",
                    padding=ft.Padding(4, 4, 4, 4),
                    border_radius=ft.RoundedRectangleBorder(radius=8),
                    border=ft.Border.all(2, "#FFFFFF"),
                    shadow=paleta.sombra_suave,
                ),
                alignment=ft.Offset(0, -1.6),
            ))
        return marcas

    capa_incidencias = ftm.MarkerLayer(markers=marcas_incidencias())
    capas.append(capa_incidencias)

    mapa = ftm.Map(
        layers=capas,
        initial_center=CENTRO_MANAGUA,
        initial_zoom=13.2,
        min_zoom=11,
        max_zoom=17,
        bgcolor=paleta.superficie_2,
    )

    # ================= Búsqueda flotante =================
    campo_busqueda = ft.TextField(
        hint_text="Buscá ruta, parada o destino…",
        text_size=TEXTO_S,
        color=paleta.texto,
        hint_style=ft.TextStyle(color=paleta.texto_sec),
        bgcolor=paleta.superficie,
        filled=True,
        border=ft.OutlineInputBorder(
            side=ft.BorderSide(1, paleta.borde),
            border_radius=ft.RoundedRectangleBorder(radius=22)),
        content_padding=ft.Padding(theme.ESPACIO_L, 10, theme.ESPACIO_S, 10),
        expand=True,
        max_lines=1,
    )

    filas_resultados = ft.Column([], spacing=0)
    resultados_container = ft.Container(
        content=ft.ListView([filas_resultados], spacing=0,
                            height=280),
        bgcolor=paleta.superficie,
        border=ft.Border.all(1, paleta.borde),
        border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
        shadow=paleta.sombra_suave,
        visible=False,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )

    def fila_resultado(r) -> ft.Container:
        def ir(ev):
            estado.navegar(page, f"/ruta/{r.id}")
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(r.numero, size=TEXTO_XS,
                                    weight=PESO_BOLD, color="#0B2A33"),
                    bgcolor=r.color,
                    padding=ft.Padding(8, 5, 8, 5),
                    border_radius=ft.RoundedRectangleBorder(radius=8),
                ),
                ft.Column([
                    ft.Text(r.nombre, size=TEXTO_S, weight=PESO_SEMIBOLD,
                            color=paleta.texto, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{r.origen} → {r.destino}", size=TEXTO_XS,
                            color=paleta.texto_sec, no_wrap=True,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=1, expand=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=18,
                        color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_M,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_S,
                               theme.ESPACIO_M, theme.ESPACIO_S),
            on_click=ir, ink=True,
            ink_color=ft.Colors.with_opacity(0.08, paleta.texto),
        )

    def al_buscar(ev=None):
        texto = (campo_busqueda.value or "").strip()
        if not texto:
            resultados_container.visible = False
            page.update()
            return
        encontradas = funciones.buscar_rutas(texto)[:5]
        filas = [fila_resultado(r) for r in encontradas]
        if not filas:
            filas = [ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SEARCH_OFF, size=18,
                            color=paleta.texto_sec),
                    ft.Text("Sin resultados. Probá con un número (106) o "
                            "una parada (UCA).", size=TEXTO_XS,
                            color=paleta.texto_sec),
                ], spacing=theme.ESPACIO_S),
                padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_S,
                                   theme.ESPACIO_M, theme.ESPACIO_S))]
        filas_resultados.controls = filas
        resultados_container.visible = True
        page.update()

    campo_busqueda.on_change = al_buscar
    campo_busqueda.on_submit = lambda e: (
        estado.navegar(page, "/buscar"))

    btn_asistente_busq = ft.Container(
        content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=20,
                        color="#FFFFFF"),
        width=38, height=38,
        bgcolor=paleta.primario,
        border_radius=ft.RoundedRectangleBorder(radius=19),
        alignment=ft.Alignment.CENTER,
        on_click=lambda e: estado.navegar(page, "/asistente"),
        tooltip="Preguntar al asistente con IA",
    )

    barra_busqueda = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.SEARCH, size=20, color=paleta.texto_sec),
            campo_busqueda,
            btn_asistente_busq,
        ], spacing=theme.ESPACIO_S,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(theme.ESPACIO_S, theme.ESPACIO_XS,
                           theme.ESPACIO_S, theme.ESPACIO_XS),
        shadow=paleta.sombra_suave,
    )

    # ================= Riel de rutas (derecha) =================
    # Todos los números del mapa oficial de mapanica, agrupados por
    # categoría y coloreados como el mapa real.
    orden_categorias = ["Centro/UCA", "Sur", "Oeste", "Este", "Norte",
                        "Internas", "Ciudad Sandino"]
    chips_riel = []
    for cat in orden_categorias:
        for r in [x for x in rutas if x.categoria == cat]:
            chips_riel.append(ft.Container(
                content=ft.Text(r.numero, size=12, weight=PESO_BOLD,
                                color="#0B2A33"),
                width=40, height=31,
                bgcolor=r.color,
                border_radius=ft.RoundedRectangleBorder(radius=9),
                alignment=ft.Alignment.CENTER,
                on_click=lambda e, rid=r.id: seleccionar_ruta(rid),
                tooltip=f"{r.numero} · {r.nombre}",
                ink=True,
            ))
    riel = ft.Container(
        content=ft.ListView(
            chips_riel, spacing=4, padding=4,
            scroll=ft.Scrollbar(thumb_visibility=True, track_visibility=True,
                                thickness=3, radius=6)),
        width=50,
        bgcolor=ft.Colors.with_opacity(0.85, "#16222E"),
        border_radius=ft.RoundedRectangleBorder(radius=ft.BorderRadius.only(
            top_left=16, bottom_left=16, top_right=0, bottom_right=0)),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )

    # ========= Selección de ruta: resaltar recorrido en el mapa =========
    ruta_sel = {"id": None}

    def actualizar_visibilidad_botones():
        # La tarjeta de selección ocupa el lugar del botón de reporte
        btn_reportar.visible = (not panel_expandido["valor"]
                                and ruta_sel["id"] is None)

    def aplicar_pantalla_limpia():
        """Al elegir una ruta se oculta el riel y los buses ajenos.

        El mapa queda limpio: solo la línea de la ruta escogida, sus
        puntos y sus unidades. Al quitar la selección vuelve todo.
        """
        rid = ruta_sel["id"]
        riel.visible = rid is None
        if rid is None:
            capa_unidades.markers = list(marcadores.values())
        else:
            capa_unidades.markers = [
                marcadores[uid] for uid, ruid in ruta_de_unidad.items()
                if ruid == rid and uid in marcadores]

    def quitar_sel():
        ruta_sel["id"] = None
        capa_sel_linea.polylines = []
        capa_sel_paradas.markers = []
        tarjeta_sel.visible = False
        aplicar_pantalla_limpia()
        actualizar_visibilidad_botones()

    def seleccionar_ruta(rid):
        r = funciones.ruta_por_id(rid)
        if r is None:
            return
        if ruta_sel["id"] == rid:  # segundo toque → quitar del mapa
            quitar_sel()
            page.update()
            return
        ruta_sel["id"] = rid
        aplicar_pantalla_limpia()
        ps = funciones.paradas_de_ruta(r)
        geo = funciones.geometria_de_ruta(r)
        capa_sel_linea.polylines = [ftm.PolylineMarker(
            coordinates=[ftm.MapLatitudeLongitude(lat, lon)
                         for lat, lon in geo],
            color=r.color, stroke_width=5,
            border_color="#FFFFFF", border_stroke_width=2,
        )] if len(geo) >= 2 else []
        capa_sel_paradas.markers = [ftm.Marker(
            coordinates=ftm.MapLatitudeLongitude(
                *funciones.parada_en_linea(r, p)),
            content=ft.Container(
                width=10, height=10, bgcolor=r.color,
                border_radius=ft.RoundedRectangleBorder(radius=5),
                border=ft.Border.all(2, "#FFFFFF")),
        ) for p in ps]
        badge_sel.bgcolor = r.color
        badge_sel.content = ft.Text(r.numero, size=11, weight=PESO_BOLD,
                                    color="#0B2A33")
        nombre_sel.value = r.nombre
        detalle_sel.value = (f"{r.categoria or 'Managua'} · "
                             f"{r.cooperativa or r.origen}")
        btn_ir_sel.on_click = lambda e, rid2=rid: estado.navegar(
            page, f"/ruta/{rid2}")
        tarjeta_sel.visible = True
        actualizar_visibilidad_botones()
        # encuadre de la cámara al recorrido completo (geometría real)
        if geo:
            lats = [pt[0] for pt in geo]
            lons = [pt[1] for pt in geo]
            centro = ftm.MapLatitudeLongitude(
                (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2)
            km_span = max((max(lats) - min(lats)) * 111.0,
                          (max(lons) - min(lons)) * 108.6)
            zoom = (15 if km_span < 3 else 14 if km_span < 6
                    else 13 if km_span < 12 else 12 if km_span < 25
                    else 11)
            asyncio.get_running_loop().create_task(mapa.move_to(
                destination=centro, zoom=zoom, animation_duration=350,
                cancel_ongoing_animations=True))
        page.update()

    badge_sel = ft.Container(
        width=36, height=27, bgcolor="#2E9E5B",
        border_radius=ft.RoundedRectangleBorder(radius=8),
        alignment=ft.Alignment.CENTER)
    nombre_sel = ft.Text("", size=TEXTO_XS, color=paleta.texto,
                         weight=PESO_SEMIBOLD, max_lines=1,
                         overflow=ft.TextOverflow.ELLIPSIS)
    detalle_sel = ft.Text("", size=TEXTO_XS, color=paleta.texto_sec,
                          max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    btn_ir_sel = ft.Container(
        content=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color="#FFFFFF"),
        width=30, height=30, bgcolor=paleta.primario,
        border_radius=ft.RoundedRectangleBorder(radius=15),
        alignment=ft.Alignment.CENTER, ink=True, tooltip="Ver detalle")
    btn_cerrar_sel = ft.Container(
        content=ft.Icon(ft.Icons.CLOSE, size=16, color=paleta.texto_sec),
        width=26, height=26, alignment=ft.Alignment.CENTER, ink=True,
        tooltip="Quitar del mapa",
        on_click=lambda e: (quitar_sel(), page.update()))
    tarjeta_sel = ft.Container(
        content=ft.Row([
            badge_sel,
            ft.Column([nombre_sel, detalle_sel], spacing=1, expand=True),
            btn_ir_sel,
            btn_cerrar_sel,
        ], spacing=theme.ESPACIO_S,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=paleta.superficie,
        border=ft.Border.all(1, paleta.borde),
        border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
        padding=ft.Padding(theme.ESPACIO_S, theme.ESPACIO_S,
                           theme.ESPACIO_S, theme.ESPACIO_S),
        shadow=paleta.sombra_suave,
        visible=False,
        width=316,
    )

    # ================= Panel inferior =================
    textos_llegadas: dict[int, list[ft.Text]] = {}

    fila_paradas_llegadas = []
    paradas = funciones.listar_paradas()
    favoritas_paradas = [p_ for p_ in paradas
                         if estado.es_favorita_parada(p_.id)]
    for par in (favoritas_paradas[:3] or
                [p_ for p_ in paradas if p_.id in (1, 9, 20)]):
        llegadas = funciones.proximas_llegadas(par.id)
        lineas = []
        for i in range(2):
            if i < len(llegadas):
                u, minutos = llegadas[i]
                valor, color = (f"{u.placa} · {minutos_a_texto(minutos)}",
                                paleta.texto)
            else:
                valor, color = "—", paleta.texto_sec
            texto_ctrl = ft.Text(valor, size=TEXTO_XS, color=color,
                                 weight=PESO_SEMIBOLD)
            lineas.append(texto_ctrl)
        textos_llegadas[par.id] = lineas
        fila_paradas_llegadas.append(ft.Row([
            ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, size=16,
                    color=paleta.primario_claro),
            ft.Column([ft.Text(par.nombre, size=TEXTO_S,
                               weight=PESO_SEMIBOLD, color=paleta.texto),
                       *lineas], spacing=1, expand=True),
        ], spacing=theme.ESPACIO_S,
            vertical_alignment=ft.CrossAxisAlignment.START))

    resumen = funciones.resumen_servicio()

    def pastilla(icono, valor, etiqueta, color):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icono, size=16, color=color),
                ft.Text(valor, size=TEXTO_S, weight=PESO_BOLD,
                        color=paleta.texto),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(theme.ESPACIO_S, theme.ESPACIO_XS,
                               theme.ESPACIO_S, theme.ESPACIO_XS),
            bgcolor=paleta.superficie_2,
            border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
            border=ft.Border.all(1, paleta.borde),
        )

    fila_resumen = ft.Row([
        pastilla(ft.Icons.ROUTE, str(resumen["rutas"]), "rutas",
                 paleta.primario_claro),
        pastilla(ft.Icons.DIRECTIONS_BUS, str(resumen["unidades_activas"]),
                 "en ruta", "#03C09C"),
        pastilla(ft.Icons.WARNING_AMBER_OUTLINED,
                 str(len(resumen["con_retraso"]) + len(resumen["suspendidas"])),
                 "con alerta", "#F2B159"),
    ], spacing=theme.ESPACIO_S, scroll=ft.ScrollMode.AUTO)

    alertas = [r for r in rutas if r.estado != "normal"]
    elementos_alertas = []
    for r in alertas[:4]:
        def ir_alerta(ev, rid=r.id):
            estado.navegar(page, f"/ruta/{rid}")
        elementos_alertas.append(ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, size=18,
                        color=color_estado(r.estado)),
                ft.Text(f"{r.numero} · {texto_estado(r.estado)}",
                        size=TEXTO_S, weight=PESO_SEMIBOLD,
                        color=paleta.texto),
                ft.Text(r.nombre, size=TEXTO_XS, color=paleta.texto_sec,
                        expand=True, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16,
                        color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_S,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_S,
                               theme.ESPACIO_M, theme.ESPACIO_S),
            bgcolor=ft.Colors.with_opacity(0.10, color_estado(r.estado)),
            border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
            on_click=ir_alerta, ink=True,
        ))

    def acceso(icono, etiqueta, ruta_destino, color):
        def ir(ev):
            estado.navegar(page, ruta_destino)
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(icono, size=20, color=color),
                    width=42, height=42,
                    bgcolor=ft.Colors.with_opacity(0.16, color),
                    border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(etiqueta, size=TEXTO_XS, weight=PESO_SEMIBOLD,
                        color=paleta.texto, no_wrap=True),
            ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            on_click=ir, ink=True,
            ink_color=ft.Colors.with_opacity(0.08, paleta.texto),
        )

    accesos = [acceso(ft.Icons.SMART_TOY_OUTLINED, "Asistente",
                      "/asistente", "#03C09C"),
               acceso(ft.Icons.DIRECTIONS_BUS_OUTLINED, "Unidades",
                      "/unidades", paleta.primario_claro)]
    if estado.usuario and estado.usuario.es_admin:
        accesos.append(acceso(ft.Icons.SETTINGS_OUTLINED, "Gestión",
                              "/gestion", "#F2B159"))
    if estado.usuario and estado.usuario.es_conductor:
        accesos.append(acceso(ft.Icons.BADGE_OUTLINED, "Mi panel",
                              "/conductor", "#03C09C"))

    elementos_favoritos = []
    fav_rutas = [r for r in rutas if estado.es_favorita_ruta(r.id)]
    for r in fav_rutas[:3]:
        def ir_fav(ev, rid=r.id):
            estado.navegar(page, f"/ruta/{rid}")
        elementos_favoritos.append(ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(r.numero, size=TEXTO_XS,
                                    weight=PESO_BOLD, color="#0B2A33"),
                    bgcolor=r.color,
                    padding=ft.Padding(8, 5, 8, 5),
                    border_radius=ft.RoundedRectangleBorder(radius=8)),
                ft.Text(r.nombre, size=TEXTO_S, color=paleta.texto,
                        expand=True, no_wrap=True,
                        overflow=ft.TextOverflow.ELLIPSIS),
                ft.Icon(ft.Icons.STAR, size=16, color="#F2B159"),
            ], spacing=theme.ESPACIO_M,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(theme.ESPACIO_S, theme.ESPACIO_XS,
                               theme.ESPACIO_S, theme.ESPACIO_XS),
            on_click=ir_fav, ink=True,
        ))
    if not elementos_favoritos:
        elementos_favoritos = [ft.Text(
            "Guardá tus rutas con ⭐ desde su detalle para verlas acá.",
            size=TEXTO_XS, color=paleta.texto_sec)]

    seccion = lambda t: c.seccion_titulo(t)

    contenido_panel = ft.Column([
        fila_resumen,
        seccion("Alertas del servicio") if elementos_alertas else
        ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=16, color="#03C09C"),
            ft.Text("Todas las rutas operan con normalidad.",
                    size=TEXTO_XS, color=paleta.texto_sec),
        ], spacing=theme.ESPACIO_S),
        *elementos_alertas,
        seccion("Próximas llegadas"),
        *fila_paradas_llegadas,
        seccion("Accesos rápidos"),
        ft.Row(accesos, spacing=theme.ESPACIO_L),
        seccion("Mis rutas favoritas"),
        *elementos_favoritos,
        ft.Container(height=theme.ESPACIO_L),
    ], spacing=theme.ESPACIO_S)

    texto_panel_titulo = ft.Text("Estado del servicio", size=TEXTO_S,
                                 weight=PESO_BOLD, color=paleta.texto)
    texto_panel_sub = ft.Text(
        f"{resumen['rutas']} rutas · {resumen['unidades_activas']} unidades "
        "en ruta · tocá para ver más", size=TEXTO_XS, color=paleta.texto_sec)
    icono_panel = ft.Icon(ft.Icons.KEYBOARD_ARROW_UP, size=22,
                          color=paleta.texto_sec)

    panel = ft.Container(
        content=ft.Column([
            ft.Container(  # manija
                content=ft.Row([
                    icono_panel,
                    ft.Column([texto_panel_titulo, texto_panel_sub],
                              spacing=1, expand=True),
                    ft.Icon(ft.Icons.SCHEDULE, size=18,
                            color=paleta.primario_claro),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_S,
                                   theme.ESPACIO_M, theme.ESPACIO_S),
                on_click=None,  # se asigna después de definir contenido
            ),
            ft.Container(
                # expand=True en cadena (Column → contenedor → ListView)
                # para que el contenido realmente se pueda desplazar, y
                # barra de desplazamiento siempre visible.
                content=ft.ListView(
                    [contenido_panel], spacing=0, expand=True,
                    scroll=ft.Scrollbar(thumb_visibility=True,
                                        track_visibility=True,
                                        thickness=4, radius=8)),
                padding=ft.Padding(theme.ESPACIO_M, 0, theme.ESPACIO_M, 0),
                expand=True,
            ),
        ], spacing=0, expand=True),
        height=ALTO_PANEL_CERRADO,
        bgcolor=paleta.superficie,
        border_radius=ft.RoundedRectangleBorder(radius=ft.BorderRadius.only(
            top_left=20, top_right=20, bottom_left=0, bottom_right=0)),
        shadow=ft.BoxShadow(blur_radius=16, color="#44000000"),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    panel_expandido = {"valor": False}

    def alternar_panel(ev=None):
        panel_expandido["valor"] = not panel_expandido["valor"]
        panel.height = (ALTO_PANEL_ABIERTO if panel_expandido["valor"]
                        else ALTO_PANEL_CERRADO)
        icono_panel.name = (ft.Icons.KEYBOARD_ARROW_DOWN
                            if panel_expandido["valor"]
                            else ft.Icons.KEYBOARD_ARROW_UP)
        actualizar_visibilidad_botones()
        page.update()

    manija = panel.content.controls[0]
    manija.on_click = alternar_panel

    # ================= Botón flotante de reporte =================
    btn_reportar = ft.Container(
        content=ft.Icon(ft.Icons.FLAG, size=24, color="#FFFFFF"),
        width=52, height=52,
        bgcolor="#F2B159",
        border_radius=ft.RoundedRectangleBorder(radius=26),
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(blur_radius=12, color="#66000000"),
        on_click=lambda e: dialog_incidencia.abrir(page),
        tooltip="Reportar incidencia (estilo Waze)",
    )

    conteo_incidencias = {"n": len(estado.incidencias)}

    def al_mover(ev=None):
        if page.route != "/inicio":
            return
        for u in funciones.listar_unidades():
            marcador = marcadores.get(u.id)
            if marcador is not None and u.estado == "en ruta":
                ru = funciones.ruta_por_id(u.ruta_id)
                lat_b, lon_b = (funciones.punto_en_linea(
                    ru, u.latitud, u.longitud)
                    if ru else (u.latitud, u.longitud))
                marcador.coordinates = ftm.MapLatitudeLongitude(lat_b, lon_b)
        for par in list(textos_llegadas):
            llegadas = funciones.proximas_llegadas(par)
            for i, texto in enumerate(textos_llegadas[par]):
                if i < len(llegadas):
                    u, minutos = llegadas[i]
                    texto.value = f"{u.placa} · {minutos_a_texto(minutos)}"
                    texto.color = paleta.texto
                else:
                    texto.value = "—"
                    texto.color = paleta.texto_sec
        # Nuevas incidencias → refrescar marcadores
        if len(estado.incidencias) != conteo_incidencias["n"]:
            conteo_incidencias["n"] = len(estado.incidencias)
            capa_incidencias.markers = marcas_incidencias()
        page.update()

    estado.registrar_tick(al_mover)

    # Los controles de un Stack se posicionan con left/top/right/bottom.
    barra_busqueda.left = theme.ESPACIO_M
    barra_busqueda.right = theme.ESPACIO_M
    barra_busqueda.top = theme.ESPACIO_M

    resultados_container.left = theme.ESPACIO_M
    resultados_container.right = theme.ESPACIO_M
    resultados_container.top = 68

    riel.right = 0
    riel.top = 100
    riel.bottom = ALTO_PANEL_CERRADO + 76

    tarjeta_sel.left = theme.ESPACIO_M
    tarjeta_sel.bottom = ALTO_PANEL_CERRADO + 12

    btn_reportar.right = theme.ESPACIO_M
    btn_reportar.bottom = ALTO_PANEL_CERRADO + 12

    panel.left = 0
    panel.right = 0
    panel.bottom = 0

    contenido = ft.Stack(
        expand=True,
        controls=[mapa, barra_busqueda, resultados_container, riel,
                  tarjeta_sel, btn_reportar, panel],
    )

    return ft.View(
        route="/inicio",
        bgcolor=paleta.fondo,
        padding=0,
        navigation_bar=c.barra_inferior(page, "/inicio"),
        controls=[contenido],
    )
