# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

import sys


def safe_code_exec(cmd, env=dict()):
    '''Safely execute code in new namespace with specified dictionary
    '''
    try:
        exec cmd in env
    except Exception:
        raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
