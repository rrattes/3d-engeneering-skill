"""Open-top three-chamber block with alternating under/over baffles."""
from build123d import Align, Box, Pos


def build(_params):
    def prism(x,y,z,px,py,pz):
        return Pos(px,py,pz)*Box(x,y,z,align=(Align.MIN,Align.MIN,Align.MIN))
    shell=prism(90,30,3,0,0,0)
    shell+=prism(90,3,27,0,0,3)
    shell+=prism(90,3,27,0,27,3)
    shell+=prism(3,24,27,0,3,3)
    shell+=prism(3,24,27,87,3,3)
    # First wall leaves a bottom passage; second leaves a top passage.
    shell+=prism(3,24,19,29,3,8)
    shell+=prism(3,24,17,59,3,3)
    return {"flow_block":shell}
