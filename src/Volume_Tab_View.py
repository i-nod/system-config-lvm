import sys
import types
import select
import math
import operator
import signal
import string
import os
from renderer import DisplayView
from Properties_Renderer import Properties_Renderer
from lvm_model import lvm_model
from InputController import InputController
from lvmui_constants import *
from WaitMsg import WaitMsg
from execute import ForkedCommand, execWithCapture



import stat
import gettext
_ = gettext.gettext

### gettext first, then import gtk (exception prints gettext "_") ###
try:
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


VOLUME_GROUPS=_("Volume Groups")
UNALLOCATED_VOLUMES=_("Unallocated Volumes")
UNINITIALIZED_ENTITIES=_("Uninitialized Entities")
PHYSICAL_VIEW=_("Physical View")
LOGICAL_VIEW=_("Logical View")

MAX_LV_FOR_BESTFIT = 100
                                                                                
#############################################################
class Volume_Tab_View:
  def __init__(self, glade_xml, model_factory, app):
                                                                                
    self.model_factory = model_factory
    
    self.main_win = app
    self.width = 0
    self.height = 0
    self.glade_xml = glade_xml

    self.try_not_best_fit = True

    ##Set up list structure
    self.treeview = self.glade_xml.get_object('treeview1')
    self.treemodel = self.treeview.get_model()
    self.treemodel = Gtk.TreeStore (GObject.TYPE_STRING,
                                    GObject.TYPE_INT,
                                    GObject.TYPE_STRING,
                                    GObject.TYPE_STRING,
                                    GObject.TYPE_PYOBJECT)
    self.treeview.set_model(self.treemodel)
    self.treeview.set_headers_visible(False)
    
    self.input_controller = InputController(self.reset_tree_model,
                                            self.treeview, 
                                            self.model_factory, 
                                            self.glade_xml)
    
    #Change Listener
    selection = self.treeview.get_selection()
    selection.connect('changed', self.on_tree_selection_changed)
    
    #self.treeview.connect('expand-collapse-cursor-row',self.on_row_expand_collapse)
    #self.treeview.connect('row-collapsed',self.on_row_expand_collapse)
    
    self.icon_ellipse_hashtable = {}
    
    renderer1 = Gtk.CellRendererText()
    column1 = Gtk.TreeViewColumn("Volumes",renderer1,markup=0)
    self.treeview.append_column(column1)
    
    
    #Time to set up draw area
    window1 = self.glade_xml.get_object("drawingarea1")
    window1.set_size_request(700, 500)
    window2 = self.glade_xml.get_object("drawingarea2")
    window2.set_size_request(700, 500)
    window3 = self.glade_xml.get_object("drawingarea3")
    window3.set_size_request(700, 500)
    window4 = self.glade_xml.get_object("drawingarea4")
    window4.set_size_request(700, 500)
    
    pr_upper = Properties_Renderer(window3, window3.get_toplevel())
    #pr_lower = Properties_Renderer(window4, window4.window)
    self.display_view = DisplayView(self.input_controller.register_highlighted_sections, window1, pr_upper, None, None)
    #self.display_view = DisplayView(self.input_controller.register_highlighted_sections, window1, pr_upper, window2, pr_lower)
    
    self.glade_xml.get_object('best_fit_button').connect('clicked', self.on_best_fit)
    self.glade_xml.get_object('zoom_in_button').connect('clicked', self.on_zoom_in)
    self.glade_xml.get_object('zoom_out_button').connect('clicked', self.on_zoom_out)
    self.glade_xml.get_object('viewport1').connect('size-allocate', self.on_resize_drawing_area)
    self.on_best_fit(None)
    self.glade_xml.get_object('zoom_box').set_sensitive(False)
    
    # set up mirror copy progress
    self.mirror_sync_progress = MirrorSyncProgress(self.glade_xml.get_object('messages_vbox'))
    
    
    #############################
    ##Highly experimental
    self.box = self.glade_xml.get_object('vbox12')
    self.uninit_panel = self.glade_xml.get_object('uninit_panel')
    self.uninit_panel.hide()
    self.unalloc_panel = self.glade_xml.get_object('unalloc_panel')
    self.unalloc_panel.hide()
    self.phys_vol_view_panel = self.glade_xml.get_object('phys_vol_view_panel')
    self.phys_vol_view_panel.hide()
    self.log_vol_view_panel = self.glade_xml.get_object('log_vol_view_panel')
    self.log_vol_view_panel.hide()
    self.on_rm_select_lvs_button = self.glade_xml.get_object('on_rm_select_lvs')
    self.phys_panel = self.glade_xml.get_object('phys_panel')
    self.phys_panel.hide()
    self.log_panel = self.glade_xml.get_object('log_panel')
    self.log_panel.hide()
    
    self.prepare_tree()
    model = self.treeview.get_model()
    vgs = self.model_factory.get_VGs()
    if len(vgs) > 0:
        model.foreach(self.check_tree_items, [list(vgs)[0].get_name()])
        
        lvs_count = 0
        for vg in vgs:
            lvs_count += len(vg.lvs)
        if (lvs_count < MAX_LV_FOR_BESTFIT):
            self.try_not_best_fit = False
        else:
            self.glade_xml.get_object('best_fit_button').set_sensitive(False)            
    else:
        unallocs = self.model_factory.query_unallocated()
        if len(unallocs) > 0:
            model.foreach(self.check_tree_items, ['', '', unallocs[0].get_path()])
        else:
            uninits = self.model_factory.query_uninitialized()
            if len(uninits) > 0:
                model.foreach(self.check_tree_items, ['', '', uninits[0].get_path()])
  
  # format is [vgname, lvpath, pvpath] - put '' if none
  def reset_tree_model(self, *in_args):
      self.prepare_tree()
      
      args = []
      for arg in in_args:
          args.append(arg)
      model = self.treeview.get_model()
      model.foreach(self.check_tree_items, args)
  
  def check_tree_items(self, model, path, iter, *args):
    # return True to stop foreach, False to continue
    
    if len(args) == 0:
        return True # don't go any further
    args_internal = []
    for arg in args[0]:
        args_internal.append(arg)
    while len(args_internal) < 3:
        args_internal.append('')
    vgname = args_internal[0]
    lvpath = args_internal[1]
    pvpath = args_internal[2]
    
    selection = self.treeview.get_selection()
    type = model.get_value(iter, TYPE_COL)
    if type == VG_PHYS_TYPE:
        if vgname != '' and lvpath == '' and pvpath != '':
            vg = model.get_value(iter, OBJ_COL)
            if vgname == vg.get_name():
                self.treeview.expand_to_path(path)
                selection.select_path(path)
                return True
    elif type == VG_LOG_TYPE:
        if vgname != '' and lvpath != '' and pvpath == '':
            vg = model.get_value(iter, OBJ_COL)
            if vgname == vg.get_name():
                self.treeview.expand_to_path(path)
                selection.select_path(path)
                return True
    elif type == VG_TYPE:
        if vgname != '' and lvpath == '' and pvpath == '':
            vg = model.get_value(iter, OBJ_COL)
            if vgname == vg.get_name():
                self.treeview.expand_to_path(path)
                selection.select_path(path)
                return True
    elif type == LOG_TYPE:
        if vgname == '' and lvpath != '' and pvpath == '':
            lv = model.get_value(iter, OBJ_COL)
            if lvpath == lv.get_path():
                self.treeview.expand_to_path(path)
                selection.select_path(path)
                return True
    elif type == PHYS_TYPE or type == UNALLOCATED_TYPE or type == UNINITIALIZED_TYPE:
        if vgname == '' and lvpath == '' and pvpath != '':
            pv = model.get_value(iter, OBJ_COL)
            if pvpath in pv.get_paths():
                self.treeview.expand_to_path(path)
                selection.select_path(path)
                return True
    return False

  def prepare_tree(self):
    treemodel = self.treeview.get_model()
    treemodel.clear()
    
    self.model_factory.reload()
    self.mirror_sync_progress.initiate()
    
    vg_list = self.model_factory.get_VGs()
    if len(vg_list) > 0:
        vg_iter = treemodel.append(None)
        vg_string = "<span size=\"11000\"><b>" + VOLUME_GROUPS + "</b></span>"
        treemodel.set(vg_iter,
                      NAME_COL, vg_string, 
                      TYPE_COL,
                      UNSELECTABLE_TYPE)
        self.__sort_list_by_get_name_fcn(vg_list)
        for vg in vg_list:
            vg_child_iter = treemodel.append(vg_iter)
            vg_name = vg.get_name()
            vg_name_marked = vg_name
            if vg.clustered():
                vg_name_marked += '<span foreground="#FF00FF">   (' + _('Clustered VG') + ')</span>'
            treemodel.set(vg_child_iter,
                          NAME_COL, vg_name_marked, 
                          TYPE_COL, VG_TYPE, 
                          OBJ_COL, vg)
            phys_iter = treemodel.append(vg_child_iter)
            log_iter = treemodel.append(vg_child_iter)
            pview_string = "<span foreground=\"#ED1C2A\"><i>  " + PHYSICAL_VIEW + "</i></span>"
            treemodel.set(phys_iter,
                          NAME_COL, pview_string,
                          TYPE_COL, VG_PHYS_TYPE,
                          PATH_COL, vg_name, 
                          OBJ_COL, vg)
            lview_string = "<span foreground=\"#43ACF6\"><i>  " + LOGICAL_VIEW + "</i></span>"
            treemodel.set(log_iter,
                          NAME_COL, lview_string,
                          TYPE_COL, VG_LOG_TYPE,
                          PATH_COL, vg_name, 
                          OBJ_COL, vg)
            
            pv_list = list(vg.get_pvs().values())
            grouped_dir, ungrouped_list = self.__group_by_device(pv_list)
            grouped_dir_sorted = list(grouped_dir.keys())
            grouped_dir_sorted.sort()
            for main_dev in grouped_dir_sorted:
                dev_iter = treemodel.append(phys_iter)
                pvs = grouped_dir[main_dev]
                devnames = pvs[0].getDevnames()
                devnames_str = devnames[0]
                for devname in devnames[1:]:
                    devnames_str = devnames_str + ', ' + devname
                if len(devnames) > 1:
                    devnames_str = str(pvs[0].getMultipath()) + ' [' + devnames_str + ']'
                treemodel.set(dev_iter, 
                              NAME_COL, devnames_str, 
                              TYPE_COL, UNSELECTABLE_TYPE)
                for pv in pvs:
                    iter = treemodel.append(dev_iter)
                    phys_string = "<span foreground=\"#ED1C2A\">" + pv.get_name() + "</span>"
                    treemodel.set(iter, 
                                  NAME_COL, phys_string, 
                                  TYPE_COL, PHYS_TYPE, 
                                  PATH_COL, pv.get_path(), 
                                  OBJ_COL, pv)
            for pv in ungrouped_list:
                iter = treemodel.append(phys_iter)
                phys_string = "<span foreground=\"#ED1C2A\">" + pv.get_name() + "</span>"
                treemodel.set(iter, 
                              NAME_COL, phys_string, 
                              TYPE_COL, PHYS_TYPE, 
                              PATH_COL, pv.get_path(), 
                              OBJ_COL, pv)
            
            lv_list = list(vg.get_lvs().values())
            self.__sort_list_by_get_name_fcn(lv_list)
            for lv in lv_list:
                if lv.is_used():
                    iter = treemodel.append(log_iter)
                    log_string = "<span foreground=\"#43ACF6\">" + lv.get_name() + "</span>"
                    treemodel.set(iter, 
                                  NAME_COL, log_string, 
                                  TYPE_COL, LOG_TYPE,
                                  PATH_COL, lv.get_path(),
                                  SIMPLE_LV_NAME_COL, lv.get_name(),
                                  OBJ_COL, lv)
            
            #Expand if there are entries 
            self.treeview.expand_row(treemodel.get_path(vg_iter),False)
            
    unalloc_list = self.model_factory.query_unallocated()
    if len(unalloc_list) > 0:
        unallocated_iter = treemodel.append(None)
        unalloc_string = "<span size=\"11000\"><b>" + UNALLOCATED_VOLUMES + "</b></span>"
        treemodel.set(unallocated_iter,
                      NAME_COL, unalloc_string, 
                      TYPE_COL, UNSELECTABLE_TYPE)
        grouped_dir, ungrouped_list = self.__group_by_device(unalloc_list)
        grouped_dir_sorted = list(grouped_dir.keys())
        grouped_dir_sorted.sort()
        for main_dev in grouped_dir_sorted:
            dev_iter = treemodel.append(unallocated_iter)
            pvs = grouped_dir[main_dev]
            devnames = pvs[0].getDevnames()
            devnames_str = devnames[0]
            for devname in devnames[1:]:
                devnames_str = devnames_str + ', ' + devname
            if len(devnames) > 1:
                devnames_str = str(pvs[0].getMultipath()) + ' [' + devnames_str + ']'
            treemodel.set(dev_iter, 
                          NAME_COL, devnames_str, 
                          TYPE_COL, UNSELECTABLE_TYPE)
            for pv in pvs:
                iter = treemodel.append(dev_iter)
                phys_string = "<span foreground=\"#ED1C2A\">" + pv.get_name() + "</span>"
                treemodel.set(iter, 
                              NAME_COL, phys_string, 
                              TYPE_COL, UNALLOCATED_TYPE, 
                              PATH_COL, pv.get_path(), 
                              OBJ_COL, pv)
        for pv in ungrouped_list:
            iter = treemodel.append(unallocated_iter)
            phys_string = "<span foreground=\"#ED1C2A\">" + pv.get_path() + "</span>"
            treemodel.set(iter, 
                          NAME_COL, phys_string, 
                          TYPE_COL, UNALLOCATED_TYPE, 
                          PATH_COL, pv.get_path(), 
                          OBJ_COL, pv)
    
    uninit_list = self.model_factory.query_uninitialized()
    if len(uninit_list) > 0:
        uninitialized_iter = treemodel.append(None)
        uninit_string = "<span size=\"11000\"><b>" + UNINITIALIZED_ENTITIES + "</b></span>"
        treemodel.set(uninitialized_iter, 
                      NAME_COL, uninit_string, 
                      TYPE_COL, UNSELECTABLE_TYPE)
        grouped_dir, ungrouped_list = self.__group_by_device(uninit_list)
        grouped_dir_sorted = list(grouped_dir.keys())
        grouped_dir_sorted.sort()
        for main_dev in grouped_dir_sorted:
            dev_iter = treemodel.append(uninitialized_iter)
            pvs = grouped_dir[main_dev]
            devnames = pvs[0].getDevnames()
            devnames_str = devnames[0]
            for devname in devnames[1:]:
                devnames_str = devnames_str + ', ' + devname
            if len(devnames) > 1:
                devnames_str = str(pvs[0].getMultipath()) + ' [' + devnames_str + ']'
            treemodel.set(dev_iter,
                          NAME_COL, devnames_str, 
                          TYPE_COL, UNSELECTABLE_TYPE)
            for pv in grouped_dir[main_dev]:
                iter = treemodel.append(dev_iter)
                treemodel.set(iter, 
                              NAME_COL, pv.get_name(), 
                              TYPE_COL, UNINITIALIZED_TYPE, 
                              PATH_COL, pv.get_path(), 
                              OBJ_COL, pv)
        for pv in ungrouped_list:
            iter = treemodel.append(uninitialized_iter)
            treemodel.set(iter, 
                          NAME_COL, pv.get_path(), 
                          TYPE_COL, UNINITIALIZED_TYPE, 
                          PATH_COL, pv.get_path(), 
                          OBJ_COL, pv)
    
    #self.treeview.expand_all()
    self.clear_all_buttonpanels()
  
  # returns {main_dev : [pv1, pv2, ...], ...}
  def __group_by_device(self, pvlist):
      grouped = {}
      ungrouped = []
      for pv in pvlist:
          if len(pv.getDevnames()) == 0 or pv.wholeDevice():
              ungrouped.append(pv)
              continue
          if pv.getDevnames()[0] in list(grouped.keys()):
              grouped[pv.getDevnames()[0]].append(pv)
          else:
              grouped[pv.getDevnames()[0]] = [pv]

      # sort lists
      for main_dev in grouped:
          self.__sort_list_by_get_name_fcn(grouped[main_dev])
      self.__sort_list_by_get_name_fcn(ungrouped)
      return grouped, ungrouped
  
  def __sort_list_by_get_name_fcn(self, some_list_dict):
      d = {}
      l = []
      some_list = list(some_list_dict)
      while len(some_list) != 0:
          o = some_list.pop()
          name = o.get_name()
          if name in d:
              d[name].append(o)
          else:
              d[name] = [o]
              l.append(name)
      l.sort()
      for name in l:
          for o in d[name]:
              some_list.append(o)
      return some_list
  
  def on_tree_selection_changed(self, *args):
    selection = self.treeview.get_selection()
    model,iter = selection.get_selected()
    if iter == None:
        self.glade_xml.get_object('zoom_box').set_sensitive(False)
        self.display_view.render_no_selection()
        self.display_view.queuedraw()
        return
    
    treepath = model.get_path(iter)
    self.treeview.expand_row(treepath, False)
    
    type = model.get_value(iter, TYPE_COL)
    if type == VG_PHYS_TYPE:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        self.phys_vol_view_panel.show()
        
        vg = model.get_value(iter, OBJ_COL)
        pv_list = list(vg.get_pvs().values())
        self.display_view.render_pvs(pv_list)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(True)
    elif type == VG_LOG_TYPE:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        
        vg = model.get_value(iter, OBJ_COL)
        lv_list = list(vg.get_lvs().values())
        self.show_log_vol_view_panel(lv_list)
        self.display_view.render_lvs(lv_list)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(True)
    elif type == VG_TYPE:
        self.clear_all_buttonpanels()
        self.input_controller.clear_highlighted_sections()
        
        vg = model.get_value(iter, OBJ_COL)
        self.display_view.render_vg(vg)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(True)
    elif type == LOG_TYPE:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        self.log_panel.show()
        
        lv = model.get_value(iter, OBJ_COL)
        self.display_view.render_lv(lv)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(False)
    elif type == PHYS_TYPE:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        self.phys_panel.show()
        
        pv = model.get_value(iter, OBJ_COL)
        self.display_view.render_pv(pv)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(True)
    elif type == UNALLOCATED_TYPE:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        self.unalloc_panel.show()
        
        pv = model.get_value(iter, OBJ_COL)
        self.display_view.render_unalloc_pv(pv)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(False)
    elif type == UNINITIALIZED_TYPE:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        button = self.input_controller.init_entity_button
        
        uv = model.get_value(iter, OBJ_COL)
        if uv.initializable:
            button.set_sensitive(True)
        else:
            button.set_sensitive(False)
        self.uninit_panel.show()
        self.display_view.render_uninit_pv(uv)
        self.on_best_fit(None)
        self.glade_xml.get_object('zoom_box').set_sensitive(False)
    else:
        self.input_controller.clear_highlighted_sections()
        self.clear_all_buttonpanels()
        self.display_view.render_no_selection()
        self.display_view.queuedraw()
        self.glade_xml.get_object('zoom_box').set_sensitive(False)
    self.display_view.queuedraw()

        
  def on_row_expand_collapse(self, treeview, logical,expand, openall, *params):
    treeview.get_model()
    selection = treeview.get_selection()
    model, iter = selection.get_selected()
