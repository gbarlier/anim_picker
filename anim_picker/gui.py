# PyQt4 user interface for anim_picker
# Author: Guillaume Barlier
# (c) 2013

# To do:
#    -rotate shape support
#    -handle size option
#    -middle click pan support
#    -custom script on default left click mouse event instead of selecting associated controls

import os
from PyQt4 import QtCore, QtGui, QtOpenGL
import sip

import re
from math import sin, cos, pi

from maya import cmds
from maya import OpenMaya
from maya import OpenMayaUI

import node
from handlers import python_handlers
from handlers import maya_handlers

from handlers import __EDIT_MODE__
from handlers import __SELECTION__

__USE_OPENGL__ = False # seems to conflicts with maya viewports...

#===============================================================================
# Dependencies ---
#===============================================================================
def get_maya_window():
    '''Get the maya main window as a QMainWindow instance
    '''
    try:
        ptr = OpenMayaUI.MQtUtil.mainWindow()
        return sip.wrapinstance(long(ptr), QtCore.QObject)
    except:
        #    fails at import on maya launch since ui isn't up yet
        return None

def get_images_folder_path():
    '''Return path for package images folder
    '''
    # Get the path to this file
    this_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(this_path, 'images')
                            
  
#===============================================================================
# Custom Widgets ---
#===============================================================================
#class Test(QtCore.QObject):
#    def __init__(self,
#                 text,
#                 parent=None):
#        pass
#    
#class QActionWithOption(QtGui.QWidgetAction):
#    def __init__(self,
#                 text,
#                 parent=None,
#                 option_callback=None):
#        QtGui.QWidgetAction.__init__(self, parent)
#        
#        self.text = text
#        self.option_callback = option_callback
#        self.setup()
#        
#    def setup(self):
#        main_widget = QtGui.QWidget()
#        self.main_layout = QtGui.QHBoxLayout(main_widget)
#        
#        action = QtGui.QWidgetAction(main_widget)
#        action.setText(self.text)
#        
##        self.main_layout.addWidget(action.defaultWidget())
#        
#        self.setDefaultWidget(main_widget)
#        return
#        
#        # add widget
#        option_box = QtGui.QLabel(self.text)
#        self.main_layout.addWidget(option_box)
#        
#        option_box = QtGui.QLabel('tutu')
#        self.main_layout.addWidget(option_box)
#        
        
class CallbackButton(QtGui.QPushButton):
    '''Dynamic callback button
    '''
    def __init__(self, callback=None, *args, **kwargs):
        QtGui.QPushButton.__init__(self)
        self.callback   =   callback
        self.args       =   args
        self.kwargs     =   kwargs
        
        # Connect event
        self.connect(self, QtCore.SIGNAL("clicked()"), self.click_event)
        
        # Set tooltip
        if hasattr(self.callback, '__doc__') and self.callback.__doc__:
            self.setToolTip(self.callback.__doc__)
        
    def click_event(self):
        if not self.callback:
            return
        self.callback(*self.args, **self.kwargs)
        

class CallbackComboBox(QtGui.QComboBox):
    '''Dynamic combo box object
    '''
    def __init__(self, callback=None, status_tip=None, *args, **kwargs):
        QtGui.QAction.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        if status_tip:
            self.setStatusTip(status_tip)
        
        self.connect(self, QtCore.SIGNAL('currentIndexChanged(int)'), self.index_change_event)
    
    def index_change_event(self, index):
        if not self.callback:
            return
        self.callback(index=index, *self.args, **self.kwargs)
        
        
class CallBackSpinBox(QtGui.QSpinBox):
    def __init__(self,
                 callback,
                 value=0,
                 min=0,
                 max=9999,
                 *args, **kwargs):
        QtGui.QSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        # Set properties
        self.setRange(min, max)
        self.setValue(value)
        
        # Signals
        self.connect(self, QtCore.SIGNAL("valueChanged(int)"), self.valueChangedEvent)
    
    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)


class CallBackDoubleSpinBox(QtGui.QDoubleSpinBox):
    def __init__(self,
                 callback,
                 value=0,
                 min=0,
                 max=9999,
                 *args,
                 **kwargs):
        QtGui.QDoubleSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        # Set properties
        self.setRange(min, max)
        self.setValue(value)
        
        # Signals
        self.connect(self, QtCore.SIGNAL("valueChanged(double)"), self.valueChangedEvent)
    
    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)
        
class CallbackLineEdit(QtGui.QLineEdit):
    def __init__(self, callback, text=None, *args, **kwargs):
        QtGui.QLineEdit.__init__(self)
        self.callback   =   callback
        self.args = args
        self.kwargs = kwargs
        
        # Set properties
        if text:
            self.setText(text)
        
        # Signals
        self.connect(self, QtCore.SIGNAL("returnPressed()"), self.return_pressed_event)
        
    def return_pressed_event(self):
        '''Will return text on return press
        '''
        self.callback(text=self.text(), *self.args, **self.kwargs)
        
        
class CallbackListWidget(QtGui.QListWidget):
    '''Dynamic List Widget object
    '''
    def __init__(self, callback=None, *args, **kwargs):
        QtGui.QListWidget.__init__(self)
        self.callback   =   callback
        self.args       =   args
        self.kwargs     =   kwargs
        
        self.connect(self, QtCore.SIGNAL('itemDoubleClicked (QListWidgetItem *)'), self.double_click_event)
        
        # Set selection mode to multi
        self.setSelectionMode(self.ExtendedSelection)
    
    def double_click_event(self, item):
        if not self.callback:
            return
        self.callback(item=item, *self.args, **self.kwargs)
     
     
class CallbackCheckBoxWidget(QtGui.QCheckBox):
    '''Dynamic CheckBox Widget object
    '''
    def __init__(self,
                 callback=None,
                 value=False,
                 label=None,
                 *args,
                 **kwargs):
        QtGui.QCheckBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        # Set init state
        self.setCheckState(value)
        self.setText(label or '')
        
        self.connect(self, QtCore.SIGNAL("toggled(bool)"), self.toggled_event)

    def toggled_event(self, value):
        if not self.callback:
            return
        self.kwargs['value'] = value
        self.callback(*self.args, **self.kwargs) 
        

class CtrlListWidgetItem(QtGui.QListWidgetItem):
    '''
    List widget item for influence list
    will handle checks, color feedbacks and edits
    '''
    def __init__(self, index=0, text=None):
        QtGui.QListWidgetItem.__init__(self)
        
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
        QtGui.QListWidgetItem.setText(self, text)
        
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
            color.setRgb(152, 251, 152) # pale green
        
        # Does not exists case
        else:
            color.setRgb(255, 165, 0) # orange
        
        self.setTextColor(color)
 
 
