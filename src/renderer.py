

import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk



from cylinder_items import *

from lvmui_constants import *

from Segment import STRIPED_SEGMENT_ID, LINEAR_SEGMENT_ID, UNUSED_SEGMENT_ID, MIRROR_SEGMENT_ID


GRADIENT_PV = "#ED1C2A"
GRADIENT_VG = "#2D6C23"
GRADIENT_LV = "#43ACE2"
GRADIENT_UV = "#404040"


HEIGHT_SINGLE = 100
HEIGHT_DUAL = 50
#WIDTH_SINGLE = 200
WIDTH_SINGLE = 250
WIDTH_MULTIPLE = 300
SMALLEST_SELECTABLE_WIDTH = 4

Y_OFFSET = 125


#UNINITIALIZED_MESSAGE=_("This extent has not yet been \n initialized for use with LVM.")
UNSELECTED_MESSAGE=_("No Volume Selected")
MULTIPLE_SELECTION_MESSAGE=_("Multiple selection")
#UNALLOCATED_MESSAGE=_("This Volume has not been allocated \n to a Volume Group yet.") 
LOGICAL_VOL_STR=_("Logical Volume")
PHYSICAL_VOL_STR=_("Physical Volume")
VOLUME_GRP_STR=_("Volume Group")
LOGICAL_VIEW_STR=_("Logical View")
PHYSICAL_VIEW_STR=_("Physical View")
UNALLOCATED_STR=_("Unallocated")
UNINITIALIZED_STR=_("Uninitialized")
DISK_ENTITY_STR=_("Disk Entity")
#EXTENTS_STR=_("extents")
#MEGABYTES_STR=_("Megabytes")



CYL_ID_VOLUME = 0
CYL_ID_FUNCTION = 1
CYL_ID_ARGS = 2





class DisplayView:
    
    def __init__(self,
                 register_selections_fcn, 
                 da1, # drawing area
                 properties_renderer1, 
                 da2=None, 
                 properties_renderer2=None):
        self.da = da1
        self.pr = properties_renderer1
        
        self.dvH = None # helper DisplayView
        if da2 != None:
            self.dvH = DisplayView(None, da2, properties_renderer2) 
        self.dvH_selectable = False
        
#        self.gc = self.da.window.new_gc()
#        white = gtk.gdk.colormap_get_system().alloc_color("white", 1,1)
#        black = gtk.gdk.colormap_get_system().alloc_color("black", 1,1)
#        self.gc.foreground = black
#        self.gc.background = white
        
#        self.da.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.da.connect('draw', self.expose)
        self.da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.da.connect('button_press_event', self.mouse_event)
        
        self.message = ''
        
        self.display = None # Single or Double Cylinder
        
        #        lv_color = gtk.gdk.colormap_get_system().alloc_color(GRADIENT_LV, 1,1)
        #        pv_color = gtk.gdk.colormap_get_system().alloc_color(GRADIENT_PV, 1,1)
        #        uv_color = gtk.gdk.colormap_get_system().alloc_color(GRADIENT_UV, 1,1)
        #        vg_color = gtk.gdk.colormap_get_system().alloc_color(GRADIENT_VG, 1,1)
        lv_color = Gdk.RGBA()
        lv_color.parse(GRADIENT_LV)
        pv_color = Gdk.RGBA()
        pv_color.parse(GRADIENT_PV)
        uv_color = Gdk.RGBA()
        uv_color.parse(GRADIENT_UV)
        vg_color = Gdk.RGBA()
        vg_color.parse(GRADIENT_VG)
        self.pv_cyl_gen = CylinderGenerator(INSTALLDIR + '/pixmaps/PV.xpm', pv_color)
        self.lv_cyl_gen = CylinderGenerator(INSTALLDIR + '/pixmaps/LV.xpm', lv_color)
        self.uv_cyl_gen = CylinderGenerator(INSTALLDIR + '/pixmaps/UV.xpm', uv_color)
        self.vg_cyl_gen = CylinderGenerator(INSTALLDIR + '/pixmaps/VG.xpm', vg_color)
        
        # to be removed when right clicking gets implemented
        self.type = None
        self.register_selections_fcn = register_selections_fcn
        
        self.set_visible_size((50, 50))
        
        self.height = None
        
    
    def zoom_in(self):
        if self.display == None:
            return (False, False)
        
        w_old = self.display.get_width()
        w_new = w_old * 1.5
        h_old = self.display.get_height()
        h_new = h_old + 2
        
        self.display.set_width(w_new)
        self.display.set_height(h_new)
        
        smallest_selectable = self.display.get_smallest_selectable_width()
        if SMALLEST_SELECTABLE_WIDTH <= smallest_selectable or smallest_selectable == 0:
            return (False, True)
        else:
            return (True, True)
    
    def zoom_out(self):
        if self.display == None:
            return (False, False)
        
        w_old = self.display.get_width()
        w_new = w_old * 0.5
        h_old = self.display.get_height()
        h_new = h_old - 2
        
        self.display.set_width(w_new)
        self.display.set_height(h_new)
        
        pix_w, nothing1, nothing2 = self.display.minimum_pixmap_dimension(self.da)
        
        if pix_w <= self.get_visible_size()[0]:
            self.set_best_fit()
            return (True, False)
        
        return (True, True)
    
    def set_best_fit(self, try_not_best_fit = False):
        if self.display == None:
            return (False, False)

        self.display.respect_smallest_selectable_width(False)

        if try_not_best_fit == True:
            return (False, False)        

        vis_w, vis_h = self.get_visible_size()
        pix_w, pix_h, u_label_h = self.display.minimum_pixmap_dimension(self.da)
        
        while pix_w+20 > 1.01 * vis_w or pix_w+20 < 0.98 * vis_w:
            cyl_w = self.display.get_width()
            if pix_w+20 > 1.01 * vis_w:
                if self.display.get_adjusted_width() > 100:
                    new_width = cyl_w * 0.8
                else:
                    break
            else:
                new_width = cyl_w * 1.2
            self.display.set_width(new_width)
            pix_w, pix_h, u_label_h = self.display.minimum_pixmap_dimension(self.da)
            
        self.display.set_height(self.height)
        
        return (True, False)
    
    def set_visible_size(self, xxx_todo_changeme):
        (width, height) = xxx_todo_changeme
        self.visible_size = (width, height)
    def get_visible_size(self):
        return self.visible_size
    
    
    def render_pv(self, pv):
        if self.dvH != None:
            self.dvH.render_no_selection()
            self.dvH_selectable = True
        
        self.type = PHYS_TYPE
        self.height = HEIGHT_SINGLE
        
        # display properties
        self.pr.render_to_layout_area(pv.get_properties(), pv.get_description(), PHYS_TYPE)
        
        # display cylinder
        line1 = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\"><b>" + PHYSICAL_VOL_STR + "</b></span>\n"
        line2 = "<span size=\"8000\"><b>" + pv.get_description() + "</b></span>"
        label = line1 + line2
        self.display = SingleCylinder(False, '', label, SMALLEST_SELECTABLE_WIDTH, WIDTH_MULTIPLE, self.height)
        self.display.append_right(End(self.pv_cyl_gen))
        for extent in pv.get_extent_blocks():
            extents_lv = extent.get_lv()
            if extents_lv.is_used():
                if extents_lv.is_mirror_log:
                    cyl = UnselectableSubcylinder(_("The extents that you are attempting to select belong to a mirror log of Logical Volume %s. Mirrored Logical Volumes are not yet migratable, so the extents are not selectable.") % extents_lv.get_name(), self.pv_cyl_gen, 1, extent.get_start_size()[1])
                elif extents_lv.is_mirror_image:
                    cyl = UnselectableSubcylinder(_("The extents that you are attempting to select belong to mirror image of Logical Volume %s. Mirrored Logical Volumes are not yet migratable, so the extents are not selectable.") % extents_lv.get_name(), self.pv_cyl_gen, 1, extent.get_start_size()[1])
                elif extents_lv.is_snapshot():
                    cyl = UnselectableSubcylinder(_("The extents that you are attempting to select belong to %s, a snapshot of %s. Snapshots are not yet migratable, so the extents are not selectable.") % (extents_lv.get_name(), extents_lv.get_snapshot_info()[0].get_name()), self.pv_cyl_gen, 1, extent.get_start_size()[1])
                elif extents_lv.has_snapshots():
                    cyl = UnselectableSubcylinder(_("The extents that you are attempting to select belong to a snapshot origin %s. Snapshot origins are not yet migratable, so the extents are not selectable.") % extents_lv.get_name(), self.pv_cyl_gen, 1, extent.get_start_size()[1])
                else:
                    cyl = Subcylinder(self.pv_cyl_gen, 1, 1, True, extent.get_start_size()[1])
            else:
                cyl = Subcylinder(self.pv_cyl_gen, 1, 1, False, extent.get_start_size()[1])
            label = "<span size=\"7000\">"
            label = label + extent.get_lv().get_name() + '\n'
            annotation = extent.get_annotation()
            if annotation != '':
                label = label + annotation + '\n'
            label = label + str(extent.get_start_size()[1]) + ' extents'
            label = label + "</span>"
            cyl.set_label_lower(label)
            self.display.append_right(cyl)
            self.display.append_right(Separator())
            # set up helper display
            cyl.add_object(CYL_ID_VOLUME, extent)
            cyl.add_object(CYL_ID_FUNCTION, DisplayView.render_ext)
            cyl.add_object(CYL_ID_ARGS, [extent])
    
    def render_unalloc_pv(self, pv):
        if self.dvH != None:
            self.dvH.render_none()
            self.dvH_selectable = False
        
        self.type = None
        self.height = HEIGHT_SINGLE
        
        # display properties
        self.pr.render_to_layout_area(pv.get_properties(), pv.get_description(), UNALLOCATED_TYPE)
        
        # display cylinder
        line1 = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\"><b>" + UNALLOCATED_STR + "</b></span>"
        line2 = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\"><b>" + PHYSICAL_VOL_STR + "</b></span>"
        line3 = "<span size=\"8000\"><b>" + pv.get_description() + "</b></span>"
        label = line1 + "\n" + line2 + "\n" + line3
        self.display = SingleCylinder(True, '', label, SMALLEST_SELECTABLE_WIDTH, WIDTH_SINGLE, self.height)
        self.display.append_right(End(self.pv_cyl_gen))
        cyl = Subcylinder(self.pv_cyl_gen, 1, 1, False, 1)
        self.display.append_right(cyl)
    
    def render_uninit_pv(self, pv):
        if self.dvH != None:
            self.dvH.render_none()
            self.dvH_selectable = False
        
        self.type = None
        self.height = HEIGHT_SINGLE
        
        # display properties
        self.pr.render_to_layout_area(pv.get_properties(), pv.get_description(), UNINITIALIZED_TYPE)
        
        # display cylinder
        line1 = "<span size=\"8000\"><b>" + UNINITIALIZED_STR + "</b></span>\n"
        line2 = "<span size=\"8000\"><b>" + DISK_ENTITY_STR + "</b></span>\n"
        line3 = "<span size=\"8000\"><b>" + pv.get_description() + "</b></span>"
        label = line1 + line2 + line3
        self.display = SingleCylinder(True, '', label, SMALLEST_SELECTABLE_WIDTH, WIDTH_SINGLE, self.height)
        self.display.append_right(End(self.uv_cyl_gen))
        cyl = Subcylinder(self.uv_cyl_gen, 1, 1, False, 1)
        self.display.append_right(cyl)
    
    def render_pvs(self, pv_list):
        if self.dvH != None:
            self.dvH.render_no_selection()
            self.dvH_selectable = True
        
        self.type = VG_PHYS_TYPE
        self.height = HEIGHT_SINGLE
        
        vg = pv_list[0].get_vg()
        
        # display properties
        self.pr.render_to_layout_area(vg.get_properties(), vg.get_name(), VG_PHYS_TYPE)
        
        # display cylinder
        line1 = "<span size=\"7000\"><b>" + VOLUME_GRP_STR + "</b></span>\n"
        line2 = "<span size=\"7000\"><b>" + vg.get_name() + "</b></span>\n"
        line3 = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\"><i>" + PHYSICAL_VIEW_STR + "</i></span>" 
        label = line1 + line2 + line3
        self.display = SingleCylinder(False, '', label, SMALLEST_SELECTABLE_WIDTH, WIDTH_MULTIPLE, self.height)
        self.display.append_right(End(self.pv_cyl_gen))
        for pv in pv_list:
            selectable = pv.is_used()
            cyl = Subcylinder(self.pv_cyl_gen, 1, 2, selectable, pv.get_extent_total_used_free()[0])
            #label = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\">" + pv.get_name() + "</span>"
            label = "<span size=\"8000\">" + pv.get_description(False, False) + "</span>"
            cyl.set_label_upper(label)
            self.display.append_right(cyl)
            self.display.append_right(Separator())
            # set up helper display
            cyl.add_object(CYL_ID_VOLUME, pv)
            cyl.add_object(CYL_ID_FUNCTION, DisplayView.render_pv)
            cyl.add_object(CYL_ID_ARGS, [pv])
    
    def render_lv(self, lv):
        if self.dvH != None:
            self.dvH.render_none()
            self.dvH_selectable = False
        
        self.type = None
        self.height = HEIGHT_SINGLE
        
        # display properties
        self.pr.render_to_layout_area(lv.get_properties(), lv.get_path(), LOG_TYPE)
        
        # display cylinder
        line1 = "<span foreground=\"" + GRADIENT_LV + "\" size=\"8000\"><b>" + LOGICAL_VOL_STR + "</b></span>\n"
        line2 = "<span size=\"8000\"><b>" + lv.get_path() + "</b></span>"
        label = line1 + line2
        self.display = SingleCylinder(True, '', label, SMALLEST_SELECTABLE_WIDTH, WIDTH_SINGLE, self.height)
        self.display.append_right(End(self.lv_cyl_gen))
        cyl = Subcylinder(self.lv_cyl_gen, 1, 1, False, lv.get_extent_total_used_free()[0])
        self.display.append_right(cyl)
    
    def render_lvs(self, lv_list):
        if self.dvH != None:
            self.dvH.render_no_selection()
            self.dvH_selectable = True
        
        self.type = VG_LOG_TYPE
        self.height = HEIGHT_SINGLE
        
        vg = lv_list[0].get_vg()
        
        # place unused space to the end
        for lv in lv_list:
            if lv.is_used():
                continue
            else:
                lv_list.remove(lv)
                lv_list.append(lv)
                break
        
        # display properties
        self.pr.render_to_layout_area(vg.get_properties(), vg.get_name(), VG_LOG_TYPE)
        
        # display cylinder
        line1 = "<span size=\"7000\"><b>" + VOLUME_GRP_STR + "</b></span>\n"
        line2 = "<span size=\"7000\"><b>" + vg.get_name() + "</b></span>\n"
        line3 = "<span foreground=\"" + GRADIENT_LV + "\" size=\"8000\"><i>" + LOGICAL_VIEW_STR + "</i></span>" 
        label = line1 + line2 + line3
        self.display = SingleCylinder(False, '', label, SMALLEST_SELECTABLE_WIDTH, WIDTH_MULTIPLE, self.height)
        self.display.append_right(End(self.lv_cyl_gen))
        lv_cyls_dir = {}
        for lv in lv_list:
            selectable = lv.is_used()
            cyl = None
            if lv.get_segments()[0].get_type() == MIRROR_SEGMENT_ID:
                cyl = Subcylinder(self.lv_cyl_gen, 1, 0, selectable)
                image_lv_cyls = []
                for image_lv in lv.get_segments()[0].get_images():
                    image_lv_cyl = Subcylinder(self.lv_cyl_gen, 1, 0, False)
                    label_mirror = "<span size=\"8000\">" + image_lv.get_segments()[0].get_extent_block().get_annotation() + "</span>"
                    image_lv_cyl.set_label_lower(label_mirror, False, True, False)
                    image_lv_cyls.append(image_lv_cyl)
                    for seg in image_lv.get_segments():
                        # mirror should have linear mapping only
                        extent = seg.get_extent_block()
                        subcyl = Subcylinder(self.lv_cyl_gen, 1, 0, False, extent.get_start_size()[1])
                        image_lv_cyl.children.append(subcyl)
                if len(image_lv_cyls) != 0:
                    cyl.children.append(image_lv_cyls[0])
                for image_lv_cyl in image_lv_cyls[1:]:
                    cyl.children.append(Separator(1, self.lv_cyl_gen, 3))
                    cyl.children.append(image_lv_cyl)
            else:
                cyl = Subcylinder(self.lv_cyl_gen, 1, 0, selectable, lv.get_extent_total_used_free()[0])
            #label = "<span foreground=\"" + GRADIENT_LV + "\" size=\"8000\">" + lv.get_name() + "</span>"
            label = "<span size=\"8000\">" + lv.get_name() + "</span>"
            cyl.set_label_upper(label)
            self.display.append_right(cyl)
            self.display.append_right(Separator())
            # set up helper display
            cyl.add_object(CYL_ID_VOLUME, lv)
            cyl.add_object(CYL_ID_FUNCTION, DisplayView.render_lv)
            cyl.add_object(CYL_ID_ARGS, [lv])
            lv_cyls_dir[lv.get_name()] = cyl
        
        # set up snapshot highlighting
        for orig in lv_list:
            snaps = orig.get_snapshots()
            for snap in snaps:
                orig_cyl = lv_cyls_dir[orig.get_name()]
                snap_cyl = lv_cyls_dir[snap.get_name()]
                orig_cyl.add_highlightable(snap_cyl)
                snap_cyl.add_highlightable(orig_cyl)
                label_snap = "<span size=\"8000\">" + (_("Snapshot of %s") % orig.get_name()) + "</span>"
                snap_cyl.set_label_lower(label_snap, False, True, True)
    
    def render_vg(self, vg):
        if self.dvH != None:
            self.dvH.render_no_selection()
            self.dvH_selectable = True
        
        self.type = None
        self.height = HEIGHT_DUAL
        
        pv_list = list(vg.get_pvs().values())
        lv_list = list(vg.get_lvs().values())
        
        # place unused space to the end
        for lv in lv_list:
            if lv.is_used():
                continue
            else:
                lv_list.remove(lv)
                lv_list.append(lv)
                break
        
        # display properties
        self.pr.render_to_layout_area(vg.get_properties(), vg.get_name(), VG_TYPE)
        
        # display cylinder
        line1 = "<span size=\"7000\"><b>" + VOLUME_GRP_STR + "</b></span>\n"
        line2 = "<span size=\"7000\"><b>" + vg.get_name() + "</b></span>\n"
        line3 = "<span foreground=\"" + GRADIENT_LV + "\" size=\"8000\"><i>" + LOGICAL_VIEW_STR + "</i></span>" 
        label_upper = line1 + line2 + line3
        line1 = "<span size=\"7000\"><b>" + VOLUME_GRP_STR + "</b></span>\n"
        line2 = "<span size=\"7000\"><b>" + vg.get_name() + "</b></span>\n"
        line3 = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\"><i>" + PHYSICAL_VIEW_STR + "</i></span>" 
        label_lower = line1 + line2 + line3
        self.display = DoubleCylinder(Y_OFFSET, '', label_upper, label_lower, 5, WIDTH_MULTIPLE, self.height)
        
        lv_cyls_dir = {}
        lv_cyls = []
        for lv in lv_list:
            #label = "<span foreground=\"" + GRADIENT_LV + "\" size=\"8000\">" + lv.get_name() + "</span>"
            label = "<span size=\"8000\">" + lv.get_name() + "</span>"
            #cyl = Subcylinder(self.lv_cyl_gen, 1, 0, lv.is_used())
            #cyl = Subcylinder(self.lv_cyl_gen, 1, 0, True)
            cyl = Subcylinder(self.lv_cyl_gen, 1, 4, True)
            lv_cyls_dir[lv] = cyl
            cyl.set_label_upper(label)
            lv_cyls.append(cyl)
            for seg in lv.get_segments():
                type = seg.get_type()
                if type == STRIPED_SEGMENT_ID:
                    for stripe in list(seg.get_stripes().values()):
                        subcyl = Subcylinder(self.lv_cyl_gen, 1, 0, False, stripe.get_start_size()[1])
                        lv_cyls_dir[stripe] = subcyl
                        cyl.children.append(subcyl)
                elif type == LINEAR_SEGMENT_ID  or type == UNUSED_SEGMENT_ID:
                    extent = seg.get_extent_block()
                    subcyl = Subcylinder(self.lv_cyl_gen, 1, 0, False, extent.get_start_size()[1])
                    lv_cyls_dir[extent] = subcyl
                    cyl.children.append(subcyl)
                elif type == MIRROR_SEGMENT_ID:
                    image_lv_cyls = []
                    for image_lv in seg.get_images():
                        image_lv_cyl = Subcylinder(self.lv_cyl_gen, 1, 0, False)
                        label_mirror = "<span size=\"8000\">" + image_lv.get_segments()[0].get_extent_block().get_annotation() + "</span>"
                        image_lv_cyl.set_label_lower(label_mirror, False, True, False)
                        image_lv_cyls.append(image_lv_cyl)
                        lv_cyls_dir[image_lv] = image_lv_cyl
                        for seg2 in image_lv.get_segments():
                            # mirror should have linear mapping only
                            extent = seg2.get_extent_block()
                            subcyl = Subcylinder(self.lv_cyl_gen, 1, 0, False, extent.get_start_size()[1])
                            lv_cyls_dir[extent] = subcyl
                            image_lv_cyl.children.append(subcyl)
                    if len(image_lv_cyls) != 0:
                        cyl.children.append(image_lv_cyls[0])
                    for image_lv_cyl in image_lv_cyls[1:]:
                        cyl.children.append(Separator(1, self.lv_cyl_gen, 3))
                        cyl.children.append(image_lv_cyl)
                else:
                    print('Error: render_vg(): invalid segment type')
            
            # set up mirroring log
            if lv.is_mirrored():
                log_lv = lv.get_mirror_log()
                if log_lv:
                    for seg2 in log_lv.get_segments():
                        # log should have linear mapping only
                        extent = seg2.get_extent_block()
                        subcyl = Subcylinder(self.lv_cyl_gen, 1, 0, False, extent.get_start_size()[1])
                        lv_cyls_dir[extent] = subcyl
                        cyl.children.append(subcyl)
            
            # set up helper display
            cyl.add_object(CYL_ID_VOLUME, lv)
            cyl.add_object(CYL_ID_FUNCTION, DisplayView.render_lv)
            cyl.add_object(CYL_ID_ARGS, [lv])
            
        
        # set up snapshot highlighting
        for orig in lv_list:
            if orig.has_snapshots():
                orig_cyl = lv_cyls_dir[orig]
                label_orig = "<span size=\"8000\">" + _("Origin") + "</span>"
                orig_cyl.set_label_lower(label_orig, False, False, True)
                for snap in orig.get_snapshots():
                    snap_cyl = lv_cyls_dir[snap]
                    orig_cyl.add_highlightable(snap_cyl)
                    snap_cyl.add_highlightable(orig_cyl)
                    label_snap = "<span size=\"8000\">" + _("Snapshot") + "</span>"
                    snap_cyl.set_label_lower(label_snap, False, True, True)
        
        pv_cyls = []
        for pv in pv_list:
            #pv_cyl = Subcylinder(self.pv_cyl_gen, 1, 2, True)
            pv_cyl = Subcylinder(self.pv_cyl_gen, 1, 2, False)
            #label = "<span foreground=\"" + GRADIENT_PV + "\" size=\"8000\">" + pv.get_name() + "</span>"
            label = "<span size=\"8000\">" + pv.get_description(False, False) + "</span>"
            pv_cyl.set_label_upper(label)
            pv_cyls.append(pv_cyl)
            # set up helper display
            pv_cyl.add_object(CYL_ID_VOLUME, pv)
            pv_cyl.add_object(CYL_ID_FUNCTION, DisplayView.render_pv)
            pv_cyl.add_object(CYL_ID_ARGS, [pv])
            for ext in pv.get_extent_blocks():
                width = ext.get_start_size()[1]
                ext_cyl_p = Subcylinder(self.pv_cyl_gen, 1, 2, False, width)
                label = "<span size=\"7000\">"
                annotation = ext.get_annotation()
                if annotation != '':
                    label = label + annotation + '\n'
                label = label + str(width) + ' extents'
                label = label + "</span>"
                ext_cyl_p.set_label_lower(label, False, False, True)
                ext_cyl_l = lv_cyls_dir[ext]
                ext_cyl_l.add_highlightable(ext_cyl_p)
                pv_cyl.children.append(ext_cyl_p)
        
        self.display.append_right(True, End(self.lv_cyl_gen))
        for lv_cyl in lv_cyls:
            self.display.append_right(True, lv_cyl)
            self.display.append_right(True, Separator())
        
        self.display.append_right(False, End(self.pv_cyl_gen))
        for pv_cyl in pv_cyls:
            self.display.append_right(False, pv_cyl)
            self.display.append_right(False, Separator())
    
    def render_ext(self, ext):
        # TODO: implement extent view
        if self.dvH != None:
            self.dvH.render_none()
            self.dvH_selectable = False
        self.render_text(_("extent view"))
        
        self.type = None
        
        return
    
    def render_no_selection(self):
        #self.render_text(UNSELECTED_MESSAGE)
        self.render_text('')
        self.dvH_selectable = True
        
        self.type = None
        
    def render_none(self):
        self.render_text('')
        self.dvH_selectable = False
        
        self.type = None
        
    def render_multiple_selection(self):
        self.render_text(MULTIPLE_SELECTION_MESSAGE)
        self.dvH_selectable = True
        
        self.type = None
        
    def render_text(self, txt):
        # clear properties
        self.pr.clear_layout_area()
        # set up message
        self.message = txt
        self.display = None
        # render helper
        if self.dvH != None:
            self.dvH.render_none()
        
        self.type = None
        
        
    def queuedraw(self):
        self.da.queue_draw()
    
    def expose(self, obj1, obj2):
        self.draw(obj1, obj2)
    
    def draw(self, draw_area, ctx):
        if self.display != None:
            w, h, u_label_h = self.display.minimum_pixmap_dimension(self.da)
            y_offset = Y_OFFSET - u_label_h
            if y_offset < 0:
                y_offset = 0
            self.da.set_size_request(w+20, h+y_offset+20)
            self.display.draw(self.da, ctx, (10, y_offset))
        else:
            # clear pixmap
