# Copyright (c) 2018 Guillaume Barlier
# This file is part of "anim_picker" and covered by MIT,
# read LICENSE.md and COPYING.md for details.

# PyQt4 user interface for anim_picker

import os

import re
from math import sin, cos, pi

from maya import cmds
from maya import OpenMayaUI

import anim_picker
import picker_node
from handlers import maya_handlers
from handlers import python_handlers

from handlers import qt_handlers
from handlers.qt_handlers import QtCore, QtWidgets, QtOpenGL, QtGui
# from Qt import QtCore, QtWidgets, QtOpenGL, QtGui

from handlers import __EDIT_MODE__
from handlers import __SELECTION__

# seems to conflicts with maya viewports...
__USE_OPENGL__ = False


# =============================================================================
# Dependencies ---
# =============================================================================
def get_module_path():
    '''Return the folder path for this module
    '''
    return os.path.dirname(os.path.abspath(__file__))


def get_images_folder_path():
    '''Return path for package images folder
    '''
    # Get the path to this file
    return os.path.join(get_module_path(), "images")


# =============================================================================
# Custom Widgets ---
# =============================================================================
class CallbackButton(QtWidgets.QPushButton):
    '''Dynamic callback button
    '''

    def __init__(self, callback=None, *args, **kwargs):
        QtWidgets.QPushButton.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Connect event
        self.clicked.connect(self.click_event)

        # Set tooltip
        if hasattr(self.callback, "__doc__") and self.callback.__doc__:
            self.setToolTip(self.callback.__doc__)

    def click_event(self):
        if not self.callback:
            return
        self.callback(*self.args, **self.kwargs)


class CallbackComboBox(QtWidgets.QComboBox):
    '''Dynamic combo box object
    '''

    def __init__(self, callback=None, status_tip=None, *args, **kwargs):
        QtWidgets.QComboBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        if status_tip:
            self.setStatusTip(status_tip)

        self.currentIndexChanged.connect(self.index_change_event)

    def index_change_event(self, index):
        if not self.callback:
            return
        self.callback(index=index, *self.args, **self.kwargs)


class CallBackSpinBox(QtWidgets.QSpinBox):
    def __init__(self, callback, value=0, min=0, max=9999, *args, **kwargs):
        QtWidgets.QSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set properties
        self.setRange(min, max)
        self.setValue(value)

        # Signals
        self.valueChanged.connect(self.valueChangedEvent)

    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)


class CallBackDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, callback, value=0, min=0, max=9999, *args, **kwargs):
        QtWidgets.QDoubleSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set properties
        self.setRange(min, max)
        self.setValue(value)

        # Signals
        self.valueChanged.connect(self.valueChangedEvent)

    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)


