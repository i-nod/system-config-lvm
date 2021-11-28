import locale
import time

import gi
gi.require_version("Gtk","3.0")
from gi.repository import Gtk, GObject, Gdk
import os, sys
import select


BASH_PATH='/bin/bash'

def execWithCapture(bin, args):
    return execWithCaptureErrorStatus(bin, args)[0]

def execWithCaptureStatus(bin, args):
    res = execWithCaptureErrorStatus(bin, args)
    return res[0], res[2]

def execWithCaptureErrorStatus(bin, args):
    command = 'LANG=C ' + bin
    if len(args) > 0:
        for arg in args[1:]:
            command = command + ' ' + arg
    return _execWithCaptureErrorStatus(BASH_PATH, [BASH_PATH, '-c', command])


def execWithCaptureProgress(bin, args, message):
    res = execWithCaptureErrorStatusProgress(bin, args, message)
    return res[0]

def execWithCaptureStatusProgress(bin, args, message):
    res = execWithCaptureErrorStatusProgress(bin, args, message)
    return res[0], res[2]

def execWithCaptureErrorStatusProgress(bin, args, message):
    progress = ProgressPopup(message)
    progress.start()
    res = execWithCaptureErrorStatus(bin, args)
    progress.stop()
    return res


class ProgressPopup:
    def __init__(self, message):
        self.message = message
        
        self.pbar_timer = 0
        self.be_patient_dialog = None
    
    def start(self):
        self.be_patient_dialog = Gtk.Dialog()
        self.be_patient_dialog.set_modal(True)
        
        self.be_patient_dialog.connect("response", self.__on_delete_event)
        self.be_patient_dialog.connect("close", self.__on_delete_event)
        self.be_patient_dialog.connect("delete_event", self.__on_delete_event)
        
        
        label = Gtk.Label(self.message)
        self.be_patient_dialog.vbox.pack_start(label, True, True, 0)
        self.be_patient_dialog.set_modal(True)
        
        #Create an alignment object that will center the pbar
        #fix, deprecated so use halign/valign
        #        align = Gtk.Alignment(0.5, 0.5, 0, 0)
        #        self.be_patient_dialog.vbox.pack_start(align, False, False, 5)
        #        align.show()
        
        self.pbar = Gtk.ProgressBar()
        #        align.add(self.pbar)
        self.be_patient_dialog.vbox.pack_start(self.pbar, False, False, 5)
        self.pbar.show()
        
        # change cursor
        cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.be_patient_dialog.get_root_window().set_cursor(cursor)
        
        # display dialog
        self.be_patient_dialog.show_all()
        
        #Start bouncing progress bar
        self.pbar_timer = GObject.timeout_add(100, self.__progress_bar_timeout)
        
        
    def stop(self):
        # remove timer
        GObject.source_remove(self.pbar_timer)
        self.pbar_timer = 0
        
        # revert cursor
        cursor = Gdk.Cursor(Gdk.CursorType.LEFT_PTR)
        self.be_patient_dialog.get_root_window().set_cursor(cursor)
        
        # destroy dialog
        self.be_patient_dialog.destroy()
        self.be_patient_dialog = None
    
    def __progress_bar_timeout(self):
        self.pbar.pulse()
        return True
    
    def __on_delete_event(self, *args):
        return True



class ForkedCommand:
    def __init__(self, bin, args):
        self.child_pid = None
        
        self.bin = bin
        self.args = args
        
        # This pipe is for the parent process to receive
        # the result of the system call in the child process.
        self.fd_read_out, self.fd_write_out = os.pipe()
        self.fd_read_err, self.fd_write_err = os.pipe()
        
    def fork(self):
        try:
            self.child_pid = os.fork()
        except OSError:
            sys.exit("Unable to fork!!!")
        
        if (self.child_pid != 0):
            # parent process
            os.close(self.fd_write_out)
            os.close(self.fd_write_err)
        else:
            # child process
            os.close(self.fd_read_out)
            os.close(self.fd_read_err)
            
            out, err, res = _execWithCaptureErrorStatus(self.bin, self.args, 0, '/', 0, 1, 2, -1, False)
            # let parent process know result of system call through IPC
