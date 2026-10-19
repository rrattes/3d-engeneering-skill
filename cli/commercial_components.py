"""Commercial records and revision locks. Schema/provenance checks are not measurement."""
from __future__ import annotations
import hashlib,json,math

def record_hash(record:dict)->str:
    return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def validate_commercial_record(record:dict)->dict:
    reasons=[];status='PASS'
    if not record.get('id') or not record.get('revision'):reasons.append('identity_or_revision_missing');status='FAIL'
    dims=record.get('dimensions',{})
    if record.get('units')!='mm' or not isinstance(dims,dict) or not dims or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in dims.values()):reasons.append('invalid_dimensions_or_units');status='FAIL'
    source=record.get('source',{})
    known=record.get('measurement_target')==record.get('record_kind')=='component' and isinstance(source,dict) and source.get('kind') in ('manufacturer_drawing','physical_measurement','reviewed_community_cad') and bool(source.get('url') or source.get('evidence_path')) and bool(source.get('date'))
    if not known:
        reasons.append('source_or_target_not_sufficient_for_component_dimensions')
        if status!='FAIL':status='NOT_EVALUATED'
    holes=record.get('mounting_holes_mm')
    # All candidate templates still require physical confirmation before manufacture.
    template=bool(status=='PASS' and source.get('kind')=='manufacturer_drawing' and isinstance(holes,list) and holes and record.get('coordinate_datum') and record.get('uncertainty_mm') is not None)
    if template:
        from component_catalog import vector3
        for h in holes:vector3(h,'mounting hole coordinates')
        u=record['uncertainty_mm']
        if isinstance(u,bool) or not isinstance(u,(int,float)) or not math.isfinite(u) or u<0:template=False;status='FAIL';reasons.append('invalid_uncertainty')
    return {'id':record.get('id'),'revision':record.get('revision'),'status':status,'reasons':reasons,'usable_for_drilling_template':template,'scope':'declared record schema and provenance; original drawing content not automatically verified','physical_validation':'NOT_EVALUATED'}

def validate_component_selection(record:dict,lock:dict)->dict:
    matched=all(record.get(k)==lock.get(k) for k in ('id','revision')) and record_hash(record)==lock.get('sha256')
    return {'status':'PASS' if matched else 'FAIL','reason':'revision_and_hash_match' if matched else 'selected_component_revision_or_content_changed','physical_validation':'NOT_EVALUATED'}

def check_commercial_keepouts(body,keepouts:dict,blockers:dict)->dict:
    from validation import pair_check
    body_checks=[pair_check(body,s,pair_id='body::'+n) for n,s in blockers.items()]
    keepout_checks=[pair_check(k,s,pair_id=n+'::'+other) for n,k in keepouts.items() for other,s in blockers.items()]
    def status(items):return 'FAIL' if any(x['status']=='FAIL' for x in items) else 'NOT_EVALUATED' if any(x['status']=='NOT_EVALUATED' for x in items) else 'PASS'
    return {'status':status(body_checks+keepout_checks),'body':{'status':status(body_checks),'checks':body_checks},'keepouts':keepout_checks,'scope':'actual declared envelopes only; actual cable bend radius not inferred'}
