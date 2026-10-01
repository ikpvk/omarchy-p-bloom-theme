"""Shared page composition for individually modeled hardware assemblies."""
import os,json
from pathlib import Path
from functools import lru_cache
from sheet import WHITE,ARC,GOLD
ROOT=Path(__file__).resolve().parents[1]/'assets/hardware-family'
SUBJECTS={'greener','sky-racer','organ-foundry','air-refinery','aroma-organ','cortical-mesh','tether-climber','fusion-transport','volumetric-stage','bounder'}
def enabled(name):return name in SUBJECTS and os.environ.get('PBLOOM_HARDWARE_SET','retro')=='retro'
@lru_cache(None)
def data(name):
 from path_cleanup import load
 return load(ROOT/(name+'.json'))
@lru_cache(None)
def labels():return json.loads((ROOT/'labels.json').read_text())
def draw(s,name,mx,my):
 d=data(name);pts=[p for path in d['paths'] for p in path['points']];x0=min(x for x,y in pts);x1=max(x for x,y in pts);y0=min(y for x,y in pts);y1=max(y for x,y in pts)
 scale=min(620/(x1-x0),695/(y1-y0));dx=-(x0+x1)/2*scale;dy=-(y0+y1)/2*scale-25
 c=s.c;c.save();c.translate(mx+dx,my+dy);c.scale(scale,scale)
 styles={'shell':(.39,.47,WHITE),'plate':(.87,1,WHITE),'structure':(.85,.86,WHITE),'detail':(.53,.43,WHITE),'accent':(.88,.65,ARC),'cable':(.57,.42,GOLD),'fine':(.40,.28,ARC),'hologram':(.60,.40,ARC),'figure':(.95,.95,WHITE),'grass':(.76,.60,WHITE),'radiator':(.66,.35,ARC)}
 from path_cleanup import trace
 for p in d['paths']:
  trace(c,p)
  a,w,col=styles[p['role']];s._stroke(a,w/max(.75,scale**.35),None,col)
 c.restore()
 annotation={v[0]:v[1] if len(v)>1 else None for v in labels()[name]}
 positions={lab:(x*scale+dx,y*scale+dy) for lab,(x,y) in d['anchors'].items()}
 for lab,(sx,sy) in ANCHOR_SHIFTS.get(name,{}).items():
  x,y=positions[lab];positions[lab]=(x+sx,y+sy)
 ordered=sorted(positions,key=lambda lab:positions[lab][0]);split=len(ordered)//2
 from label_layout import LABEL_OFFSETS,COMPACT_OFFSETS
 def elbow(side,i,n,lab):
  ex=side*383;ey=-345+i*(550 if side<0 else 635)/max(1,n-1)
  if name=='cortical-mesh' and lab=='MESH THREAD':ey-=22
  ox,oy=LABEL_OFFSETS.get(name,{}).get(lab,(0,0))
  if not s.wide:
   cx,cy=COMPACT_OFFSETS.get(name,{}).get(lab,(0,0));ox+=cx;oy+=cy
  return ex-ox,ey-oy
 for side,group in [(-1,ordered[:split]),(1,ordered[split:])]:
  group.sort(key=lambda lab:positions[lab][1])
  def drawn(i,lab):
   # Where s.leader puts the elbow: it adds the sheet subject's offsets back.
   ex,ey=elbow(side,i,len(group),lab);subject=getattr(s,'subject','')
   ox,oy=LABEL_OFFSETS.get(subject,{}).get(lab,(0,0))
   if not s.wide:
    cx,cy=COMPACT_OFFSETS.get(subject,{}).get(lab,(0,0));ox+=cx;oy+=cy
   return ex+ox,ey+oy
  group=uncrossed(group,positions,drawn)
  for i,lab in enumerate(group):
   x,y=positions[lab];ex,ey=elbow(side,i,len(group),lab)
   s.leader(mx+x,my+y,ex-x,ey-y,side*95,lab,annotation.get(lab))


# Anchor dots that land on a neighbouring part in the projection (drawing units):
# the dot moves onto the visible part it names.
ANCHOR_SHIFTS={'sky-racer':{'FOLDING ARM':(-6,31)},          # off the pack, onto the arm
               'aroma-organ':{'BASE ODORANT':(17,-41)},      # off the clearing fan, onto a cartridge
               'air-refinery':{'MIRROR FIELD':(-73,58)}}     # off the base plate, onto a mirror


def uncrossed(group,positions,elbow):
 """Label order on one side, top to bottom. Sorting by anchor height can still
 cross two leaders (an anchor far inside sits lower than its neighbour's);
 then the order with no crossing and the least leader length wins."""
 from itertools import permutations
 def cross(a,b,c,d):
  o=lambda p,q,r:(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
  return o(a,b,c)*o(a,b,d)<0 and o(c,d,a)*o(c,d,b)<0
 def crossings(order):
  seg=[(positions[lab],elbow(i,lab)) for i,lab in enumerate(order)]
  return sum(cross(*seg[i],*seg[j]) for i in range(len(seg)) for j in range(i+1,len(seg)))
 if not crossings(group) or len(group)>6:return group
 def length(order):
  return sum(((positions[lab][0]-elbow(i,lab)[0])**2+(positions[lab][1]-elbow(i,lab)[1])**2)**.5 for i,lab in enumerate(order))
 return list(min(permutations(group),key=lambda o:(crossings(o),length(o))))
