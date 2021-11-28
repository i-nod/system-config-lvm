
import fdisk_wrapper
from Partition import ID_EMPTY, ID_UNKNOWN
from Partition import ID_EXTENDS, ID_SWAPS
from Partition import PARTITION_IDs
from Partition import ID_LINUX_LVM

from BlockDevice import *


class BlockDeviceModel:
    
    def __init__(self):
        self.__views = dict()
        
        self.__devices = dict()
        fd = fdisk_wrapper.FDisk()
        for devname in fd.getDeviceNames():
            try:
                bd = BlockDevice(devname)
                self.__devices[devname] = bd
            except:
                pass
    
    def reload(self):
        for devname in self.__devices:
            self.reloadDisk(devname)
        
    def reloadDisk(self, devname):
        self.__devices[devname].reload()
        self.__notifyViews()
    
    # returns {devname : [Segment1, Segment2, Segment3, ...], ...}
    def getDevices(self):
        data = dict()
        for devname in self.__devices:
            data[devname] = self.getDevice(devname)
        return data
    
    # returns [Segment1, Segment2, Segment3, ...]
    def getDevice(self, devname):
        return self.__devices[devname].getSegments()
    
    def getPartition(self, devname, partnum):
        segs = self.getDevice(devname)
        return self.__getPartition(partnum, segs)
    def __getPartition(self, partnum, segs):
        for seg in segs:
            if seg.id == ID_EMPTY:
                continue
            if seg.num == partnum:
                return seg
            elif seg.id in ID_EXTENDS:
                part = self.__getPartition(partnum, seg.children)
                if part != None:
                    return part
        return None
        
    def add(self, devname, part):
        beg = part.beg
        end = part.end
        id = part.id
        boot = part.bootable
        num = self.__devices[devname].addAlign(beg, end, id, boot, part.num)
        self.__notifyViews()
        return num
    
    def addNoAlign(self, devname, part):
        beg = part.beg
        end = part.end
        id = part.id
        boot = part.bootable
        num = self.__devices[devname].addNoAlign(beg, end, id, boot, part.num)
        self.__notifyViews()
        return num
    
    def remove(self, devname, partnum):
        self.__devices[devname].remove(partnum)
        self.__notifyViews()
    
    ### commit changes to disk !!! ###
    def saveTable(self, devname):
        self.__devices[devname].saveTable()
        self.reloadDisk(devname)
        self.__notifyViews()
    
    def renumberExtends(self, devname):
        self.__devices[devname].renumberExtends()
        self.__notifyViews()
    
    def getSectorSize(self, devname):
        return self.__devices[devname].sectorSize
    
    def printDevicesDebug(self):
        for devname in self.__devices:
            self.__devices[devname].printout()
    
    def printDevices(self):
        devs = self.getDevices()
        for dev in devs:
            print('device:', dev)
            for part in devs[dev]:
                part.printout()
    
    # will call obj.funct(self.getDevices()) on any changes
    def registerView(self, obj, funct):
        self.__views[obj] = funct
    def removeView(self, obj):
        del(self.__views[obj])
    def __notifyViews(self):
        for obj in self.__views:
            (self.__views[obj])(obj, self.getDevices())
    
