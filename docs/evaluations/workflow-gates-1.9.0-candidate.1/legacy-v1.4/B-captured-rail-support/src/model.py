"""Generic serviceable structural foot and upright with a captured T rail."""
from build123d import Align, Box, Pos


def build(_params):
    def box(x,y,z,px,py,pz):
        return Pos(px,py,pz)*Box(x,y,z,align=(Align.CENTER,Align.MIN,Align.MIN))
    # Base datum plate and the two T-track webs/lips.
    base=box(60,40,8,0,0,0)
    base+=box(60,2,4,0,14,8)
    base+=box(60,2,4,0,24,8)
    base+=box(60,2,2,0,16,10)
    base+=box(60,2,2,0,22,10)
    # Tongue slides from an open end; its wider toe is retained below the lips.
    upright=box(14,7.2,2,-20,16.4,8)
    upright+=box(14,3.6,2,-20,18.2,10)
    upright+=box(14,4,40,-20,18,12)
    return {"base":base,"upright":upright}
