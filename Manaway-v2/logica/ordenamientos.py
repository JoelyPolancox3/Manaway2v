"""Ordenamiento por burbuja, inserción y selección."""


def ordenar_burbuja(lista: list, clave=None,
                    inverso: bool = False) -> tuple[list, int]:
    """Ordena por intercambio sucesivo de elementos vecinos (burbuja).

    Compara pares vecinos y los intercambia si están desordenados; en
    cada pasada el elemento mayor «sube» al final. Si una pasada no
    produce ningún intercambio, la lista ya está ordenada y el
    algoritmo se detiene antes (mejor caso: n-1 comparaciones).

    Args:
        lista: colección a ordenar (no se modifica).
        clave: función que extrae la clave de comparación.
        inverso: True para ordenar de mayor a menor.

    Returns:
        (copia ordenada, comparaciones realizadas).
    """
    if clave is None:
        clave = lambda x: x  
    resultado = list(lista)
    n = len(resultado)
    pasos = 0
    for i in range(n - 1):
        hubo_cambio = False
        for j in range(n - 1 - i):
            pasos += 1
            a, b = clave(resultado[j]), clave(resultado[j + 1])
            desordenados = a < b if inverso else a > b
            if desordenados:
                resultado[j], resultado[j + 1] = resultado[j + 1], resultado[j]
                hubo_cambio = True
        if not hubo_cambio:
            break  # ya estaba ordenada: no hace falta seguir comparando
    return resultado, pasos


def ordenar_insercion(lista: list, clave=None,
                      inverso: bool = False) -> tuple[list, int]:
    """Ordena colocando cada elemento en su lugar dentro de la parte ordenada.

    Recorre la lista de izquierda a derecha; cada elemento se «inserta»
    desplazando hacia la derecha los elementos mayores que él hasta
    encontrar su posición. Es el algoritmo más eficiente de los tres
    para listas casi ordenadas (mejor caso: n-1 comparaciones).

    Args:
        lista: colección a ordenar (no se modifica).
        clave: función que extrae la clave de comparación.
        inverso: True para ordenar de mayor a menor.

    Returns:
        (copia ordenada, comparaciones realizadas).
    """
    if clave is None:
        clave = lambda x: x  # noqa: E731
    resultado = list(lista)
    pasos = 0
    for i in range(1, len(resultado)):
        actual = resultado[i]
        j = i - 1
        while j >= 0:
            pasos += 1
            desordenado = (clave(resultado[j]) < clave(actual) if inverso
                           else clave(resultado[j]) > clave(actual))
            if not desordenado:
                break
            resultado[j + 1] = resultado[j]
            j -= 1
        resultado[j + 1] = actual
    return resultado, pasos


def ordenar_seleccion(lista: list, clave=None,
                      inverso: bool = False) -> tuple[list, int]:
    """Ordena seleccionando en cada posición el extremo restante.

    Busca el elemento mínimo (o máximo, si es inverso) de la parte sin
    ordenar y lo coloca al inicio, repitiendo hasta agotar la lista.
    Siempre realiza n(n-1)/2 comparaciones, haya o no intercambios.

    Args:
        lista: colección a ordenar (no se modifica).
        clave: función que extrae la clave de comparación.
        inverso: True para ordenar de mayor a menor.

    Returns:
        (copia ordenada, comparaciones realizadas).
    """
    if clave is None:
        clave = lambda x: x  # noqa: E731
    resultado = list(lista)
    n = len(resultado)
    pasos = 0
    for i in range(n - 1):
        extremo = i
        for j in range(i + 1, n):
            pasos += 1
            a, b = clave(resultado[j]), clave(resultado[extremo])
            mas_extremo = a > b if inverso else a < b
            if mas_extremo:
                extremo = j
        if extremo != i:
            resultado[i], resultado[extremo] = resultado[extremo], resultado[i]
    return resultado, pasos


# Registro de algoritmos disponibles (seleccionables desde la interfaz)
ALGORITMOS = {
    "burbuja": ordenar_burbuja,
    "insercion": ordenar_insercion,
    "seleccion": ordenar_seleccion,
}


def peor_caso(total: int) -> int:
    """Comparaciones en el peor caso de los tres algoritmos: n(n-1)/2."""
    if total <= 1:
        return 0
    return total * (total - 1) // 2


def comparar_ordenamientos(lista: list, clave=None) -> dict:
    """Ejecuta los tres algoritmos sobre la misma lista y resume los pasos.

    Returns:
        dict con las comparaciones de cada algoritmo, el total de
        elementos, el peor caso teórico O(n²) y si los tres obtuvieron
        el mismo orden (se comparan las claves extraídas, de modo que
        los empates entre elementos no cuentan como diferencia).
    """
    if clave is None:
        clave = lambda x: x  
    orden_b, pasos_b = ordenar_burbuja(lista, clave=clave)
    orden_i, pasos_i = ordenar_insercion(lista, clave=clave)
    orden_s, pasos_s = ordenar_seleccion(lista, clave=clave)
    claves_b = [clave(x) for x in orden_b]
    claves_i = [clave(x) for x in orden_i]
    claves_s = [clave(x) for x in orden_s]
    return {
        "total": len(lista),
        "burbuja": pasos_b,
        "insercion": pasos_i,
        "seleccion": pasos_s,
        "peor_caso": peor_caso(len(lista)),
        "coinciden": claves_b == claves_i == claves_s,
    }
