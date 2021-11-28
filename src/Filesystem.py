
import re
import os

from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus, execWithCaptureProgress, execWithCaptureErrorStatusProgress, execWithCaptureStatusProgress
from CommandError import *

from Cluster import Cluster


import xml
import xml.dom
from xml.dom import minidom

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from lvmui_constants import PROGNAME, INSTALLDIR


CREATING_FS=_("Creating %s filesystem")
RESIZING_FS=_("Resizing %s filesystem")
CHECKING_FS=_("Checking %s filesystem")
UPGRADING_FS=_("Upgrading %s filesystem to %s")
FSCREATE_FAILURE=_("Creation of filesystem failed. Command attempted: \"%s\" - System Error Message: %s")
FSRESIZE_FAILURE=_("Resize of filesystem failed. Command attempted: \"%s\" - System Error Message: %s")
FSCHECK_FAILURE=_("Check of filesystem failed. Command attempted: \"%s\" - System Error Message: %s")
FSUPGRADE_FAILURE=_("Upgrade of filesystem failed. Command attempted: \"%s\" - System Error Message: %s")
gfs_types = {"1309":"gfs","1801":"gfs2"}
cache_mountable_fs = { }
cache_file_results = { }
resize2fs_v139plus = None

def get_fs(path):
    for fs in get_filesystems():
        if fs.probe(path):
            return fs

    if path not in cache_file_results:
        result = execWithCapture("/usr/bin/file", ['/usr/bin/file', '-s', '-L', path])
        cache_file_results[path] = result
    else:
        result = cache_file_results[path]
        
    if re.search('FAT \(12 bit\)', result, re.I):
        return Unknown('vfat12')
    elif re.search('FAT \(16 bit\)', result, re.I):
        return Unknown('vfat16')
    elif re.search('FAT \(32 bit\)', result, re.I):
        return Unknown('vfat32')
    elif re.search('minix', result, re.I):
        return Unknown('minix')
    elif re.search('jfs', result, re.I):
        return Unknown('jfs')
    elif re.search('reiserfs', result, re.I):
        return Unknown('reiserfs')
    elif re.search('swap', result, re.I):
        return Unknown('swap')
    else:
        return NoFS()
    

def get_filesystems():
    # NoFS has to be first
    return [NoFS(), ext4(), ext3(), ext2(), gfs2(), gfs2_clustered(), gfs(), gfs_clustered(), xfs()]


class Filesystem:
    def __init__(self, name, creatable, editable, mountable,
                 extendable_online, extendable_offline,
                 reducible_online, reducible_offline,
                 fsname):
        self.name = name
        self.fsname = fsname
        
        self.creatable = creatable
        self.editable = editable
        self.mountable = mountable
        
        self.extendable_online = extendable_online and mountable
        self.extendable_offline = extendable_offline
        self.reducible_online = reducible_online and mountable
        self.reducible_offline = reducible_offline
        
        self.upgradable = False
        
    
    def create(self, path):
        pass
    
    def extend_online(self, dev_path):
        pass
    
    def extend_offline(self, dev_path):
        pass
    
    def reduce_online(self, dev_path, new_size_bytes):
        pass
    
    def reduce_offline(self, dev_path, new_size_bytes):
        pass
    
    def set_options(self, devpath):
        pass
    def change_options(self, devpath):
        pass
    
    def get_label(self, devpath):
        return None
    
    def probe(self, path):
        return False
    
    def set_clustered(self, clustered):
        return

    def check_mountable(self, fsname, module):
        global cache_mountable_fs

        if fsname in cache_mountable_fs:
          return cache_mountable_fs[fsname]

        mountable = False
        out = execWithCapture('/bin/cat', ['/bin/cat', '/proc/filesystems'])
        if re.search(fsname, out, re.I):
            mountable = True
        if mountable == False:
            out, status = execWithCaptureStatus('/sbin/modprobe', ['/sbin/modprobe', '-n', module])
            if status == 0:
                mountable = True
        cache_mountable_fs[fsname] = mountable
        return mountable
    
    def check_path(self, path):
        if os.access(path, os.F_OK):
            return True
        else:
            return False
    def check_paths(self, paths):
        for path in paths:
            if self.check_path(path) == False:
                return False
        return True
    

class NoFS(Filesystem):
    def __init__(self):
        Filesystem.__init__(self, _('None'), True, False, False, 
                            True, True, True, True,
                            'none')
        

