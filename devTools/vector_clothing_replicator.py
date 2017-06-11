#!/usr/bin/env python3

from svg.path import parse_path
import copy

REFERENCE_PATH_SAMPLES = 50

xpath_shape = './svg:g[@id="Chest"]/svg:g[@id="Boob_%s"]/svg:g[starts-with(@id, "Boob_Large") or starts-with(@id, "Areola")]/svg:path[@style="fill:#f6e0e8" or @style="fill:#d76b93"]/@d'
xpath_outfit_container = './svg:g[@id="Chest_Outfit"]'
xpath_outfit = './svg:g[@id="Boob_%s_straps"]'
target_ids = "0,1,2,3,4,5,6,7".split(",")
reference_id = "2"

#xpath_shape = './svg:g[@id="Torso"]/svg:g[@id="Torso_%s"]/svg:path[@style="fill:#f6e0e8"]/@d'
#xpath_outfit_container = './svg:g[@id="Torso_Outfit"]'
#xpath_outfit = './svg:g[@id="Torso_%s_straps"]'
#target_ids = "Unnatural,Hourglass,Normal".split(",")
#reference_id = "Hourglass"

#import xml.etree.ElementTree # insufficient xpath abilities
import lxml.etree as etree
root = etree.parse('vector source.svg')
ns = {'svg' : 'http://www.w3.org/2000/svg'}

def get_points(xpath_shape, index):
  print('Getting shape data for "%s"...'%(index))
  paths_data = root.xpath(xpath_shape%(index),namespaces=ns)
  points = []
  path_length = None
  for path_data in paths_data:
    p = parse_path(path_data)
    points += [
      p.point(1.0/float(REFERENCE_PATH_SAMPLES)*i) 
      for i in range(REFERENCE_PATH_SAMPLES)
    ]
  if (not points):
    raise RuntimeError('No reference points found by selector "%s".'%(xpath_shape%(index)))
  return points

def point_movement(point, reference_points, target_points):
  distances = [abs(point - reference_point) for reference_point in reference_points]
  min_ref_dist_idx = min(enumerate(distances), key=lambda x:x[1])[0]
  movement = target_points[min_ref_dist_idx] - reference_points[min_ref_dist_idx]
  return movement

reference_points = get_points(xpath_shape, reference_id)
container = root.xpath(xpath_outfit_container,namespaces=ns)
if (len(container) != 1):
  raise RuntimeError('Outfit container selector "%s" does not yield exactly one layer.'%(xpath_outfit_container))
container = container[0]
outfit_source = container.xpath(xpath_outfit%(reference_id),namespaces=ns)
if (len(outfit_source) != 1):
  raise RuntimeError('Outfit source selector "%s" does not yield exactly one outfit layer in container selected by "%s".'%(xpath_outfit%(reference_id), xpath_outfit_container))
outfit_source = outfit_source[0]

for target_id in target_ids:
  outfit = copy.deepcopy(outfit_source)
  paths = outfit.xpath('./svg:path',namespaces=ns)
  if target_id == reference_id:
    continue
  layerid = outfit.get("id").replace("_%s_"%(reference_id),"_%s_"%(target_id))
  outfit.set("id", layerid)
  outfit.set(etree.QName("http://www.inkscape.org/namespaces/inkscape", 'label'), layerid)
  target_points = get_points(xpath_shape, target_id)
  for path in paths:
    path_data = path.get("d")
    p = parse_path(path_data)
    for segment in p:
      start_movement = point_movement(segment.start, reference_points, target_points)
      segment.start += start_movement
      end_movement = point_movement(segment.end, reference_points, target_points)
      segment.end += end_movement
      try:
        segment.control1 += start_movement
        segment.control2 += end_movement
      except AttributeError as ae:
        # segment is not a CubicBezier
        pass
    path.set("d", p.d())
  container.append(outfit)

svg = etree.tostring(root, pretty_print=True)
with open('replicated.svg', 'wb') as f: 
  f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'.encode("utf-8"))
  f.write(svg)

'''
Problems:
* Inconsistent layer names
* Groups are no Inkscape layers by default
* Inkscape uses layer labels instead of ids
* handles paths only
* only svg.path Line and CubicBezier are tested
'''