class CallbackLineEdit(QtWidgets.QLineEdit):
    def __init__(self, callback, text=None, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set properties
        if text:
            self.setText(text)

        # Signals
        self.returnPressed.connect(self.return_pressed_event)

    def return_pressed_event(self):
        '''Will return text on return press
        '''
        self.callback(text=self.text(), *self.args, **self.kwargs)


class CallbackListWidget(QtWidgets.QListWidget):
    '''Dynamic List Widget object
    '''

    def __init__(self, callback=None, *args, **kwargs):
        QtWidgets.QListWidget.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        self.itemDoubleClicked.connect(self.double_click_event)

        # Set selection mode to multi
        self.setSelectionMode(self.ExtendedSelection)

    def double_click_event(self, item):
        if not self.callback:
            return
        self.callback(item=item, *self.args, **self.kwargs)


class CallbackCheckBoxWidget(QtWidgets.QCheckBox):
    '''Dynamic CheckBox Widget object
    '''

    def __init__(self,
                 callback=None,
                 value=False,
                 label=None,
                 *args,
                 **kwargs):
        QtWidgets.QCheckBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

        # Set init state
        if value:
            self.setCheckState(QtCore.Qt.Checked)
        self.setText(label or "")

        self.toggled.connect(self.toggled_event)

    def toggled_event(self, value):
        if not self.callback:
            return
        self.kwargs["value"] = value
        self.callback(*self.args, **self.kwargs)


class CallbackRadioButtonWidget(QtWidgets.QRadioButton):
    '''Dynamic callback radioButton
    '''

    def __init__(self, name_value, callback, checked=False):
        QtWidgets.QRadioButton.__init__(self)
        self.name_value = name_value
        self.callback = callback

        self.setChecked(checked)

        self.clicked.connect(self.click_event)

    def click_event(self):
        self.callback(self.name_value)


class CtrlListWidgetItem(QtWidgets.QListWidgetItem):
    '''
    List widget item for influence list
    will handle checks, color feedbacks and edits
    '''

    def __init__(self, index=0, text=None):
        QtWidgets.QListWidgetItem.__init__(self)

        self.index = index
        if text:
            self.setText(text)

    def setText(self, text):
        '''Overwrite default setText with auto color status check
        '''
        # Skip if name hasn't changed
        if text == self.text():
            return None

        # Run default setText action
        QtWidgets.QListWidgetItem.setText(self, text)

        # Set color status
        self.set_color_status()

        return text

    def node(self):
        '''Return a usable string for maya instead of a QString
        '''
        return unicode(self.text())

    def node_exists(self):
        '''Will check that the node from "text" exists
        '''
        return cmds.objExists(self.node())

    def set_color_status(self):
        '''Set the color to red/green based on node existence status
        '''
        color = QtGui.QColor()

        # Exists case
        if self.node_exists():
            # pale green
            color.setRgb(152, 251, 152)

        # Does not exists case
        else:
            # orange
            color.setRgb(255, 165, 0)

        brush = self.foreground()
        brush.setColor(color)
        self.setForeground(brush)


class ContextMenuTabWidget(QtWidgets.QTabWidget):
    '''Custom tab widget with specific context menu support
    '''

    def __init__(self,
                 parent,
                 main_window=None,
                 *args, **kwargs):
        QtWidgets.QTabWidget.__init__(self, parent, *args, **kwargs)
        self.main_window = main_window

    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        # Abort out of edit mode
        if not __EDIT_MODE__.get():
            return

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Build context menu
        rename_action = QtWidgets.QAction("Rename", None)
        rename_action.triggered.connect(self.rename_event)
        menu.addAction(rename_action)

        add_action = QtWidgets.QAction("Add Tab", None)
        add_action.triggered.connect(self.add_tab_event)
        menu.addAction(add_action)

        remove_action = QtWidgets.QAction("Remove Tab", None)
        remove_action.triggered.connect(self.remove_tab_event)
        menu.addAction(remove_action)

        # Open context menu under mouse
        menu.exec_(self.mapToGlobal(event.pos()))

    def fit_contents(self):
        '''Will resize views content to match views size
        '''
        for i in range(self.count()):
            widget = self.widget(i)
            if not isinstance(widget, GraphicViewWidget):
                continue
            widget.fit_scene_content()

    def rename_event(self, event):
        '''Will open dialog to rename tab
        '''
        # Get current tab index
        index = self.currentIndex()

        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr("Tab name"),
                                                  self.tr('New name'),
                                                  QtWidgets.QLineEdit.Normal,
                                                  self.tr(self.tabText(index)))
        if not (ok and name):
            return

        # Update influence name
        self.setTabText(index, name)

    def add_tab_event(self):
        '''Will open dialog to get tab name and create a new tab
        '''
        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr("Create new tab"),
                                                  self.tr("Tab name"),
                                                  QtWidgets.QLineEdit.Normal,
                                                  self.tr(""))
        if not (ok and name):
            return

        # Add tab
        self.addTab(GraphicViewWidget(main_window=self.main_window), name)

        # Set new tab active
        self.setCurrentIndex(self.count() - 1)

    def remove_tab_event(self):
        '''Will remove tab from widget
        '''
        # Get current tab index
        index = self.currentIndex()

        # Open confirmation
        reply = QtWidgets.QMessageBox.question(self,
                                               "Delete",
                                               "Delete tab '{}'?".format(
                                                   self.tabText(index)),
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return

        # Remove tab
        self.removeTab(index)

    def get_namespace(self):
        '''Return data_node namespace
        '''
        # Proper parent
        if self.main_window and isinstance(self.main_window, MainDockWindow):
            return self.main_window.get_current_namespace()

        return None

    def get_current_picker_items(self):
        '''Return all picker items for current active tab
        '''
        return self.currentWidget().get_picker_items()

    def get_all_picker_items(self):
        '''Returns all picker items for all tabs
        '''
        items = []
        for i in range(self.count()):
            items.extend(self.widget(i).get_picker_items())
        return items

    def get_data(self):
        '''Will return all tabs data
        '''
        data = []
        for i in range(self.count()):
            name = unicode(self.tabText(i))
            tab_data = self.widget(i).get_data()
            data.append({"name": name, "data": tab_data})
        return data

    def set_data(self, data):
        '''Will, set/load tabs data
        '''
        self.clear()
        for tab in data:
            view = GraphicViewWidget(namespace=self.get_namespace(),
                                     main_window=self.main_window)
            self.addTab(view, tab.get('name', 'default'))

            tab_content = tab.get('data', None)
            if tab_content:
                view.set_data(tab_content)


class BackgroundWidget(QtWidgets.QLabel):
    '''QLabel widget to support background options for tabs.
    '''

    def __init__(self,
                 parent=None):
        QtWidgets.QLabel.__init__(self, parent)

        self.setBackgroundRole(QtGui.QPalette.Base)
        self.background = None

    def _assert_path(self, path):
        assert os.path.exists(path), "Could not find file {}".format(path)

    def resizeEvent(self, event):
        QtWidgets.QLabel.resizeEvent(self, event)
        self._set_stylesheet_background()

    def _set_stylesheet_background(self):
        '''
        Will set proper sylesheet based on edit status to have
        fixed size background in edit mode and stretchable in anim mode
        '''
        if not self.background:
            self.setStyleSheet("")
            return

        bg = self.background
        if __EDIT_MODE__.get():
            edit_css = "QLabel {background-image: url('{}'); background-repeat: no repeat;}".format(bg)
            self.setStyleSheet(edit_css)
        else:
            self.setStyleSheet("QLabel {border-image: url('{}');}".format(bg))

    def set_background(self, path=None):
        '''Set character snapshot picture
        '''
        if not (path and os.path.exists(path)):
            path = None
            self.background = None
        else:
            self.background = unicode(path)

        # Use stylesheet rather than pixmap for proper resizing support
        self._set_stylesheet_background()

    def file_dialog(self):
        '''Get file dialog window starting in default folder
        '''
        imgs_dir = get_images_folder_path()
        file_path = QtWidgets.QFileDialog.getOpenFileName(self,
                                                          'Choose picture',
                                                          imgs_dir)
        # Filter return result (based on qt version)
        if isinstance(file_path, tuple):
            file_path = file_path[0]

        if not file_path:
            return

        return file_path


class SnapshotWidget(BackgroundWidget):
    '''Top right character "snapshot" widget, to display character picture
    '''

    def __init__(self,
                 parent=None):
        BackgroundWidget.__init__(self, parent)

        self.setFixedWidth(80)
        self.setFixedHeight(80)

        self.set_background()

        self.setToolTip("Click here to Open About/Help window")

    def _get_default_snapshot(self, name='undefined'):
        '''Return default snapshot
        '''
        # Define image path
        folder_path = get_images_folder_path()
        image_path = os.path.join(folder_path, "{}.png".format(name))

        # Assert path
        self._assert_path(image_path)

        return image_path

    def set_background(self, path=None):
        '''Set character snapshot picture
        '''
        if not (path and os.path.exists(unicode(path))):
            path = self._get_default_snapshot()
            self.background = None
        else:
            self.background = unicode(path)

        # Load image
        image = QtGui.QImage(path)
        self.setPixmap(QtGui.QPixmap.fromImage(image))

    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        # Abort in non edit mode
        if not __EDIT_MODE__.get():
            return

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Add choose action
        choose_action = QtWidgets.QAction("Select Picture", None)
        choose_action.triggered.connect(self.select_image)
        menu.addAction(choose_action)

        # Add reset action
        reset_action = QtWidgets.QAction("Reset", None)
        reset_action.triggered.connect(self.reset_image)
        menu.addAction(reset_action)

        # Open context menu under mouse
        if not menu.isEmpty():
            menu.exec_(self.mapToGlobal(event.pos()))

    def select_image(self):
        '''Pick/set snapshot image
        '''
        # Open file dialog
        file_name = self.file_dialog()

        # Abort on cancel
        if not file_name:
            return

        # Set picture
        self.set_background(file_name)

    def reset_image(self):
        '''Reset snapshot image to default
        '''
        # Reset background
        self.set_background()

    def get_data(self):
        '''Return snapshot picture path
        '''
        return self.background


class OverlayWidget(QtWidgets.QWidget):
    '''
    Transparent overlay type widget

    add resize to parent resetEvent to resize this event window as:
    #def resizeEvent(self, event):
    #    self.overlay.resize(self.widget().size())
    #    self.overlay.move(self.widget().pos())
    #    event.accept()

    '''

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.set_default_background_color()
        self.setup()

    def set_default_background_color(self):
        palette = self.parent().palette()
        color = palette.color(palette.Background)
        self.set_overlay_background(color)

    def set_overlay_background(self, color=QtGui.QColor(20, 20, 20, 90)):
        palette = QtGui.QPalette(self.parent().palette())
        palette.setColor(palette.Background, color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def setup(self):
        # Add default layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Hide by default
        self.hide()


class State():
    '''State object, for easy state handling
    '''

    def __init__(self, state, name=False):
        self.state = state
        self.name = name

    def __lt__(self, other):
        '''Override for "sort" function
        '''
        return self.name < other.name

    def get(self):
        return self.state

    def set(self, state):
        self.state = state


class DataCopyDialog(QtWidgets.QDialog):
    '''PickerItem data copying dialog handler
    '''
    __DATA__ = {}

    __STATES__ = []
    __DO_POS__ = State(False, 'position')
    __STATES__.append(__DO_POS__)
    __DO_COLOR__ = State(True, 'color')
    __STATES__.append(__DO_COLOR__)
    __DO_ACTION_MODE__ = State(True, 'action_mode')
    __STATES__.append(__DO_ACTION_MODE__)
    __DO_ACTION_SCRIPT__ = State(True, 'action_script')
    __STATES__.append(__DO_ACTION_SCRIPT__)
    __DO_HANDLES__ = State(True, 'handles')
    __STATES__.append(__DO_HANDLES__)
    __DO_TEXT__ = State(True, 'text')
    __STATES__.append(__DO_TEXT__)
    __DO_TEXT_SIZE__ = State(True, 'text_size')
    __STATES__.append(__DO_TEXT_SIZE__)
    __DO_TEXT_COLOR__ = State(True, 'text_color')
    __STATES__.append(__DO_TEXT_COLOR__)
    __DO_CTRLS__ = State(True, 'controls')
    __STATES__.append(__DO_CTRLS__)
    __DO_MENUS__ = State(True, 'menus')
    __STATES__.append(__DO_MENUS__)

    def __init__(self,
                 parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.apply = False
        self.setup()

    def setup(self):
        '''Build/Setup the dialog window
        '''
        self.setWindowTitle('Copy/Paste')

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add data field options
        for state in self.__STATES__:
            label_name = state.name.capitalize().replace('_', ' ')
            cb = CallbackCheckBoxWidget(callback=self.check_box_event,
                                        value=state.get(),
                                        label=label_name,
                                        state_obj=state)
            self.main_layout.addWidget(cb)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

    def check_box_event(self, value=False, state_obj=None):
        '''Update state object value on checkbox state change event
        '''
        state_obj.set(value)

    def accept_event(self):
        '''Accept button event
        '''
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        '''Cancel button event
        '''
        self.apply = False
        self.close()

    @classmethod
    def options(cls, item=None):
        '''
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        '''
        win = cls()
        win.exec_()
        win.raise_()

        if not win.apply:
            return
        win.set(item)

    @staticmethod
    def set(item=None):
        # Sanity check
        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg
        assert DataCopyDialog.__DATA__, "No stored data to paste"

        # Filter data keys to copy
        keys = []
        for state in DataCopyDialog.__STATES__:
            if not state.get():
                continue
            keys.append(state.name)

        # Build valid data
        data = {}
        for key in keys:
            if key not in DataCopyDialog.__DATA__:
                continue
            data[key] = DataCopyDialog.__DATA__[key]

        # Get picker item data
        item.set_data(data)

    @staticmethod
    def get(item=None):
        '''Will get and store data for specified item
        '''
        # Sanity check
        msg = "Item is not an PickerItem instance"
        assert isinstance(item, PickerItem), msg

        # Get picker item data
        data = item.get_data()

        # Store data
        DataCopyDialog.__DATA__ = data

        return data


class CustomScriptEditDialog(QtWidgets.QDialog):
    '''Custom python script window (used for custom picker item
    action and context menu)
    '''
    __TITLE__ = "Custom script"

    def __init__(self,
                 parent=None,
                 cmd=None,
                 item=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.cmd = cmd
        self.picker_item = item

        self.apply = False
        self.setup()

    @staticmethod
    def get_default_script():
        '''Custom script default content
        '''
        text = "# Custom anim_picker python script window\n"
        text += "# Use the following variables in your code to access \
        related data:\n"
        text += "# __CONTROLS__ for picker item associated controls \
        (will return sets and not content).\n"
        text += "# __FLATCONTROLS__ for associated controls and control \
        set content.\n"
        text += "# __NAMESPACE__ for current picker namespace\n"
        text += '\n'
        return text

    def setup(self):
        '''Build/Setup the dialog window
        '''
        self.setWindowTitle(self.__TITLE__)

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add cmd txt field
        self.cmd_widget = QtWidgets.QTextEdit()
        if self.cmd:
            self.cmd_widget.setText(self.cmd)
        else:
            default_script = self.get_default_script()
            self.cmd_widget.setText(default_script)
        self.main_layout.addWidget(self.cmd_widget)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

        run_btn = CallbackButton(callback=self.run_event)
        run_btn.setText("Run")
        btn_layout.addWidget(run_btn)

        self.resize(500, 600)

    def accept_event(self):
        '''Accept button event
        '''
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        '''Cancel button event
        '''
        self.apply = False
        self.close()

    def run_event(self):
        '''Run event button
        '''
        cmd_str = unicode(self.cmd_widget.toPlainText())

        if self.picker_item:
            python_handlers.safe_code_exec(cmd_str,
                                           env=self.picker_item.get_exec_env())
        else:
            python_handlers.safe_code_exec(cmd_str)

    def get_values(self):
        '''Return dialog window result values
        '''
        cmd_str = unicode(self.cmd_widget.toPlainText())

        return cmd_str, self.apply

    @classmethod
    def get(cls, cmd=None, item=None):
        '''
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        '''
        win = cls(cmd=cmd, item=item)
        win.exec_()
        win.raise_()
        return win.get_values()


class CustomMenuEditDialog(CustomScriptEditDialog):
    '''Custom python script window for picker item context menu
    '''
    __TITLE__ = "Custom Menu"

    def __init__(self, parent=None, name=None, cmd=None, item=None):

        self.name = name
        CustomScriptEditDialog.__init__(self,
                                        parent=parent,
                                        cmd=cmd,
                                        item=item)

    def setup(self):
        '''Add name field to default window setup
        '''
        # Run default setup
        CustomScriptEditDialog.setup(self)

        # Add name line edit
        name_layout = QtWidgets.QHBoxLayout(self)

        label = QtWidgets.QLabel()
        label.setText("Name")
        name_layout.addWidget(label)

        self.name_widget = QtWidgets.QLineEdit()
        if self.name:
            self.name_widget.setText(self.name)
        name_layout.addWidget(self.name_widget)

        self.main_layout.insertLayout(0, name_layout)

    def accept_event(self):
        '''Accept button event, check for name
        '''
        if not self.name_widget.text():
            QtWidgets.QMessageBox.warning(self,
                                          "Warning",
                                          "You need to specify a menu name")
            return

        self.apply = True

        self.accept()
        self.close()

    def get_values(self):
        '''Return dialog window result values
        '''
        name_str = unicode(self.name_widget.text())
        cmd_str = unicode(self.cmd_widget.toPlainText())

        return name_str, cmd_str, self.apply

    @classmethod
    def get(cls, name=None, cmd=None, item=None):
        '''
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        '''
        win = cls(name=name, cmd=cmd, item=item)
        win.exec_()
        win.raise_()
        return win.get_values()


class SearchAndReplaceDialog(QtWidgets.QDialog):
    '''Search and replace dialog window
    '''
    __SEARCH_STR__ = "^L_"
    __REPLACE_STR__ = "R_"

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.apply = False
        self.setup()

    def setup(self):
        '''Build/Setup the dialog window
        '''
        self.setWindowTitle("Search And Replace")

        # Add layout
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Add line edits
        self.search_widget = QtWidgets.QLineEdit()
        self.search_widget.setText(self.__SEARCH_STR__)
        self.main_layout.addWidget(self.search_widget)

        self.replace_widget = QtWidgets.QLineEdit()
        self.replace_widget.setText(self.__REPLACE_STR__)
        self.main_layout.addWidget(self.replace_widget)

        # Add buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        ok_btn = CallbackButton(callback=self.accept_event)
        ok_btn.setText("Ok")
        btn_layout.addWidget(ok_btn)

        cancel_btn = CallbackButton(callback=self.cancel_event)
        cancel_btn.setText("Cancel")
        btn_layout.addWidget(cancel_btn)

        ok_btn.setFocus()

    def accept_event(self):
        '''Accept button event
        '''
        self.apply = True

        self.accept()
        self.close()

    def cancel_event(self):
        '''Cancel button event
        '''
        self.apply = False
        self.close()

    def get_values(self):
        '''Return field values and button choice
        '''
        search_str = unicode(self.search_widget.text())
        replace_str = unicode(self.replace_widget.text())
        if self.apply:
            SearchAndReplaceDialog.__SEARCH_STR__ = search_str
            SearchAndReplaceDialog.__REPLACE_STR__ = replace_str
        return search_str, replace_str, self.apply

    @classmethod
    def get(cls):
        '''
        Default method used to run the dialog input window
        Will open the dialog window and return input texts.
        '''
        win = cls()
        win.exec_()
        win.raise_()
        return win.get_values()


class OrderedGraphicsScene(QtWidgets.QGraphicsScene):
    '''
    Custom QGraphicsScene with x/y axis line options for origin
    feedback in edition mode
    (provides a center reference to work from, view will fit what ever
    is the content in use mode).

    Had to add z_index support since there was a little z
    conflict when "moving" items to back/front in edit mode
    '''
    __DEFAULT_SCENE_WIDTH__ = 400
    __DEFAULT_SCENE_HEIGHT__ = 600

    def __init__(self, parent=None):
        QtWidgets.QGraphicsScene.__init__(self, parent=parent)

        self.set_default_size()
        self._z_index = 0

    def set_size(self, width, heith):
        '''Will set scene size with proper center position
        '''
        self.setSceneRect(-width / 2, -heith / 2, width, heith)

    def set_default_size(self):
        self.set_size(self.__DEFAULT_SCENE_WIDTH__,
                      self.__DEFAULT_SCENE_HEIGHT__)

    def get_bounding_rect(self, margin=0):
        '''
        Return scene content bounding box with specified margin
        Warning: In edit mode, will return default scene rectangle
        '''
        # Return default size in edit mode
        if __EDIT_MODE__.get():
            return self.sceneRect()

        # Get item boundingBox
        scene_rect = self.itemsBoundingRect()

        # Stop here if no margin
        if not margin:
            return scene_rect

        # Add margin
        scene_rect.setX(scene_rect.x() - margin)
        scene_rect.setY(scene_rect.y() - margin)
        scene_rect.setWidth(scene_rect.width() + margin)
        scene_rect.setHeight(scene_rect.height() + margin)

        return scene_rect

    def clear(self):
        '''Reset default z index on clear
        '''
        QtWidgets.QGraphicsScene.clear(self)
        self._z_index = 0

    def set_picker_items(self, items):
        '''Will set picker items
        '''
        self.clear()
        for item in items:
            QtWidgets.QGraphicsScene.addItem(self, item)
            self.set_z_value(item)
        self.add_axis_lines()

    def get_picker_items(self):
        '''Will return all scenes' picker items
        '''
        picker_items = []
        # Filter picker items (from handles etc)
        for item in self.items():
            if not isinstance(item, PickerItem):
                continue
            picker_items.append(item)
        return picker_items

    def set_z_value(self, item):
        '''set proper z index for item
        '''
        item.setZValue(self._z_index)
        self._z_index += 1

    def addItem(self, item):
        '''Overload to keep axis on top
        '''
        QtWidgets.QGraphicsScene.addItem(self, item)
        self.set_z_value(item)


class GraphicViewWidget(QtWidgets.QGraphicsView):
    '''Graphic view widget that display the "polygons" picker items
    '''
    __DEFAULT_SCENE_WIDTH__ = 400
    __DEFAULT_SCENE_HEIGHT__ = 600

    def __init__(self,
                 namespace=None,
                 main_window=None):
        QtWidgets.QGraphicsView.__init__(self)

        self.setScene(OrderedGraphicsScene())

        self.namespace = namespace
        self.main_window = main_window
        self.setParent(self.main_window)

        # Scale view in Y for positive Y values (maya-like)
        self.scale(1, -1)

        # Open GL render, to check...
        if __USE_OPENGL__:
            # make that view use OpenGL
            gl_format = QtOpenGL.QGLFormat()
            gl_format.setSampleBuffers(True)
            gl_widget = QtOpenGL.QGLWidget(gl_format)

            # use the GL widget for viewing
            self.setViewport(gl_widget)

        self.setResizeAnchor(self.AnchorViewCenter)

        # TODO
#        # Set selection mode
#        self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemBoundingRect)
#        self.setDragMode(self.RubberBandDrag)
        self.scene_mouse_origin = QtCore.QPointF()
        self.drag_active = False
        self.pan_active = False

        # Disable scroll bars
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # Set background color
        brush = QtGui.QBrush(QtGui.QColor(70, 70, 70, 255))
        self.setBackgroundBrush(brush)
        self.background_image = None
        self.background_image_path = None

    def get_center_pos(self):
        return self.mapToScene(QtCore.QPoint(self.width() / 2,
                                             self.height() / 2))

    def mousePressEvent(self, event):
        '''Overload to clear selection on empty area
        '''
        QtWidgets.QGraphicsView.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())

            # Get current viewport transformation
            transform = self.viewportTransform()

            # Clear selection if no picker item below mouse
            if not self.scene().itemAt(scene_pos, transform):
                if not event.modifiers():
                    cmds.select(cl=True)

        elif event.buttons() == QtCore.Qt.MidButton:
            self.pan_active = True
            self.scene_mouse_origin = self.mapToScene(event.pos())

            # Rubber band selection support
            # self.scene_mouse_origin = self.mapToScene(event.pos())
            # self.drag_active = True

    def mouseMoveEvent(self, event):
        result = QtWidgets.QGraphicsView.mouseMoveEvent(self, event)

        if self.pan_active:
            current_center = self.get_center_pos()
            scene_paning = self.mapToScene(event.pos())

            new_center = current_center - (scene_paning -
                                           self.scene_mouse_origin)
            self.centerOn(new_center)

        return result

    def mouseReleaseEvent(self, event):
        result = QtWidgets.QGraphicsView.mouseReleaseEvent(self, event)

        # Area selection
        # if (self.drag_active and event.button() == QtCore.Qt.LeftButton):
        #    scene_drag_end = self.mapToScene(event.pos())

        #    sel_area = QtCore.QRectF(self.scene_mouse_origin, scene_drag_end)

        #    transform = self.viewportTransform()
        #    if not sel_area.size().isNull():
        #        items = self.scene().items(sel_area,
        #                                   QtCore.Qt.IntersectsItemShape,
        #                                   QtCore.Qt.AscendingOrder,
        #                                   deviceTransform=transform)

        #        picker_items = []
        #        for item in items:
        #            if not isinstance(item, PickerItem):
        #                continue
        #            picker_items.append(item)

        #        print picker_items
        # self.drag_active = False

        # Middle mouse view panning
        if (self.pan_active and event.button() == QtCore.Qt.MidButton):
            current_center = self.get_center_pos()
            scene_drag_end = self.mapToScene(event.pos())

            new_center = current_center - (scene_drag_end -
                                           self.scene_mouse_origin)
            self.centerOn(new_center)
            self.pan_active = False

        return result

    def wheelEvent(self, event):
        '''Wheel event overload to add zoom support
        '''
        # Run default event
        QtWidgets.QGraphicsView.wheelEvent(self, event)

        # Define zoom factor
        factor = 1.1
        if event.delta() < 0:
            factor = 0.9

        # Apply zoom
        self.zoom(factor,)
        # self.get_center_pos())
        # self.mapToScene(event.pos()))

    def zoom(self, factor, center=QtCore.QPointF(0, 0)):
        '''Zoom by factor and keep "center" in view
        '''
        self.scale(factor, factor)
        self.centerOn(center)

    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        # Item area
        picker_item = self.itemAt(event.pos())
        if picker_item:
            # Run default method that call on childs
            return QtWidgets.QGraphicsView.contextMenuEvent(self, event)

        # Init context menu
        menu = QtWidgets.QMenu(self)

        # Build Edit move options
        if __EDIT_MODE__.get():
            add_action = QtWidgets.QAction("Add Item", None)
            add_action.triggered.connect(self.add_picker_item)
            menu.addAction(add_action)

            toggle_handles_action = QtWidgets.QAction("Toggle all handles",
                                                      None)
            func = self.toggle_all_handles_event
            toggle_handles_action.triggered.connect(func)
            menu.addAction(toggle_handles_action)

            menu.addSeparator()

            background_action = QtWidgets.QAction("Set background image", None)
            background_action.triggered.connect(self.set_background_event)
            menu.addAction(background_action)

            reset_background_action = QtWidgets.QAction("Reset background",
                                                        None)
            func = self.reset_background_event
            reset_background_action.triggered.connect(func)
            menu.addAction(reset_background_action)

            menu.addSeparator()

        if __EDIT_MODE__.get_main():
            toggle_mode_action = QtWidgets.QAction("Toggle Mode", None)
            toggle_mode_action.triggered.connect(self.toggle_mode_event)
            menu.addAction(toggle_mode_action)

            menu.addSeparator()

        # Common actions
        reset_view_action = QtWidgets.QAction("Reset view", None)
        reset_view_action.triggered.connect(self.fit_scene_content)
        menu.addAction(reset_view_action)

        # Open context menu under mouse
        menu.exec_(self.mapToGlobal(event.pos()))

    def resizeEvent(self, *args, **kwargs):
        '''Overload to force scale scene content to fit view
        '''
        # Fit scene content to view
        self.fit_scene_content()

        # Run default resizeEvent
        return QtWidgets.QGraphicsView.resizeEvent(self, *args, **kwargs)

    def fit_scene_content(self):
        '''Will fit scene content to view, by scaling it
        '''
        scene_rect = self.scene().get_bounding_rect(margin=8)
        self.fitInView(scene_rect, QtCore.Qt.KeepAspectRatio)

    def add_picker_item(self, event=None):
        '''Add new PickerItem to current view
        '''
        ctrl = PickerItem(main_window=self.main_window,
                          namespace=self.namespace)
        ctrl.setParent(self)
        self.scene().addItem(ctrl)

        # Move ctrl
        if event:
            ctrl.setPos(event.pos())
        else:
            ctrl.setPos(0, 0)

        return ctrl

    def toggle_all_handles_event(self, event=None):
        new_status = None
        for item in self.scene().items():
            # Skip non picker items
            if not isinstance(item, PickerItem):
                continue

            # Get first status
            if new_status is None:
                new_status = not item.get_edit_status()

            # Set item status
            item.set_edit_status(new_status)

    def toggle_mode_event(self, event=None):
        '''Will toggle UI edition mode
        '''
        if not self.main_window:
            return

        # Check for possible data change/loss
        if __EDIT_MODE__.get():
            if not self.main_window.check_for_data_change():
                return

        # Toggle mode
        __EDIT_MODE__.toggle()

        # Reset size to default
        self.main_window.reset_default_size()
        self.main_window.refresh()

    def set_background(self, path=None):
        '''Set tab index widget background image
        '''
        if not path:
            return
        path = unicode(path)

        # Check that path exists
        if not (path and os.path.exists(path)):
            print "# background image not found: '{}'".format(path)
            return

        self.background_image_path = path

        # Load image and mirror it vertically
        self.background_image = QtGui.QImage(path).mirrored(False, True)

        # Set scene size to background picture
        width = self.background_image.width()
        height = self.background_image.height()
        self.scene().set_size(width, height)

        # Update display
        self.fit_scene_content()

    def set_background_event(self, event=None):
        '''Set background image pick dialog window
        '''
        # Open file dialog
        img_dir = get_images_folder_path()
        file_path = QtWidgets.QFileDialog.getOpenFileName(self,
                                                          "Pick a background",
                                                          img_dir)

        # Filter return result (based on qt version)
        if isinstance(file_path, tuple):
            file_path = file_path[0]

        # Abort on cancel
        if not file_path:
            return

        # Set background
        self.set_background(file_path)

    def reset_background_event(self, event=None):
        '''Reset background to default
        '''
        self.background_image = None
        self.background_image_path = None
        self.scene().set_default_size()

        # Update display
        self.fit_scene_content()

    def get_background(self, index):
        '''Return background for tab index
        '''
        return self.background_image

    def clear(self):
        '''Clear view, by replacing scene with a new one
        '''
        old_scene = self.scene()
        self.setScene(OrderedGraphicsScene())
        old_scene.deleteLater()

    def get_picker_items(self):
        '''Return scene picker items in proper order (back to front)
        '''
        items = []
        for item in self.scene().items():
            # Skip non picker graphic items
            if not isinstance(item, PickerItem):
                continue

            # Add picker item to filtered list
            items.append(item)

        # Reverse list order (to return back to front)
        items.reverse()

        return items

    def get_data(self):
        '''Return view data
        '''
        data = {}

        # Add background to data
        if self.background_image_path:
            data["background"] = self.background_image_path

        # Add items to data
        items = []
        for item in self.get_picker_items():
            items.append(item.get_data())
        if items:
            data["items"] = items

        return data

    def set_data(self, data):
        '''Set/load view data
        '''
        self.clear()

        # Set backgraound picture
        background = data.get("background", None)
        if background:
            self.set_background(background)

        # Add items to view
        for item_data in data.get("items", []):
            item = self.add_picker_item()
            item.set_data(item_data)

    def drawBackground(self, painter, rect):
        '''Default method override to draw view custom background image
        '''
        # Run default method
        result = QtWidgets.QGraphicsView.drawBackground(self, painter, rect)

        # Stop here if view has no background
        if not self.background_image:
            return result

        # Draw background image
        painter.drawImage(self.sceneRect(),
                          self.background_image,
                          QtCore.QRectF(self.background_image.rect()))

        return result

    def drawForeground(self, painter, rect):
        '''Default method override to draw origin axis in edit mode
        '''
        # Run default method
        result = QtWidgets.QGraphicsView.drawForeground(self, painter, rect)

        # Paint axis in edit mode
        if __EDIT_MODE__.get():
            self.draw_overlay_axis(painter, rect)

        return result

    def draw_overlay_axis(self, painter, rect):
        '''Draw x and y origin axis
        '''
        # Set Pen
        pen = QtGui.QPen(QtGui.QColor(160, 160, 160, 120),
                         1,
                         QtCore.Qt.DashLine)
        painter.setPen(pen)

        # Get event rect in scene coordinates
        # Draw x line
        if rect.y() < 0 and (rect.height() - rect.y()) > 0:
            x_line = QtCore.QLine(rect.x(),
                                  0,
                                  rect.width() + rect.x(),
                                  0)
            painter.drawLine(x_line)

        # Draw y line
        if rect.x() < 0 and (rect.width() - rect.x()) > 0:
            y_line = QtCore.QLineF(0, rect.y(),
                                   0, rect.height() + rect.y())
            painter.drawLine(y_line)


class DefaultPolygon(QtWidgets.QGraphicsObject):
    '''Default polygon class, with move and hover support
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(0, 0, 0, 255)

    def __init__(self, parent=None):
        QtWidgets.QGraphicsObject.__init__(self, parent=parent)

        if parent:
            self.setParent(parent)

        # Hover feedback
        self.setAcceptHoverEvents(True)
        self._hovered = False

        # Init default
        self.color = DefaultPolygon.__DEFAULT_COLOR__

    def hoverEnterEvent(self, event=None):
        '''Lightens background color on mose over
        '''
        QtWidgets.QGraphicsObject.hoverEnterEvent(self, event)
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event=None):
        '''Resets mouse over background color
        '''
        QtWidgets.QGraphicsObject.hoverLeaveEvent(self, event)
        self._hovered = False
        self.update()

    def boundingRect(self):
        '''
        Needed override:
        Returns the bounding rectangle for the graphic item
        '''
        return self.shape().boundingRect()

    def itemChange(self, change, value):
        '''itemChange update behavior
        '''
        # Catch position update
        if change == self.ItemPositionChange:
            # Force scene update to prevent "ghosts"
            # (ghost happen when the previous polygon is out of
            # the new bounding rect when updating)
            if self.scene():
                self.scene().update()

        # Run default action
        return QtWidgets.QGraphicsObject.itemChange(self, change, value)

    def get_color(self):
        '''Get polygon color
        '''
        return self.color

    def set_color(self, color=None):
        '''Set polygon color
        '''
        if not color:
            color = self.__DEFAULT_COLOR__
        elif isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)

        msg = "input color '{}' is invalid".format(color)
        assert isinstance(color, QtGui.QColor), msg

        self.color = color
        self.update()

        return color


class PointHandle(DefaultPolygon):
    '''Handle polygon object to move picker polygon cvs
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 200)

    def __init__(self, x=0, y=0, size=8, color=None, parent=None, index=0):

        DefaultPolygon.__init__(self, parent)

        # Make movable
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemSendsScenePositionChanges)
        self.setFlag(self.ItemIgnoresTransformations)

        # Set values
        self.setPos(x, y)
        self.index = index
        self.size = size
        self.set_color()
        self.draw_index = False

        # Hide by default
        self.setVisible(False)

        # Add index element
        self.index = PointHandleIndex(parent=self, index=index)

    # =========================================================================
    # Default python methods
    # =========================================================================
    def _new_pos_handle_copy(self, pos):
        '''Return a new PointHandle isntance with same attributes
        but different position
        '''
        new_handle = PointHandle(x=pos.x(),
                                 y=pos.y(),
                                 size=self.size,
                                 color=self.color,
                                 parent=self.parentObject())
        return new_handle

    def _get_pos_for_input(self, other):
        if isinstance(other, PointHandle):
            return other.pos()
        return other

    def __add__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() + other
        return self._new_pos_handle_copy(new_pos)

    def __sub__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() - other
        return self._new_pos_handle_copy(new_pos)

    def __div__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() / other
        return self._new_pos_handle_copy(new_pos)

    def __mul__(self, other):
        other = self._get_pos_for_input(other)
        new_pos = self.pos() / other
        return self._new_pos_handle_copy(new_pos)

    # =========================================================================
    # QT OVERRIDES
    # =========================================================================
    def setX(self, value=0):
        '''Override to support keyword argument for spin_box callback
        '''
        DefaultPolygon.setX(self, value)

    def setY(self, value=0):
        '''Override to support keyword argument for spin_box callback
        '''
        DefaultPolygon.setY(self, value)

    # =========================================================================
    # Graphic item methods
    # =========================================================================
    def shape(self):
        '''Return default handle square shape based on specified size
        '''
        path = QtGui.QPainterPath()
        # TODO some ints are being set to negative, make sure it survived the
        # pep8
        rectangle = QtCore.QRectF(QtCore.QPointF(-self.size / 2.0,
                                                 self.size / 2.0),
                                  QtCore.QPointF(self.size / 2.0,
                                                 -self.size / 2.0))
       # path.addRect(rectangle)
        path.addEllipse(rectangle)
        return path

    def paint(self, painter, options, widget=None):
        '''Paint graphic item
        '''
        if __USE_OPENGL__:
            painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        else:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Get polygon path
        path = self.shape()

        # Set node background color
        brush = QtGui.QBrush(self.color)
        if self._hovered:
            brush = QtGui.QBrush(self.color.lighter(500))

        # Paint background
        painter.fillPath(path, brush)

        border_pen = QtGui.QPen(QtGui.QColor(200, 200, 200, 255))
        painter.setPen(border_pen)

        # Paint Borders
        painter.drawPath(path)

        # if not edit_mode: return
        # Paint center cross
        cross_size = self.size / 2 - 2
        painter.setPen(QtGui.QColor(0, 0, 0, 180))
        painter.drawLine(-cross_size, 0, cross_size, 0)
        painter.drawLine(0, cross_size, 0, -cross_size)

    def mirror_x_position(self):
        '''will mirror local x position value
        '''
        self.setX(-1 * self.x())

    def scale_pos(self, x=1.0, y=1.0):
        '''Scale handle local position
        '''
        factor = QtGui.QTransform().scale(x, y)
        self.setPos(self.pos() * factor)
        self.update()

    def enable_index_draw(self, status=False):
        self.index.setVisible(status)

    def set_index(self, index):
        self.index.setText(index)

    def get_index(self):
        return int(self.index.text())


class Polygon(DefaultPolygon):
    '''
    Picker controls visual graphic object
    (inherits from QtWidgets.QGraphicsObject rather
    than QtWidgets.QGraphicsItem for signal support)
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(200, 200, 200, 180)
    __DEFAULT_SELECT_COLOR__ = QtGui.QColor(0, 30, 0, 180)

    def __init__(self, parent=None, points=[], color=None):

        DefaultPolygon.__init__(self, parent=parent)
        self.points = points
        self.set_color(Polygon.__DEFAULT_COLOR__)

        self._edit_status = False
        self.selected = False

    def set_edit_status(self, status=False):
        self._edit_status = status
        self.update()

    def shape(self):
        '''Override function to return proper "hit box",
        and compute shape only once.
        '''
        path = QtGui.QPainterPath()

        # Polygon case
        if len(self.points) > 2:
            # Define polygon points for closed loop
            shp_points = []
            for handle in self.points:
                shp_points.append(handle.pos())
            shp_points.append(self.points[0].pos())

            # Draw polygon
            polygon = QtGui.QPolygonF(shp_points)

            # Update path
            path.addPolygon(polygon)

        # Circle case
        else:
            center = self.points[0].pos()
            radius = QtGui.QVector2D(self.points[0].pos() -
                                     self.points[1].pos()).length()

            # Update path
            path.addEllipse(center.x() - radius,
                            center.y() - radius,
                            radius * 2,
                            radius * 2)

        return path

    def paint(self, painter, options, widget=None):
        '''Paint graphic item
        '''
        # Set render quality
        if __USE_OPENGL__:
            painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        else:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Get polygon path
        path = self.shape()

        # Background color
        color = QtGui.QColor(self.color)
        if self._hovered:
            color = color.lighter(130)
        brush = QtGui.QBrush(color)

        painter.fillPath(path, brush)

        # Add white layer color overlay on selected state
        if self.selected:
            color = QtGui.QColor(255, 255, 255, 50)
            brush = QtGui.QBrush(color)
            painter.fillPath(path, brush)

        # Border status feedback
        border_pen = QtGui.QPen(self.__DEFAULT_SELECT_COLOR__)
        border_pen.setWidthF(1.5)

        if self.selected:
            painter.setPen(border_pen)
            painter.drawPath(path)

        elif self._hovered:
            border_pen.setStyle(QtCore.Qt.DashLine)
            painter.setPen(border_pen)
            painter.drawPath(path)

        # Stop her if not in edit mode
        if not self._edit_status:
            return

        # Paint center cross
        painter.setRenderHints(QtGui.QPainter.HighQualityAntialiasing, False)
        painter.setPen(QtGui.QColor(0, 0, 0, 180))
        painter.drawLine(-5, 0, 5, 0)
        painter.drawLine(0, 5, 0, -5)

    def set_selected_state(self, state):
        '''Will set border color feedback based on selection state
        '''
        # Do nothing on same state
        if state == self.selected:
            return

        # Change state, and update
        self.selected = state
        self.update()

    def set_color(self, color):
        # Run default method
        color = DefaultPolygon.set_color(self, color)

        # Store new color as default
        Polygon.__DEFAULT_COLOR__ = color


class PointHandleIndex(QtWidgets.QGraphicsSimpleTextItem):
    '''Point handle index text element
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(130, 50, 50, 255)

    def __init__(self, parent=None, scene=None, index=0):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Init defaults
        self.set_size()
        self.set_color(PointHandleIndex.__DEFAULT_COLOR__)
        self.setPos(QtCore.QPointF(-9, -14))
        self.setFlag(self.ItemIgnoresTransformations)

        # Hide by default
        self.setVisible(False)

        self.setText(index)

    def set_size(self, value=8.0):
        '''Set pointSizeF for text
        '''
        font = self.font()
        font.setPointSizeF(value)
        self.setFont(font)

    def set_color(self, color=None):
        '''Set text color
        '''
        if not color:
            return
        brush = self.brush()
        brush.setColor(color)
        self.setBrush(brush)

    def setText(self, text):
        '''Override default setText method to force unicode on int index input
        '''
        return QtWidgets.QGraphicsSimpleTextItem.setText(self, unicode(text))


class GraphicText(QtWidgets.QGraphicsSimpleTextItem):
    '''Picker item text element
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(30, 30, 30, 255)

    def __init__(self, parent=None, scene=None):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self, parent, scene)

        # Counter view scale
        self.scale_transform = QtGui.QTransform().scale(1, -1)
        self.setTransform(self.scale_transform)

        # Init default size
        self.set_size()
        self.set_color(GraphicText.__DEFAULT_COLOR__)

    def set_text(self, text):
        '''
        Set current text
        (Will center text on parent too)
        '''
        self.setText(text)
        self.center_on_parent()

    def get_text(self):
        '''Return element text
        '''
        return unicode(self.text())

    def set_size(self, value=10.0):
        '''Set pointSizeF for text
        '''
        font = self.font()
        font.setPointSizeF(value)
        self.setFont(font)
        self.center_on_parent()

    def get_size(self):
        '''Return text pointSizeF
        '''
        return self.font().pointSizeF()

    def get_color(self):
        '''Return text color
        '''
        return self.brush().color()

    def set_color(self, color=None):
        '''Set text color
        '''
        if not color:
            return
        brush = self.brush()
        brush.setColor(color)
        self.setBrush(brush)

        # Store new color as default color
        GraphicText.__DEFAULT_COLOR__ = color

    def center_on_parent(self):
        '''
        Center text on parent item
        (Since by default the text start on the bottom left corner)
        '''
        center_pos = self.boundingRect().center()
        self.setPos(-center_pos * self.scale_transform)


class PickerItem(DefaultPolygon):
    '''Main picker graphic item container
    '''

    def __init__(self,
                 parent=None,
                 point_count=4,
                 namespace=None,
                 main_window=None):
        DefaultPolygon.__init__(self, parent=parent)
        self.point_count = point_count

        self.setPos(25, 30)

        # Make item movable
        if __EDIT_MODE__.get():
            self.setFlag(self.ItemIsMovable)
            self.setFlag(self.ItemSendsScenePositionChanges)

        # Default vars
        self.namespace = namespace
        self.main_window = main_window
        self._edit_status = False
        self.edit_window = None

        # Add polygon
        self.polygon = Polygon(parent=self)

        # Add text
        self.text = GraphicText(parent=self)

        # Add handles
        self.handles = []
        self.set_handles(self.get_default_handles())

        # Controls vars
        self.controls = []
        self.custom_menus = []

        # Custom action
        self.custom_action = False
        self.custom_action_script = None

    def shape(self):
        path = QtGui.QPainterPath()

        if self.polygon:
            path.addPath(self.polygon.shape())

        # Stop here in default mode
        if not self._edit_status:
            return path

        # Add handles to shape
        for handle in self.handles:
            path.addPath(handle.mapToParent(handle.shape()))

        return path

    def paint(self, painter, *args, **kwargs):
        pass
        # for debug only
        # # Set render quality
        # if __USE_OPENGL__:
        #    painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        # else:
        #    painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # # Get polygon path
        # path = self.shape()

        # # Set node background color
        # brush = QtGui.QBrush(QtGui.QColor(0,0,200,255))

        # # Paint background
        # painter.fillPath(path, brush)

        # border_pen = QtGui.QPen(QtGui.QColor(0,200,0,255))
        # painter.setPen(border_pen)

        # # Paint Borders
        # painter.drawPath(path)

    def get_default_handles(self):
        '''
        Generate default point handles coordinate for polygon
        (on circle)
        '''
        unit_scale = 20
        handles = []

        # Define angle step
        angle_step = pi * 2 / self.point_count

        # Generate point coordinates
        for i in range(0, self.point_count):
            x = sin(i * angle_step + pi / self.point_count) * unit_scale
            y = cos(i * angle_step + pi / self.point_count) * unit_scale
            handle = PointHandle(x=x, y=y, parent=self, index=i + 1)
            handles.append(handle)

        # Circle case
        if len(handles) == 2:
            handles.reverse()
            handles[0] = handles[0] + (handles[1] - handles[0]) / 2

        return handles

    def edit_point_count(self, value=4):
        '''
        Change/edit the number of points for the polygon
        (that will reset the shape)
        '''
        # Update point count
        self.point_count = value

        # Reset points
        points = self.get_default_handles()
        self.set_handles(points)

    def get_handles(self):
        '''Return picker item handles
        '''
        return self.handles

    def set_handles(self, handles=list()):
        '''Set polygon handles points
        '''
        # Remove existing handles
        for handle in self.handles:
            handle.setParent(None)
            handle.deleteLater()

        # Parse input type
        new_handles = []
        # start index at 1 since table Widget raw are indexed at 1
        index = 1
        for handle in handles:
            if isinstance(handle, (list, tuple)):
                handle = PointHandle(x=handle[0],
                                     y=handle[1],
                                     parent=self,
                                     index=index)
            elif hasattr(handle, 'x') and hasattr(handle, 'y'):
                handle = PointHandle(x=handle.x(),
                                     y=handle.y(),
                                     parent=self,
                                     index=index)
            new_handles.append(handle)
            index += 1

        # Update handles list
        self.handles = new_handles
        self.polygon.points = new_handles

        # Set current visibility status
        for handle in self.handles:
            handle.setVisible(self.get_edit_status())

        # Set new point count
        self.point_count = len(self.handles)

    # =========================================================================
    # Mouse events ---
    def hoverEnterEvent(self, event=None):
        '''Update tooltip on hoover with associated controls in edit mode
        '''
        if __EDIT_MODE__.get():
            text = '\n'.join(self.get_controls())
            self.setToolTip(text)
        DefaultPolygon.hoverEnterEvent(self, event)

    def mousePressEvent(self, event):
        '''Event called on mouse press
        '''
        # Simply run default event in edit mode, and exit
        if __EDIT_MODE__.get():
            return DefaultPolygon.mousePressEvent(self, event)

        # Run selection on left mouse button event
        if event.buttons() == QtCore.Qt.LeftButton:
            # Run custom script action
            if self.get_custom_action_mode():
                self.mouse_press_custom_action(event)
            # Run default selection action
            else:
                self.mouse_press_select_event(event)

        # Set focus to maya window
        maya_window = qt_handlers.get_maya_window()
        if maya_window:
            maya_window.setFocus()

    def mouse_press_select_event(self, event):
        '''
        Default select event on mouse press.
        Will select associated controls
        '''
        # Get keyboard modifier
        modifiers = event.modifiers()
        modifier = None

        # Shift cases (toggle)
        if modifiers == QtCore.Qt.ShiftModifier:
            modifier = "shift"

        # Controls case
        if modifiers == QtCore.Qt.ControlModifier:
            modifier = "control"

        # Alt case (remove)
        if modifiers == QtCore.Qt.AltModifier:
            modifier = "alt"

        # Call action
        self.select_associated_controls(modifier=modifier)

    def mouse_press_custom_action(self, event):
        '''Custom script action on mouse press
        '''
        # Run custom action script with picker item environnement
        python_handlers.safe_code_exec(self.get_custom_action_script(),
                                       env=self.get_exec_env())

    def mouseDoubleClickEvent(self, event):
        '''Event called when mouse is double clicked
        '''
        if not __EDIT_MODE__.get():
            return

        self.edit_options()

    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        # Context menu for edition mode
        if __EDIT_MODE__.get():
            self.edit_context_menu(event)

        # Context menu for default mode
        else:
            self.default_context_menu(event)

        # Force call release method
        # self.mouseReleaseEvent(event)

    def edit_context_menu(self, event):
        '''Context menu (right click) in edition mode
        '''
        # Init context menu
        menu = QtWidgets.QMenu(self.parent())

        # Build edit context menu
        options_action = QtWidgets.QAction("Options", None)
        options_action.triggered.connect(self.edit_options)
        menu.addAction(options_action)

        handles_action = QtWidgets.QAction("Toggle handles", None)
        handles_action.triggered.connect(self.toggle_edit_status)
        menu.addAction(handles_action)

        menu.addSeparator()

        # Shape options menu
        shape_menu = QtWidgets.QMenu(menu)
        shape_menu.setTitle("Shape")

        move_action = QtWidgets.QAction("Move to center", None)
        move_action.triggered.connect(self.move_to_center)
        shape_menu.addAction(move_action)

        shp_mirror_action = QtWidgets.QAction("Mirror shape", None)
        shp_mirror_action.triggered.connect(self.mirror_shape)
        shape_menu.addAction(shp_mirror_action)

        color_mirror_action = QtWidgets.QAction("Mirror color", None)
        color_mirror_action.triggered.connect(self.mirror_color)
        shape_menu.addAction(color_mirror_action)

        menu.addMenu(shape_menu)

        move_back_action = QtWidgets.QAction("Move to back", None)
        move_back_action.triggered.connect(self.move_to_back)
        menu.addAction(move_back_action)

        move_front_action = QtWidgets.QAction("Move to front", None)
        move_front_action.triggered.connect(self.move_to_front)
        menu.addAction(move_front_action)

        menu.addSeparator()

        # Copy handling
        copy_action = QtWidgets.QAction("Copy", None)
        copy_action.triggered.connect(self.copy_event)
        menu.addAction(copy_action)

        paste_action = QtWidgets.QAction("Paste", None)
        if DataCopyDialog.__DATA__:
            paste_action.triggered.connect(self.past_event)
        else:
            paste_action.setEnabled(False)
        menu.addAction(paste_action)

        paste_options_action = QtWidgets.QAction("Paste Options", None)
        if DataCopyDialog.__DATA__:
            paste_options_action.triggered.connect(self.past_option_event)
        else:
            paste_options_action.setEnabled(False)
        menu.addAction(paste_options_action)

        menu.addSeparator()

        # Duplicate options
        duplicate_action = QtWidgets.QAction("Duplicate", None)
        duplicate_action.triggered.connect(self.duplicate)
        menu.addAction(duplicate_action)

        mirror_dup_action = QtWidgets.QAction("Duplicate/mirror", None)
        mirror_dup_action.triggered.connect(self.duplicate_and_mirror)
        menu.addAction(mirror_dup_action)

        menu.addSeparator()

        # Delete
        remove_action = QtWidgets.QAction("Remove", None)
        remove_action.triggered.connect(self.remove)
        menu.addAction(remove_action)

        menu.addSeparator()

        # Control association
        ctrls_menu = QtWidgets.QMenu(menu)
        ctrls_menu.setTitle("Ctrls Association")

        select_action = QtWidgets.QAction("Select", None)
        select_action.triggered.connect(self.select_associated_controls)
        ctrls_menu.addAction(select_action)

        replace_action = QtWidgets.QAction("Replace with selection", None)
        replace_action.triggered.connect(self.replace_controls_selection)
        ctrls_menu.addAction(replace_action)

        menu.addMenu(ctrls_menu)

        # Open context menu under mouse
        # offset position to prevent accidental mouse release on menu
        offseted_pos = event.pos() + QtCore.QPointF(5, 0)
        scene_pos = self.mapToScene(offseted_pos)
        view_pos = self.parent().mapFromScene(scene_pos)
        screen_pos = self.parent().mapToGlobal(view_pos)
        menu.exec_(screen_pos)

    def default_context_menu(self, event):
        '''Context menu (right click) out of edition mode (animation)
        '''
        # Init context menu
        menu = QtWidgets.QMenu(self.parent())

        # Add reset action
        # reset_action = QtWidgets.QAction("Reset", None)
        # reset_action.triggered.connect(self.active_control.reset_to_bind_pose)
        # menu.addAction(reset_action)

        # Add custom actions
        actions = self._get_custom_action_menus()
        for action in actions:
            menu.addAction(action)

        # Abort on empty menu
        if menu.isEmpty():
            return

        # Open context menu under mouse
        # offset position to prevent accidental mouse release on menu
        offseted_pos = event.pos() + QtCore.QPointF(5, 0)
        scene_pos = self.mapToScene(offseted_pos)
        view_pos = self.parent().mapFromScene(scene_pos)
        screen_pos = self.parent().mapToGlobal(view_pos)
        menu.exec_(screen_pos)

    def get_exec_env(self):
        '''
        Will return proper environnement dictionnary for eval execs
        (Will provide related controls as __CONTROLS__
        and __NAMESPACE__ variables)
        '''
        # Init env
        env = {}

        # Add controls vars
        env["__CONTROLS__"] = self.get_controls()
        ctrls = self.get_controls()
        env["__FLATCONTROLS__"] = maya_handlers.get_flattened_nodes(ctrls)
        env["__NAMESPACE__"] = self.get_namespace()

        return env

    def _get_custom_action_menus(self):
        # Init action list to fix loop problem where qmenu only
        # show last action when using the same variable name ...
        actions = []

        # Define custom exec cmd wrapper
        def wrapper(cmd):
            def custom_eval(*args, **kwargs):
                python_handlers.safe_code_exec(cmd,
                                               env=self.get_exec_env())
            return custom_eval

        # Get active controls custom menus
        custom_data = self.get_custom_menus()
        if not custom_data:
            return actions

        # Build menu
        for i in range(len(custom_data)):
            actions.append(QtWidgets.QAction(custom_data[i][0], None))
            actions[i].triggered.connect(wrapper(custom_data[i][1]))

        return actions

    # =========================================================================
    # Edit picker item options ---
    def edit_options(self):
        '''Open Edit options window
        '''
        # Delete old window
        if self.edit_window:
            try:
                self.edit_window.close()
                self.edit_window.deleteLater()
            except Exception:
                pass

        # Init new window
        self.edit_window = ItemOptionsWindow(parent=self.main_window,
                                             picker_item=self)

        # Show window
        self.edit_window.show()
        self.edit_window.raise_()

    def set_edit_status(self, status):
        '''Set picker item edit status (handle visibility etc.)
        '''
        self._edit_status = status

        for handle in self.handles:
            handle.setVisible(status)

        self.polygon.set_edit_status(status)

    def get_edit_status(self):
        return self._edit_status

    def toggle_edit_status(self):
        '''Will toggle handle visibility status
        '''
        self.set_edit_status(not self._edit_status)

    # =========================================================================
    # Properties methods ---
    def get_color(self):
        '''Get polygon color
        '''
        return self.polygon.get_color()

    def set_color(self, color=None):
        '''Set polygon color
        '''
        self.polygon.set_color(color)

    # =========================================================================
    # Text handling ---
    def get_text(self):
        return self.text.get_text()

    def set_text(self, text):
        self.text.set_text(text)

    def get_text_color(self):
        return self.text.get_color()

    def set_text_color(self, color):
        self.text.set_color(color)

    def get_text_size(self):
        return self.text.get_size()

    def set_text_size(self, size):
        self.text.set_size(size)

    # =========================================================================
    # Scene Placement ---
    def move_to_front(self):
        '''Move picker item to scene front
        '''
        # Get current scene
        scene = self.scene()

        # Move to temp scene
        tmp_scene = QtWidgets.QGraphicsScene()
        tmp_scene.addItem(self)

        # Add to current scene (will be put on top)
        scene.addItem(self)

        # Clean
        tmp_scene.deleteLater()

    def move_to_back(self):
        '''Move picker item to background level behind other items
        '''
        # Get picker Items
        picker_items = self.scene().get_picker_items()

        # Reverse list since items are returned front to back
        picker_items.reverse()

        # Move current item to front of list (back)
        picker_items.remove(self)
        picker_items.insert(0, self)

        # Move each item in proper oder to front of scene
        # That will add them in the proper order to the scene
        for item in picker_items:
            item.move_to_front()

    def move_to_center(self):
        '''Move picker item to pos 0,0
        '''
        self.setPos(0, 0)

    def remove(self):
        self.scene().removeItem(self)
        self.setParent(None)
        self.deleteLater()

    # =========================================================================
    # Ducplicate and mirror methods ---
    def mirror_position(self):
        '''Mirror picker position (on X axis)
        '''
        self.setX(-1 * self.pos().x())

    def mirror_shape(self):
        '''Will mirror polygon handles position on X axis
        '''
        for handle in self.handles:
            handle.mirror_x_position()

    def mirror_color(self):
        '''Will reverse red/bleu rgb values for the polygon color
        '''
        old_color = self.get_color()
        new_color = QtGui.QColor(old_color.blue(),
                                 old_color.green(),
                                 old_color.red(),
                                 alpha=old_color.alpha())
        self.set_color(new_color)

    def duplicate(self, *args, **kwargs):
        '''Will create a new picker item and copy data over.
        '''
        # Create new picker item
        new_item = PickerItem()
        new_item.setParent(self.parent())
        self.scene().addItem(new_item)

        # Copy data over
        data = self.get_data()
        new_item.set_data(data)

        return new_item

    def duplicate_and_mirror(self):
        '''Duplicate and mirror picker item
        '''
        new_item = self.duplicate()
        new_item.mirror_color()
        new_item.mirror_position()
        new_item.mirror_shape()
        if self.get_controls():
            new_item.search_and_replace_controls()
        return new_item

    def copy_event(self):
        '''Store pickerItem data for copy/paste support
        '''
        DataCopyDialog.get(self)

    def past_event(self):
        '''Apply previously stored pickerItem data
        '''
        DataCopyDialog.set(self)

    def past_option_event(self):
        '''Will open Paste option dialog window
        '''
        DataCopyDialog.options(self)

    # =========================================================================
    # Transforms ---
    def scale_shape(self, x=1.0, y=1.0, world=False):
        '''Will scale shape based on axis x/y factors
        '''
        # Scale handles
        for handle in self.handles:
            handle.scale_pos(x, y)

        # Scale position
        if world:
            factor = QtGui.QTransform().scale(x, y)
            self.setPos(self.pos() * factor)

        self.update()

    # =========================================================================
    # Custom action handling ---
    def get_custom_action_mode(self):
        return self.custom_action

    def set_custom_action_mode(self, state):
        self.custom_action = state

    def set_custom_action_script(self, cmd):
        self.custom_action_script = cmd

    def get_custom_action_script(self):
        return self.custom_action_script

    # =========================================================================
    # Controls handling ---
    def get_namespace(self):
        '''Will return associated namespace
        '''
        return self.namespace

    def set_control_list(self, ctrls=list()):
        '''Update associated control list
        '''
        self.controls = ctrls

    def get_controls(self, with_namespace=True):
        '''Return associated controls
        '''
        # Returned controls without namespace (as data stored)
        if not with_namespace:
            return list(self.controls)

        # Get namespace
        namespace = self.get_namespace()

        # No namespace, return nodes
        if not namespace:
            return list(self.controls)

        # Prefix nodes with namespace
        nodes = []
        for node in self.controls:
            nodes.append("{}:{}".format(namespace, node))

        return nodes

    def append_control(self, ctrl):
        '''Add control to list
        '''
        self.controls.append(ctrl)

    def remove_control(self, ctrl):
        '''Remove control from list
        '''
        if ctrl not in self.controls:
            return
        self.controls.remove(ctrl)

    def search_and_replace_controls(self):
        '''Will search and replace in associated controls names
        '''
        # Open Search and replace dialog window
        search, replace, ok = SearchAndReplaceDialog.get()
        if not ok:
            return False

        # Parse controls
        node_missing = False
        controls = self.get_controls()[:]
        for i in range(len(controls)):
            controls[i] = re.sub(search, replace, controls[i])
            if not cmds.objExists(controls[i]):
                node_missing = True

        # Print warning
        if node_missing:
            QtWidgets.QMessageBox.warning(self.parent(),
                                          "Warning",
                                          "Some target controls do not exist")

        # Update list
        self.set_control_list(controls)

        return True

    def select_associated_controls(self, modifier=None):
        '''Will select maya associated controls
        '''
        maya_handlers.select_nodes(self.get_controls(),
                                   modifier=modifier)

    def replace_controls_selection(self):
        '''Will replace controls association with current selection
        '''
        self.set_control_list([])
        self.add_selected_controls()

    def add_selected_controls(self):
        '''Add selected controls to control list
        '''
        # Get selection
        sel = cmds.ls(sl=True)

        # Add to stored list
        for ctrl in sel:
            if ctrl in self.get_controls():
                continue
            self.append_control(ctrl)

    def is_selected(self):
        '''
        Will return True if a related control is currently selected
        (Only works with polygon that have a single associated maya_node)
        '''
        # Get controls associated nodes
        controls = self.get_controls()

        # Abort if not single control polygon
        if not len(controls) == 1:
            return False

        # Check
        return __SELECTION__.is_selected(controls[0])

    def set_selected_state(self, state):
        '''Will set border color feedback based on selection state
        '''
        self.polygon.set_selected_state(state)

    def run_selection_check(self):
        '''Will set selection state based on selection status
        '''
        self.set_selected_state(self.is_selected())

    # =========================================================================
    # Custom menus handling ---
    def set_custom_menus(self, menus):
        '''Set custom menu list for current poly data
        '''
        self.custom_menus = list(menus)

    def get_custom_menus(self):
        '''Return current menu list for current poly data
        '''
        return self.custom_menus

    # =========================================================================
    # Data handling ---
    def set_data(self, data):
        '''Set picker item from data dictionary
        '''
        # Set color
        if "color" in data:
            color = QtGui.QColor(*data["color"])
            self.set_color(color)

        # Set position
        if "position" in data:
            position = data.get("position", [0, 0])
            self.setPos(*position)

        # Set handles
        if "handles" in data:
            self.set_handles(data["handles"])

        # Set action mode
        if data.get("action_mode", False):
            self.set_custom_action_mode(True)
            self.set_custom_action_script(data.get("action_script", None))

        # Set controls
        if "controls" in data:
            self.set_control_list(data["controls"])

        # Set custom menus
        if "menus" in data:
            self.set_custom_menus(data["menus"])

        # Set text
        if "text" in data:
            self.set_text(data["text"])
            self.set_text_size(data["text_size"])
            color = QtGui.QColor(*data["text_color"])
            self.set_text_color(color)

    def get_data(self):
        '''Get picker item data in dictionary form
        '''
        # Init data dict
        data = {}

        # Add polygon color
        data["color"] = self.get_color().getRgb()

        # Add position
        data["position"] = [self.x(), self.y()]

        # Add handles datas
        handles_data = []
        for handle in self.handles:
            handles_data.append([handle.x(), handle.y()])
        data["handles"] = handles_data

        # Add mode data
        if self.get_custom_action_mode():
            data["action_mode"] = True
            data["action_script"] = self.get_custom_action_script()

        # Add controls data
        if self.get_controls():
            data["controls"] = self.get_controls(with_namespace=False)

        # Add custom menus data
        if self.get_custom_menus():
            data["menus"] = self.get_custom_menus()

        if self.get_text():
            data["text"] = self.get_text()
            data["text_size"] = self.get_text_size()
            data["text_color"] = self.get_text_color().getRgb()

        return data


class HandlesPositionWindow(QtWidgets.QMainWindow):
    '''Whild window to edit picker item handles local positions
    '''
    __OBJ_NAME__ = "picker_item_handles_window"
    __TITLE__ = "Handles positions"

    __DEFAULT_WIDTH__ = 250
    __DEFAULT_HEIGHT__ = 300

    def __init__(self, parent=None, picker_item=None):
        QtWidgets.QMainWindow.__init__(self, parent=None)

        self.picker_item = picker_item

        # Run setup
        self.setup()

    def setup(self):
        '''Setup window elements
        '''
        # Main window setting
        self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)
        self.resize(self.__DEFAULT_WIDTH__, self.__DEFAULT_HEIGHT__)

        # Set size policies
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        # self.setSizePolicy(sizePolicy)

        # Create main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QVBoxLayout(self.main_widget)

        self.setCentralWidget(self.main_widget)

        # Add content
        self.add_position_table()
        self.add_option_buttons()

        # Populate table
        self.populate_table()

    def add_position_table(self):
        self.table = QtWidgets.QTableWidget(self)

        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["X", "Y"])

        self.main_layout.addWidget(self.table)

    def add_option_buttons(self):
        '''Add window option buttons
        '''
        # Refresh button
        self.refresh_button = CallbackButton(callback=self.refresh_event)
        self.refresh_button.setText("Refresh")
        self.main_layout.addWidget(self.refresh_button)

    def refresh_event(self):
        '''Refresh table event
        '''
        self.populate_table()

    def populate_table(self):
        '''Populate table with X/Y handles position items
        '''
        # Clear table
        while self.table.rowCount():
            self.table.removeRow(0)

        # Abort if no pickeritem specified
        if not self.picker_item:
            return

        # Parse handles
        handles = self.picker_item.get_handles()
        for i in range(len(handles)):
            self.table.insertRow(i)
            spin_box = CallBackDoubleSpinBox(callback=handles[i].setX,
                                             value=handles[i].x(),
                                             min=-999)
            self.table.setCellWidget(i, 0, spin_box)

            spin_box = CallBackDoubleSpinBox(callback=handles[i].setY,
                                             value=handles[i].y(),
                                             min=-999)
            self.table.setCellWidget(i, 1, spin_box)

    def display_handles_index(self, status=True):
        '''Display related picker handles index
        '''
        for handle in self.picker_item.get_handles():
            handle.enable_index_draw(status)

    def closeEvent(self, *args, **kwargs):
        self.display_handles_index(status=False)
        return QtWidgets.QMainWindow.closeEvent(self, *args, **kwargs)

    def show(self, *args, **kwargs):
        '''Override default show function to display related picker
        handles index
        '''
        self.display_handles_index(status=True)
        return QtWidgets.QMainWindow.show(self, *args, **kwargs)


class ItemOptionsWindow(QtWidgets.QMainWindow):
    '''Child window to edit shape options
    '''
    __OBJ_NAME__ = "ctrl_picker_edit_window"
    __TITLE__ = "Picker Item Options"

    #  ----------------------------------------------------------------------
    # constructor
    def __init__(self, parent=None, picker_item=None):
        QtWidgets.QMainWindow.__init__(self, parent=parent)
        self.picker_item = picker_item

        # Define size
        self.default_width = 270
        self.default_height = 140

        # Run setup
        self.setup()

        # Other
        self.handles_window = None
        self.event_disabled = False

    def setup(self):
        '''Setup window elements
        '''
        # Main window setting
        self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)
        self.resize(self.default_width, self.default_height)

        # Set size policies
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                           QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        # Create main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.main_layout = QtWidgets.QHBoxLayout(self.main_widget)

        self.left_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.left_layout)

        self.right_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.right_layout)

        self.control_layout = QtWidgets.QVBoxLayout()
        self.control_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.addLayout(self.control_layout)

        self.setCentralWidget(self.main_widget)

        # Add content
        self.add_main_options()
        self.add_position_options()
        self.add_color_options()
        self.add_scale_options()
        self.add_text_options()
        self.add_action_mode_field()
        self.add_target_control_field()
        self.add_custom_menus_field()

        # Add layouts stretch
        self.left_layout.addStretch()

        # Udpate fields
        self._update_shape_infos()
        self._update_position_infos()
        self._update_color_infos()
        self._update_text_infos()
        self._update_ctrls_infos()
        self._update_menus_infos()

    def closeEvent(self, *args, **kwargs):
        '''Overwriting close event to close child windows too
        '''
        # Close child windows
        if self.handles_window:
            try:
                self.handles_window.close()
            except Exception:
                pass

        QtWidgets.QMainWindow.closeEvent(self, *args, **kwargs)

    def _update_shape_infos(self):
        self.event_disabled = True
        self.handles_cb.setChecked(self.picker_item.get_edit_status())
        self.count_sb.setValue(self.picker_item.point_count)
        self.event_disabled = False

    def _update_position_infos(self):
        self.event_disabled = True
        position = self.picker_item.pos()
        self.pos_x_sb.setValue(position.x())
        self.pos_y_sb.setValue(position.y())
        self.event_disabled = False

    def _update_color_infos(self):
        self.event_disabled = True
        self._set_color_button(self.picker_item.get_color())
        self.alpha_sb.setValue(self.picker_item.get_color().alpha())
        self.event_disabled = False

    def _update_text_infos(self):
        self.event_disabled = True

        # Retrieve et set text field
        text = self.picker_item.get_text()
        if text:
            self.text_field.setText(text)

        # Set text color fields
        self._set_text_color_button(self.picker_item.get_text_color())
        self.text_alpha_sb.setValue(self.picker_item.get_text_color().alpha())
        self.event_disabled = False

    def _update_ctrls_infos(self):
        self._populate_ctrl_list_widget()

    def _update_menus_infos(self):
        self._populate_menu_list_widget()

    def add_main_options(self):
        '''Add vertex count option
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Main Properties")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add edit check box
        func = self.handles_cb_event
        self.handles_cb = CallbackCheckBoxWidget(callback=func)
        self.handles_cb.setText("Show handles")

        layout.addWidget(self.handles_cb)

        # Add point count spin box
        spin_layout = QtWidgets.QHBoxLayout()

        spin_label = QtWidgets.QLabel()
        spin_label.setText("Vtx Count")
        spin_layout.addWidget(spin_label)

        point_count = self.picker_item.edit_point_count
        self.count_sb = CallBackSpinBox(callback=point_count,
                                        value=self.picker_item.point_count)
        self.count_sb.setMinimum(2)
        spin_layout.addWidget(self.count_sb)

        layout.addLayout(spin_layout)

        # Add handles position button
        handle_position = self.edit_handles_position_event
        handles_button = CallbackButton(callback=handle_position)
        handles_button.setText("Handles Positions")
        layout.addWidget(handles_button)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_position_options(self):
        '''Add position field for precise control positioning
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Position")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Get bary-center
        position = self.picker_item.pos()

        # Add X position spin box
        spin_layout = QtWidgets.QHBoxLayout()

        spin_label = QtWidgets.QLabel()
        spin_label.setText("X")
        spin_layout.addWidget(spin_label)

        edit_pos_event = self.edit_position_event
        self.pos_x_sb = CallBackDoubleSpinBox(callback=edit_pos_event,
                                              value=position.x(),
                                              min=-9999)
        spin_layout.addWidget(self.pos_x_sb)

        layout.addLayout(spin_layout)

        # Add Y position spin box
        spin_layout = QtWidgets.QHBoxLayout()

        label = QtWidgets.QLabel()
        label.setText('Y')
        spin_layout.addWidget(label)

        self.pos_y_sb = CallBackDoubleSpinBox(callback=edit_pos_event,
                                              value=position.y(),
                                              min=-9999)
        spin_layout.addWidget(self.pos_y_sb)

        layout.addLayout(spin_layout)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def _set_color_button(self, color):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.color_button.setPalette(palette)
        self.color_button.setAutoFillBackground(True)

    def _set_text_color_button(self, color):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.text_color_button.setPalette(palette)
        self.text_color_button.setAutoFillBackground(True)

    def add_color_options(self):
        '''Add color edition field for polygon
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Color options")

        # Add layout
        layout = QtWidgets.QHBoxLayout(group_box)

        # Add color button
        self.color_button = CallbackButton(callback=self.change_color_event)

        layout.addWidget(self.color_button)

        # Add alpha spin box
        layout.addStretch()

        label = QtWidgets.QLabel()
        label.setText("Alpha")
        layout.addWidget(label)

        alpha_event = self.change_color_alpha_event
        alpha_value = self.picker_item.get_color().alpha()
        self.alpha_sb = CallBackSpinBox(callback=alpha_event,
                                        value=alpha_value,
                                        max=255)
        layout.addWidget(self.alpha_sb)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_text_options(self):
        '''Add text option fields
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Text options")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add Caption text field
        self.text_field = CallbackLineEdit(self.set_text_event)
        layout.addWidget(self.text_field)

        # Add size factor spin box
        spin_layout = QtWidgets.QHBoxLayout()

        spin_label = QtWidgets.QLabel()
        spin_label.setText("Size factor")
        spin_layout.addWidget(spin_label)

        text_size = self.picker_item.get_text_size()
        value_sb = CallBackDoubleSpinBox(callback=self.edit_text_size_event,
                                         value=text_size)
        spin_layout.addWidget(value_sb)

        layout.addLayout(spin_layout)

        # Add color layout
        color_layout = QtWidgets.QHBoxLayout(group_box)

        # Add color button
        color_event = self.change_text_color_event
        self.text_color_button = CallbackButton(callback=color_event)

        color_layout.addWidget(self.text_color_button)

        # Add alpha spin box
        color_layout.addStretch()

        label = QtWidgets.QLabel()
        label.setText("Alpha")
        color_layout.addWidget(label)

        alpha_event = self.change_text_alpha_event
        alpha_value = self.picker_item.get_text_color().alpha()
        self.text_alpha_sb = CallBackSpinBox(callback=alpha_event,
                                             value=alpha_value,
                                             max=255)
        color_layout.addWidget(self.text_alpha_sb)

        # Add color layout to group box layout
        layout.addLayout(color_layout)

        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_scale_options(self):
        '''Add scale group box options
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Scale")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add edit check box
        self.worldspace_box = QtWidgets.QCheckBox()
        self.worldspace_box.setText("World space")

        layout.addWidget(self.worldspace_box)

        # Add alpha spin box
        spin_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(spin_layout)

        label = QtWidgets.QLabel()
        label.setText("Factor")
        spin_layout.addWidget(label)

        self.scale_sb = QtWidgets.QDoubleSpinBox()
        self.scale_sb.setValue(1.1)
        self.scale_sb.setSingleStep(0.05)
        spin_layout.addWidget(self.scale_sb)

        # Add scale buttons
        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        btn = CallbackButton(callback=self.scale_event, x=True)
        btn.setText("X")
        btn_layout.addWidget(btn)

        btn = CallbackButton(callback=self.scale_event, y=True)
        btn.setText("Y")
        btn_layout.addWidget(btn)

        btn = CallbackButton(callback=self.scale_event, x=True, y=True)
        btn.setText("XY")
        btn_layout.addWidget(btn)

        # Add to main left layout
        self.left_layout.addWidget(group_box)

    def add_action_mode_field(self):
        '''Add custom action mode field group box
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Action Mode")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Add default select mode radio button
        custom_mode = not self.picker_item.get_custom_action_mode()
        default_rad = CallbackRadioButtonWidget("default",
                                                self.mode_radio_event,
                                                checked=custom_mode)
        default_rad.setText("Default action (select)")
        default_rad.setToolTip(
            "Run default selection action on related controls")
        layout.addWidget(default_rad)

        # Add custom action script radio button
        action_mode = self.picker_item.get_custom_action_mode()
        custom_rad = CallbackRadioButtonWidget("custom",
                                               self.mode_radio_event,
                                               checked=action_mode)
        custom_rad.setText("Custom action (script)")
        custom_rad.setToolTip("Change mode to run a custom action script")
        layout.addWidget(custom_rad)

        # Add edit custom script button
        custom_script = self.edit_custom_action_script
        custom_script_btn = CallbackButton(callback=custom_script)
        custom_script_btn.setText("Edit Action script")
        custom_script_btn.setToolTip("Open custom action script edit window")
        layout.addWidget(custom_script_btn)

        self.control_layout.addWidget(group_box)

    def add_target_control_field(self):
        '''Add target control association group box
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Control Association")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Init list object
        ctrl_name = self.edit_ctrl_name_event
        self.control_list = CallbackListWidget(callback=ctrl_name)
        self.control_list.setToolTip("Associated controls/objects that will be\
         selected when clicking picker item")
        layout.addWidget(self.control_list)

        # Add buttons
        btn_layout1 = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout1)

        btn = CallbackButton(callback=self.add_selected_controls_event)
        btn.setText("Add Selection")
        btn.setToolTip("Add selected controls to list")
        btn.setMinimumWidth(75)
        btn_layout1.addWidget(btn)

        btn = CallbackButton(callback=self.remove_controls_event)
        btn.setText("Remove")
        btn.setToolTip("Remove selected controls")
        btn.setMinimumWidth(75)
        btn_layout1.addWidget(btn)

        btn = CallbackButton(callback=self.search_replace_controls_event)
        btn.setText("Search & Replace")
        btn.setToolTip("Will search and replace all controls names")
        layout.addWidget(btn)

        self.control_layout.addWidget(group_box)

    def add_custom_menus_field(self):
        '''Add custom menu management groupe box
        '''
        # Create group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Custom Menus")

        # Add layout
        layout = QtWidgets.QVBoxLayout(group_box)

        # Init list object
        self.menus_list = CallbackListWidget(callback=self.edit_menu_event)
        self.menus_list.setToolTip(
            "Custom action menus that will be accessible through right clicking the picker item in animation mode")
        layout.addWidget(self.menus_list)

        # Add buttons
        btn_layout1 = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout1)

        btn = CallbackButton(callback=self.new_menu_event)
        btn.setText("New")
        btn.setMinimumWidth(60)
        btn_layout1.addWidget(btn)

        btn = CallbackButton(callback=self.remove_menus_event)
        btn.setText("Remove")
        btn.setMinimumWidth(60)
        btn_layout1.addWidget(btn)

        self.right_layout.addWidget(group_box)

    # =========================================================================
    # Events
    def handles_cb_event(self, value=False):
        '''Toggle edit mode for shape
        '''
        self.picker_item.set_edit_status(value)

    def edit_handles_position_event(self):

        # Delete old window
        if self.handles_window:
            try:
                self.handles_window.close()
                self.handles_window.deleteLater()
            except Exception:
                pass

        # Init new window
        picker_item = self.picker_item
        self.handles_window = HandlesPositionWindow(parent=self,
                                                    picker_item=picker_item)

        # Show window
        self.handles_window.show()
        self.handles_window.raise_()

    def edit_position_event(self, value=0):
        '''Will move polygon based on new values
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        x = self.pos_x_sb.value()
        y = self.pos_y_sb.value()

        self.picker_item.setPos(QtCore.QPointF(x, y))

    def change_color_alpha_event(self, value=255):
        '''Will edit the polygon transparency alpha value
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Get current color
        color = self.picker_item.get_color()
        color.setAlpha(value)

        # Update color
        self.picker_item.set_color(color)

    def change_color_event(self):
        '''Will edit polygon color based on new values
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Open color picker dialog
        picker_color = self.picker_item.get_color()
        color = QtWidgets.QColorDialog.getColor(initial=picker_color,
                                                parent=self)

        # Abort on invalid color (cancel button)
        if not color.isValid():
            return

        # Update button color
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.color_button.setPalette(palette)

        # Edit new color alpha
        alpha = self.picker_item.get_color().alpha()
        color.setAlpha(alpha)

        # Update color
        self.picker_item.set_color(color)

    def scale_event(self, x=False, y=False):
        '''Will scale polygon on specified axis based on scale factor
        value from spin box
        '''
        # Get scale factor value
        scale_factor = self.scale_sb.value()

        # Build kwargs
        kwargs = {"x": 1.0, "y": 1.0}
        if x:
            kwargs["x"] = scale_factor
        if y:
            kwargs["y"] = scale_factor

        # Check space
        if self.worldspace_box.isChecked():
            kwargs["world"] = True

        # Apply scale
        self.picker_item.scale_shape(**kwargs)

    def set_text_event(self, text=None):
        '''Will set polygon text to field
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        text = unicode(text)
        self.picker_item.set_text(text)

    def edit_text_size_event(self, value=1):
        '''Will edit text size factor
        '''
        self.picker_item.set_text_size(value)

    def change_text_alpha_event(self, value=255):
        '''Will edit the polygon transparency alpha value
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Get current color
        color = self.picker_item.get_text_color()
        color.setAlpha(value)

        # Update color
        self.picker_item.set_text_color(color)

    def change_text_color_event(self):
        '''Will edit polygon color based on new values
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        # Open color picker dialog
        picker_color = self.picker_item.get_text_color()
        color = QtWidgets.QColorDialog.getColor(initial=picker_color,
                                                parent=self)

        # Abort on invalid color (cancel button)
        if not color.isValid():
            return

        # Update button color
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.text_color_button.setPalette(palette)

        # Edit new color alpha
        alpha = self.picker_item.get_text_color().alpha()
        color.setAlpha(alpha)

        # Update color
        self.picker_item.set_text_color(color)

    # =========================================================================
    # Custom action management
    def mode_radio_event(self, mode):
        '''Action mode change event
        '''
        # Skip if event is disabled (updating ui value)
        if self.event_disabled:
            return

        if mode == "default":
            self.picker_item.custom_action = False

        elif mode == "custom":
            self.picker_item.custom_action = True

    def edit_custom_action_script(self):

        # Open input window
        action_script = self.picker_item.custom_action_script
        cmd, ok = CustomScriptEditDialog.get(cmd=action_script,
                                             item=self.picker_item)
        if not (ok and cmd):
            return

        self.picker_item.set_custom_action_script(cmd)

    # =========================================================================
    # Control management
    def _populate_ctrl_list_widget(self):
        '''Will update/populate list with current shape ctrls
        '''
        # Empty list
        self.control_list.clear()

        # Populate node list
        controls = self.picker_item.get_controls()
        for i in range(len(controls)):
            item = CtrlListWidgetItem(index=i)
            item.setText(controls[i])
            self.control_list.addItem(item)

       # if controls:
           # self.control_list.setCurrentRow(0)

    def edit_ctrl_name_event(self, item=None):
        '''Double click event on associated ctrls list
        '''
        if not item:
            return

        # Open input window
        line_normal = QtWidgets.QLineEdit.Normal
        name, ok = QtWidgets.QInputDialog.getText(self,
                                                  "Ctrl name",
                                                  "New name",
                                                  mode=line_normal,
                                                  text=str(item.text()))
        if not (ok and name):
            return

        # Update influence name
        new_name = item.setText(name)
        if new_name:
            self.update_shape_controls_list()

        # Deselect item
        self.control_list.clearSelection()

    def add_selected_controls_event(self):
        '''Will add maya selected object to control list
        '''
        self.picker_item.add_selected_controls()

        # Update display
        self._populate_ctrl_list_widget()

    def remove_controls_event(self):
        '''Will remove selected item list from stored controls
        '''
        # Get selected item
        items = self.control_list.selectedItems()
        assert items, "no list item selected"

        # Remove item from list
        for item in items:
            self.picker_item.remove_control(item.node())

        # Update display
        self._populate_ctrl_list_widget()

    def search_replace_controls_event(self):
        '''Will search and replace controls names for related picker item
        '''
        if self.picker_item.search_and_replace_controls():
            self._populate_ctrl_list_widget()

    def get_controls_from_list(self):
        '''Return the controls from list widget
        '''
        ctrls = []
        for i in range(self.control_list.count()):
            item = self.control_list.item(i)
            ctrls.append(item.node())
        return ctrls

    def update_shape_controls_list(self):
        '''Update shape stored control list
        '''
        ctrls = self.get_controls_from_list()
        self.picker_item.set_control_list(ctrls)

    # =========================================================================
    # Menus management
    def _add_menu_item(self, text=None):
        '''Add a menu item to menu list widget
        '''
        item = QtWidgets.QListWidgetItem()
        item.index = self.menus_list.count()
        if text:
            item.setText(text)
        self.menus_list.addItem(item)
        return item

    def _populate_menu_list_widget(self):
        '''Populate list widget with menu data
        '''
        # Empty list
        self.menus_list.clear()

        # Populate node list
        menus_data = self.picker_item.get_custom_menus()
        for i in range(len(menus_data)):
            self._add_menu_item(text=menus_data[i][0])

    def _update_menu_data(self, index, name, cmd):
        '''Update custom menu data
        '''
        menu_data = self.picker_item.get_custom_menus()
        if index > len(menu_data) - 1:
            menu_data.append([name, cmd])
        else:
            menu_data[index] = [name, cmd]
        self.picker_item.set_custom_menus(menu_data)

    def edit_menu_event(self, item=None):
        '''Double click event on associated menu list
        '''
        if not item:
            return

        name, cmd = self.picker_item.get_custom_menus()[item.index]

        # Open input window
        name, cmd, ok = CustomMenuEditDialog.get(name=name,
                                                 cmd=cmd,
                                                 item=self.picker_item)
        if not (ok and name and cmd):
            return

        # Update menu display name
        item.setText(name)

        # Update menu data
        self._update_menu_data(item.index, name, cmd)

        # Deselect item
        self.menus_list.clearSelection()

    def new_menu_event(self):
        '''Add new custom menu btn event
        '''
        # Open input window
        name, cmd, ok = CustomMenuEditDialog.get(item=self.picker_item)
        if not (ok and name and cmd):
            return

        # Update menu display name
        item = self._add_menu_item(text=name)

        # Update menu data
        self._update_menu_data(item.index, name, cmd)

    def remove_menus_event(self):
        '''Remove custom menu btn event
        '''
        # Get selected item
        items = self.menus_list.selectedItems()
        assert items, "no list item selected"

        # Remove item from list
        menu_data = self.picker_item.get_custom_menus()
        for i in range(len(items)):
            menu_data.pop(items[i].index - i)
        self.picker_item.set_custom_menus(menu_data)

        # Update display
        self._populate_menu_list_widget()


