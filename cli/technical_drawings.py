"""CAD hidden-line orthographic sheets with overall dimensions; not full ISO drawings."""
from __future__ import annotations
import math
from pathlib import Path
import re
from build123d import Plane, section
from face_references import select_face, surface
from brep_pairs import distance


def _name(value):
    return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',value)


def _details(shapes, config, samples):
    sections=[]; dimensions=[]
    for key in ('sections','feature_dimensions'):
        if not isinstance(config.get(key,[]),list) or len(config.get(key,[]))>64:
            raise ValueError(key+' must be a list of at most 64 entries')
    used=set()
    for item in config.get('sections',[]):
        if not isinstance(item,dict) or set(item)!={'name','part','axis','at_mm'}:
            raise ValueError('section requires name, part, axis and at_mm')
        name=item['name']; part=item['part']; axis=item['axis']; at=item['at_mm']
        if not _name(name) or not isinstance(part,str) or part not in shapes or axis not in ('x','y','z') or isinstance(at,bool) or not isinstance(at,(int,float)) or not math.isfinite(at):
            raise ValueError('invalid section identity, axis or plane location')
        filename=part+'-section-'+name
        if filename in used or filename in shapes:raise ValueError('duplicate drawing file name')
        used.add(filename)
        origin=[0.,0.,0.];normal=[0.,0.,0.];normal['xyz'.index(axis)]=1.;origin['xyz'.index(axis)]=at
        cut=section(shapes[part],section_by=Plane(origin=origin,z_dir=normal))
        if not cut.is_valid or not cut.faces() or not math.isfinite(cut.area) or cut.area<=0:
            raise ValueError('section is empty or invalid: '+name)
        axes={'x':('Y','Z'),'y':('X','Z'),'z':('X','Y')}[axis]
        lines=[]
        for edge in cut.edges():
            points=[edge.position_at(i/samples) for i in range(samples+1)]
            lines.append([(getattr(p,axes[0]),getattr(p,axes[1])) for p in points])
        sections.append({**item,'status':'PASS','area_mm2':cut.area,'edge_count':len(cut.edges()),'lines':lines,'filename':filename,'axes':axes})
    used=set()
    for item in config.get('feature_dimensions',[]):
        if not isinstance(item,dict):raise ValueError('dimension must be a mapping')
        kind=item.get('type'); allowed={'name','part','type'}|({'selector'} if kind=='diameter' else {'first','second'} if kind=='minimum_distance' else set())
        if kind not in ('diameter','minimum_distance') or set(item)!=allowed or not _name(item.get('name')) or not isinstance(item.get('part'),str) or item['part'] not in shapes:
            raise ValueError('dimension requires safe name, existing part, diameter/selector or minimum_distance/first/second')
        identity=(item['part'],item['name'])
        if identity in used:raise ValueError('duplicate feature dimension name')
        used.add(identity)
        result={'name':item['name'],'part':item['part'],'type':kind,'status':'NOT_EVALUATED','source':'actual_selected_CAD_faces'}
        selectors=[item['selector']] if kind=='diameter' else [item['first'],item['second']]
        selected=[select_face(shapes[item['part']],x) for x in selectors]
        result['face_selections']=[r for _,r in selected]
        if all(face is not None and r['status']=='PASS' for face,r in selected):
            try:
                if kind=='diameter':
                    surface_type,attributes=surface(selected[0][0])
                    if surface_type!='cylinder':raise ValueError('diameter requires cylindrical face')
                    value=2*attributes['radius_mm']
                else:value=distance(selected[0][0],selected[1][0])
                if not math.isfinite(value) or value<0:raise ValueError('nonfinite CAD dimension')
                result.update(status='PASS',value_mm=value)
            except Exception as exc:result['reason']=str(exc)
        else:result['reason']='face selection absent, ambiguous or unavailable'
        dimensions.append(result)
    if any(sum(d['part']==name for d in dimensions)>8 for name in shapes):
        raise ValueError('at most eight feature measurements per part sheet')
    return sections,dimensions


