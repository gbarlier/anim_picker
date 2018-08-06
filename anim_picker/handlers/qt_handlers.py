# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

from maya import OpenMayaUI

# Main Qt support
try:
    from anim_picker.Qt import QtCore, QtGui, QtOpenGL, QtWidgets
except Exception:
    raise Exception("Failed to import Qt.py")

try:
    import sip
except Exception:
    try:
        import shiboken
    except Exception:
        try:
            from PySide import shiboken
        except Exception:
            try:
                import shiboken2 as shiboken
            except Exception:
                raise Exception("Failed to import sip or shiboken")


# Instance handling
def wrap_instance(ptr, base):
    '''Return QtGui object instance based on pointer address
    '''
    if "sip" in globals():
        return sip.wrapinstance(long(ptr), QtCore.QObject)
    elif "shiboken" in globals():
        return shiboken.wrapInstance(long(ptr), base)


def unwrap_instance(qt_object):
    '''Return pointer address for qt class instance
    '''
    if "sip" in globals():
        return long(sip.unwrapinstance(qt_object))
    elif "shiboken" in globals():
        return long(shiboken.getCppPointer(qt_object)[0])


def get_maya_window():
    '''Get the maya main window as a QMainWindow instance
    '''
    try:
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        return wrap_instance(long(ptr), QtWidgets.QMainWindow)
    except Exception:
        #    fails at import on maya launch since ui isn't up yet
        return None