class ContextMenuTabWidget(QtGui.QTabWidget):
    '''Custom tab widget with specific context menu support
    '''
    def __init__(self,
                 parent,
                 main_window=None,
                 *args, **kwargs):
        QtGui.QTabWidget.__init__(self, parent, *args, **kwargs)
        self.main_window = main_window
        
    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        # Abort out of edit mode
        if not __EDIT_MODE__.get():
            return
            
        # Init context menu
        menu = QtGui.QMenu(self)
        
        # Build context menu
        rename_action = QtGui.QAction("Rename", None)
        rename_action.triggered.connect(self.rename_event)
        menu.addAction(rename_action)
        
        add_action = QtGui.QAction("Add Tab", None)
        add_action.triggered.connect(self.add_tab_event)
        menu.addAction(add_action)
        
        remove_action = QtGui.QAction("Remove Tab", None)
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
        name, ok = QtGui.QInputDialog.getText(self,
                                              self.tr("Tab name"),
                                              self.tr('New name'),
                                              QtGui.QLineEdit.Normal,
                                              self.tr(self.tabText(index)) )
        if not (ok and name):
            return
        
        # Update influence name
        self.setTabText(index, name)
    
    def add_tab_event(self):
        '''Will open dialog to get tab name and create a new tab
        '''
        # Open input window
        name, ok = QtGui.QInputDialog.getText(self,
                                              self.tr("Create new tab"),
                                              self.tr('Tab name'),
                                              QtGui.QLineEdit.Normal,
                                              self.tr('') )
        if not (ok and name):
            return
        
        # Add tab
        self.addTab(GraphicViewWidget(), name)
        
        # Set new tab active
        self.setCurrentIndex(self.count()-1)

    def remove_tab_event(self):
        '''Will remove tab from widget
        '''
        # Get current tab index
        index = self.currentIndex()
        
        # Open confirmation
        reply = QtGui.QMessageBox.question(self, 'Delete',
                                           "Delete tab '%s'?"%self.tabText(index),
                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                           QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
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
        items = list()
        for i in range(self.count()):
            items.extend(self.widget(i).get_picker_items())
        return items
        
    def get_data(self):
        '''Will return all tabs data
        '''
        data = list()
        for i in range(self.count()):
            name = unicode(self.tabText(i))
            tab_data = self.widget(i).get_data()
            data.append([name, tab_data])
        return data
    
    def set_data(self, data):
        '''Will, set/load tabs data
        '''
        self.clear()
        for tab in data:
            view = GraphicViewWidget(namespace=self.get_namespace())
            self.addTab(view, tab[0])
            view.set_data(tab[1])
    
        
class BackgroundWidget(QtGui.QLabel):
    '''QLabel widget to support background options for tabs.
    '''
    def __init__(self,
                 parent=None):
        QtGui.QLabel.__init__(self, parent )
        
        self.setBackgroundRole(QtGui.QPalette.Base)
        self.background = None
        
    def _assert_path(self, path):
        assert os.path.exists(path), 'Could not find file%s'%path
    
    def resizeEvent(self, event):
        QtGui.QLabel.resizeEvent(self, event)
        self._set_stylesheet_background()
    
    def _set_stylesheet_background(self):
        '''
        Will set proper sylesheet based on edit status to have
        fixed size background in edit mode and stretchable in anim mode
        '''
        if not self.background:
            self.setStyleSheet("")
            return
        
        if __EDIT_MODE__.get():
            self.setStyleSheet("QLabel {background-image: url('%s'); background-repeat: no repeat;}"%self.background)
        else:
            self.setStyleSheet("QLabel {border-image: url('%s');}"%self.background)
        
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
        file_path = QtGui.QFileDialog.getOpenFileName(self,
                                                      'Choose picture',
                                                      get_images_folder_path())
        return file_path
    
    
class SnapshotWidget(BackgroundWidget):
    '''Top right character "snapshot" widget, to display character picture
    '''
    def __init__(self,
                 parent=None):
        BackgroundWidget.__init__(self, parent )
        
        self.setFixedWidth(80)
        self.setFixedHeight(80)
        
        self.set_background()
    
    def _get_default_snapshot(self, name='undefined'):
        '''Return default snapshot
        '''
        # Define image path
        folder_path = get_images_folder_path()
        image_path = os.path.join(folder_path, '%s.png'%name)
        
        # Assert path
        self._assert_path(image_path)
        
        return image_path
        
    def set_background(self, path=None):
        '''Set character snapshot picture
        '''
        if not (path and os.path.exists(path)):
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
        menu = QtGui.QMenu(self)
        
        # Add choose action
        choose_action = QtGui.QAction("Select Picture", None)
        choose_action.triggered.connect(self.select_image)
        menu.addAction(choose_action)
        
        # Add reset action
        reset_action = QtGui.QAction("Reset", None)
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
        


#===============================================================================
# New code ---
#===============================================================================

##http://www.rqna.net/qna/ihviws-pyqt-why-qglwidget-influenced-by-maya-event.html
#from OpenGL import WGL
#class OpenGlWidget(QtOpenGL.QGLWidget):
#    '''
#    Overload of QGLWidget to counter conflict with maya viewports
#    '''
#    def __init__(self, *args, **kwargs):
#        QtOpenGL.QGLWidget.__init__(self, *args, **kwargs)
#        
#        self._HDC = None
#        self._HRC = None
#        
#    def makeCurrent(self):
#        print 'make current'
#        self._HDC = WGL.wglGetCurrentDC()
#        self._HRC = WGL.wglGetCurrentContext()
#        QtOpenGL.QGLWidget.makeCurrent(self)
#        
#    def doneCurrent(self):
#        print 'done current'
#        QtOpenGL.QGLWidget.doneCurrent(self)
#        WGL.wglMakeCurrent(self._HDC, self._HRC)


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
        
    
class DataCopyDialog(QtGui.QDialog):
    '''PickerItem data copying dialog handler
    '''
    __DATA__ = dict()
    
    __STATES__ = list()
    __DO_POS__ = State(False, 'position')
    __STATES__.append(__DO_POS__)
    __DO_COLOR__ = State(True, 'color')
    __STATES__.append(__DO_COLOR__)
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
        QtGui.QDialog.__init__(self, parent)
        self.apply = False
        self.setup()
        
    def setup(self):
        '''Build/Setup the dialog window
        '''
        self.setWindowTitle('Copy/Paste')
        
        # Add layout
        self.main_layout = QtGui.QVBoxLayout(self)
        
        # Add data field options
        for state in self.__STATES__:
            cb = CallbackCheckBoxWidget(callback=self.check_box_event,
                                             value=state.get(),
                                             label=state.name.capitalize().replace('_', ' '),
                                             state_obj=state)
            self.main_layout.addWidget(cb)
        
        # Add buttons
        btn_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)
        
        ok_btn = CallbackButton(callback=self.accept_event)
        ok_btn.setText('Ok')
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = CallbackButton(callback=self.cancel_event)
        cancel_btn.setText('Cancel')
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
        assert isinstance(item, PickerItem), 'Item is not an PickerItem instance' 
        assert DataCopyDialog.__DATA__, 'No stored data to paste'
        
        # Filter data keys to copy
        keys = list()
        for state in DataCopyDialog.__STATES__:
            if not state.get():
                continue
            keys.append(state.name)
        
        # Build valid data
        data = dict()
        for key in keys:
            if not key in DataCopyDialog.__DATA__:
                continue
            data[key] = DataCopyDialog.__DATA__[key]
        
        # Get picker item data
        item.set_data(data)
    
    @staticmethod
    def get(item=None):
        '''Will get and store data for specified item
        '''
        # Sanity check
        assert isinstance(item, PickerItem), 'Item is not an PickerItem instance' 
        
        # Get picker item data
        data = item.get_data()
        
        # Store data
        DataCopyDialog.__DATA__ = data
        
        return data
    
    
class CustomMenuEditDialog(QtGui.QDialog):
    def __init__(self,
                 parent=None,
                 name=None,
                 cmd=None,
                 item=None):
        QtGui.QDialog.__init__(self, parent)
        
        self.name = name
        self.cmd = cmd
        self.picker_item = item
        
        self.apply = False
        self.setup()
    
    def get_default_script(self):
        '''
        '''
        text = '# Custom python script window\n'
        text += '# Use __CONTROLS__ in your code to get picker item associated controls\n'
        text += '# Use __NAMESPACE__ variable where proper namespace is needed\n'
        return text
        
    def setup(self):
        '''Build/Setup the dialog window
        '''
        self.setWindowTitle('Custom Menu')
        
        # Add layout
        self.main_layout = QtGui.QVBoxLayout(self)
        
        # Add name line edit
        name_layout = QtGui.QHBoxLayout(self)
        
        label = QtGui.QLabel()
        label.setText('Name')
        name_layout.addWidget(label)
        
        self.name_widget = QtGui.QLineEdit()
        if self.name:
            self.name_widget.setText(self.name)
        name_layout.addWidget(self.name_widget)
        
        self.main_layout.addLayout(name_layout)
        
        # Add cmd txt field
        self.cmd_widget = QtGui.QTextEdit()
        if self.cmd:
            self.cmd_widget.setText(self.cmd)
        else:
            default_script = self.get_default_script()
            self.cmd_widget.setText(default_script)
        self.main_layout.addWidget(self.cmd_widget)
        
        # Add buttons
        btn_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)
        
        ok_btn = CallbackButton(callback=self.accept_event)
        ok_btn.setText('Ok')
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = CallbackButton(callback=self.cancel_event)
        cancel_btn.setText('Cancel')
        btn_layout.addWidget(cancel_btn)
        
        run_btn = CallbackButton(callback=self.run_event)
        run_btn.setText('Run')
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