#    if model.iter_parent(iter) == None:  #Top level
    return True
#    else:
#    return False

  def show_log_vol_view_panel(self,lv_list):
    #This is a wrapper for self.log_vol_view_panel.show()
    #If the VG has no LVs, then a proxy LV is returned as an 'Unused' LV.
    #We do not want to allow the deletion of this unused LV.
    #So we'll gray out the button.
    self.on_rm_select_lvs_button.set_sensitive(True)
    if len(lv_list) == 1:
        if lv_list[0].is_used() == False:
            self.on_rm_select_lvs_button.set_sensitive(False)
    self.log_vol_view_panel.show()
  
  def clear_all_buttonpanels(self):
      self.unalloc_panel.hide()
      self.uninit_panel.hide()
      self.log_vol_view_panel.hide()
      self.phys_vol_view_panel.hide()
      self.log_panel.hide()
      self.phys_panel.hide()
      
  
  def on_best_fit(self, obj):
      if (self.try_not_best_fit == True):
          return

      self.on_resize_drawing_area(None, None)
      self.__set_zoom_buttons(self.display_view.set_best_fit(self.try_not_best_fit))
      self.display_view.queuedraw()
  
  def on_zoom_in(self, obj):
      self.__set_zoom_buttons(self.display_view.zoom_in())
      self.display_view.queuedraw()
  
  def on_zoom_out(self, obj):
      self.__set_zoom_buttons(self.display_view.zoom_out())
      self.display_view.queuedraw()
  
  def __set_zoom_buttons(self, xxx_todo_changeme):
      (z_in, z_out) = xxx_todo_changeme
      if z_in:
          self.glade_xml.get_object('zoom_in_button').set_sensitive(True)
      else:
          self.glade_xml.get_object('zoom_in_button').set_sensitive(False)
      if z_out:
          self.glade_xml.get_object('zoom_out_button').set_sensitive(True)
      else:
          self.glade_xml.get_object('zoom_out_button').set_sensitive(False)
  
  def on_resize_drawing_area(self, obj1, obj2):
      self.display_view.set_visible_size((self.glade_xml.get_object('viewport1').get_allocated_width(),
                                          self.glade_xml.get_object('viewport1').get_allocated_height()))
  

