"""This renderer class renders volume properties into a separate
   drawing area next to the main volume rendering drawing area.
"""
 
import sys
import math
import operator
import types
import select
import signal
import gobject
import string
import os
from lvmui_constants import *
import stat
from html import escape
import gettext
_ = gettext.gettext
### gettext first, then import gtk (exception prints gettext "_") ###
try:
    import gi
    gi.require_version('Pango', '1.0')
    gi.require_version('PangoCairo', '1.0')
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, PangoCairo

    import cairo

except RuntimeError as e:
    print(_("""
  Unable to initialize graphical environment. Most likely cause of failure
  is that the tool was not run using a graphical environment. Please either
  start your graphical user interface or set your DISPLAY variable.
                                                                                
  Caught exception: %s
""") % e)
    sys.exit(-1)
                                                                                

LABEL_X = 325
LABEL_Y = 600
X_OFF = 20
Y_OFF = 10
BIG_HEADER_SIZE = 12000
PROPERTY_SIZE = 8000
PROPERTIES_STR=_("Properties for")
PHYSICAL_VOLUME_STR=_("Physical Volume")
LOGICAL_VOLUME_STR=_("Logical Volume")
UNALLOCATED_VOLUME_STR=_("Unallocated Volume")
UNINITIALIZED_VOLUME_STR=_("Disk Entity")
PHYSICAL_VOLUMEGROUP_STR=_("Volume Group")
LOGICAL_VOLUMEGROUP_STR=_("Volume Group")
VOLUMEGROUP_STR=_("Volume Group")
                                                                                
##############################################################

class Properties_Renderer:
  def __init__(self, area, widget):
    self.main_window = widget
    self.area = area  #actual widget, used for getting style, hence bgcolor
    
    self.area.set_size_request(700, 500)
    
    self.current_selection_layout = None
    
    self.layout_list = list()
    
#    self.layout_pixmap = gtk.gdk.Pixmap(self.main_window, LABEL_X, LABEL_Y)
    
#    self.gc = self.main_window.new_gc()
    self.pango_context = self.area.get_pango_context()
    
#    color = gtk.gdk.colormap_get_system().alloc_color("white", 1,1)
    self.area.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(1,1,1)) 
    self.area.connect('draw', self.on_expose_event)
    
#    self.clear_layout_pixmap()
  
  def render_to_layout_area(self, prop_list, name, type):
#    self.clear_layout_pixmap()
    self.layout_list = list()
    self.prepare_header_layout(name, type)
    self.prepare_prop_layout(prop_list, type)
    self.prepare_selection_props()
    self.area.queue_draw()
    
  
  def prepare_header_layout(self, name, type):
    pc = self.pango_context
    desc = pc.get_font_description()
    desc.set_size(BIG_HEADER_SIZE)
    pc.set_font_description(desc)
    
    layout_string1 = "<span size=\"12000\">" +PROPERTIES_STR + "</span>\n"
    if type == PHYS_TYPE:
      layout_string2 = "<span size=\"12000\">" + PHYSICAL_VOLUME_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#ED1C2A\" size=\"12000\"><b>" + name + "</b></span>"
    elif type == LOG_TYPE:
      layout_string2 = "<span size=\"12000\">" + LOGICAL_VOLUME_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#43ACE2\" size=\"12000\"><b>" + name + "</b></span>"
    elif type == UNALLOCATED_TYPE:
      layout_string2 = "<span size=\"12000\">" + UNALLOCATED_VOLUME_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#ED1C2A\" size=\"12000\"><b>" + name + "</b></span>"
    elif type == UNINITIALIZED_TYPE:
      layout_string2 = "<span size=\"12000\">" + UNINITIALIZED_VOLUME_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#404040\" size=\"12000\"><b>" + name + "</b></span>"

    elif type == VG_PHYS_TYPE:
      layout_string2 = "<span size=\"12000\">" + PHYSICAL_VOLUMEGROUP_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#ED1C2A\" size=\"12000\"><b>" + name + "</b></span>"
    elif type == VG_LOG_TYPE:
      layout_string2 = "<span size=\"12000\">" + LOGICAL_VOLUMEGROUP_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#43ACE2\" size=\"12000\"><b>" + name + "</b></span>"
    else:
      layout_string2 = "<span size=\"12000\">" + VOLUMEGROUP_STR + "</span>\n"
      layout_string3 = "<span foreground=\"#43A2FF\" size=\"12000\"><b>" + name + "</b></span>"
    layout_string = layout_string1 + layout_string2 + layout_string3
    
    header_layout = self.area.create_pango_layout('')
    header_layout.set_markup(layout_string)
    self.layout_list.append(header_layout)
  
  def prepare_prop_layout(self, prop_list,type):
    pc = self.pango_context
    desc = pc.get_font_description()
    desc.set_size(PROPERTY_SIZE)
    pc.set_font_description(desc)
    
    text_str = self.prepare_props_list(prop_list, type)
    props_layout = self.area.create_pango_layout('')
    props_layout.set_markup(text_str)
    self.layout_list.append(props_layout)
  
