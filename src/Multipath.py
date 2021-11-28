
import os

from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus, execWithCaptureProgress, execWithCaptureErrorStatusProgress, execWithCaptureStatusProgress

from lvmui_constants import *

MULTIPATH_BIN='/sbin/multipath'
DMSETUP_BIN='/sbin/dmsetup'
LS_BIN='/bin/ls'


class Multipath:
    
    def __init__(self):
        pass
    
    # {multipath_access_path:[dev1, dev2, ...], ... }
    def get_multipath_data(self):
        multipath_data = {}
        
        dmsetup_lines = None
        if os.access(DMSETUP_BIN, os.F_OK):
            args = list()
            args.append(DMSETUP_BIN)
            args.append('table')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus(DMSETUP_BIN, args)
            if r != 0:
                raise CommandError('FATAL', COMMAND_FAILURE % ("dmsetup",cmdstr, e))
            dmtable_lines = o.splitlines()
        else:
            return multipath_data
        
        args = list()
        args.append(LS_BIN)
        args.append('-l')
        args.append('--time-style=long-iso')
        args.append('/dev/')
        cmdstr = ' '.join(args)
        o,e,r = execWithCaptureErrorStatus(LS_BIN, args)
        if r != 0:
            raise CommandError('FATAL', COMMAND_FAILURE % ("ls",cmdstr, e))
        ls_lines = o.splitlines()
        
        # get block devices
        block_devices = []
        for line in ls_lines:
            words = line.split()
            if len(words) == 0:
                continue
            if words[0][0] == 'b':
                # [name, major, minor]
                block_devices.append(['/dev/' + words[8], words[4].rstrip(','), words[5]])
        
        # process dmsetup table
        for line in dmtable_lines:
            if len(line) == 0:
                continue
            words = line.split()
            if 'multipath' not in words:
                continue
            
            # get origin
            args = list()
            args.append(DMSETUP_BIN)
            args.append('info')
            args.append('-c')
            args.append('-o name,major,minor')
            args.append('--noheadings')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus(DMSETUP_BIN, args)
            if r != 0:
                raise CommandError('FATAL', COMMAND_FAILURE % ("dmsetup",cmdstr, e))
            origin = None
            origin_name = words[0].rstrip(':')
            for or_line in o.splitlines():
                or_words = or_line.split(':')
                if or_words[0] == origin_name:
                    major = or_words[1].strip()
                    minor = or_words[2].strip()
                    for l in block_devices:
                        if l[1] == major and l[2] == minor:
                            origin = l[0]
                            break
                    break
            if origin == None:
                origin = '/dev/mapper/' + origin_name
            
            devices = []
            for word in words[1:]:
                if ':' in word:
                    idx = word.find(':')
                    major = word[:idx]
                    minor = word[idx+1:]
                    for bd in block_devices:
                        if bd[1] == major and bd[2] == minor:
                            devices.append(bd[0])
            if len(devices) == 0:
                print('multipath error: ' + origin + str(devices))
                continue
            
            multipath_data[origin] = devices
        
        return multipath_data
