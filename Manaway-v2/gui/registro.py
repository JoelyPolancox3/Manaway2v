"""Registro de usuarios con validación campo por campo."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import PESO_BOLD, PESO_SEMIBOLD, TEXTO_S, TEXTO_XS, p


def vista_registro(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()

    campo_nombre = c.campo("Nombre completo", icono=ft.Icons.BADGE_OUTLINED,
                           hint_text="Ana Pérez")
    campo_usuario = c.campo("Usuario", icono=ft.Icons.PERSON_OUTLINE,
                            hint_text="3 a 15 caracteres, sin espacios",
                            valor=estado.usuario_prellenado)
    campo_correo = c.campo("Correo (opcional)",
                           icono=ft.Icons.MAIL_OUTLINED,
                           hint_text="correo@ejemplo.com",
                           keyboard_type=ft.KeyboardType.EMAIL)
    campo_telefono = c.campo("Teléfono (opcional)",
                             icono=ft.Icons.PHONE_OUTLINED,
                             hint_text="8888-8888")
    campo_clave = c.campo("Contraseña", icono=ft.Icons.LOCK_OUTLINE,
                          password=True, can_reveal_password=True,
                          hint_text="Mínimo 6 caracteres")
    campo_confirmar = c.campo("Confirmar contraseña",
                              icono=ft.Icons.LOCK_RESET,
                              password=True, can_reveal_password=True)

    # ----- Medidor de fuerza en vivo -----
    barra_relleno = ft.Container(
        height=6, width=0, bgcolor="#F1706E",
        border_radius=ft.RoundedRectangleBorder(radius=3))
    pista_barra = ft.Container(
        content=ft.Row([barra_relleno], spacing=0),
        height=6, width=220, bgcolor=paleta.borde,
        border_radius=ft.RoundedRectangleBorder(radius=3))
    texto_fuerza = ft.Text("", size=TEXTO_XS, weight=PESO_SEMIBOLD)
    indicador_fuerza = ft.Row(
        [pista_barra, texto_fuerza],
        spacing=theme.ESPACIO_S,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        visible=False)

    indicador_coincide = ft.Row(
        [ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=15, color="#03C09C"),
         ft.Text("Las contraseñas coinciden", size=TEXTO_XS,
                 color="#03C09C", weight=PESO_SEMIBOLD)],
        spacing=6, visible=False)

    def al_cambiar_clave(ev=None):
        puntos, etiqueta, color = c.fuerza_clave(campo_clave.value or "")
        indicador_fuerza.visible = bool(campo_clave.value)
        texto_fuerza.value = etiqueta
        texto_fuerza.color = color
        # ancho proporcional sobre la pista de 220 px
        barra_relleno.width = int(220 * puntos / 4)
        barra_relleno.bgcolor = color
        campo_clave.error = None
        if campo_confirmar.value:
            coinciden = campo_confirmar.value == campo_clave.value
            indicador_coincide.visible = coinciden
            if coinciden:
                campo_confirmar.error = None
        page.update()

    def al_cambiar_confirmar(ev=None):
        coincide = (campo_confirmar.value == campo_clave.value
                    and bool(campo_confirmar.value))
        indicador_coincide.visible = coincide
        campo_confirmar.error = None
        page.update()

    campo_clave.on_change = al_cambiar_clave
    campo_confirmar.on_change = al_cambiar_confirmar

    # ----- Términos -----
    acepta = ft.Checkbox(
        label=ft.Text("Acepto los términos de uso y la política de "
                      "privacidad de ManaWAY.",
                      size=TEXTO_XS, color=paleta.texto_sec),
        fill_color=paleta.primario,
        check_color="#FFFFFF",
    )

    def _limpiar_errores():
        for campo in (campo_nombre, campo_usuario, campo_correo,
                      campo_telefono, campo_clave, campo_confirmar):
            campo.error = None

    def registrar(ev):
        _limpiar_errores()
        hubo_error = False

        # Validaciones de campo (la lógica final vive en funciones.py)
        if campo_confirmar.value != campo_clave.value:
            campo_confirmar.error = "Las contraseñas no coinciden."
            hubo_error = True
        if not acepta.value:
            hubo_error = True
            estado.snack(page, "Debés aceptar los términos de uso para "
                               "crear la cuenta.", "aviso")
        if hubo_error:
            page.update()
            return

        usuario, error = funciones.registrar_usuario(
            campo_nombre.value, campo_usuario.value, campo_clave.value,
            campo_correo.value, campo_telefono.value)
        if error:
            e = error.lower()
            if "usuario" in e:
                campo_usuario.error = error
            elif "correo" in e:
                campo_correo.error = error
            elif "teléfono" in e or "telefono" in e:
                campo_telefono.error = error
            elif "nombre" in e:
                campo_nombre.error = error
            elif "contrase" in e:
                campo_clave.error = error
            else:
                campo_usuario.error = error
            page.update()
            return

        estado.usuario_prellenado = usuario.usuario
        estado.navegar_atras(page)
        estado.snack(page, f"¡Cuenta creada! Bienvenido/a {usuario.nombre.split()[0]},"
                           " iniciá sesión para continuar.", "exito")

    contenido = ft.Column([
        c.boton("Ya tengo cuenta", on_click=lambda e: estado.navegar_atras(page),
                estilo="texto", icono=ft.Icons.ARROW_BACK),
        ft.Text("Crear cuenta", size=26, weight=PESO_BOLD,
                color=paleta.texto),
        ft.Text("Guardá tus rutas favoritas, tus paradas frecuentes y tus "
                "preferencias de tema.",
                size=TEXTO_S, color=paleta.texto_sec),
        ft.Container(height=theme.ESPACIO_S),
        campo_nombre,
        campo_usuario,
        campo_correo,
        campo_telefono,
        campo_clave,
        indicador_fuerza,
        campo_confirmar,
        indicador_coincide,
        acepta,
        ft.Container(height=theme.ESPACIO_XS),
        c.boton("Registrarme", on_click=registrar,
                icono=ft.Icons.PERSON_ADD_ALT, alto=48),
        ft.Container(height=theme.ESPACIO_L),
    ], spacing=theme.ESPACIO_M, expand=True)

    return ft.View(
        route="/registro",
        bgcolor=paleta.fondo,
        padding=ft.Padding(theme.ESPACIO_XL, theme.ESPACIO_L,
                           theme.ESPACIO_XL, theme.ESPACIO_XL),
        controls=[
            ft.ListView([contenido], spacing=0, expand=True),
        ],
    )
