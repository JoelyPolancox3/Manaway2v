"""Pantalla de inicio de sesión."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import PESO_BOLD, PESO_SEMIBOLD, TEXTO_S, TEXTO_XS, p


def vista_login(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()

    campo_usuario = c.campo(
        "Usuario", valor=estado.usuario_prellenado,
        icono=ft.Icons.PERSON_OUTLINE, hint_text="tu_usuario",
        autofocus=not bool(estado.usuario_prellenado))
    campo_clave = c.campo(
        "Contraseña", icono=ft.Icons.LOCK_OUTLINE, password=True,
        can_reveal_password=True, hint_text="••••••",
        on_submit=lambda e: intentar_ingresar(None))
    recordar = ft.Switch(label="Recordar sesión", value=estado.recordar_sesion,
                         active_color=paleta.primario,
                         label_text_style=ft.TextStyle(
                             color=paleta.texto, size=TEXTO_S))

    def intentar_ingresar(ev):
        campo_usuario.error = None
        campo_clave.error = None
        usuario = campo_usuario.value.strip()
        clave = campo_clave.value
        if not usuario:
            campo_usuario.error = "Escribe tu usuario."
            page.update()
            return
        if not clave:
            campo_clave.error = "Escribe tu contraseña."
            page.update()
            return
        u = funciones.buscar_por_credenciales(usuario, clave)
        if not u:
            campo_clave.error = "Usuario o contraseña incorrectos."
            estado.usuario_prellenado = usuario
            page.update()
            return
        estado.usuario_prellenado = ""
        estado.mensaje_flash = None
        estado.iniciar_sesion(u, recordar=recordar.value)
        # Cada rol entra directo a su interfaz: conductor a su panel y
        # administrador a la gestión del servicio.
        destino = ("/gestion" if u.es_admin
                   else "/conductor" if u.es_conductor
                   else "/inicio")
        estado.navegar(page, destino, limpiar=True)
        estado.snack(page, f"¡Bienvenido, {u.nombre.split()[0]}!", "exito")

    def ir_a_registro(ev):
        estado.usuario_prellenado = campo_usuario.value.strip()
        estado.navegar(page, "/registro")

    def ir_a_recuperar(ev):
        estado.usuario_prellenado = campo_usuario.value.strip()
        estado.navegar(page, "/recuperar")

    contenido = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(ft.Icons.DIRECTIONS_BUS, size=40,
                                    color="#FFFFFF"),
                    width=82, height=82,
                    bgcolor=paleta.profundo,
                    border_radius=ft.RoundedRectangleBorder(radius=22),
                    alignment=ft.Alignment.CENTER,
                    shadow=paleta.sombra,
                ),
                ft.Text("ManaWAY", size=24, weight=PESO_BOLD,
                        color=paleta.texto,
                        font_family=theme.FUENTE_TITULOS),
                ft.Text("Ingresa para ver tu transporte en vivo",
                        size=TEXTO_S, color=paleta.texto_sec),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=theme.ESPACIO_S),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(0, theme.ESPACIO_L, 0, theme.ESPACIO_XL),
        ),
        ft.Container(
            content=ft.Column([
                campo_usuario,
                campo_clave,
                ft.Row([
                    recordar,
                    c.boton("¿Olvidaste tu contraseña?",
                            on_click=ir_a_recuperar, estilo="texto",
                            alto=36),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                c.boton("Ingresar", on_click=intentar_ingresar,
                        icono=ft.Icons.LOGIN, alto=48),
            ], spacing=theme.ESPACIO_L),
        ),
        ft.Container(height=theme.ESPACIO_M),
        c.tarjeta(
            ft.Row([
                ft.Icon(ft.Icons.PERSON_ADD_ALT, size=20,
                        color=paleta.primario_claro),
                ft.Text("¿No tenés cuenta?", size=TEXTO_S,
                        color=paleta.texto_sec),
                c.boton("Creá una", on_click=ir_a_registro,
                        estilo="texto", alto=38),
            ], spacing=theme.ESPACIO_S,
                alignment=ft.MainAxisAlignment.CENTER),
            padding=theme.ESPACIO_S,
            relleno=paleta.superficie_2,
        ),
        c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                            color=paleta.advertencia),
                    ft.Text("Cuentas de prueba", size=TEXTO_XS,
                            weight=PESO_SEMIBOLD, color=paleta.advertencia),
                ], spacing=theme.ESPACIO_S),
                ft.Text("Usuario: tim · Contraseña: 1234\n"
                        "Usuario: admin · Contraseña: admin123\n"
                        "Usuario: conductor · Contraseña: conductor123",
                        size=TEXTO_XS, color=paleta.texto_sec,
                        selectable=True),
            ], spacing=theme.ESPACIO_S),
            padding=theme.ESPACIO_M,
            relleno=ft.Colors.with_opacity(0.10, paleta.advertencia),
            borde=False,
            sombra=False,
        ),
    ], spacing=theme.ESPACIO_L, expand=True)

    return ft.View(
        route="/login",
        bgcolor=paleta.fondo,
        padding=ft.Padding(theme.ESPACIO_XL, theme.ESPACIO_XXL,
                           theme.ESPACIO_XL, theme.ESPACIO_XL),
        controls=[contenido],
    )
