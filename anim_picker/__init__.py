# Copyright (c) 2012-2013 Guillaume Barlier
# This file is part of "anim_picker" and covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.

import gui
load = gui.load

def use_opengl(state=True):
    '''
    Will set the viewport to openGl or not
    (will need to restart maya to take effect, since the picker will does not "restart")
    '''
    gui.__USE_OPENGL__ = state
