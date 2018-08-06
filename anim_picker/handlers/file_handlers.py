# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

import os
import re

from qt_handlers import QtGui, get_maya_window

header_text = '''# Copyright (c) 2018 Guillaume Barlier
# This file is a data file for the anim_picker tool.
# The "anim_picker" tool is covered by the LGPLv3 or later,
# read LICENSE.md and COPYING.md for details.
# The tool can be downloaded from: https://github.com/gbarlier
'''

data_start_tag = "<data_start/>"
data_end_tag = "<data_end/>"


def convert_data_to_text(data):
    '''Convert picker data to text data to make it more readable
    '''
    # To do: export a nice indented data text
    return unicode(data)


def read_data_file(file_path):
    '''Read data from file
    '''
    msg = "file path '{}' not found".format(file_path)
    assert os.path.exists(file_path), msg
    msg = "{} does not seem to be a file".format(file_path)
    assert os.path.isfile(file_path), msg

    # Read file
    try:
        data_file = open(file_path, "r")
        try:
            text_data = data_file.read()
        finally:
            data_file.close()
    except IOError:
        # Show error warning
        msg = "Failed to read from file:\n'{}'".format(file_path)
        QtGui.QMessageBox.warning(get_maya_window(), "Warning", )

    # Get data segment
    regex_res = re.search(r"(?<=%s)(.*?)(?=%s)" % (data_start_tag,
                                                   data_end_tag),
                          text_data,
                          re.DOTALL)
    msg = "file '{}' appear to be invalid and is missing the data delimiters"
    assert regex_res, msg.format(file_path)

    return eval(regex_res.group())


def write_data_file(file_path=None, data={}, f=False):
    '''Write data to file

    # kwargs:
    file_path: the file path to write to
    data: the data to write
    f (bool): force write mode, if false, will ask for confirmation when
    overwriting existing files
    '''
    # Ask for confirmation on existing file
    if not f and os.path.exists(file_path):
        # to do
        pass

    # write file
    status = False
    try:
        # Open file in write mode
        data_file = open(file_path, "w")
        try:
            data_file.write(header_text)
            data_file.write("\n{}\n".format(data_start_tag))
            data_file.write(convert_data_to_text(data))
            data_file.write("\n{}\n".format(data_end_tag))
            status = True
        finally:
            data_file.close()
    except IOError:
        # Show error warning
        msg = "Failed to write to file:\n'{}'".format(file_path)
        QtGui.QMessageBox.warning(get_maya_window(), "Warning", msg)

    return status