#            print("out is ", out)
            os.write(self.fd_write_out, out.encode('utf-8'))
            os.write(self.fd_write_err, err.encode('utf-8'))
            os.close(self.fd_write_out)
            os.close(self.fd_write_err)
            
            os._exit(res)
            
    def get_stdout_stderr_status(self):
        (reaped, status) = os.waitpid(self.child_pid, os.WNOHANG)
        
        if reaped != self.child_pid:
            # child still alive
            return None, None, None
        
        # child exited
        if os.WIFEXITED(status):
            ret_status = os.WEXITSTATUS(status)
            retval = ret_status
        else:
            retval = 255
        # collect data
        in_list = [self.fd_read_out, self.fd_read_err]
        out = ''
        err = ''
        while len(in_list) != 0:
            i,o,e = select.select(in_list, [], [])
            for fd in i:
                if fd == self.fd_read_out:
                    s = os.read(self.fd_read_out, 1000)
                    if len(s) == 0:
                        in_list.remove(self.fd_read_out)
                    out = out + s.decode('utf-8', 'ignore')
                if fd == self.fd_read_err:
                    s = os.read(self.fd_read_err, 1000)
                    if len(s) == 0:
                        in_list.remove(self.fd_read_err)
                    err = err + s.decode('utf-8', 'ignore')
        os.close(self.fd_read_out)
        os.close(self.fd_read_err)
        
        return out, err, retval
    



def _execWithCaptureErrorStatus(command, argv, searchPath = 0, root = '/', stdin = 0, catchfd = 1, catcherrfd = 2, closefd = -1, update_gtk=True):
    if not os.access (root + command, os.X_OK):
        raise RuntimeError(command + " can not be run")
    
    (read, write) = os.pipe()
    (read_err,write_err) = os.pipe()
    
    childpid = os.fork()
    if (not childpid):
        # child
        if (root and root != '/'): os.chroot (root)
        if isinstance(catchfd, tuple):
            for fd in catchfd:
                os.dup2(write, fd)
        else:
            os.dup2(write, catchfd)
        os.close(write)
        os.close(read)
        
        if isinstance(catcherrfd, tuple):
            for fd in catcherrfd:
                os.dup2(write_err, fd)
        else:
            os.dup2(write_err, catcherrfd)
        os.close(write_err)
        os.close(read_err)
        
        if closefd != -1:
            os.close(closefd)
        
        if stdin:
            os.dup2(stdin, 0)
            os.close(stdin)
        
        if (searchPath):
            os.execvp(command, argv)
        else:
            os.execv(command, argv)
        # will never come here
    
    os.close(write)
    os.close(write_err)
    
    rc = ""
    rc_err = ""
    in_list = [read, read_err]
    while len(in_list) != 0:
        i,o,e = select.select(in_list, [], [], 0.1)
        for fd in i:
            if fd == read:
                s = os.read(read, 1000)
                if len(s) == 0:
                    in_list.remove(read)
                else:
                    rc = rc + s.decode('utf-8','ignore')
            if fd == read_err:
                s = os.read(read_err, 1000)
                if len(s) == 0:
                    in_list.remove(read_err)
                rc_err = rc_err + s.decode('utf-8','ignore')
    
    # let GUI update
    if update_gtk:
         while Gtk.events_pending():
             Gtk.main_iteration()

    os.close(read)
    os.close(read_err)
    
    status = -1
    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError as xxx_todo_changeme:
        (errno, msg) = xxx_todo_changeme.args
        print(__name__, "waitpid:", msg)
    
    if os.WIFEXITED(status):
        status = os.WEXITSTATUS(status)
    else:
        status = -1
    return (rc, rc_err, status)
