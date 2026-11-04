"""Recuperación de contraseña en tres pasos con código simulado en pantalla."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import (PESO_BOLD, PESO_SEMIBOLD, RADIO_M, TEXTO_S, TEXTO_XS,
                       p)


def vista_recuperar(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    # Estado interno del flujo (solo vive en esta pantalla)
    sesion = {"cuenta": "", "usuario": "", "codigo": ""}

    # ---------- Paso 1: identificación ----------
    campo_cuenta = c.campo(
        "Usuario o correo", icono=ft.Icons.PERSON_SEARCH_OUTLINED,
        hint_text="tu_usuario · correo@ejemplo.com",
        on_submit=lambda e: solicitar(None))

    # ---------- Paso 2: código simulado ----------
    texto_destino = ft.Text("", size=TEXTO_XS, color=paleta.texto_sec)
    texto_codigo_demo = ft.Text("", size=30, weight=PESO_BOLD,
                                color=paleta.primario_claro,
                                text_align=ft.TextAlign.CENTER)
    campo_codigo = c.campo(
        "Código de 6 dígitos", icono=ft.Icons.PIN_OUTLINED,
        hint_text="000000", max_length=6,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_submit=lambda e: verificar(None))

    # ---------- Paso 3: contraseña nueva ----------
    campo_nueva = c.campo(
        "Nueva contraseña", icono=ft.Icons.LOCK_OUTLINE, password=True,
        can_reveal_password=True, hint_text="Mínimo 6 caracteres")
    campo_confirmar = c.campo(
        "Confirmar contraseña", icono=ft.Icons.LOCK_RESET, password=True,
        can_reveal_password=True)

    barra_relleno = ft.Container(
        height=6, width=0, bgcolor="#F1706E",
        border_radius=ft.RoundedRectangleBorder(radius=3))
    pista_barra = ft.Container(
        content=ft.Row([barra_relleno], spacing=0),
        height=6, width=220, bgcolor=paleta.borde,
        border_radius=ft.RoundedRectangleBorder(radius=3))
    texto_fuerza = ft.Text("", size=TEXTO_XS, weight=PESO_SEMIBOLD)
    indicador_fuerza = ft.Row([pista_barra, texto_fuerza],
                              spacing=theme.ESPACIO_S,
                              vertical_alignment=ft.CrossAxisAlignment.CENTER,
                              visible=False)
    indicador_coincide = ft.Row(
        [ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=15, color="#03C09C"),
         ft.Text("Las contraseñas coinciden", size=TEXTO_XS,
                 color="#03C09C", weight=PESO_SEMIBOLD)],
        spacing=6, visible=False)

    def al_cambiar_nueva(ev=None):
        puntos, etiqueta, color = c.fuerza_clave(campo_nueva.value or "")
        indicador_fuerza.visible = bool(campo_nueva.value)
        texto_fuerza.value = etiqueta
        texto_fuerza.color = color
        barra_relleno.width = int(220 * puntos / 4)
        barra_relleno.bgcolor = color
        campo_nueva.error = None
        if campo_confirmar.value and campo_confirmar.value == campo_nueva.value:
            indicador_coincide.visible = True
            campo_confirmar.error = None
        else:
            indicador_coincide.visible = False
        page.update()

    def al_cambiar_confirmar(ev=None):
        coincide = (bool(campo_confirmar.value)
                    and campo_confirmar.value == campo_nueva.value)
        indicador_coincide.visible = coincide
        campo_confirmar.error = None
        page.update()

    campo_nueva.on_change = al_cambiar_nueva
    campo_confirmar.on_change = al_cambiar_confirmar

    # ---------- Navegación entre pasos ----------
    def paso_chips(actual: int) -> ft.Row:
        """Indicador «1 Cuenta · 2 Código · 3 Contraseña»."""
        pasos = [("1", "Cuenta"), ("2", "Código"), ("3", "Contraseña")]
        filas = []
        for numero, etiqueta in pasos:
            activo = int(numero) == actual
            filas.append(ft.Container(
                content=ft.Row([
                    ft.Text(numero, size=TEXTO_XS, weight=PESO_BOLD,
                            color="#FFFFFF" if activo else paleta.texto_sec),
                    ft.Text(etiqueta, size=TEXTO_XS,
                            weight=PESO_SEMIBOLD if activo else None,
                            color=paleta.texto if activo else paleta.texto_sec),
                ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.Padding(9, 4, 9, 4),
                bgcolor=(ft.Colors.with_opacity(0.20, paleta.primario)
                         if activo else paleta.superficie_2),
                border_radius=ft.RoundedRectangleBorder(radius=RADIO_M),
            ))
        return ft.Row(filas, spacing=theme.ESPACIO_S,
                      alignment=ft.MainAxisAlignment.CENTER)

    def mostrar_paso(n: int):
        cuerpo_paso1.visible = n == 1
        cuerpo_paso2.visible = n == 2
        cuerpo_paso3.visible = n == 3
        page.update()

    # ---------- Acciones ----------
    def solicitar(ev):
        campo_cuenta.error = None
        ok, error, codigo = funciones.solicitar_recuperacion(campo_cuenta.value)
        if not ok:
            campo_cuenta.error = error
            page.update()
            return
        u = funciones.buscar_cuenta(campo_cuenta.value)
        sesion["cuenta"] = campo_cuenta.value.strip()
        sesion["usuario"] = u.usuario if u else ""
        sesion["codigo"] = codigo or ""
        destino = (u.correo or f"usuario «{u.usuario}»") if u else ""
        texto_destino.value = f"Enviado a {destino}"
        texto_codigo_demo.value = codigo or ""
        campo_codigo.value = ""
        mostrar_paso(2)

    def verificar(ev):
        campo_codigo.error = None
        ok, error = funciones.verificar_codigo(sesion["usuario"],
                                               campo_codigo.value)
        if not ok:
            campo_codigo.error = error
            page.update()
            return
        campo_nueva.value = ""
        campo_confirmar.value = ""
        indicador_fuerza.visible = False
        indicador_coincide.visible = False
        mostrar_paso(3)

    def guardar(ev):
        campo_nueva.error = None
        campo_confirmar.error = None
        if campo_confirmar.value != campo_nueva.value:
            campo_confirmar.error = "Las contraseñas no coinciden."
            page.update()
            return
        ok, error = funciones.restablecer_contrasena(
            sesion["usuario"], sesion["codigo"], campo_nueva.value)
        if not ok:
            campo_nueva.error = error
            page.update()
            return
        estado.usuario_prellenado = sesion["usuario"]
        estado.mensaje_flash = None
        estado.navegar(page, "/login", limpiar=True)
        estado.snack(page, "¡Contraseña actualizada! Iniciá sesión con tu "
                           "nueva contraseña.", "exito")

    cuerpo_paso1 = ft.Column([
        paso_chips(1),
        ft.Text("Recuperar contraseña", size=24, weight=PESO_BOLD,
                color=paleta.texto),
        ft.Text("Sin correo real: este es un prototipo, así que el código "
                "se mostrará en la siguiente pantalla.",
                size=TEXTO_S, color=paleta.texto_sec),
        campo_cuenta,
        c.boton("Enviar código", on_click=solicitar,
                icono=ft.Icons.MAIL_OUTLINE, alto=48),
    ], spacing=theme.ESPACIO_L, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    cuerpo_paso2 = ft.Column([
        paso_chips(2),
        c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.MAIL_OUTLINED, size=20,
                            color=paleta.primario_claro),
                    ft.Text("Correo simulado", size=TEXTO_S,
                            weight=PESO_SEMIBOLD, color=paleta.texto),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                texto_destino,
                ft.Container(height=theme.ESPACIO_XS),
                texto_codigo_demo,
                ft.Text(f"Vigencia: {funciones.VIGENCIA_CODIGO_MIN} minutos "
                        f"· hasta {funciones.MAX_INTENTOS_CODIGO} intentos",
                        size=TEXTO_XS, color=paleta.texto_sec,
                        text_align=ft.TextAlign.CENTER),
            ], spacing=theme.ESPACIO_S,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            relleno=ft.Colors.with_opacity(0.10, paleta.primario),
            borde=False, sombra=False,
        ),
        campo_codigo,
        c.boton("Verificar código", on_click=verificar,
                icono=ft.Icons.VPN_KEY_OUTLINED, alto=48),
        ft.Row([
            c.boton("Reenviar código", on_click=lambda e: solicitar(None),
                    estilo="texto", alto=36),
            c.boton("Volver", on_click=lambda e: mostrar_paso(1),
                    estilo="texto", alto=36),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    ], spacing=theme.ESPACIO_M, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    cuerpo_paso3 = ft.Column([
        paso_chips(3),
        ft.Text("Nueva contraseña", size=24, weight=PESO_BOLD,
                color=paleta.texto),
        ft.Text("Elegí una clave que no uses en otras cuentas.",
                size=TEXTO_S, color=paleta.texto_sec),
        campo_nueva,
        indicador_fuerza,
        campo_confirmar,
        indicador_coincide,
        c.boton("Guardar contraseña", on_click=guardar,
                icono=ft.Icons.SAVE_OUTLINED, alto=48),
    ], spacing=theme.ESPACIO_M, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    cuerpo_paso1.visible = True
    cuerpo_paso2.visible = False
    cuerpo_paso3.visible = False

    contenido = ft.Column([
        c.boton("Volver al inicio de sesión",
                on_click=lambda e: estado.navegar_atras(page),
                estilo="texto", icono=ft.Icons.ARROW_BACK),
        cuerpo_paso1,
        cuerpo_paso2,
        cuerpo_paso3,
    ], spacing=theme.ESPACIO_L, expand=True)

    return ft.View(
        route="/recuperar",
        bgcolor=paleta.fondo,
        padding=ft.Padding(theme.ESPACIO_XL, theme.ESPACIO_L,
                           theme.ESPACIO_XL, theme.ESPACIO_XL),
        controls=[ft.ListView([contenido], spacing=0, expand=True)],
    )
