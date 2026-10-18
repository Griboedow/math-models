"""Render the CAD surface and checked cord pose at one reported risk zone."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import vtk

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yarnstand.mesh import MeshScene

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('manifest');parser.add_argument('audit');parser.add_argument('--case',required=True)
parser.add_argument('--part',required=True);parser.add_argument('--out',required=True)
args=parser.parse_args()
scene=MeshScene.from_manifest(args.manifest);report=json.loads(Path(args.audit).read_text(encoding='utf-8-sig'))
case=next(c for c in report['cases'] if c['id']==args.case)
part=next(p for p in case['parts'] if p['part']==args.part);site=part['site']
if site is None:parser.error('This part was separated by bounding volumes; no sampled closest pose is available')
inputs=next(c for c in report['inputs']['cases'] if c['id']==args.case)
focus=np.asarray(site['surface_world_m']);origin=np.asarray(inputs.get('rotation_origin_m',[0,0,0]))
progress=site['pose_coordinate'];i=min(int(progress),len(inputs['poses_m'])-1);fraction=progress-i
# Successful rows intentionally omit the large stored cord pose. Reconstruct
# their checked world pose from the unchanged input nodes and interpolation.
poses=np.asarray(inputs['poses_m'])
cord_pose=site.get('cord_pose_world_m',poses[i] if i==len(poses)-1 else poses[i]+fraction*(poses[i+1]-poses[i]))
ren=vtk.vtkRenderer();ren.SetBackground(.955,.961,.94)
for name,_,_,_,poly in scene.parts:
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly)
    actor=vtk.vtkActor();actor.SetMapper(mapper)
    if name==args.part:actor.GetProperty().SetColor(.25,.55,.43)
    else:actor.GetProperty().SetColor(.63,.66,.65);actor.GetProperty().SetOpacity(.22)
    angles=inputs.get('part_rotation_deg',{}).get(name,[0.]*len(inputs['poses_m']))
    angle=angles[i] if i==len(angles)-1 else angles[i]+fraction*(angles[i+1]-angles[i])
    actor.SetOrigin(*origin);actor.RotateZ(angle);ren.AddActor(actor)

def cord(points,radius,color,opacity=1.):
    pts=vtk.vtkPoints()
    for p in points:pts.InsertNextPoint(*p)
    line=vtk.vtkPolyLine();line.GetPointIds().SetNumberOfIds(len(points))
    for j in range(len(points)):line.GetPointIds().SetId(j,j)
    cells=vtk.vtkCellArray();cells.InsertNextCell(line)
    poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetLines(cells)
    tube=vtk.vtkTubeFilter();tube.SetInputData(poly);tube.SetRadius(radius);tube.SetNumberOfSides(16);tube.CappingOn()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(tube.GetOutputPort())
    actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*color);actor.GetProperty().SetOpacity(opacity);ren.AddActor(actor)

cord(cord_pose,case['yarn_radius_m']+report['effective_radial_allowance_m'],(.93,.6,.12),.3)
cord(cord_pose,case['yarn_radius_m'],(.76,.18,.13))
sphere=vtk.vtkSphereSource();sphere.SetCenter(*focus);sphere.SetRadius(.00065);sphere.SetThetaResolution(20);sphere.SetPhiResolution(16)
mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(sphere.GetOutputPort());actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(.95,.03,.08);ren.AddActor(actor)
camera=ren.GetActiveCamera();camera.SetFocalPoint(*focus)
direction=focus-origin;direction[2]=0
if np.linalg.norm(direction)<.001:direction=np.array([1.,-1.,0.])
direction/=np.linalg.norm(direction)
camera.SetPosition(*(focus+direction*.15+np.array([0,0,.065])))
camera.SetViewUp(0,0,1);camera.ParallelProjectionOn();camera.SetParallelScale(.025)
ren.ResetCameraClippingRange();ren.UseFXAAOn()
window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.AddRenderer(ren);window.SetSize(1200,900);window.SetMultiSamples(0);window.Render()
capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
writer=vtk.vtkPNGWriter();writer.SetFileName(str(Path(args.out).resolve()));writer.SetInputConnection(capture.GetOutputPort());writer.Write();window.Finalize()
print(args.out)
