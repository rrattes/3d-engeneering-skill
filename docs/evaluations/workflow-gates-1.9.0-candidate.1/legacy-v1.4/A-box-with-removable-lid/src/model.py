"""Generic enclosure body and clearance-controlled removable lid."""
from build123d import Align, Box, Pos


def build(params):
    p=params["box"]
    length,width,height,wall,gap=(float(p[k]) for k in ("length","width","height","wall","clearance"))
    if min(length,width,height,wall)<=0 or gap<0 or 2*wall+2*gap>=min(length,width):
        raise ValueError("invalid enclosure size, wall or lid clearance")
    outer=Box(length,width,height,align=(Align.CENTER,Align.CENTER,Align.MIN))
    cavity=Pos(0,0,wall)*Box(length-2*wall,width-2*wall,height+1,
                             align=(Align.CENTER,Align.CENTER,Align.MIN))
    body=outer-cavity
    lid_plate=Pos(0,0,height)*Box(length,width,wall,align=(Align.CENTER,Align.CENTER,Align.MIN))
    skirt=Pos(0,0,height-wall)*Box(length-2*wall-2*gap,width-2*wall-2*gap,wall,
                                   align=(Align.CENTER,Align.CENTER,Align.MIN))
    return {"body":body,"lid":lid_plate+skirt}
