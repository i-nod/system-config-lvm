
import os
import string
from lvmui_constants import VG_TYPE

from Volume import Volume


class VolumeGroup(Volume):
  def __init__(self, name, attr, extent_size, extents_total, extents_free, pvs_max, lvs_max):
    Volume.__init__(self, name, [], True, attr, None)
    
    self.set_extent_size(extent_size)
    self.set_extent_count(extents_total, extents_total - extents_free)
    
    self.lvs = {}
    self.pvs = {}
    
    self.max_pvs = pvs_max
    self.max_lvs = lvs_max
    
  
  def clustered(self):
    return 'c' in self.get_attr()
  
  
  def get_max_lvs(self):
    return self.max_lvs
  def get_max_pvs(self):
    return self.max_pvs
  
  def add_lv(self, lv):
    lv.set_vg(self)
    lv.set_extent_size(self.get_extent_size())
    self.lvs[lv.get_name()] = lv
  def get_lvs(self):
    return self.lvs
  
  def add_pv(self, pv):
    pv.set_vg(self)
    pv.set_extent_size(self.get_extent_size())
    self.pvs[pv.get_name()] = pv
  def get_pvs(self):
    return self.pvs
  
  
  def print_out(self):
    print('VG: ' + self.get_name())
    print(self.get_extent_total_used_free())
    print('LVs:')
    for lv in list(self.lvs.values()):
      lv.print_out('  ')
    print('PVs')
    for pv in list(self.pvs.values()):
      pv.print_out('  ')
    print('')
    print('')
