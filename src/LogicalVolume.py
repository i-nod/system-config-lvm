
import os
import string
from lvmui_constants import *

from Volume import Volume
from Segment import MIRROR_SEGMENT_ID


class LogicalVolume(Volume):
  
  def __init__(self, name, path, used, attrs, uuid):
    Volume.__init__(self, name, path, used, attrs, uuid)
    
    self.segments = []
    
    self.snapshot_origin = None
    self.snapshot_usage = 0
    self.snapshots = []
    
    self.set_mirror_log()
    self.is_mirror_log = False
    self.is_mirror_image = False
    
    self.set_stripes_num(0)
    
  
  def add_segment(self, segment):
    self.segments.append(segment)
    self.__sort_segments()
  def get_segments(self):
    return self.segments
  def __sort_segments(self):
    segs = self.segments
    for i in range(len(segs) - 1, 0, -1):
      for j in range(i, 0, -1):
        start1, size1 = segs[j-1].get_start_size()
        start2, size2 = segs[j].get_start_size()
        if start2 < start1:
          tmp = segs[j-1]
          segs[j-1] = segs[j]
          segs[j] = tmp
    
  
  def is_snapshot(self):
    return self.snapshot_origin != None
  def set_snapshot_info(self, origin, usage_percent):
    self.snapshot_origin = origin
    self.snapshot_usage = int(usage_percent)
  def get_snapshot_info(self):
    return self.snapshot_origin, self.snapshot_usage
  def has_snapshots(self):
    return len(self.snapshots) > 0
  def add_snapshot(self, snapshot):
    self.snapshots.append(snapshot)
  def get_snapshots(self):
    return self.snapshots
  
  def is_mirrored(self):
    if len(self.segments) == 1:
      if self.segments[0].get_type() == MIRROR_SEGMENT_ID:
        return True
    return False
  
  def set_stripes_num(self, num):
    self.stripes = num
  def is_striped(self):
    return self.stripes > 1
  def stripes_num(self):
    return self.stripes
  
  def set_mirror_log(self, log=None):
    self.mirror_log = log
    if log != None and log.__class__ == self.__class__:
      log.is_mirror_log = True
      log.set_name(self.get_name())
  def get_mirror_log(self):
    return self.mirror_log
  
  def print_out(self, padding):
    print(padding + 'LV: ' + self.get_name() + ' ' + str(self.get_path()) + ' ' + str(self.get_extent_total_used_free()[1]))
    if self.is_snapshot():
      info = self.get_snapshot_info()
      print(padding + 'snapshot origin(' + info[0].get_name() + ')')
    if self.has_snapshots():
      snaps = self.get_snapshots()
      snaps_str = snaps[0].get_name()
      for snap in snaps:
        snaps_str = snaps_str + ', ' + snap.get_name()
      print(padding + 'snapshots: ' + snaps_str)
    print(padding + 'segments:')
    for seg in self.segments:
      seg.print_out(padding + '  ')
