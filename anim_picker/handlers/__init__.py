# Copyright (c) 2012-2013 Guillaume Barlier
# This file is part of "anim_picker" and covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.

import mode_handlers
import maya_handlers

# INIT HANDLERS INSTANCES
__EDIT_MODE__ = mode_handlers.EditMode()
__SELECTION__ = maya_handlers.SelectionCheck()