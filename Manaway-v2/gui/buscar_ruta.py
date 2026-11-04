"""Pantalla de búsqueda de rutas."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import (PESO_BOLD, PESO_SEMIBOLD, TEXTO_L, TEXTO_S, TEXTO_XS,
                       TEXTO_XXS, p)

FILTROS = [
    ("todas", "Todas", ft.Icons.LIST_ALT),
    ("activas", "En servicio", ft.Icons.CHECK_CIRCLE_OUTLINE),
    ("favoritas", "Favoritas", ft.Icons.STAR_BORDER),
    ("retraso", "Con retraso", ft.Icons.WARNING_AMBER_OUTLINED),
]

# Algoritmos de ordenamiento seleccionables (ordenamientos.py)
ALGORITMOS_ORDEN = [
    ("insercion", "Inserción"),
    ("burbuja", "Burbuja"),
    ("seleccion", "Selección"),
]


def vista_buscar(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    # Pantalla del viajero: otros roles vuelven a su interfaz propia.
    u_rol = estado.usuario
    if u_rol and (u_rol.es_admin or u_rol.es_conductor):
        estado.navegar(page, "/gestion" if u_rol.es_admin else "/conductor",
                       limpiar=True)
        return ft.View(route="/buscar", bgcolor=paleta.fondo, controls=[])
    filtro_actual = {"valor": "todas"}
    # Criterio y algoritmo de ordenamiento de los resultados
    orden_actual = {"criterio": "numero", "algoritmo": "insercion"}

    campo_busqueda = c.campo(
        "Buscar", icono=ft.Icons.SEARCH,
        hint_text="Número, ruta, parada…",
        on_change=lambda e: actualizar(),
    )

    resultados = ft.Column(spacing=theme.ESPACIO_S,
                           horizontal_alignment=ft.CrossAxisAlignment.START)
    contador = ft.Text(size=TEXTO_S, color=paleta.texto_sec)
    comparacion_ctrl = ft.Container()
    orden_ctrl = ft.Container()

    def _mini_algoritmo(titulo, datos_alg, color, descripcion) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo, size=TEXTO_XS, weight=PESO_SEMIBOLD,
                        color=paleta.texto_sec),
                ft.Row([
                    ft.Text(str(datos_alg["pasos"]), size=TEXTO_L,
                            weight=PESO_BOLD, color=color),
                    ft.Text("pasos", size=TEXTO_XS, color=paleta.texto_sec),
                ], spacing=3,
                    vertical_alignment=ft.CrossAxisAlignment.END),
                ft.Text(descripcion, size=TEXTO_XXS, color=paleta.texto_sec),
            ], spacing=2),
            padding=ft.Padding(theme.ESPACIO_M, theme.ESPACIO_S,
                               theme.ESPACIO_M, theme.ESPACIO_S),
            bgcolor=paleta.superficie_2,
            border_radius=theme.RADIO_M,
            expand=True,
        )

    def construir_comparacion(valor: str) -> ft.Container:
        """Tarjeta pedagógica: pasos de la búsqueda lineal vs. binaria."""
        comp = funciones.comparar_busquedas(valor)
        if comp["lineal"] is None:
            cuerpo = ft.Text(
                "Escribí un número de ruta (ej.: 106) para comparar cuántos "
                "pasos realiza cada algoritmo de búsqueda.",
                size=TEXTO_XS, color=paleta.texto_sec)
        else:
            lin, binaria = comp["lineal"], comp["binaria"]
            if not lin["encontrado"]:
                veredicto = (
                    f"Ninguno lo encuentra: la lineal revisó las "
                    f"{comp['peor_lineal']} rutas y la binaria descartó la "
                    f"mitad en solo {binaria['pasos']} pasos.")
            elif binaria["pasos"] < lin["pasos"]:
                veces = lin["pasos"] / max(binaria["pasos"], 1)
                veredicto = (
                    f"Gana la binaria: {binaria['pasos']} pasos frente a "
                    f"{lin['pasos']} de la lineal "
                    f"(hasta {veces:.0f}× menos comparaciones).")
            elif lin["pasos"] < binaria["pasos"]:
                veredicto = (
                    f"Gana la lineal: el número estaba al principio "
                    f"({lin['pasos']} pasos).")
            else:
                veredicto = (f"Empate: ambos algoritmos realizaron "
                             f"{lin['pasos']} pasos.")
            cuerpo = ft.Column([
                ft.Row([
                    _mini_algoritmo("Lineal", lin, paleta.primario_claro,
                                    "revisa 1 por 1"),
                    _mini_algoritmo("Binaria", binaria, paleta.acento,
                                    "descarta la mitad"),
                ], spacing=theme.ESPACIO_S),
                ft.Row([
                    ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=15,
                            color=paleta.advertencia),
                    ft.Text(veredicto, size=TEXTO_XS,
                            color=paleta.texto_sec, expand=True),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Text(
                    f"Sobre {comp['total']} rutas ordenadas por número · "
                    f"peor caso: lineal {comp['peor_lineal']} · binaria "
                    f"{comp['peor_binaria']} (precondición: lista ordenada).",
                    size=TEXTO_XXS, color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_S)
        return c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.FUNCTIONS, size=17, color=paleta.acento),
                    ft.Text("Búsqueda lineal vs. binaria",
                            size=TEXTO_S, weight=PESO_SEMIBOLD,
                            color=paleta.texto),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                cuerpo,
            ], spacing=theme.ESPACIO_S),
            padding=theme.ESPACIO_M,
            sombra=False,
        )

    def construir_ordenamiento(rutas, pasos_orden) -> ft.Container:
        """Tarjeta pedagógica: pasos de burbuja, inserción y selección."""
        comp = funciones.comparar_ordenamientos_rutas(
            orden_actual["criterio"], rutas=rutas)
        nombres = dict(ALGORITMOS_ORDEN)
        criterio = funciones.ETIQUETAS_ORDEN.get(
            orden_actual["criterio"], "Número").lower()
        if not rutas:
            cuerpo = ft.Text(
                "Sin rutas para ordenar: quitá los filtros para comparar "
                "cuántas comparaciones realiza cada algoritmo.",
                size=TEXTO_XS, color=paleta.texto_sec)
        else:
            cuerpo = ft.Column([
                ft.Row([
                    _mini_algoritmo("Burbuja", {"pasos": comp["burbuja"]},
                                    paleta.primario_claro,
                                    "compara vecinos"),
                    _mini_algoritmo("Inserción", {"pasos": comp["insercion"]},
                                    paleta.acento, "inserta en su lugar"),
                    _mini_algoritmo("Selección", {"pasos": comp["seleccion"]},
                                    paleta.advertencia, "elige el mínimo"),
                ], spacing=theme.ESPACIO_S),
                ft.Text(
                    f"Orden actual: por {criterio} con "
                    f"{nombres.get(orden_actual['algoritmo'], 'Inserción')} "
                    f"({pasos_orden} comparaciones) · peor caso teórico "
                    f"O(n²): {comp['peor_caso']} sobre {comp['total']} rutas.",
                    size=TEXTO_XXS, color=paleta.texto_sec),
            ], spacing=theme.ESPACIO_S)
        return c.tarjeta(
            ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.SORT, size=17, color=paleta.acento),
                    ft.Text("Ordenamiento: burbuja, inserción y selección",
                            size=TEXTO_S, weight=PESO_SEMIBOLD,
                            color=paleta.texto),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                cuerpo,
            ], spacing=theme.ESPACIO_S),
            padding=theme.ESPACIO_M,
            sombra=False,
        )

    def aplicar_filtro(rutas):
        filtro = filtro_actual["valor"]
        if filtro == "activas":
            return [r for r in rutas if r.estado != "suspendido"]
        if filtro == "favoritas":
            return [r for r in rutas if estado.es_favorita_ruta(r.id)]
        if filtro == "retraso":
            return [r for r in rutas if r.estado in ("retraso", "suspendido")]
        return rutas

    def elegir_orden(campo):
        """Handler de los dropdowns de orden (criterio y algoritmo)."""
        def handler(ev):
            valor = ev.data or ev.control.value
            if valor:
                orden_actual[campo] = valor
                actualizar()
        return handler

    selector_criterio = ft.Dropdown(
        value="numero",
        options=[ft.DropdownOption(key=clave, text=etiqueta)
                 for clave, etiqueta in funciones.ETIQUETAS_ORDEN.items()],
        text_size=TEXTO_XS, color=paleta.texto, bgcolor=paleta.superficie_2,
        border=c.bordes_formulario(10), label_style=None,
        menu_width=170, width=140,
        on_select=elegir_orden("criterio"),
    )
    selector_algoritmo = ft.Dropdown(
        value="insercion",
        options=[ft.DropdownOption(key=clave, text=etiqueta)
                 for clave, etiqueta in ALGORITMOS_ORDEN],
        text_size=TEXTO_XS, color=paleta.texto, bgcolor=paleta.superficie_2,
        border=c.bordes_formulario(10),
        menu_width=160, width=125,
        on_select=elegir_orden("algoritmo"),
    )
    fila_orden = ft.Row([
        ft.Icon(ft.Icons.SWAP_VERT, size=15, color=paleta.texto_sec),
        ft.Text("Ordenar por", size=TEXTO_XS, color=paleta.texto_sec),
        selector_criterio,
        selector_algoritmo,
    ], spacing=theme.ESPACIO_S,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO)

    def actualizar(ev=None):
        rutas = funciones.buscar_rutas(campo_busqueda.value)
        rutas = aplicar_filtro(rutas)
        # Ordenamiento con el algoritmo clásico elegido (curso)
        rutas, pasos_orden = funciones.ordenar_rutas(
            orden_actual["criterio"], orden_actual["algoritmo"], rutas=rutas)
        contador.value = (f"{len(rutas)} "
                          f"{'ruta encontrada' if len(rutas) == 1 else 'rutas encontradas'}")
        orden_ctrl.content = construir_ordenamiento(rutas, pasos_orden)
        comparacion_ctrl.content = construir_comparacion(campo_busqueda.value)
        resultados.controls.clear()
        if not rutas:
            resultados.controls.append(c.estado_vacio(
                ft.Icons.SEARCH_OFF,
                "Sin resultados",
                "Probá con otro número, nombre de ruta o parada.",
                accion_texto="Limpiar búsqueda",
                on_accion=lambda e: (setattr(campo_busqueda, "value", ""),
                                     setattr(filtro_actual, "valor", "todas"),
                                     refrescar_chips(), actualizar())))
        else:
            for r in rutas:
                resultados.controls.append(c.tarjeta_ruta(page, r))
        page.update()

    chips_refs: dict[str, ft.Chip] = {}

    def refrescar_chips():
        for clave, chip in chips_refs.items():
            chip.selected = clave == filtro_actual["valor"]

    def elegir_filtro(clave):
        def handler(ev):
            filtro_actual["valor"] = clave
            refrescar_chips()
            actualizar()
        return handler

    chips = []
    for clave, texto, icono in FILTROS:
        chip_ctrl = c.chip(texto, icono=icono,
                           seleccionado=(clave == "todas"),
                           on_click=elegir_filtro(clave))
        chips_refs[clave] = chip_ctrl
        chips.append(chip_ctrl)
    fila_chips = ft.Row(chips, spacing=theme.ESPACIO_S,
                        scroll=ft.ScrollMode.AUTO)

    contenido = ft.ListView([
        ft.Column([
            campo_busqueda,
            ft.Container(content=fila_chips),
            ft.Container(content=fila_orden),
            contador,
            orden_ctrl,
            comparacion_ctrl,
            resultados,
            ft.Container(height=theme.ESPACIO_XL),
        ], spacing=theme.ESPACIO_M,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True, padding=ft.Padding(0, 0, 0, theme.ESPACIO_L))

    actualizar()

    return ft.View(
        route="/buscar",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Buscar rutas", page, atras=False),
        navigation_bar=c.barra_inferior(page, "/buscar"),
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )
