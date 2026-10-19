"""Synthetic propagation fixture, not a physically validated console design."""
import math
from build123d import Align,Box,Cylinder,Pos,Compound
MIN=(Align.MIN,Align.MIN,Align.MIN)
def derive_layout(params:dict)->dict:
    c=params['case'];f=params['fan'];ps=params['psu'];gap=params['clearance']
    values=[*c.values(),*f.values(),*ps.values(),gap]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in values):raise ValueError('dimensions must be finite and positive')
    size=f['size'];pitch=f['pitch'];cx=c['wall']+gap+(size+12)/2;cy=c['depth']/2
    xps=c['wall']+gap+size+12+gap
    layout={'case':dict(c),'fan':dict(f),'psu':dict(ps),'fan_center':[cx,cy],'fan_holes':[[cx+x*pitch/2,cy+y*pitch/2] for x in (-1,1) for y in (-1,1)],'plate_z':c['floor']+6,'plate_thickness':c['wall']+1,'plate_size':size+12,'psu_origin':[xps,c['wall']+gap,c['floor']+gap],'cable_reserve':20,'screw_length':math.ceil(c['wall']+1+3)}
    issues=validate_layout(layout)
    if issues:raise ValueError('cavity incompatible: '+','.join(x['reason'] for x in issues))
    return layout
def validate_layout(l:dict)->list[dict]:
    c=l['case'];f=l['fan'];p=l['psu'];x,y,z=l['psu_origin'];issues=[]
    if 2*c['wall']>=min(c['width'],c['depth']) or c['floor']>=c['height']:issues.append({'reason':'wall'})
    if l['plate_size']+2*c['wall']>c['depth'] or f['pitch']+5>=l['plate_size']:issues.append({'reason':'fan_fit'})
    if x+p['width']+c['wall']>=c['width'] or y+p['length']+l['cable_reserve']+c['wall']>=c['depth']:issues.append({'reason':'PSU_and_cable'})
    if max(z+p['height'],l['plate_z']+l['plate_thickness']+f['height']+3)>=c['height']:issues.append({'reason':'height'})
    return issues
def build(params):
    l=derive_layout(params);c=l['case'];f=l['fan'];ps=l['psu'];cx,cy=l['fan_center'];t=c['wall'];z=l['plate_z'];th=l['plate_thickness'];size=l['plate_size']
    outer=Box(c['width'],c['depth'],c['height'],align=MIN)
    cavity=Pos(t,t,c['floor'])*Box(c['width']-2*t,c['depth']-2*t,c['height'],align=MIN)
    chassis=outer-cavity
    plate=Pos(cx-size/2,cy-size/2,z)*Box(size,size,th,align=MIN)
    plate-=Pos(cx,cy,z-1)*Cylinder(f['size']*.43,th+2,align=(Align.CENTER,Align.CENTER,Align.MIN))
    screws=[]
    for x,y in l['fan_holes']:
        post=Pos(x,y,c['floor'])*Cylinder(4.5,6,align=(Align.CENTER,Align.CENTER,Align.MIN))
        post-=Pos(x,y,c['floor'])*Cylinder(1.7,7,align=(Align.CENTER,Align.CENTER,Align.MIN))
        chassis+=post
        shank=Pos(x,y,z+th-l['screw_length'])*Cylinder(1.5,l['screw_length'],align=(Align.CENTER,Align.CENTER,Align.MIN))
        head=Pos(x,y,z+th)*Cylinder(3,2.5,align=(Align.CENTER,Align.CENTER,Align.MIN))
        screws.append(shank+head)
    for x,y in l['fan_holes']:plate-=Pos(x,y,z-1)*Cylinder(1.7,th+2,align=(Align.CENTER,Align.CENTER,Align.MIN))
    reference=Pos(*l['psu_origin'])*Box(ps['width'],ps['length'],ps['height'],align=MIN)
    return {'chassis':chassis,'fan_plate':plate,'psu_reference':reference,'mounting_hardware':Compound(screws)}