class Unknown(Filesystem):
    def __init__(self, name=_('Unknown filesystem'), mountable=False):
        Filesystem.__init__(self, name, False, False, mountable,
                            False, False, False, False,
                            'unknown')
        
        
class ext4(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/mkfs.ext4')
        mountable = self.check_mountable('ext4', 'ext4')
        resize_offline = self.check_paths(['/sbin/e2fsck', '/sbin/resize2fs'])
        extend_online = self.check_path('/sbin/resize2fs')

        Filesystem.__init__(self, 'Ext4', creatable, True, mountable,
                            extend_online, resize_offline, False, resize_offline,
                            'ext4')


    def probe(self, path):
        if path not in cache_file_results:
            result = execWithCapture("/usr/bin/file", ['/usr/bin/file', '-s', '-L', path])
            cache_file_results[path] = result
        else:
            result = cache_file_results[path]

        if re.search('ext4', result, re.I):
            return True

    # Note, you may need a test for new-enough e2fsprogs for ext4
    def create(self, path):
        args = list()
        args.append("/sbin/mkfs")
        args.append("-t")
        args.append('ext4')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress("/sbin/mkfs", args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))

    def extend_online(self, dev_path):
        cmd = '/sbin/resize2fs'
        args = [cmd, dev_path]
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o, e, s = execWithCaptureErrorStatusProgress(cmd, args, msg)
        if s != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr, e))

    def reduce_online(self, dev_path, new_size_bytes):
        # not supported
        raise 'NOT supported'

    def extend_offline(self, dev_path):
        # first check fs (resize2fs requirement)
        args = list()
        args.append('/sbin/e2fsck')
        args.append('-f')
        args.append('-p') # repair fs
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = CHECKING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/e2fsck', args, msg)
        if not (r==0 or r==1):
            raise CommandError('FATAL', FSCHECK_FAILURE % (cmdstr,e))

        args = list()
        args.append('/sbin/resize2fs')
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/resize2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))

    def reduce_offline(self, dev_path, new_size_bytes):
        # first check fs (resize2fs requirement)
        args = list()
        args.append('/sbin/e2fsck')
        args.append('-f')
        args.append('-p') # repair fs
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = CHECKING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/e2fsck', args, msg)
        if not (r==0 or r==1):
            raise CommandError('FATAL', FSCHECK_FAILURE % (cmdstr,e))

        new_size_kb = new_size_bytes / 1024
        args = list()
        args.append('/sbin/resize2fs')
        args.append(dev_path)
        args.append(str(new_size_kb) + 'K')
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/resize2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))

    def get_label(self, devpath):
        args = ['/sbin/tune2fs']
        args.append('-l')
        args.append(devpath)
        o, r = execWithCaptureStatus('/sbin/tune2fs', args)
        if r == 0:
            lines = o.splitlines()
            for line in lines:
                if re.search('volume name', line, re.I):
                    words = line.split()
                    label = words[len(words) - 1]
                    if re.match('<none>', label, re.I):
                        return None
                    else:
                        return label
        return None

class ext3(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/mkfs.ext3')
        mountable = self.check_mountable('ext3', 'ext3')
        resize_offline = self.check_paths(['/sbin/e2fsck', '/sbin/resize2fs'])
        extend_online, dummy = self.__extend_online_cmd()
        
        Filesystem.__init__(self, 'Ext3', creatable, True, mountable, 
                            extend_online, resize_offline, False, resize_offline,
                            'ext3')
        
    
    def probe(self, path):
        if path not in cache_file_results:
            result = execWithCapture("/usr/bin/file", ['/usr/bin/file', '-s', '-L', path])
            cache_file_results[path] = result
        else:
            result = cache_file_results[path]

        if re.search('ext3', result, re.I):
            return True
    
    def create(self, path):
        args = list()
        args.append("/sbin/mkfs")
        args.append("-t")
        args.append('ext3')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress("/sbin/mkfs", args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))
    
    def extend_online(self, dev_path):
        dummy, cmd = self.__extend_online_cmd()
        args = [cmd, dev_path]
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o, e, s = execWithCaptureErrorStatusProgress(cmd, args, msg)
        if s != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr, e))
    def __extend_online_cmd(self):
        global resize2fs_v139plus;
        
        # if ext2online is present, use it
        cmd = '/usr/sbin/ext2online'
        if self.check_path(cmd):
            return (True, cmd)
        # resize2fs 1.39 and above are also able to online extend ext3
        try:
            cmd = '/sbin/resize2fs'
            if resize2fs_v139plus != None:
                return (True, cmd)
            
            o, e, s = execWithCaptureErrorStatus(cmd, [cmd])
            if (s == 0 or s == 1) and float(e.strip().split()[1]) >= 1.39:
                resize2fs_v139plus = True
                return (True, cmd)
            else:
                resize2fs_v139plus = False
        except:
            pass
        return (False, None)
    
    def reduce_online(self, dev_path, new_size_bytes):
        # not supported
        raise 'NOT supported'
    
    def extend_offline(self, dev_path):
        # first check fs (resize2fs requirement)
        args = list()
        args.append('/sbin/e2fsck')
        args.append('-f')
        args.append('-p') # repair fs
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = CHECKING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/e2fsck', args, msg)
        if not (r==0 or r==1):
            raise CommandError('FATAL', FSCHECK_FAILURE % (cmdstr,e))
        
        args = list()
        args.append('/sbin/resize2fs')
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/resize2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
        
    def reduce_offline(self, dev_path, new_size_bytes):
        # first check fs (resize2fs requirement)
        args = list()
        args.append('/sbin/e2fsck')
        args.append('-f')
        args.append('-p') # repair fs
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = CHECKING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/e2fsck', args, msg)
        if not (r==0 or r==1):
            raise CommandError('FATAL', FSCHECK_FAILURE % (cmdstr,e))
        
        new_size_kb = new_size_bytes / 1024
        args = list()
        args.append('/sbin/resize2fs')
        args.append(dev_path)
        args.append(str(new_size_kb) + 'K')
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/resize2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
    
    def get_label(self, devpath):
        args = ['/sbin/tune2fs']
        args.append('-l')
        args.append(devpath)
        o, r = execWithCaptureStatus('/sbin/tune2fs', args)
        if r == 0:
            lines = o.splitlines()
            for line in lines:
                if re.search('volume name', line, re.I):
                    words = line.split()
                    label = words[len(words) - 1]
                    if re.match('<none>', label, re.I):
                        return None
                    else:
                        return label
        return None
    