class SearchAndReplaceDialog(QtGui.QDialog):
    '''Search and replace dialog window
    '''
    __SEARCH_STR__ = '^L_'
    __REPLACE_STR__ = 'R_'
    
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        
        self.apply = False
        self.setup()
        
    def setup(self):
        '''Build/Setup the dialog window
        '''
        self.setWindowTitle('Search And Replace')
        
        # Add layout
        self.main_layout = QtGui.QVBoxLayout(self)
        
        # Add line edits
        self.search_widget = QtGui.QLineEdit()
        self.search_widget.setText(self.__SEARCH_STR__)
        self.main_layout.addWidget(self.search_widget)
        
        self.replace_widget = QtGui.QLineEdit()
        self.replace_widget.setText(self.__REPLACE_STR__)
        self.main_layout.addWidget(self.replace_widget)
    
        # Add buttons
        btn_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(btn_layout)
        
        ok_btn = CallbackButton(callback=self.accept_event)
        ok_btn.setText('Ok')
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = CallbackButton(callback=self.cancel_event)
        cancel_btn.setText('Cancel')
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

        
class AxedGraphicsScene(QtGui.QGraphicsScene):
    '''
    Custom QGraphicsScene with x/y axis line options for origin feedback in edition mode
    (provides a center reference to work from, view will fit what ever is the content in use mode).
    
    Had to add z_index support since there was a little z conflict when "moving" items to back/front in edit mode 
    '''
    ___DEFAULT_SIZE__ = 200
    
    def __init__(self, parent=None):
        QtGui.QGraphicsScene.__init__(self, parent=parent)
        
        self._z_index = 0
        
        self.x_axis_line = None
        self.y_axis_line = None
        
        self.add_axis_lines()
    
    def clear(self):
        '''Reset default z index on clear
        '''
        QtGui.QGraphicsScene.clear(self)
        self._z_index = 0
        
    def set_picker_items(self, items):
        '''Will set picker items
        '''
        self.clear()
        for item in items:
            QtGui.QGraphicsScene.addItem(self, item)
            self.set_z_value(item)
        self.add_axis_lines()
            
    def get_picker_items(self):
        '''Will return all scenes' picker items
        '''
        picker_items = list()
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
        QtGui.QGraphicsScene.addItem(self, item)
        self.set_z_value(item)
        self.move_axis_line_to_front()
        
    def move_axis_line_to_front(self):
        '''Move axis lines to front, to appear on top of every other scene item
        '''
        # Move to temp scene
        tmp_scene = QtGui.QGraphicsScene()
        
        if self.x_axis_line:
            tmp_scene.addItem(self.x_axis_line)
            QtGui.QGraphicsScene.addItem(self, self.x_axis_line)
            self.x_axis_line.setZValue(self._z_index+0.1)
        
        if self.y_axis_line:
            tmp_scene.addItem(self.y_axis_line)
            QtGui.QGraphicsScene.addItem(self, self.y_axis_line)
            self.y_axis_line.setZValue(self._z_index+0.2)
            
        # Clean
        tmp_scene.deleteLater()
    
    def add_axis_lines(self):
        if __EDIT_MODE__.get():
            self.add_x_axis()
            self.add_y_axis()
             
    def add_x_axis(self):
        '''Add x axis doted line item to scene
        '''
        self.x_axis_line = QtGui.QGraphicsLineItem(self.get_x_line())
        self.set_line_properties(self.x_axis_line)
        self.addItem(self.x_axis_line)
        return self.x_axis_line
    
    def add_y_axis(self):
        '''Add y axis doted line item to scene
        '''
        self.y_axis_line = QtGui.QGraphicsLineItem(self.get_y_line())
        self.set_line_properties(self.y_axis_line)
        self.addItem(self.y_axis_line)
        return self.y_axis_line
        
    def set_line_properties(self, line_item):
        '''set proper paint properties for axis line item
        '''
        pen = QtGui.QPen(QtGui.QColor(160,160,160,120),
                         1,
                         QtCore.Qt.DashLine)
        line_item.setPen(pen)
    
    def get_x_line(self):
        '''Return x axis QLineF
        '''
        line = QtCore.QLineF(-self.___DEFAULT_SIZE__, 0,
                             self.___DEFAULT_SIZE__, 0)
        return line
    
    def get_y_line(self):
        '''Return y axis QLineF
        '''
        line = QtCore.QLineF(0, -self.___DEFAULT_SIZE__,
                             0, self.___DEFAULT_SIZE__)
        return line

        
class GraphicViewWidget(QtGui.QGraphicsView):
    '''Graphic view widget that display the "polygons" picker items 
    '''
    def __init__(self,
                 namespace=None):
        QtGui.QGraphicsView.__init__(self)
        
        self.setScene(AxedGraphicsScene())
        self.scene().setSceneRect( -200,-300, 400, 600 )
        
        self.namespace = namespace
        
        # Scale view in Y for positive Y values (maya-like)
        self.scale(1, -1)
        
        # Open GL render, to check...
        if __USE_OPENGL__:
            # make that view use OpenGL
            gl_format = QtOpenGL.QGLFormat()
            gl_format.setSampleBuffers(True)
            gl_widget = QtOpenGL.QGLWidget(gl_format)
#            gl_widget = OpenGlWidget(gl_format)

#            # turn off auto swapping of the buffer
#            gl_widget.setAutoBufferSwap(False)
      
            # use the GL widget for viewing
            self.setViewport(gl_widget)
            
        self.setResizeAnchor( self.AnchorViewCenter )
    
#        # Set selection mode
#        self.setRubberBandSelectionMode(QtCore.Qt.IntersectsItemBoundingRect)
#        self.setDragMode(self.RubberBandDrag)
#        self.scene_drag_origin = QtCore.QPointF()
#        self.drag_active = False

        # Disable scroll bars 
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff);
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff);
        
        # Set background color
        brush = QtGui.QBrush(QtGui.QColor(70,70,70,255))
        self.setBackgroundBrush(brush)
        
    def mousePressEvent(self, event):
        '''Overload to clear selection on empty area
        '''
        QtGui.QGraphicsView.mousePressEvent(self, event)
        if event.buttons() == QtCore.Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            # Get current viewport transformation
            transform = self.viewportTransform()
            
            # Clear selection if no picker item below mouse
            if not self.scene().itemAt(scene_pos, transform):
                if not event.modifiers():
                    cmds.select(cl=True)
                
#            # Rubber band selection support
#            self.scene_drag_origin = self.mapToScene(event.pos())
#            self.drag_active = True            

#    def mouseReleaseEvent(self, event):
#        QtGui.QGraphicsView.mouseReleaseEvent(self, event)
#  
#        if(event.button() == QtCore.Qt.LeftButton and self.drag_active):
#            scene_drag_end = self.mapToScene(event.pos())
#            
#            sel_area = QtCore.QRectF(self.scene_drag_origin, scene_drag_end)
#            
#            transform = self.viewportTransform()
#            if not sel_area.size().isNull():
#                items = self.scene().items(sel_area,
#                                           QtCore.Qt.IntersectsItemShape,
#                                           QtCore.Qt.AscendingOrder,
#                                           deviceTransform=transform)
#                
#                picker_items = list()
#                for item in items:
#                    if not isinstance(item, PickerItem):
#                        continue
#                    picker_items.append(item)
#                    
#                print picker_items 
#  
#        self.drag_active = False
    
    def wheelEvent(self, event):
        '''Wheel event overload to add zoom support
        '''
        # Run default event
        QtGui.QGraphicsView.wheelEvent(self, event)
        
        # Define zoom factor
        factor = 1.1
        if event.delta() < 0:
            factor = 0.9
        
        # Apply zoom
        self.zoom(factor,)
#                  self.mapToScene(event.pos()))
        
    def zoom(self, factor, center=QtCore.QPointF(0,0)):
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
            return QtGui.QGraphicsView.contextMenuEvent(self, event)
        
        # Abort out of edit mode
        if not __EDIT_MODE__.get():
            return
            
        # Init context menu
        menu = QtGui.QMenu(self)
        
        # Build context menu
        add_action = QtGui.QAction("Add Item", None)
        add_action.triggered.connect(self.add_picker_item)
        menu.addAction(add_action)
        
        toggle_handles_action = QtGui.QAction("Toggle all handles", None)
        toggle_handles_action.triggered.connect(self.toggle_all_handles_event)
        menu.addAction(toggle_handles_action)
        
