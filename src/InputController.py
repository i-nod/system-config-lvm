"""This class represents the primary controller interface
   for the LVM UI application.
"""


import string
import os
import re
import stat
import os.path
import locale
from lvm_model import lvm_model
from CommandHandler import CommandHandler
from lvmui_constants import *
from CommandError import CommandError
import Fstab
import Filesystem
from Segment import STRIPED_SEGMENT_ID
from ExtentBlock import ExtentBlock
from WaitMsg import WaitMsg

import PhysicalVolume

from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus
from utilities import follow_links_to_target


import gettext
_ = gettext.gettext

### gettext first, then import gtk (exception prints gettext "_") ###
try:
    #    import gtk
    #    import gtk.glade
    import gi
    gi.require_version('Pango', '1.0')
    gi.require_version('PangoCairo', '1.0')
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, PangoCairo, GObject

    import cairo
except RuntimeError as e:
    print(_("""
  Unable to initialize graphical environment. Most likely cause of failure
  is that the tool was not run using a graphical environment. Please either
  start your graphical user interface or set your DISPLAY variable.
                                                                                
  Caught exception: %s
""") % e)
    sys.exit(-1)
                                                                                

SIZE_COL = TYPE_COL
VOL_TYPE_COL = 3

UNALLOC_VOL = 0
UNINIT_VOL = 1

###TRANSLATOR: The string below is seen when adding a new Physical
###Volume to an existing Volume Group.
ADD_PV_TO_VG_LABEL=_("Select a Volume Group to add %s to:")

MEGA_MULTIPLIER = 1000000.0
GIGA_MULTIPLIER = 1000000000.0
KILO_MULTIPLIER = 1000.0

DEFAULT_STRIPE_SIZE_IDX = 4

MAX_PHYSICAL_VOLS = 256
MAX_LOGICAL_VOLS = 256
DEFAULT_EXTENT_SIZE = 4
DEFAULT_EXTENT_SIZE_MEG_IDX = 1
DEFAULT_EXTENT_SIZE_KILO_IDX = 2

NO_FILESYSTEM_FS = 0

ACCEPTABLE_STRIPE_SIZES = [4,8,16,32,64,128,256,512]

ACCEPTABLE_EXTENT_SIZES = ["2","4","8","16","32","64","128","256","512","1024"]

###TRANSLATOR: The two strings below refer to the name and type of
###available disk entities on the system. There are two types --
###The first is an 'unallocated physical volume' which is a disk or
###partition that has been initialized for use with LVM, by writing
###a special label onto the first block of the partition. The other type
###is an 'uninitialized entity', which is an available disk or partition
###that is NOT yet initialized to be used with LVM. Hope this helps give
###some context.
ENTITY_NAME=_("Name")
ENTITY_SIZE=_("Size")
ENTITY_TYPE=_("Entity Type")

UNALLOCATED_PV=_("Unallocated Physical Volume")
UNINIT_DE=_("Uninitialized Disk Entity") 
ADD_VG_LABEL=_("Select disk entities to add to the %s Volume Group:")

CANT_STRIPE_MESSAGE=_("A Volume Group must be made up of two or more Physical Volumes to support striping. This Volume Group does not meet that requirement.")

NON_UNIQUE_NAME=_("A Logical Volume with the name %s already exists in this Volume Group. Please choose a unique name.")

NON_UNIQUE_VG_NAME=_("A Volume Group with the name %s already exists. Please choose a unique name.")

MUST_PROVIDE_NAME=_("A Name must be provided for the new Logical Volume")

MUST_PROVIDE_VG_NAME=_("A Name must be provided for the new Volume Group")

BAD_MNT_POINT=_("The specified mount point, %s, does not exist. Do you wish to create it?")

BAD_MNT_CREATION=_("The creation of mount point %s unexpectedly failed.")

NOT_IMPLEMENTED=_("This capability is not yet implemented in this version")

EXCEEDED_MAX_LVS=_("The number of Logical Volumes in this Volume Group has reached its maximum limit.")

EXCEEDED_MAX_PVS=_("The number of Physical Volumes in this Volume Group has reached its maximum limit.")

EXCEEDING_MAX_PVS=_("At most %s Physical Volumes can be added to this Volume Group before the limit is reached.")

NOT_ENOUGH_SPACE_FOR_NEW_LV=_("Volume Group %s does not have enough space for new Logical Volumes. A possible solution would be to add an additional Physical Volume to the Volume Group.")

ALREADY_A_SNAPSHOT=_("A snapshot of a snapshot is not supported.")
CANNOT_SNAPSHOT_A_MIRROR=_("A snapshot of a mirrored Logical Volume is not supported.")

CANNOT_REMOVE_UNDER_SNAPSHOT=_("Logical volume %s has snapshot %s currently associated with it. Please remove the snapshot first.")
CANNOT_REMOVE_UNDER_SNAPSHOTS=_("Logical volume %s has snapshots: %s currently associated with it. Please remove snapshots first.")

TYPE_CONVERSION_ERROR=_("Undefined type conversion error in model factory. Unable to complete task.")

MOUNTED_WARNING=_("BIG WARNING: Logical Volume %s has an %s file system on it and is currently mounted on %s. Are you absolutely certain that you wish to discard the data on this mounted filesystem?")

UNMOUNT_PROMPT=_("Logical Volume %s is currently mounted on %s. In order to complete request, it has to be unmounted. Are you sure you want it unmounted?")



###TRANSLATOR: An extent below is an abstract unit of storage. The size
###of an extent is user-definable.
REMAINING_SPACE_VGNAME=_("Unused space on %s")
REMAINING_SPACE_MEGABYTES=_("%s megabytes")
REMAINING_SPACE_KILOBYTES=_("%s kilobytes")
REMAINING_SPACE_GIGABYTES=_("%s gigabytes")
REMAINING_SPACE_EXTENTS=_("%s extents")

REMAINING_SPACE_VG=_("Remaining free space in Volume Group:\n")
REMAINING_SPACE_AFTER=_("Remaining space for this Volume:\n")

EXTENTS=_("Extents")
GIGABYTES=_("Gigabytes")
MEGABYTES=_("Megabytes")
KILOBYTES=_("Kilobytes")

NUMBERS_ONLY=_("The %s should only contain number values")
NUMBERS_ONLY_MAX_PVS=_("The Maximum Physical Volumes field should contain only integer values between 1 and 256")
NUMBERS_ONLY_MAX_LVS=_("The Maximum Logical Volumes field should contain only integer values between 1 and 256")

CONFIRM_PVREMOVE=_("Are you quite certain that you wish to remove %s from Logical Volume Management?")

SOLO_PV_IN_VG=_("The Physical Volume named %s, that you wish to remove, has data from active Logical Volume(s) mapped to its extents. Because it is the only Physical Volume in the Volume Group, there is no place to move the data to. Recommended action is either to add a new Physical Volume before removing this one, or else remove the Logical Volumes that are associated with this Physical Volume.") 
CONFIRM_PV_VG_REMOVE=_("Are you quite certain that you wish to remove %s from the %s Volume Group?")
CONFIRM_VG_REMOVE=_("Removing Physical Volume %s from the Volume Group %s will leave the Volume group empty, and it will be removed as well. Do you wish to proceed?")
NOT_ENOUGH_SPACE_VG=_("Volume Group %s does not have enough space to move the data stored on %s. A possible solution would be to add an additional Physical Volume to the Volume Group.")
NO_DM_MIRROR=_("The dm-mirror module is either not loaded in your kernel, or your kernel does not support the dm-mirror target. If it is supported, try running \"modprobe dm-mirror\". Otherwise, operations that require moving data on Physical Extents are unavailable.")
NO_DM_SNAPSHOT=_("The dm-snapshot module is either not loaded in your kernel, or your kernel does not support the dm-snapshot target. If it is supported, try running \"modprobe dm-snapshot\". Otherwise, creation of snapshots is unavailable.")

CONFIRM_LV_REMOVE=_("Are you quite certain that you wish to remove logical volume %s?")
CONFIRM_LV_REMOVE_FILESYSTEM=_("Logical volume %s contains %s filesystem. All data on it will be lost! Are you quite certain that you wish to remove logical volume %s?")
CONFIRM_LV_REMOVE_MOUNTED=_("Logical volume %s contains data from directory %s. All data in it will be lost! Are you quite certain that you wish to remove logical volume %s?")


