"""Versioned, opt-in calibration measurements. Never mutates shared material presets."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path


def make_calibration_record(payload):
    identity=payload.get('identity',{})
    required=('printer','nozzle_diameter_mm','material','process_settings_sha256')
    missing=[key for key in required if key not in identity]
    measurements=payload.get('measurements')
    if missing or not isinstance(measurements,dict) or not measurements:
        raise ValueError(f"identity fields and non-empty measurements required; missing={missing}")
    for key,value in measurements.items():
        vals=value if isinstance(value,list) else [value]
        if not vals or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):
            raise ValueError(f"measurement '{key}' must be a number or numeric list")
    if not re.fullmatch(r'[0-9a-fA-F]{64}',str(identity['process_settings_sha256'])):
        raise ValueError('process_settings_sha256 must be a SHA-256 hex digest')
    stamp={'identity':identity,'measured_at':payload.get('measured_at'),
           'method':payload.get('method'),'evidence':payload.get('evidence'),
           'measurements':measurements,
           'calibrated':bool(payload.get('confirmed_physical_measurements') is True and payload.get('evidence')),
           'status':'CALIBRATED' if payload.get('confirmed_physical_measurements') is True and payload.get('evidence') else 'RECORDED_UNCONFIRMED',
           'fit_ranges_mm':payload.get('fit_ranges_mm',{}),'min_wall_mm':payload.get('min_wall_mm'),
           'shrinkage_percent':payload.get('shrinkage_percent')}
    fingerprint=hashlib.sha256(json.dumps(stamp,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]
    printer_slug=re.sub('[^a-z0-9]+','-',str(identity['printer']).lower()).strip('-')
    material_slug=re.sub('[^a-z0-9]+','-',str(identity['material']).lower()).strip('-')
    stamp['id']=f"{printer_slug}-{material_slug}-{fingerprint}"
    return stamp


def compare_calibration_identity(identity, printer_config, parameters):
    material=parameters.get('material',{}).get('profile')
    expected={'printer':printer_config.get('name'),
              'nozzle_diameter_mm':printer_config.get('nozzle_diameter_mm'),
              'material':material,
              'process_settings_sha256':printer_config.get('process_settings_sha256')}
    missing=[key for key,value in expected.items() if value is None]
    if missing:
        return {'status':'NOT_EVALUATED','reason':'project_calibration_identity_incomplete','missing':missing}
    mismatches=[]
    for key,value in expected.items():
        observed=identity.get(key)
        same=(abs(float(observed)-float(value))<=1e-9 if key=='nozzle_diameter_mm' and observed is not None
              else str(observed).strip().casefold()==str(value).strip().casefold())
        if not same: mismatches.append({'field':key,'project':value,'record':observed})
    return {'status':'FAIL' if mismatches else 'PASS','mismatches':mismatches,'identity':expected}


def write_calibration_record(payload, project_root='.'):
    import yaml
    record=make_calibration_record(payload)
    if record['calibrated']:
        evidence=Path(payload['evidence'])
        if not evidence.is_absolute(): evidence=Path(project_root)/evidence
        if not evidence.is_file():
            raise FileNotFoundError('physical measurement evidence file is required before confirming calibration')
    directory=Path(project_root)/'profiles/calibrations'; directory.mkdir(parents=True,exist_ok=True)
    target=directory/(record['id']+'.yaml')
    if target.exists():
        raise FileExistsError(f'calibration record exists and will not be overwritten: {target}')
    target.write_text(yaml.safe_dump(record,sort_keys=False,allow_unicode=True))
    return target,record