#        menu.addSeparator()
#        
#        background_action = QtGui.QAction("Set background image", None)
#        background_action.triggered.connect(self.set_background_event)
#        menu.addAction(background_action)
#        
#        reset_background_action = QtGui.QAction("Reset background", None)
#        reset_background_action.triggered.connect(self.set_background_event)
#        menu.addAction(reset_background_action)
#        
#        menu.addSeparator()
#        
#        toggle_mode_action = QtGui.QAction("Switch to Anim mode", None)
#        toggle_mode_action.triggered.connect(self.toggle_mode_event)
#        menu.addAction(toggle_mode_action)

        # Open context menu under mouse
        menu.exec_(self.mapToGlobal(event.pos()))
    
    def resizeEvent(self, *args, **kwargs):
        '''Overload to force scale scene content to fit view
        '''
        # Fit scene content to view
        self.fit_scene_content()
        
        # Run default resizeEvent
        return QtGui.QGraphicsView.resizeEvent(self, *args, **kwargs)
    
    def fit_scene_content(self):
        '''Will fit scene content to view, by scaling it
        '''
        margin = 5
        self.fitInView(-margin, -margin,
                       self.scene().width() +margin, self.scene().height() +margin,
                       mode=QtCore.Qt.KeepAspectRatio)
        
    def add_picker_item(self, event=None):
        '''Add new PickerItem to current view
        '''
        ctrl = PickerItem(namespace=self.namespace)
        ctrl.setParent(self)
        self.scene().addItem(ctrl)
        
        # Move ctrl
        if event:
            ctrl.setPos(event.pos())
        else:
            ctrl.setPos(0,0)

        return ctrl
            
    def toggle_all_handles_event(self, event=None):
        new_status = None
        for item in self.scene().items():
            # Skip non picker items
            if not isinstance(item, PickerItem):
                continue
            
            # Get first status
            if new_status == None:
                new_status = not item.get_edit_status()
            
            # Set item status    
            item.set_edit_status(new_status)
    
    def set_background_event(self, event=None):
        pass

    def toggle_mode_event(self, event=None):
        '''Will toggle UI edition mode
        '''
        pass
#        # Save before switching from edit to anim
#        if __EDIT_MODE__.get_main():
#            self.parentWidget().save_character()
#        
#        # Toggle and refresh
#        __EDIT_MODE__.toggle()
#        
#        # Reset size to default
#        self.parentWidget().reset_default_size()
#        self.parentWidget().refresh()
    
#    def set_background(self, index, path=None):
#        '''Set tab index widget background image
#        '''
#        # Get widget for tab index
#        widget = self.widget(index)
#        widget.set_background(path)
#        
#        # Update data
#        if not path:
#            self.get_current_data().tabs[index].background = None
#        else:
#            self.get_current_data().tabs[index].background = unicode(path)
#    
#    def set_background_event(self, event=None):
#        '''Set background image pick dialog window
#        '''
#        # Open file dialog
#        file_path = QtGui.QFileDialog.getOpenFileName(self,
#                                                      'Choose picture',
#                                                      get_images_folder_path())
#        
#        # Abort on cancel
#        if not file_path:
#            return
#        
#        # Get current index
#        index = self.currentIndex()
#        
#        # Set background
#        self.set_background(index, file_path)
#    
#    def reset_background_event(self, event=None):
#        '''Reset background to default
#        '''
#        # Get current index
#        index = self.currentIndex()
#        
#        # Set background
#        self.set_background(index, path=None)
#        
#    def get_background(self, index):
#        '''Return background for tab index
#        '''
#        # Get current index
#        index = self.currentIndex()
#        
#        # Get background
#        widget = self.widget(index)
#        return widget.background
    
    def clear(self):
        '''Clear view, by replacing scene with a new one
        '''
        old_scene = self.scene()
        self.setScene(AxedGraphicsScene())
        old_scene.deleteLater()
        
    def get_picker_items(self):
        '''Return scene picker items in proper order (back to front)
        '''
        items = list()
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
        data = list()
        for item in self.get_picker_items():
            data.append(item.get_data())
        return data
        
    def set_data(self, data):
        '''Set/load view data
        '''
        self.clear()
        for item_data in data:
            item = self.add_picker_item()
            item.set_data(item_data)
        
        
class DefaultPolygon(QtGui.QGraphicsObject):
    '''Default polygon class, with move and hover support
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(0,0,0,255)
    
    def __init__(self, parent=None):
        QtGui.QGraphicsObject.__init__(self, parent=parent)
        
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
        QtGui.QGraphicsObject.hoverEnterEvent(self, event)
        self._hovered = True
        self.update()
    
    def hoverLeaveEvent(self, event=None):
        '''Resets mouse over background color
        '''
        QtGui.QGraphicsObject.hoverLeaveEvent(self, event)
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
            # (ghost happen when the previous polygon is out of the new bounding rect when updating)
            if self.scene():
                self.scene().update()
        
        # Run default action
        return QtGui.QGraphicsObject.itemChange(self, change, value)
    
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
        
        assert isinstance(color, QtGui.QColor), 'input color"%s" is invalid'
        
        self.color = color
        self.update()
        
        return color


class PointHandle(DefaultPolygon):
    '''Handle polygon object to move picker polygon cvs
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(30,30,30,200)
    
    def __init__(self,
                 x=0,
                 y=0,
                 size=8,
                 color=None,
                 parent=None):
        
        DefaultPolygon.__init__(self, parent)
        
        # make movable
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemSendsScenePositionChanges)

        self.setPos(x, y)
        
        self.size = size
        self.set_color()
    
        # Hide by default
        self.setVisible(False)
        
    #===========================================================================
    # Default python methods
    #===========================================================================
    def _new_pos_handle_copy(self, pos):
        '''Return a new PointHandle isntance with same attributes but different position
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
    
    #===========================================================================
    # QT OVERRIDES
    #===========================================================================
    def setX(self, value=0):
        '''Override to support keyword argument for spin_box callback
        '''
        DefaultPolygon.setX(self, value)
    
    def setY(self, value=0):
        '''Override to support keyword argument for spin_box callback
        '''
        DefaultPolygon.setY(self, value)
        
    #===========================================================================
    # Graphic item methods
    #===========================================================================
    def shape(self):
        '''Return default handle square shape based on specified size
        '''
        path = QtGui.QPainterPath()
        rectangle = QtCore.QRectF(QtCore.QPointF(-self.size / 2.0, self.size / 2.0),
                                  QtCore.QPointF(self.size / 2.0, -self.size / 2.0))
#        path.addRect(rectangle)
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
        
        border_pen = QtGui.QPen(QtGui.QColor(200,200,200,255))
        painter.setPen(border_pen)
        
        # Paint Borders
        painter.drawPath(path)
        
        # if not edit_mode: return
        # Paint center cross
        cross_size = self.size/2 -2
        painter.setPen( QtGui.QColor(0,0,0,180) ) 
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
        
        
class Polygon(DefaultPolygon):
    '''
    Picker controls visual graphic object
    (inherits from QtGui.QGraphicsObject rather than QtGui.QGraphicsItem for signal support)
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(200,200,200,180)
    __DEFAULT_SELECT_COLOR__ = QtGui.QColor(0,30,0,180)
    
    def __init__(self,
                 parent=None, # QGraphicItem
                 points=list(),
                 color=None):
        
        DefaultPolygon.__init__(self, parent=parent)
        self.points = points
        self.set_color(Polygon.__DEFAULT_COLOR__)
        
        self._edit_status = False
        self.selected = False
    
    def set_edit_status(self, status=False):
        self._edit_status = status
        self.update()
    
    def shape(self):
        '''Override function to return proper "hit box", and compute shape only once.
        '''
        path = QtGui.QPainterPath()
        
        # Polygon case
        if len(self.points)>2:
            # Define polygon points for closed loop
            shp_points = list()
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
            radius = QtGui.QVector2D(self.points[0].pos()-self.points[1].pos()).length()
            
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
            color = QtGui.QColor(255,255,255, 50)
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
        painter.setPen( QtGui.QColor(0,0,0,180) ) 
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
        