class SaveOverlayWidget(OverlayWidget):
    '''Save options overlay widget
    '''

    def __init__(self, parent):
        OverlayWidget.__init__(self, parent=parent)

    def setup(self):
        OverlayWidget.setup(self)

        # Add options group box
        group_box = QtWidgets.QGroupBox()
        group_box.setTitle("Save options")
        self.option_layout = QtWidgets.QVBoxLayout(group_box)
        self.layout.addWidget(group_box)

        # Add options
        self.add_node_save_options()
        self.add_file_save_options()

        # Add action buttons
        self.add_confirmation_buttons()

        # Add vertical spacer
        spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        self.data_node = None

    def add_node_save_options(self):
        '''Save data to node option
        '''
        self.node_option_cb = QtWidgets.QCheckBox()
        self.node_option_cb.setText("Save data to node")

        self.option_layout.addWidget(self.node_option_cb)

    def add_file_save_options(self):
        '''Add save to file options
        '''
        self.file_option_cb = QtWidgets.QCheckBox()
        self.file_option_cb.setText("Save data to file")

        self.option_layout.addWidget(self.file_option_cb)

        file_layout = QtWidgets.QHBoxLayout()

        self.file_path_le = QtWidgets.QLineEdit()
        file_layout.addWidget(self.file_path_le)

        file_btn = CallbackButton(callback=self.select_file_event)
        file_btn.setText("Select File")
        file_layout.addWidget(file_btn)

        self.option_layout.addLayout(file_layout)

    def add_confirmation_buttons(self):
        '''Add save confirmation buttons to overlay
        '''
        btn_layout = QtWidgets.QHBoxLayout()

        spacer = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Minimum)
        btn_layout.addItem(spacer)

        close_btn = CallbackButton(callback=self.cancel_event)
        close_btn.setText("Cancel")
        btn_layout.addWidget(close_btn)

        save_btn = CallbackButton(callback=self.save_event)
        save_btn.setText("Save")
        btn_layout.addWidget(save_btn)

        spacer = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Minimum)
        btn_layout.addItem(spacer)

        self.layout.addLayout(btn_layout)

    def show(self):
        '''Update fields for current data node on show
        '''
        self.update_fields()
        OverlayWidget.show(self)

    def update_fields(self):
        '''Update fields for current data node
        '''
        self.data_node = self.parent().get_current_data_node()

        # Update node field
        self.node_option_cb.setCheckState(QtCore.Qt.Checked)

        # Update file fields
        current_file_path = self.data_node.get_file_path()
        self.file_path_le.setText(current_file_path or '')
        if current_file_path:
            self.file_option_cb.setCheckState(QtCore.Qt.Checked)

    def select_file_event(self):
        '''Open save dialog window to select file path
        '''
        file_path = self.select_file_dialog()
        if not file_path:
            return
        self.file_path_le.setText(file_path)

    def select_file_dialog(self):
        '''Get file dialog window starting in default folder
        '''
        picker_msg = "Picker Datas (*.pkr)"
        file_path = QtWidgets.QFileDialog.getSaveFileName(self,
                                                          "Choose file",
                                                          get_module_path(),
                                                          picker_msg)

        # Filter return result (based on qt version)
        if isinstance(file_path, tuple):
            file_path = file_path[0]

        if not file_path:
            return

        return file_path

    def _get_file_path(self):
        '''Return line edit file path
        '''
        file_path = self.file_path_le.text()
        if file_path:
            return unicode(file_path)
        return None

    def save_event(self):
        '''Process save operation
        '''
        # Get DataNode
        assert self.data_node, "No data_node found/selected"

        # Get character data
        data = self.parent().get_character_data()

        # Write data to node
        self.data_node.set_data(data)
        self.data_node.write_data(to_node=self.node_option_cb.checkState(),
                                  to_file=self.file_option_cb.checkState(),
                                  file_path=self._get_file_path())

        # Hide overlay
        self.hide()

    def cancel_event(self):
        '''Cancel save
        '''
        self.hide()


