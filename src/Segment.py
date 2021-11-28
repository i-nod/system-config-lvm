
import os
import string



STRIPED_SEGMENT_ID = 1
LINEAR_SEGMENT_ID  = 2
UNUSED_SEGMENT_ID  = 3
MIRROR_SEGMENT_ID  = 4


class Segment:
  
  def __init__(self, type, start, size): # logical range
    self.type = type
    
    self.start = start
    self.size = size
    
  
  def get_start_size(self):
    return self.start, self.size
  
  def get_type(self):
    return self.type
  
  
  def print_out(self, padding):
    print(padding + str(self.get_start_size()))
  

class StripedSegment(Segment):
  
  def __init__(self, stripe_size, start, size): # logical range
    Segment.__init__(self, STRIPED_SEGMENT_ID, start, size)
    
    self.stripe_size = stripe_size # bytes
    self.stripes = {}
    
  
  def add_stripe(self, id, extent_block):
    self.stripes[id] = extent_block
    extent_block.set_annotation(_("Stripe") + str(id))
  def get_stripes(self):
    return self.stripes
  
  def get_stripe_size(self):
    return self.stripe_size
  
  def print_out(self, padding):
    Segment.print_out(self, padding + 'striped: ')
    for stripe_id in self.get_stripes():
      print(padding + ' stripe' + str(stripe_id) + ': ')
      self.get_stripes()[stripe_id].print_out(padding + '  ')
  

class LinearSegment(Segment):
  
  def __init__(self, start, size, type=LINEAR_SEGMENT_ID): # logical range
    Segment.__init__(self, type, start, size)
    
    self.extent_block = None
    
  
  def set_extent_block(self, extent_block):
    self.extent_block = extent_block
    self.extent_block.set_annotation(_("Linear Mapping"))
  def get_extent_block(self):
    return self.extent_block
  
  
  def print_out(self, padding):
    Segment.print_out(self, padding + 'linear: ')
    self.get_extent_block().print_out(padding + '  ')
  

class UnusedSegment(LinearSegment):
  
  def __init__(self, start, size): # logical range
    LinearSegment.__init__(self, start, size, UNUSED_SEGMENT_ID)
    
    
  def set_extent_block(self, extent_block):
    self.extent_block = extent_block
    self.extent_block.set_annotation('')
    
  
  def print_out(self, padding):
    print(padding + 'unused: ')
    LinearSegment.print_out(self, padding + '  ')
  

class MirroredSegment(Segment):
  
  def __init__(self, start, size): # logical range
    Segment.__init__(self, MIRROR_SEGMENT_ID, start, size)
    
    self.image_lvs = []
    
  
  def add_image(self, image_lv):
    image_lv.is_mirror_image = True
    image_num = len(self.image_lvs)
    self.image_lvs.append(image_lv)
    # set annotations
    for seg in image_lv.get_segments():
      extent = seg.get_extent_block()
      extent.set_annotation(_("Mirror") + str(image_num))
  def get_images(self):
    return self.image_lvs
  def clear_images(self):
    self.image_lvs = []
  
  def print_out(self, padding):
    Segment.print_out(self, padding + 'mirrored: ')
    print(padding + 'images: ')
    for image in self.get_images():
      image.print_out(padding + '  ')
