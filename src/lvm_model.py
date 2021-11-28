
import os
import sys
import string
import re
from lvmui_constants import *
from BlockDeviceModel import *
from CommandError import CommandError
from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus, ProgressPopup
import gettext
_ = gettext.gettext

from PhysicalVolume import *
from LogicalVolume import *
from VolumeGroup import *
from Segment import *
from ExtentBlock import *
from Multipath import Multipath

import Filesystem
import Fstab

from utilities import follow_links_to_target


#Column names for PVS calls
P_NAME_COL=0
P_VG_NAME_COL=1
P_FMT_COL=2
P_ATTR_COL=3
P_SIZE_COL=4
P_FREE_COL=5
P_PE_COUNT_COL=6
P_PE_ALLOC_COL=7

#Column names for PVS calls
L_NAME_COL=0
L_VG_NAME_COL=1
L_ATTR_COL=2
L_SIZE_COL=3

#Column names for lvdisplay calls
LV_PATH_COL=0
LV_VGNAME_COL=1

UNUSED=_("Unused") 
UNUSED_SPACE=_("Unused Space")

UNMOUNTED=_("Unmounted")
SEG_START_COL = 2
SEG_END_COL = 4
GIG=1000000000.00
VGS_OPTION_STRING="vg_name,vg_sysid,vg_fmt,vg_attr,vg_size,vg_free,vg_extent_count,vg_free_count,vg_extent_size,max_pv,pv_count,max_lv,lv_count,vg_uuid"


PVS_OPTION_STRING="pv_name,vg_name,pv_size,pv_used,pv_free,pv_pe_count,pv_pe_alloc_count,pv_attr,pv_uuid"


VG_NAME=_("Volume Group Name:   ")
VG_SYSID=_("System ID:   ")
VG_FMT=_("Format:   ")
VG_ATTR=_("Attributes:   ")
VG_SIZE=_("Volume Group Size:   ")
VG_FREE=_("Available Space:   ")
VG_EXTENT_COUNT=_("Total Number of Extents:   ")
VG_FREE_COUNT=_("Number of Free Extents:   ")
VG_EXTENT_SIZE=_("Extent Size:   ")
MAX_PV=_("Maximum Allowed Physical Volumes:   ")
PV_COUNT=_("Number of Physical Volumes:   ")
MAX_LV=_("Maximum Allowed Logical Volumes:   ")
LV_COUNT=_("Number of Logical Volumes:   ")
VG_UUID=_("VG UUID:   ")

LV_NAME=_("Logical Volume Name:   ")
LV_SIZE=_("Logical Volume Size:   ")
LV_SEG_COUNT=_("Number of Segments:   ")
LV_STRIPE_COUNT=_("Number of Stripes:   ")
LV_STRIPE_SIZE=_("Stripe Size:   ")
LV_ATTR=_("Attributes:   ")
LV_UUID=_("LV UUID:   ")

UV_PARTITION_TYPE=_("Partition Type:   ")
UV_SIZE=_("Size:   ")
UV_MOUNT_POINT=_("Mount Point:   ")
UV_MOUNTPOINT_AT_REBOOT=_("Mount Point when Rebooted:   ")
UV_FILESYSTEM=_("File System:   ")

PV_NAME=_("Physical Volume Name:   ")
PV_SIZE=_("Physical Volume Size:   ")
PV_USED=_("Space Used:   ")
PV_FREE=_("Space Free:   ")
PV_PE_COUNT=_("Total Physical Extents:   ")
PV_PE_ALLOC_COUNT=_("Allocated Physical Extents:   ")
PV_ATTR=_("Attributes:   ")
PV_UUID=_("PV UUID:   ")

NOT_INITIALIZABLE=_("Not initializable:")
EXTENDED_PARTITION=_("Extended partition")
#Translator: the line below refers to a standard linux swap partition.
SWAP_IN_USE=_("Swap partition currently in use")
FOREIGN_BOOT_PARTITION=_("Foreign boot partition")
AUTOPARTITION_FAILURE=_("Autopartition failure: %s")

VG_NAME_IDX = 0
VG_SYSID_IDX = 1
VG_FMT_IDX = 2
VG_ATTR_IDX = 3
VG_SIZE_IDX = 4
VG_FREE_IDX = 5
VG_EXTENT_COUNT_IDX = 6
VG_FREE_COUNT_IDX = 7
VG_EXTENT_SIZE_IDX = 8
MAX_PV_IDX = 9
PV_COUNT_IDX = 10
MAX_LV_IDX = 11
LV_COUNT_IDX = 12
VG_UUID_IDX = 13

PV_NAME_IDX = 0
PV_VG_NAME_IDX = 1
PV_SIZE_IDX = 2
PV_USED_IDX = 3
PV_FREE_IDX = 4
PV_PE_COUNT_IDX = 5
PV_PE_ALLOC_COUNT_IDX = 6
PV_ATTR_IDX = 7
PV_UUID_IDX = 8



LVS_HAS_ALL_OPTION = False
LVS_HAS_MIRROR_OPTIONS = False


