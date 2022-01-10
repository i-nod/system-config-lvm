import os
from execute import execWithCapture, execWithCaptureErrorStatus, execWithCaptureStatus

cache_readlink_o = {}
cache_readlink_s = {}

def follow_links_to_target(path, paths=[]):
    global cache_readlink_o
    global cache_readlink_s
    
    if path.startswith("/") == False:
        return None

    #ubuntu puts readlink in /bin so need to see if it exists in /usr/bin or /bin
    if os.path.isfile("/usr/bin/readlink"):
        if path not in cache_readlink_s:
            o, s = execWithCaptureStatus('/usr/bin/readlink', ['/usr/bin/readlink', '-e', path])
            cache_readlink_o[path] = o
            cache_readlink_s[path] = s
        else:
            s = cache_readlink_s[path]
            o = cache_readlink_o[path]
    elif os.path.isfile("/bin/readlink"):
        if path not in cache_readlink_s:
            o, s = execWithCaptureStatus('/bin/readlink', ['/bin/readlink', '-e', path])
            cache_readlink_o[path] = o
            cache_readlink_s[path] = s
        else:
            s = cache_readlink_s[path]
            o = cache_readlink_o[path]
    else: #can't find readlink
        return None
    
    if s == 0:
        word = o.strip()
        
        if word != path:
            paths.append(word)
            return follow_links_to_target(word, paths)
        else:
            return path
    else:
        return None
