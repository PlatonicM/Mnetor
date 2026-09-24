import os
import sys

# Suppress GLib / GIO C-level warning messages on Windows
if os.name == 'nt':
    os.environ["GIO_USE_VFS"] = "local"
    os.environ["G_MESSAGES_DEBUG"] = "none"
    try:
        _devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(_devnull, 2)
        os.close(_devnull)
    except Exception:
        pass