class GraphicText(QtGui.QGraphicsSimpleTextItem):
    '''
    '''
    __DEFAULT_COLOR__ = QtGui.QColor(30,30,30,255)
    
    def __init__(self, parent=None, scene=None):
        QtGui.QGraphicsSimpleTextItem.__init__(self, parent, scene)
        
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
                 namespace=None):
        
        DefaultPolygon.__init__(self, parent=parent)
        self.point_count = point_count
        
        self.setPos(25,30)
        
        # Make item movable
        if __EDIT_MODE__.get():
            self.setFlag(self.ItemIsMovable)
            self.setFlag(self.ItemSendsScenePositionChanges)
        
        # Default vars
        self.namespace = namespace
        self._edit_status = False
        self.edit_window = None
        
        # Add polygon
        self.polygon = Polygon(parent=self)
        
        # Add text
        self.text = GraphicText(parent=self)
        
        # Add handles
        self.handles = list() 
        self.set_handles(self.get_default_handles())
        
        # Controls vars
        self.controls = list()
        self.custom_menus = list()
            
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
#        ## for debug only
#        # Set render quality
#        if __USE_OPENGL__:
#            painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
#        else:
#            painter.setRenderHint(QtGui.QPainter.Antialiasing)
#        
#        # Get polygon path
#        path = self.shape()
#        
#        # Set node background color
#        brush = QtGui.QBrush(QtGui.QColor(0,0,200,255))
#        
#        # Paint background
#        painter.fillPath(path, brush)
#        
#        border_pen = QtGui.QPen(QtGui.QColor(0,200,0,255))
#        painter.setPen(border_pen)
#        
#        # Paint Borders
#        painter.drawPath(path)
        
    def get_default_handles(self):
        '''
        Generate default point handles coordinate for polygon
        (on circle)
        '''
        unit_scale = 20
        handles = list()

        # Define angle step
        angle_step = pi * 2 / self.point_count
        
        # Generate point coordinates
        for i in range(0, self.point_count):
            x = sin(i * angle_step + pi/self.point_count) * unit_scale
            y = cos(i * angle_step + pi/self.point_count) * unit_scale
            handle = PointHandle(x=x, y=y, parent=self)
            handles.append(handle)
            
        # Circle case
        if len(handles) == 2:
            handles.reverse()
            handles[0] = handles[0] + (handles[1] - handles[0])/2
            
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
        new_handles = list()
        for handle in handles:
            if isinstance(handle, (list, tuple)):
                handle = PointHandle(x=handle[0], y=handle[1], parent=self)
            elif hasattr(handle, 'x') and hasattr(handle, 'y'):
                handle = PointHandle(x=handle.x(), y=handle.y(), parent=self)
            new_handles.append(handle)
            
        # Update handles list
        self.handles = new_handles
        self.polygon.points = new_handles
        
        # Set current visibility status
        for handle in self.handles:
            handle.setVisible(self.get_edit_status())
    
    #===========================================================================
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
            self.mouse_press_select_event(event)
            
        # Set focus to maya window
        maya_window = get_maya_window()
        if maya_window:
            maya_window.setFocus(True)
    
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
            modifier = 'shift'
        
        # Controls case
        if modifiers == QtCore.Qt.ControlModifier:
            modifier = 'control'
            
        # Alt case (remove)
        if modifiers == QtCore.Qt.AltModifier:
            modifier = 'alt'
        
        # Call action
        self.select_associated_controls(modifier=modifier)

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
        
#        # Force call release method
#        self.mouseReleaseEvent(event)
    
    def edit_context_menu(self, event):
        '''Context menu (right click) in edition mode
        '''
        # Init context menu
        menu = QtGui.QMenu(self.parent())
        
        # Build edit context menu
        options_action = QtGui.QAction("Options", None)
        options_action.triggered.connect(self.edit_options)
        menu.addAction(options_action)
        
        handles_action = QtGui.QAction("Toggle handles", None)
        handles_action.triggered.connect(self.toggle_edit_status)
        menu.addAction(handles_action)
        
        menu.addSeparator()
        
        # Shape options menu
        shape_menu = QtGui.QMenu(menu)
        shape_menu.setTitle('Shape')
        
        move_action = QtGui.QAction("Move to center", None)
        move_action.triggered.connect(self.move_to_center)
        shape_menu.addAction(move_action)
        
        shp_mirror_action = QtGui.QAction("Mirror shape", None)
        shp_mirror_action.triggered.connect(self.mirror_shape)
        shape_menu.addAction(shp_mirror_action)
        
        color_mirror_action = QtGui.QAction("Mirror color", None)
        color_mirror_action.triggered.connect(self.mirror_color)
        shape_menu.addAction(color_mirror_action)
        
        menu.addMenu(shape_menu)
        
        move_back_action = QtGui.QAction("Move to back", None)
        move_back_action.triggered.connect(self.move_to_back)
        menu.addAction(move_back_action)
        
        move_front_action = QtGui.QAction("Move to front", None)
        move_front_action.triggered.connect(self.move_to_front)
        menu.addAction(move_front_action)
        
        menu.addSeparator()
        
        # Copy handling
        copy_action = QtGui.QAction("Copy", None)
        copy_action.triggered.connect(self.copy_event)
        menu.addAction(copy_action)
        
        paste_action = QtGui.QAction("Paste", None)
        if DataCopyDialog.__DATA__:
            paste_action.triggered.connect(self.past_event)
        else:
            paste_action.setEnabled(False)
        menu.addAction(paste_action)
        
        paste_options_action = QtGui.QAction("Paste Options", None)
        if DataCopyDialog.__DATA__:
            paste_options_action.triggered.connect(self.past_option_event)
        else:
            paste_options_action.setEnabled(False)
        menu.addAction(paste_options_action)
        
        menu.addSeparator()
        
        # Duplicate options
        duplicate_action = QtGui.QAction("Duplicate", None)
        duplicate_action.triggered.connect(self.duplicate)
        menu.addAction(duplicate_action)
        
        mirror_dup_action = QtGui.QAction("Duplicate/mirror", None)
        mirror_dup_action.triggered.connect(self.duplicate_and_mirror)
        menu.addAction(mirror_dup_action)
        
        menu.addSeparator()
        
        # Delete
        remove_action = QtGui.QAction("Remove", None)
        remove_action.triggered.connect(self.remove)
        menu.addAction(remove_action)
        
        menu.addSeparator()
        
        # Control association
        ctrls_menu = QtGui.QMenu(menu)
        ctrls_menu.setTitle('Ctrls Association')
        
        select_action = QtGui.QAction("Select", None)
        select_action.triggered.connect(self.select_associated_controls)
        ctrls_menu.addAction(select_action)
        
        replace_action = QtGui.QAction("Replace with selection", None)
        replace_action.triggered.connect(self.replace_controls_selection)
        ctrls_menu.addAction(replace_action)
        
        menu.addMenu(ctrls_menu)
        
        # Open context menu under mouse
        offseted_pos = event.pos() + QtCore.QPointF(5,0) # offset position to prevent accidental mouse release on menu 
        scene_pos = self.mapToScene(offseted_pos)        
        view_pos = self.parent().mapFromScene(scene_pos)
        screen_pos = self.parent().mapToGlobal(view_pos)
        menu.exec_(screen_pos)
    
    def default_context_menu(self, event):
        '''Context menu (right click) out of edition mode (animation)
        '''
        # Init context menu
        menu = QtGui.QMenu(self.parent())
            
