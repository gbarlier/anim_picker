# Copyright (c) 2012-2013 Guillaume Barlier
# This file is part of "anim_picker" and covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.

__version__ = '1.0.1'

def load(edit=False, multi=False):
    '''Fast load method
    '''
    import gui
    return gui.load(edit=edit, multi=multi)

# def use_opengl(state=True):
#     '''Will set the viewport to openGl or not
#     '''
#     import gui
#     gui.__USE_OPENGL__ = state
