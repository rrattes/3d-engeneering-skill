#!/usr/bin/env python3
"""Isolated OrcaSlicer runner. Standard library only."""
import argparse, hashlib, json, math, os, re, shlex, subprocess, sys, time, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

APP=Path("/opt/orca/AppDir")
PROFILES=APP/"resources/profiles"
ORCA=APP/"AppRun"
ROOT=Path("/workspace")
OUT=ROOT/"build/slicer"
VERSION=os.environ.get("CAD3D_ORCA_VERSION","2.4.2")
MACHINE=PROFILES/"Elegoo/machine/ECC2/Elegoo Centauri Carbon 2 0.4 nozzle.json"
FILAMENT=PROFILES/"Elegoo/filament/ECC2/Elegoo PETG @ECC2.json"
PROCESS=PROFILES/"Elegoo/process/ECC2/0.20mm Standard @Elegoo CC2 0.4 nozzle.json"
PRINTERS={"elegoo-cc2":MACHINE}
MATERIALS={"petg":FILAMENT}
PROCESSES={"standard-0.20":PROCESS}

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""): h.update(b)
 return h.hexdigest()

def obj(path): return json.loads(Path(path).read_text())

def index_profiles():
 result={}
 for p in PROFILES.rglob("*.json"):
  try: d=obj(p)
  except Exception: continue
  if isinstance(d,dict) and isinstance(d.get("name"),str): result.setdefault(d["name"],[]).append(p)
 return result

def chain(path, kind, idx):
 out=[]; seen=set(); p=Path(path); family=p.relative_to(PROFILES).parts[:2]
 while True:
  if not p.is_file(): raise FileNotFoundError(f"profile missing: {p}")
  d=obj(p)
  if d.get("type")!=kind: raise ValueError(f"profile type mismatch: {p}")
  name=d.get("name")
  if name in seen: raise ValueError(f"profile inheritance cycle: {name}")
  seen.add(name); out.append((p,d))
  parent=d.get("inherits")
  if not parent: break
  matches=idx.get(parent,[])
  if not matches: raise ValueError(f"unresolved profile parent {kind}: {parent}")
  # Inheritance identifiers such as fdm_process_common occur in many vendors.
  # Resolve inside the exact Elegoo profile family before falling back.
  p=next((candidate for candidate in matches if candidate.relative_to(PROFILES).parts[:2]==family),matches[0])
 out.reverse()
 return out

def chains(printer,material,process):
 if printer not in PRINTERS: raise ValueError(f"unsupported printer profile: {printer}")
 if material not in MATERIALS: raise ValueError(f"unsupported material profile: {material}")
 if process not in PROCESSES: raise ValueError(f"unsupported process profile: {process}")
 idx=index_profiles()
 mc=chain(PRINTERS[printer],"machine",idx)
 fc=chain(MATERIALS[material],"filament",idx)
 pc=chain(PROCESSES[process],"process",idx)
 m=obj(MACHINE); f=obj(FILAMENT); p=obj(PROCESS)
 if m.get("printer_model")!="Elegoo Centauri Carbon 2" or m.get("nozzle_diameter")!=["0.4"]: raise ValueError("machine preset is not official ECC2 0.4 mm")
 if float(m.get("printable_height",0))!=256 or "256x256" not in m.get("printable_area",[]): raise ValueError("ECC2 envelope mismatch")
 if m["name"] not in f.get("compatible_printers",[]): raise ValueError("PETG is not compatible with ECC2 0.4 mm")
 if m["name"] not in p.get("compatible_printers",[]): raise ValueError("process is not compatible with ECC2 0.4 mm")
 if m.get("manual_filament_change")!="0" or m.get("auto_toolchange_command")!="0": raise ValueError("multi-filament profile rejected for single color")
 return mc,fc,pc

def version():
 # OrcaSlicer v2.4.2 has no --version option; --help prints a version banner.
 p=subprocess.run([str(ORCA),"--help"],cwd="/tmp",text=True,capture_output=True,timeout=60)
 s=(p.stdout+"\n"+p.stderr).strip()
 if p.returncode or f"OrcaSlicer-{VERSION}:" not in s: raise RuntimeError(f"Orca version mismatch/failed: rc={p.returncode} output={s[:1200]}")
 return s

def doctor():
 mc,fc,pc=chains("elegoo-cc2","petg","standard-0.20")
 print(json.dumps({"status":"PASS","engine":"OrcaSlicer","version":VERSION,"version_output":version(),"headless":True,
  "printer":"Elegoo Centauri Carbon 2 0.4 nozzle","material":"Elegoo PETG @ECC2","process":"0.20mm Standard @Elegoo CC2 0.4 nozzle",
  "envelope_mm":[256,256,256],"inheritance":"PASS","profiles":{k:[{"name":d["name"],"relative_path":str(p.relative_to(PROFILES)),"sha256":sha(p)} for p,d in c] for k,c in (("machine",mc),("filament",fc),("process",pc))},"multicolor":"disabled"},indent=2))

def preflight(printer, material, process):
 """Check the requested installed preset chain without models or output writes."""
 result={"status":"NOT_EVALUATED","scope":"PRESET_CHAIN_AND_ENGINE_ONLY",
  "requested":{"printer":printer,"material":material,"process":process},
  "supported":{"printers":sorted(PRINTERS),"materials":sorted(MATERIALS),"processes":sorted(PROCESSES)},
  "slicing":"NOT_PERFORMED","physical_validation":"NOT_EVALUATED","printer_communication":"NOT_PERFORMED"}
 try:
  mc,fc,pc=chains(printer,material,process)
  result.update(status="PASS",version=VERSION,version_output=version(),
   profiles={k:[{"name":d["name"],"relative_path":str(p.relative_to(PROFILES)),"sha256":sha(p)} for p,d in c] for k,c in (("machine",mc),("filament",fc),("process",pc))})
 except ValueError as exc:
  result.update(status="NOT_EVALUATED" if str(exc).startswith("unsupported ") else "FAIL",reason=str(exc))
 except Exception as exc:
  result.update(status="FAIL",reason=str(exc))
 return result

def vertices(path):
 path=Path(path)
 if path.suffix.lower()==".stl":
  raw=path.read_bytes()
  if len(raw)>=84:
   n=int.from_bytes(raw[80:84],"little")
   if 84+n*50==len(raw):
    import struct
    return [v for i in range(n) for v in (struct.unpack_from("<3f",raw,84+i*50+12),struct.unpack_from("<3f",raw,84+i*50+24),struct.unpack_from("<3f",raw,84+i*50+36))]
  v=[]
  for line in raw.decode("ascii",errors="ignore").splitlines():
   a=line.split()
   if len(a)==4 and a[0].lower()=="vertex": v.append(tuple(map(float,a[1:])))
  if not v: raise ValueError("STL has no parseable vertices")
  return v
 if path.suffix.lower()==".3mf":
  with zipfile.ZipFile(path) as z:
   model=next((n for n in z.namelist() if n.startswith("3D/") and n.endswith(".model")),None)
   if not model: raise ValueError("3MF contains no model XML")
   root=ET.fromstring(z.read(model))
   v=[tuple(float(e.get(k)) for k in ("x","y","z")) for e in root.iter() if e.tag.endswith("vertex")]
   if not v: raise ValueError("3MF has no parseable vertices")
   return v
 raise ValueError("input must be STL or 3MF")

def dims(v): return [max(p[i] for p in v)-min(p[i] for p in v) for i in range(3)]

def rotated(v,r):
 x,y,z=[math.radians(a) for a in r]; sx,cx,sy,cy,sz,cz=math.sin(x),math.cos(x),math.sin(y),math.cos(y),math.sin(z),math.cos(z)
 out=[]
 for a,b,c in v:
  b,c=b*cx-c*sx,b*sx+c*cx
  a,c=a*cy+c*sy,-a*sy+c*cy
  a,b=a*cz-b*sz,a*sz+b*cz
  out.append((a,b,c))
 return out

def rotate_stl(source,target,rotation):
 """Write an orientation-only STL copy; original CAD/export is never edited."""
 import struct
 raw=Path(source).read_bytes()
 if len(raw)>=84:
  count=int.from_bytes(raw[80:84],"little")
  if 84+count*50==len(raw):
   data=bytearray(raw)
   for i in range(count):
    base=84+i*50
    for offset in (0,12,24,36):
     point=struct.unpack_from("<3f",data,base+offset)
     struct.pack_into("<3f",data,base+offset,*rotated([point],rotation)[0])
   Path(target).write_bytes(data);return
 text=raw.decode("ascii")
 lines=[]
 for line in text.splitlines():
  fields=line.strip().split()
  is_facet_normal=len(fields)==5 and fields[0].lower()=="facet" and fields[1].lower()=="normal"
  is_vertex=len(fields)==4 and fields[0].lower()=="vertex"
  if is_vertex or is_facet_normal:
   label=(fields[0]+" "+fields[1]) if is_facet_normal else fields[0]
   prefix=line[:len(line)-len(line.lstrip())]+fields[0]
   point=tuple(float(v) for v in (fields[2:] if is_facet_normal else fields[1:]))
   xyz=rotated([point],rotation)[0]
   line=line[:len(line)-len(line.lstrip())]+label+" "+" ".join(f"{v:.9g}" for v in xyz)
  lines.append(line)
 Path(target).write_text("\n".join(lines)+"\n")

def metrics(text,zpath):
 m={"estimated_time":None,"estimated_time_seconds":None,"material":None,"filament_length_m":None,"filament_mass_g":None,"layer_count":None,"support":None,"source":"Orca CLI stdout/stderr and sliced 3MF metadata"}
 pats={"estimated_time":r"(?:estimated\s+(?:printing\s+)?time|print\s+time)\s*[:=]\s*([^\r\n]+)",
       "material":r"(?:filament|material)\s+(?:used|required|consumption)\s*[:=]\s*([^\r\n]+)",
       "layer_count":r"(?:total\s+)?layers?\s*[:=]\s*(\d+)","support":r"support(?:\s+material)?\s*[:=]\s*([^\r\n]+)"}
 for k,p in pats.items():
  q=re.search(p,text,re.I)
  if q: m[k]=q.group(1).strip()
 entries=[]
 if zpath and Path(zpath).is_file():
  with zipfile.ZipFile(zpath) as z:
   if z.testzip() is not None: raise ValueError("3MF CRC validation failed")
   entries=[n for n in z.namelist() if n.lower().endswith((".json",".config"))]
   for n in entries:
    s=z.read(n).decode("utf8",errors="replace")
    if n.lower().endswith("slice_info.config"):
     root=ET.fromstring(s)
     prediction=root.find(".//metadata[@key='prediction']")
     if prediction is not None and prediction.get("value"):
      seconds=float(prediction.get("value"));m["estimated_time_seconds"]=seconds
      m["estimated_time"]=f"{int(seconds//3600):02d}:{int(seconds%3600//60):02d}:{int(seconds%60):02d}"
     filaments=root.findall(".//filament")
     if filaments:
      lengths=[float(f.get("used_m","0")) for f in filaments]
      masses=[float(f.get("used_g","0")) for f in filaments]
      m["filament_length_m"]=round(sum(lengths),4)
      m["filament_mass_g"]=round(sum(masses),4) if any(masses) else None
      m["material"]={"length_m":m["filament_length_m"],"mass_g":m["filament_mass_g"],"preset_ids":[f.get("id") for f in filaments],"types":[f.get("type") for f in filaments]}
     layer_lists=root.findall(".//layer_filament_list")
     ranges=[]
     for item in layer_lists:
      nums=[int(v) for v in re.findall(r"\d+",item.get("layer_ranges", ""))]
      if len(nums)>=2:ranges.append(max(nums[1]-nums[0]+1,1))
     if ranges:m["layer_count"]=max(ranges)
     for item in root.findall(".//metadata"):
      if item.get("key")=="support_used":m["support"]=item.get("value")
    for k,p in {"estimated_time":r"(?:estimated_time|print_time|total_time)\s*[\"=: ]+\s*([\w .:]+)",
                "material":r"(?:filament used|filament_weight|total filament)\s*[\"=: ]+\s*([\w .:]+)",
                "layer_count":r"(?:total_layer_count|layer_count)\s*[\"=: ]+\s*(\d+)",
                "support":r"(?:support_material|support filament)\s*[\"=: ]+\s*([\w .:]+)"}.items():
     if m[k] is None:
      q=re.search(p,s,re.I)
      if q:m[k]=q.group(1).strip()
 m["metadata_entries_inspected"]=entries
 return m

def parse_seconds(s):
 if not s:return None
 s=str(s).strip()
 q=re.fullmatch(r"(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)",s)
 if q:return int(q[1] or 0)*3600+int(q[2])*60+float(q[3])
 total=0.; found=False
 for n,u in re.findall(r"(\d+(?:\.\d+)?)\s*(h|hr|hours?|m|min|minutes?|s|sec|seconds?)",s,re.I):
  found=True; total+=float(n)*(3600 if u.lower().startswith("h") else 60 if u.lower().startswith("m") else 1)
 return total if found else (float(s) if s.isnumeric() else None)

def run_one(model,rotation,args,part_name=None):
 name=f"{part_name or Path(model).stem}-rot-{rotation[0]}-{rotation[1]}-{rotation[2]}"
 target=OUT/f"{name}.3mf"; log=OUT/f"{name}.log"
 mc,fc,pc=chains(args.printer,args.material,args.process)
 # Orca resolves the selected leaf preset through its bundled catalog. The CLI
 # keeps some inherited filament identifiers as separate vector slots, so set
 # the material identity/density from the verified same-version parent chain.
 effective={}
 for _,preset in fc: effective.update(preset)
 cmd=[str(ORCA),str(model),"--load-settings",str(pc[-1][0])+";"+str(mc[-1][0]),"--load-filaments",str(fc[-1][0])]
 for key in ("filament_type","filament_density","filament_diameter"):
  value=effective.get(key)
  if isinstance(value,list) and value:value=value[-1]
  if value is not None:cmd.append("--"+key.replace("_","-")+"="+str(value))
 cmd += ["--ensure-on-bed","--arrange","1","--slice","0","--export-3mf",target.name,"--outputdir",str(OUT)]
 start=time.monotonic()
 try:
  cp=subprocess.run(cmd,cwd="/tmp",text=True,capture_output=True,timeout=int(os.environ.get("CAD3D_ORCA_TIMEOUT","1800")))
  rc,out,err=cp.returncode,cp.stdout,cp.stderr
 except subprocess.TimeoutExpired as e:rc,out,err=124,e.stdout or "",(e.stderr or "")+"\nORCASLICER_TIMEOUT"
 elapsed=round(time.monotonic()-start,3)
 log.write_text("$ "+shlex.join(cmd)+"\n--- stdout ---\n"+out+"\n--- stderr ---\n"+err)
 valid=False
 if target.is_file() and target.stat().st_size:
  with zipfile.ZipFile(target) as z: valid=z.testzip() is None and any(n.startswith("3D/") and n.endswith(".model") for n in z.namelist())
 profile_data={k:[{"name":d["name"],"path":str(p.relative_to(PROFILES)),"sha256":sha(p)} for p,d in c] for k,c in (("machine",mc),("filament",fc),("process",pc))}
 effective={}
 for _,preset in fc:effective.update(preset)
 for key in ("filament_type","filament_vendor","filament_density","filament_diameter"):
  value=effective.get(key)
  if isinstance(value,list) and value:value=value[-1]
  effective[key]=value
 estimates=metrics(out+"\n"+err,target if target.exists() else None)
 # Orca's --slice action emits a default plate_1.gcode as a side effect even
 # when the requested deliverable is only a 3MF. Keep that transient output
 # out of the project so the CLI never hands off a machine-code file.
 transient_gcode=OUT/"plate_1.gcode"
 gcode_side_effect_removed=False
 if transient_gcode.is_file():
  transient_gcode.unlink()
  gcode_side_effect_removed=True
 material_types=(estimates.get("material") or {}).get("types",[])
 effective_type=effective.get("filament_type")
 type_match=("PASS" if effective_type in material_types else "FAIL") if material_types else "NOT_EVALUATED"
 successful=rc==0 and valid and type_match=="PASS"
 return {"rotation_deg":list(rotation),"status":"PASS" if successful else "FAIL","returncode":rc,"stdout":out,"stderr":err,
  "command":cmd,"elapsed_wall_seconds":elapsed,"log":str(log.relative_to(ROOT)),
  "output":str(target.relative_to(ROOT)) if target.exists() else None,"bytes":target.stat().st_size if target.exists() else 0,
  "sha256":sha(target) if target.is_file() else None,"valid_3mf":valid,"profiles":profile_data,
  "effective_filament_settings":effective,"effective_material_match":type_match,
  "estimates":estimates,"standalone_gcode_exported":False,"gcode_side_effect_removed":gcode_side_effect_removed,
  "printer_communication":"NOT_PERFORMED"}

def slice_cmd(a):
 chains(a.printer,a.material,a.process)
 model=Path(a.model); model=model if model.is_absolute() else ROOT/model
 if model.is_dir():
  xs=sorted([*model.glob("*.stl"),*model.glob("*.3mf")])
  if len(xs)!=1:raise ValueError(f"select one STL/3MF; found {len(xs)}")
  model=xs[0]
 if not model.is_file():raise FileNotFoundError(f"model not found: {model}")
 vs=vertices(model); d=dims(vs); margin=float(a.margin_mm); env=[256-margin]*3
 if a.compare_orientations and model.suffix.lower()!=".stl":raise ValueError("--compare-orientations currently requires an STL so the engine can create audited transformed input copies")
 OUT.mkdir(parents=True,exist_ok=True)
 reportpath=OUT/"slice-report.json"
 if any(d[i]>env[i]+1e-6 for i in range(3)):
  report={"status":"FAIL","reason":"exceeds_useful_envelope","dimensions_mm":d,"nominal_envelope_mm":[256]*3,"margin_mm":margin,"effective_envelope_mm":env,"slicing_started":False}
  reportpath.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2));return 3
 in_copy=OUT/(model.stem+"-input"+model.suffix.lower())
 if model.resolve()!=in_copy.resolve():in_copy.write_bytes(model.read_bytes())
 rotations=[(0,0,0)]
 if a.compare_orientations:rotations=[(0,0,0),(90,0,0),(180,0,0),(270,0,0),(0,90,0),(0,270,0)]
 result=[]
 for r in rotations:
  rd=dims(rotated(vs,r))
  if any(rd[i]>env[i]+1e-6 for i in range(3)):result.append({"rotation_deg":list(r),"status":"NOT_EVALUATED","reason":"outside_envelope","dimensions_mm":rd})
  else:
   candidate_model=model
   if any(r):
    candidate_model=OUT/f"{model.stem}-orientation-{r[0]}-{r[1]}-{r[2]}.stl"
    rotate_stl(model,candidate_model,r)
   c=run_one(candidate_model,r,a,part_name=model.stem);c["dimensions_mm"]=rd;c["input_model"]=str(Path(candidate_model).relative_to(ROOT));c["input_sha256"]=sha(candidate_model);result.append(c)
 passed=[c for c in result if c["status"]=="PASS"]
 parsed=[(parse_seconds(c["estimates"]["estimated_time"]),c) for c in passed]
 chosen=min(parsed,key=lambda x:x[0])[1] if parsed and all(x[0] is not None for x in parsed) else (passed[0] if len(passed)==1 else None)
 status="PASS" if chosen and (not a.compare_orientations or len(passed)==len(rotations)) else "FAIL"
 report={"status":status,"orca_slicer_version":VERSION,"model":str(model.relative_to(ROOT)),"input_copy":str(in_copy.relative_to(ROOT)),"input_sha256":sha(in_copy),
  "printer_id":a.printer,"material_id":a.material,"process_id":a.process,"printer_compatibility":"PASS_PRESET_CHAIN_ONLY",
  "physical_print_validation":"NOT_EVALUATED","envelope_mm":[256]*3,"operational_margin_mm":margin,"effective_envelope_mm":env,"dimensions_mm":d,
  "orientation_selection":"fastest real Orca estimate when parseable; input mesh copies rotated; does not infer strength" if a.compare_orientations else "single requested orientation",
  "chosen_rotation_deg":chosen["rotation_deg"] if chosen else None,"candidates":result,"estimates":chosen["estimates"] if chosen else None,
  "multicolor":"NOT_ENABLED","standalone_gcode_exported":False,
  "gcode_deliverables":"NOT_RETAINED; Orca CLI transient plate_1.gcode side effect is removed after slicing",
  "printer_communication":"NOT_PERFORMED"}
 reportpath.write_text(json.dumps(report,indent=2)+"\n")
 artifacts=[{"path":c.get("output"),"sha256":c.get("sha256"),"bytes":c.get("bytes"),"status":c["status"]} for c in result if c.get("output")]
 manifest={"version":VERSION,"input":str(in_copy.relative_to(ROOT)),"input_sha256":sha(in_copy),"candidate_inputs":[{"path":c.get("input_model"),"sha256":c.get("input_sha256")} for c in result if c.get("input_model")],"report":"build/slicer/slice-report.json","report_sha256":sha(reportpath),"artifacts":artifacts,"network":"disabled"}
 (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
 print(json.dumps(report,indent=2));return 0 if status=="PASS" else 3

def main():
 p=argparse.ArgumentParser(prog="cad3d-orca");s=p.add_subparsers(dest="cmd",required=True)
 s.add_parser("doctor");s.add_parser("slice-report")
 q=s.add_parser("preflight");q.add_argument("--printer",required=True);q.add_argument("--material",required=True);q.add_argument("--process",default="standard-0.20")
 q=s.add_parser("slice");q.add_argument("--printer",required=True);q.add_argument("--material",required=True);q.add_argument("--process",default="standard-0.20");q.add_argument("--model",default="build/outputs");q.add_argument("--margin-mm",type=float,default=5.);q.add_argument("--compare-orientations",action="store_true")
 a=p.parse_args()
 try:
  if a.cmd=="doctor":doctor();return 0
  if a.cmd=="preflight":
   result=preflight(a.printer,a.material,a.process);print(json.dumps(result,indent=2))
   return {"PASS":0,"NOT_EVALUATED":4,"FAIL":2}[result["status"]]
  if a.cmd=="slice-report":
   f=OUT/"slice-report.json"
   if not f.is_file():print(json.dumps({"status":"NOT_EVALUATED","reason":"report_missing"}));return 4
   print(f.read_text());return 0
  return slice_cmd(a)
 except Exception as e:
  OUT.mkdir(parents=True,exist_ok=True);r={"status":"FAIL","reason":"orca_engine_error","detail":str(e),"printer_communication":"NOT_PERFORMED"}
  (OUT/"slice-report.json").write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2),file=sys.stderr);return 2

if __name__=="__main__":sys.exit(main())

