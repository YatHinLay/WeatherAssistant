import json,re,math
from pathlib import Path
root=Path.cwd()
# 坐标来源为 BD-09；转换为 Open-Meteo 使用的 WGS-84。
def wgs(lng,lat):
 x,y=lng-.0065,lat-.006
 z=math.hypot(x,y)-.00002*math.sin(y*math.pi*3000/180)
 t=math.atan2(y,x)-.000003*math.cos(x*math.pi*3000/180)
 lng,lat=z*math.cos(t),z*math.sin(t)
 if not (72.004<lng<137.8347 and .8293<lat<55.8271): return [round(lng,5),round(lat,5)]
 x,y=lng-105,lat-35
 dlat=-100+2*x+3*y+.2*y*y+.1*x*y+.2*math.sqrt(abs(x))
 dlat+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
 dlat+=(20*math.sin(y*math.pi)+40*math.sin(y*math.pi/3))*2/3
 dlat+=(160*math.sin(y*math.pi/12)+320*math.sin(y*math.pi/30))*2/3
 dlng=300+x+2*y+.1*x*x+.1*x*y+.1*math.sqrt(abs(x))
 dlng+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
 dlng+=(20*math.sin(x*math.pi)+40*math.sin(x*math.pi/3))*2/3
 dlng+=(150*math.sin(x*math.pi/12)+300*math.sin(x*math.pi/30))*2/3
 rad=lat*math.pi/180; magic=1-.006693421622965943*math.sin(rad)**2
 dlat=dlat*180/((6378245*(1-.006693421622965943))/(magic*math.sqrt(magic))*math.pi)
 dlng=dlng*180/(6378245/math.sqrt(magic)*math.cos(rad)*math.pi)
 return [round(lng-dlng,5),round(lat-dlat,5)]
coords={code:(name,wgs(float(lng),float(lat))) for code,name,parent,lng,lat in re.findall(r"\('([^']+)','([^']+)','([^']*)','([^']+)','([^']+)'",(root/'backend/regions-coordinates.sql').read_text(encoding='utf-8')) if lng and lat}
regions=json.loads((root/'frontend/src/regions.json').read_text(encoding='utf-8'))
counts=[0,0]
for province in regions:
 for city in province['children']:
  if city['name']=='市辖区': city['name']=province['name']
  for district in city['children']:
   counts[0]+=1
   item=coords.get(district['code'])
   if item and item[0]==district['name']:
    district['longitude'],district['latitude']=item[1];counts[1]+=1
(root/'frontend/src/regions.json').write_text(json.dumps(regions,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
assert len(regions)>=31
print('districts, with coordinates:',counts)