#        # Add reset action
#        reset_action = QtGui.QAction("Reset", None)
#        reset_action.triggered.connect(self.active_control.reset_to_bind_pose)
#        menu.addAction(reset_action)
                        
        # Add custom actions
        actions = self._get_custom_action_menus()
        for action in actions:
            menu.addAction(action)
        
        # Abort on empty menu
        if menu.isEmpty():
            return
        
        # Open context menu under mouse
        offseted_pos = event.pos() + QtCore.QPointF(5,0) # offset position to prevent accidental mouse release on menu 
        scene_pos = self.mapToScene(offseted_pos)        
        view_pos = self.parent().mapFromScene(scene_pos)
        screen_pos = self.parent().mapToGlobal(view_pos)
        menu.exec_(screen_pos)
    
    def get_exec_env(self):
        '''
        Will return proper environnement dictionnary for eval execs
        (Will provide related controls as __CONTROLS__ and __NAMESPACE__ variables)
        '''
        # Init env
        env  = dict()
        
        # Add controls vars
        env['__CONTROLS__'] = self.get_controls()
        env['__NAMESPACE__'] = self.get_namespace()
        
        return env
    
    def _get_custom_action_menus(self):
        # Init action list to fix loop problem where qmenu only show last action
        # when using the same variable name ...
        actions = list() 
        
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
            actions.append(QtGui.QAction(custom_data[i][0], None))
            actions[i].triggered.connect(wrapper(custom_data[i][1]))
        
        return actions
    
    #===========================================================================
    # Edit picker item options ---
    def edit_options(self):
        '''Open Edit options window
        '''
        # Delete old window 
        if self.edit_window:
            self.edit_window.close()
            self.edit_window.deleteLater()
            
        # Init new window
        self.edit_window = ItemOptionsWindow(parent=self.parentWidget(), picker_item=self)
        
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
    
    #===========================================================================
    # Properties methods ---
    def get_color(self):
        '''Get polygon color
        '''
        return self.polygon.get_color()
    
    def set_color(self, color=None):
        '''Set polygon color
        '''
        self.polygon.set_color(color)
    
    #===========================================================================
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
    
    #===========================================================================
    # Scene Placement ---
    def move_to_front(self):
        '''Move picker item to scene front
        '''
        # Get current scene
        scene = self.scene()
        
        # Move to temp scene
        tmp_scene = QtGui.QGraphicsScene()
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
        self.setPos(0,0)
        
    def remove(self):
        self.scene().removeItem(self)
        self.setParent(None)
        self.deleteLater()
    
    #===========================================================================
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
        
    #===========================================================================
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
        
    #===========================================================================
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
        nodes = list()
        for node in self.controls:
            nodes.append('%s:%s'%(namespace, node))

        return nodes
    
    def append_control(self, ctrl):
        '''Add control to list
        '''
        self.controls.append(ctrl)
    
    def remove_control(self, ctrl):
        '''Remove control from list
        '''
        if not ctrl in self.controls:
            return
        self.controls.remove(ctrl)
    
    def search_and_replace_controls(self):
        '''Will search and replace in associated controls names
        '''
        # Open Search and replace dialog window
        search, replace, ok = SearchAndReplaceDialog.get()
        if not ok:
            return
        
        # Parse controls
        node_missing = False
        controls = self.get_controls()[:]
        for i in range(len(controls)):
            controls[i] = re.sub(search, replace, controls[i])
            if not cmds.objExists(controls[i]):
                node_missing = True 
        
        # Print warning
        if node_missing:
            QtGui.QMessageBox.warning(self.parent(),
                                      "Warning",
                                      "Some target controls do not exist")
        
        # Update list
        self.set_control_list(controls)
        
    def select_associated_controls(self, modifier=None):
        '''Will select maya associated controls
        '''       
        maya_handlers.select_nodes(self.get_controls(),
                                   modifier=modifier)
    
    def replace_controls_selection(self):
        '''Will replace controls association with current selection
        '''
        self.set_control_list(list())
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
    
    #===========================================================================
    # Custom menus handling ---
    def set_custom_menus(self, menus):
        '''Set custom menu list for current poly data
        '''
        self.custom_menus = list(menus)
    
    def get_custom_menus(self):
        '''Return current menu list for current poly data
        '''
        return self.custom_menus
    
    #===========================================================================
    # Data handling ---
    def set_data(self, data):
        '''Set picker item from data dictionary
        '''
        # Set color
        if 'color' in data:
            color = QtGui.QColor(*data['color'])
            self.set_color(color)
        
        # Set position
        if 'position' in data:
            position = data.get('position', [0,0])
            self.setPos(*position)
        
        # Set handles
        if 'handles' in data:
            self.set_handles(data['handles'])
            
        # Set controls
        if 'controls' in data:
            self.set_control_list(data['controls'])
        
        # Set custom menus
        if 'menus' in data:
            self.set_custom_menus(data['menus'])
        
        # Set text
        if 'text' in data:
            self.set_text(data['text'])
            self.set_text_size(data['text_size'])
            color = QtGui.QColor(*data['text_color'])
            self.set_text_color(color)
            
    def get_data(self):
        '''Get picker item data in dictionary form
        '''
        # Init data dict
        data = dict()
        
        # Add polygon color
        data['color'] = self.get_color().getRgb()
        
        # Add position
        data['position'] = [self.x(), self.y()]
        
        # Add handles datas
        handles_data = list()
        for handle in self.handles:
            handles_data.append([handle.x(), handle.y()])
        data['handles'] = handles_data
        
        # Add controls data
        if self.get_controls():
            data['controls'] = self.get_controls(with_namespace=False)
        
        # Add custom menus data
        if self.get_custom_menus():
            data['menus'] = self.get_custom_menus()
        
        if self.get_text():
            data['text'] = self.get_text()
            data['text_size'] = self.get_text_size()
            data['text_color'] = self.get_text_color().getRgb()
            
        return data
        

class HandlesPositionWindow(QtGui.QMainWindow):
    '''Whild window to edit picker item handles local positions
    '''
    __OBJ_NAME__ = 'picker_item_handles_window'
    __TITLE__ = 'Handles positions'
    
    __DEFAULT_WIDTH__ = 250
    __DEFAULT_HEIGHT__ = 300
    
    def __init__(self,
                 parent=None,
                 picker_item=None):
        QtGui.QMainWindow.__init__(self, parent=None)
        
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
#        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
#        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
#        self.setSizePolicy(sizePolicy)
        
        # Create main widget
        self.main_widget = QtGui.QWidget(self)
        self.main_layout = QtGui.QVBoxLayout(self.main_widget)
        
        self.setCentralWidget(self.main_widget)
        
        # Add content
        self.add_position_table()
        self.add_option_buttons()
        
        # Populate table
        self.populate_table()
        
    def add_position_table(self):
        self.table = QtGui.QTableWidget(self)
        
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['X', 'Y'])
        
        self.main_layout.addWidget(self.table)
    
    def add_option_buttons(self):
        '''Add window option buttons
        '''
        # Refresh button
        self.refresh_button = CallbackButton(callback=self.refresh_event)
        self.refresh_button.setText('Refresh')
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
            
    
class ItemOptionsWindow(QtGui.QMainWindow):
    '''Child window to edit shape options
    '''
    __OBJ_NAME__ = 'ctrl_picker_edit_window'
    __TITLE__ = 'Picker Item Options'
    
    #-----------------------------------------------------------------------------------------------
    #    constructor
    def __init__(self, parent=None, picker_item=None):
        QtGui.QMainWindow.__init__(self, parent=None)
        
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
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        
        # Create main widget
        self.main_widget = QtGui.QWidget(self)
        self.main_layout = QtGui.QHBoxLayout(self.main_widget)
        
        self.left_layout = QtGui.QVBoxLayout()
        self.main_layout.addLayout(self.left_layout)
        
        self.right_layout = QtGui.QHBoxLayout()
        self.main_layout.addLayout(self.right_layout)
        
        self.setCentralWidget(self.main_widget)
        
        # Add content
        self.add_main_options()
        self.add_position_options()
        self.add_color_options()
        self.add_scale_options()
        self.add_text_options()
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
            self.handles_window.close() 

        QtGui.QMainWindow.closeEvent(self, *args, **kwargs)
        
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
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Main Properties')
        
        # Add layout
        layout = QtGui.QVBoxLayout(group_box)
        
        # Add edit check box
        self.handles_cb = CallbackCheckBoxWidget(callback=self.handles_cb_event)
        self.handles_cb.setText('Show handles ')
        
        layout.addWidget(self.handles_cb)
        
        # Add point count spin box
        spin_layout = QtGui.QHBoxLayout()
        
        spin_label = QtGui.QLabel()
        spin_label.setText('Vtx Count')
        spin_layout.addWidget(spin_label)
        
        self.count_sb = CallBackSpinBox(callback=self.picker_item.edit_point_count,
                                        value=self.picker_item.point_count)
        self.count_sb.setMinimum(2)
        spin_layout.addWidget(self.count_sb)
        
        layout.addLayout(spin_layout)
        
        # Add handles position button
        handles_button = CallbackButton(callback=self.edit_handles_position_event)
        handles_button.setText('Handles Positions')
        layout.addWidget(handles_button)
        
        # Add to main layout
        self.left_layout.addWidget(group_box)

    def add_position_options(self):
        '''Add position field for precise control positioning
        '''
        # Create group box
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Position')
        
        # Add layout
        layout = QtGui.QVBoxLayout(group_box)
        
        # Get bary-center
        position = self.picker_item.pos()
        
        # Add X position spin box
        spin_layout = QtGui.QHBoxLayout()
        
        spin_label = QtGui.QLabel()
        spin_label.setText('X')
        spin_layout.addWidget(spin_label)
        
        self.pos_x_sb = CallBackDoubleSpinBox(callback=self.edit_position_event,
                                              value=position.x(),
                                              min=-9999)
        spin_layout.addWidget(self.pos_x_sb)
        
        layout.addLayout(spin_layout)
        
        # Add Y position spin box
        spin_layout = QtGui.QHBoxLayout()
        
        label = QtGui.QLabel()
        label.setText('Y')
        spin_layout.addWidget(label)
        
        self.pos_y_sb = CallBackDoubleSpinBox(callback=self.edit_position_event,
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
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Color options')
        
        # Add layout
        layout = QtGui.QHBoxLayout(group_box)
        
        # Add color button
        self.color_button = CallbackButton(callback=self.change_color_event)
        
        layout.addWidget(self.color_button)
        
        # Add alpha spin box
        layout.addStretch()
        
        label = QtGui.QLabel()
        label.setText('Alpha')
        layout.addWidget(label)
        
        self.alpha_sb = CallBackSpinBox(callback=self.change_color_alpha_event,
                                         value=self.picker_item.get_color().alpha(),
                                         max=255)
        layout.addWidget(self.alpha_sb)
        
        # Add to main layout
        self.left_layout.addWidget(group_box)
    
    def add_text_options(self):
        '''Add text option fields 
        '''
        # Create group box
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Text options')
        
        # Add layout
        layout = QtGui.QVBoxLayout(group_box)
        
        # Add Caption text field
        self.text_field = CallbackLineEdit(self.set_text_event)
        layout.addWidget(self.text_field)
        
        # Add size factor spin box
        spin_layout = QtGui.QHBoxLayout()
        
        spin_label = QtGui.QLabel()
        spin_label.setText('Size factor')
        spin_layout.addWidget(spin_label)
        
        value_sb = CallBackDoubleSpinBox(callback=self.edit_text_size_event,
                                         value=self.picker_item.get_text_size())
        spin_layout.addWidget(value_sb)
        
        layout.addLayout(spin_layout)
        
        # Add color layout
        color_layout = QtGui.QHBoxLayout(group_box)
        
        # Add color button
        self.text_color_button = CallbackButton(callback=self.change_text_color_event)
        
        color_layout.addWidget(self.text_color_button)
        
        # Add alpha spin box
        color_layout.addStretch()
        
        label = QtGui.QLabel()
        label.setText('Alpha')
        color_layout.addWidget(label)
        
        self.text_alpha_sb = CallBackSpinBox(callback=self.change_text_alpha_event,
                                         value=self.picker_item.get_text_color().alpha(),
                                         max=255)
        color_layout.addWidget(self.text_alpha_sb)

        # Add color layout to group box layout
        layout.addLayout(color_layout)
        
        # Add to main layout
        self.left_layout.addWidget(group_box)
#        
    def add_scale_options(self):
        '''Add scale group box options
        '''
        # Create group box
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Scale')
        
        # Add layout
        layout = QtGui.QVBoxLayout(group_box)
        
        # Add edit check box
        self.worldspace_box = QtGui.QCheckBox()
        self.worldspace_box.setText('World space')
        
        layout.addWidget(self.worldspace_box)
        
        # Add alpha spin box
        spin_layout = QtGui.QHBoxLayout()
        layout.addLayout(spin_layout)
        
        label = QtGui.QLabel()
        label.setText('Factor')
        spin_layout.addWidget(label)
        
        self.scale_sb = QtGui.QDoubleSpinBox()
        self.scale_sb.setValue(1.1)
        self.scale_sb.setSingleStep(0.05)
        spin_layout.addWidget(self.scale_sb)
        
        # Add scale buttons
        btn_layout = QtGui.QHBoxLayout()
        layout.addLayout(btn_layout)
        
        btn = CallbackButton(callback=self.scale_event, x=True)
        btn.setText('X')
        btn_layout.addWidget(btn)
        
        btn = CallbackButton(callback=self.scale_event, y=True)
        btn.setText('Y')
        btn_layout.addWidget(btn)
        
        btn = CallbackButton(callback=self.scale_event, x=True, y=True)
        btn.setText('XY')
        btn_layout.addWidget(btn)
        
        # Add to main left layout
        self.left_layout.addWidget(group_box)
        
    def add_target_control_field(self):
        '''Add target control association group box
        '''
        # Create group box
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Control Association')
        
        # Add layout
        layout = QtGui.QVBoxLayout(group_box)
        
        # Init list object
        self.control_list = CallbackListWidget(callback=self.edit_ctrl_name_event)
        self.control_list.setToolTip('Associated controls/objects that will be selected when clicking picker item')
        layout.addWidget(self.control_list)
        
        # Add buttons
        btn_layout1 = QtGui.QHBoxLayout()
        layout.addLayout(btn_layout1)
        
        btn = CallbackButton(callback=self.add_selected_controls_event)
        btn.setText('Add Selection')
        btn.setMinimumWidth(75)
        btn_layout1.addWidget(btn)
        
        btn = CallbackButton(callback=self.remove_controls_event)
        btn.setText('Remove')
        btn.setMinimumWidth(75)
        btn_layout1.addWidget(btn)
        
        self.right_layout.addWidget(group_box)
    
    def add_custom_menus_field(self):
        '''Add custom menu management groupe box
        '''
        # Create group box
        group_box = QtGui.QGroupBox()
        group_box.setTitle('Custom Menus')
        
        # Add layout
        layout = QtGui.QVBoxLayout(group_box)
        
        # Init list object
        self.menus_list = CallbackListWidget(callback=self.edit_menu_event)
        self.menus_list.setToolTip('Custom action menus that will be accessible through right clicking the picker item in animation mode')
        layout.addWidget(self.menus_list)
        
        # Add buttons
        btn_layout1 = QtGui.QHBoxLayout()
        layout.addLayout(btn_layout1)
        
        btn = CallbackButton(callback=self.new_menu_event)
        btn.setText('New')
        btn.setMinimumWidth(60)
        btn_layout1.addWidget(btn)
        
        btn = CallbackButton(callback=self.remove_menus_event)
        btn.setText('Remove')
        btn.setMinimumWidth(60)
        btn_layout1.addWidget(btn)
        
        self.right_layout.addWidget(group_box)
        
    #===========================================================================
    # Events    
    def handles_cb_event(self, value=False):
        '''Toggle edit mode for shape
        '''
        self.picker_item.set_edit_status(value)
    
    def edit_handles_position_event(self):
        
        # Delete old window 
        if self.handles_window:
            self.handles_window.close()
            self.handles_window.deleteLater()
            
        # Init new window
        self.handles_window = HandlesPositionWindow(parent=self,
                                                    picker_item=self.picker_item)
        
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
        
        self.picker_item.setPos(QtCore.QPointF(x,y))

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
        color = QtGui.QColorDialog.getColor(initial=self.picker_item.get_color(),
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
        '''Will scale polygon on specified axis based on scale factor value from spin box
        '''
        # Get scale factor value
        scale_factor = self.scale_sb.value()
        
        # Build kwargs
        kwargs = {'x':1.0, 'y':1.0}
        if x:
            kwargs['x'] = scale_factor
        if y:
            kwargs['y'] = scale_factor
        
        # Check space
        if self.worldspace_box.isChecked():
            kwargs['world'] = True
            
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
        color = QtGui.QColorDialog.getColor(initial=self.picker_item.get_text_color(),
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
        
    #===========================================================================
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
            
        if controls:
            self.control_list.setCurrentRow(0)
    
    def edit_ctrl_name_event(self, item=None):
        '''Double click event on associated ctrls list
        '''
        if not item:
            return
        
        # Open input window
        name, ok = QtGui.QInputDialog.getText(self,
                                              self.tr("Ctrl name"),
                                              self.tr('New name'),
                                              QtGui.QLineEdit.Normal,
                                              self.tr(item.text()))
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
        assert items, 'no list item selected'
        
        # Remove item from list
        for item in items:
            self.picker_item.remove_control(item.node())
            
        # Update display
        self._populate_ctrl_list_widget()
              
    def get_controls_from_list(self):
        '''Return the controls from list widget
        '''
        ctrls = list()
        for i in range(self.control_list.count()):
            item = self.control_list.item(i)
            ctrls.append(item.node()) 
        return ctrls
        
    def update_shape_controls_list(self):
        '''Update shape stored control list
        '''        
        ctrls = self.get_controls_from_list()
        self.picker_item.set_control_list(ctrls)

    #===========================================================================
    # Menus management
    def _add_menu_item(self, text=None):
        '''Add a menu item to menu list widget
        '''
        item = QtGui.QListWidgetItem()
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
        if index> len(menu_data)-1:
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
        assert items, 'no list item selected'
        
        # Remove item from list
        menu_data = self.picker_item.get_custom_menus()
        for i in range(len(items)):
            menu_data.pop(items[i].index -i)
        self.picker_item.set_custom_menus(menu_data)
        
        # Update display
        self._populate_menu_list_widget()
        
    
class MainDockWindow(QtGui.QDockWidget):
    __OBJ_NAME__ = 'ctrl_picker_window'
    __TITLE__ = 'Ctrl Picker'
    
    def __init__(self,
                 parent=get_maya_window(),
                 edit=False ):
        '''init pyqt4 GUI'''
        QtGui.QDockWidget.__init__(self, parent)
        
        self.parent =   parent
                
        # Window size
        #(default size to provide a 450/700 for tab area and propoer image size)
        self.default_width = 476
        self.default_height = 837
        
        # Default vars
        self.childs = list()
        self.status = False
        self.script_jobs = list()
        
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
        
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea|QtCore.Qt.RightDockWidgetArea)
        self.setFeatures(QtGui.QDockWidget.DockWidgetFloatable|QtGui.QDockWidget.DockWidgetMovable|QtGui.QDockWidget.DockWidgetClosable)
        
        # Add to maya window for proper behavior
        maya_window = get_maya_window()
        maya_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, self)
        self.setFloating(True)
        
        # Add main widget and vertical layout
        self.main_widget = QtGui.QWidget(self)
        self.main_vertical_layout = QtGui.QVBoxLayout(self.main_widget)
        
        # Add window fields
        self.add_character_selector()
        self.add_tab_widget()

        # Add main widget to window
        self.setWidget(self.main_widget)
        
#        # Add docking event signal
#        self.connect(self,
#                     QtCore.SIGNAL('topLevelChanged(bool)'),
#                     self.dock_event)
        
    def reset_default_size(self):
        '''Reset window size to default
        '''
        self.resize(self.default_width, self.default_height)

    def add_character_selector(self):
        '''Add Character comboBox selector
        '''
        # Create layout
        layout = QtGui.QHBoxLayout()
        self.main_vertical_layout.addLayout(layout)
        
        # Create group box
        box = QtGui.QGroupBox()
        box.setTitle('Character Selector')
        box.setFixedHeight(80)
        
        layout.addWidget(box)
        
        # Add layout
        box_layout = QtGui.QVBoxLayout(box)
        
        # Add combo box
        self.char_selector_cb = CallbackComboBox(callback=self.selector_change_event)
        box_layout.addWidget(self.char_selector_cb)
        
        # Init combo box data
        self.char_selector_cb.nodes = list()
        
        # Add option buttons
        btns_layout = QtGui.QHBoxLayout(box)
        box_layout.addLayout(btns_layout)
        
        # Add horizont spacer
        spacer = QtGui.QSpacerItem(10,0, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        btns_layout.addItem(spacer)
        
        # Load from node
        if not __EDIT_MODE__.get():
            self.char_from_node_btn = CallbackButton(callback=self.load_from_sel_node)
            self.char_from_node_btn.setText('Load from selection')
#            self.char_from_node_btn.setFixedWidth(60)
            btns_layout.addWidget(self.char_from_node_btn)
        
        # Refresh button
        self.char_refresh_btn = CallbackButton(callback=self.refresh)
        self.char_refresh_btn.setText('Refresh')
#        self.char_refresh_btn.setFixedWidth(60)
        btns_layout.addWidget(self.char_refresh_btn)
        
        # Edit buttons
        self.new_char_btn = None
        self.save_char_btn = None
        if __EDIT_MODE__.get():
            # Add New  button
            self.new_char_btn = CallbackButton(callback=self.new_character)
            self.new_char_btn.setText('New')
            self.new_char_btn.setFixedWidth(40)
        
            btns_layout.addWidget(self.new_char_btn)
            
            # Add Save  button
            self.save_char_btn = CallbackButton(callback=self.save_character)
            self.save_char_btn.setText('Save')
            self.save_char_btn.setFixedWidth(40)
        
            btns_layout.addWidget(self.save_char_btn)
            
        # Create character picture widget
        self.pic_widget = SnapshotWidget()
        layout.addWidget(self.pic_widget)
        
    def add_tab_widget(self, name = 'default'):
        '''Add control display field
        '''
        self.tab_widget = ContextMenuTabWidget(self, main_window=self)
        self.main_vertical_layout.addWidget(self.tab_widget)
        
        # Add default first tab
        view = GraphicViewWidget()
        self.tab_widget.addTab(view, name)
    
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
            child.close()
        
        # Close ctrls options windows
        for item in self.get_all_picker_items():
            if not item.edit_window:
                continue
            item.edit_window.close()
        
        # Default close    
        QtGui.QDockWidget.closeEvent(self, *args, **kwargs)
    
    def showEvent(self,  *args, **kwargs):
        '''Default showEvent overload
        '''
        # Default close    
        QtGui.QDockWidget.showEvent(self, *args, **kwargs)
        
        # Force char load
        self.refresh()
        
        # Add script jobs
        self.add_script_jobs()

    #===========================================================================
    # Character selector handlers ---
    def selector_change_event(self, index):
        '''Will load data node relative to selector index
        '''
        self.load_character()
        
    def populate_char_selector(self):
        '''Will populate char selector combo box
        '''
        # Get char nodes
        nodes = node.get_nodes()
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
        self.tab_widget.addTab(GraphicViewWidget(), 'None')
    
    def refresh(self):
        '''Refresh char selector and window
        '''
        # Get current active node
        current_node = None
        data_node = self.get_current_data_node()
        if data_node and data_node.exists():
            current_node = data_node.name
        
        # Save current character in edit mode
        if __EDIT_MODE__.get() and current_node:
            self.save_character()
            
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
        self.tab_widget.currentWidget().setFocus(True)
    
    def load_from_sel_node(self):
        '''Will try to load character for selected node
        '''
        sel = cmds.ls(sl=True)
        if not sel:
            return
        data_node = node.get_node_for_object(sel[0])
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
        name, ok = QtGui.QInputDialog.getText(self,
                                              self.tr("New character"),
                                              self.tr('Node name'),
                                              QtGui.QLineEdit.Normal,
                                              self.tr('PICKER_DATA') )
        if not (ok and name):
            return
        
        # Save current character
        if self.get_current_data_node():
            self.save_character()
        
        # Create new data node
        data_node = node.DataNode(name=unicode(name))
        data_node.create()
        self.refresh()
        self.make_node_active(data_node)
    
    #===========================================================================
    # Data ---
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
        path = picker_data.get('snapshot', None)
        self.pic_widget.set_background(path)
        
        # load tabs
        tabs_data = picker_data.get('tabs', dict())
        self.tab_widget.set_data(tabs_data)
        
        # Default tab
        if not self.tab_widget.count():
            self.tab_widget.addTab(GraphicViewWidget(), 'default')
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
        assert data_node, 'No data_node found/selected'
        
        # Block save in anim mode
        if not __EDIT_MODE__.get():
            QtGui.QMessageBox.warning(self,
                                      "Warning",
                                      "Save is not permited in anim mode")
            return
        
        # Write data to node
        data_node.set_data(self.get_character_data())
        data_node.write_data()
    
    def get_character_data(self):
        '''Return window data
        '''
        picker_data = dict()
        
        # Add snapshot path data
        snapshot_data = self.pic_widget.get_data()
        if snapshot_data:
            picker_data['snapshot'] = snapshot_data
        
        # Add tabs data
        tabs_data = self.tab_widget.get_data()
        if tabs_data:
            picker_data['tabs'] = tabs_data
    
        return picker_data
    
    #===========================================================================
    # Script jobs handling ---
    def add_script_jobs(self):
        '''Will add maya scripts job events
        '''
        # Clear any existing scrip jobs
        self.kill_script_jobs()
        
        # Get current UI maya_name
        ui_id = sip.unwrapinstance(self)
        ui_name = OpenMayaUI.MQtUtil.fullName( long(ui_id) )
        
        # Add selection change event
        job_id = cmds.scriptJob(p=ui_name, cu=True, kws=False, e=['SelectionChanged', self.selection_change_event])
        self.script_jobs.append(job_id)
        
        # Add scene open event
        job_id = cmds.scriptJob(p=ui_name, kws=False, e=['SceneOpened', self.selection_change_event])
        self.script_jobs.append(job_id)
    
    def kill_script_jobs(self):
        '''Will kill any associated script job
        '''
        for job_id in self.script_jobs:
            if not cmds.scriptJob(ex=job_id):
                continue
            cmds.scriptJob(k=job_id, f=True)
        self.script_jobs = list()
        
    def selection_change_event(self):
        '''
        Event called with a script job from maya on selection change.
        Will properly parse poly_ctrls associated node, and set border visible if content is selected
        '''
        # Abort in Edit mode
        if __EDIT_MODE__.get():
            return
        
        # Update selection data
        __SELECTION__.update()
        
        # Update controls for active tab
        for item in self.get_picker_items():
            item.run_selection_check()
            
        
#===============================================================================
# Load user interface function
#===============================================================================
def load(edit=False):
    '''Load ui for gb_skin_weights scripts
    '''
    # Check if window already exists
#    dock_pt = OpenMayaUI.MQtUtil.findControl(MainDockWindow.__OBJ_NAME__)
#    if dock_pt:
#        # Get dock qt instance
#        dock_widget = sip.wrapinstance(long(dock_pt), QtCore.QObject)
#        dock_widget.show()
#        dock_widget.raise_()
#        
#        # Reload container selector
##        dock_widget.refresh()
#        
#        return dock_widget
    
    # Init UI
    dock_widget = MainDockWindow(parent=get_maya_window(),
                                 edit=edit)
    
    # Show ui
    dock_widget.show()
    dock_widget.raise_()
    
    return dock_widget


# Load on exec
if __name__ == "__main__":
    load()
    