###########################################################
class InputController:
  def __init__(self, reset_tree_model, treeview, model_factory, glade_xml):
    self.reset_tree_model = reset_tree_model
    self.treeview = treeview
    self.model_factory = model_factory
    self.glade_xml = glade_xml
    
    self.command_handler = CommandHandler()
    self.section_list = list()
    self.section_type = UNSELECTABLE_TYPE
    
    self.setup_dialogs()
    
    # check if pvmove is in progress
    if self.model_factory.pvmove_in_progress():
        self.command_handler.complete_pvmove()
  
  def setup_dialogs(self):
    self.init_entity_button = self.glade_xml.get_object('uninit_button')
    self.init_entity_button.connect("clicked", self.on_init_entity)
    
    self.setup_new_vg_form()
    #self.setup_pv_rm_migrate()
    #self.setup_pv_rm()
    
    ###################
    ##This form adds an unallocated PV to a VG
    self.add_pv_to_vg_dlg = self.glade_xml.get_object('add_pv_to_vg_form')
    self.add_pv_to_vg_dlg.connect("delete_event",self.add_pv_to_vg_delete_event)
    self.add_pv_to_vg_button = self.glade_xml.get_object('add_pv_to_vg_button')
    self.add_pv_to_vg_button.connect("clicked",self.on_add_pv_to_vg)
    self.add_pv_to_vg_treeview = self.glade_xml.get_object('add_pv_to_vg_treeview')
    self.ok_add_pv_to_vg_button = self.glade_xml.get_object('ok_add_pv_to_vg_button')
    self.ok_add_pv_to_vg_button.connect("clicked",self.on_ok_add_pv_to_vg)
    self.cancel_add_pv_to_vg_button = self.glade_xml.get_object('cancel_add_pv_to_vg_button')
    self.cancel_add_pv_to_vg_button.connect("clicked",self.on_cancel_add_pv_to_vg)
    self.add_pv_to_vg_label = self.glade_xml.get_object('add_pv_to_vg_label')
    model = Gtk.ListStore (GObject.TYPE_STRING,
                           GObject.TYPE_STRING)
    self.add_pv_to_vg_treeview.set_model(model)
    renderer1 = Gtk.CellRendererText()
    column1 = Gtk.TreeViewColumn("Volume Groups",renderer1, text=0)
    self.add_pv_to_vg_treeview.append_column(column1)
    renderer2 = Gtk.CellRendererText()
    column2 = Gtk.TreeViewColumn("Size",renderer2, text=1)
    self.add_pv_to_vg_treeview.append_column(column2)
    self.add_pv_to_vg_treeview.get_selection().connect("changed", self.vg_selection_on_change)
    
    # new lv button
    self.new_lv_button = self.glade_xml.get_object('new_lv_button')
    self.new_lv_button.connect("clicked",self.on_new_lv)
    
    self.setup_extend_vg_form()
    self.setup_misc_widgets()
    
  ##################
  ##This form adds a new VG
  def setup_new_vg_form(self):
    self.new_vg_dlg = self.glade_xml.get_object('new_vg_form')
    self.new_vg_dlg.connect("delete_event",self.new_vg_delete_event)
    self.new_vg_button = self.glade_xml.get_object('new_vg_button')
    self.new_vg_button.connect("clicked", self.on_new_vg)
    self.ok_new_vg_button = self.glade_xml.get_object('ok_new_vg_button')
    self.ok_new_vg_button.connect("clicked",self.ok_new_vg)
    self.cancel_new_vg_button = self.glade_xml.get_object('cancel_new_vg_button')
    self.cancel_new_vg_button.connect("clicked", self.cancel_new_vg)
    
    ##Buttons and fields...
    self.new_vg_name = self.glade_xml.get_object('new_vg_name')
    self.new_vg_max_pvs = self.glade_xml.get_object('new_vg_max_pvs')
    self.new_vg_max_lvs = self.glade_xml.get_object('new_vg_max_lvs')
    self.new_vg_extent_size = self.glade_xml.get_object('new_vg_extent_size')
    self.new_vg_radio_meg = self.glade_xml.get_object('radiobutton1')
    self.new_vg_radio_meg.connect('clicked', self.change_new_vg_radio)
    self.new_vg_radio_kilo = self.glade_xml.get_object('radiobutton2')
    self.new_vg_clustered = self.glade_xml.get_object('clustered_butt')

  def on_new_vg(self, button):
    self.prep_new_vg_dlg()
    self.new_vg_dlg.show()
                                                                                
  def cancel_new_vg(self, button):
    self.new_vg_dlg.hide()

  def ok_new_vg(self, button):
    Name_request = ""
    max_physical_volumes = 256
    max_logical_volumes = 256
    phys_extent_size = 8
    phys_extent_units_meg = True
    autobackup = True
    resizable = True
    
    selection = self.treeview.get_selection()
    model,iter = selection.get_selected()
    pv = model.get_value(iter, OBJ_COL)
    
    proposed_name = self.new_vg_name.get_text().strip()
    if proposed_name == "":
        self.errorMessage(MUST_PROVIDE_VG_NAME)
        return
    
    #Now check for unique name
    vg_list = self.model_factory.get_VGs()
    for vg in vg_list:
        if vg.get_name() == proposed_name:
            self.new_vg_name.select_region(0, (-1))
            self.errorMessage(NON_UNIQUE_VG_NAME % proposed_name)
            return
    Name_request = proposed_name
    
    max_pvs_field = self.new_vg_max_pvs.get_text()
    if max_pvs_field.isalnum() == False:
        self.errorMessage(NUMBERS_ONLY_MAX_PVS)
        self.new_vg_max_pvs.set_text(str(MAX_PHYSICAL_VOLS))
        return
    else:
        max_pvs = int(max_pvs_field)
        if (max_pvs < 1) or (max_pvs > MAX_PHYSICAL_VOLS):
            self.errorMessage(NUMBERS_ONLY_MAX_PVS)
            self.new_vg_max_pvs.set_text(str(MAX_PHYSICAL_VOLS))
            return
        max_physical_volumes = max_pvs
    
    max_lvs_field = self.new_vg_max_lvs.get_text()
    if max_lvs_field.isalnum() == False:
        self.errorMessage(NUMBERS_ONLY_MAX_LVS)
        self.new_vg_max_lvs.set_text(str(MAX_LOGICAL_VOLS))
        return
    else:
        max_lvs = int(max_lvs_field)
        if (max_lvs < 1) or (max_lvs > MAX_LOGICAL_VOLS):
            self.errorMessage(NUMBERS_ONLY_MAX_LVS)
            self.new_vg_max_lvs.set_text(str(MAX_LOGICAL_VOLS))
            return
        max_logical_volumes = max_lvs
    
    extent_idx = self.new_vg_extent_size.get_active()
    phys_extent_units_meg =  self.new_vg_radio_meg.get_active()
    
    clustered = self.new_vg_clustered.get_active()
    if clustered:
        msg = _("In order for Volume Group to be safely used in clustered environment, lvm2-cluster rpm has to be installed, `lvmconf --enable-cluster` has to be executed and clvmd service has to be running")
        self.infoMessage(msg)
    
    try:
        self.command_handler.create_new_vg(Name_request,
                                           str(max_physical_volumes),
                                           str(max_logical_volumes),
                                           ACCEPTABLE_EXTENT_SIZES[extent_idx],
                                           phys_extent_units_meg,
                                           pv.get_path(),
                                           clustered)
    except CommandError as e:
        self.errorMessage(e.getMessage())
    
    self.new_vg_dlg.hide()
    
    self.reset_tree_model(*[Name_request])
  
  def prep_new_vg_dlg(self):
      self.new_vg_name.set_text("")
      self.new_vg_max_pvs.set_text(str(MAX_PHYSICAL_VOLS))
      self.new_vg_max_lvs.set_text(str(MAX_LOGICAL_VOLS))
      self.new_vg_radio_meg.set_active(True)
      self.new_vg_extent_size.set_active(DEFAULT_EXTENT_SIZE_MEG_IDX)
      self.new_vg_clustered.set_active(False)

  def change_new_vg_radio(self, button):
      pass
      #menu = self.new_vg_extent_size.get_menu()
      #items = menu.get_children()
      #We don't want to offer the 2 and 4 options for kilo's - min size is 8k
      #if self.new_vg_radio_meg.get_active() == True:
      #    items[0].set_sensitive(True)
      #    items[1].set_sensitive(True)
      #    self.new_vg_extent_size.set_history(DEFAULT_EXTENT_SIZE_MEG_IDX)
      #else:
      #    items[0].set_sensitive(False)
      #    items[1].set_sensitive(False)
      #    self.new_vg_extent_size.set_history(DEFAULT_EXTENT_SIZE_KILO_IDX)
  
  def on_pv_rm(self, button):
      self.remove_pv()
  
  def remove_pv(self, pv=None):
    mapped_lvs = True
    solo_pv = False
    reset_tree = False
    if pv == None:
        reset_tree = True #This says that tree reset will not be handled by caller
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        pv = model.get_value(iter, OBJ_COL)
    vg = pv.get_vg()
    
    # first check if all extents can be migrated
    for extent in pv.get_extent_blocks():
        extents_lv = extent.get_lv()
        if extents_lv.is_used():
            error_message = None
            if extents_lv.is_mirror_log:
                error_message = _("Physical Volume %s contains extents belonging to a mirror log of Logical Volume %s. Mirrored Logical Volumes are not yet migratable, so %s is not removable.")
                error_message = error_message % (pv.get_path(), extents_lv.get_name(), pv.get_path())
            elif extents_lv.is_mirror_image:
                error_message = _("Physical Volume %s contains extents belonging to a mirror image of Logical Volume %s. Mirrored Logical Volumes are not yet migratable, so %s is not removable.")
                error_message = error_message % (pv.get_path(), extents_lv.get_name(), pv.get_path())
            elif extents_lv.is_snapshot():
                error_message = _("Physical Volume %s contains extents belonging to %s, a snapshot of %s. Snapshots are not yet migratable, so %s is not removable.")
                error_message = error_message % (pv.get_path(), extents_lv.get_name(), extents_lv.get_snapshot_info()[0].get_name(), pv.get_path())
            elif extents_lv.has_snapshots():
                snapshots = extents_lv.get_snapshots()
                if len(snapshots) == 1:
                    error_message = _("Physical Volume %s contains extents belonging to %s, the origin of snapshot %s. Snapshot origins are not yet migratable, so %s is not removable.")
                else:
                    error_message = _("Physical Volume %s contains extents belonging to %s, the origin of snapshots %s. Snapshot origins are not yet migratable, so %s is not removable.")
                snapshots_string = snapshots[0].get_name()
                for snap in snapshots[1:]:
                    snapshot_string = snapshot_string + ', ' + snap.get_name()
                error_message = error_message % (pv.get_path(), extents_lv.get_name(), snapshots_string, pv.get_path())
            if error_message != None:
                self.errorMessage(error_message)
                return False
    
    #The following cases must be considered in this method:
    #1) a PV is to be removed that has extents mapped to an LV:
    #  1a) if there are other PVs, call pvmove on the PV to migrate the 
    #      data to other  PVs in the VG
    #      i) If there is sufficient room, pvmove the extents, then vgreduce
    #      ii) If there is not room, inform the user to add more storage and
    #           try again later
    #  1b) If there are not other PVs, state that either more PVs must
    #      be added so that the in use extents can be migrated, or else
    #      present a list of LVs that must be removed in order to 
    #      remove the PV
    #2) a PV is to be removed that has NO LVs mapped to its extents:
    #  2a) If there are more than one PV in the VG, just vgreduce away the PV
    #  2b) If the PV is the only one, then vgremove the VG
    #
    
    total, alloc, free = pv.get_extent_total_used_free()
    pv_list = list(vg.get_pvs().values())
    if len(pv_list) <= 1: #This PV is the only one in the VG
        solo_pv = True
    else:
        solo_pv = False
    
    extent_list = pv.get_extent_blocks()[:] # copy
    if len(extent_list) == 1: #There should always be at least one extent seg
        #We now know either the entire PV is used by one LV, or else it is
        #an unutilized PV. If the latter, we can just vgreduce it away 
        #if (seg_name == FREE) or (seg_name == UNUSED):
        if extent_list[0].get_lv().is_used():
            mapped_lvs = True
        else:
            mapped_lvs = False
    else:
        mapped_lvs = True
    
    #Cases:
    if mapped_lvs == False:
        if solo_pv:
            #call vgremove
            retval = self.warningMessage(CONFIRM_VG_REMOVE % (pv.get_path(),vg.get_name()))
            if (retval == Gtk.ResponseType.NO):
                return False
            try:
                self.command_handler.remove_vg(vg.get_name())
            except CommandError as e:
                self.errorMessage(e.getMessage())
                return False
        else: #solo_pv is False, more than one PV...
            retval = self.warningMessage(CONFIRM_PV_VG_REMOVE % (pv.get_path(),vg.get_name()))
            if (retval == Gtk.ResponseType.NO):
                return False
            try:
                self.command_handler.reduce_vg(vg.get_name(), pv.get_path())
            except CommandError as e:
                self.errorMessage(e.getMessage())
                return False
    else:
        #Two cases here: if solo_pv, bail, else check for size needed
        if solo_pv:
            self.errorMessage(SOLO_PV_IN_VG % pv.get_path())
            return False
        else: #There are additional PVs. We need to check space 
            ext_total, ext_used, ext_free = vg.get_extent_total_used_free()
            actual_free_exts = ext_free - free
            if alloc <= actual_free_exts:
                if self.command_handler.is_dm_mirror_loaded() == False:
                    self.errorMessage(NO_DM_MIRROR)
                    return False
                retval = self.warningMessage(CONFIRM_PV_VG_REMOVE % (pv.get_path(),vg.get_name()))
                if (retval == Gtk.ResponseType.NO):
                    return False
                
                # remove unused from extent_list
                for ext in extent_list[:]:
                    if ext.get_lv().is_used() == False:
                        extent_list.remove(ext)
                dlg = self.migrate_exts_dlg(True, pv, extent_list)
                if dlg == None:
                    return False
                exts_structs = []
                for ext in extent_list:
                    exts_structs.append(ext.get_start_size())
                try:
                    self.command_handler.move_pv(pv.get_path(), exts_structs, dlg.get_data())
                except CommandError as e:
                    self.errorMessage(e.getMessage())
                    return True
                try:
                    self.command_handler.reduce_vg(vg.get_name(), pv.get_path())
                except CommandError as e:
                    self.errorMessage(e.getMessage())
                    return True
                
            else:
                self.errorMessage(NOT_ENOUGH_SPACE_VG % (vg.get_name(),pv.get_path()))
                return False
    
    if reset_tree == True:
        self.reset_tree_model(*[vg.get_name()])
    
    return True
  
  def on_lv_rm(self, button):
    self.remove_lv()
  
  def remove_lv(self, lv=None):
    reset_tree = False
    if lv == None:
        reset_tree = True
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        lv = model.get_value(iter, OBJ_COL)
    
    if lv.has_snapshots():
        snapshots = lv.get_snapshots()
        if len(snapshots) == 1:
            self.errorMessage(CANNOT_REMOVE_UNDER_SNAPSHOT % (lv.get_name(), snapshots[0].get_name()))
        else:
            snaps_str = snapshots[0].get_name()
            for snap in snapshots[1:]:
                snaps_str = snaps_str + ', ' + snap.get_name()
            self.errorMessage(CANNOT_REMOVE_UNDER_SNAPSHOTS % (lv.get_name(), snaps_str))
        return False
    
    mountpoint = self.model_factory.getMountPoint(lv.get_path())
    fs = Filesystem.get_fs(lv.get_path())
    if fs.name == Filesystem.get_filesystems()[0].name:
        fs = None
    fstab_mountpoint = Fstab.get_mountpoint(lv.get_path())
    
    # prompt for confirmation
    message = None
    if mountpoint == None:
        if fs == None:
            message = CONFIRM_LV_REMOVE % lv.get_name()
        else:
            message = CONFIRM_LV_REMOVE_FILESYSTEM % (lv.get_name(), fs.name, lv.get_name())
    else:
        message = CONFIRM_LV_REMOVE_MOUNTED % (lv.get_name(), mountpoint, lv.get_name())
    retval = self.warningMessage(message)
    if retval == Gtk.ResponseType.NO:
        return False
    
    # unmount and remove from fstab
    if mountpoint != None:
        try:
            self.command_handler.unmount(mountpoint)
        except CommandError as e:
            self.errorMessage(e.getMessage())
            return False
    if fstab_mountpoint != None:
        Fstab.remove(lv.get_path())
    
    # finally remove lv
    try:
        self.command_handler.remove_lv(lv.get_path())
    except CommandError as e:
        self.errorMessage(e.getMessage())
        return False
    
    if reset_tree:
        self.reset_tree_model(*[lv.get_vg().get_name()])
    
    return True
  
  def on_rm_select_lvs(self, button):
    if self.section_list == None:
        return
    #check if list > 0
    lvs_to_remove = self.section_list[:]
    if len(lvs_to_remove) == 0:
        return
    vg = lvs_to_remove[0].get_vg()
    # check if all operations could be completed
    for lv in lvs_to_remove:
        if lv.has_snapshots():
            for snap in lv.get_snapshots():
                if snap not in lvs_to_remove:
                    self.errorMessage(UNABLE_TO_PROCESS_REQUEST + '\n' + _("Logical Volume \"%s\" has snapshots that are not selected for removal. They must be removed as well.") % lv.get_name())
                    return
    # remove snapshots first
    reload_lvm = False
    reset_tree_model = False
    for lv in lvs_to_remove[:]:
        if lv.is_snapshot():
            lvs_to_remove.remove(lv)
            if self.remove_lv(lv):
                # success
                reload_lvm = True
            else:
                # remove_lv failure
                origin = lv.get_snapshot_info()[0]
                if origin in lvs_to_remove:
                    msg = _("\"%s\", an origin of snapshot \"%s\", has been deleted from removal list.")
                    msg = msg % (origin.get_name(), lv.get_name())
                    self.simpleInfoMessage(msg)
                    lvs_to_remove.remove(origin)
    
    if reload_lvm:
        self.model_factory.reload()
        vg = self.model_factory.get_VG(vg.get_name())
        reset_tree_model = True
    # remove other lvs
    for lv in lvs_to_remove:
        if self.remove_lv(vg.get_lvs()[lv.get_name()]):
            reset_tree_model = True
    
    if reset_tree_model:
        self.clear_highlighted_sections()
        self.reset_tree_model(*[vg.get_name()])
  
  def on_rm_select_pvs(self, button):
      if self.section_list == None:
          return
      #need to check if list > 0
      if len(self.section_list) == 0:
          return
      # check if all operations could be completed
      for pv in self.section_list:
          for extent in pv.get_extent_blocks():
              extents_lv = extent.get_lv()
              if extents_lv.is_used():
                  error_message = None
                  if extents_lv.is_mirror_log or extents_lv.is_mirror_image:
                      error_message = _("Physical Volume \"%s\" contains extents belonging to a mirror. Mirrors are not migratable, so %s is not removable.")
                      error_message = error_message % (pv.get_path(), pv.get_path())
                  elif extents_lv.is_snapshot() or extents_lv.has_snapshots():
                      error_message = _("Physical Volume \"%s\" contains extents belonging to a snapshot or a snapshot's origin. Snapshots are not migratable, so %s is not removable.")
                      error_message = error_message % (pv.get_path(), pv.get_path())
                  if error_message != None:
                      self.errorMessage(UNABLE_TO_PROCESS_REQUEST + '\n' + error_message)
                      return
    
      # do the job
      reset_tree_model = False
      for pv in self.section_list:
          pvpath = pv.get_path()
          vgname = pv.get_vg().get_name()
          pv_to_remove = self.model_factory.get_VG(vgname).get_pvs()[pvpath]
          if self.remove_pv(pv_to_remove):
              # remove_pv migrates extents -> need to reload lvm data
              self.model_factory.reload()
              reset_tree_model = True
      
      selection = self.treeview.get_selection()
      model,iter = selection.get_selected()
      vg = model.get_value(iter, OBJ_COL)
      
      if reset_tree_model:
          self.clear_highlighted_sections()
          self.reset_tree_model(*[vg.get_name()])
  
  def on_new_lv(self, button):
      main_selection = self.treeview.get_selection()
      main_model, main_iter = main_selection.get_selected()
      main_path = main_model.get_path(main_iter)
      vg = main_model.get_value(main_iter, OBJ_COL)
      if len(list(vg.get_lvs().values())) == vg.get_max_lvs():
          self.errorMessage(EXCEEDED_MAX_LVS)
          return
      
      total_exts, used_exts, free_exts = vg.get_extent_total_used_free()
      if free_exts == 0:
          self.errorMessage(NOT_ENOUGH_SPACE_FOR_NEW_LV % vg.get_name())
          return
      
      dlg = LV_edit_props(None, vg, self.model_factory, self.command_handler)
      if dlg.run() == False:
          return
      
      self.reset_tree_model(*[vg.get_name()])
  
  def on_init_entity(self, button):
      selection = self.treeview.get_selection()
      model,iter = selection.get_selected()
      pv = model.get_value(iter, OBJ_COL)
      if self.initialize_entity(pv) == None:
          return
      self.reset_tree_model(*['', '', pv.get_path()])
  
  def on_init_entity_from_menu(self, obj, dlg=None):
      if dlg == None:
          dlg = self.glade_xml.get_object("init_block_device_dlg")
      label = self.glade_xml.get_object("init_block_device_dlg_path")
      label.select_region(0, (-1))
      label.grab_focus()
      rc = dlg.run()
      dlg.hide()
      if rc == Gtk.ResponseType.APPLY:
          path = label.get_text().strip()
          target = follow_links_to_target(path)
          if target == None:
              self.errorMessage(_("The path you specified does not exist."))
              self.on_init_entity_from_menu(None, dlg)
              return
          else:
              o = execWithCapture('/bin/ls', ['/bin/ls', '-l', target])
              output = o.strip()
              if output[0] != 'b':
                  self.errorMessage(_("The path you specified is not a Block Device."))
                  self.on_init_entity_from_menu(None, dlg)
                  return
          pv = PhysicalVolume.PhysicalVolume(path, None, None, 0, 0, False, 0, 0)
          pv.set_path(path)
          self.glade_xml.get_object("init_block_device_dlg_path").set_text('')
          if self.initialize_entity(pv) == None:
              self.glade_xml.get_object("init_block_device_dlg_path").set_text(path)
              self.on_init_entity_from_menu(None, dlg)
          else:
              self.reset_tree_model(*['', '', pv.get_path()])
      else:
          self.glade_xml.get_object("init_block_device_dlg_path").set_text('')
  
  def initialize_entity(self, pv):
      path = pv.get_path()
      mountPoint = self.model_factory.getMountPoint(path)
      doFormat = False
      message = ''
      if mountPoint == None:
          fs = Filesystem.get_fs(path)
          if fs.name == Filesystem.get_filesystems()[0].name:
              fs = None
          if fs == None:
              if pv.needsFormat():
                  if pv.wholeDevice():
                      message = INIT_ENTITY % path
                  else:
                      # disabled until fdisk_wrapper gets into reliable shape
                      # doFormat = True
                      # message = INIT_ENTITY_FREE_SPACE % (pv.get_volume_size_string(), path)
                      return None
              else:
                  message = INIT_ENTITY % path
          else:
              message = INIT_ENTITY_FILESYSTEM % (path, fs.name, path)
      else:
          message = INIT_ENTITY_MOUNTED % (path, mountPoint, path)
      rc = self.warningMessage(message)
      if (rc == Gtk.ResponseType.NO):
          return None
      
      if mountPoint != None:
          try:
              self.command_handler.unmount(mountPoint)
          except CommandError as e:
              self.errorMessage(e.getMessage())
              return None
      
      if pv.needsFormat() and pv.wholeDevice():
          dialog = self.glade_xml.get_object('whole_device_format_choice')
          label = self.glade_xml.get_object('whole_device_format_choice_label')
          label.set_text(INIT_ENTITY_DEVICE_CHOICE % path) 
          rc = dialog.run()
          dialog.hide()
          if rc == Gtk.ResponseType.YES:
              doFormat = True
          elif rc == Gtk.ResponseType.NO:
              doFormat = False
          else:
              return None
      
      try:
          if doFormat:
              # format
              devpath = path
              path = self.model_factory.partition_UV(pv)
              # tell kernel to reread new partition table
              if self.command_handler.reread_partition_table(devpath) == False:
                  message = RESTART_COMPUTER % pv.getDevnames()[0]
                  self.errorMessage(message)
                  self.errorMessage(_("Initialization of %s failed") % pv.getDevnames()[0])
                  return None
              
          self.command_handler.initialize_entity(path)
      except CommandError as e:
          self.errorMessage(e.getMessage())
          return None
      return path
  
  def vg_selection_on_change(self, tree_view):
    selection = self.add_pv_to_vg_treeview.get_selection()
    (model, iter) = selection.get_selected()

    if iter == None:
        self.ok_add_pv_to_vg_button.set_sensitive(False)
    else:
        self.ok_add_pv_to_vg_button.set_sensitive(True)

  def on_add_pv_to_vg(self, button):
      model = self.add_pv_to_vg_treeview.get_model()
      if model != None:
          model.clear()
      
      vg_list = self.model_factory.get_VGs()
      if len(vg_list) > 0:
          for vg in vg_list:
              iter = model.append()
              model.set(iter,
                        NAME_COL, vg.get_name(),
                        SIZE_COL, vg.get_size_total_used_free_string()[0])
      
      selection = self.treeview.get_selection()
      main_model, iter_val = selection.get_selected()
      pv = main_model.get_value(iter_val, OBJ_COL)
      label_string = ADD_PV_TO_VG_LABEL % pv.get_path()
      self.add_pv_to_vg_label.set_text(label_string)
      self.add_pv_to_vg_treeview.set_model(model)
      self.add_pv_to_vg_dlg.show()
  
  def add_pv_to_vg_delete_event(self, *args):
      self.add_pv_to_vg_dlg.hide()
      return True
  
  def on_ok_add_pv_to_vg(self, button):
      selection = self.treeview.get_selection()
      main_model, iter_val = selection.get_selected()
      pv = main_model.get_value(iter_val, OBJ_COL)
      
      selection = self.add_pv_to_vg_treeview.get_selection()
      model, iter = selection.get_selected()
      if iter == None:
          return
      vgname = model.get_value(iter, NAME_COL)
      
      vg = self.model_factory.get_VG(vgname)
      
      #Check if this VG allows an Additional PV
      if vg.get_max_pvs() == len(list(vg.get_pvs().values())):
          self.errorMessage(EXCEEDED_MAX_PVS)
          self.add_pv_to_vg_dlg.hide()
          return
      
      try:
          self.command_handler.add_unalloc_to_vg(pv.get_path(), vgname)
      except CommandError as e:
          self.errorMessage(e.getMessage())
          return
      
      args = list()
      args.append(pv.get_path())
      self.reset_tree_model(*[vg.get_name()])
      
      self.add_pv_to_vg_dlg.hide()
  
  def on_cancel_add_pv_to_vg(self,button):
      self.add_pv_to_vg_dlg.hide()
  
  
  def setup_extend_vg_form(self):
      self.on_extend_vg_button = self.glade_xml.get_object('on_extend_vg_button')
      self.on_extend_vg_button.connect("clicked",self.on_extend_vg)
      self.extend_vg_form = self.glade_xml.get_object('extend_vg_form')
      self.extend_vg_form.connect("delete_event",self.extend_vg_delete_event)
      self.extend_vg_tree = self.glade_xml.get_object('extend_vg_tree')
      self.extend_vg_label = self.glade_xml.get_object('extend_vg_label')
      self.glade_xml.get_object('on_ok_extend_vg').connect('clicked', self.on_ok_extend_vg)
      self.glade_xml.get_object('on_cancel_extend_vg').connect('clicked',self.on_cancel_extend_vg)
      #set up columns for tree
      model = Gtk.ListStore (GObject.TYPE_STRING,
                             GObject.TYPE_STRING,
                             GObject.TYPE_STRING,
                             GObject.TYPE_INT,
                             GObject.TYPE_PYOBJECT)
      
      self.extend_vg_tree.set_model(model)
      renderer1 = Gtk.CellRendererText()
      column1 = Gtk.TreeViewColumn(ENTITY_NAME,renderer1, text=0)
      self.extend_vg_tree.append_column(column1)
      renderer2 = Gtk.CellRendererText()
      column2 = Gtk.TreeViewColumn(ENTITY_SIZE,renderer2, text=1)
      self.extend_vg_tree.append_column(column2)
      renderer3 = Gtk.CellRendererText()
      column3 = Gtk.TreeViewColumn(ENTITY_TYPE,renderer3, markup=2)
      self.extend_vg_tree.append_column(column3)
      # set up multiselection
      self.extend_vg_tree.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
  
  def on_extend_vg(self, button):
      main_selection = self.treeview.get_selection()
      main_model,main_iter = main_selection.get_selected()
      main_path = main_model.get_path(main_iter)
      vg = main_model.get_value(main_iter, OBJ_COL)
      if vg.get_max_pvs() == len(list(vg.get_pvs().values())):
          self.errorMessage(EXCEEDED_MAX_PVS)
          return
      
      self.rebuild_extend_vg_tree()
      self.extend_vg_form.show()
  
  def on_ok_extend_vg(self, button):
      selection = self.extend_vg_tree.get_selection()
      if selection == None:
          self.extend_vg_form.hide() #cancel opp if OK clicked w/o selection
      
      #Now get name of VG to be extended...
      main_selection = self.treeview.get_selection()
      main_model,main_iter = main_selection.get_selected()
      main_path = main_model.get_path(main_iter)
      vg = main_model.get_value(main_iter, OBJ_COL)
      
      # handle selections
      model, treepathlist = selection.get_selected_rows()
      
      # check if pvs can be added to vg
      max_addable_pvs = vg.get_max_pvs() - len(list(vg.get_pvs().values()))
      if max_addable_pvs < len(treepathlist):
          self.errorMessage(EXCEEDING_MAX_PVS % max_addable_pvs)
          return
      
      reset_tree_model = False
      for treepath in treepathlist:
          iter = model.get_iter(treepath)
          entity_path = model.get_value(iter, NAME_COL)
          entity_type = model.get_value(iter, VOL_TYPE_COL)
          if entity_type == UNINIT_VOL:  #First, initialize if necessary
              entity = model.get_value(iter, OBJ_COL)
              entity_path = self.initialize_entity(entity)
              if entity_path == None:
                  continue
          try:
              self.command_handler.add_unalloc_to_vg(entity_path, vg.get_name())
          except CommandError as e:
              self.errorMessage(e.getMessage())
              continue
          reset_tree_model = True
      
      self.extend_vg_form.hide()
      if reset_tree_model:
          self.reset_tree_model(*[vg.get_name()])
  
  def on_cancel_extend_vg(self, button):
      self.extend_vg_form.hide()
  
  def extend_vg_delete_event(self, *args):
      self.extend_vg_form.hide()
      return True
  
  def rebuild_extend_vg_tree(self):
    uv_string = "<span foreground=\"#ED1C2A\"><b>" + UNALLOCATED_PV + "</b></span>"
    iv_string = "<span foreground=\"#BBBBBB\"><b>" + UNINIT_DE + "</b></span>"
    model = self.extend_vg_tree.get_model()
    if model != None:
        model.clear()
    
    unallocated_vols = self.model_factory.query_unallocated()
    for vol in unallocated_vols:
        iter = model.append()
        model.set(iter,
                  NAME_COL, vol.get_path(),
                  SIZE_COL, vol.get_size_total_string(),
                  PATH_COL, uv_string,
                  VOL_TYPE_COL, UNALLOC_VOL,
                  OBJ_COL, vol)
    
    uninitialized_list = self.model_factory.query_uninitialized()
    for item in uninitialized_list:
        if item.initializable:
            iter = model.append()
            model.set(iter,
                      NAME_COL, item.get_path(),
                      SIZE_COL, item.get_size_total_string(),
                      PATH_COL, iv_string,
                      VOL_TYPE_COL,UNINIT_VOL,
                      OBJ_COL, item)
    
    selection = self.treeview.get_selection()
    main_model, iter_val = selection.get_selected()
    vg = main_model.get_value(iter_val, OBJ_COL)
    self.extend_vg_label.set_text(ADD_VG_LABEL % vg.get_name())
  
  def new_vg_delete_event(self, *args):
    self.new_vg_dlg.hide()
    return True
  
  def setup_misc_widgets(self):
      self.remove_unalloc_pv = self.glade_xml.get_object('remove_unalloc_pv')
      self.remove_unalloc_pv.connect("clicked",self.on_remove_unalloc_pv)
      self.on_pv_rm_button = self.glade_xml.get_object('on_pv_rm_button')
      self.on_pv_rm_button.connect("clicked",self.on_pv_rm)
      self.on_lv_rm_button = self.glade_xml.get_object('on_lv_rm_button')
      self.on_lv_rm_button.connect("clicked",self.on_lv_rm)
      self.on_rm_select_lvs_button = self.glade_xml.get_object('on_rm_select_lvs')
      self.on_rm_select_lvs_button.connect("clicked",self.on_rm_select_lvs)
      self.on_rm_select_pvs_button = self.glade_xml.get_object('on_rm_select_pvs')
      self.on_rm_select_pvs_button.connect("clicked",self.on_rm_select_pvs)
      self.migrate_exts_button = self.glade_xml.get_object('button27')
      self.migrate_exts_button.connect("clicked",self.on_migrate_exts)
      self.edit_lv_button = self.glade_xml.get_object('button35')
      self.edit_lv_button.connect("clicked",self.on_edit_lv)
      self.create_snapshot_button = self.glade_xml.get_object('create_snapshot_button')
      self.create_snapshot_button.connect("clicked",self.on_create_snapshot)
      
      # misc events
      self.glade_xml.get_object("initialize_block_device1").connect('activate', self.on_init_entity_from_menu)
      
  
  def on_remove_unalloc_pv(self, button):
      selection = self.treeview.get_selection()
      model, iter = selection.get_selected()
      pv = model.get_value(iter, OBJ_COL)
      retval = self.warningMessage(CONFIRM_PVREMOVE % pv.get_path())
      if (retval == Gtk.ResponseType.NO):
          return
      else:
          try:
              self.command_handler.remove_pv(pv.get_path())
          except CommandError as e:
              self.errorMessage(e.getMessage())
              return
          self.reset_tree_model(*['', '', pv.get_path()])
  
  def on_migrate_exts(self, button):
      selection = self.treeview.get_selection()
      model, iter = selection.get_selected()
      pv = model.get_value(iter, OBJ_COL)
      
      # get selected extents
      if self.section_list == None:
          self.simpleInfoMessage(_("Please select some extents first"))
          return
      if len(self.section_list) == 0:
          self.simpleInfoMessage(_("Please select some extents first"))
          return
      extents_from = self.section_list[:]
      
      # dialog
      dlg = self.migrate_exts_dlg(False, pv, extents_from)
      if dlg == None:
          return
      exts_from_structs = []
      for ext in extents_from:
          exts_from_structs.append(ext.get_start_size())
      try:
          self.command_handler.move_pv(pv.get_path(), exts_from_structs, dlg.get_data())
      except CommandError as e:
          self.errorMessage(e.getMessage())
      self.reset_tree_model(*[pv.get_vg().get_name()])
      return
  
  # removal - whether this is a migration or a removal operation
  def migrate_exts_dlg(self, removal, pv, exts):
      vg = pv.get_vg()
      needed_extents = 0
      for ext in exts:
          needed_extents = needed_extents + ext.get_start_size()[1]
      
      free_extents = 0
      pvs = []
      for p in list(vg.get_pvs().values()):
          if pv != p:
              p_free_exts = p.get_extent_total_used_free()[2]
              if p_free_exts >= needed_extents:
                  pvs.append(p)
              free_extents = free_extents + p_free_exts
      if needed_extents > free_extents:
          self.errorMessage(_("There are not enough free extents to perform the necessary migration. Adding more physical volumes would solve the problem."))
          return None
      lvs = {}
      for ext in exts:
          lv = ext.get_lv()
          lvs[lv] = lv
      dlg = MigrateDialog(not removal, pvs, list(lvs.values()))
      if not dlg.run():
          return None
      return dlg
  
  def on_edit_lv(self, button):
      selection = self.treeview.get_selection()
      model, iter = selection.get_selected()
      lv = model.get_value(iter, OBJ_COL)
      vg = lv.get_vg()
      dlg = LV_edit_props(lv, vg, self.model_factory, self.command_handler)
      if dlg.run() == False:
          return
      
      self.reset_tree_model(*[vg.get_name()])
  
  def on_create_snapshot(self, button):
      selection = self.treeview.get_selection()
      model, iter = selection.get_selected()
      lv = model.get_value(iter, OBJ_COL)
      vg = lv.get_vg()
      if vg.get_max_lvs() == len(list(vg.get_lvs().values())):
          self.errorMessage(EXCEEDED_MAX_LVS)
          return
      
      # checks
      if lv.is_snapshot():
          self.errorMessage(ALREADY_A_SNAPSHOT)
          return
      if lv.is_mirrored():
          self.errorMessage(CANNOT_SNAPSHOT_A_MIRROR)
          return
      t_exts, u_exts, f_exts = vg.get_extent_total_used_free()
      if f_exts == 0:
          self.errorMessage(NOT_ENOUGH_SPACE_FOR_NEW_LV % vg.get_name())
          return
      if self.command_handler.is_dm_snapshot_loaded() == False:
          self.errorMessage(NO_DM_SNAPSHOT)
          return
      
      dlg = LV_edit_props(lv, vg, self.model_factory, self.command_handler, True)
      if dlg.run() == False:
          return
      
      self.reset_tree_model(*[vg.get_name()])
      
      
      
  #######################################################
  ###Convenience Dialogs
  
  def warningMessage(self, message):
      dlg = Gtk.MessageDialog(None, 0,
                              Gtk.MessageType.WARNING,
                              Gtk.ButtonsType.YES_NO,
                              message)
      dlg.show_all()
      rc = dlg.run()
      dlg.destroy()
      if (rc == Gtk.ResponseType.NO):
          return Gtk.ResponseType.NO
      elif (rc == Gtk.ResponseType.DELETE_EVENT):
          return Gtk.ResponseType.NO
      elif (rc == Gtk.ResponseType.CLOSE):
          return Gtk.ResponseType.NO
      elif (rc == Gtk.ResponseType.CANCEL):
          return Gtk.ResponseType.NO
      else:
          return rc
  
  def errorMessage(self, message):
      dlg = Gtk.MessageDialog(None, 0,
                              Gtk.MessageType.ERROR,
                              Gtk.ButtonsType.OK,
                              message)
      dlg.show_all()
      rc = dlg.run()
      dlg.destroy()
      return rc
  
  def infoMessage(self, message):
      dlg = Gtk.MessageDialog(None, 0,
                              Gtk.MessageType.INFO,
                              Gtk.ButtonsType.OK,
                              message)
      dlg.show_all()
      rc = dlg.run()
      dlg.destroy()
      return rc
  
  def simpleInfoMessage(self, message):
      dlg = Gtk.MessageDialog(None, 0,
                              Gtk.MessageType.INFO,
                              Gtk.ButtonsType.OK,
                              message)
      dlg.show_all()
      rc = dlg.run()
      dlg.destroy()
      if (rc == Gtk.ResponseType.NO):
          return Gtk.ResponseType.NO
      elif (rc == Gtk.ResponseType.DELETE_EVENT):
          return Gtk.ResponseType.NO
      elif (rc == Gtk.ResponseType.CLOSE):
          return Gtk.ResponseType.NO
      elif (rc == Gtk.ResponseType.CANCEL):
          return Gtk.ResponseType.NO
      else:
          return rc
  
  def register_highlighted_sections(self, section_type, section_list):
      self.section_type = section_type
      self.section_list = section_list
  
  def clear_highlighted_sections(self):
      self.section_type = UNSELECTABLE_TYPE
      self.section_list = None
      
    