class AboutOverlayWidget(OverlayWidget):
    def __init__(self, parent=None):
        OverlayWidget.__init__(self, parent=parent)

    def setup(self):
        OverlayWidget.setup(self)

        # Add label
        label = QtWidgets.QLabel()
        label.setText(self.get_text())
        self.layout.addWidget(label)

        # Add Close button
        btn_layout = QtWidgets.QHBoxLayout()

        spacer = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Minimum)
        btn_layout.addItem(spacer)

        close_btn = CallbackButton(callback=self.hide)
        close_btn.setText("Close")
        close_btn.setToolTip("Hide about informations")
        btn_layout.addWidget(close_btn)

        spacer = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Minimum)
        btn_layout.addItem(spacer)

        self.layout.addLayout(btn_layout)

        # Add vertical spacer
        spacer = QtWidgets.QSpacerItem(0,
                                       0,
                                       QtWidgets.QSizePolicy.Minimum,
                                       QtWidgets.QSizePolicy.Expanding)
        self.layout.addItem(spacer)

    def get_text(self):
        text = '''
        Anim_picker, {}

        Copyright (c) 2012-2013 Guillaume Barlier
        This programe is covered by the LGPLv3 or later.

        Check for updates on my website:
        https://github.com/gbarlier

        '''.format(anim_picker.__version__)

        return text