#  def clear_layout_pixmap(self):
#    self.set_color("white")
#    self.layout_pixmap.draw_rectangle(self.gc, True, 0, 0, -1, -1)
  
  def clear_layout_area(self):
#      self.clear_layout_pixmap()
      self.layout_list = list()
#      self.main_window.draw_drawable(self.gc, self.layout_pixmap, 0, 0, X_OFF, Y_OFF, -1, -1)
    
  
  def set_color(self, color):
      #self.gc.set_foreground(gtk.gdk.colormap_get_system().alloc_color(color, 1,1))
      pass
  
  def prepare_selection_props(self):
      pass
  
  def prepare_props_list(self, props_list, type):
    stringbuf = list()
    for i in range(0, len(props_list), 2):
      if i != 0:
        stringbuf.append("\n")
        
      stringbuf.append("<b>" + escape(props_list[i]) + "</b>")
      if (type == PHYS_TYPE) or (type == VG_PHYS_TYPE) or (type == UNALLOCATED_TYPE):
        stringbuf.append("<span foreground=\"#ED1C2A\">")  
      elif (type == LOG_TYPE) or (type == VG_LOG_TYPE):
        stringbuf.append("<span foreground=\"#43ACE2\">")  
      elif type == VG_TYPE:
        stringbuf.append("<span foreground=\"#43A2FF\">")  
      else:
        stringbuf.append("<span foreground=\"#404040\">")  

      stringbuf.append(escape(props_list[i+1]))
      stringbuf.append("</span>")

    text_str = "".join(stringbuf)
    return text_str
  
  def do_render(self, ctx):
    #    self.clear_layout_pixmap()
    Gdk.cairo_set_source_rgba(ctx, Gdk.RGBA(1,1,1,1))
    ctx.rectangle(0, 0, self.area.get_allocated_width(),
                  self.area.get_allocated_height())
    ctx.fill()
    Gdk.cairo_set_source_rgba(ctx, Gdk.RGBA(0,0,0,1))
    self.set_color("black")
    y_offset = 0
    for layout in self.layout_list:
      x,y = layout.get_pixel_size()
      if y_offset == 0:
        ctx.save()
        ctx.move_to(X_OFF, Y_OFF)
        PangoCairo.update_layout(ctx, layout)
        PangoCairo.show_layout(ctx, layout)
        ctx.restore()
        #        self.layout_pixmap.draw_layout(self.gc, 0, 0, layout)
        y_offset = y_offset + y
      else:
        ctx.save()
        ctx.move_to(X_OFF, Y_OFF + y_offset + 5)
        PangoCairo.update_layout(ctx, layout)
        PangoCairo.show_layout(ctx, layout)
        ctx.restore()
        #        self.layout_pixmap.draw_layout(self.gc, 0, y_offset + 5, layout)
        y_offset = y_offset + y
        
      if self.current_selection_layout != None:
        ctx.save()
        ctx.move_to(X_OFF, Y_OFF + y_offset + 5)
        PangoCairo.update_layout(ctx, self.current_selection_layout)
        PangoCairo.show_layout(ctx, self.current_selection_layout)
        ctx.restore()
        #        self.layout_pixmap.draw_layout(self.gc, 0, y_offset + 5, self.current_selection_layout)
        pass
#    self.main_window.draw_drawable(self.gc, self.layout_pixmap, 0, 0, X_OFF, Y_OFF, -1, -1)
  
  def render_selection(self, layout):
      ###FIXME - This has the potential of eliminating all entries on the list.
      if layout == None:
          self.current_selection_layout = None
          self.do_render()
      elif layout is self.current_selection_layout:
          return
      else:
          self.current_selection_layout = layout
          self.do_render() 
  
  def on_expose_event(self, widget, ctx):
      self.do_render(ctx)