#            pixmap = self.da.window
#            (w, h) = pixmap.get_size()
            w = draw_area.get_allocated_width()
            h = draw_area.get_allocated_height()
            Gdk.cairo_set_source_rgba(ctx, Gdk.RGBA(1,1,1,1))
            ctx.rectangle(0, 0, w, h);
            ctx.fill()       
            Gdk.cairo_set_source_rgba(ctx, Gdk.RGBA(0,0,0,1))
            
            # draw message
            layout = self.da.create_pango_layout('')
            layout.set_markup(self.message)
            label_w, label_h = layout.get_pixel_size()
            #pixmap.draw_layout(self.gc, (w-label_w)/2, (h-label_h)/2, layout)
            ctx.save()
            ctx.move_to(180, 180)
            PangoCairo.update_layout(ctx, layout)
            PangoCairo.show_layout(ctx, layout)
            ctx.restore()
#            pixmap.draw_layout(self.gc, 180, 180, layout)
        
    def mouse_event(self, obj, event, *args):
        
        if self.display != None:
            self.display.click((int(event.x), int(event.y)), event.button==1)
            
            selection = self.display.get_selection()
            
            # register selection
            if self.register_selections_fcn != None and self.type != None:
                sels = []
                for sel in selection:
                    sels.append(sel.get_object(CYL_ID_VOLUME))
                self.register_selections_fcn(self.type, sels)
            
            # render helper DisplayView
            if self.dvH != None:
                if len(selection) == 0:
                    if self.dvH_selectable:
                        self.dvH.render_no_selection()
                    else:
                        self.dvH.render_none()
                elif len(selection) == 1:
                    # render to dvH
                    cyl = selection[0]
                    volume = cyl.get_object(CYL_ID_VOLUME)
                    render_fct = cyl.get_object(CYL_ID_FUNCTION)
                    args = cyl.get_object(CYL_ID_ARGS)
                    if len(args) == 0:
                        render_fct(self.dvH)
                    elif len(args) == 1:
                        render_fct(self.dvH, args[0])
                    elif len(args) == 2:
                        render_fct(self.dvH, args[0], args[1])
                    elif len(args) == 3:
                        render_fct(self.dvH, args[0], args[1], args[2])
                else:
                    self.dvH.render_multiple_selection()
            self.queuedraw()
#            self.draw()
