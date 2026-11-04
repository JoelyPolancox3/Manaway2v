"""ManaWAY — punto de entrada."""
import flet as ft

from gui import theme
from gui.asistente import vista_asistente
from gui.buscar_ruta import vista_buscar
from gui.conductor import vista_conductor
from gui.detalle_ruta import vista_detalle_ruta
from gui.gestion import vista_gestion
from gui.home import vista_home
from gui.login import vista_login
from gui.navegar import vista_navegar
from gui.perfil import vista_perfil
from gui.planificador import vista_planificador
from gui.recuperar import vista_recuperar
from gui.registro import vista_registro
from gui.splash import vista_splash
from gui.unidades import vista_unidades
from modelo.estado import estado


def construir_vista(page: ft.Page) -> ft.View:
    """Devuelve la vista correspondiente a la ruta actual."""
    partes = [p for p in page.route.strip("/").split("/") if p]
    raiz = "/" + (partes[0] if partes else "")
    argumentos = partes[1:]

    constructores = {
        "/": vista_splash,
        "/login": vista_login,
        "/registro": vista_registro,
        "/recuperar": vista_recuperar,
        "/inicio": vista_home,
        "/buscar": vista_buscar,
        "/ruta": vista_detalle_ruta,
        "/navegar": vista_navegar,
        "/unidades": vista_unidades,
        "/planificar": vista_planificador,
        "/asistente": vista_asistente,
        "/perfil": vista_perfil,
        "/gestion": vista_gestion,
        "/conductor": vista_conductor,
    }
    constructor = constructores.get(raiz)
    if constructor is None:
        # Ruta desconocida: ir al inicio (o al login sin sesión)
        destino = "/inicio" if estado.hay_sesion() else "/login"
        page.route = destino
        raiz = destino
        constructor = constructores[raiz]

    return constructor(page, argumentos)


def main(page: ft.Page):
    paleta = theme.p()

    page.fonts = {
        theme.FUENTE: "fuentes/Rubik.ttf",
        theme.FUENTE_TITULOS: "fuentes/Alata.ttf",
    }
    page.theme = ft.Theme(font_family=theme.FUENTE)

    # 680 px: la ventana cabe en pantallas de 768 px y la barra
    # inferior queda siempre visible.
    page.title = "ManaWAY"
    page.window.width = 400
    page.window.height = 680
    page.window.min_width = 360
    page.window.min_height = 600
    page.window.bgcolor = paleta.fondo
    if hasattr(page.window, "center"):
        # center() es corrutina en Flet 1.0: en un handler síncrono
        # hay que agendarla en el event loop.
        import asyncio
        try:
            asyncio.get_running_loop().create_task(page.window.center())
        except RuntimeError:
            pass

    estado.arrancar(page)
    paleta = theme.p()

    def route_change(ev=None):
        estado.desregistrar_ticks()
        vista = construir_vista(page)
        page.views.clear()
        page.views.append(vista)
        page.update()

    def view_pop(ev=None):
        # Botón atrás del sistema: usar el historial propio
        if estado.historial:
            estado.navegar_atras(page)
        else:
            route_change()

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    def al_cerrar(ev=None):
        estado.detener_simulacion()

    page.on_close = al_cerrar

    estado.iniciar_simulacion()
    route_change()


if __name__ == "__main__":
    ft.run(main)
