
import os
import string
from lvmui_constants import *
from fdisk_wrapper import ID_EMPTY


from Volume import Volume


class PhysicalVolume(Volume):
  def __init__(self, name, fmt, attr, psize, pfree, initialized, total, alloc):
    Volume.__init__(self, name, None, initialized, attr, None)
    
    # pv properties
    self.size = float(psize) #This is in gigabytes
    #self.size_string = self.build_size_string(self.size)
    self.pfree = float(pfree)
    
    self.format = fmt
    
    self.set_extent_count(total, alloc)
    
    self.extent_blocks = []
    
    # type will get changed at set_vg call
    self.type = UNINITIALIZED_TYPE
    
    # general properties
    self.devnames = []
    self.part = None
    self.initializable = True
    
    self.setMultipath(None)
    
  
  def get_size_total_string(self):
    if self.get_type() == PHYS_TYPE:
      size = self.get_size_total_used_free_string()[0]
    else:
      return "%.2f" % self.size + GIG_SUFFIX
  
  def get_description(self, fullpath=True, long_descr=True):
    if fullpath:
      ret_str = self.get_path()
    else:
      ret_str = self.extract_name(self.get_path())
    if long_descr:
      upper_limit = len(self.get_paths())
    else:
      upper_limit = 2
    for path in self.get_paths()[1:upper_limit]:
      if fullpath:
        ret_str = ret_str + ',\n' + path
      else:
        ret_str = ret_str + ',\n' + self.extract_name(path)
    if upper_limit < len(self.get_paths()):
      ret_str = ret_str + ', ...'
    
    if self.part != None:
      if self.part.id == ID_EMPTY and not self.wholeDevice():
        ret_str = UNPARTITIONED_SPACE_ON % ('\n' + ret_str)
    
    return ret_str
  
  def get_type(self):
    return self.type
  
  def add_extent_block(self, extent_block):
    self.extent_blocks.append(extent_block)
    self.__sort_extent_blocks()
  def get_extent_blocks(self):
    return self.extent_blocks
  def __sort_extent_blocks(self):
    blocks = self.extent_blocks
    for i in range(len(blocks) - 1, 0, -1):
      for j in range(i, 0, -1):
        start1, size1 = blocks[j-1].get_start_size()
        start2, size2 = blocks[j].get_start_size()
        if start2 < start1:
          tmp = blocks[j-1]
          blocks[j-1] = blocks[j]
          blocks[j] = tmp
  
  def extract_name(self, path):
    idx = path.rfind("/")
    idx = idx + 1    #Leave off '/' char
    name = path[idx:] #get substring from idx to end of string
    return name
  
  def set_vg(self, vg):
    Volume.set_vg(self, vg)
    if vg == None:
      self.type = UNALLOCATED_TYPE
    else:
      self.type = PHYS_TYPE
  
  def get_paths(self):
    volume_path = Volume.get_path(self)
    part = self.part
    if part == None:
      return [volume_path]
    paths = []
    if volume_path != None:
      paths.append(volume_path)
    for devname in self.devnames:
      if part.id == ID_EMPTY:
        path = devname
      else:
        path = devname + str(part.num)
      if path not in paths:
        paths.append(path)
    return paths
  def get_path(self): # return main path
    if len(self.get_paths()) == 0:
      return None
    else:
      return self.get_paths()[0]
  
  def getDevnames(self):
    return self.devnames
  def addDevname(self, devname):
    devname = devname.strip()
    if devname not in self.devnames:
      self.devnames.append(devname)
  def removeDevname(self, devname):
    if devname in self.devnames:
      self.devnames.pop(self.devnames.index(devname))
  
  def setMultipath(self, multipath):
    self.multipath = multipath
  def getMultipath(self):
    return self.multipath
  
  def setPartition(self, xxx_todo_changeme):
    (devname, part) = xxx_todo_changeme
    self.size = part.getSizeBytes()/1024.0/1024/1024
    self.part = part
    self.addDevname(devname)
    if part.id == ID_EMPTY:
      self.set_name(UNPARTITIONED_SPACE)
    else:
      self.set_name(_("Partition %s") % str(part.num))
    
    
  def getPartition(self):
    if len(self.getDevnames()) > 0:
      return (self.getDevnames()[0], self.part)
    else:
      return None
  
  def needsFormat(self):
    if self.part == None:
      return False
    return self.part.id == ID_EMPTY
  
  def wholeDevice(self): # part occupies whole device
    if self.part == None:
      return False
    return self.part.wholeDevice
  
  
  
  def print_out(self, padding):
    print(padding + 'PV: ' + self.get_name() + ' paths: ' + str(self.get_paths()) + ' devices: ' + str(self.getDevnames()) + ' multipath ' + str(self.getMultipath()))
    print(padding + 'extents:')
    if len(self.get_extent_blocks()) == 0:
      print(padding + '  None')
    for extent in self.get_extent_blocks():
      extent.print_out(padding + '  ')
