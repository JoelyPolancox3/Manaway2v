"""Panel de gestión: usuarios, unidades, rutas e incidencias (solo administradores)."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import PESO_BOLD, PESO_SEMIBOLD, TEXTO_S, TEXTO_XS, color_estado, texto_estado, p

ESTADOS_UNIDAD = ["en ruta", "mantenimiento", "fuera de servicio"]
ESTADOS_RUTA = ["normal", "retraso", "suspendido"]
ROLES_USUARIO = [("viajero", "Viajero"), ("conductor", "Conductor"),
                 ("admin", "Administrador")]


def vista_gestion(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    usuario = estado.usuario
    if not usuario or not usuario.es_admin:
        # Cada rol vuelve a su propia interfaz: el admin a esta
        # pantalla solo si tiene sesión de administrador.
        destino = ("/login" if not usuario
                   else "/conductor" if usuario.es_conductor
                   else "/inicio")
        estado.snack(page, "Se requiere una cuenta de administrador.", "error")
        estado.navegar(page, destino, limpiar=True)
        return ft.View(route="/gestion", bgcolor=paleta.fondo, controls=[])

    # Sección que pide la ruta: /gestion, /gestion/unidades,
    # /gestion/rutas o /gestion/incidencias (cuatro pantallas propias
    # del administrador, unidas por la barra barra_admin).
    seccion = (args[0].lower() if args else "usuarios")
    if seccion not in ("usuarios", "unidades", "rutas", "incidencias"):
        seccion = "usuarios"

    # ----- Usuarios (CRUD) -----
    usuarios_app = funciones.listar_usuarios()
    dueno_unidad = {u.unidad_id: u for u in usuarios_app if u.unidad_id}
    filas_usuarios = []
    for u in usuarios_app:
        es_sistema = u.usuario.lower() in funciones.CUENTAS_SISTEMA
        es_propia = estado.usuario and estado.usuario.id == u.id

        def cambiar_rol(ev, uid=u.id, nombre=u.nombre):
            clave = ev.data or ev.control.value
            usuario, error = funciones.cambiar_rol_usuario(uid, clave)
            if error:
                estado.snack(page, error, "error")
            else:
                estado.snack(page, f"{nombre}: rol «{clave}»", "exito")
                # Si el rol cambió en la cuenta con sesión abierta,
                # la persona pasa de inmediato a las pantallas de su
                # nuevo rol (sus pantallas son las de su rol).
                if (usuario and estado.usuario
                        and estado.usuario.id == usuario.id):
                    estado.usuario.rol = usuario.rol
                    if not estado.usuario.es_admin:
                        destino = ("/conductor"
                                   if estado.usuario.es_conductor
                                   else "/inicio")
                        estado.navegar(page, destino, limpiar=True)
                        return
            refrescar()

        selector_rol = ft.Dropdown(
            value=u.rol,
            options=[ft.DropdownOption(key=k, text=t)
                     for k, t in ROLES_USUARIO],
            text_size=TEXTO_XS, color=paleta.texto,
            bgcolor=paleta.superficie_2, border=c.bordes_formulario(10),
            menu_width=170, on_select=cambiar_rol,
            width=150,
        )

        controles_fila = [selector_rol]

        if u.es_conductor:
            def asignar_unidad(ev, uid=u.id, nombre=u.nombre):
                clave = ev.data or ev.control.value
                usuario, error = funciones.asignar_unidad_conductor(
                    uid, clave or 0)
                if error:
                    estado.snack(page, error, "error")
                else:
                    texto = ("sin unidad"
                             if not usuario.unidad_id else
                             f"unidad {funciones.unidad_por_id(usuario.unidad_id).placa}")
                    estado.snack(page, f"{nombre}: {texto}", "exito")
                refrescar()

            opciones_unidad = [ft.DropdownOption(key="", text="Sin unidad")]
            for un in funciones.listar_unidades():
                otro = dueno_unidad.get(un.id)
                if otro and otro.id != u.id:
                    continue  # ya asignada a otro conductor
                r_un = funciones.ruta_por_id(un.ruta_id)
                opciones_unidad.append(ft.DropdownOption(
                    key=str(un.id),
                    text=f"{un.placa} · Ruta {r_un.numero if r_un else '—'}"))
            controles_fila.append(ft.Dropdown(
                value=str(u.unidad_id) if u.unidad_id else "",
                options=opciones_unidad,
                label="Unidad", label_style=ft.TextStyle(
                    color=paleta.texto_sec, size=TEXTO_XS),
                text_size=TEXTO_XS, color=paleta.texto,
                bgcolor=paleta.superficie_2,
                border=c.bordes_formulario(10),
                menu_width=200, on_select=asignar_unidad,
                width=190,
            ))

        def eliminar(ev, uid=u.id, nombre=u.nombre, sistema=es_sistema,
                     propia=es_propia):
            if sistema or propia:
                motivo = ("tu propia cuenta" if propia
                          else "una cuenta del sistema")
                estado.snack(page, f"No se puede eliminar {motivo}.", "aviso")
                return
            ok, error = funciones.eliminar_usuario(uid)
            if ok:
                estado.snack(page, f"Cuenta «{nombre}» eliminada.", "exito")
            else:
                estado.snack(page, error or "No se pudo eliminar.", "error")
            refrescar()

        icono_eliminar = ft.IconButton(
            icon=(ft.Icons.LOCK_OUTLINE if es_sistema else ft.Icons.DELETE_OUTLINE),
            icon_color=(paleta.texto_sec if es_sistema else paleta.error),
            tooltip=("Cuenta del sistema: no se puede eliminar"
                     if es_sistema else "Eliminar cuenta"),
            on_click=eliminar,
            disabled=es_sistema or es_propia,
        )

        filas_usuarios.append(
            c.tarjeta(
                ft.Column([
                    ft.Row([
                        c.avatar(u.iniciales, radio=18),
                        ft.Column([
                            ft.Text(u.nombre, size=TEXTO_S,
                                    weight=PESO_SEMIBOLD, color=paleta.texto),
                            ft.Text(f"@{u.usuario}", size=TEXTO_XS,
                                    color=paleta.texto_sec),
                        ], spacing=1, expand=True),
                        c.badge(dict(ROLES_USUARIO).get(u.rol, u.rol),
                                fondo=ft.Colors.with_opacity(
                                    0.18,
                                    {"viajero": paleta.primario_claro,
                                     "conductor": paleta.exito,
                                     "admin": paleta.advertencia}.get(
                                         u.rol, paleta.primario)),
                                color_texto=paleta.texto),
                        icono_eliminar,
                    ], spacing=theme.ESPACIO_S,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row(controles_fila, spacing=theme.ESPACIO_S,
                           scroll=ft.ScrollMode.AUTO),
                ], spacing=theme.ESPACIO_S),
                padding=theme.ESPACIO_M, sombra=False,
            ))

    # ----- Unidades -----
    filas_unidades = []
    for u in funciones.listar_unidades():
        r = funciones.ruta_por_id(u.ruta_id)

        def cambiar_unidad(ev, uid=u.id):
            clave = ev.data or ev.control.value
            if funciones.cambiar_estado_unidad(uid, clave):
                estado.snack(page,
                             f"{u.placa}: estado «{texto_estado(clave)}»",
                             "exito")
                refrescar()

        selector = ft.Dropdown(
            value=u.estado,
            options=[ft.DropdownOption(key=e, text=texto_estado(e))
                     for e in ESTADOS_UNIDAD],
            text_size=TEXTO_XS, color=color_estado(u.estado),
            bgcolor=paleta.superficie_2, border=c.bordes_formulario(10),
            menu_width=190,
            on_select=cambiar_unidad,
            width=160,
        )
        filas_unidades.append(
            c.tarjeta(
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.DIRECTIONS_BUS, size=18,
                                        color="#0B2A33"),
                        width=36, height=36,
                        bgcolor=(r.color if r else paleta.primario)
                                if u.estado == "en ruta"
                                else color_estado(u.estado),
                        border_radius=ft.RoundedRectangleBorder(radius=10),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(u.placa, size=TEXTO_S, weight=PESO_SEMIBOLD,
                                color=paleta.texto),
                        ft.Text(f"Ruta {r.numero if r else '—'}",
                                size=TEXTO_XS, color=paleta.texto_sec),
                    ], spacing=1, expand=True),
                    selector,
                ], spacing=theme.ESPACIO_M,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_M, sombra=False,
            ))

    # ----- Rutas -----
    filas_rutas = []
    for r in funciones.listar_rutas():
        chips = []
        for clave in ESTADOS_RUTA:
            chip_ctrl = c.chip(texto_estado(clave), seleccionado=(r.estado == clave))
            chip_ctrl.on_click = lambda e, rid=r.id, k=clave: (
                funciones.cambiar_estado_ruta(rid, k),
                estado.snack(page,
                             f"Ruta {funciones.ruta_por_id(rid).numero}: "
                             f"«{texto_estado(k)}»",
                             "exito" if k == "normal" else "aviso"),
                refrescar())
            chips.append(chip_ctrl)

        filas_rutas.append(
            c.tarjeta(
                ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(r.numero, size=TEXTO_S,
                                            weight=PESO_BOLD, color="#0B2A33"),
                            width=40, height=40,
                            bgcolor=r.color,
                            border_radius=ft.RoundedRectangleBorder(radius=10),
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column([
                            ft.Text(r.nombre, size=TEXTO_S,
                                    weight=PESO_SEMIBOLD, color=paleta.texto),
                            ft.Text(f"{len(funciones.unidades_de_ruta(r.id))} "
                                    f"unidades asignadas",
                                    size=TEXTO_XS, color=paleta.texto_sec),
                        ], spacing=1, expand=True),
                    ], spacing=theme.ESPACIO_M,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row(chips, spacing=theme.ESPACIO_S,
                           scroll=ft.ScrollMode.AUTO),
                ], spacing=theme.ESPACIO_S),
                padding=theme.ESPACIO_M, sombra=False,
            ))

    # ----- Incidencias reportadas -----
    filas_incidencias = []
    if not estado.incidencias:
        filas_incidencias.append(
            c.tarjeta(
                ft.Row([
                    ft.Icon(ft.Icons.FLAG_OUTLINED, size=18,
                            color=paleta.texto_sec),
                    ft.Text("Sin incidencias reportadas por los viajeros.",
                            size=TEXTO_XS, color=paleta.texto_sec,
                            expand=True),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_M, sombra=False,
            ))
    else:
        for indice, inc in enumerate(estado.incidencias):
            r = inc.ruta
            color_inc = paleta.exito if inc.resuelta else paleta.advertencia

            def alternar(ev, k=indice):
                incidencia = estado.incidencias[k]
                incidencia.resuelta = not incidencia.resuelta
                resuelta = incidencia.resuelta
                funciones.guardar_incidencias()
                estado.snack(
                    page,
                    f"Incidencia {'resuelta' if resuelta else 'reabierta'}.",
                    "exito" if resuelta else "aviso")
                refrescar()

            filas_incidencias.append(
                c.tarjeta(
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.FLAG, size=16,
                                    color=color_inc),
                            ft.Text(inc.tipo, size=TEXTO_S,
                                    weight=PESO_SEMIBOLD,
                                    color=paleta.texto, expand=True),
                            c.badge("Resuelta" if inc.resuelta
                                    else "Abierta",
                                    fondo=ft.Colors.with_opacity(
                                        0.18, color_inc),
                                    color_texto=color_inc),
                        ], spacing=theme.ESPACIO_S,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(inc.descripcion, size=TEXTO_XS,
                                color=paleta.texto_sec),
                        ft.Row([
                            ft.Text(
                                f"Ruta {r.numero if r else '—'} · "
                                f"{inc.hora} · {inc.reportado_por}",
                                size=TEXTO_XS, color=paleta.texto_sec,
                                expand=True),
                            c.boton("Reabrir" if inc.resuelta
                                    else "Resolver",
                                    estilo="texto", on_click=alternar,
                                    alto=32),
                        ], spacing=theme.ESPACIO_S,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ], spacing=theme.ESPACIO_S),
                    padding=theme.ESPACIO_M, sombra=False,
                ))

    def refrescar(ev=None):
        estado.desregistrar_ticks()
        args_seccion = [] if seccion == "usuarios" else [seccion]
        vista = vista_gestion(page, args_seccion)
        vista.route = page.route
        page.views[-1] = vista
        page.update()

    # Tarjeta de bienvenida (solo en la pantalla de usuarios)
    tarjeta_info = c.tarjeta(
        ft.Row([
            ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=22,
                    color=paleta.primario_claro),
            ft.Text("Administra cuentas, unidades, rutas e "
                    "incidencias: los cambios se aplican de "
                    "inmediato a toda la app.",
                    size=TEXTO_XS, color=paleta.texto_sec,
                    expand=True),
        ], spacing=theme.ESPACIO_M),
        padding=theme.ESPACIO_M,
        relleno=ft.Colors.with_opacity(0.10, paleta.primario),
        borde=False, sombra=False,
    )

    # Cuerpo de cada pantalla independiente del panel de administración
    cuerpos = {
        "usuarios": [
            tarjeta_info,
            c.seccion_titulo("Usuarios"),
            ft.Text("Creá cuentas nuevas desde el registro; aquí cambiás "
                    "roles, asignás unidades y eliminás cuentas.",
                    size=TEXTO_XS, color=paleta.texto_sec),
            ft.Column(filas_usuarios, spacing=theme.ESPACIO_S),
        ],
        "unidades": [
            c.seccion_titulo("Unidades"),
            ft.Text("Cambiá el estado operativo de cada unidad: en ruta, "
                    "mantenimiento o fuera de servicio.",
                    size=TEXTO_XS, color=paleta.texto_sec),
            ft.Column(filas_unidades, spacing=theme.ESPACIO_S),
        ],
        "rutas": [
            c.seccion_titulo("Rutas y estado del servicio"),
            ft.Text("Marcá el estado del servicio de cada ruta: normal, "
                    "con retraso o suspendido.",
                    size=TEXTO_XS, color=paleta.texto_sec),
            ft.Column(filas_rutas, spacing=theme.ESPACIO_S),
        ],
        "incidencias": [
            c.seccion_titulo("Incidencias reportadas"),
            ft.Text("Resolvé o reabrí los reportes que hacen los "
                    "viajeros desde el mapa.",
                    size=TEXTO_XS, color=paleta.texto_sec),
            ft.Column(filas_incidencias, spacing=theme.ESPACIO_S),
        ],
    }
    etiquetas = {"usuarios": "Usuarios", "unidades": "Unidades",
                 "rutas": "Rutas", "incidencias": "Incidencias"}

    contenido = ft.ListView([
        ft.Column(cuerpos[seccion] + [ft.Container(height=theme.ESPACIO_XL)],
                  spacing=theme.ESPACIO_M,
                  horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True, padding=ft.Padding(0, 0, 0, theme.ESPACIO_L))

    ruta_seccion = ("/gestion" if seccion == "usuarios"
                    else f"/gestion/{seccion}")

    return ft.View(
        route=page.route,
        bgcolor=paleta.fondo,
        appbar=c.app_bar(
            "Gestión del servicio", page,
            subtitulo=f"Solo administradores · {etiquetas[seccion]}",
            atras=False,
            acciones=[ft.IconButton(
                icon=ft.Icons.PERSON_OUTLINE,
                icon_color=paleta.texto,
                on_click=lambda e: estado.navegar(page, "/perfil"),
                tooltip="Mi perfil")],
            salir=True),
        navigation_bar=c.barra_admin(page, ruta_seccion),
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )
