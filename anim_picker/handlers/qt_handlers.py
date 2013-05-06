# Copyright (c) 2012-2013 Guillaume Barlier
# This file is part of "anim_picker" and covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.


# Main Qt support
try:
    from PyQt4 import QtCore, QtGui, QtOpenGL
except:
    try:
        from PySide import QtCore, QtGui, QtOpenGL
    except:
        raise Exception, 'Failed to import PyQt4 or Pyside'
    
try:
    import sip
except:
    try:
        import shiboken
    except:
        raise Exception, 'Failed to import sip or shiboken'
    
    
# Instance handling
def wrap_instance(ptr, base):
    '''Return QtGui object instance based on pointer address
    '''
    if globals().has_key('sip'):
        return sip.wrapinstance(long(ptr), QtCore.QObject)
    elif globals().as_key('shiboken'):
        return shiboken.wrapInstance(long(ptr), base)
    
def unwrap_instance(qt_object):
    '''Return pointer address for qt class instance
    '''
    if globals().has_key('sip'):
        return long(sip.unwrapinstance(qt_object))
    elif globals().as_key('shiboken'):
        return long(shiboken.getCppPointer(qt_object)[0])