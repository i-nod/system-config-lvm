import os
import string
from CommandError import CommandError
from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus, execWithCaptureProgress, execWithCaptureErrorStatusProgress, execWithCaptureStatusProgress

from lvmui_constants import *

import gettext
_ = gettext.gettext


class CommandHandler:
  
  def __init__(self):
    pass
  
  def new_lv(self, cmd_args_dict, pvlist=[]):
    #first set up lvcreate args
    arglist = list()
    arglist.append(LVCREATE_BIN_PATH)
    arglist.append("-n")
    lvname = cmd_args_dict[NEW_LV_NAME_ARG]
    arglist.append(lvname)
    if cmd_args_dict[NEW_LV_UNIT_ARG] == EXTENT_IDX:
      arglist.append("-l")
      arglist.append(str(cmd_args_dict[NEW_LV_SIZE_ARG]))
    else:
      arglist.append("-L")
      if cmd_args_dict[NEW_LV_UNIT_ARG] == KILOBYTE_IDX:
        arglist.append(str(cmd_args_dict[NEW_LV_SIZE_ARG]) + "k")
      elif cmd_args_dict[NEW_LV_UNIT_ARG] == MEGABYTE_IDX:
        arglist.append(str(cmd_args_dict[NEW_LV_SIZE_ARG]) + "m")
      elif cmd_args_dict[NEW_LV_UNIT_ARG] == GIGABYTE_IDX:
        arglist.append(str(cmd_args_dict[NEW_LV_SIZE_ARG]) + "g")
    
    if cmd_args_dict[NEW_LV_SNAPSHOT]:
      arglist.append("-s")
      arglist.append(cmd_args_dict[NEW_LV_SNAPSHOT_ORIGIN])
    else:
      if cmd_args_dict[NEW_LV_MIRRORING]:
        arglist.append("-m1")
      if cmd_args_dict[NEW_LV_IS_STRIPED_ARG] == True:
        arglist.append("-i")
        arglist.append(str(cmd_args_dict[NEW_LV_NUM_STRIPES_ARG]))
        arglist.append("-I")
        arglist.append(str(cmd_args_dict[NEW_LV_STRIPE_SIZE_ARG]))
      vgname = cmd_args_dict[NEW_LV_VGNAME_ARG]
      arglist.append(vgname)
    
    for pv in pvlist:
      arglist.append(pv.get_path())
    
    cmd_str = ' '.join(arglist)
    result_string,err,res = execWithCaptureErrorStatusProgress(LVCREATE_BIN_PATH, arglist,
                                                               _("Creating Logical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvcreate",cmd_str,err))
  
  def reduce_lv(self, lvpath, new_size_extents, test=False): 
    cmd_args = list()
    cmd_args.append(LVREDUCE_BIN_PATH)
    cmd_args.append("--config")
    cmd_args.append("'log{command_names=0}'")    
    if test:
      cmd_args.append('--test')
    cmd_args.append('-f')
    cmd_args.append('-l')
    cmd_args.append(str(new_size_extents))
    cmd_args.append(lvpath)
    cmdstr = ' '.join(cmd_args)
    
    if test:
      out,err,res = execWithCaptureErrorStatus(LVREDUCE_BIN_PATH, cmd_args)
      return (res == 0)
    out,err,res = execWithCaptureErrorStatusProgress(LVREDUCE_BIN_PATH, cmd_args,
                                                     _("Resizing Logical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvresize",cmdstr,err))
  
  def extend_lv(self, lvpath, new_size_extents, test=False): 
    cmd_args = list()
    cmd_args.append(LVEXTEND_BIN_PATH)
    cmd_args.append("--config")
    cmd_args.append("'log{command_names=0}'")    
    if test:
      cmd_args.append('--test')
    cmd_args.append('-l')
    cmd_args.append(str(new_size_extents))
    cmd_args.append(lvpath)
    cmdstr = ' '.join(cmd_args)
    if test:
      out,err,res = execWithCaptureErrorStatus(LVEXTEND_BIN_PATH, cmd_args)
      return (res == 0)
    out,err,res = execWithCaptureErrorStatusProgress(LVEXTEND_BIN_PATH, cmd_args,
                                                     _("Resizing Logical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvresize",cmdstr,err))
  
  def activate_lv(self, lvpath):
    cmd_args = list()
    cmd_args.append(LVCHANGE_BIN_PATH)
    cmd_args.append("--config")
    cmd_args.append("'log{command_names=0}'")    
    cmd_args.append('-ay')
    cmd_args.append(lvpath)
    cmdstr = ' '.join(cmd_args)
    out,err,res = execWithCaptureErrorStatus(LVCHANGE_BIN_PATH, cmd_args)
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvchange",cmdstr,err))
  
  def deactivate_lv(self, lvpath):
    cmd_args = list()
    cmd_args.append(LVCHANGE_BIN_PATH)
    cmd_args.append("--config")
    cmd_args.append("'log{command_names=0}'")    
    cmd_args.append('-an')
    cmd_args.append(lvpath)
    cmdstr = ' '.join(cmd_args)
    out,err,res = execWithCaptureErrorStatus(LVCHANGE_BIN_PATH, cmd_args)
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvchange",cmdstr,err))
  
  def add_mirroring(self, lvpath, pvlist=[]):
    cmd_args = list()
    cmd_args.append(LVCONVERT_BIN_PATH)
    cmd_args.append("--config")
    cmd_args.append("'log{command_names=0}'")    
    cmd_args.append('-m1')
    cmd_args.append(lvpath)
    for pv in pvlist:
      cmd_args.append(pv.get_path())
    cmdstr = ' '.join(cmd_args)
    out,err,res = execWithCaptureErrorStatusProgress(LVCONVERT_BIN_PATH, cmd_args,
                                                     _("Adding Mirror to Logical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvconvert",cmdstr,err))
  
  def remove_mirroring(self, lvpath):
    cmd_args = list()
    cmd_args.append(LVCONVERT_BIN_PATH)
    cmd_args.append("--config")
    cmd_args.append("'log{command_names=0}'")    
    cmd_args.append('-m0')
    cmd_args.append(lvpath)
    cmdstr = ' '.join(cmd_args)
    out,err,res = execWithCaptureErrorStatusProgress(LVCONVERT_BIN_PATH, cmd_args,
                                                     _("Removing Mirror from Logical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvconvert",cmdstr,err))
  
  def mount(self, dev_path, mnt_point, fstype): 
    cmd_args = list()
    cmd_args.append("/bin/mount")
    cmd_args.append('-t')
    cmd_args.append(fstype)
    cmd_args.append(dev_path)
    cmd_args.append(mnt_point)
    cmdstr = ' '.join(cmd_args)
    out,err,res = execWithCaptureErrorStatus("/bin/mount",cmd_args)
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("mount",cmdstr,err))
  
  def initialize_entity(self, ent):
    entity = ent.strip()
    command_args = list()
    command_args.append(PVCREATE_BIN_PATH)
    command_args.append("-M")
    command_args.append("2")
    command_args.append(entity)
    commandstring = ' '.join(command_args)
    out,err,res = execWithCaptureErrorStatusProgress(PVCREATE_BIN_PATH,command_args,
                                                     _("Initializing Physical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("pvcreate",commandstring,err))

  def add_unalloc_to_vg(self, pv, vg):
    args = list()
    args.append(VGEXTEND_BIN_PATH)
    args.append("--config")
    args.append("'log{command_names=0}'")    
    args.append(vg.strip())
    args.append(pv.strip())
    cmdstr = ' '.join(args)
    out,err,res = execWithCaptureErrorStatusProgress(VGEXTEND_BIN_PATH, args, 
                                                     _("Adding Physical Volume to Volume Group"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("vgextend",cmdstr,err))

  def create_new_vg(self, name, max_phys, max_log, extent_size, is_unit_megs,
                    pv, clustered=False):

    if is_unit_megs:
      units_arg = 'm'
    else:
      units_arg = 'k'

    size_arg = extent_size + units_arg
    
    args = list()
    args.append(VGCREATE_BIN_PATH)
    args.append("-M2")
    args.append("-l")
    args.append(max_log)
    args.append("-p")
    args.append(max_phys)
    args.append("-s")
    args.append(size_arg)
    #new vgcreate doesn't support cluster
    #args.append('-c')
    #if clustered:
    #  args.append('y')
    #else:
    #  args.append('n')
    args.append(name.strip())
    args.append(pv.strip())
    cmdstr = ' '.join(args)
    #print(VGCREATE_BIN_PATH,args)
    out,err,res = execWithCaptureErrorStatusProgress(VGCREATE_BIN_PATH, args, 
                                                     _("Creating Volume Group"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("vgcreate",cmdstr,err))

  def remove_vg(self, vgname):
    args = list()
    args.append(VGCHANGE_BIN_PATH)
    args.append("--config")
    args.append("'log{command_names=0}'")    
    args.append("-a")
    args.append("n")
    args.append(vgname.strip())
    cmdstr = ' '.join(args)
    out,err,res = execWithCaptureErrorStatus(VGCHANGE_BIN_PATH,args)
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("vgchange",cmdstr,err))
      return

    commandstring = VGREMOVE_BIN_PATH + " " + vgname
    args_list = list()
    args_list.append(VGREMOVE_BIN_PATH)
    args_list.append("--config")
    args_list.append("'log{command_names=0}'")    
    args_list.append(vgname)
    cmdstring = ' '.join(args)
    outs,errs,result = execWithCaptureErrorStatusProgress(VGREMOVE_BIN_PATH,args_list,
                                                          _("Removing Volume Group"))
    if result != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("vgremove",cmdstring,errs))

  def remove_pv(self, pvname):
    args = list()
    args.append(PVREMOVE_BIN_PATH)
    args.append("--config")
    args.append("'log{command_names=0}'")    
    args.append(pvname.strip())
    cmdstr = ' '.join(args)
    out,err,res = execWithCaptureErrorStatusProgress(PVREMOVE_BIN_PATH,args,
                                                     _("Removing Physical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("pvremove",cmdstr,err))

  def remove_lv(self, lvpath):
    if self.is_snapshot(lvpath) == False:
      self.deactivate_lv(lvpath)
      
    try:
      args = list()
      args.append(LVREMOVE_BIN_PATH)
      args.append("--config")
      args.append("'log{command_names=0}'")    
      args.append("--force")
      args.append(lvpath.strip())
      cmdstr = ' '.join(args)
      out,err,res = execWithCaptureErrorStatusProgress(LVREMOVE_BIN_PATH,args,
                                                       _("Removing Logical Volume"))
      if res != 0:
        raise CommandError('FATAL', COMMAND_FAILURE % ("lvremove",cmdstr,err))
    except CommandError as e:
      self.activate_lv(lvpath)
      raise e
  
  def rename_lv(self, vgname, lvname_old, lvname_new):
    args = list()
    args.append(LVRENAME_BIN_PATH)
    args.append("--config")
    args.append("'log{command_names=0}'")    
    args.append(vgname)
    args.append(lvname_old)
    args.append(lvname_new)
    cmdstr = ' '.join(args)
    out,err,res = execWithCaptureErrorStatusProgress(LVRENAME_BIN_PATH,args,
                                                     _("Renaming Logical Volume"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("lvrename",cmdstr,err))
  
  def unmount(self, mountpoint):
    args = ['/bin/umount']
    args.append(mountpoint)
    cmdstr = ' '.join(args)
    out,err,res = execWithCaptureErrorStatus("/bin/umount", args)
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("umount",cmdstr, err))
    # unmount all with mountpoint
    while res == 0:
      out,err,res = execWithCaptureErrorStatus("/bin/umount", args)
  
  def reduce_vg(self, vg, pv):
    args = list()
    args.append(VGREDUCE_BIN_PATH)
    args.append("--config")
    args.append("'log{command_names=0}'")    
    args.append(vg.strip())
    args.append(pv.strip())
    cmdstr = ' '.join(args)
    out,err,res = execWithCaptureErrorStatusProgress(VGREDUCE_BIN_PATH,args,
                                                     _("Removing Physical Volume from Volume Group"))
    if res != 0:
      raise CommandError('FATAL', COMMAND_FAILURE % ("vgreduce",cmdstr,err))

  # data = [pv to migrate to, policy (0 - inherit, 1 - normal, 2 - contiguous, 3 - anywhere), lv_path to migrate from]
  # extents_from = [(start, size), ...]
  def move_pv(self, pv, extents_from, data, background=False):
    args = list()
    args.append(PVMOVE_BIN_PATH)
    args.append("--config")
    args.append("'log{command_names=0}'")        
    # policy
    if data[1] != None:
      if data[1] == 0:
        args.append('--alloc inherit')
      elif data[1] == 1:
        args.append('--alloc normal')
      elif data[1] == 2:
        args.append('--alloc contiguous')
      elif data[1] == 3:
        args.append('--alloc anywhere')
    # lv to migrate from
    if data[2] != None:
      args.append('--name ' + data[2])
    # pv to migrate from
    pv_from = pv.strip()
    for (start, size) in extents_from:
      pv_from = pv_from + ':' + str(start) + '-' + str(start + size - 1)
    args.append(pv_from)
    # pv to migrate to
    if data[0] != None:
      args.append(data[0])
    if background:
      args.append('--background')
      out, err, res = execWithCaptureErrorStatus(PVMOVE_BIN_PATH, args)
    else:
      out, err, res = execWithCaptureErrorStatusProgress(PVMOVE_BIN_PATH, args,
                                                         _("Migrating Extents"))
    if res != 0:
      cmdstr = ' '.join(args)
      raise CommandError('FATAL', COMMAND_FAILURE % ("pvmove",cmdstr, err))
  
  def complete_pvmove(self, background=False):
    args = [PVMOVE_BIN_PATH]
    args.append("--config")
    args.append("'log{command_names=0}'")
    if background:
      args.append('--background')
      out, err, res = execWithCaptureErrorStatus(PVMOVE_BIN_PATH, args)
    else:
      out, err, res = execWithCaptureErrorStatusProgress(PVMOVE_BIN_PATH, args,
                                                         _("Completing Extent Migration"))
    if res != 0:
      cmdstr = ' '.join(args)
      raise CommandError('FATAL', COMMAND_FAILURE % ("pvmove",cmdstr, err))
  
  def is_dm_mirror_loaded(self):
    arglist = list()
    arglist.append("/sbin/dmsetup")
    arglist.append("targets")
    result  = execWithCapture("/sbin/dmsetup", arglist)
    textlines = result.splitlines()
    for textline in textlines:
      text_words = textline.split()
      possible_target = text_words[0].strip()
      if possible_target == "mirror":
        return True
      
    return False
  
  def is_dm_mirror_loaded(self):
    arglist = list()
    arglist.append("/sbin/dmsetup")
    arglist.append("targets")
    result  = execWithCapture("/sbin/dmsetup", arglist)
    textlines = result.splitlines()
    for textline in textlines:
      text_words = textline.split()
      possible_target = text_words[0].strip()
      if possible_target == "mirror":
        return True
    return False
  
  def is_dm_snapshot_loaded(self):
    arglist = list()
    arglist.append("/sbin/dmsetup")
    arglist.append("targets")
    result  = execWithCapture("/sbin/dmsetup", arglist)
    textlines = result.splitlines()
    for textline in textlines:
      text_words = textline.split()
      possible_target = text_words[0].strip()
      if possible_target == "snapshot":
        return True
    return False
  
  def reread_partition_table(self, devpath):
    BLOCKDEV_BIN = '/sbin/blockdev'
    args = [BLOCKDEV_BIN, '--rereadpt', devpath]
    out, err, status = execWithCaptureErrorStatus(BLOCKDEV_BIN, args)
    if status != 0:
      return False
    execWithCaptureProgress('sleep', ['sleep', '1'], _('Rereading partition table'))
    return True
  
  def is_snapshot(self, lvpath):
    arglist = list()
    arglist = [LVM_BIN_PATH, 'lvs', '--config', "'log{command_names=0}'", "-o", "attr", "--noheadings", lvpath]

    out, err, status = execWithCaptureErrorStatus(LVM_BIN_PATH, arglist)
    
    if status != 0:
      return False
      
    if out.lstrip().startswith("s") == True:
      return True
    else:
      return False
