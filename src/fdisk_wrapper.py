
import os, sys
import re
from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus, execWithCaptureProgress, execWithCaptureErrorStatusProgress, execWithCaptureStatusProgress

from Partition import *


SFDISK='/sbin/sfdisk'
FDISK='/sbin/fdisk'
BLKID='/sbin/blkid'
BASH='/bin/bash'
LVDISPLAY='/sbin/lvdisplay'
    
TMP_FILE='/tmp/one_extremely_long_name_hoping_nobody_is_gona_use_it'



# all size values are in sectors

        

class FDisk:

    def getDeviceNames(self):
        res = execWithCapture(SFDISK, [SFDISK, '-s'])
        lines = res.splitlines()
        devices = list()
        for line in lines:
            if not re.match('^/dev/', line):
                continue
            words = line.split(':')
            devname = words[0].strip()
            if not re.match('.*[0-9]', devname):
                # check if partition table is OK       
                # out, err, ret = rhpl.executil.execWithCaptureErrorStatus(SFDISK, [SFDISK, '-V', devname])
                out, ret = execWithCaptureStatus(SFDISK, [SFDISK, '-V', devname])
                if ret != 0:
                    #print 'THERE IS A PROBLEM WITH PARTITION TABLE at device ' + devname
                    # print err
                    pass
                devices.append(devname)
        # check if geometry can be detected
        for dev in devices[:]:
            res = execWithCapture(SFDISK, [SFDISK, '-s', dev])
            if re.match('.*cannot get geometry.*', res):
                devices.remove(dev)

        # check with blkid to remove false PV (all logical volumes in /dev/mapper)
        for dev in devices[:]:
            out, ret = execWithCaptureStatus(BLKID, [BLKID, dev])
            if ret == 0:
                devices.remove(dev)
                continue
            out, ret = execWithCaptureStatus(LVDISPLAY, [LVDISPLAY, dev])
            if ret == 0:
                devices.remove(dev)
                continue
        
        return devices
    
    
    # returns [sectors, sectorSize, cylinders,  sectorsPerTrack, sectorsPerCylinder]
    def getDeviceGeometry(self, devname):
        sectors = None
        sectorSize = None
        spt = None
        spc = None
        cyls = None
        res = execWithCapture(FDISK, [FDISK, '-l', '-u', devname])
        lines = res.splitlines()
        for line in lines:
            if re.match('^Units = sectors .* [0-9]* bytes', line):
                words = line.split()
                if (words[len(words) - 1] == 'bytes'):
                    sectorSize = int(words[len(words) - 2])
                else:
                    raise 'bad fdisk output for device ' + devname
            elif re.match('.* [0-9]* sectors/track, [0-9]* cylinders, total [0-9]* sectors', line):
                words = line.split()
                if (words[len(words) - 1] == 'sectors') and (words[len(words) - 3] == 'total'):
                    sectors = int(words[len(words) - 2])
                else:
                    raise 'bad fdisk output for device ' + devname
                if words[3].rstrip(',') == 'sectors/track':
                    spt = int(words[2])
                else:
                    raise 'bad fdisk output for device ' + devname
                if words[5].rstrip(',') == 'cylinders':
                    cyls = int(words[4])
                else:
                    raise 'bad fdisk output for device ' + devname
        if sectors == None or sectorSize == None or spt == None or cyls == None:
            raise 'bad fdisk output for device ' + devname
        return [sectors, sectorSize, cyls, spt, sectors/cyls]
    
    
    def getPartitions(self, devname):
        sectorSize = self.getDeviceGeometry(devname)[1]
        parts = list()
        res = execWithCapture(SFDISK, [SFDISK, '-l', '-uS', devname])
        lines = res.splitlines()
        for line in lines:
            if not re.match('^/dev/', line):
                continue
            words = line.split()
            # partition num
            tmp = words[0].strip()
            try:
                part_num = int(tmp[len(devname):])
            except ValueError:
                continue
            del(words[0])
            # bootable
            if words[0] == '*':
                bootable = True
                del(words[0])
            else:
                bootable = False
            beg, end, ignore, id = words[:4]
            # beg
            if beg == '-':
                continue
            else:
                beg = int(beg)
            #end
            if end == '-':
                continue
            else:
                end = int(end)
            # partition id
            id = int(id, 16)
            part = Partition(beg, end, id, part_num, bootable, sectorSize)
            parts.append(part)
        return parts
    
    
    def savePartTable(self, devname, parts):
        new_parts = []
        for part in parts:
            if part.id != ID_EMPTY:
                new_parts.append(part)
                if part.id in ID_EXTENDS:
                    for p in part.children:
                        if p.id != ID_EMPTY:
                            new_parts.append(p)
        parts = new_parts
        
        # make sure all partitions are in the list
        max = 0
        for part in parts:
            if part.num > max:
                max = part.num
        part_nums = list()
        for part in parts:
            part_nums.append(part.num)
        for i in range(1, max + 1):
            if i not in part_nums:
                if i < 5:
                    p = Partition(0, 0, ID_EMPTY, i, False, 0)
                    parts.append(p)
                else:
                    print('A gap in extended partition nums for', devname + '!!!')
                    sys.exit()
        
        # sort parts
        for i in range(len(parts) - 1, 0, -1):
            for j in range(i):
                if parts[j].num > parts[j+1].num:
                    tmp = parts[j + 1]
                    parts[j + 1] = parts[j]
                    parts[j] = tmp    
        
        # create sfdisk's input
        commands = list()
        for part in parts:
            if part.id == ID_EMPTY:
                beg = ''
                size = '0'
            else:
                beg = str(part.beg)
                size = str(part.getSize())
            id = hex(part.id)[2:]
            boot = '-'
            if part.bootable:
                boot = '*'
            
            commands.append(beg + ',' + size + ',' + id + ',' + boot)
        
        # write to disk
        TMP_FILE_INPUT = TMP_FILE + '_input'
        file = open(TMP_FILE_INPUT, 'w')
        for command in commands:
            file.write(command + '\n')
            #print command
        file.flush()
        file.close()
        TMP_FILE_COMMAND = TMP_FILE + '_command'
        file = open(TMP_FILE_COMMAND, 'w')
        file.write('#!' + BASH + '\n')
        file.write(SFDISK + ' -uS -L -f ' + devname + ' < ' + TMP_FILE_INPUT + '\n')
        file.flush()
        file.close()
        os.chmod(TMP_FILE_COMMAND, 0o700)
        #print 'commiting partitions to disk ' + devname
        
        if len(self.getPartitions(devname)) == 0:
            # no existing partitions, write
            out, ret = execWithCaptureStatusProgress(TMP_FILE_COMMAND, [TMP_FILE_COMMAND], _("Please wait while partition is being created"))
            #print out, ret
        else:
            # there is something on drive, ignore for now
            #print 'joking :)'
            #print 'for now'
            pass
        
        os.remove(TMP_FILE_COMMAND)
        os.remove(TMP_FILE_INPUT)
        
    
    def printSupportedPartitions(self):
        result = execWithCapture(SFDISK, [SFDISK, '-T'])
        lines = result.splitlines()
        for line in lines:
            if 'Id' in line:
                continue
            if line.strip() == '':
                continue
            id = int(line[:2].strip(), 16)
            name = line[2:].strip()
            print(str(id), ':', '\'' + name + '\'' + ',')
