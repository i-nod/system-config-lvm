

from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus, execWithCaptureProgress, execWithCaptureErrorStatusProgress, execWithCaptureStatusProgress
from CommandError import *

import xml
import xml.dom
from xml.dom import minidom

import os


class Cluster:
    cluster_name = None
    cluster_lock = None
    cluster_nodes = None
    cluster_conf_mtime = None
    
    def __init__(self):
        return
    
    def get_name(self):
        return self.__get_info()[0]
    
    def get_lock_type(self):
        return self.__get_info()[1]
    
    def get_nodes_num(self):
        return self.__get_info()[2]
    
    def __get_info(self):
        try:
          mtime = os.stat('/etc/cluster/cluster.conf').st_mtime
        except:
          return (None, None, None)

        if Cluster.cluster_conf_mtime != None and Cluster.cluster_conf_mtime == mtime:
             return (Cluster.cluster_name, Cluster.cluster_lock, Cluster.cluster_nodes)
        else:
             Cluster.cluster_conf_mtime = mtime
        
        try:
            c_conf = minidom.parseString(file('/etc/cluster/cluster.conf').read(10000000)).firstChild
            name = c_conf.getAttribute('name')
            lock = 'dlm'
            nodes_num = 0
            for node in c_conf.childNodes:
                if node.nodeType == xml.dom.Node.ELEMENT_NODE:
                    if node.nodeName == 'cman':
                        lock = 'dlm'
                    elif node.nodeName == 'gulm':
                        lock = 'gulm'
                    elif node.nodeName == 'clusternodes':
                        nodes = node
                        for node in nodes.childNodes:
                            if node.nodeType == xml.dom.Node.ELEMENT_NODE:
                                if node.nodeName == 'clusternode':
                                    nodes_num += 1
            if nodes_num != 0:
                Cluster.cluster_name = name
                Cluster.cluster_lock = lock
                Cluster.cluster_nodes = nodes_num
        except:
            Cluster.cluster_name = None
            Cluster.cluster_lock = None
            Cluster.cluster_nodes = None

        return (Cluster.cluster_name, Cluster.cluster_lock, Cluster.cluster_nodes)
    
    def running(self):
        if self.get_name() == None:
            return False
        try:
            # try magma_tool
            args = ['/sbin/magma_tool', 'quorum']
            o, e, s = execWithCaptureErrorStatus('/sbin/magma_tool', args)
            if s == 0:
                if o.find('Quorate') != -1:
                    return True
        except:
            pass
        
        try:
            # try cman_tool
            cman_tool_path = '/sbin/cman_tool'
            if os.access(cman_tool_path, os.X_OK) == False:
                cman_tool_path = '/usr/sbin/cman_tool'
            args = [cman_tool_path, 'status']
            o, e, s = execWithCaptureErrorStatus(cman_tool_path, args)
            if s != 0:
                return False
            
            quorum = -1
            votes  = -1
            lines  = o.splitlines()
            for line in lines:
                words = line.split()
                if len(words) < 2:
                    continue
                if words[0] == 'Quorum:':
                    quorum = int(words[1])
                elif words[0] == 'Total_votes:':
                    votes = int(words[1])
                if len(words) < 3:
                    continue
                if words[0] == 'Total' and words[1] == 'votes:':
                    votes = int(words[2])
            if quorum <= 0 or votes < 0:
                raise 'Unable to retrieve cluster quorum info'
            return votes >= quorum
        except:
            return False
        
