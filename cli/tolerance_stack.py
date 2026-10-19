"""Signed linear worst-case intervals; no statistical or physical-fit inference."""
import math


def _number(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('invalid '+name)
    return float(value)


def evaluate_stack(stack,dimensions):
    if not isinstance(stack,dict) or not isinstance(dimensions,dict):raise ValueError('stack and dimensions must be mappings')
    ident=stack.get('id');terms=stack.get('terms');allowed=stack.get('allowed_mm')
    if not isinstance(ident,str) or not ident or not isinstance(terms,list) or not terms:raise ValueError('stack requires id and nonempty terms')
    if not isinstance(allowed,(list,tuple)) or len(allowed)!=2:raise ValueError('allowed_mm requires [min,max]')
    lo,hi=(_number(v,'allowed_mm') for v in allowed)
    if lo>hi:raise ValueError('allowed range reversed')
    coefficients={}
    for term in terms:
        if not isinstance(term,dict) or term.get('dimension') not in dimensions:raise ValueError('unknown tolerance dimension')
        name=term['dimension'];coefficient=_number(term.get('coefficient'),'coefficient')
        coefficients[name]=coefficients.get(name,0)+coefficient
        if not math.isfinite(coefficients[name]):raise ValueError('coefficient outside numeric range')
    offset=_number(stack.get('offset_mm',0),'offset_mm');minimum=maximum=nominal=offset
    evidence=[];unknown=[];assumed=[]
    for name,coefficient in coefficients.items():
        if coefficient==0:continue  # same variable cancels; do not double-count uncertainty
        spec=dimensions[name]
        if not isinstance(spec,dict):raise ValueError('dimension must be mapping')
        if 'min_mm' in spec or 'max_mm' in spec:
            if any(k in spec for k in ('minus_mm','plus_mm')):raise ValueError('mixed dimension interval encodings')
            if not all(k in spec for k in ('min_mm','max_mm')):unknown.append({'dimension':name,'reason':'uncertainty_bounds_missing'});continue
            lower=_number(spec['min_mm'],'min_mm');upper=_number(spec['max_mm'],'max_mm')
            center=_number(spec.get('nominal_mm',(lower+upper)/2),'nominal_mm')
        else:
            if not all(k in spec for k in ('nominal_mm','minus_mm','plus_mm')):unknown.append({'dimension':name,'reason':'uncertainty_bounds_missing'});continue
            center=_number(spec['nominal_mm'],'nominal_mm');minus=_number(spec['minus_mm'],'minus_mm');plus=_number(spec['plus_mm'],'plus_mm')
            if minus<0 or plus<0:raise ValueError('dimension deviations must be nonnegative')
            lower=center-minus;upper=center+plus
        if not all(math.isfinite(v) for v in (lower,upper,center)) or lower>upper or not lower<=center<=upper:raise ValueError('invalid dimension interval or nominal')
        basis=spec.get('basis');source=spec.get('source')
        if basis is not None and basis not in ('measured','supplier','calibrated','assumed','exact'):raise ValueError('unknown uncertainty basis')
        if basis is None or not isinstance(source,str) or not source.strip():unknown.append({'dimension':name,'reason':'uncertainty_provenance_missing'})
        if basis=='assumed':assumed.append(name)
        contributions=(coefficient*lower,coefficient*upper)
        minimum+=min(contributions);maximum+=max(contributions);nominal+=coefficient*center
        evidence.append({'dimension':name,'coefficient':coefficient,'nominal_mm':center,'interval_mm':[lower,upper],
                         'contribution_mm':[min(contributions),max(contributions)],'basis':basis,'source':source})
    if not all(math.isfinite(v) for v in (minimum,maximum,nominal)):raise ValueError('stack result outside numeric range')
    missing_bounds=any(r['reason']=='uncertainty_bounds_missing' for r in unknown)
    within=not missing_bounds and minimum>=lo-1e-9 and maximum<=hi+1e-9
    status='NOT_EVALUATED' if missing_bounds else 'FAIL' if not within else 'NOT_EVALUATED' if unknown else 'WARNING' if assumed else 'PASS'
    return {'id':ident,'status':status,'method':'signed_linear_worst_case_intervals',
            'minimum_mm':None if missing_bounds else minimum,'maximum_mm':None if missing_bounds else maximum,
            'nominal_mm':None if missing_bounds else nominal,'allowed_mm':[lo,hi],'offset_mm':offset,
            'terms':evidence,'combined_coefficients':coefficients,'unknown_dimensions':unknown,'assumed_dimensions':assumed,
            'bounded_arithmetic_status':'NOT_EVALUATED' if missing_bounds else 'PASS' if within else 'FAIL',
            'physical_fit_validation':'NOT_EVALUATED','scope':'declared linear bounded dimensions; no GD&T, thermal model or statistical yield inference'}


def evaluate_stacks(records,dimensions):
    if not isinstance(records,list):raise ValueError('tolerance_stacks must be a list')
    ids=[r.get('id') for r in records]
    if len(set(ids))!=len(ids):raise ValueError('duplicate tolerance stack id')
    return [evaluate_stack(record,dimensions) for record in records]
