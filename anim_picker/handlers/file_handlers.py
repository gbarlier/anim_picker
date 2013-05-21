# Copyright (c) 2012-2013 Guillaume Barlier
# This file is part of "anim_picker" and covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.

import os
import re

from qt_handlers import QtGui, get_maya_window

header_text = '''# Copyright (c) 2012-2013 Guillaume Barlier
# This file is a data file for the anim_picker tool.
# The "anim_picker" tool is covered by the LGPLv3 or later,
# read COPYING and COPYING.LESSER for details.
# The tool can be downloaded from: http://guillaume.barlier.com/code
'''

data_start_tag = '<data_start/>'
data_end_tag = '<data_end/>'

#def to_indented_text(data, indent=0):
#    text = ''
#    
#    # Dictionary case
#    if type(data) is dict:
#        text += '{'
#        keys = data.keys()
#        for i in range(len(keys)):
#            if i:
#                text += '\t'*indent
#            text += '%s:%s\n'%(data[keys[i]],
#                             to_indented_text(data[keys[i]], indent=indent+1))
#        text += '},\n'
#    
#    # List case
#    elif type(data) is list:
#        text += '['
#        for i in range(len(data)):
#            if i:
#                text += '\t'*indent
#            text += '%s,\n'%to_indented_text(data[i], indent=indent+1)
#        text += '],\n'
#    else:
#        text += '%s,\n'%unicode(data)
#    return text
        
    
def convert_data_to_text(data):
    '''Convert picker data to text data to make it more readable
    '''
    # To do: export a nice indented data text
    return unicode(data)
    
def read_data_file(file_path):
    '''Read data from file
    '''
    assert os.path.exists(file_path), 'file path "%s" not found'%file_path
    assert os.path.isfile(file_path), '"%s does not seem to be a file"'%file_path
    
    # Read file
    try:
        data_file = open(file_path, "r")
        try:
            text_data = data_file.read()
        finally:
            data_file.close()
    except IOError:
        # Show error warning
        QtGui.QMessageBox.warning(get_maya_window(),
                                  'Warning',
                                  'Failed to read from file:\n"%s"'%file_path)
    
    # Get data segment
    regex_res = re.search( r'(?<=%s)(.*?)(?=%s)'%(data_start_tag, data_end_tag),
                           text_data,
                           re.DOTALL)
    assert regex_res, 'file "%s" appear to be invalid and is missing the data delimiters'%file_path
    
    return eval(regex_res.group())
    
def write_data_file(file_path=None,
                    data=dict(),
                    f=False):
    '''Write data to file
    
    # kwargs:
    file_path: the file path to write to
    data: the data to write
    f (bool): force write mode, if false, will ask for confirmation when overwriting existing files
    '''
    # Ask for confirmation on existing file
    if not f and os.path.exists(file_path):
        pass # to do
    
    # write file
    status = False
    try:
        # Open file in write mode
        data_file = open(file_path, "w")
        try:
            data_file.write(header_text)
            data_file.write('\n%s\n'%data_start_tag)
            data_file.write(convert_data_to_text(data))
            data_file.write('\n%s\n'%data_end_tag)
            status = True
        finally:
            data_file.close()
    except IOError:
        # Show error warning
        QtGui.QMessageBox.warning(get_maya_window(),
                                  'Warning',
                                  'Failed to write to file:\n"%s"'%file_path)

    return status

