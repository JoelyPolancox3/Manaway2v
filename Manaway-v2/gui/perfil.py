"""Pantalla de perfil de usuario: datos, preferencias y sesión."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import PESO_BOLD, PESO_SEMIBOLD, TEXTO_S, TEXTO_XS, p
from logica.utilidades import nombre_rol


def vista_perfil(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    usuario = estado.usuario
    if not usuario:
        # Sin sesión no hay perfil: volver al login
        estado.navegar(page, "/login", limpiar=True)
        return ft.View(route="/perfil", bgcolor=paleta.fondo, controls=[])

    # El perfil es de todos los roles. El viajero llega desde la barra
    # inferior; admin y conductor, desde el icono de su encabezado, así
    # que estos dos vuelven con la flecha atrás.
    viajero = not (usuario.es_admin or usuario.es_conductor)

    campo_nombre = c.campo("Nombre", valor=usuario.nombre,
                           icono=ft.Icons.BADGE_OUTLINED)
    campo_correo = c.campo("Correo", valor=usuario.correo,
                           icono=ft.Icons.MAIL_OUTLINE,
                           keyboard_type=ft.KeyboardType.EMAIL)
    campo_telefono = c.campo("Teléfono", valor=usuario.telefono,
                             icono=ft.Icons.PHONE_OUTLINED)
    campo_usuario = c.campo("Usuario", valor=usuario.usuario,
                            icono=ft.Icons.PERSON_OUTLINE, read_only=True)

    # Contraseña: solo de lectura aquí, se cambia en la sección Seguridad
    campo_clave_actual = c.campo(
        "Contraseña actual", icono=ft.Icons.LOCK_OUTLINE,
        password=True, can_reveal_password=True, hint_text="••••••")
    campo_clave_nueva = c.campo(
        "Nueva contraseña", icono=ft.Icons.PASSWORD,
        password=True, can_reveal_password=True, hint_text="••••••")
    campo_clave_confirmar = c.campo(
        "Confirmar contraseña", icono=ft.Icons.KEY,
        password=True, can_reveal_password=True, hint_text="••••••")

    def refrescar(ev=None):
        """Reconstruye la vista del perfil en el sitio."""
        estado.desregistrar_ticks()
        vista = vista_perfil(page, [])
        vista.route = page.route
        page.views[-1] = vista
        page.update()

    def cambiar_contrasena(ev):
        campo_clave_actual.error = None
        campo_clave_nueva.error = None
        campo_clave_confirmar.error = None
        u_nueva, error = funciones.cambiar_contrasena_propia(
            usuario.id,
            campo_clave_actual.value or "",
            campo_clave_nueva.value or "",
            campo_clave_confirmar.value or "")
        if error:
            # El mensaje de la lógica dice qué campo hay que corregir
            if "confirmación" in error:
                campo_clave_confirmar.error = error
            elif "actual" in error and "nueva" not in error:
                campo_clave_actual.error = error
            else:
                campo_clave_nueva.error = error
            page.update()
            return
        # La sesión abierta se queda con la contraseña nueva
        if u_nueva:
            usuario.contrasena = u_nueva.contrasena
        estado.snack(page, "Contraseña actualizada correctamente.", "exito")
        refrescar()

    def guardar(ev):
        nombre = campo_nombre.value.strip()
        if len(nombre) < 3:
            campo_nombre.error = "El nombre debe tener al menos 3 caracteres."
            page.update()
            return
        campo_nombre.error = None
        usuario.nombre = nombre
        usuario.correo = campo_correo.value.strip()
        usuario.telefono = campo_telefono.value.strip()
        from modelo import persistencia
        persistencia.actualizar_usuario(usuario)
        estado.snack(page, "Cambios guardados correctamente.", "exito")
        refrescar()

    switch_tema = ft.Switch(label="Tema oscuro",
                            value=theme.es_oscuro(),
                            active_color=paleta.primario,
                            label_text_style=ft.TextStyle(color=paleta.texto,
                                                          size=TEXTO_S),
                            on_change=lambda e: estado.aplicar_tema(
                                page, "oscuro" if e.control.value else "claro"))
    switch_sesion = ft.Switch(label="Recordar sesión",
                              value=estado.recordar_sesion,
                              active_color=paleta.primario,
                              label_text_style=ft.TextStyle(color=paleta.texto,
                                                            size=TEXTO_S),
                              on_change=lambda e: (
                                  setattr(estado, "recordar_sesion",
                                          e.control.value),
                                  estado.guardar_preferencias()))

    def tarjeta_favorito(titulo, subtitulo, icono, on_quitar):
        return c.tarjeta(
            ft.Row([
                ft.Icon(icono, size=20, color=paleta.acento),
                ft.Column([
                    ft.Text(titulo, size=TEXTO_S, weight=PESO_SEMIBOLD,
                            color=paleta.texto),
                    ft.Text(subtitulo, size=TEXTO_XS, color=paleta.texto_sec),
                ], spacing=1, expand=True),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=18,
                              icon_color=paleta.texto_sec, on_click=on_quitar,
                              tooltip="Quitar de favoritos"),
            ], spacing=theme.ESPACIO_M,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=theme.ESPACIO_M, sombra=False,
        )

    filas_favoritos = []
    for rid in sorted(estado.favoritos_rutas):
        r = funciones.ruta_por_id(rid)
        if r:
            def quitar_ruta(ev, rid=rid):
                estado.alternar_favorito_ruta(rid)
                refrescar()
            filas_favoritos.append(tarjeta_favorito(
                f"Ruta {r.numero}", r.nombre, ft.Icons.DIRECTIONS_BUS,
                quitar_ruta))
    for pid in sorted(estado.favoritos_paradas):
        par = funciones.parada_por_id(pid)
        if par:
            def quitar_parada(ev, pid=pid):
                estado.alternar_favorito_parada(pid)
                refrescar()
            filas_favoritos.append(tarjeta_favorito(
                par.nombre, "Parada", ft.Icons.STOP_CIRCLE_OUTLINED,
                quitar_parada))

    if not filas_favoritos:
        filas_favoritos.append(c.tarjeta(
            ft.Text("Todavía no tenés favoritos. Tocá la estrella de una "
                    "ruta o parada para guardarla.",
                    size=TEXTO_XS, color=paleta.texto_sec),
            padding=theme.ESPACIO_M, sombra=False,
        ))

    def cerrar_sesion(ev):
        estado.cerrar_sesion()
        estado.snack(page, "Sesión cerrada. ¡Hasta pronto!", "info")
        estado.navegar(page, "/login", limpiar=True)

    contenido = ft.ListView([
        ft.Column([
            c.tarjeta(
                ft.Row([
                    c.avatar(usuario.iniciales, radio=28),
                    ft.Column([
                        ft.Text(usuario.nombre, size=18, weight=PESO_BOLD,
                                color=paleta.texto),
                        ft.Text(f"@{usuario.usuario} · {nombre_rol(usuario.rol)}",
                                size=TEXTO_XS, color=paleta.texto_sec),
                    ], spacing=2, expand=True),
                ], spacing=theme.ESPACIO_M,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_L,
            ),
            c.seccion_titulo("Mis datos"),
            campo_nombre,
            campo_usuario,
            campo_correo,
            campo_telefono,
            c.boton("Guardar cambios", on_click=guardar,
                    icono=ft.Icons.SAVE_OUTLINED),
            ft.Container(height=theme.ESPACIO_XS),
            c.seccion_titulo("Seguridad"),
            ft.Text("Cambiá tu contraseña: pide la actual y la nueva "
                    "tiene que tener al menos 6 caracteres.",
                    size=TEXTO_XS, color=paleta.texto_sec),
            campo_clave_actual,
            campo_clave_nueva,
            campo_clave_confirmar,
            c.boton("Cambiar contraseña", on_click=cambiar_contrasena,
                    icono=ft.Icons.LOCK_RESET),
            ft.Container(height=theme.ESPACIO_XS),
            c.seccion_titulo("Preferencias"),
            c.tarjeta(
                ft.Column([
                    switch_tema,
                    c.divisor(),
                    switch_sesion,
                ], spacing=theme.ESPACIO_M),
                padding=theme.ESPACIO_L,
            ),
            c.seccion_titulo(
                f"Favoritos ({len(estado.favoritos_rutas) + len(estado.favoritos_paradas)})"),
            ft.Column(filas_favoritos, spacing=theme.ESPACIO_S),
            ft.Container(height=theme.ESPACIO_XS),
            c.boton("Cerrar sesión", on_click=cerrar_sesion,
                    icono=ft.Icons.LOGOUT, estilo="peligro"),
            ft.Container(
                content=ft.Text("ManaWAY 2.0 · Datos de demostración",
                                size=TEXTO_XS, color=paleta.texto_sec),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding(0, theme.ESPACIO_L, 0, theme.ESPACIO_L),
            ),
        ], spacing=theme.ESPACIO_M,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True, padding=ft.Padding(0, 0, 0, theme.ESPACIO_L))

    return ft.View(
        route="/perfil",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Mi perfil", page, atras=not viajero),
        navigation_bar=c.barra_inferior(page, "/perfil") if viajero else None,
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )
