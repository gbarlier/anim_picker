# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

__version__ = "1.0.4"


def load(edit=False, multi=False):
    '''Fast load method
    '''
    import gui
    return gui.load(edit=edit, multi=multi)