class MainDockWindow(QtWidgets.QDockWidget):
    __OBJ_NAME__ = "ctrl_picker_window"
    __TITLE__ = "Anim Picker"

    def __init__(self, parent=qt_handlers.get_maya_window(), edit=False):
        self.ready = False

        '''init pyqt4 GUI'''
        QtWidgets.QDockWidget.__init__(self, parent)

        self.parent = parent

        # Window size
        # (default size to provide a 450/700 for tab area and propoer img size)
        self.default_width = 476
        self.default_height = 837

        # Default vars
        self.childs = []
        self.status = False
        self.script_jobs = []

        __EDIT_MODE__.set_init(edit)

        # Setup ui
        self.setup()

    def setup(self):
        '''Setup interface
        '''
        # Main window setting
        self.setObjectName(self.__OBJ_NAME__)
        self.setWindowTitle(self.__TITLE__)
        self.resize(self.default_width, self.default_height)

        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea |
                             QtCore.Qt.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetFloatable |
                         QtWidgets.QDockWidget.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetClosable)

        # Add to maya window for proper behavior
        maya_window = qt_handlers.get_maya_window()
        maya_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        self.setFloating(True)

        # Add main widget and vertical layout
        self.main_widget = QtWidgets.QWidget(self)
        self.main_vertical_layout = QtWidgets.QVBoxLayout(self.main_widget)

        # Add window fields
        self.add_character_selector()
        self.add_tab_widget()
        self.add_overlays()

        # Add main widget to window
        self.setWidget(self.main_widget)

        # Creating is done (workaround for signals being fired
        # off before everything is created)
        self.ready = True

        # Add docking event signal
        # self.connect(self,
        #              QtCore.SIGNAL('topLevelChanged(bool)'),
        #              self.dock_event)

    def reset_default_size(self):
        '''Reset window size to default
        '''
        self.resize(self.default_width, self.default_height)

    def add_character_selector(self):
        '''Add Character comboBox selector
        '''
        # Create layout
        layout = QtWidgets.QHBoxLayout()
        self.main_vertical_layout.addLayout(layout)

        # Create group box
        box = QtWidgets.QGroupBox()
        box.setTitle("Character Selector")
        box.setFixedHeight(80)

        layout.addWidget(box)

        # Add layout
        box_layout = QtWidgets.QVBoxLayout(box)

        # Add combo box
        self.char_selector_cb = CallbackComboBox(
            callback=self.selector_change_event)
        box_layout.addWidget(self.char_selector_cb)

        # Init combo box data
        self.char_selector_cb.nodes = []

        # Add option buttons
        btns_layout = QtWidgets.QHBoxLayout()
        box_layout.addLayout(btns_layout)

        # Add horizont spacer
        spacer = QtWidgets.QSpacerItem(10,
                                       0,
                                       QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        btns_layout.addItem(spacer)

        # About btn
        about_btn = CallbackButton(callback=self.show_about_infos)
        about_btn.setText("?")
        about_btn.setToolTip("Show help/about informations")
        btns_layout.addWidget(about_btn)

        # Load from node
        if not __EDIT_MODE__.get():
            self.char_from_node_btn = CallbackButton(
                callback=self.load_from_sel_node)
            self.char_from_node_btn.setText("Load from selection")
            btns_layout.addWidget(self.char_from_node_btn)

        # Refresh button
        self.char_refresh_btn = CallbackButton(callback=self.refresh)
        self.char_refresh_btn.setText("Refresh")
        # self.char_refresh_btn.setFixedWidth(60)
        btns_layout.addWidget(self.char_refresh_btn)

        # Edit buttons
        self.new_char_btn = None
        self.save_char_btn = None
        if __EDIT_MODE__.get():
            # Add New  button
            self.new_char_btn = CallbackButton(callback=self.new_character)
            self.new_char_btn.setText("New")
            self.new_char_btn.setFixedWidth(40)

            btns_layout.addWidget(self.new_char_btn)

            # Add Save  button
            self.save_char_btn = CallbackButton(callback=self.save_character)
            self.save_char_btn.setText("Save")
            self.save_char_btn.setFixedWidth(40)

            btns_layout.addWidget(self.save_char_btn)

        # Create character picture widget
        self.pic_widget = SnapshotWidget()
        layout.addWidget(self.pic_widget)

    def add_tab_widget(self, name="default"):
        '''Add control display field
        '''
        self.tab_widget = ContextMenuTabWidget(self, main_window=self)
        self.main_vertical_layout.addWidget(self.tab_widget)

        # Add default first tab
        view = GraphicViewWidget(main_window=self)
        self.tab_widget.addTab(view, name)

    def add_overlays(self):
        '''Add transparent overlay widgets
        '''
        self.about_widget = AboutOverlayWidget(self)
        self.save_widget = SaveOverlayWidget(self)

    def get_picker_items(self):
        '''Return picker items for current active tab
        '''
        return self.tab_widget.get_current_picker_items()

    def get_all_picker_items(self):
        '''Return all picker items for current picker
        '''
        return self.tab_widget.get_all_picker_items()

    def closeEvent(self, *args, **kwargs):
        '''Overwriting close event to close child windows too
        '''
        # Delete script jobs
        self.kill_script_jobs()

        # Close childs
        for child in self.childs:
            try:
                child.close()
            except Exception:
                pass

        # Close ctrls options windows
        for item in self.get_all_picker_items():
            try:
                if not item.edit_window:
                    continue
                item.edit_window.close()
            except Exception:
                pass

        # Default close
        QtWidgets.QDockWidget.closeEvent(self, *args, **kwargs)

    def showEvent(self, *args, **kwargs):
        '''Default showEvent overload
        '''
        # Prevent firing this event before the window is set up
        if not self.ready:
            return

        # Default close
        QtWidgets.QDockWidget.showEvent(self, *args, **kwargs)

        # Force char load
        self.refresh()

        # Add script jobs
        self.add_script_jobs()

    def resizeEvent(self, event):
        '''Resize about overlay on resize event
        '''
        # Prevent firing this event before the window is set up
        if not self.ready:
            return

        size = self.main_widget.size()
        pos = self.main_widget.pos()

        self.about_widget.resize(size)
        self.about_widget.move(pos)

        self.save_widget.resize(size)
        self.save_widget.move(pos)

        return QtWidgets.QDockWidget.resizeEvent(self, event)

    def show_about_infos(self):
        '''Open animation picker about and help infos
        '''
        self.about_widget.show()

    # =========================================================================
    # Character selector handlers ---
    def selector_change_event(self, index):
        '''Will load data node relative to selector index
        '''
        self.load_character()

    def populate_char_selector(self):
        '''Will populate char selector combo box
        '''
        # Get char nodes
        nodes = picker_node.get_nodes()
        self.char_selector_cb.nodes = nodes

        # Empty combo box
        self.char_selector_cb.clear()

        # Populate
        for data_node in nodes:
            text = data_node.get_namespace() or data_node.name
            self.char_selector_cb.addItem(text)

        # Set elements active status
        self.set_field_status()

    def set_field_status(self):
        '''Will toggle elements active status
        '''
        # Define status from node list
        self.status = False
        if self.char_selector_cb.count():
            self.status = True

        # Set status
        self.char_selector_cb.setEnabled(self.status)
        self.tab_widget.setEnabled(self.status)
        if self.save_char_btn:
            self.save_char_btn.setEnabled(self.status)

        # Reset tabs
        if not self.status:
            self.load_default_tabs()

    def load_default_tabs(self):
        '''Will reset and load default empty tabs
        '''
        self.tab_widget.clear()
        self.tab_widget.addTab(GraphicViewWidget(main_window=self), "None")

    def refresh(self):
        '''Refresh char selector and window
        '''
        # Get current active node
        current_node = None
        data_node = self.get_current_data_node()
        if data_node and data_node.exists():
            current_node = data_node.name

        # Check/abort on possible data changes
        if __EDIT_MODE__.get() and current_node:
            if not self.check_for_data_change():
                return

        # Re-populate selector
        self.populate_char_selector()

        # Set proper index
        if current_node:
            self.make_node_active(current_node)

        # Refresh selection check
        self.selection_change_event()

        # Force view resize
        self.tab_widget.fit_contents()

        # Set focus on view
        self.tab_widget.currentWidget().setFocus()

    def load_from_sel_node(self):
        '''Will try to load character for selected node
        '''
        sel = cmds.ls(sl=True)
        if not sel:
            return
        data_node = picker_node.get_node_for_object(sel[0])
        self.make_node_active(data_node.name)

    def make_node_active(self, data_node):
        '''Will set character selector to specified data_node
        '''
        index = 0
        for i in range(len(self.char_selector_cb.nodes)):
            node = self.char_selector_cb.nodes[i]
            if not data_node == node.name or data_node == node:
                continue
            index = i
            break
        self.char_selector_cb.setCurrentIndex(index)

    def new_character(self):
        '''
        Will create a new data node, and init a new window
        (edit mode only)
        '''
        # Open input window
        name, ok = QtWidgets.QInputDialog.getText(self,
                                                  self.tr("New character"),
                                                  self.tr('Node name'),
                                                  QtWidgets.QLineEdit.Normal,
                                                  self.tr('PICKER_DATA'))
        if not (ok and name):
            return

        # Check for possible data changes/loss
        if not self.check_for_data_change():
            return

        # Create new data node
        data_node = picker_node.DataNode(name=unicode(name))
        data_node.create()
        self.refresh()
        self.make_node_active(data_node)

    # =========================================================================
    # Data ---
    def check_for_data_change(self):
        '''
        Check if data changed
        If changes are detected will ask user if he wants to proceed any
        way and loose thoses changes
        Return user answer
        '''
        # Get current data node
        data_node = self.get_current_data_node()
        if not (data_node and data_node.exists()):
            return True

        # Return true if no changes were detected
        if data_node == self.get_character_data():
            return True

        # Open question window
        msg = "Any changes will be lost, proceed any way ?"
        answer = QtWidgets.QMessageBox.question(self,
                                                "Changes detected",
                                                msg,
                                                buttons=QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Yes)
        return answer == QtWidgets.QMessageBox.Yes

    def get_current_namespace(self):
        return self.get_current_data_node().get_namespace()

    def get_current_data_node(self):
        '''Return current character data node
        '''
        # Empty list case
        if not self.char_selector_cb.count():
            return None

        # Return node from combo box index
        index = self.char_selector_cb.currentIndex()
        return self.char_selector_cb.nodes[index]

    def load_character(self):
        '''Load currently selected data node
        '''
        # Get DataNode
        data_node = self.get_current_data_node()
        if not data_node:
            return
        picker_data = data_node.get_data()

        # Load snapshot
        path = picker_data.get("snapshot", None)
        self.pic_widget.set_background(path)

        # load tabs
        tabs_data = picker_data.get("tabs", {})
        self.tab_widget.set_data(tabs_data)

        # Default tab
        if not self.tab_widget.count():
            self.tab_widget.addTab(GraphicViewWidget(main_window=self),
                                   "default")
        else:
            # Return to first tab
            self.tab_widget.setCurrentIndex(0)

        # Fit content
        self.tab_widget.fit_contents()

        # Update selection states
        self.selection_change_event()

    def save_character(self):
        '''Save data to current selected data_node
        '''
        # Get DataNode
        data_node = self.get_current_data_node()
        assert data_node, "No data_node found/selected"

        # Block save in anim mode
        if not __EDIT_MODE__.get():
            QtWidgets.QMessageBox.warning(self,
                                          "Warning",
                                          "Save is not permited in anim mode")
            return

        # Block save on referenced nodes
        if data_node.is_referenced():
            msg = "Save is not permited on referenced nodes"
            QtWidgets.QMessageBox.warning(self, "Warning", msg)
            return

        self.save_widget.show()

    def get_character_data(self):
        '''Return window data
        '''
        picker_data = {}

        # Add snapshot path data
        snapshot_data = self.pic_widget.get_data()
        if snapshot_data:
            picker_data["snapshot"] = snapshot_data

        # Add tabs data
        tabs_data = self.tab_widget.get_data()
        if tabs_data:
            picker_data["tabs"] = tabs_data

        return picker_data

    # =========================================================================
    # Script jobs handling ---
    def add_script_jobs(self):
        '''Will add maya scripts job events
        '''
        # Clear any existing scrip jobs
        self.kill_script_jobs()

        # Get current UI maya_name
        ui_id = qt_handlers.unwrap_instance(self)
        ui_name = OpenMayaUI.MQtUtil.fullName(long(ui_id))

        # Add selection change event
        job_id = cmds.scriptJob(p=ui_name,
                                cu=True,
                                kws=False,
                                e=["SelectionChanged",
                                   self.selection_change_event])
        self.script_jobs.append(job_id)

        # Add scene open event
        job_id = cmds.scriptJob(p=ui_name,
                                kws=False,
                                e=["SceneOpened",
                                   self.selection_change_event])

        self.script_jobs.append(job_id)

    def kill_script_jobs(self):
        '''Will kill any associated script job
        '''
        for job_id in self.script_jobs:
            if not cmds.scriptJob(ex=job_id):
                continue
            cmds.scriptJob(k=job_id, f=True)
        self.script_jobs = []

    def selection_change_event(self):
        '''
        Event called with a script job from maya on selection change.
        Will properly parse poly_ctrls associated node, and set border
        visible if content is selected
        '''
        # Abort in Edit mode
        if __EDIT_MODE__.get():
            return

        # Update selection data
        __SELECTION__.update()

        # Update controls for active tab
        for item in self.get_picker_items():
            item.run_selection_check()


# =============================================================================
# Load user interface function
# =============================================================================
def load(edit=False, multi=False):
    '''Load anim_picker ui window
    '''
    # Return existing window if not multi option
    # Force multi in edit mode to prevent locked window issues

    # Init UI
    dock_widget = MainDockWindow(parent=qt_handlers.get_maya_window(),
                                 edit=edit)

    # Show ui
    dock_widget.show()
    dock_widget.raise_()

    return dock_widget


# Load on exec
# if __name__ == "__main__":
#     load()
