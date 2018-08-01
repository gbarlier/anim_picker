# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

from maya import OpenMayaUI

# Main Qt support
try:
    from anim_picker.Qt import QtCore, QtGui, QtOpenGL, QtWidgets
except:
    raise Exception, 'Failed to import Qt.py'

try:
    import sip
except:
    try:
        import shiboken
    except:
        try:
            from PySide import shiboken
        except:
            try:
                import shiboken2 as shiboken
            except:
                raise Exception, 'Failed to import sip or shiboken'


# Instance handling
def wrap_instance(ptr, base):
    '''Return QtGui object instance based on pointer address
    '''
    if globals().has_key('sip'):
        return sip.wrapinstance(long(ptr), QtCore.QObject)
    elif globals().has_key('shiboken'):
        return shiboken.wrapInstance(long(ptr), base)

def unwrap_instance(qt_object):
    '''Return pointer address for qt class instance
    '''
    if globals().has_key('sip'):
        return long(sip.unwrapinstance(qt_object))
    elif globals().has_key('shiboken'):
        return long(shiboken.getCppPointer(qt_object)[0])


def get_maya_window():
    '''Get the maya main window as a QMainWindow instance
    '''
    try:
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        return wrap_instance(long(ptr), QtWidgets.QMainWindow)
    except:
        #    fails at import on maya launch since ui isn't up yet
        return None