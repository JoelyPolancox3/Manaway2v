"""Incidencias reportadas por el conductor, con su estado actual."""
import flet as ft

from logica import funciones
from modelo.estado import estado
from gui import componentes as c
from gui import theme
from gui.theme import (PESO_SEMIBOLD, TEXTO_S, TEXTO_XS,
                       p)


def vista_mis_incidencias(page: ft.Page, args: list = None) -> ft.View:
    paleta = p()
    usuario = estado.usuario
    if not usuario or not usuario.es_conductor:
        destino = ("/gestion" if usuario and usuario.es_admin else "/inicio")
        estado.snack(page, "Se requiere una cuenta de conductor.", "error")
        estado.navegar(page, destino, limpiar=True)
        return ft.View(route="/conductor/incidencias",
                       bgcolor=paleta.fondo, controls=[])

    unidad = funciones.unidad_por_id(usuario.unidad_id)
    ruta = funciones.ruta_por_id(unidad.ruta_id) if unidad else None

    def reportar(ev):
        from gui import dialog_incidencia
        dialog_incidencia.abrir(page, ruta.id if ruta else None)

    mis = funciones.incidencias_de_usuario(usuario.nombre)

    filas = []
    if not mis:
        filas.append(
            c.tarjeta(
                ft.Row([
                    ft.Icon(ft.Icons.FLAG_OUTLINED, size=20,
                            color=paleta.texto_sec),
                    ft.Text("Todavía no reportaste incidencias. Si notás un "
                            "accidente, desvío o falla en tu recorrido, "
                            "usá «Reportar incidencia».",
                            size=TEXTO_XS, color=paleta.texto_sec,
                            expand=True),
                ], spacing=theme.ESPACIO_S,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=theme.ESPACIO_L, sombra=False,
            ))
    else:
        for inc in mis:
            color_inc = paleta.exito if inc.resuelta else paleta.advertencia
            detalle_ruta = f"Ruta {inc.ruta.numero}"
            if inc.parada:
                detalle_ruta += f" · Parada {inc.parada.nombre}"
            filas.append(
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
                        ft.Text(f"{detalle_ruta} · {inc.hora}",
                                size=TEXTO_XS, color=paleta.texto_sec),
                    ], spacing=theme.ESPACIO_S),
                    padding=theme.ESPACIO_M, sombra=False,
                ))

    contenido = ft.ListView([
        ft.Column([
            c.boton("Reportar incidencia", on_click=reportar,
                    icono=ft.Icons.FLAG_OUTLINED,
                    estilo="contorneado" if ruta else None) if ruta
            else c.tarjeta(
                ft.Text("Sin ruta asignada no podés reportar incidencias.",
                        size=TEXTO_XS, color=paleta.texto_sec),
                padding=theme.ESPACIO_M, sombra=False),
            c.seccion_titulo(f"Reportadas por vos ({len(mis)})"),
            ft.Column(filas, spacing=theme.ESPACIO_S),
            ft.Container(height=theme.ESPACIO_XL),
        ], spacing=theme.ESPACIO_M,
            horizontal_alignment=ft.CrossAxisAlignment.START),
    ], spacing=0, expand=True,
        padding=ft.Padding(0, 0, 0, theme.ESPACIO_L))

    return ft.View(
        route="/conductor/incidencias",
        bgcolor=paleta.fondo,
        appbar=c.app_bar("Mis incidencias", page,
                         subtitulo=unidad.placa if unidad else "Sin unidad",
                         atras=True, salir=True),
        padding=ft.Padding(theme.ESPACIO_L, theme.ESPACIO_M,
                           theme.ESPACIO_L, 0),
        controls=[contenido],
    )
