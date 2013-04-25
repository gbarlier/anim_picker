# Copyright (c) 2012-2013 Guillaume Barlier
# This file is part of "anim_picker" and covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.

import sys

def safe_code_exec(cmd, env=dict()):
    '''Safely execute code in new namespace with specified dictionary
    '''
    try:
        exec cmd in env
    except:
        raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]