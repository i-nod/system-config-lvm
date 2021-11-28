
import os
import string
from lvmui_constants import *


class Volume:

  def __init__(self, name, path, used, attrs, uuid):
    self.set_name(name)
    self.set_path(path)
    self.set_vg(None)
    self.set_used(used)
    self.set_attr(attrs)
    self.set_uuid(uuid)
    
    self.set_properties([])
    
    self.set_extent_size(0)
    self.total_extents = None
    self.allocated_extents = None
    self.free_extents = None
    
  
  def set_name(self, name):
    self.name = name.strip()
  def get_name(self):
    return self.name
  
  def set_uuid(self, uuid):
    self.uuid = uuid
  def get_uuid(self):
    return self.uuid
  
  def set_extent_size(self, size): # in bytes
    self.extent_size = int(size)
  def get_extent_size(self): # bytes
    return self.extent_size
  
  def set_extent_count(self, total, used):
    self.total_extents = int(total)
    self.allocated_extents = int(used)
    self.free_extents = self.total_extents - self.allocated_extents
  def get_extent_total_used_free(self):
    return self.total_extents, self.allocated_extents, self.free_extents
  
  def get_size_total_used_free_string(self):
    total, used, free = self.get_extent_total_used_free()
    total = self.__build_size_string(total)
    used = self.__build_size_string(used)
    free = self.__build_size_string(free)
    return total, used, free
  
  def get_size_total_string(self):
    return self.get_size_total_used_free_string()[0]
  
  def set_path(self, path):
    self.path = path
  def get_path(self):
    return self.path
  
  def set_vg(self, vg):
    self.vg = vg
  def get_vg(self):
    return self.vg
  
  def set_used(self, bool):
    self.used = bool
  def is_used(self):
    return self.used
  
  def set_attr(self, attr):
    self.attr = attr
  def get_attr(self):
    return self.attr
  
  def set_properties(self, props_list):
    self.properties = props_list
  def add_property(self, prop_key, prop):
    self.properties.append(prop_key)
    self.properties.append(prop)
  def get_properties(self):
    return self.properties
  
  
  def __build_size_string(self, extents):
    if extents == None:
      return '0' + BYTE_SUFFIX
    
    size_bytes = self.get_extent_size() * extents
    size_kilos = size_bytes / 1024.0
    size_megas = size_kilos / 1024.0
    size_gigs = size_megas / 1024.0
    
    if size_gigs > 1.0:
      return "%.2f " % size_gigs + GIG_SUFFIX
    elif size_megas > 1.0:
      return "%.2f " % size_megas + MEG_SUFFIX
    elif size_kilos > 1.0:
      return "%.2f " % size_kilos + KILO_SUFFIX
    else:
      return str(size_bytes) + BYTE_SUFFIX