class MigrateDialog:
    
    def __init__(self, migrate, pvs, lvs):
        gladepath = 'migrate_extents.glade'
        if not os.path.exists(gladepath):
            gladepath = "%s/%s" % (INSTALLDIR, gladepath)
        self.glade_xml = Gtk.Builder()
        self.glade_xml.add_from_file(gladepath)
        
        # fill out lv selection combobox
        self.lv_combo = Gtk.ComboBoxText()
        self.glade_xml.get_object('lv_selection_container').pack_end(self.lv_combo, True, False, 0)
        self.lv_combo.show()
        self.lv_combo.set_sensitive(False)
        for lv in lvs:
            self.lv_combo.append_text(lv.get_name())
        model = self.lv_combo.get_model()
        iter = model.get_iter_first()
        self.lv_combo.set_active_iter(iter)
        
        # fill out pv selection combobox
        pv_selection_container = self.glade_xml.get_object('pv_selection_container')
        self.pv_combo = Gtk.ComboBoxText()
        pv_selection_container.pack_end(self.pv_combo, True, False, 0)
        self.pv_combo.show()
        self.pv_combo.set_sensitive(False)
        if len(pvs) != 0:
            for p in pvs:
                self.pv_combo.append_text(p.get_path())
            model = self.pv_combo.get_model()
            iter = model.get_iter_first()
            self.pv_combo.set_active_iter(iter)
        else:
            pv_selection_container.hide()
        
        self.dlg = self.glade_xml.get_object('dialog1')
        msg_label = self.glade_xml.get_object('msg_label')
        self.dlg.set_title(_("Migrate extents"))
        if migrate:
            msg_label.hide()
        else:
            # remove
            self.glade_xml.get_object('lv_selection_container').hide()
        
        # events
        self.glade_xml.get_object('choose_pv_radio').connect('clicked', self.on_choose_pv_radio)
        self.glade_xml.get_object('choose_lv_check').connect('clicked', self.on_choose_lv_check)
        
    
    def on_choose_pv_radio(self, obj1):
        if self.glade_xml.get_object('choose_pv_radio').get_active():
            self.pv_combo.set_sensitive(True)
        else:
            self.pv_combo.set_sensitive(False)
    
    def on_choose_lv_check(self, obj1):
        if self.glade_xml.get_object('choose_lv_check').get_active():
            self.lv_combo.set_sensitive(True)
        else:
            self.lv_combo.set_sensitive(False)
    
    def run(self):
        rc = self.dlg.run()
        self.dlg.hide()
        return rc == Gtk.ResponseType.OK
    
    # return [pv to migrate to, policy (0 - inherit, 1 - normal, 2 - contiguous, 3 - anywhere), lv to migrate from]
    def get_data(self):
        ret = []
        
        # migrate extents to
        if self.glade_xml.get_object('choose_pv_radio').get_active() == True:
            iter = self.pv_combo.get_active_iter()
            ret.append(self.pv_combo.get_model().get_value(iter, 0))
        else:
            ret.append(None)
        
        if self.glade_xml.get_object('radiobutton4').get_active():
            ret.append(0)
        elif self.glade_xml.get_object('radiobutton5').get_active():
            ret.append(1)
        elif self.glade_xml.get_object('radiobutton6').get_active():
            ret.append(2)
        else:
            ret.append(3)
        
        # lv to migrate from
        if self.glade_xml.get_object('choose_lv_check').get_active():
            iter = self.lv_combo.get_active_iter()
            ret.append(self.lv_combo.get_model().get_value(iter, 0))
        else:
            ret.append(None)    
        
        return ret