class ext2(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/mkfs.ext2')
        mountable = self.check_mountable('ext2', 'ext2')
        resize_offline = self.check_paths(['/sbin/e2fsck', '/sbin/resize2fs'])
        
        Filesystem.__init__(self, 'Ext2', creatable, True, mountable, 
                            False, resize_offline, False, resize_offline,
                            'ext2')
        self.upgradable = True
        
    
    def probe(self, path):
        if path not in cache_file_results:
            result = execWithCapture("/usr/bin/file", ['/usr/bin/file', '-s', '-L', path])
            cache_file_results[path] = result
        else:
            result = cache_file_results[path]

        if re.search('ext2', result, re.I):
            return True
    
    def create(self, path):
        args = list()
        args.append("/sbin/mkfs")
        args.append("-t")
        args.append('ext2')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress("/sbin/mkfs", args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))
    
    def extend_online(self, dev_path):
        # not supported
        raise 'NOT supported'
    
    def reduce_online(self, dev_path, new_size_bytes):
        # not supported
        raise 'NOT supported'
    
    def extend_offline(self, dev_path):
        # first check fs (resize2fs requirement)
        args = list()
        args.append('/sbin/e2fsck')
        args.append('-f')
        args.append('-p') # repair fs
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = CHECKING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/e2fsck', args, msg)
        if not (r==0 or r==1):
            raise CommandError('FATAL', FSCHECK_FAILURE % (cmdstr,e))
        
        args = list()
        args.append('/sbin/resize2fs')
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/resize2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
        
    def reduce_offline(self, dev_path, new_size_bytes):
        # first check fs (resize2fs requirement)
        args = list()
        args.append('/sbin/e2fsck')
        args.append('-f')
        args.append('-p') # repair fs
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = CHECKING_FS % self.name
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/e2fsck', args, msg)
        if not (r==0 or r==1):
            raise CommandError('FATAL', FSCHECK_FAILURE % (cmdstr,e))
        
        new_size_kb = new_size_bytes / 1024
        args = list()
        args.append('/sbin/resize2fs')
        args.append(dev_path)
        args.append(str(new_size_kb) + 'K')
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/resize2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
    
    def upgrade(self, dev_path):
        args = ['/sbin/tune2fs']
        args.append('-j')
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = UPGRADING_FS % (self.name, ext3().name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/tune2fs', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSUPGRADE_FAILURE % (cmdstr,e))
    
    def get_label(self, devpath):
        args = ['/sbin/tune2fs']
        args.append('-l')
        args.append(devpath)
        o, r = execWithCaptureStatus('/sbin/tune2fs', args)
        if r == 0:
            lines = o.splitlines()
            for line in lines:
                if re.search('volume name', line, re.I):
                    words = line.split()
                    label = words[len(words) - 1]
                    if re.match('<none>', label, re.I):
                        return None
                    else:
                        return label
        return None
    


class gfs(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/gfs_mkfs')
        mountable = self.check_mountable('gfs', 'gfs')
        extendable_online = self.check_path('/sbin/gfs_grow')
        
        Filesystem.__init__(self, _("GFS (local)"), creatable, False, mountable, 
                            extendable_online, False, False, False,
                            'gfs')
        
    
    def probe(self, path):
        l_type = self.__get_gfs_lock_type(path)
        if l_type == 'nolock':
            gfs_type = self.__get_gfs_fstype(path)
            if gfs_type == 'gfs':
                return True
        return False

    
    def create(self, path):
        MKFS_GFS_BIN='/sbin/gfs_mkfs'
        args = [MKFS_GFS_BIN]
        args.append('-j')
        args.append('1')
        args.append('-p')
        args.append('lock_nolock')
        args.append('-O')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress(MKFS_GFS_BIN, args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))
    
    def extend_online(self, dev_path):
        args = ['/sbin/gfs_grow']
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/gfs_grow', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
    
    def set_clustered(self, clustered):
        if clustered:
            self.creatable = False
    
    def __get_gfs_lock_type(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('proto')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                if 'lock_dlm' in o:
                    return 'dlm'
                elif 'lock_gulm' in o:
                    return 'gulm'
                elif 'nolock' in o:
                    return 'nolock'
        return None

    def __get_gfs_fstype(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('ondisk')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                for k,v in gfs_types.items():
                    if k in o: 
                        return v
        return None
    


class gfs_clustered(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/gfs_mkfs')
        mountable = self.check_mountable('gfs', 'gfs')
        extendable_online = self.check_path('/sbin/gfs_grow')
        
        # gui stuff
        gladepath = 'Filesystem.glade'
        if not os.path.exists(gladepath):
            gladepath = "%s/%s" % (INSTALLDIR, gladepath)
        self.glade_xml = Gtk.Builder()
        self.glade_xml.add_from_file(gladepath)
        self.dlg = self.glade_xml.get_object('new_gfs_props')
        
        self.clustername_entry  = self.glade_xml.get_object('clustername')
        self.gfsname_entry      = self.glade_xml.get_object('gfsname')
        self.journals_spin      = self.glade_xml.get_object('journals')
        self.lock_dlm_butt      = self.glade_xml.get_object('lock_dlm')
        self.lock_gulm_butt     = self.glade_xml.get_object('lock_gulm')
        self.locking_box        = self.glade_xml.get_object('locking_box')
        
        # populate new GFS form
        clustername = self.__get_cluster_name()
        nodes_num = self.__get_cluster_nodes_num()
        lock_type = self.__get_cluster_lock_type()
        if clustername != None:
            self.clustername_entry.set_text(clustername)
            self.journals_spin.set_value(nodes_num)
            if lock_type == 'dlm':
                self.lock_dlm_butt.set_active(True)
            elif lock_type == 'gulm':
                self.lock_gulm_butt.set_active(True)
            self.clustername_entry.set_sensitive(False)
            self.locking_box.set_sensitive(False)
            pass
        
        # mountable only if cluster is quorate, and kernel supports GFS
        if mountable:
            mountable = self.__is_cluster_running(clustername)
        
        Filesystem.__init__(self, _("GFS (clustered)"), creatable, False, mountable, 
                            extendable_online, False, False, False,
                            'gfs')
    
    def probe(self, path):
        gfs_lock = self.__get_gfs_lock_type(path)
        if gfs_lock == 'dlm' or gfs_lock == 'gulm':
            if self.mountable:
                c_name = self.__get_cluster_name()
                c_lock = self.__get_cluster_lock_type()
                c_running = self.__is_cluster_running(c_name)
                gfs_clustername = self.__get_gfs_table_name(path)[0]
                self.mountable = (gfs_clustername == c_name) and c_running and (gfs_lock == c_lock)
            gfs_type = self.__get_gfs_fstype(path)
            if gfs_type == "gfs":
                return True
        return False
 
    def create(self, path):
        if not self.creatable:
            raise "not creatable"
        
        try:
            valid = False
            while not valid:
                rc = self.dlg.run()
                if rc == Gtk.ResponseType.OK:
                    valid = True
                    msg = ''
                    illegal_chars = ';:\'"/?.>,<]}[{ =+)(*&^%$#@!`~'
                    c_name = self.clustername_entry.get_text().strip()
                    g_name = self.gfsname_entry.get_text().strip()
                    for c in illegal_chars:
                        if c in c_name:
                            msg = _("Cluster name contains illegal character " + c)
                            valid = False
                        if c in g_name:
                            msg = _("GFS name contains illegal character " + c)
                            valid = False
                    if len(c_name) == 0:
                        msg = _("Missing Cluster Name")
                        valid = False
                    elif len(g_name) == 0:
                        msg = _("Missing GFS Name")
                        valid = False
                    if not valid:
                        self.__errorMessage(msg)
                    else:
                        j_num = self.journals_spin.get_value_as_int()
                        table = c_name + ':' + g_name
                        locking_type = 'lock_'
                        if self.lock_dlm_butt.get_active():
                            locking_type += 'dlm'
                        elif self.lock_gulm_butt.get_active():
                            locking_type += 'gulm'
        except:
            self.dlg.hide()
            raise
        self.dlg.hide()
        
        MKFS_GFS_BIN='/sbin/gfs_mkfs'
        args = [MKFS_GFS_BIN]
        args.append('-j')
        args.append(str(j_num))
        args.append('-p')
        args.append(locking_type)
        args.append('-t')
        args.append(table)
        args.append('-O')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress(MKFS_GFS_BIN, args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))
    
    def extend_online(self, dev_path):
        args = ['/sbin/gfs_grow']
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/gfs_grow', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
    
    def set_clustered(self, clustered, path=None):
        pass
    
    
    def __get_gfs_lock_type(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('proto')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                if 'lock_dlm' in o:
                    return 'dlm'
                elif 'lock_gulm' in o:
                    return 'gulm'
                elif 'nolock' in o:
                    return 'nolock'
        return None
    def __get_gfs_table_name(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('table')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                words = o.strip().split()
                if len(words) == 6:
                    return words[5].strip('\"').split(':')
        return (None, None)
    
    def __get_cluster_name(self):
        return Cluster().get_name()
    def __get_cluster_lock_type(self):
        return Cluster().get_lock_type()
    def __get_cluster_nodes_num(self):
        return Cluster().get_nodes_num()
    def __is_cluster_running(self, clustername):
        if clustername == None:
            return False
        return Cluster().running()
    
    def __errorMessage(self, message):
        dlg = Gtk.MessageDialog(None, 0,
                                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                message)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()
        return rc

    def __get_gfs_fstype(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('ondisk')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                for k,v in gfs_types.items():
                    if k in o:
                        return v
        return None

class xfs(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/mkfs.xfs')
        mountable = self.check_mountable('xfs', 'xfs')
        extend_online = self.check_path('/usr/sbin/xfs_growfs')

        Filesystem.__init__(self, 'XFS', creatable, True, mountable,
                            extend_online, False, False, False,
                            'xfs')

    def probe(self, path):
        if path not in cache_file_results:
            result = execWithCapture("/usr/bin/file", ['/usr/bin/file', '-s', '-L', path])
            cache_file_results[path] = result
        else:
            result = cache_file_results[path]

        if re.search('SGI XFS', result, re.I):
            return True

    def create(self, path):
        args = list()
        args.append("/sbin/mkfs")
        args.append("-t")
        args.append('xfs')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress("/sbin/mkfs", args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))

    def extend_online(self, dev_path):
        cmd = '/usr/sbin/xfs_growfs'
        args = [cmd, dev_path]
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o, e, s = execWithCaptureErrorStatusProgress(cmd, args, msg)
        if s != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr, e))

    def reduce_online(self, dev_path, new_size_bytes):
        # not supported
        raise 'NOT supported'

    def extend_offline(self, dev_path):
        # not supported
        raise 'NOT supported'

    def reduce_offline(self, dev_path, new_size_bytes):
        # not supported
        raise 'NOT supported'

    def get_label(self, devpath):
        args = ['/usr/sbin/xfs_admin']
        args.append('-l')
        args.append(devpath)
        o, r = execWithCaptureStatus('/usr/sbin/xfs_admin', args)
        if r == 0:
            words = o.split()
            label = re.sub('\"', '', words[len(words) - 1])
            if label:
                return label
            return None
        return None
    


class gfs2(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/gfs2_mkfs')
        mountable = self.check_mountable('gfs2', 'gfs2')
        extendable_online = self.check_path('/sbin/gfs2_grow')
        
        Filesystem.__init__(self, _("GFS2 (local)"), creatable, False, mountable, 
                            extendable_online, False, False, False,
                            'gfs2')
        
    
    def probe(self, path):
        l_type = self.__get_gfs_lock_type(path)
        if l_type == 'nolock':
            gfs_type = self.__get_gfs_fstype(path)
            if gfs_type == "gfs2":
                return True
        return False
    
    def create(self, path):
        MKFS_GFS_BIN='/sbin/gfs2_mkfs'
        args = [MKFS_GFS_BIN]
        args.append('-j')
        args.append('1')
        args.append('-p')
        args.append('lock_nolock')
        args.append('-O')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress(MKFS_GFS_BIN, args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))
    
    def extend_online(self, dev_path):
        args = ['/sbin/gfs2_grow']
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/gfs2_grow', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
    
    def set_clustered(self, clustered):
        if clustered:
            self.creatable = False
    
    def __get_gfs_lock_type(self, path):
        if self.check_path('/sbin/gfs2_tool'):
            args = ['/sbin/gfs2_tool']
            args.append('sb')
            args.append(path)
            args.append('proto')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs2_tool', args)
            if r == 0:
                if 'lock_dlm' in o:
                    return 'dlm'
                elif 'lock_gulm' in o:
                    return 'gulm'
                elif 'nolock' in o:
                    return 'nolock'
        return None
    
    def __get_gfs_fstype(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('ondisk')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                for k,v in gfs_types.items():
                    if k in o: 
                        return v
        return None



class gfs2_clustered(Filesystem):
    def __init__(self):
        creatable = self.check_path('/sbin/gfs2_mkfs')
        mountable = self.check_mountable('gfs2', 'gfs2')
        extendable_online = self.check_path('/sbin/gfs2_grow')
        
        # gui stuff
        gladepath = 'Filesystem.glade'
        if not os.path.exists(gladepath):
            gladepath = "%s/%s" % (INSTALLDIR, gladepath)
        #gtk.glade.bindtextdomain(PROGNAME)
        self.glade_xml = Gtk.Builder()
        self.glade_xml.add_from_file(gladepath)
        self.dlg = self.glade_xml.get_object('new_gfs_props')
        
        self.clustername_entry  = self.glade_xml.get_object('clustername')
        self.gfsname_entry      = self.glade_xml.get_object('gfsname')
        self.journals_spin      = self.glade_xml.get_object('journals')
        self.lock_dlm_butt      = self.glade_xml.get_object('lock_dlm')
        self.lock_gulm_butt     = self.glade_xml.get_object('lock_gulm')
        self.locking_box        = self.glade_xml.get_object('locking_box')
        
        # populate new GFS form
        clustername = self.__get_cluster_name()
        nodes_num = self.__get_cluster_nodes_num()
        lock_type = self.__get_cluster_lock_type()
        if clustername != None:
            self.clustername_entry.set_text(clustername)
            self.journals_spin.set_value(nodes_num)
            if lock_type == 'dlm':
                self.lock_dlm_butt.set_active(True)
            elif lock_type == 'gulm':
                self.lock_gulm_butt.set_active(True)
            self.clustername_entry.set_sensitive(False)
            self.locking_box.set_sensitive(False)
            pass
        
        # mountable only if cluster is quorate, and kernel supports GFS
        if mountable:
            mountable = self.__is_cluster_running(clustername)
        
        Filesystem.__init__(self, _("GFS2 (clustered)"), creatable, False, mountable, 
                            extendable_online, False, False, False,
                            'gfs2')
    
    def probe(self, path):
        gfs_lock = self.__get_gfs_lock_type(path)
        if gfs_lock == 'dlm' or gfs_lock == 'gulm':
            if self.mountable:
                c_name = self.__get_cluster_name()
                c_lock = self.__get_cluster_lock_type()
                c_running = self.__is_cluster_running(c_name)
                gfs_clustername = self.__get_gfs_table_name(path)[0]
                self.mountable = (gfs_clustername == c_name) and c_running and (gfs_lock == c_lock)
            gfs_type = self.__get_gfs_fstype(path)
            if gfs_type == "gfs2":
                return True
        return False
    
    def create(self, path):
        if not self.creatable:
            raise "not creatable"
        
        try:
            valid = False
            while not valid:
                rc = self.dlg.run()
                if rc == Gtk.ResponseType.OK:
                    valid = True
                    msg = ''
                    illegal_chars = ';:\'"/?.>,<]}[{ =+)(*&^%$#@!`~'
                    c_name = self.clustername_entry.get_text().strip()
                    g_name = self.gfsname_entry.get_text().strip()
                    for c in illegal_chars:
                        if c in c_name:
                            msg = _("Cluster name contains illegal character " + c)
                            valid = False
                        if c in g_name:
                            msg = _("GFS name contains illegal character " + c)
                            valid = False
                    if len(c_name) == 0:
                        msg = _("Missing Cluster Name")
                        valid = False
                    elif len(g_name) == 0:
                        msg = _("Missing GFS Name")
                        valid = False
                    if not valid:
                        self.__errorMessage(msg)
                    else:
                        j_num = self.journals_spin.get_value_as_int()
                        table = c_name + ':' + g_name
                        locking_type = 'lock_'
                        if self.lock_dlm_butt.get_active():
                            locking_type += 'dlm'
                        elif self.lock_gulm_butt.get_active():
                            locking_type += 'gulm'
        except:
            self.dlg.hide()
            raise
        self.dlg.hide()
        
        MKFS_GFS_BIN='/sbin/gfs2_mkfs'
        args = [MKFS_GFS_BIN]
        args.append('-j')
        args.append(str(j_num))
        args.append('-p')
        args.append(locking_type)
        args.append('-t')
        args.append(table)
        args.append('-O')
        args.append(path)
        cmdstr = ' '.join(args)
        msg = CREATING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress(MKFS_GFS_BIN, args, msg)
        if r != 0:
            raise CommandError('FATAL', FSCREATE_FAILURE % (cmdstr,e))
    
    def extend_online(self, dev_path):
        args = ['/sbin/gfs2_grow']
        args.append(dev_path)
        cmdstr = ' '.join(args)
        msg = RESIZING_FS % (self.name)
        o,e,r = execWithCaptureErrorStatusProgress('/sbin/gfs2_grow', args, msg)
        if r != 0:
            raise CommandError('FATAL', FSRESIZE_FAILURE % (cmdstr,e))
    
    def set_clustered(self, clustered, path=None):
        pass
    
    
    def __get_gfs_lock_type(self, path):
        if self.check_path('/sbin/gfs2_tool'):
            args = ['/sbin/gfs2_tool']
            args.append('sb')
            args.append(path)
            args.append('proto')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs2_tool', args)
            if r == 0:
                if 'lock_dlm' in o:
                    return 'dlm'
                elif 'lock_gulm' in o:
                    return 'gulm'
                elif 'nolock' in o:
                    return 'nolock'
        return None
    def __get_gfs_table_name(self, path):
        if self.check_path('/sbin/gfs2_tool'):
            args = ['/sbin/gfs2_tool']
            args.append('sb')
            args.append(path)
            args.append('table')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs2_tool', args)
            if r == 0:
                words = o.strip().split()
                if len(words) == 6:
                    return words[5].strip('\"').split(':')
        return (None, None)
    
    def __get_cluster_name(self):
        return Cluster().get_name()
    def __get_cluster_lock_type(self):
        return Cluster().get_lock_type()
    def __get_cluster_nodes_num(self):
        return Cluster().get_nodes_num()
    def __is_cluster_running(self, clustername):
        if clustername == None:
            return False
        return Cluster().running()
    
    def __errorMessage(self, message):
        dlg = Gtk.MessageDialog(None, 0,
                                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                message)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()
        return rc

    def __get_gfs_fstype(self, path):
        if self.check_path('/sbin/gfs_tool'):
            args = ['/sbin/gfs_tool']
            args.append('sb')
            args.append(path)
            args.append('ondisk')
            cmdstr = ' '.join(args)
            o,e,r = execWithCaptureErrorStatus('/sbin/gfs_tool', args)
            if r == 0:
                for k,v in gfs_types.items():
                    if k in o:
                        return v
        return None

