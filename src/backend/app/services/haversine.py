"""
Calcul de distance GPS - Formule de Haversine (précision métrique)
"""
import math


EARTH_RADIUS_M = 6_371_000  # rayon terrestre en mètres


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en mètres entre deux coordonnées GPS.
    Formule de Haversine - précision métrique suffisante pour cross-country.

    Args:
        lat1, lon1: coordonnées point A (degrés décimaux)
        lat2, lon2: coordonnées point B (degrés décimaux)

    Returns:
        distance en mètres
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


def total_distance(points: list[tuple[float, float]]) -> float:
    """
    Calcule la distance totale d'un parcours.

    Args:
        points: liste de (lat, lon)

    Returns:
        distance totale en mètres
    """
    if len(points) < 2:
        return 0.0
    return sum(
        haversine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
        for i in range(len(points) - 1)
    )
