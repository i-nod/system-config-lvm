
import sys
import re
from execute import execWithCapture, execWithCaptureStatus

from Partition import *
from fdisk_wrapper import FDisk


PARTED='/sbin/parted'


class Parted:
    
    def getPartitions(self, devpath):
        sectorSize = FDisk().getDeviceGeometry(devpath)[1]
        parts = list()
        
        args = [PARTED, devpath]
        if self.version() >= '1.6.23' :
            # parted versioned 1.6.23 and above has command "unit",
            # 1.6.22 and bellow displays in MBs
            args.append('unit')
            args.append('b')
        args.append('print')
        args.append('-s')
        res, status = execWithCaptureStatus(PARTED, args)
        if status != 0:
            msg = 'parted failed on ' + devpath
            print(msg)
            raise msg
        
        lines = res.splitlines()
        for line in lines:
            if not re.match('^[0-9]', line):
                continue
            words = line.split()
            if len(words) < 3:
                continue
            # partition num
            part_num = int(words[0])
            # beg, end
            beg = self.__to_bytes(words[1]) / sectorSize
            end = self.__to_bytes(words[2]) / sectorSize - 1
            # bootable
            bootable = False
            for word in words:
                if 'boot' in word:
                    bootable = True
            # partition id
            id = ID_UNKNOWN
            if 'lvm' in words:
                id = ID_LINUX_LVM
            elif 'raid' in words:
                id = 253
            else:
                for word in words:
                    if 'swap' in word:
                        id = ID_SWAPS[0]
            
            part = Partition(beg, end, id, part_num, bootable, sectorSize)
            parts.append(part)
        
        return parts
    
    
    
    def savePartTable(self, devpath, parts):
        if len(self.getPartitions(devpath)) != 0:
            print('partition table already exists')
            sys.exit(1)
        if len(parts) != 1:
            print('parted save implementation is not complete')
            sys.exit(1)
        
        # create partition table
        execWithCapture(PARTED, [PARTED, devpath, 'mklabel', 'gpt', '-s'])
        # create partition
        part = parts[0]
        beg = part.beg * part.sectorSize / 1024.0 / 1024 # parted uses Magabytes
        end = part.end * part.sectorSize / 1024.0 / 1024
        #print beg, end
        execWithCapture(PARTED, [PARTED, devpath, 'mkpart', 'primary', str(beg), str(end), '-s'])
        # add flags - if any
        if part.id == ID_LINUX_LVM:
            print(execWithCapture(PARTED, [PARTED, devpath, 'set', str(part.num), 'lvm', 'on', '-s']))




    def __to_bytes(self, word):
        # parted versioned 1.6.23 and above has command "unit",
        # 1.6.22 and below displays in MBs
        # this function handles both
        
        t = word.strip().lower()
        multiplier = 1024 * 1024
        if t.endswith('b') or t.endswith('B'):
            t = t.rstrip('b')
            t = t.rstrip('B')
            multiplier = 1
            if t.endswith('k') or t.endswith('K'):
                t = t.rstrip('k')
                t = t.rstrip('K')
                multiplier = 1024
            elif t.endswith('m') or t.endswith('M'):
                t = t.rstrip('M')
                t = t.rstrip('m')
                multiplier = 1024 * 1024
            elif t.endswith('g') or t.endswith('G'):
                t = t.rstrip('G')
                t = t.rstrip('g')
                multiplier = 1024 * 1024 * 1024
            elif t.endswith('t') or t.endswith('T'):
                t = t.rstrip('T')
                t = t.rstrip('t')
                multiplier = 1024 * 1024 * 1024 * 1024

        # avoid potentially losing precision due to floating
        # point multiplication if parted returned the units in
        # bytes (and, as a result, our multiplier is 1).
        # Note: this is not actually a problem in practice today. You'd
        # need an absolutely massive partition (about 89 petabyte) for any
        # loss of precision to occur.
        if multiplier == 1:
            return int(t)
        return int(float(t) * multiplier)


    def version(self):
        res, status = execWithCaptureStatus(PARTED, [PARTED, '-v'])
        res = res.strip()
        words = res.split()
        if len(words) != 3:
            raise Exception("unable to get parted version")
        return words[2]
