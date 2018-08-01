# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

__version__ = '1.0.3'

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
