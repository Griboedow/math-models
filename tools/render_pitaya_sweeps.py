from pathlib import Path
import sys,json,math,argparse
import numpy as np
import vtk
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Render the saved PITAYA loop sweep results; requires VTK, numpy, Pillow and the CAD package renderer.')
parser.add_argument('cad_package',type=Path)
parser.add_argument('--results',type=Path,default=ROOT/'results/pitaya_v10_recheck')
args=parser.parse_args();CAD=args.cad_package.resolve();OUT=args.results.resolve()
sys.path.insert(0,str(CAD/'source'))
from render_model import actor_from_file,BG
data=json.loads((OUT/'sweeps.json').read_text())
routes={r['kind']:r for r in data if r['kind'].startswith('loop')}
angle=math.radians(-30)
rotation=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])

def cord(ren,points,color,radius=1,opacity=1):
    points=np.asarray(points)@rotation.T*1000
    pts=vtk.vtkPoints()
    for p in points:pts.InsertNextPoint(*p)
    cell=vtk.vtkPolyLine();cell.GetPointIds().SetNumberOfIds(len(points))
    for i in range(len(points)):cell.GetPointIds().SetId(i,i)
    cells=vtk.vtkCellArray();cells.InsertNextCell(cell)
    poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetLines(cells)
    tube=vtk.vtkTubeFilter();tube.SetInputData(poly);tube.SetRadius(radius);tube.SetNumberOfSides(20);tube.CappingOn()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(tube.GetOutputPort())
    a=vtk.vtkActor();a.SetMapper(mapper);a.GetProperty().SetColor(*color);a.GetProperty().SetOpacity(opacity);ren.AddActor(a)

def render(name,route):
    ren=vtk.vtkRenderer();ren.SetBackground(*BG)
    for part,color in [('body','#F43788'),('leaf_1','#58AE70'),('platter','#FFF8E9'),('seeds','#34303C')]:
        a=actor_from_file(CAD/'cad'/f'{part}.stl',color)
        a.RotateZ(-30);a.SetPosition(0,0,1)
        if part=='leaf_1':a.GetMapper().GetInputAlgorithm().SetFeatureAngle(5)
        ren.AddActor(a)
    poses=np.asarray(route['poses_m'])
    cord(ren,poses[0],(.45,.48,.49),opacity=.7)
    if route['result']['status']=='contact_on_prescribed_sweep':
        cord(ren,route['result']['contact_points_m'],(.9,.20,.08))
    else:
        for pose in poses[1:]:cord(ren,pose,(.10,.36,.66))
        cord(ren,poses.mean(axis=1),(.10,.36,.66),radius=.3)
    ren.AutomaticLightCreationOff()
    for pos,intensity in [((180,-150,220),.75),((180,170,100),.55)]:
        light=vtk.vtkLight();light.SetPosition(*pos);light.SetFocalPoint(76,0,20);light.SetIntensity(intensity);ren.AddLight(light)
    cam=ren.GetActiveCamera();cam.SetFocalPoint(78,0,24);cam.SetPosition(200,225,120);cam.SetViewUp(0,0,1);cam.ParallelProjectionOn();cam.SetParallelScale(37)
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.AddRenderer(ren);win.SetSize(1000,900);ren.UseFXAAOn();win.SetMultiSamples(0);ren.ResetCameraClippingRange();win.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(win);capture.ReadFrontBufferOff();capture.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(OUT/name));writer.SetInputConnection(capture.GetOutputPort());writer.Write();win.Finalize()

render('loop_contact.png',routes['loop_lift_straight'])
render('loop_clear_route.png',routes['loop_outward_then_up'])
board=Image.new('RGB',(2000,1040),'#f4f1eb');d=ImageDraw.Draw(board)
try:
    bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',31);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
except OSError:
    bold=ImageFont.truetype('DejaVuSans-Bold.ttf',31);font=ImageFont.truetype('DejaVuSans.ttf',25)
for x,name,title in [(0,'loop_contact.png','Подъём петли вверх: контакт с листом'),(1000,'loop_clear_route.png','Сначала наружу, затем вверх: свободно')]:
    board.paste(Image.open(OUT/name),(x,65));d.text((x+25,17),title,font=bold,fill='#993260')
d.text((25,977),'Нить Ø2 мм. Серый — начальное положение; цвет — проверенные положения заданного движения.',font=font,fill='#57665f')
d.text((25,1008),'Геометрическая проверка по STL: трение, ворс и самостоятельное соскальзывание не рассчитывались.',font=font,fill='#57665f')
board.save(OUT/'leaf_sweep_comparison.png')
print(OUT/'leaf_sweep_comparison.png')