class LV_edit_props:
    
    # set lv to None if new lv is to be created
    def __init__(self, lv, vg, model_factory, command_handler, snapshot=False):
        self.snapshot = snapshot
        if lv == None:
            self.new = True
            self.snapshot = False
        else:
            if self.snapshot:
                self.new = True
            else:
                self.new = False
        self.lv = lv
        self.vg = vg
        self.model_factory = model_factory
        self.command_handler = command_handler
        
        # available filesystems
        self.filesystems = dict()
        fss = Filesystem.get_filesystems()
        self.fs_none = fss[0]
        for fs in fss:
            self.filesystems[fs.name] = fs
        if self.new:
            if self.snapshot:
                self.fs = Filesystem.get_fs(self.lv.get_path())
                self.filesystems[self.fs.name] = self.fs    
            else:
                self.fs = self.fs_none
            self.mount_point = ''
            self.mount = False
            self.mount_at_reboot = False
        else:
            self.fs = Filesystem.get_fs(lv.get_path())
            if self.fs.name == self.fs_none.name:
                self.fs = self.fs_none
            else:
                self.filesystems.pop(self.fs_none.name)
            self.filesystems[self.fs.name] = self.fs
            self.mount_point = self.model_factory.getMountPoint(lv.get_path())
            self.mountpoint_at_reboot = Fstab.get_mountpoint(lv.get_path().strip())
            if self.mount_point == None:
                if self.mountpoint_at_reboot == None:
                    self.mount_point = ''
                else:
                    self.mount_point = self.mountpoint_at_reboot
                self.mount = False
            else:
                self.mount = True
            self.mount_at_reboot = (self.mountpoint_at_reboot != None)
        for fs_name in self.filesystems:
            self.filesystems[fs_name].set_clustered(vg.clustered())
        
        gladepath = 'lv_edit_props.glade'
        if not os.path.exists(gladepath):
            gladepath = "%s/%s" % (INSTALLDIR, gladepath)
        self.glade_xml = Gtk.Builder()
        self.glade_xml.add_from_file(gladepath)
        self.dlg = self.glade_xml.get_object('dialog1')
        
        self.size_units_combo = Gtk.ComboBoxText()
        self.glade_xml.get_object('size_units_container').pack_end(self.size_units_combo, True, False, 0)
        self.size_units_combo.show()
        
        self.filesys_combo = Gtk.ComboBoxText()
        self.glade_xml.get_object('filesys_container').pack_start(self.filesys_combo, True, False, 0)
        self.filesys_combo.show()
        self.fs_config_button = Gtk.Button(_("Options"))
        self.glade_xml.get_object('filesys_container').pack_end(self.fs_config_button, True, False, 0)
        #self.fs_config_button.show()
        self.fs_config_button.hide()
        
    
    def run(self):
        need_reload = False
        
        self.setup_dlg()
        while True:
            rc = self.dlg.run()
            if rc == Gtk.ResponseType.REJECT:
                self.setup_dlg()
                continue
            elif rc == Gtk.ResponseType.OK:
                try:
                    if self.apply() == True:
                        need_reload = True
                        break
                except CommandError as e:
                    self.errorMessage(e.getMessage())
                    need_reload = True
                    break
            else:
                break
        self.dlg.hide()
        
        return need_reload
    
    def setup_dlg(self):
        # title
        if self.new:
            if self.snapshot:
                self.dlg.set_title(_("Create A Snapshot of %s") % self.lv.get_name())
            else:
                self.dlg.set_title(_("Create New Logical Volume"))
        else:
            if self.lv.is_snapshot():
                message = _("Edit %s, a Snapshot of %s")
                self.dlg.set_title(message % (self.lv.get_name(), self.lv.get_snapshot_info()[0].get_name()))
            else:
                self.dlg.set_title(_("Edit Logical Volume"))
        
        # lv name
        self.name_entry = self.glade_xml.get_object('lv_name')
        if self.new:
            self.name_entry.set_text('')
        else:
            self.name_entry.set_text(self.lv.get_name())
        
        # revert button
        if self.new:
            self.glade_xml.get_object('revert_button').hide()
        else:
            self.glade_xml.get_object('revert_button').show()
        
        # lv properties
        # TODO: use ACCEPTABLE_STRIPE_SIZES
        stripe_size_combo = self.glade_xml.get_object('stripe_size')
        model = stripe_size_combo.get_model()
        iter = model.get_iter_first()
        stripe_size_combo.set_active_iter(iter)
        if self.new:
            if self.snapshot:
                self.glade_xml.get_object('lv_properties_frame').hide()
            else:
                self.glade_xml.get_object('stripes_container').set_sensitive(False)
                stripe_size_combo = self.glade_xml.get_object('stripe_size')
                model = stripe_size_combo.get_model()
                iter = model.get_iter_first()
                stripe_size_combo.set_active_iter(iter)
                max_stripes = len(self.vg.get_pvs())
                if max_stripes > 8:
                    max_stripes = 8
                self.glade_xml.get_object('stripes_num').set_range(2, max_stripes)
                self.glade_xml.get_object('stripes_num').set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        else:
            if self.lv.is_snapshot():
                self.glade_xml.get_object('lv_properties_frame').hide()
            else:
                self.glade_xml.get_object('linear').hide()
                self.glade_xml.get_object('striped').hide()
                self.glade_xml.get_object('stripes_container').hide()
        
        # filesystem
        self.glade_xml.get_object('filesys_container').remove(self.filesys_combo)
        self.filesys_combo = Gtk.ComboBoxText()
        self.glade_xml.get_object('filesys_container').pack_start(self.filesys_combo, True, False, 0)
        self.filesys_combo.show()
        self.filesys_combo.append_text(self.fs.name)
        for filesys in self.filesystems:
            if (self.fs.name != filesys) and self.filesystems[filesys].creatable:
                self.filesys_combo.append_text(filesys)
        model = self.filesys_combo.get_model()
        iter = model.get_iter_first()
        self.filesys_combo.set_active_iter(iter)
        self.filesys_show_hide()
        if self.snapshot:
            self.glade_xml.get_object('filesys_container').set_sensitive(False)
        elif not self.new:
            if self.lv.is_snapshot():
                self.glade_xml.get_object('filesys_container').set_sensitive(False)
        self.mountpoint_entry = self.glade_xml.get_object('mount_point')
        if self.new:
            self.mountpoint_entry.set_text('')
        else:
            self.mountpoint_entry.set_text(self.mount_point)
        self.glade_xml.get_object('mount').set_active(self.mount)
        self.glade_xml.get_object('mount_at_reboot').set_active(self.mount_at_reboot)
        self.on_mount_changed(None)
        
        # size
        self.size_scale = self.glade_xml.get_object('size_scale')
        self.size_entry = self.glade_xml.get_object('size_entry')
        self.glade_xml.get_object('size_units_container').remove(self.size_units_combo)
        self.size_units_combo = Gtk.ComboBoxText()
        self.glade_xml.get_object('size_units_container').pack_end(self.size_units_combo, True, False, 0)
        self.size_units_combo.show()
        for unit in [EXTENTS, GIGABYTES, MEGABYTES, KILOBYTES]:
            self.size_units_combo.append_text(unit)
        model = self.size_units_combo.get_model()

        # set active item in combo box 
        iter = model.get_iter_first()
        active_iter = iter
        while (iter != None):
            if model.get_value(iter, 0) == GIGABYTES:
                active_iter = iter
            iter = model.iter_next(iter)
        
        self.size_units_combo.set_active_iter(active_iter)
        self.extent_size = self.vg.get_extent_size()
        self.size_lower = 1
        if self.new:
            self.size = 0
        else:
            self.size = self.lv.get_extent_total_used_free()[0]
        self.size_upper = self.vg.get_extent_total_used_free()[2] + self.size
        self.set_size_new(self.size)
        self.update_size_limits()
        self.change_size_units()
        
        # mirroring
        if self.new:
            self.mirror_to_diff_hds = None # prompt for option
            self.glade_xml.get_object('enable_mirroring').set_active(False)
        else:
            already_mirrored = self.lv.is_mirrored()
            if already_mirrored:
                self.mirror_to_diff_hds = False # mirror not resizable => don't care for now
            else:
                self.mirror_to_diff_hds = None # prompt for option
            self.glade_xml.get_object('enable_mirroring').set_active(already_mirrored)
        self.mirror_to_diff_hds = False
        if MIRRORING_UI_SUPPORT == False:
            if self.new:
                self.glade_xml.get_object('enable_mirroring').hide()
            else:
                self.glade_xml.get_object('lv_properties_frame').hide()
        
        # set up mirror limits
        self.on_enable_mirroring(None)
        
        # events
        self.fs_config_button.connect('clicked', self.on_fs_config)
        self.filesys_combo.connect('changed', self.on_fs_change)
        self.size_units_combo.connect('changed', self.on_units_change)
        self.size_scale.connect('adjust-bounds', self.on_size_change_scale)
        self.size_entry.connect('focus-out-event', self.on_size_change_entry)
        self.glade_xml.get_object('linear').connect('clicked', self.on_linear_changed)
        self.glade_xml.get_object('enable_mirroring').connect('clicked', self.on_enable_mirroring)
        self.glade_xml.get_object('striped').connect('clicked', self.on_striped_changed)
        self.glade_xml.get_object('mount').connect('clicked', self.on_mount_changed)
        self.glade_xml.get_object('mount_at_reboot').connect('clicked', self.on_mount_changed)
        self.glade_xml.get_object('use_remaining_button').connect('clicked', self.on_use_remaining)
        
    
    def on_linear_changed(self, obj):
        if self.glade_xml.get_object('linear').get_active() == False:
            self.glade_xml.get_object('enable_mirroring').set_active(False)
            self.glade_xml.get_object('enable_mirroring').set_sensitive(False)
            return
        else:
            self.glade_xml.get_object('stripes_container').set_sensitive(False)
            self.glade_xml.get_object('enable_mirroring').set_sensitive(True)
    def on_striped_changed(self, obj):
        if self.glade_xml.get_object('striped').get_active() == False:
            return
        pv_list = self.vg.get_pvs()
        if len(pv_list) < 2:  #striping is not an option
            self.errorMessage(CANT_STRIPE_MESSAGE)
            self.glade_xml.get_object('linear').set_active(True)
            return
        else:
            self.glade_xml.get_object('stripes_container').set_sensitive(True)
    def on_enable_mirroring(self, obj):
        if self.glade_xml.get_object('enable_mirroring').get_active() == False:
            self.update_size_limits()
            return
        # is mirroring supported by lvm version in use?
        if self.model_factory.is_mirroring_supported() == False:
            self.errorMessage(_("Underlying Logical Volume Management does not support mirroring"))
            self.glade_xml.get_object('enable_mirroring').set_active(False)
            self.update_size_limits()
            return
        # check if lv is striped - no mirroring
        if not self.new:
            if self.lv.is_striped():
                self.errorMessage(_("Striped Logical Volumes cannot be mirrored."))
                self.glade_xml.get_object('enable_mirroring').set_active(False)
                self.update_size_limits()
                return
        # check if lv is origin - no mirroring
        if not self.new:
            if self.lv.has_snapshots() and not self.lv.is_mirrored():
                self.errorMessage(_("Logical Volumes with associated snapshots cannot be mirrored yet."))
                self.glade_xml.get_object('enable_mirroring').set_active(False)
                self.update_size_limits()
                return
        
        # mirror images placement: diff HDs or anywhere
        if self.mirror_to_diff_hds == None: # prompt
            rc = self.questionMessage(_("The primary purpose of mirroring is to protect data in the case of hard drive failure. Do you want to place mirror images onto different hard drives?"))
            if rc == Gtk.ResponseType.YES:
                self.mirror_to_diff_hds = True
            else:
                self.mirror_to_diff_hds = False
        
        max_mirror_size = self.__get_max_mirror_data(self.vg)[0]
        if max_mirror_size == 0:
            if self.mirror_to_diff_hds:
                self.errorMessage(_("Less than 3 hard drives are available with free space. Disabling mirroring."))
                self.glade_xml.get_object('enable_mirroring').set_active(False)
                self.update_size_limits()
                return
            else:
                self.errorMessage(_("There must be free space on at least three Physical Volumes to enable mirroring"))
                self.glade_xml.get_object('enable_mirroring').set_active(False)
                self.update_size_limits()
                return
        
        if self.size_new > max_mirror_size:
            if self.new:
                self.update_size_limits(max_mirror_size)
                self.infoMessage(_("The size of the Logical Volume has been adjusted to the maximum available size for mirrors."))
                self.size_entry.select_region(0, (-1))
                self.size_entry.grab_focus()
            else:
                if self.lv.is_mirrored() == False:
                    message = _("There is not enough free space to add mirroring. Reduce size of Logical Volume to at most %s, or add Physical Volumes.")
                    iter = self.size_units_combo.get_active_iter()
                    units = self.size_units_combo.get_model().get_value(iter, 0)
                    reduce_to_string = str(self.__get_num(max_mirror_size)) + ' ' + units
                    self.errorMessage(message % reduce_to_string)
                    self.glade_xml.get_object('enable_mirroring').set_active(False)
                    self.size_entry.select_region(0, (-1))
                    self.size_entry.grab_focus()
                else:
                    self.update_size_limits()
        else:
            self.update_size_limits(max_mirror_size)
    
    def __get_max_mirror_data(self, vg):
        # copy pvs into list
        free_list = []
        for pv in list(vg.get_pvs().values()):
            free_extents = pv.get_extent_total_used_free()[2]
            # add extents of current LV
            if not self.new:
                if self.lv.is_mirrored():
                    lvs_to_match = self.lv.get_segments()[0].get_images()
                else:
                    lvs_to_match = [self.lv]
                for ext in pv.get_extent_blocks():
                    if ext.get_lv() in lvs_to_match:
                        free_extents = free_extents + ext.get_start_size()[1]
            if free_extents != 0:
                free_list.append((free_extents, pv))
        
        if self.mirror_to_diff_hds:
            ## place mirror onto different hds ##
            # group pvs into hd groups
            devices = {}
            for t in free_list:
                pv = t[1]
                pv_free = t[0]
                device_name_in_list = None
                for devname in pv.getDevnames():
                    if devname in list(devices.keys()):
                        device_name_in_list = devname
                if device_name_in_list == None:
                    if len(pv.getDevnames()) == 0:
                        # no known devnmaes
                        devices[pv.get_path()] = [pv_free, [[pv_free, pv]]]
                    else:
                        # not in the list
                        devices[pv.getDevnames()[0]] = [pv_free, [[pv_free, pv]]]
                else:
                    devices[device_name_in_list][0] = devices[device_name_in_list][0] + pv_free
                    devices[device_name_in_list][1].append([pv_free, pv])
            free_list = list(devices.values())
            if len(list(devices.keys())) < 3:
                return 0, [], [], []
            # sort free_list
            for i in range(len(free_list) - 1, 0, -1):
                for j in range(0, i):
                    if free_list[j][0] < free_list[j + 1][0]:
                        tmp = free_list[j + 1]
                        free_list[j + 1] = free_list[j]
                        free_list[j] = tmp
            # sort within free_list
            for t in free_list:
                sort_me = t[1]
                for i in range(len(sort_me) - 1, 0, -1):
                    for j in range(0, i):
                        if sort_me[j][0] < sort_me[j + 1][0]:
                            tmp = sort_me[j + 1]
                            sort_me[j + 1] = sort_me[j]
                            sort_me[j] = tmp
            # create list of largest partitions
            largest_list = []
            for t in free_list:
                t_largest_size = t[1][0][0]
                t_largest_pv = t[1][0][1]
                largest_list.append([t_largest_size, t_largest_pv])
            # sort largest list
            for i in range(len(largest_list) - 1, 0, -1):
                for j in range(0, i):
                    if largest_list[j][0] < largest_list[j + 1][0]:
                        tmp = largest_list[j + 1]
                        largest_list[j + 1] = largest_list[j]
                        largest_list[j] = tmp
            return largest_list[1][0], [largest_list[0][1]], [largest_list[1][1]], [largest_list.pop()[1]]
        else:
            ## place mirror anywhere, even on the same hd :( ##
            if len(free_list) < 3:
                return 0, [], [], []
            # sort
            for i in range(len(free_list) - 1, 0, -1):
                for j in range(0, i):
                    if free_list[j][0] < free_list[j + 1][0]:
                        tmp = free_list[j + 1]
                        free_list[j + 1] = free_list[j]
                        free_list[j] = tmp
            # remove smallest one for log
            log = free_list.pop()[1]
            
            # place pvs into buckets of similar size
            buck1, s1 = [free_list[0][1]], free_list[0][0]
            buck2, s2 = [free_list[1][1]], free_list[1][0]
            for t in free_list[2:]:
                if s1 < s2:
                    s1 = s1 + t[0]
                    buck1.append(t[1])
                else:
                    s2 = s2 + t[0]
                    buck2.append(t[1])
            
            max_m_size = 0
            if s1 < s2:
                max_m_size = s1
            else:
                max_m_size = s2
            
            return max_m_size, buck1, buck2, [log]
        
    def on_mount_changed(self, obj):
        m1 = self.glade_xml.get_object('mount').get_active()
        m2 = self.glade_xml.get_object('mount_at_reboot').get_active()
        if m1 or m2:
            self.mountpoint_entry.set_sensitive(True)
        else:
            self.mountpoint_entry.set_sensitive(False)
    
    def on_fs_config(self, button):
        pass
    
    def on_fs_change(self, obj):
        self.filesys_show_hide()
        # go thru on_enable_mirroring() to get to update_size_limits,
        # that in turn disables resizing if fs doesn't support that
        self.on_enable_mirroring(None)
    
    def filesys_show_hide(self):
        iter = self.filesys_combo.get_active_iter()
        filesys = self.filesystems[self.filesys_combo.get_model().get_value(iter, 0)]
        
        if filesys.editable:
            self.fs_config_button.set_sensitive(True)
        else:
            self.fs_config_button.set_sensitive(False)
        
        if filesys.mountable:
            self.glade_xml.get_object('mountpoint_container').set_sensitive(True)
            self.glade_xml.get_object('mount_container').set_sensitive(True)
        else:
            self.glade_xml.get_object('mount').set_active(False)
            self.glade_xml.get_object('mount_at_reboot').set_active(False)
            self.glade_xml.get_object('mountpoint_container').set_sensitive(False)
            self.glade_xml.get_object('mount_container').set_sensitive(False)
        
    
    def update_size_limits(self, upper=None):
        iter = self.filesys_combo.get_active_iter()
        filesys = self.filesystems[self.filesys_combo.get_model().get_value(iter, 0)]
        fs_resizable = (filesys.extendable_online or filesys.extendable_offline or filesys.reducible_online or filesys.reducible_offline)
        
        if not self.new:
            if fs_resizable:
                self.glade_xml.get_object('fs_not_resizable').hide()
            else:
                self.glade_xml.get_object('fs_not_resizable').show()
            
            if self.lv.has_snapshots():
                self.glade_xml.get_object('origin_not_resizable').show()
                self.glade_xml.get_object('free_space_label').hide()
                self.size_scale.set_sensitive(False)
                self.size_entry.set_sensitive(False)
                self.glade_xml.get_object('use_remaining_button').set_sensitive(False)
                self.glade_xml.get_object('remaining_space_label').hide()
                return
            elif self.lv.is_mirrored():
                if self.glade_xml.get_object('enable_mirroring').get_active():
                    self.glade_xml.get_object('mirror_not_resizable').show()
                    self.glade_xml.get_object('free_space_label').hide()
                    self.size_scale.set_sensitive(False)
                    self.size_entry.set_sensitive(False)
                    self.glade_xml.get_object('use_remaining_button').set_sensitive(False)
                    self.glade_xml.get_object('remaining_space_label').hide()
                    self.set_size_new(self.size)
                    return
                else:
                    self.glade_xml.get_object('mirror_not_resizable').hide()
                    self.glade_xml.get_object('free_space_label').show()
                    self.size_scale.set_sensitive(True)
                    self.size_entry.set_sensitive(True)
                    self.glade_xml.get_object('use_remaining_button').set_sensitive(True)
                    self.glade_xml.get_object('remaining_space_label').show()
        
        self.size_lower = 1
        if upper == None:
            self.size_upper = self.vg.get_extent_total_used_free()[2] + self.size
        else:
            self.size_upper = upper
        
        as_new = self.new
        fs_change = not (filesys == self.fs)
        if fs_change:
            as_new = True
        
        if as_new:
            self.glade_xml.get_object('fs_not_resizable').hide()
            self.glade_xml.get_object('free_space_label').show()
            self.size_scale.set_sensitive(True)
            self.size_entry.set_sensitive(True)
            self.glade_xml.get_object('use_remaining_button').set_sensitive(True)
            self.glade_xml.get_object('remaining_space_label').show()
        else:
            if not (filesys.extendable_online or filesys.extendable_offline):
                self.size_upper = self.size
            if not (filesys.reducible_online or filesys.reducible_offline):
                self.size_lower = self.size
            
            if fs_resizable:
                self.glade_xml.get_object('fs_not_resizable').hide()
                self.glade_xml.get_object('free_space_label').show()
                self.size_scale.set_sensitive(True)
                self.size_entry.set_sensitive(True)
                self.glade_xml.get_object('use_remaining_button').set_sensitive(True)
                self.glade_xml.get_object('remaining_space_label').show()
            else:
                self.glade_xml.get_object('fs_not_resizable').show()
                self.glade_xml.get_object('free_space_label').hide()
                self.size_scale.set_sensitive(False)
                self.size_entry.set_sensitive(False)
                self.glade_xml.get_object('use_remaining_button').set_sensitive(False)
                self.glade_xml.get_object('remaining_space_label').hide()
                
                # set old size value
                self.set_size_new(self.size)
                
        if self.size_lower < self.size_upper:
            self.glade_xml.get_object('size_scale_container').set_sensitive(True)
        else:
            self.glade_xml.get_object('size_scale_container').set_sensitive(False)
        
        # update values to be within limits
        self.change_size_units()
        self.set_size_new(self.size_new)
    
    def on_units_change(self, obj):
        self.change_size_units()
    
    def change_size_units(self):
        lower = self.__get_num(self.size_lower)
        upper = self.__get_num(self.size_upper)
        
        size_beg_label = self.glade_xml.get_object('size_beg')
        size_beg_label.set_text(str(lower))
        size_end_label = self.glade_xml.get_object('size_end')
        size_end_label.set_text(str(upper))
        
        if self.size_lower < self.size_upper:
            self.size_scale.set_range(lower, upper)
        
        self.set_size_new(self.size_new)
    
    def update_remaining_space_label(self):
        iter = self.size_units_combo.get_active_iter()
        units = self.size_units_combo.get_model().get_value(iter, 0)
        rem = self.size_upper - self.size_new
        rem_vg = self.vg.get_extent_total_used_free()[2]
        if self.glade_xml.get_object('enable_mirroring').get_active():
            mirror_log_size = 1
            rem_vg = rem_vg + (self.size - self.size_new) * 2 - mirror_log_size
        else:
            rem_vg = rem_vg - self.size_new + self.size
        string_vg = REMAINING_SPACE_VG + str(self.__get_num(rem_vg)) + ' ' + units
        self.glade_xml.get_object('free_space_label').set_text(string_vg)
        string = REMAINING_SPACE_AFTER + str(self.__get_num(rem)) + ' ' + units
        self.glade_xml.get_object('remaining_space_label').set_text(string)
    
    def on_use_remaining(self, obj):
        self.set_size_new(self.size_upper)
    
    def on_size_change_scale(self, obj1, obj2):
        size = self.size_scale.get_value()
        self.set_size_new(self.__get_extents(size))
    
    def on_size_change_entry(self, obj1, obj2):
        size_text = self.size_entry.get_text()
        size_float = 0.0
        try:  ##In case gibberish is entered into the size field...
            size_float = float(size_text)
        except ValueError as e:
            self.size_entry.set_text(str(self.__get_num(self.size_new)))
            return False
        self.set_size_new(self.__get_extents(size_float))
        return False
    def set_size_new(self, exts):
        size = exts
        if size > self.size_upper:
            size = self.size_upper
        elif size < self.size_lower:
            size = self.size_lower
        self.size_new = size
        size_units = self.__get_num(size)
        self.size_entry.set_text(str(size_units))
        self.size_scale.set_value(size_units)
        self.update_remaining_space_label()
    def __get_extents(self, num):
        iter = self.size_units_combo.get_active_iter()
        units = self.size_units_combo.get_model().get_value(iter, 0)
        if units == EXTENTS:
            return int(num)
        elif units == GIGABYTES:
            num = int(num * 1024 * 1024 * 1024 / self.extent_size)
        elif units == MEGABYTES:
            num = int(num * 1024 * 1024 / self.extent_size)
        elif units == KILOBYTES:
            num = int(num * 1024 / self.extent_size)
        if num < 1:
            num = 1
        return num
    def __get_num(self, extents):
        iter = self.size_units_combo.get_active_iter()
        units = self.size_units_combo.get_model().get_value(iter, 0)
        if units == EXTENTS:
            return int(extents)
        elif units == GIGABYTES:
            val = extents * self.extent_size / 1024.0 / 1024.0 / 1024.0
        elif units == MEGABYTES:
            val = extents * self.extent_size / 1024.0 / 1024.0
        elif units == KILOBYTES:
            val = extents * self.extent_size / 1024.0
        string = '%.2f' % float(val)
        return float(string)
    
    def apply(self):
        name_new = self.name_entry.get_text().strip()
        size_new = int(self.size_new) # in extents
        
        iter = self.filesys_combo.get_active_iter()
        filesys_new = self.filesystems[self.filesys_combo.get_model().get_value(iter, 0)]
        
        if filesys_new.mountable:
            mount_new = self.glade_xml.get_object('mount').get_active()
            mount_at_reboot_new = self.glade_xml.get_object('mount_at_reboot').get_active()
            mountpoint_new = self.mountpoint_entry.get_text().strip()
        else:
            mount_new = False
            mount_at_reboot_new = False 
            mountpoint_new = ''
        force_create = self.glade_xml.get_object('force_create').get_active()
        mirrored_new = self.glade_xml.get_object('enable_mirroring').get_active()
        striped = self.glade_xml.get_object('striped').get_active()
        stripe_size_combo = self.glade_xml.get_object('stripe_size')
        iter = stripe_size_combo.get_active_iter()
        stripe_size = int(stripe_size_combo.get_model().get_value(iter, 0))
        stripes_num = int(self.glade_xml.get_object('stripes_num').get_value_as_int())
        
        # TODO
        fs_options_changed = False
        
        
        # validation Ladder
        # name
        if name_new == '':
            self.errorMessage(MUST_PROVIDE_NAME)
            return False
        # illegal characters
        invalid_lvname_message = ''
        if re.match('snapshot', name_new) or re.match('pvmove', name_new):
            invalid_lvname_message = _("Names beginning with \"snapshot\" or \"pvmove\" are reserved keywords.")
        elif re.search('_mlog', name_new) or re.search('_mimage', name_new):
            invalid_lvname_message = _("Names containing \"_mlog\" or \"_mimage\" are reserved keywords.")
        elif name_new[0] == '-':
            invalid_lvname_message = _("Names beginning with a \"-\" are invalid")
        elif name_new == '.' or name_new == '..':
            invalid_lvname_message = _("Name can be neither \".\" nor \"..\"")
        else:
            for t in name_new:
                if t in string.ascii_letters + string.digits + '._-+':
                    continue
                elif t in string.whitespace:
                    invalid_lvname_message = _("Whitespaces are not allowed in Logical Volume names")
                    break
                else:
                    invalid_lvname_message = _("Invalid character \"%s\" in Logical Volume name") % t
                    break
        if invalid_lvname_message != '':
            self.errorMessage(invalid_lvname_message)
            self.name_entry.select_region(0, (-1))
            self.name_entry.grab_focus()
            return False
        # Name must be unique for this VG
        for lv in list(self.vg.get_lvs().values()):
            if lv.get_name() == name_new:
                if not self.new:
                    if self.lv.get_name() == name_new:
                        continue
                self.name_entry.select_region(0, (-1))
                self.name_entry.grab_focus()
                self.errorMessage(NON_UNIQUE_NAME % name_new)
                return False
        # check mountpoint
        if mount_new or mount_at_reboot_new:
            if mountpoint_new == '':
                self.errorMessage(_("Please specify mount point"))
                return False
            # create folder if it doesn't exist
            if os.path.exists(mountpoint_new) == False:  ###stat mnt point
                rc = self.questionMessage(BAD_MNT_POINT % mountpoint_new)
                if (rc == Gtk.ResponseType.YES):  #create mount point
                    try:
                        os.mkdir(mountpoint_new)
                    except OSError as e:
                        self.errorMessage(BAD_MNT_CREATION % mountpoint_new)
                        self.mountpoint_entry.set_text('')
                        return False
                else:
                    self.mountpoint_entry.select_region(0, (-1))
                    return False
        
        # action
        if self.new:
            ### new LV ###
            
            # create LV
            new_lv_command_set = {}
            new_lv_command_set[NEW_LV_NAME_ARG] = name_new
            new_lv_command_set[NEW_LV_VGNAME_ARG] = self.vg.get_name()
            new_lv_command_set[NEW_LV_UNIT_ARG] = EXTENT_IDX
            new_lv_command_set[NEW_LV_SIZE_ARG] = size_new
            new_lv_command_set[NEW_LV_IS_STRIPED_ARG] = striped
            new_lv_command_set[NEW_LV_MIRRORING] = mirrored_new
            new_lv_command_set[NEW_LV_FORCE] = force_create
            if striped == True:
                new_lv_command_set[NEW_LV_STRIPE_SIZE_ARG] = stripe_size
                new_lv_command_set[NEW_LV_NUM_STRIPES_ARG] = stripes_num
            new_lv_command_set[NEW_LV_SNAPSHOT] = self.snapshot
            if self.snapshot:
                new_lv_command_set[NEW_LV_SNAPSHOT_ORIGIN] = self.lv.get_path()
            pvs_to_create_at = []
            if mirrored_new:
                size, b1, b2, l1 = self.__get_max_mirror_data(self.vg)
                pvs_to_create_at = b1[:]
                for pv in b2:
                    pvs_to_create_at.append(pv)
                for pv in l1:
                    pvs_to_create_at.append(pv)
            self.command_handler.new_lv(new_lv_command_set, pvs_to_create_at)
            
            lv_path = self.model_factory.get_logical_volume_path(name_new, self.vg.get_name())
            
            # make filesystem
            if not self.snapshot:
                try:
                    filesys_new.create(lv_path)
                except CommandError as e:
                    self.command_handler.remove_lv(lv_path)
                    raise e
            
            # mount
            if mount_new:
                self.command_handler.mount(lv_path, mountpoint_new, filesys_new.fsname)
            if mount_at_reboot_new:
                Fstab.add(None, lv_path, mountpoint_new, filesys_new.fsname)
        else:
            ### edit LV ###
            
            rename = name_new != self.lv.get_name()
            filesys_change = (filesys_new != self.fs)
            ext2_to_ext3 = (filesys_new.name == Filesystem.ext3().name) and (self.fs.name == Filesystem.ext2().name)
            if ext2_to_ext3:
                retval = self.questionMessage(_("Do you want to upgrade ext2 to ext3 preserving data on Logical Volume?"))
                if (retval == Gtk.ResponseType.NO):
                    ext2_to_ext3 = False
            
            snapshot = None
            if self.lv.is_snapshot():
                snapshot = self.lv.get_snapshot_info()[0]
            
            resize = (size_new != self.size)
            extend = (size_new > self.size)
            reduce = (size_new < self.size)
            
            # remove mirror if not needed anymore
            if self.lv.is_mirrored() and not mirrored_new:
                self.command_handler.remove_mirroring(self.lv.get_path())
            
            # DEBUGING: check if resizing is posible
            #if extend:
            #    if self.command_handler.extend_lv(self.lv.get_path(), size_new, True) == False:
            #        retval = self.infoMessage(_("fixme: resizing not possible"))
            #        return False
            #elif reduce:
            #    if self.command_handler.reduce_lv(self.lv.get_path(), size_new, True) == False:
            #        retval = self.infoMessage(_("fixme: resizing not possible"))
            #        return False
            
            mounted = self.mount
            unmount = False
            unmount_prompt = True
            if rename or filesys_change or mount_new == False:
                unmount = True
            if resize and self.lv.is_mirrored():
                unmount = True

            lv_open = False
            if len(self.lv.get_attr()) >= 6 and self.lv.get_attr()[5] == "o":
              lv_open = True

            if lv_open and mounted == False:
              ## LV is probably exported to another computer(s)
              retval = self.errorMessage(_("Logical volume is not mounted but is in use. Please close all applications using this device (eg iscsi)"))
              return False

            if filesys_change and self.fs.name!=self.fs_none.name and not ext2_to_ext3:
                retval = self.warningMessage(_("Changing the filesystem will destroy all data on the Logical Volume! Are you sure you want to proceed?"))
                if (retval == Gtk.ResponseType.NO):
                    return False
                unmount_prompt = False
            else:
                if not snapshot:
                    if extend and mounted and (not self.fs.extendable_online):
                        unmount = True
                    if reduce and mounted and (not self.fs.reducible_online):
                        unmount = True
            
            # unmount if needed
            if unmount and mounted:
                if unmount_prompt:
                    retval = self.warningMessage(UNMOUNT_PROMPT % (self.lv.get_path(), self.mount_point))
                    if (retval == Gtk.ResponseType.NO):
                        return False
                self.command_handler.unmount(self.mount_point)
                mounted = False
            
            # rename
            if rename:
                self.command_handler.rename_lv(self.vg.get_name(), self.lv.get_name(), name_new)
            lv_path = self.model_factory.get_logical_volume_path(name_new, self.vg.get_name())
            lv_path_old = self.lv.get_path()
            
            # resize lv
            if resize:
                if (filesys_change and not ext2_to_ext3) or snapshot:
                    # resize LV only
                    if size_new > self.size:
                        self.command_handler.extend_lv(lv_path, size_new)
                    else:
                        self.command_handler.reduce_lv(lv_path, size_new)
                else:
                    # resize lv and filesystem
                    if size_new > self.size:
                        # resize LV first
                        self.command_handler.extend_lv(lv_path, size_new)
                        # resize FS
                        try:
                            if mounted:
                                if self.fs.extendable_online:
                                    self.fs.extend_online(lv_path)
                                else:
                                    self.command_handler.unmount(self.mount_point)
                                    mounted = False
                                    self.fs.extend_offline(lv_path)
                            else:
                                if self.fs.extendable_offline:
                                    self.fs.extend_offline(lv_path)
                                else:
                                    # mount temporarily
                                    tmp_mountpoint = '/tmp/tmp_mountpoint'
                                    while os.access(tmp_mountpoint, os.F_OK):
                                        tmp_mountpoint = tmp_mountpoint + '1'
                                    os.mkdir(tmp_mountpoint)
                                    self.command_handler.mount(lv_path, tmp_mountpoint, Filesystem.get_fs(lv_path).fsname)
                                    self.fs.extend_online(lv_path)
                                    self.command_handler.unmount(tmp_mountpoint)
                                    os.rmdir(tmp_mountpoint)
                        except:
                            # revert LV size
                            self.command_handler.reduce_lv(lv_path, self.size)
                            raise
                    else:
                        # resize FS first
                        new_size_bytes = size_new * self.extent_size
                        if mounted:
                            if self.fs.reducible_online:
                                self.fs.reduce_online(lv_path, new_size_bytes)
                            else:
                                self.command_handler.unmount(self.mount_point)
                                mounted = False
                                self.fs.reduce_offline(lv_path, new_size_bytes)
                        else:
                            if self.fs.reducible_offline:
                                self.fs.reduce_offline(lv_path, new_size_bytes)
                            else:
                                # mount temporarily
                                tmp_mountpoint = '/tmp/tmp_mountpoint'
                                while os.access(tmp_mountpoint, os.F_OK):
                                    tmp_mountpoint = tmp_mountpoint + '1'
                                os.mkdir(tmp_mountpoint)
                                self.command_handler.mount(lv_path, tmp_mountpoint)
                                self.fs.reduce_online(lv_path, new_size_bytes)
                                self.command_handler.unmount(tmp_mountpoint)
                                os.rmdir(tmp_mountpoint)
                        # resize LV
                        self.command_handler.reduce_lv(lv_path, size_new)
            
            
            # add mirror if needed
            if not self.lv.is_mirrored() and mirrored_new:
                # first reload lvm_data so that resizing info is known
                self.model_factory.reload()
                self.lv = self.model_factory.get_VG(self.lv.get_vg().get_name()).get_lvs()[name_new]
                # make room for mirror (free some pvs of main image's extents)
                pvlist_from_make_room = self.__make_room_for_mirror(self.lv)
                if pvlist_from_make_room == None:
                    # migration not performed, continue process with no mirroring
                    self.infoMessage(_("Mirror not created. Completing remaining tasks."))
                else:
                    # create mirror
                    self.infoMessage(_('Underlaying LVM doesn\'t support addition of mirrors to existing Logical Volumes. Completing remaining tasks.'))
                    #self.command_handler.add_mirroring(self.lv.get_path(), pvlist_from_make_room)
                    pass
            
            # fs options
            if fs_options_changed and not filesys_change:
                self.fs.change_options(lv_path)
            
            # change FS
            if filesys_change:
                if ext2_to_ext3:
                    self.fs.upgrade(lv_path)
                else:
                    filesys_new.create(lv_path)
            
            # mount
            fsname = self.fs.fsname
            if filesys_change:
                fsname = filesys_new.fsname
            if mount_new and not mounted:
                self.command_handler.mount(lv_path, mountpoint_new, fsname)
            fstab_op = Fstab.get_mount_options(lv_path_old)
            if mount_at_reboot_new:
                # Add new entry; if mount_at_reboot was not set before
                # then all fstab_op[] will be None, so default options
                # should be set
                if (fstab_op[Fstab.OPTIONS] != None):
                    Fstab.add(lv_path_old, lv_path, mountpoint_new, fsname, fstab_op[Fstab.OPTIONS], fstab_op[Fstab.DUMP], fstab_op[Fstab.FSCK])
                else:
                    Fstab.add(lv_path_old, lv_path, mountpoint_new, fsname)
            else:
              Fstab.remove(lv_path_old)
                
        return True
    
    # return list of pvs to use for mirror, or None on failure
    def __make_room_for_mirror(self, lv):
        t, bucket1, bucket2, logs = self.__get_max_mirror_data(lv.get_vg())
        return_pvlist = bucket1[:]
        for pv in bucket2:
            return_pvlist.append(pv)
        for pv in logs:
            return_pvlist.append(pv)
        
        structs = self.__get_structs_for_ext_migration(lv)
        if len(structs) == 0:
            # nothing to be migrated
            return return_pvlist
        
        # extents need moving :(
        string = ''
        for struct in structs:
            string = string + '\n' + struct[0].get_path()
            string = string + ':' + str(struct[1]) + '-' + str(struct[1] + struct[2] - 1)
            string = string + '   -> ' + struct[3].get_path()
        rc = self.questionMessage(_("In order to add mirroring, some extents need to be migrated.") + '\n' + string + '\n' + _("Do you want to migrate specified extents?"))
        if rc == Gtk.ResponseType.YES:
            for struct in structs:
                pv_from = struct[0]
                ext_start = struct[1]
                size = struct[2]
                pv_to = struct[3]
                self.command_handler.move_pv(pv_from.get_path(), 
                                             [(ext_start, size)],
                                             [pv_to.get_path(), None, lv.get_path()])
            return return_pvlist
        else:
            return None
    # return [[pv_from, ext_start, size, pv_to], ...]
    def __get_structs_for_ext_migration(self, lv):
        t, bucket1, bucket2, logs = self.__get_max_mirror_data(lv.get_vg())
        
        # pick bucket to move lv to
        if self.__get_extent_count_in_bucket(lv, bucket1) < self.__get_extent_count_in_bucket(lv, bucket2):
            bucket_to = bucket2
        else:
            bucket_to = bucket1
        bucket_from = []
        for pv in list(lv.get_vg().get_pvs().values()):
            if pv not in bucket_to:
                bucket_from.append(pv)
        
        structs = []
        bucket_to_i = 0
        pv_to = bucket_to[bucket_to_i]
        free_exts = pv_to.get_extent_total_used_free()[2]
        for pv_from in bucket_from:
            for ext_block in pv_from.get_extent_blocks():
                if ext_block.get_lv() != lv:
                    continue
                block_start, block_size = ext_block.get_start_size()
                while block_size != 0:
                    if block_size >= free_exts:
                        structs.append([pv_from, block_start, free_exts, pv_to])
                        block_start = block_start + free_exts
                        block_size = block_size - free_exts
                        # get next pv_to from bucket_to
                        bucket_to_i = bucket_to_i + 1
                        if bucket_to_i == len(bucket_to):
                            # should be done
                            return structs
                        pv_to = bucket_to[bucket_to_i]
                        free_exts = pv_to.get_extent_total_used_free()[2]
                    else:
                        structs.append([pv_from, block_start, block_size, pv_to])
                        block_start = block_start + block_size
                        block_size = block_size - block_size
                        free_exts = free_exts - block_size
        return structs
    
    def __get_extent_count_in_bucket(self, lv, bucket_pvs):
        ext_count = 0
        for pv in bucket_pvs:
            for ext_block in pv.get_extent_blocks():
                if ext_block.get_lv() == lv:
                    ext_count = ext_count + ext_block.get_start_size()[1]
        return ext_count
    
    def errorMessage(self, message):
        dlg = Gtk.MessageDialog(None, 0,
                                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                message)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()
        return rc
    
    def infoMessage(self, message):
        dlg = Gtk.MessageDialog(None, 0,
                                Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                                message)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()
        return rc
    
    def questionMessage(self, message):
        dlg = Gtk.MessageDialog(None, 0,
                                Gtk.MessageType.INFO, Gtk.ButtonsType.YES_NO,
                                message)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()
        if (rc == Gtk.ResponseType.NO):
            return Gtk.ResponseType.NO
        elif (rc == Gtk.ResponseType.DELETE_EVENT):
            return Gtk.ResponseType.NO
        elif (rc == Gtk.ResponseType.CLOSE):
            return Gtk.ResponseType.NO
        elif (rc == Gtk.ResponseType.CANCEL):
            return Gtk.ResponseType.NO
        else:
            return rc
    
    def warningMessage(self, message):
        dlg = gtk.MessageDialog(None, 0,
                                Gtk.MessageType.WARNING, Gtk.ButtonsType.YES_NO,
                                message)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()
        if (rc == Gtk.ResponseType.NO):
            return Gtk.ResponseType.NO
        elif (rc == Gtk.ResponseType.DELETE_EVENT):
            return Gtk.ResponseType.NO
        elif (rc == Gtk.ResponseType.CLOSE):
            return Gtk.ResponseType.NO
        elif (rc == Gtk.ResponseType.CANCEL):
            return Gtk.ResponseType.NO
        else:
            return rc

        
