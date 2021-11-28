
import sys
import os
import re

import Filesystem

from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus
from utilities import follow_links_to_target


DEVICE = 0
MOUNTPOINT = 1
FSTYPE = 2
OPTIONS = 3
DUMP = 4
FSCK = 5


FSTAB = '/etc/fstab'
FSTAB_TMP = '/etc/fstab.tmp.system-config-lvm'

    
def add(dev_path_old, dev_path, mnt_point, fstype, options='defaults', dump='1', fsck='2'):
    line = dev_path + '\t\t' + mnt_point + '\t\t' + fstype + '\t' + options
    line = line + '\t' + dump + ' ' + fsck
    
    fstab = __remove_and_replace(dev_path_old, line)
    fstab.close()    
    os.rename(FSTAB_TMP, FSTAB)
    
def remove(mnt_device):
    fstab = __remove_and_replace(mnt_device, None)
    fstab.close()
    os.rename(FSTAB_TMP, FSTAB)
    
def __remove_and_replace(mnt_device, new_line):
    added = False

    fstab = open(FSTAB, 'r')
    lines = fstab.readlines()
    fstab.close()

    if (mnt_device != None):
        paths = get_all_paths(mnt_device)
    else:
        paths = []
    
    fstab_new = open(FSTAB_TMP, 'w')
    for line in lines:
        line = line.strip().rstrip('\n')
        words = line.split(' ')
        words_new = []
        for word in words:
            for w in word.split('\t'):
                if w != '':
                    words_new.append(w)
        words = words_new
        
        if len(words) != 6:
            fstab_new.write(line + '\n')
            continue
        
        if words[0] == '#':
            fstab_new.write(line + '\n')
            continue
        
        if words[DEVICE] in paths:
            # line needs to be removed/replaced
            if (new_line != None) and (added == False):
              fstab_new.write(new_line + '\n')
              added = True
            pass
        else:
            fstab_new.write(line + '\n')
            
    if (new_line != None) and (added == False):
      fstab_new.write(new_line + '\n')
            
    return fstab_new


def get_mountpoint(dev_path):
    opt = get_mount_options(dev_path)
    return opt[MOUNTPOINT]

def get_mount_options(dev_path):
    if dev_path == None:
        return (None, None, None, None, None, None)
    
    paths = get_all_paths(dev_path)
    
    fstab = open(FSTAB, 'r')
    lines = fstab.readlines()
    fstab.close()
    for line in lines:
        line = line.strip().rstrip('\n')
        words = line.split(' ')
        words_new = []
        for word in words:
            for w in word.split('\t'):
                if w != '':
                    words_new.append(w)
        words = words_new
        
        if len(words) != 6:
            continue
        if words[0] == '#':
            continue
        
        if words[DEVICE] in paths:
            return words

    return (None, None, None, None, None, None)

def get_all_paths(dev_path):
    paths = [dev_path]
    follow_links_to_target(dev_path, paths)
    label = Filesystem.get_fs(dev_path).get_label(dev_path)
    if label != None:
        paths.append('LABEL=' + label)

    ## in new distributions there is no link from /dev/vg/lv
    ## to /dev/mapper/vg-lv - so we will try to map it directly
    regex = re.compile("^/dev\/([^\/]*?)\/([^\/]*?)$")
    append_paths = []
    for p in paths:
        r = regex.search(p)
        if r != None:
            append_paths.append("/dev/mapper/" + r.groups()[0].replace("-", "--") + "-" + r.groups()[1].replace("-", "--"))

    if append_paths != None:
        paths.extend(append_paths)

    return paths
