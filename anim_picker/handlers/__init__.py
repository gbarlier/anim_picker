# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

import mode_handlers
import maya_handlers

# INIT HANDLERS INSTANCES
__EDIT_MODE__ = mode_handlers.EditMode()
__SELECTION__ = maya_handlers.SelectionCheck()
