import os
import string


class ExtentBlock:
  
  def __init__(self, pv, lv, start, size): # physical range
    self.__pv = pv
    self.__lv = lv
    self.__start = start
    self.__size = size
    self.__annotation = ''
    
    self.__pv.add_extent_block(self)
    
  
  def get_start_size(self):
    return self.__start, self.__size
  
  def get_pv(self):
    return self.__pv
  
  def get_lv(self):
    return self.__lv
  
  def is_used(self):
    return self.__lv.is_used()
  
  def set_annotation(self, txt):
    self.__annotation = txt
  def get_annotation(self):
    return self.__annotation
  
  def print_out(self, padding):
    start, size = self.get_start_size()
    end = start + size - 1
    string = 'start: ' + str(start)
    string = string + ', end: ' + str(end)
    string = string + ', size: ' + str(size)
    string = string + ' on ' + self.get_pv().get_name()
    print(padding + string)
