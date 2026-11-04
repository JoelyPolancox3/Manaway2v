"""Estado global: sesión, favoritos, tema, navegación y simulación."""
import asyncio
import logging
from typing import Callable, Optional

import flet as ft

from logica import funciones
from modelo import persistencia
from modelo.entidades import Incidencia, Usuario
from gui import theme

logger = logging.getLogger("manaway")

SEGUNDOS_POR_TICK = 2.5


class EstadoApp:
    def __init__(self):
        self.usuario: Optional[Usuario] = None
        self.tema: str = "oscuro"
        self.recordar_sesion: bool = True
        self.historial: list[str] = []
        self.favoritos_rutas: set[int] = set()
        self.favoritos_paradas: set[int] = set()
        self.mensaje_flash: Optional[str] = None
        self.usuario_prellenado: str = ""
        self.filtro_unidades: Optional[int] = None
        self.incidencias: list[Incidencia] = []
        self._ticks: list[Callable] = []
        self._tarea_simulacion: Optional[asyncio.Task] = None

    # ---------- Arranque ----------
    def arrancar(self, page: ft.Page) -> None:
        """Carga preferencias, sesión e incidencias guardadas."""
        pref = persistencia.cargar_preferencias()
        self.tema = pref.get("tema", "oscuro")
        self.recordar_sesion = pref.get("recordar_sesion", True)
        theme.fijar_tema(self.tema)
        page.theme_mode = ft.ThemeMode.DARK if self.tema == "oscuro" else ft.ThemeMode.LIGHT
        page.bgcolor = theme.p().fondo
        # Incidencias persistidas en datos_persistidos/incidencias.json
        funciones.cargar_incidencias()
        if self.recordar_sesion:
            usuario = persistencia.cargar_sesion()
            if usuario:
                u = funciones.usuario_por_nombre(usuario)
                if not u:
                    from modelo import datos
                    u = next((x for x in datos.usuarios
                              if x.usuario.lower() == usuario.lower()), None)
                if u:
                    self.iniciar_sesion(u, recordar=True)

    # ---------- Sesión ----------
    def iniciar_sesion(self, usuario: Usuario, recordar: bool = True) -> None:
        self.usuario = usuario
        self.recordar_sesion = recordar
        if recordar:
            persistencia.guardar_sesion(usuario.usuario)
        else:
            persistencia.borrar_sesion()
        self.cargar_favoritos()

    def cerrar_sesion(self) -> None:
        self.usuario = None
        self.favoritos_rutas.clear()
        self.favoritos_paradas.clear()
        self.historial.clear()
        persistencia.borrar_sesion()

    def hay_sesion(self) -> bool:
        return self.usuario is not None

    # ---------- Favoritos ----------
    def cargar_favoritos(self) -> None:
        if not self.usuario:
            self.favoritos_rutas.clear()
            self.favoritos_paradas.clear()
            return
        fav = persistencia.cargar_favoritos(self.usuario.id)
        self.favoritos_rutas = set(int(i) for i in fav.get("rutas", []))
        self.favoritos_paradas = set(int(i) for i in fav.get("paradas", []))

    def guardar_favoritos(self) -> None:
        if self.usuario:
            persistencia.guardar_favoritos(
                self.usuario.id, self.favoritos_rutas, self.favoritos_paradas)

    def es_favorita_ruta(self, ruta_id: int) -> bool:
        return int(ruta_id) in self.favoritos_rutas

    def alternar_favorito_ruta(self, ruta_id: int) -> bool:
        """Alterna el favorito de una ruta. Devuelve True si quedó como favorita."""
        ruta_id = int(ruta_id)
        if ruta_id in self.favoritos_rutas:
            self.favoritos_rutas.discard(ruta_id)
            resultado = False
        else:
            self.favoritos_rutas.add(ruta_id)
            resultado = True
        self.guardar_favoritos()
        return resultado

    def es_favorita_parada(self, parada_id: int) -> bool:
        return int(parada_id) in self.favoritos_paradas

    def alternar_favorito_parada(self, parada_id: int) -> bool:
        parada_id = int(parada_id)
        if parada_id in self.favoritos_paradas:
            self.favoritos_paradas.discard(parada_id)
            resultado = False
        else:
            self.favoritos_paradas.add(parada_id)
            resultado = True
        self.guardar_favoritos()
        return resultado

    # ---------- Preferencias ----------
    def guardar_preferencias(self) -> None:
        persistencia.guardar_preferencias(self.tema, self.recordar_sesion)

    def aplicar_tema(self, page: ft.Page, nombre: str) -> None:
        self.tema = "claro" if nombre == "claro" else "oscuro"
        theme.fijar_tema(self.tema)
        page.theme_mode = ft.ThemeMode.DARK if self.tema == "oscuro" else ft.ThemeMode.LIGHT
        p = theme.p()
        page.bgcolor = p.fondo
        try:
            page.window.bgcolor = p.fondo
        except Exception:
            pass
        self.guardar_preferencias()

    # ---------- Navegación ----------
    def navegar(self, page: ft.Page, ruta: str, limpiar: bool = False) -> None:
        if limpiar:
            self.historial.clear()
        elif page.route and page.route != ruta:
            self.historial.append(page.route)
            if len(self.historial) > 30:
                self.historial.pop(0)
        page.navigate(ruta)

    def navegar_atras(self, page: ft.Page) -> None:
        ruta = self.historial.pop() if self.historial else "/inicio"
        page.navigate(ruta)

    # ---------- Avisos ----------
    def snack(self, page: ft.Page, texto: str, tipo: str = "info") -> None:
        p = theme.p()
        colores = {"info": p.primario, "exito": p.exito,
                   "error": p.error, "aviso": p.advertencia}
        page.show_dialog(ft.SnackBar(
            ft.Text(texto, color="#FFFFFF", size=13),
            bgcolor=colores.get(tipo, p.primario),
            duration=ft.Duration(milliseconds=3200),
        ))

    # ---------- Simulación en vivo ----------
    def registrar_tick(self, callback: Callable) -> None:
        self._ticks.append(callback)

    def desregistrar_ticks(self) -> None:
        self._ticks.clear()

    def notificar_tick(self) -> None:
        for cb in list(self._ticks):
            try:
                cb()
            except Exception:
                logger.exception("Error en callback de simulación")

    def iniciar_simulacion(self) -> None:
        if self._tarea_simulacion and not self._tarea_simulacion.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._tarea_simulacion = loop.create_task(self._bucle_simulacion())

    def detener_simulacion(self) -> None:
        if self._tarea_simulacion and not self._tarea_simulacion.done():
            self._tarea_simulacion.cancel()
        self._tarea_simulacion = None

    async def _bucle_simulacion(self) -> None:
        while True:
            await asyncio.sleep(SEGUNDOS_POR_TICK)
            try:
                funciones.avanzar_unidades(SEGUNDOS_POR_TICK / 3600)
                self.notificar_tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error en la simulación de unidades")


# Instancia global
estado = EstadoApp()
