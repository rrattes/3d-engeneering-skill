"""Caixa de calibração genérica, com corpo e tampa separados."""
from build123d import Align, Box, Locations, Mode, Pos


def build(params):
    p = params["box"]
    length, width, height = p["length"], p["width"], p["height"]
    wall, gap = p["wall"], p["clearance"]
    if min(length, width, height, wall) <= 0 or gap < 0:
        raise ValueError("Dimensões e parede precisam ser positivas; folga não pode ser negativa")
    if 2 * wall >= min(length, width) or wall >= height:
        raise ValueError("Parede incompatível com dimensões externas")
    body_outer = Box(length, width, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cavity = Pos(0, 0, wall) * Box(length-2*wall, width-2*wall, height,
                                    align=(Align.CENTER, Align.CENTER, Align.MIN))
    body = body_outer - cavity
    lid_h = max(2.0, wall)
    lid = Pos(0, 0, height + 5) * Box(length+2*gap, width+2*gap, lid_h,
                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    return {"body": body, "lid": lid}