class MirrorSyncProgress:
    def __init__(self, vbox):
        self.vbox = vbox
        
        # {name : [hbox, progressbar], ...}
        self.progress_bars = {}
        
        self.timer = 0
        
        self.forked_command = None
        
    
    def initiate(self):
        if MIRRORING_UI_SUPPORT == False:
            return
        
        # return if timer is already ticking
        if self.timer != 0:
            return
        if self.crank():
            # set up timer to call crank
            self.timer = GObject.timeout_add(1000, self.crank)
    
    def crank(self):
        # initiate lvprobe if not initiated
        if self.forked_command == None:
            args = [LVM_BIN_PATH, 'lvs', '--noheadings', '--separator', ';', '-o', 'lv_name,vg_name,lv_attr,copy_percent,move_pv']
            self.forked_command = ForkedCommand(LVM_BIN_PATH, args)
            self.forked_command.fork()
        
        # get lv data if completed
        out, err, status = self.forked_command.get_stdout_stderr_status()
        if out == None:
            # not done yet
            return True
        else:
            # command completed
            self.forked_command = None
            
            # find mirrors and copy percent
            mirrors = {}
            lines = out.splitlines()
            for line in lines:
                words = line.strip().split(';')
                lvname = words[0]
                vgname = words[1]
                lvattrs = words[2]
                copy_percent = words[3]
                if lvattrs[0] == 'm':
                    percent = float(copy_percent)
                    if percent != float('100.00'):
                        mirrors[vgname + '/' + lvname] = percent
            
            # add new lvs
            for name in mirrors:
                if name not in self.progress_bars:
                    progress = Gtk.ProgressBar()
                    progress.set_text(_("%s mirror synchronisation") % name)
                    progress.set_fraction(mirrors[name]/100.0)
                    hbox = Gtk.HBox()
                    hbox.pack_end(progress)
                    self.vbox.pack_start(hbox)
                    self.progress_bars[name] = [hbox, progress]
            # remove completed or renamed lvs
            for name in list(self.progress_bars.keys())[:]:
                if name not in mirrors:
                    self.vbox.remove(self.progress_bars[name][0])
                    self.progress_bars.pop(name)
            
            self.vbox.show_all()
            # update progress bars
            for name in self.progress_bars:
                self.progress_bars[name][1].set_fraction(mirrors[name]/100.0)
                
            # stop timer if all done
            if len(list(self.progress_bars.keys())) == 0:
                self.timer = 0
                return False
            else:
                return True
