# Animation Control Picker
# Author: Guillaume Barlier
# 10/2012

import gui
load = gui.load

def use_opengl(state=True):
    '''
    Will set the viewport to openGl or not
    (will need to restart maya to take effect, since the picker will does not "restart")
    '''
    gui.__USE_OPENGL__ = state

'''
To do list:

- display/edit poly vtx coordinates
- anim mirror options
- copy/past points
- (poly alignment)
- do something about gui.MouseEventCatcherWidget callbacks inputs
'''