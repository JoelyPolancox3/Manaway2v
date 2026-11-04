"""Panel del conductor: unidad asignada, ruta, próximas paradas e incidencias."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import (PESO_BOLD, PESO_SEMIBOLD, TEXTO_L, TEXTO_S, TEXTO_XS,
                       TEXTO_XL, color_estado, texto_estado, p)

ESTADOS_UNIDAD = ["en ruta", "mantenimiento", "fuera de servicio"]
RUTA_SIN_UNIDAD = "#8895A0"


def vista_conductor(page: ft.Page, args: list = None) -> ft.View:
    if args and args[0] == "incidencias":
        # Sub-pantalla «Mis incidencias» del conductor
        from gui.mis_incidencias import vista_mis_incidencias
        return vista_mis_incidencias(page, args[1:])
    paleta = p()
    usuario = estado.usuario
    if not usuario or not usuario.es_conductor:
        # Solo conductores: otros roles vuelven a su propia interfaz.
        destino = ("/inicio" if not usuario
                   else "/gestion" if usuario.es_admin
                   else "/inicio")
        estado.snack(page, "Se requiere una cuenta de conductor.", "error")
        estado.navegar(page, destino, limpiar=True)
        return ft.View(route="/conductor", bgcolor=paleta.fondo, controls=[])

    unidad = funciones.unidad_por_id(usuario.unidad_id)
    ruta = funciones.ruta_por_id(unidad.ruta_id) if unidad else None
    color_ruta = ruta.color if ruta else RUTA_SIN_UNIDAD

    # ----- Tarjeta de estado de mi unidad -----
    def cambiar_estado_unidad(ev):
        clave = ev.data or ev.control.value
        if funciones.cambiar_estado_unidad(unidad.id, clave):
            estado.snack(page, f"{unidad.placa}: estado "
                               f"«{texto_estado(clave)}»", "exito")
            refrescar()

    if unidad:
        selector_estado = ft.Dropdown(
            value=unidad.estado,
            options=[ft.DropdownOption(key=e, text=texto_estado(e))
                     for e in ESTADOS_UNIDAD],
            text_size=TEXTO_S, color=color_estado(unidad.estado),
            bgcolor=paleta.superficie_2, border=c.bordes_formulario(12),
            menu_width=190, on_select=cambiar_estado_unidad,
            width=180,
        )
        tarjeta_unidad = c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.DIRECTIONS_BUS, size=26,
                                        color="#0B2A33"),
                        width=52, height=52,
                        bgcolor=color_ruta if unidad.estado == "en ruta"
                                else color_estado(unidad.estado),
                        border_radius=ft.RoundedRectangleBorder(radius=14),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text("Unidad asignada", size=TEXTO_XS,
                                color=paleta.texto_sec),
                        ft.Text(unidad.placa, size=TEXTO_XL,
                                weight=PESO_BOLD, color=paleta.texto),
                    ], spacing=2, expand=True),
                    selector_estado,
                ], spacing=theme.ESPACIO_M,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Icon(ft.Icons.SPEED_OUTLINED, size=15,
                            color=paleta.texto_sec),
                    ft.Text(f"{unidad.velocidad_kmh:.0f} km/h promedio",
                            size=TEXTO_XS, color=paleta.texto_sec),
                    ft.Icon(ft.Icons.SETTINGS_ACCESSIBILITY_OUTLINED,
                            size=15, color=paleta.texto_sec),
                    ft.Text(f"{len(funciones.paradas_de_ruta(ruta))} paradas "
                            f"en el recorrido" if ruta else "Sin ruta",
                            size=TEXTO_XS, color=paleta.texto_sec),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=theme.ESPACIO_M),
            padding=theme.ESPACIO_L,
            relleno=ft.Colors.with_opacity(0.10, color_ruta),
            borde=False,
        )
    else:
        tarjeta_unidad = c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.DIRECTIONS_BUS_OUTLINED, size=22,
                            color=paleta.advertencia),
                    ft.Text("Aún no tenés una unidad asignada",
                            size=TEXTO_S, weight=PESO_SEMIBOLD,
                            color=paleta.texto, expand=True),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text("Pedile a un administrador que te asigne una desde "
                        "Gestión → Usuarios; aparecerá aquí al instante.",
                        size=TEXTO_XS, color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_S),
            padding=theme.ESPACIO_L,
            relleno=ft.Colors.with_opacity(0.10, paleta.advertencia),
            borde=False,
        )

    # ----- Tarjeta de mi ruta -----
    def ir_a_navegar(ev):
        estado.navegar(page, f"/navegar/{ruta.id}")

    def reportar(ev):
        from gui import dialog_incidencia
        dialog_incidencia.abrir(page, ruta.id)

    def ver_mis_incidencias(ev):
        estado.navegar(page, "/conductor/incidencias")

    if ruta:
        paradas_ruta = funciones.paradas_de_ruta(ruta)
        tarjeta_ruta = c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Text(ruta.numero, size=TEXTO_S,
                                        weight=PESO_BOLD, color="#0B2A33"),
                        width=44, height=44, bgcolor=ruta.color,
                        border_radius=ft.RoundedRectangleBorder(radius=12),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(ruta.nombre, size=TEXTO_S,
                                weight=PESO_SEMIBOLD, color=paleta.texto),
                        ft.Text(f"{ruta.origen} → {ruta.destino}",
                                size=TEXTO_XS, color=paleta.texto_sec),
                    ], spacing=1, expand=True),
                    c.chip_estado(ruta.estado),
                ], spacing=theme.ESPACIO_M,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Icon(ft.Icons.BUS_ALERT_OUTLINED, size=15,
                            color=paleta.texto_sec),
                    ft.Text(ruta.cooperativa, size=TEXTO_XS,
                            color=paleta.texto_sec),
                    ft.Icon(ft.Icons.SCHEDULE, size=15,
                            color=paleta.texto_sec),
                    ft.Text(ruta.horario, size=TEXTO_XS,
                            color=paleta.texto_sec),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Container(
                        expand=True,
                        content=c.boton("Navegar mi ruta", on_click=ir_a_navegar,
                                        icono=ft.Icons.MAP_OUTLINED)),
                    ft.Container(
                        expand=True,
                        content=c.boton("Reportar incidencia", on_click=reportar,
                                        icono=ft.Icons.FLAG_OUTLINED,
                                        estilo="contorneado")),
                ], spacing=theme.ESPACIO_S),
                c.boton(
                    f"Mis incidencias ({len(funciones.incidencias_de_usuario(usuario.nombre))})",
                    on_click=ver_mis_incidencias,
                    icono=ft.Icons.OUTBOX_OUTLINED,
                    estilo="texto"),
            ], spacing=theme.ESPACIO_M),
            padding=theme.ESPACIO_L,
        )
    else:
        tarjeta_ruta = c.tarjeta(
            ft.Row([
                ft.Icon(ft.Icons.ROUTE_OUTLINED, size=20,
                        color=paleta.texto_sec),
                ft.Text("Sin ruta asignada todavía.", size=TEXTO_XS,
                        color=paleta.texto_sec, expand=True),
            ], spacing=theme.ESPACIO_S,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.ESPACIO_L, sombra=False,
        )

    # ----- Próximas paradas con ETA en vivo -----
    filas_paradas = []
    etiquetas_eta: list[tuple[ft.Text, int]] = []
    proximas = funciones.proximas_paradas_de_unidad(unidad) if unidad else []
    if not proximas:
        filas_paradas.append(
            c.tarjeta(
                ft.Row([
                    ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, size=18,
                            color=paleta.texto_sec),
                    ft.Text("No hay paradas para mostrar con la unidad "
                            "actual.", size=TEXTO_XS, color=paleta.texto_sec,
                            expand=True),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_M, sombra=False,
            ))
    else:
        for i, (parada, minutos) in enumerate(proximas):
            texto_eta = ft.Text(
                "—" if minutos is None else f"{minutos} min",
                size=TEXTO_XS, weight=PESO_SEMIBOLD,
                color=paleta.primario_claro if minutos is not None
                else paleta.texto_sec)
            etiquetas_eta.append((texto_eta, parada.id))
            filas_paradas.append(
                c.tarjeta(
                    ft.Row([
                        ft.Container(
                            content=ft.Text(str(i + 1), size=TEXTO_XS,
                                            weight=PESO_BOLD,
                                            color="#FFFFFF"),
                            width=26, height=26, bgcolor=color_ruta,
                            border_radius=ft.RoundedRectangleBorder(radius=8),
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(parada.nombre, size=TEXTO_S,
                                color=paleta.texto, expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        texto_eta,
                    ], spacing=theme.ESPACIO_S,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=theme.ESPACIO_M, sombra=False,
                ))

    # ETA en vivo: el tick de la simulación refresca los minutos
    def al_tiquear():
        if not unidad:
            return
        for texto_eta, parada_id in etiquetas_eta:
            minutos = funciones.eta_minutos(unidad, parada_id)
            texto_eta.value = "—" if minutos is None else f"{minutos} min"
            texto_eta.color = (paleta.primario_claro if minutos is not None
                               else paleta.texto_sec)
        page.update()

    if etiquetas_eta:
        estado.registrar_tick(al_tiquear)

    def refrescar(ev=None):
        estado.desregistrar_ticks()
        vista = vista_conductor(page, [])
        vista.route = page.route
        page.views[-1] = vista
        page.update()

    contenido = ft.ListView([
        ft.Column([
            c.tarjeta(
                ft.Row([
                    c.avatar(usuario.iniciales, radio=24, color=color_ruta),
                    ft.Column([
                        ft.Text(f"Hola, {usuario.nombre.split()[0]}",
                                size=TEXTO_L, weight=PESO_BOLD,
                                color=paleta.texto),
                        ft.Text("Turno en curso · Panel del conductor",
                                size=TEXTO_XS, color=paleta.texto_sec),
                    ], spacing=1, expand=True),
                    c.badge("Conductor", fondo=ft.Colors.with_opacity(
                        0.18, paleta.primario_claro),
                        color_texto=paleta.primario_claro),
                ], spacing=theme.ESPACIO_M,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_M, sombra=False,
            ),
            tarjeta_unidad,
            c.seccion_titulo("Mi ruta"),
            tarjeta_ruta,
            c.seccion_titulo("Próximas paradas"),
            ft.Column(filas_paradas, spacing=theme.ESPACIO_S),
            ft.Container(height=theme.ESPACIO_XL),
        ], spacing=theme.ESPACIO_M,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True,
        padding=ft.Padding(0, 0, 0, theme.ESPACIO_L))

    return ft.View(
        route="/conductor",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Panel del conductor", page,
                         subtitulo=unidad.placa if unidad else "Sin unidad",
                         atras=False,
                         acciones=[ft.IconButton(
                             icon=ft.Icons.PERSON_OUTLINE,
                             icon_color=paleta.texto,
                             on_click=lambda e: estado.navegar(page, "/perfil"),
                             tooltip="Mi perfil")],
                         salir=True),
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )
