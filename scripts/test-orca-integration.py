#!/usr/bin/env python3
"""Black-box acceptance checks against the real, isolated OrcaSlicer container."""
import argparse, json, os, shutil, subprocess, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAD=shutil.which("cad3d")
if not CAD: raise SystemExit("cad3d CLI is not on PATH")

def box_stl(x, y, z):
    v=[(0,0,0),(x,0,0),(x,y,0),(0,y,0),(0,0,z),(x,0,z),(x,y,z),(0,y,z)]
    faces=[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    lines=["solid cad3d"]
    for a,b,c in faces:
        lines += [" facet normal 0 0 0","  outer loop"]
        lines += [f"   vertex {v[i][0]} {v[i][1]} {v[i][2]}" for i in (a,b,c)]
        lines += ["  endloop"," endfacet"]
    lines.append("endsolid cad3d")
    return "\n".join(lines)+"\n"

def call(cwd,*args,expect=0):
    p=subprocess.run([CAD,*args],cwd=cwd,text=True,capture_output=True)
    if p.returncode!=expect:
        raise AssertionError(f"{args}: expected exit {expect}, got {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p

def payload(p):
    text=p.stdout+"\n"+p.stderr
    start=text.find("{")
    if start<0: raise AssertionError(f"no JSON report in command output:\n{text}")
    return json.JSONDecoder().raw_decode(text[start:])[0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project",default="/tmp/cad3d-orca-v13-acceptance")
    a=ap.parse_args()
    project=Path(a.project).resolve()
    if project.exists() and any(project.iterdir()):
        raise SystemExit(f"refusing to overwrite nonempty acceptance project: {project}")
    project.mkdir(parents=True,exist_ok=True)
    # CAD Engine produces the real calibration specimen; only this exported STL is copied to the new project.
    source=ROOT/"examples/calibration-box/build/outputs/body.stl"
    if not source.is_file():
        subprocess.run([CAD,"build"],cwd=ROOT/"examples/calibration-box",check=True)
    shutil.copy2(source,project/"calibration-body.stl")
    (project/"oversize.stl").write_text(box_stl(252,20,20))
    doctor=call(project,"slicer","doctor")
    assert payload(doctor)["status"]=="PASS"
    missing=call(project,"slice","--printer","does-not-exist","--material","petg","--model","calibration-body.stl",expect=2)
    assert payload(missing)["status"]=="FAIL"
    too_big=call(project,"slice","--printer","elegoo-cc2","--material","petg","--model","oversize.stl",expect=3)
    big_report=payload(too_big)
    assert big_report["slicing_started"] is False and big_report["status"]=="FAIL"
    sliced=call(project,"slice","--printer","elegoo-cc2","--material","petg","--model","calibration-body.stl")
    report=payload(sliced)
    assert report["status"]=="PASS",sliced.stdout
    candidate=report["candidates"][0]
    assert candidate["returncode"]==0 and candidate["valid_3mf"] is True
    assert candidate["effective_material_match"]=="PASS"
    artifact=project/candidate["output"]
    assert artifact.is_file() and artifact.stat().st_size>0
    with zipfile.ZipFile(artifact) as z:
        assert z.testzip() is None and any(n.startswith("3D/") and n.endswith(".model") for n in z.namelist())
    assert all(name in candidate["profiles"] for name in ("machine","filament","process"))
    assert report["estimates"]["estimated_time_seconds"]>0
    assert report["estimates"]["filament_length_m"]>0
    assert report["estimates"]["filament_mass_g"]>0
    assert report["estimates"]["material"]["types"]==["PETG"]
    assert report["physical_print_validation"]=="NOT_EVALUATED"
    assert report["standalone_gcode_exported"] is False and report["printer_communication"]=="NOT_PERFORMED"
    assert candidate["gcode_side_effect_removed"] is True
    assert not (project/"build/slicer/plate_1.gcode").exists()
    shown=call(project,"slice-report")
    assert payload(shown)["status"]=="PASS"
    oriented=call(project,"slice","--printer","elegoo-cc2","--material","petg","--model","calibration-body.stl","--compare-orientations")
    orientation_report=payload(oriented)
    assert orientation_report["status"]=="PASS" and len(orientation_report["candidates"])==6
    assert all(c["returncode"]==0 and c["valid_3mf"] and c["effective_material_match"]=="PASS" for c in orientation_report["candidates"])
    security_env=os.environ.copy()
    security_env.update({"CAD3D_PROJECT":str(project),"CAD3D_UID":str(os.getuid()),"CAD3D_GID":str(os.getgid())})
    sec=subprocess.run(["docker","compose","-f",str(ROOT/"compose.yaml"),"config"],cwd=project,env=security_env,text=True,capture_output=True,check=True).stdout
    service=sec.split("  orca:",1)[1]
    assert "network_mode: none" in service and "read_only: true" in service and "no-new-privileges:true" in service
    assert "ports:" not in service and "/var/run/docker.sock" not in sec
    assert "cap_drop:" in service and "- ALL" in service and "cpus: 4" in service
    assert 'mem_limit: "8589934592"' in service and "pids_limit: 512" in service
    assert "source: /tmp/" in service and "target: /workspace" in service
    image_user=subprocess.run(["docker","image","inspect","cad3d-orca:2.4.2","--format","{{.Config.User}}"],text=True,capture_output=True,check=True).stdout.strip()
    assert image_user=="1000:1000",image_user
    print(json.dumps({"status":"PASS","project":str(project),"tests":{
      "real_headless_orca_and_exact_profiles":"PASS","unknown_profile_rejected":"PASS","over_envelope_rejected":"PASS",
      "real_sliced_3mf_reopened":"PASS","report_cli":"PASS","transient_gcode_removed":"PASS","container_security_contract":"PASS"},
      "slicer_estimates":orientation_report["estimates"],"orientation_candidates":len(orientation_report["candidates"]),
      "sliced_artifact":str(artifact),"report":str(project/"build/slicer/slice-report.json")},indent=2))

if __name__=="__main__":main()

