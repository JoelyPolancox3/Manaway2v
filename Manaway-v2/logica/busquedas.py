"""Búsqueda lineal y binaria con conteo de pasos."""
import math


def busqueda_lineal(lista: list, objetivo, clave=None) -> tuple[int, int]:
    """Busca `objetivo` comparando cada elemento en orden.

    Args:
        lista: colección a recorrer (no necesita estar ordenada).
        objetivo: valor a buscar.
        clave: función opcional que extrae la clave de comparación
            de cada elemento (por ejemplo: lambda r: r.numero).

    Returns:
        (índice del objetivo, pasos realizados). Si no existe:
        (-1, len(lista)).
    """
    if clave is None:
        clave = lambda x: x  # noqa: E731
    pasos = 0
    for i, elemento in enumerate(lista):
        pasos += 1
        if clave(elemento) == objetivo:
            return i, pasos
    return -1, pasos


def busqueda_binaria(lista: list, objetivo, clave=None) -> tuple[int, int]:
    """Busca `objetivo` en una lista ORDENADA dividiéndola a la mitad.

    Precondición: `lista` debe estar ordenada de forma creciente según
    `clave`; en caso contrario el resultado no es confiable.

    En cada paso compara contra el elemento central y descarta la mitad
    de los candidatos, por lo que en el peor caso realiza
    ⌈log₂(n + 1)⌉ comparaciones frente a n de la búsqueda lineal.

    Returns:
        (índice del objetivo, pasos realizados). Si no existe:
        (-1, ⌈log₂(n + 1)⌉ comparaciones como máximo).
    """
    if clave is None:
        clave = lambda x: x  # noqa: E731
    izquierda, derecha = 0, len(lista) - 1
    pasos = 0
    while izquierda <= derecha:
        pasos += 1
        medio = (izquierda + derecha) // 2
        valor = clave(lista[medio])
        if valor == objetivo:
            return medio, pasos
        if valor < objetivo:
            izquierda = medio + 1
        else:
            derecha = medio - 1
    return -1, pasos


def peor_caso_lineal(total: int) -> int:
    """Comparaciones en el peor caso: recorrer toda la lista."""
    return total


def peor_caso_binaria(total: int) -> int:
    """Comparaciones en el peor caso: ⌈log₂(total + 1)⌉."""
    if total <= 0:
        return 0
    return math.ceil(math.log2(total + 1))


def comparar(lista: list, objetivo, clave=None) -> dict:
    """Ejecuta ambos algoritmos sobre la misma lista y resume los pasos.

    Returns:
        dict con los pasos de cada algoritmos, si encontró el objetivo,
        los peores casos y el total de elementos evaluados.
    """
    idx_l, pasos_l = busqueda_lineal(lista, objetivo, clave=clave)
    idx_b, pasos_b = busqueda_binaria(lista, objetivo, clave=clave)
    total = len(lista)
    return {
        "total": total,
        "lineal": {"pasos": pasos_l, "encontrado": idx_l >= 0},
        "binaria": {"pasos": pasos_b, "encontrado": idx_b >= 0},
        "peor_lineal": peor_caso_lineal(total),
        "peor_binaria": peor_caso_binaria(total),
    }