def generate_drawings(shapes, output: Path, config=None):
    """Generate SVG/PDF views, optional real sections and CAD-selected dimensions.

    True CAD hidden-line removal supplies top/front/right views. Curves are sampled
    only for rendering; dimension values come from the actual BREP bounding box.
    """
    config = {} if config is None else config
    if not isinstance(config,dict) or set(config)-{'title','samples_per_edge','sections','feature_dimensions'}:
        raise ValueError('unknown drawing configuration')
    samples=config.get('samples_per_edge',64)
    title=config.get('title','CAD orthographic drawing')
    if isinstance(samples,bool) or not isinstance(samples,int) or not 8 <= samples <= 512:
        raise ValueError('samples_per_edge must be integer 8..512')
    if not isinstance(title,str) or len(title)>200 or any(ord(c)<32 for c in title):
        raise ValueError('title must be printable text up to 200 characters')
    if not isinstance(shapes,dict) or not 1 <= len(shapes) <= 64:
        raise ValueError('shapes must contain 1..64 named CAD parts')
    for name,shape in shapes.items():
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}',name):
            raise ValueError('part name must be a safe ASCII identifier, max 64 characters')
        if not getattr(shape,'is_valid',False) or not shape.solids() or any(not math.isfinite(s.volume) or s.volume<=0 for s in shape.solids()):
            raise ValueError('drawing requires valid positive volume CAD solids')
    sections,dimensions=_details(shapes,config,samples)
    # Collect all CAD projections before producing any output files.
    records=[]
    for name,shape in shapes.items():
        box=shape.bounding_box(); overall={c.lower():float(getattr(box.size,c)) for c in 'XYZ'}
        if not all(math.isfinite(v) and v>0 for v in overall.values()):
            raise ValueError('nonfinite or degenerate CAD bounds')
        views=[]
        for view,origin,up,dims in [('front',(0,-1,0),(0,0,1),('x','z')),('top',(0,0,1),(0,1,0),('x','y')),('right',(1,0,0),(0,0,1),('y','z'))]:
            visible,hidden=shape.project_to_viewport(origin,viewport_up=up,look_at=(0,0,0))
            if not visible:
                raise ValueError('CAD projection produced no visible edges')
            lines=[]
            for hidden_flag,edges in ((False,visible),(True,hidden)):
                for edge in edges:
                    points=[edge.position_at(i/samples) for i in range(samples+1)]
                    lines.append((hidden_flag,[(p.X,p.Y) for p in points]))
            views.append({'name':view,'visible_edges':len(visible),'hidden_edges':len(hidden),'axes':dims,'lines':lines})
        records.append((name,overall,views))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import rc_context
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    parts=[]
    with rc_context({'svg.fonttype':'none','font.size':8}):
        for name,overall,views in records:
            fig,axes=plt.subplots(1,3,figsize=(11.7,8.3))
            try:
                for ax,view in zip(axes,views):
                    points=[p for _,line in view['lines'] for p in line]
                    xmin=min(p[0] for p in points);xmax=max(p[0] for p in points);ymin=min(p[1] for p in points);ymax=max(p[1] for p in points)
                    span=max(xmax-xmin,ymax-ymin); offset=span*.15
                    for hidden,line in view['lines']:
                        ax.plot([p[0] for p in line],[p[1] for p in line],color='.6' if hidden else 'black',linewidth=.5 if hidden else .8,linestyle='--' if hidden else '-')
                    for start,end,label in [((xmin,ymin-offset),(xmax,ymin-offset),overall[view['axes'][0]]),((xmax+offset,ymin),(xmax+offset,ymax),overall[view['axes'][1]])]:
                        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'<->','lw':.6})
                        horizontal=start[1]==end[1]
                        ax.text((start[0]+end[0])/2+(0 if horizontal else offset*.25),(start[1]+end[1])/2-(offset*.35 if horizontal else 0),f'{label:.2f} mm',ha='center' if horizontal else 'left',va='top' if horizontal else 'center',rotation=0 if horizontal else 90)
                    # Extension lines tie the overall dimensions to projected extents.
                    for x in (xmin,xmax):ax.plot([x,x],[ymin,ymin-offset*1.15],color='black',lw=.4)
                    for y in (ymin,ymax):ax.plot([xmax,xmax+offset*1.15],[y,y],color='black',lw=.4)
                    ax.set_xlim(xmin-offset,xmax+offset*2.2);ax.set_ylim(ymin-offset*2,ymax+offset)
                    ax.set_aspect('equal');ax.axis('off');ax.set_title(view['name'].upper())
                fig.suptitle(title+' — '+name)
                fig.text(.05,.08,'Units: mm | Overall CAD envelope dimensions | Independent view scales (not for paper measurement)',fontsize=8)
                fig.text(.05,.05,'Nominal geometry only. No tolerances, datum scheme or manufacturing/physical approval.',fontsize=8)
                labels=[f"{d['name']}: {d['type']} = {d['value_mm']:.3f} mm" if d['status']=='PASS' else d['name']+': NOT_EVALUATED (face unresolved or unsupported)' for d in dimensions if d['part']==name]
                if labels:fig.text(.05,.14,'\n'.join(labels),fontsize=8)
                files=[]
                for ext in ('svg','pdf'):
                    path=output/(name+'.'+ext);fig.savefig(path,format=ext);files.append(str(path))
                parts.append({'id':name,'overall_mm':overall,'views':[{k:v for k,v in x.items() if k!='lines'} for x in views],'files':files})
            finally:
                plt.close(fig)
        for detail in sections:
            fig,ax=plt.subplots(figsize=(8.3,8.3))
            try:
                for line in detail['lines']:ax.plot([p[0] for p in line],[p[1] for p in line],color='black',lw=.8)
                ax.set_aspect('equal');ax.set_xlabel(detail['axes'][0]+' (mm)');ax.set_ylabel(detail['axes'][1]+' (mm)')
                ax.set_title('SECTION '+detail['name']+' — '+detail['part']+'\n'+detail['axis'].upper()+f" = {detail['at_mm']:.3f} mm")
                fig.text(.05,.03,f"Actual CAD section contours | Section area {detail['area_mm2']:.3f} mm² | No tolerances or physical approval",fontsize=8)
                detail['files']=[]
                for ext in ('svg','pdf'):
                    path=output/(detail['filename']+'.'+ext);fig.savefig(path,format=ext);detail['files'].append(str(path))
            finally:plt.close(fig)
    status='NOT_EVALUATED' if any(d['status']!='PASS' for d in dimensions) else 'PASS'
    return {'status':status,'sections':[{k:v for k,v in d.items() if k not in ('lines','filename')} for d in sections], 'feature_dimensions':dimensions,'method':'OCP orthographic hidden-line removal; sampled curve rendering','units':'mm','parts':parts,
            'samples_per_edge':samples,'physical_validation':'NOT_EVALUATED','standards_compliance':'NOT_EVALUATED',
            'limitations':['Overall dimensions and declared CAD-selected feature measurements only; no tolerances, datums or GD&T','Views independently scaled; numeric dimensions govern','Curves sampled for rendering; exact BREP bounds supply dimensions']}
