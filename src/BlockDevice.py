
import copy

from fdisk_wrapper import FDisk
from parted_wrapper import Parted
from Partition import *



class BlockDeviceErr:
    pass
class BlockDeviceErr_occupied(BlockDeviceErr):
    pass
class BlockDeviceErr_cannotFit(BlockDeviceErr):
    pass
class BlockDeviceErr_extended(BlockDeviceErr):
    pass
class BlockDeviceErr_extendedNumsMissing(BlockDeviceErr):
    pass
class BlockDeviceErr_num(BlockDeviceErr):
    pass
class BlockDeviceErr_partFormat(BlockDeviceErr):
    pass



class BlockDevice:
    
    def __init__(self, devpath):
        self.__segs = list()
        self.dev = devpath
        
        self.sectors = 0
        self.sectorSize = 0
        self.cyls = 0
        self.spt = 0   # sectors per track
        self.spc = 0   # sectors per cylinder
        
        self.useParted = False
        
        self.reload()
    
    # discard changes
    def reload(self):
        fdisk = FDisk()
        self.__segs = list()
        # get disk geometry
        self.sectors, self.sectorSize, self.cyls, self.spt, self.spc = fdisk.getDeviceGeometry(self.dev)
        # allocate all space
        new_seg = BlockDeviceSegment(1, self.sectors-1, self.sectorSize)
        new_seg.wholeDevice = True
        self.__segs.append(new_seg)
        # get partitions
        parts = fdisk.getPartitions(self.dev)
        # then insert extended partitions
        for part in parts:
            if part.id in ID_EXTENDS:
                self.addNoAlign(part.beg, part.end, part.id, part.bootable, part.num)
        # insert other partitions
        for part in parts:
            if part.id not in ID_EXTENDS:
                self.addNoAlign(part.beg, part.end, part.id, part.bootable, part.num)
        self.__sortSegs()
        
        # check for gpt tables
        if self.__segs[0].id == ID_GPT:
            # gpt table already present
            self.__parted_reload()
        if self.sectors * self.sectorSize > 2 * 1024 * 1024 * 1024 * 1024:
            # msdos partition label handles up to 2 TB
            # use gpt table
            self.__parted_reload()
    
    def __parted_reload(self):
        self.useParted = True
        # allocate all space
        new_seg = BlockDeviceSegment(1, self.sectors-1, self.sectorSize)
        new_seg.wholeDevice = True
        self.__segs = [new_seg]
        # get partitions
        parts = Parted().getPartitions(self.dev)
        # insert partitions
        for part in parts:
            self.addNoAlign(part.beg, part.end, part.id, part.bootable, part.num)
        self.__sortSegs()
                
    
    # !!! save partition to disk !!!
    def saveTable(self):
        # make sure extended partitions don't have gaps in numbering
        nums = self.getPartNums()
        max_part = 4
        for i in nums:
            if i > max_part:
                max_part = i
        for i in range(5, max_part + 1):
            if i not in nums:
                raise BlockDeviceErr_extendedNumsMissing()
        
        if self.useParted:
            Parted().savePartTable(self.dev, self.getSegments())
        else:
            FDisk().savePartTable(self.dev, self.getSegments())
    
    def renumberExtends(self):
        self.__sortSegs()
        i = 5
        for part in self.__segs:
            if part.id in ID_EXTENDS:
                for p in part.children:
                    if p.id != ID_EMPTY:
                        p.num = i
                        p.children[1].num = i
                        i = i + 1
    
    def getSegments(self):
        segs_copy = copy.deepcopy(self.__sortSegs())
        return self.__getSegments(segs_copy, False)
    def __getSegments(self, segs, extended):
        if extended:
            # clean up
            for seg in segs:
                if seg.id != ID_EMPTY:
                    seg.beg = seg.children[1].beg
                    seg.children = list()
        # remove small unallocatable segments
        for seg in segs[:]:
            seg.children = self.__getSegments(seg.children, True)
            if (seg.id == ID_EMPTY) and (seg.getSize() <= self.spc):
                segs.remove(seg)
        return segs
    
    def getPartNums(self):
        nums = list()
        for seg in self.__segs:
            if seg.id != ID_EMPTY:
                nums.append(seg.num)
            if seg.id in ID_EXTENDS:
                for s in seg.children:
                    if s.id != ID_EMPTY:
                        nums.append(s.num)
        return nums
    
    def addAlign(self, beg, end, id, bootable, num = None):
        beg = self.__alignLowerBound(beg)
        if end != self.sectors - 1:
            end = self.__alignUpperBound(end)
        return self.addNoAlign(beg, end, id, bootable, num)
    
    def addNoAlign(self, beg, end, id, bootable, num = None):
        if beg >= end or beg == None or end == None:
            raise BlockDeviceErr_partFormat()
        if id == None or id < 1 or (id > 255 and id != ID_UNKNOWN):
            raise BlockDeviceErr_partFormat()
        if (bootable != True) and (bootable != False):
            raise BlockDeviceErr_partFormat()
        if (num != None) and (num < 1):
            raise BlockDeviceErr_partFormat()
        
        if beg >= end or id == ID_EMPTY:
            return None
        
        if id in ID_EXTENDS:
            bootable = False
            for seg in self.__segs:
                if seg.id in ID_EXTENDS:
                    # only one extended allowed
                    raise BlockDeviceErr_extended()
        
        intoExtended = False
        for seg in self.__segs:
            if seg.id in ID_EXTENDS:
                if beg >= seg.beg and beg <= seg.end:
                    intoExtended = True
        
        # autodetermine partition number
        if num == None:
            avail_nums = list()
            if not self.useParted:
                if intoExtended:
                    avail_nums = list(range(5, 100))
                    for i in self.getPartNums():
                        if i > 4:
                            avail_nums.remove(i)
                else:
                    avail_nums = list(range(1,5))
                    for i in self.getPartNums():
                        if i < 5:
                            avail_nums.remove(i)
            else:
                avail_nums = list(range(1,100))
                for i in self.getPartNums():
                    avail_nums.remove(i)
            
            if len(avail_nums) == 0:
                raise BlockDeviceErr_num()
            num = avail_nums[0]
        
        if num in self.getPartNums():
            raise BlockDeviceErr_num()
        if not self.useParted:
            if (id in ID_EXTENDS) and (num > 4):
                raise BlockDeviceErr_extended()
            if intoExtended and num < 5:
                raise BlockDeviceErr_extended()
            if (not intoExtended) and (num > 4):
                raise BlockDeviceErr_extended()
        
        part = Partition(beg, end, id, num, bootable, self.sectorSize)
        if part.id in ID_EXTENDS:
            new_seg = BlockDeviceSegment(part.beg, part.end, self.sectorSize)
            part.children = [new_seg]
        self.__insert(part)
        return num
    
    # no allignment is performed
    def __insert(self, part):
        self.__insert2(part, self.__segs, False)
    def __insert2(self, part, segs, extended):
        for seg in segs:
            if (part.beg >= seg.beg) and (part.end <= seg.end):
                if seg.id in ID_EXTENDS:
                    self.__insert2(part, seg.children, True)
                    return
                elif seg.id == ID_EMPTY:
                    if extended:
                        if part.beg == seg.beg:
                            part.beg = part.beg + 1
                        new_part = Partition(part.beg-1, part.end, part.id, part.num, part.bootable, part.sectorSize)
                        new_seg = BlockDeviceSegment(new_part.beg, new_part.end, new_part.sectorSize)
                        new_part.children.append(new_seg)
                        self.__insert2(part, new_part.children, False)
                        part = new_part
                    if seg.beg < part.beg:
                        # add seg before
                        new_seg = BlockDeviceSegment(seg.beg, part.beg - 1, self.sectorSize)
                        segs.append(new_seg)
                    if seg.end > part.end:
                        # add seg after
                        new_seg = BlockDeviceSegment(part.end + 1, seg.end, self.sectorSize)
                        segs.append(new_seg)
                    # replace current seg with part
                    segs.remove(seg)
                    segs.append(part)
                    return
                else:
                    raise BlockDeviceErr_occupied()
        raise BlockDeviceErr_cannotFit()
    
    
    def remove(self, partNum):
        self.__sortSegs() # make sure to sort first
        self.__remove(partNum, self.__segs)
        self.__sortSegs()
    def __remove(self, partNum, segs):
        length = len(segs)
        for i in range(length):
            seg = segs[i]
            if seg.id == ID_EMPTY:
                continue
            if seg.num == partNum:
                beg = seg.beg
                end = seg.end
                remove_list = [seg]
                # merge with preceding empty segment
                if i-1 >= 0:
                    if segs[i-1].id == ID_EMPTY:
                        beg = segs[i-1].beg
                        remove_list.append(segs[i-1])
                # merge with following empty segment
                if i+1 < length:
                    if segs[i+1].id == ID_EMPTY:
                        end = segs[i+1].end
                        remove_list.append(segs[i+1])
                for rem in remove_list:
                    segs.remove(rem)
                new_seg = BlockDeviceSegment(beg, end, self.sectorSize)
                if (new_seg.beg == 1) and (new_seg.end == self.sectors - 1):
                    new_seg.wholeDevice = True
                segs.append(new_seg)
                return
            elif seg.id in ID_EXTENDS:
                self.__remove(partNum, seg.children)
        
    
    def printout(self):
        print('device: ' + self.dev)
        print(str(self.sectorSize * self.sectors), 'bytes,', str(self.sectors), 'sectors,', str(self.cyls), 'cylinders,', str(self.spt), 'sectors/track,', str(self.spc), 'sectors/cylinder')
        print('partitions:')
        for seg in self.__segs:
            seg.printout()

    
    def __alignLowerBound(self, num):
        if num == self.spt:
            return num
        val = (num / self.spc) * self.spc
        if num == val + 1:
            return num
        val = ((num + self.spc - 1) / self.spc) * self.spc
        if val < 1:
            val = 1
        return val
    def __alignUpperBound(self, num):
        if (num + 1) % self.spc == 0:
            return num
        else:
            return (num / self.spc) * self.spc - 1
    
    def __sortSegs(self):
        return self.__sortSegs2(self.__segs)
    def __sortSegs2(self, segs):
        for seg in segs:
            self.__sortSegs2(seg.children)
        for i in range(len(segs) - 1, 0, -1):
            for j in range(i):
                if segs[j].beg < segs[j+1].beg:
                    tmp = segs[j + 1]
                    segs[j + 1] = segs[j]
                    segs[j] = tmp
        segs.reverse()
        return segs