class lvm_model:
  
  def __init__(self):
    global LVS_HAS_ALL_OPTION
    global LVS_HAS_MIRROR_OPTIONS
    
    out, status = execWithCaptureStatus(LVM_BIN_PATH, [LVM_BIN_PATH, 'lvs', '--config', "'log{command_names=0}'", '--all'])
    if status == 0:
      LVS_HAS_ALL_OPTION = True
    LVS_HAS_MIRROR_OPTIONS = LVS_HAS_ALL_OPTION
    
    self.__block_device_model = BlockDeviceModel()
    self.__VGs = {}
    self.__PVs = []
  
  def reload(self):
    progress = ProgressPopup(RELOAD_LVM_MESSAGE)
    progress.start()
    
    # clean-up everything
    self.__block_device_model = BlockDeviceModel()
    self.__VGs = {}
    self.__PVs = []
    
    # first query VolumeGroups
    self.__VGs = {}
    for vg in self.__query_VGs():
      self.__VGs[vg.get_name()] = vg
    
    # then query PVs
    self.__PVs = self.__query_partitions()
    
    # then query LVs
    self.__query_LVs()
    
    # then link all together
    self.__link_snapshots()
    self.__link_mirrors()
    
    # setup properties
    self.__set_VGs_props()
    self.__set_LVs_props() # has to come after link_mirrors
    self.__set_PVs_props()
    
    self.__add_unused_space()
    
    # debugging
    #for vg in self.__VGs.values():
    #  vg.print_out()
    #print '\n\nAll PVs'
    #for pv in self.__PVs:
    #  pv.print_out('')
    #sys.exit(0)
    
    progress.stop()
  
  def __query_partitions(self):
    parts = {} # PVs on a partition
    segs = []  # PVs on free space
    # get partitions from hard drives
    self.__block_device_model.reload()
    devs = self.__block_device_model.getDevices()
    # multipathing
    multipath_obj = Multipath()
    multipath_data = multipath_obj.get_multipath_data()
    for multipath in multipath_data:
      segments = []
      for path in multipath_data[multipath]:
        if path in devs:
          segments = devs[path]
          devs.pop(path)
      devs[multipath] = segments
    for devname in devs:
      self.__query_partitions2(devname, devs[devname], parts, segs)
    for pv in list(parts.values())[:]:
      devname = pv.getPartition()[0]
      if devname in multipath_data:
        parts.pop(pv.get_path())
        pv.removeDevname(devname)
        pv.setMultipath(devname)
        for path in multipath_data[devname]:
          pv.addDevname(path)
      for path in pv.get_paths():
        parts[path] = pv
    for pv in segs:
      devname = pv.getPartition()[0]
      if devname in multipath_data:
        pv.removeDevname(devname)
        pv.setMultipath(devname)
        for path in multipath_data[devname]:
          pv.addDevname(path)
    # disable swap partitions if in use
    result = execWithCapture('/bin/cat', ['/bin/cat', '/proc/swaps'])
    lines = result.splitlines()
    for line in lines:
      swap = line.split()[0]
      for multipath in multipath_data:
        if swap in multipath_data[multipath]:
          swap = multipath
      if swap in parts:
        parts[swap].initializable = False
        parts[swap].add_property(NOT_INITIALIZABLE, SWAP_IN_USE)
      for seg in segs:
        # swap could be a whole drive
        if swap == seg.get_path():
          seg.name = seg.extract_name(seg.get_path())
          seg.initializable = False
          seg.add_property(NOT_INITIALIZABLE, SWAP_IN_USE)
    # disable bootable partitions only if EXTended FS NOT on it (bootable flag is used by windows only)
    for path in parts:
      partition = parts[path].getPartition()[1]
      if partition.bootable:
        fs = self.__getFS(path)
        if re.match('.*ext[23].*', fs, re.I):
          # EXTended FS on it
          pass
        else:
          # some other filesystem on it
          parts[path].initializable = False
          parts[path].add_property(NOT_INITIALIZABLE, FOREIGN_BOOT_PARTITION)
    # disable unformated space, unless whole drive
    for seg in segs:
      if not seg.wholeDevice():
        # fdisk_wrapper not tested enough, so use it only on unpartitioned drives
        seg.initializable = False
        seg.add_property(NOT_INITIALIZABLE, _("Partition manually"))
    # merge parts with PVs
    for pv in self.__query_PVs():
      # assign unpartitioned drives, to PVs, if already used by LVM
      for seg in segs[:]:
        if pv.get_path() in seg.get_paths() or pv.get_path() == seg.getMultipath():
          pv.setPartition(seg.getPartition())
          pv.setMultipath(seg.getMultipath())
          for devname in seg.getDevnames():
            pv.addDevname(devname)
          pv.set_name(pv.extract_name(pv.get_path())) # overwrite Free Space label
          segs.remove(seg)
      # merge
      path = pv.get_path()
      if path in parts:
        old_pv = parts[path]
        pv.setPartition(old_pv.getPartition())
        pv.setMultipath(old_pv.getMultipath())
        for devname in old_pv.getDevnames():
          pv.addDevname(devname)
      else:
        # pv is not a partition, eg. loop device, or LV
        pass
      for path in pv.get_paths():
        parts[path] = pv
    # create return list
    pvs_list = list()
    for part in parts.values():
      if part not in pvs_list:
        pvs_list.append(part)
    for seg in segs:
      pvs_list.append(seg)
    # disable initialization of multipathed devices (for now)
    for pv in pvs_list:
      if len(pv.get_paths()) > 1:
        if pv.get_type() == UNINITIALIZED_TYPE:
          pv.add_property(NOT_INITIALIZABLE, _("Multipath device"))
          if pv.initializable:
            pv.initializable = False
            pv.add_property(_("Note:"), _("Initialize manually"))
    # all done
    return pvs_list
  def __query_partitions2(self, devname, segs, part_dictionary, seg_list):
    for seg in segs:
      if seg.id in ID_EXTENDS:
        self.__query_partitions2(devname, seg.children, part_dictionary, seg_list)
      # create pv
      pv = PhysicalVolume('/nothing', '', '', 0, 0, False, 0, 0)
      pv.setPartition((devname, seg))
      if seg.id == ID_EMPTY:
        seg_list.append(pv)
      else:
        if seg.id in ID_EXTENDS:
          # initialization of extended partition wipes all logical partitions !!!
          pv.initializable = False
          pv.add_property(NOT_INITIALIZABLE, EXTENDED_PARTITION)
        part_dictionary[pv.get_path()] = pv
  def __query_PVs(self):
    pvlist = list()
    arglist = list()
    arglist.append(LVM_BIN_PATH)
    arglist.append("pvs")
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")
    arglist.append("--nosuffix")
    arglist.append("--noheadings")
    arglist.append("--units")
    arglist.append("g")
    arglist.append("--separator")
    arglist.append(",")
    arglist.append("-o")
    arglist.append("+pv_pe_count,pv_pe_alloc_count")
    result_string = execWithCapture(LVM_BIN_PATH, arglist)
    lines = result_string.splitlines()
    for line in lines:
      line = line.strip()
      words = line.split(",")
      path = words[P_NAME_COL]
      pv = PhysicalVolume(path, 
                          words[P_FMT_COL], 
                          words[P_ATTR_COL], 
                          words[P_SIZE_COL], 
                          words[P_FREE_COL],
                          True,
                          words[P_PE_COUNT_COL], 
                          words[P_PE_ALLOC_COL])
      pv.set_path(path)
      vgname = words[P_VG_NAME_COL]
      if vgname == '':
        pv.set_vg(None)
      else:
        self.__VGs[vgname].add_pv(pv)
      pvlist.append(pv)
    return pvlist
  
  def query_uninitialized(self):
    uninit_list = list()
    for part in self.__PVs:
      if part.get_type() == UNINITIALIZED_TYPE:
        uninit_list.append(part)
    return uninit_list
  
  def query_unallocated(self):
    unalloc_list = list()
    for pv in self.__PVs:
      if pv.get_type() == UNALLOCATED_TYPE:
        unalloc_list.append(pv)
    return unalloc_list
  
  def query_PVs(self):
    pv_list = list()
    for pv in self.__PVs:
      if pv.get_type() == PHYS_TYPE:
        pv_list.append(pv)
    return pv_list
  
  
  def query_PVs_for_VG(self, vgname):
    vg = self.__VGs[vgname]
    return vg.get_pvs().values()
  
    hotlist = list()
    pv_s = self.query_PVs()
    for pv in pv_s:
      if pv.get_vg() == vg:
        hotlist.append(pv)
    return hotlist
  
  def __query_VGs(self):
    vglist = list()
    arglist = list()
    arglist.append(LVM_BIN_PATH)
    arglist.append("vgs")
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")
    arglist.append("--nosuffix")
    arglist.append("--noheadings")
    arglist.append("--units")
    arglist.append("b")
    arglist.append("--separator")
    arglist.append(",")
    arglist.append("-o")
    arglist.append("vg_name,vg_attr,vg_size,vg_extent_size,vg_free_count,max_lv,max_pv")
    
    result_string = execWithCapture(LVM_BIN_PATH,arglist)
    lines = result_string.splitlines()
    for line in lines:
      line = line.strip()
      words = line.split(",")
      
      extent_size = int(words[3])
      extents_total = int(words[2]) / extent_size
      extents_free = int(words[4])
      
      vgname = words[0].strip()
      
      max_lvs, max_pvs = int(words[5]), int(words[6])
      if max_lvs == 0:
        max_lvs = 256
      if max_pvs == 0:
        max_pvs = 256
      
      vg = VolumeGroup(vgname, words[1], extent_size, extents_total, extents_free, max_pvs, max_lvs)
      vglist.append(vg)
    return vglist
  
  
  def get_VGs(self):
    return self.__VGs.values()
  
  def get_VG(self, vgname):
    return self.__VGs[vgname]
  
  
  def get_VG_for_PV(self, pv):
    return pv.get_vg()
  
  def __query_LVs(self):
    if LVS_HAS_MIRROR_OPTIONS:
      LVS_OPTION_STRING="lv_name,vg_name,stripes,stripesize,lv_attr,lv_uuid,devices,origin,snap_percent,seg_start,seg_size,vg_extent_size,lv_size,mirror_log"
    else:
      LVS_OPTION_STRING="lv_name,vg_name,stripes,stripesize,lv_attr,lv_uuid,devices,origin,snap_percent,seg_start,seg_size,vg_extent_size,lv_size"
    LV_NAME_IDX         = 0
    LV_VG_NAME_IDX      = 1
    LV_STRIPES_NUM_IDX  = 2
    LV_STRIPE_SIZE_IDX  = 3
    LV_ATTR_IDX         = 4
    LV_UUID_IDX         = 5
    LV_DEVICES_IDX      = 6
    LV_SNAP_ORIGIN_IDX  = 7
    LV_SNAP_PERCENT_IDX = 8
    LV_SEG_START_IDX    = 9
    LV_SEG_SIZE_IDX     = 10
    LV_EXTENT_SIZE_IDX  = 11
    LV_SIZE_IDX         = 12
    LV_MIRROR_LOG_IDX   = 13
    
    self.__reload_logical_volumes_paths()
    
    arglist = list()
    arglist.append(LVM_BIN_PATH)
    arglist.append("lvs")
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")    
    arglist.append("--nosuffix")
    arglist.append("--noheadings")
    arglist.append("--units")
    arglist.append("b")
    arglist.append("--separator")
    arglist.append("\";\"")
    arglist.append("-o")
    arglist.append(LVS_OPTION_STRING)
    if LVS_HAS_ALL_OPTION:
      arglist.append("--all")
    result_string = execWithCapture(LVM_BIN_PATH, arglist)
    lines = result_string.splitlines()
    for line in lines:
      line = line.strip()
      words = line.split(';')
      vgname = words[LV_VG_NAME_IDX].strip()
      attrs = words[LV_ATTR_IDX].strip()
      uuid = words[LV_UUID_IDX].strip()
      extent_size = int(words[LV_EXTENT_SIZE_IDX])
      seg_start = int(words[LV_SEG_START_IDX]) / extent_size
      lv_size = int(words[LV_SIZE_IDX]) / extent_size
      seg_size = int(words[LV_SEG_SIZE_IDX]) / extent_size
      devices = words[LV_DEVICES_IDX]
      if LVS_HAS_MIRROR_OPTIONS:
        mirror_log = words[LV_MIRROR_LOG_IDX].strip()
      
      lvname = words[LV_NAME_IDX].strip()
      # remove [] if there (used to mark hidden lvs)
      lvname = lvname.lstrip('[')
      lvname = lvname.rstrip(']')
      
      vg = self.__VGs[vgname]
      vg_lvs = vg.get_lvs()
      lv = None
      if lvname not in vg_lvs:
        lv = LogicalVolume(lvname, self.__get_logical_volume_path(lvname, vg.get_name()), True, attrs, uuid)
        lv.set_extent_count(lv_size, lv_size)
        vg.add_lv(lv)
      lv = vg_lvs[lvname]
      
      segment = None
      devs = devices.split(',')
      if attrs[0] == 'm' or attrs[0] == 'M':
        # mirrored LV
        lv.set_mirror_log(mirror_log) # tmp, will get replaced with real one at __link_mirrors()
        segment = MirroredSegment(seg_start, seg_size)
        images = devs
        for image_name in images:
          idx = image_name.find('(')
          image_lv = LogicalVolume(image_name[:idx], None, True, None, None) # tmp, will get replaced with real one at __link_mirrors()
          segment.add_image(image_lv)
      elif len(devs) == 1:
        # linear segment
        segment = LinearSegment(seg_start, seg_size)
        idx = devs[0].find('(')
        pvpath = devs[0][:idx]
        ph_ext_beg = int(devs[0][idx+1:len(devs[0])-1])
        pv = None
        for pv_t in self.__PVs:
          if pv_t.get_path() == pvpath:
            pv = pv_t
            break
        extent_block = ExtentBlock(pv, lv, ph_ext_beg, seg_size)
        segment.set_extent_block(extent_block)
      else:
        # striped segment
        lv.set_stripes_num(int(words[LV_STRIPES_NUM_IDX]))
        stripe_size = int(words[LV_STRIPE_SIZE_IDX])
        segment = StripedSegment(stripe_size, seg_start, seg_size)
        stripe_id = 0
        for stripe in devs:
          idx = stripe.find('(')
          pvpath = stripe[:idx]
          ph_ext_beg = int(stripe[idx+1:len(stripe)-1])
          pv = None
          for pv_t in self.__PVs:
            if pv_t.get_path() == pvpath:
              pv = pv_t
              break
          if pv != None:
            extent_block = ExtentBlock(pv, lv, ph_ext_beg, seg_size/len(devs))
            segment.add_stripe(stripe_id, extent_block)
            stripe_id = stripe_id + 1
      
      lv.add_segment(segment)
      
      origin = words[LV_SNAP_ORIGIN_IDX].strip()
      if origin != '':
        # snapshot
        usage = float(0)
        if (words[LV_SNAP_PERCENT_IDX] != "" ):
          usage = float(words[LV_SNAP_PERCENT_IDX].strip())
        lv.set_snapshot_info(origin, usage) # set name for now, real LV will get set at __link_snapshots()
      
    # all LVs created  
  
  def __link_snapshots(self):
    for vgname in self.__VGs:
      vg = self.__VGs[vgname]
      snapshots = []
      lv_dict = vg.get_lvs()
      for lv in lv_dict.values():
        if lv.is_snapshot():
          snapshots.append(lv)
      for snap in snapshots:
        # find origin
        origin_name = snap.get_snapshot_info()[0]
        origin = lv_dict[origin_name]
        snap.set_snapshot_info(origin, snap.get_snapshot_info()[1]) # real object as origin
        origin.add_snapshot(snap)
    
  def __link_mirrors(self):
    for vgname in self.__VGs:
      vg = self.__VGs[vgname]
      lv_names = list(vg.get_lvs().keys())[:]
      for lvname in lv_names:
        if lvname in vg.get_lvs():
          lv = vg.get_lvs()[lvname]
          if lv.is_mirrored():
            # replace tmp lvs with real one
            # log
            #log_lv = vg.get_lvs()[lv.get_mirror_log()]
            #vg.get_lvs().pop(log_lv.get_name()) # remove log_lv from vg
            #lv.set_mirror_log(log_lv)
            mlog = lv.get_mirror_log()
            if mlog:
                log_lv = vg.get_lvs()[mlog]
                vg.get_lvs().pop(log_lv.get_name()) # remove log_lv from vg
                lv.set_mirror_log(log_lv)
            # images
            segment = lv.get_segments()[0]
            images_tmp = segment.get_images()[:] # copy
            segment.clear_images()
            for image_lv_tmp in images_tmp:
              # get real LV
              image_lv_real = vg.get_lvs()[image_lv_tmp.get_name()]
              # remove image_lv_real from vg
              vg.get_lvs().pop(image_lv_real.get_name())
              # rename it to mirror_name
              image_lv_real.set_name(lvname)
              # add it to the segment
              segment.add_image(image_lv_real)
    
  
  def __add_unused_space(self):
    #Now check if there is free space in Volume Groups
    #If there is free space, add an LV marked as 'unused' for that available space
    for vg in self.__VGs.values():
      if vg.get_extent_total_used_free()[2] == 0:
        continue
      lv_unused = LogicalVolume(UNUSED_SPACE, None, False, None, None)
      lv_unused.set_extent_count(vg.get_extent_total_used_free()[2], vg.get_extent_total_used_free()[2])
      vg.add_lv(lv_unused)
      segment_offset = 0
      # map unused extents on PVs to lv_unused
      for pv in vg.get_pvs().values():
        ext_total, ext_used, ext_free = pv.get_extent_total_used_free()
        if ext_free == 0:
          continue
        if len(pv.get_extent_blocks()) == 0:
          # nothing on PV
          segment = UnusedSegment(segment_offset, ext_free)
          segment_offset = segment_offset + ext_free
          extent = ExtentBlock(pv, lv_unused, 0, ext_free)
          segment.set_extent_block(extent)
          lv_unused.add_segment(segment)
          continue
        # fill in gaps
        ext_list = pv.get_extent_blocks()
        start1, size1 = 0, 0
        i = 0
        while i < len(ext_list):
          start2, size2 = ext_list[i].get_start_size()
          if (start1 + size1) == start2:
            start1, size1 = start2, size2
          else:
            # add extent block
            start_new = start1 + size1
            size_new = start2 - start_new
            segment = UnusedSegment(segment_offset, size_new)
            segment_offset = segment_offset + size_new
            extent = ExtentBlock(pv, lv_unused, start_new, size_new)
            segment.set_extent_block(extent)
            lv_unused.add_segment(segment)
            start1, size1 = ext_list[i].get_start_size()
          i = i + 1
        # add last one
        ext_list = pv.get_extent_blocks()
        last_ext = ext_list[len(ext_list) - 1]
        start_new = last_ext.get_start_size()[0] + last_ext.get_start_size()[1]
        size_new = ext_total - start_new
        if size_new != 0:
          segment = UnusedSegment(segment_offset, size_new)
          segment_offset = segment_offset + size_new
          extent = ExtentBlock(pv, lv_unused, start_new, size_new)
          segment.set_extent_block(extent)
          lv_unused.add_segment(segment)
    
  
  def pvmove_in_progress(self):
    LVS_OPTION_STRING="move_pv"
    arglist = list()
    arglist.append(LVM_BIN_PATH)
    arglist.append("lvs")
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")
    arglist.append("--noheadings")
    arglist.append("-o")
    arglist.append('move_pv')
    if LVS_HAS_ALL_OPTION:
      arglist.append("--all")
    
    result_string = execWithCapture(LVM_BIN_PATH, arglist)
    lines = result_string.splitlines()
    for line in lines:
      if line.strip() != '':
        return True
    return False
  
  def get_logical_volume_path(self, lvname, vgname):
    self.__reload_logical_volumes_paths()
    return self.__get_logical_volume_path(lvname, vgname)
  def __get_logical_volume_path(self, lvname, vgname):
    vgname = vgname.strip()
    lvname = lvname.strip()
    return self.__lvs_paths[vgname + '`' + lvname]
  def __reload_logical_volumes_paths(self):
    self.__lvs_paths = {}
    arglist = [LVDISPLAY_BIN_PATH] #lvs does not give path info
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")
    arglist.append('-c')
    if LVS_HAS_ALL_OPTION:
      arglist.append('-a')
    result_string = execWithCapture(LVDISPLAY_BIN_PATH,arglist)
    lines = result_string.splitlines()
    for line in lines:
      words = line.strip().split(":")
      vgname = words[LV_VGNAME_COL].strip()
      lvpath = words[LV_PATH_COL].strip()
      last_slash_index = lvpath.rfind("/") + 1
      lvname = lvpath[last_slash_index:]
      self.__lvs_paths[vgname + '`' + lvname] = lvpath
  
  def partition_UV(self, pv):
    if pv.needsFormat():
      try:
        (devname, seg) = pv.getPartition()
        fdisk_devname = None
        fdisk_devnames = self.__block_device_model.getDevices().keys()
        if devname in fdisk_devnames:
          fdisk_devname = devname
        else:
          # if pv has multipath info, devname doesn't have to be known to BlockDeviceModel
          # so find device it does :)
          multipath_object = Multipath()
          multipath_data = Multipath.get_multipath_data()
          # devname should be a multipath access point
          for path in multipath_data[devname]:
            if path in fdisk_devnames:
              fdisk_devname = path
        part = Partition(seg.beg, seg.end, ID_LINUX_LVM, None, False, seg.sectorSize)
        part_num = self.__block_device_model.add(fdisk_devname, part)
        self.__block_device_model.saveTable(fdisk_devname)
        new_part = self.__block_device_model.getPartition(fdisk_devname, part_num)
        pv.setPartition((devname, new_part))
      except BlockDeviceErr:
        self.__block_device_model.reload()
        raise CommandError('FATAL', AUTOPARTITION_FAILURE % devname)
      except AttributeError:
        self.__block_device_model.reload()
        raise CommandError('FATAL', AUTOPARTITION_FAILURE % devname)

    return pv.get_path()
  
  def __set_VGs_props(self):
    arglist = [LVM_BIN_PATH]
    arglist.append("vgs")
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")
    arglist.append("--nosuffix")
    arglist.append("--noheadings")
    #arglist.append("--units")
    #arglist.append("g")
    arglist.append("--separator")
    arglist.append(",")
    arglist.append("-o")
    arglist.append(VGS_OPTION_STRING)
    vgs_output = execWithCapture(LVM_BIN_PATH,arglist)
    for vg in self.__VGs.values():
      vg.set_properties(self.__get_data_for_VG(vg, vgs_output))
  def __get_data_for_VG(self, vg, vgs_output):
    lines = vgs_output.splitlines()
    for line in lines:
      words = line.strip().split(",")
      if words[VG_NAME_IDX] == vg.get_name():
        break
    
    text_list = list()
    text_list.append(VG_NAME)
    text_list.append(words[VG_NAME_IDX])
    
    text_list.append(_("Clustered:   "))
    if vg.clustered():
      text_list.append(_("True"))
    else:
      text_list.append(_("False"))
    
    text_list.append(VG_SYSID)
    text_list.append(words[VG_SYSID_IDX])
    text_list.append(VG_FMT)
    text_list.append(words[VG_FMT_IDX])
    text_list.append(VG_ATTR)
    text_list.append(words[VG_ATTR_IDX])
    text_list.append(VG_SIZE)
    text_list.append(words[VG_SIZE_IDX])
    
    text_list.append(VG_FREE)
    text_list.append(words[VG_FREE_IDX])
    
    text_list.append(VG_EXTENT_COUNT)
    text_list.append(words[VG_EXTENT_COUNT_IDX])
    
    text_list.append(VG_FREE_COUNT)
    text_list.append(words[VG_FREE_COUNT_IDX])
    
    text_list.append(VG_EXTENT_SIZE)
    text_list.append(words[VG_EXTENT_SIZE_IDX])
    
    text_list.append(MAX_PV)
    #lvs reports 0 for sys max
    if words[MAX_PV_IDX] == "0":
      text_list.append("256")
    else:
      text_list.append(words[MAX_PV_IDX])
    
    text_list.append(PV_COUNT)
    text_list.append(words[PV_COUNT_IDX])
    
    text_list.append(MAX_LV)
    if words[MAX_LV_IDX] == "0":
      text_list.append("256")
    else:
      text_list.append(words[MAX_LV_IDX])
    
    text_list.append(LV_COUNT)
    text_list.append(words[LV_COUNT_IDX])
    
    text_list.append(VG_UUID)
    text_list.append(words[VG_UUID_IDX])
    
    return text_list
  
  def __set_LVs_props(self):
    for vg in self.__VGs.values():
      for lv in vg.get_lvs().values():
        if lv.is_used():
          lv.set_properties(self.__get_data_for_LV(lv))
  def __get_data_for_LV(self, lv):
    text_list = list()
    
    text_list.append(LV_NAME)
    text_list.append(lv.get_name())
    if lv.is_mirrored():
      text_list.append(_("Number of mirror images:"))
      text_list.append(str(len(lv.get_segments()[0].get_images())-1))
    if lv.has_snapshots():
      text_list.append(_("Snapshots:"))
      string = lv.get_snapshots()[0].get_name()
      for snap in lv.get_snapshots()[1:]:
        string = string + ', ' + snap.get_name()
      text_list.append(string)
    if lv.is_snapshot():
      text_list.append(_("Snapshot origin:"))
      text_list.append(lv.get_snapshot_info()[0].get_name())
    text_list.append(VG_NAME)
    text_list.append(lv.get_vg().get_name())
    text_list.append(LV_SIZE)
    text_list.append(lv.get_size_total_string())
    if lv.is_snapshot():
      text_list.append(_("Snapshot usage:"))
      text_list.append(str(lv.get_snapshot_info()[1]) + '%')
    text_list.append(LV_SEG_COUNT)
    text_list.append(str(len(lv.get_segments())))
    
    segment0 = lv.get_segments()[0]
    if segment0.get_type() == STRIPED_SEGMENT_ID:
      # striped
      text_list.append(LV_STRIPE_COUNT)
      text_list.append(str(len(segment0.get_stripes().values())))
      text_list.append(LV_STRIPE_SIZE)
      text_list.append(str(segment0.get_stripe_size()/1024) + KILO_SUFFIX)
    
    text_list.append(LV_ATTR)
    text_list.append(lv.get_attr())
    text_list.append(LV_UUID)
    text_list.append(lv.get_uuid())
    
    mount_point = self.getMountPoint(lv.get_path())
    if mount_point == None:
      mount_point = UNMOUNTED
    else:
      if mount_point == '/':
        mount_point = _("/   Root Filesystem")
    text_list.append(UV_MOUNT_POINT)
    text_list.append(mount_point)
    
    mountpoint_at_reboot = Fstab.get_mountpoint(lv.get_path())
    if mountpoint_at_reboot == '/':
      mountpoint_at_reboot = _("/   Root Filesystem")
    text_list.append(UV_MOUNTPOINT_AT_REBOOT)
    text_list.append(str(mountpoint_at_reboot))
    text_list.append(UV_FILESYSTEM)
    text_list.append(self.__getFS(lv.get_path()))
    
    return text_list
  
  def __set_PVs_props(self):
    arglist = list()
    arglist.append(LVM_BIN_PATH)
    arglist.append("pvs")
    arglist.append("--config")
    arglist.append("'log{command_names=0}'")
    arglist.append("--noheadings")
    arglist.append("--separator")
    arglist.append(",")
    arglist.append("-o")
    arglist.append(PVS_OPTION_STRING)
    pvs_output = execWithCapture(LVM_BIN_PATH,arglist)
    for pv in self.__PVs:
      prop = []
      for path in pv.get_paths():
        wwid = self.__get_wwid(path)
        if wwid != None and wwid != "":
          prop.append("SCSI WWID: ")
          prop.append(wwid)
        
      pv.set_properties(prop)
      pv.set_properties(self.__get_data_for_PV(pv, pvs_output))

  def __get_wwid(self, device):
    try:
      output = execWithCapture(SCSIID_BIN_PATH, ["--page=0x83", "--whitelisted", "--device=" + device]);
      return output
    except Exception:
      return None    
      
  def __get_data_for_PV(self, pv, pvs_output):
    # anything that is in, place to the end
    end = pv.get_properties()
    text_list = list()
    
    if pv.get_type() == UNINITIALIZED_TYPE:
      # size
      size_string = pv.get_size_total_string()
      text_list.append(UV_SIZE)
      text_list.append(size_string)
      # partition type
      part = pv.getPartition()[1]
      partition_type = PARTITION_IDs[part.id]
      if part.id != ID_EMPTY and part.id != ID_UNKNOWN:
        partition_type = partition_type + ' (' + str(hex(part.id)) + ')'
      text_list.append(UV_PARTITION_TYPE)
      text_list.append(partition_type)
      # mount point
      mountPoints = []
      for path in pv.get_paths():
        mountPoint = self.getMountPoint(path)
        if mountPoint != None:
          if mountPoint == '/':
            mountPoint = _("/   Root Filesystem")
          mountPoints.append(mountPoint)
      if len(mountPoints) == 0:
        mountPoints = UNMOUNTED
      else:
        mount_list = mountPoints
        mountPoints = mount_list[0]
        for mountPoint in mount_list[1:]:
          mountPoints = mountPoints + ', ' + mountPoint
      text_list.append(UV_MOUNT_POINT)
      text_list.append(mountPoints)
      fstabMountPoints = []
      for path in pv.get_paths():
        mountPoint = Fstab.get_mountpoint(path)
        if mountPoint != None:
          if mountPoint == '/':
            mountPoint = _("/   Root Filesystem")
          fstabMountPoints.append(mountPoint)
      if len(fstabMountPoints) == 0:
        fstabMountPoints = _("None")
      else:
        mount_list = fstabMountPoints
        fstabMountPoints = mount_list[0]
        for mountPoint in mount_list[1:]:
          fstabMountPoints = fstabMountPoints + ', ' + mountPoint
      text_list.append(UV_MOUNTPOINT_AT_REBOOT)
      text_list.append(fstabMountPoints)
      # filesystem
      text_list.append(UV_FILESYSTEM)
      text_list.append(self.__getFS(path))
    else: # UNALLOCATED_TYPE || PHYS_TYPE
      lines = pvs_output.splitlines()
      for line in lines:
        words = line.strip().split(',')
        if words[PV_NAME_IDX] in pv.get_paths():
          break
      text_list.append(PV_NAME)
      text_list.append(words[PV_NAME_IDX])
      if words[PV_VG_NAME_IDX] == "":
        text_list.append(VG_NAME)
        text_list.append("---")
      else:
        text_list.append(VG_NAME)
        text_list.append(words[PV_VG_NAME_IDX])
      text_list.append(PV_SIZE)
      text_list.append(words[PV_SIZE_IDX])
      text_list.append(PV_USED)
      text_list.append(words[PV_USED_IDX])
      text_list.append(PV_FREE)
      text_list.append(words[PV_FREE_IDX])
      text_list.append(PV_PE_COUNT)
      text_list.append(words[PV_PE_COUNT_IDX])
      text_list.append(PV_PE_ALLOC_COUNT)
      text_list.append(words[PV_PE_ALLOC_COUNT_IDX])
      text_list.append(PV_ATTR)
      text_list.append(words[PV_ATTR_IDX])
      text_list.append(PV_UUID)
      text_list.append(words[PV_UUID_IDX])
      
    # append old props
    for prop in end:
      text_list.append(prop)
    
    try:
      # add scsi dev info
      device = pv.getDevnames()[0]
      devname = pv.extract_name(device)
      SCSI_ID_BIN = '/sbin/scsi_id'
      args = [SCSI_ID_BIN, '-g', '-i', '-u', '-s', '/block/' + devname]
      o, e, s = execWithCaptureErrorStatus(SCSI_ID_BIN, args)
      if s == 0:
        scsi_addr, scsi_id = o.strip().split()
        scsi_addr = scsi_addr.strip(':')
        text_list.append(_("SCSI Address:  "))
        text_list.append(scsi_addr)
        text_list.append(_("SCSI ID:  "))
        text_list.append(scsi_id)
    except:
      pass
    
    return text_list
  
  def __getFS(self, path):
    path_list = list()
    for pv in self.__PVs:
      if pv.get_path() == path:
        path_list.append(pv)
    if len(path_list) == 0:
      # nothing on a drive, maybe a LV, or a loopback device
      pass
    elif len(path_list) == 1:
      if path_list[0].getPartition() == None:
        # nothing on a drive, maybe a LV, or a loopback device
        pass
      # either a partition, a drive or free space
      if path_list[0].getPartition()[1].id == ID_EMPTY:
        # drive or free space
        # fixme - drive could have a filesystem on it
        return NO_FILESYSTEM
      else: 
        # partition
        pass
    else:
      # free space
      return NO_FILESYSTEM
    
    
    filesys = Filesystem.get_fs(path)
    if filesys.name == Filesystem.get_filesystems()[0].name:
      return NO_FILESYSTEM
    else:
      return filesys.name
  
  def getMountPoint(self, path):
    # follow links
    paths = [path]
    if follow_links_to_target(path, paths) == None:
      return None
    
    result = execWithCapture('/bin/cat', ['/bin/cat', '/proc/mounts', '/etc/mtab'])
    lines = result.splitlines()
    for line in lines:
      words = line.split()
      possible_path = words[0]
      if possible_path in paths:
        return words[1]
      if follow_links_to_target(possible_path, []) in paths:
        return words[1]
    return None
  
  def is_mirroring_supported(self):
    return LVS_HAS_MIRROR_OPTIONS


  
def lvm_conf_get_locking_type():
  conf = open('/etc/lvm/lvm.conf')
  
  lines = conf.readlines()
  for line in lines:
    words = line.split()
    if len(words) < 3:
      continue
    if words[0] == 'locking_type':
      if words[1] == '=':
        locking_type = int(words[2])
        return locking_type
  return int(1)
