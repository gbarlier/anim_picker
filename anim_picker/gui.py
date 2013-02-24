# PyQt4 user interface for ctrl_picker
# Author: Guillaume Barlier

import sys
import os
import math
from PyQt4 import QtCore, QtGui, QtOpenGL
import sip

import re
from math import sin, cos, pi

from maya import cmds
from maya import OpenMaya
from maya import OpenMayaUI

import data
import node
from handlers import python_handlers
from handlers import maya_handlers

import handlers
from anim_picker.handlers import __EDIT_MODE__
from anim_picker.handlers import __SELECTION__

__USE_OPENGL__ = False # seems to conflicts with maya viewports...

#===============================================================================
# Dependencies
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
                            
def to_qpoint_float(value):
    # List case
    if type(value) in [list, tuple]:
        results = list()
        for arg in value:
            results.append(to_qpoint_float(arg))
        return results
    
    # Dictionary case
    elif type(value) == dict:
        results = dict()
        for key in value:
            results[key] = to_qpoint_float(value[key])
        return results
    
    # QPoint case:
    elif isinstance(value, QtCore.QPoint):
        return QtCore.QPointF(value)
    
    # Other
    return value


class QPointToQPointF(object): # must inherit from "object" to run __get_ !
    '''
    Will decorate function or method and convert any QPoint input to QPointsF
    '''
    def __init__(self, decorated):
        self.decorated = decorated
        
        # update decorator doc with decorated doc
        self.__doc__ = decorated.__doc__
    
    def __get__(self, obj, obj_type=None):
        return self.__class__(self.decorated.__get__(obj, obj_type))
    
    def __call__(self, *args, **kwargs):
        try:
            args = to_qpoint_float(args)
            kwargs = to_qpoint_float(kwargs)
            return self.decorated(*args, **kwargs)
        except:
            raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]

    
#===============================================================================
# Custom Widgets ---
#===============================================================================
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
    def __init__(self, callback, value=0, *args, **kwargs):
        QtGui.QSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        # Set properties
        self.setMaximum(999)
        self.setValue(value)
        
        # Signals
        self.connect(self, QtCore.SIGNAL("valueChanged(int)"), self.valueChangedEvent)
    
    def valueChangedEvent(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs)


class CallBackDoubleSpinBox(QtGui.QDoubleSpinBox):
    def __init__(self, callback, value=0, *args, **kwargs):
        QtGui.QDoubleSpinBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        # Set properties
        self.setMaximum(999)
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
    '''Dynamic List Widget object
    '''
    def __init__(self, callback=None, *args, **kwargs):
        QtGui.QCheckBox.__init__(self)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        self.connect(self, QtCore.SIGNAL("toggled(bool)"), self.toggled_event)

    def toggled_event(self, value):
        if not self.callback:
            return
        self.callback(value=value, *self.args, **self.kwargs) 
        

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
            color.setRgb(152, 251, 152) # palegreen
        
        # Does not exists case
        else:
            color.setRgb(255, 165, 0) # orange
        
        self.setTextColor(color)
 
 
class ContextMenuTabWidget(QtGui.QTabWidget):
    '''Custom tab widget with specific context menu support
    '''
    __EDIT_MODE__ = handlers.__EDIT_MODE__
    
    def __init__(self,
                 parent,
                 *args, **kwargs):
        QtGui.QTabWidget.__init__(self, parent, *args, **kwargs)
        
        self.get_current_data = parent.get_current_data
        
#    def mouseDoubleClickEvent(self, event):
#        '''Open tab rename on double click
#        '''
#        print '###double click event'
#        # Abort out of edit mode
#        if not __EDIT_MODE__.get():
#            return
#        
#        self.rename_event(event)
        
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
    
    def reset(self):
        # Remove all tabs
        while self.count():
            self.removeTab(0)
        
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
        
    def setTabText(self, index, name):
        '''Surcharged method to update name data on text change
        '''
        self.get_current_data().tabs[index].name = unicode(name)
        return QtGui.QTabWidget.setTabText(self, index, name)
    
    def addTab(self, widget, name, load=False):
        '''Surcharged method to add tab to data too.
        '''
        # Default TabWidget behavior
        index = QtGui.QTabWidget.addTab(self, widget, name)
        
        # Skip add to data on load
        if load:
            return index
        
        # Add tab to datas
        tab_data = data.TabData(name=unicode(name))
        self.get_current_data().tabs.append(tab_data)

        return index
    
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
        
        # Update influence name
        self.addTab(GraphicViewWidget(), name)
    
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
        
        # Remove from data
        self.get_current_data().tabs.pop(index)
        
        # Add default tab
        if not self.count():
            self.addTab(GraphicViewWidget(), 'default')
        
    def set_background(self, index, path=None):
        '''Set tab index widget background image
        '''
        # Get widget for tab index
        widget = self.widget(index)
        widget.set_background(path)
        
        # Update data
        if not path:
            self.get_current_data().tabs[index].background = None
        else:
            self.get_current_data().tabs[index].background = unicode(path)
    
    def set_background_event(self, event=None):
        '''Set background image pick dialog window
        '''
        # Open file dialog
        file_path = QtGui.QFileDialog.getOpenFileName(self,
                                                      'Choose picture',
                                                      get_images_folder_path())
        
        # Abort on cancel
        if not file_path:
            return
        
        # Get current index
        index = self.currentIndex()
        
        # Set background
        self.set_background(index, file_path)
    
    def reset_background_event(self, event=None):
        '''Reset background to default
        '''
        # Get current index
        index = self.currentIndex()
        
        # Set background
        self.set_background(index, path=None)
        
    def get_background(self, index):
        '''Return background for tab index
        '''
        # Get current index
        index = self.currentIndex()
        
        # Get background
        widget = self.widget(index)
        return widget.background
    
    def set_fixed_size(self):
        self.setMaximumWidth(450)
        self.setMinimumWidth(450)
        self.setMaximumHeight(700)
        self.setMinimumHeight(700)
        
    def set_stretchable_size(self):
        if __EDIT_MODE__.get():
            return
            
        self.setMaximumWidth(9999)
        self.setMinimumWidth(50)
        self.setMaximumHeight(9999)
        self.setMinimumHeight(70)
        
#        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        
    def paintEvent(self, event=None):
        '''Used as size constraint override based on edit status
        '''
        if __EDIT_MODE__.get():
            self.set_fixed_size()
        else:
            self.set_stretchable_size()
        
        if event:
            QtGui.QTabWidget.paintEvent(self, event)

        
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

#        # Load image
#        image = QtGui.QImage(path)
#        self.setPixmap(QtGui.QPixmap.fromImage(image))
#        self.setAlignment(QtCore.Qt.AlignTop)
#        self.setScaledContents(True)

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
    __EDIT_MODE__ = handlers.__EDIT_MODE__
    
    def __init__(self,
                 parent=None,
                 get_current_data_callback=None):
        BackgroundWidget.__init__(self, parent )
        
        self.setFixedWidth(80)
        self.setFixedHeight(80)
        
        self.get_current_data = get_current_data_callback
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
        
        # Update data
        self.get_current_data().snapshot = self.background
            
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
        
        
#class MouseEventCatcherWidget(QtGui.QWidget):
#    '''Custom widget that catch the mouse events to transfer them to the proper control 
#    '''
#    def __init__(self,
#                 parent=None,
#                 get_ctrls_callback=None,
#                 field_widget_callback=None,
#                 add_ctrl_callback=None,
#                 remove_ctrl_callback=None,
#                 set_tab_background_callback=None,
#                 reset_tab_background_callback=None,
#                 move_to_back_callback=None,
#                 *args, **kwargs):
#        '''
#        Key arguments:
#        -parent: parent for widget
#        -edit: callback function that return the current edit status of the ui
#        -ctrls: callback function that returns the controls handled by this widget
#        '''
#        QtGui.QWidget.__init__(self, parent, *args, **kwargs)
#        
#        self.field_widget = field_widget_callback
#        
#        # Default vars
#        self.active_control = None
#        
#        # Callbacks
#        self.get_ctrls = get_ctrls_callback
#        self.add_ctrl = add_ctrl_callback
#        self.remove_ctrl = remove_ctrl_callback
#        self.set_tab_background = set_tab_background_callback
#        self.reset_tab_background = reset_tab_background_callback
#        self.move_to_back = move_to_back_callback
#             
##        self.debug_overlay_background()
#        
#    def debug_overlay_background(self):
#        '''Add visible color to widget to see placement for debuging
#        '''
#        palette = QtGui.QPalette(self.palette())
#        palette.setColor(palette.Background, QtGui.QColor(20, 0, 20, 80))
#        self.setPalette(palette)        
#        self.setAutoFillBackground(True)
#    
#    def paintEvent(self, event):
#        '''Paint event that will draw the controls polygons
#        '''
#        if not __EDIT_MODE__.get():
#            return
#        
#        # Init painter
#        painter = QtGui.QPainter()
#        painter.begin(self)
#        
#        # Get widget current size
#        size = self.size()
#        
#        # Draw middle line
#        pen = QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.DashLine)
#        painter.setPen(pen)
#        painter.drawLine(size.width()/2, 0, size.width()/2, size.height())
#        
##        # Set painter property
##        painter.setRenderHint(QtGui.QPainter.Antialiasing)
##        
##        # Define border color based on selected state
##        border_color = QtGui.QColor(0, 0, 0, 255)
##        if not self.selected:
##            border_color.setAlpha(0)
##        painter.setPen(QtGui.QPen(border_color))
##        
##        # Set Polygon background color
##        painter.setBrush(QtGui.QBrush(self.data.color))
##        
##        # Get working points
##        data_points = self._get_working_points()
##        
##        # Polygon case
##        if len(data_points)>2:
##            # Define polygon points for closed loop
##            shp_points = data_points[:]
##            shp_points.append(shp_points[0])
##        
##            # Draw polygon
##            self.polygon = QtGui.QPolygonF(shp_points)
##            painter.drawPolygon(self.polygon)
##        
##        # Circle case
##        else:
##            center = data_points[0]
##            radius = QtGui.QVector2D(data_points[0]-data_points[1]).length()
##            painter.drawEllipse(center.x() - radius,
##                                     center.y() - radius,
##                                     radius * 2,
##                                     radius * 2)
##            
##        # Draw handles (after polygon to be on top)
##        self.handles = list()
##        if __EDIT_MODE__.get() and self.handles_visibility:
##            # Set handle color
##            border_pen = QtGui.QPen(QtCore.Qt.white)
##            border_pen.setWidthF(0.5)
##            painter.setPen(border_pen)
##            painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
##            
##            for i in range(len(data_points)):
##                handle = self.create_edit_handle(pos=data_points[i])
##                painter.drawRect(handle)
##                self.handles.append(handle)
#            
#        painter.end()
#        event.accept()
#        
#    def update_size(self):
#        '''Update size to match parent
#        '''
#        self.resize(self.field_widget().size())
#        
#        # Move to field position in window space
#        pos = self.field_widget().mapFrom(self.parentWidget(), QtCore.QPoint(0,0))
#        self.move(-pos)
#    
#    def showEvent(self, event):
#        '''Force correct position on show
#        '''
#        self.update_size()
#        
#    def mousePressEvent(self, event):
#        '''Event called on mouse press
#        '''
#        # Find selected control
#        ctrl = self.find_active_control(event.pos())
#        if not ctrl:
#            # Clear selection on empty zone click
#            cmds.select(cl=True)
#            return
#        
#        # Set active control
#        self.set_active_control(ctrl)
#
#        # Abort on any thing ells than left mouse button
#        if not event.button() == QtCore.Qt.LeftButton:
#            return
#        
#        # Forward event to control
#        self.active_control.mousePressEvent(event)
#    
#    def mouseMoveEvent(self, event):
#        '''Event called when mouse moves while clicking
#        '''
#        # Abort action on non edit mode
#        if not __EDIT_MODE__.get():
#            return
#        
#        # Abort if no active control
#        if not self.active_control:
#            return
#        
#        # Forward event to control
#        self.active_control.mouseMoveEvent(event)
#            
#    def mouseReleaseEvent(self, event):
#        '''Event called when mouse click is released
#        '''
#        # Forward event to control
#        if self.active_control:
#            self.active_control.mouseReleaseEvent(event)
#        
#        # Reset active control
#        self.set_active_control(None)
#        
#    def mouseDoubleClickEvent(self, event):
#        '''Event called when mouse is double clicked
#        '''
#        # Update active control
#        self.update_active_control(event.pos())        
#        
#        # Forward event to control
#        if self.active_control:
#            self.active_control.mouseDoubleClickEvent(event)
#            return
#        
#        # Open background image option window
#        elif __EDIT_MODE__.get():
#            pass
#    
#    def contextMenuEvent(self, event):
#        '''Right click menu options
#        '''        
#        # Context menu for edition mode
#        if __EDIT_MODE__.get():
#            self.edit_context_menu(event)
#        
#        # Context menu for default mode
#        else:
#            self.default_context_menu(event)  
#        
#        # Force call release method
#        self.mouseReleaseEvent(event)
#    
#    def edit_context_menu(self, event):
#        '''Context menu (right click) in edition mode
#        '''
#        # Init context menu
#        menu = QtGui.QMenu(self)
#        
#        # Poly case area
#        if self.active_control:
#            options_action = QtGui.QAction("Options", None)
#            options_action.triggered.connect(self.active_control.mouseDoubleClickEvent)
#            menu.addAction(options_action)
#            
#            handles_action = QtGui.QAction("Toggle handles", None)
#            handles_action.triggered.connect(self.active_control.toggle_handles_visility)
#            menu.addAction(handles_action)
#            
#            menu.addSeparator()
#            
#            move_action = QtGui.QAction("Move to center", None)
#            move_action.triggered.connect(self.active_control.move_to_center)
#            menu.addAction(move_action)
#            
#            shp_mirror_action = QtGui.QAction("Mirror shape", None)
#            shp_mirror_action.triggered.connect(self.active_control.mirror_shape)
#            menu.addAction(shp_mirror_action)
#            
#            color_mirror_action = QtGui.QAction("Mirror color", None)
#            color_mirror_action.triggered.connect(self.active_control.mirror_color)
#            menu.addAction(color_mirror_action)
#            
#            menu.addSeparator()
#            
#            move_back_action = QtGui.QAction("Move to back", None)
#            move_back_action.triggered.connect(self.move_to_back_event)
#            menu.addAction(move_back_action)
#            
#            menu.addSeparator()
#            
#            remove_action = QtGui.QAction("Remove", None)
#            remove_action.triggered.connect(self.remove_ctrl_event)
#            menu.addAction(remove_action)
#            
#            duplicate_action = QtGui.QAction("Duplicate", None)
#            duplicate_action.triggered.connect(self.active_control.duplicate)
#            menu.addAction(duplicate_action)
#            
#            mirror_dup_action = QtGui.QAction("Duplicate/mirror", None)
#            mirror_dup_action.triggered.connect(self.active_control.duplicate_and_mirror)
#            menu.addAction(mirror_dup_action)
#            
#        # Empty area
#        else:
#            add_action = QtGui.QAction("Add ctrl", None)
#            add_action.triggered.connect(self.add_ctrl)
#            menu.addAction(add_action)
#            
#            toggle_handles_action = QtGui.QAction("Toggle all handles", None)
#            toggle_handles_action.triggered.connect(self.toggle_all_handles)
#            menu.addAction(toggle_handles_action)
#            
#            menu.addSeparator()
#            
#            background_action = QtGui.QAction("Set background image", None)
#            background_action.triggered.connect(self.set_tab_background)
#            menu.addAction(background_action)
#            
#            rest_bkg_action = QtGui.QAction("Reset background", None)
#            rest_bkg_action.triggered.connect(self.reset_tab_background)
#            menu.addAction(rest_bkg_action)
#            
#            menu.addSeparator()
#            
#            toggle_action = QtGui.QAction("Anim mode", None)
#            toggle_action.triggered.connect(self.toggle_edit_mode)
#            menu.addAction(toggle_action)
#            
#        # Open context menu under mouse
#        if not menu.isEmpty():
#            menu.exec_(self.mapToGlobal(event.pos()))
#    
#    def default_context_menu(self, event):
#        '''Context menu (right click) out of edition mode (animation)
#        '''
#        # Init context menu
#        menu = QtGui.QMenu(self)
#            
#        # Poly case area
#        if self.active_control:
#            # Add reset action
#            reset_action = QtGui.QAction("Reset", None)
#            reset_action.triggered.connect(self.active_control.reset_to_bind_pose)
#            menu.addAction(reset_action)
#                
#            
#            # Add custom actions
#            self._add_custom_action_menus(menu)
#            
#        # Empty area
#        else:
#            if __EDIT_MODE__.get_main():
##                menu.addSeparator()
#                
#                toggle_action = QtGui.QAction("Edit mode", None)
#                toggle_action.triggered.connect(self.toggle_edit_mode)
#                menu.addAction(toggle_action)
#        
#        # Open context menu under mouse
#        if not menu.isEmpty():
#            menu.exec_(self.mapToGlobal(event.pos()))
#    
#    def _add_custom_action_menus(self, menu):
#        # Define custom exec cmd wrapper
#        def wrapper(cmd):
#            def custom_eval(*args, **kwargs):
#                python_handlers.safe_code_exec(cmd)
#            return custom_eval
#        
#        # Get active controls custom menus
#        custom_data = self.active_control.data.get_custom_menus()
#        if not custom_data:
#            return
#        
#        # Add separator
#        menu.addSeparator()
#        
#        # Init action list to fix loop problem where qmenu only show last action
#        # when using the same variable name ...
#        actions = list() 
#        
#        # Build menu
#        for i in range(len(custom_data)):
#            actions.append(QtGui.QAction(custom_data[i][0], None))
#            actions[i].triggered.connect(wrapper(custom_data[i][1]))
#            menu.addAction(actions[i])
#        
#    def move_to_back_event(self):
#        '''Move active control to back layer
#        '''
#        self.move_to_back(self.active_control)
#    
#    def remove_ctrl_event(self):
#        '''Will remove control from display and control list
#        '''
#        self.remove_ctrl(self.active_control)
#    
#    @QPointToQPointF
#    def find_active_control(self, point=QtCore.QPointF()):
#        '''Will return control under pointer
#        '''
#        ctrl = None
#        
#        # Find handle active control
#        if __EDIT_MODE__.get():
#            ctrl = self.find_handle_under_point(point)
#            
#        # Find/set active control
#        if not ctrl:
#            ctrl = (self.find_controls_under_point(point) or [None])[0]
#        
#        return ctrl
#    
#    def set_active_control(self, ctrl):
#        self.active_control = ctrl
#    
#    @QPointToQPointF
#    def update_active_control(self, point=QtCore.QPointF()):
#        ctrl = self.find_active_control(point)
#        self.set_active_control(ctrl)
#    
#    @QPointToQPointF            
#    def find_controls_under_point(self, point, first_only=True):
#        '''Will return the control polygon under cursor
#        '''
#        # Get control list
#        ctrls = self.get_ctrls()
#        
#        # Parse controls
#        results = list()
#        for ctrl in reversed(ctrls):
#            ctrl_widget = ctrl.get_widget()
#            
#            # Skip invalid controls
#            if not ctrl_widget.poly_contains(point):
#                continue
#            
#            # Add ctrl to results
#            results.append(ctrl_widget)
#            
#            # Stop at first
#            if first_only:
#                break
#        
#        return results
#    
#    @QPointToQPointF
#    def find_handle_under_point(self, point):
#        '''Will return the first ctrl whose handle is under point
#        '''
#        # Get control list
#        ctrls = self.get_ctrls()
#        
#        # Parse controls
#        for ctrl in reversed(ctrls):
#            ctrl_widget = ctrl.get_widget()
#            
#            # Skip invalid controls
#            if not ctrl_widget.handle_contains(point):
#                continue
#            
#            return ctrl_widget
#        
#    def toggle_all_handles(self):
#        '''Will toggle all handles for all polygon on/off 
#        '''
#        # Get control list
#        ctrls = self.get_ctrls()
#        if not ctrls:
#            return
#        
#        # Get state of first control
#        state = ctrls[0].get_widget().handles_visibility
#        for ctrl in ctrls:
#            ctrl_widget = ctrl.get_widget()
#            
#            if ctrl_widget.handles_visibility != state:
#                continue
#            ctrl_widget.toggle_handles_visility()
#            
#    def toggle_edit_mode(self):
#        '''Will toggle UI edition mode
#        '''
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
        
            
class PolygonShapeWidget(QtGui.QWidget):
    '''Custom control shape widget with editing options
    '''
    __EDIT_MODE__ = handlers.__EDIT_MODE__
        
    def __init__(self,
                 parent,
                 point_count=4,
                 color=QtGui.QColor(200,200,200,180),
                 set_default_color_callback=None,
                 add_ctrl_callback=None,
                 get_current_data_node_callback=None,
                 namespace=None,
                 *args, **kwargs):
        QtGui.QWidget.__init__(self, parent, *args, **kwargs)

        # Init data
        self.data = data.PolyData(widget=self)
        
        # Datas vars
        self.point_count = point_count
        self.namespace = namespace
        
        self.data.set_points(self.get_default_points())
        self.data.set_color(color)

        # Default vars
        self.handles = list()
        self.selected = False
        self.edit_window = None
        self.handles_visibility = False
        
        # Callback
        self.set_default_color = set_default_color_callback
        self.add_ctrl_callback = add_ctrl_callback
        self.get_current_data_node = get_current_data_node_callback
        
        self.show()
    
    def set_data(self, poly_data):
        assert isinstance(poly_data, data.PolyData), 'input data is not an instance of data.PolyData'
        self.data = poly_data
        poly_data.set_widget(self)
        self.update()
        
    def get_data(self):
        '''Returns polygon data
        '''
        return self.data.get_data()

    def update_size(self):
        '''Update size to match parent
        '''
        self.resize(self.parentWidget().size())
    
    def resizeEvent(self, event):
        '''Resize polygons
        '''
        # Abort resizing in edit mode
        if __EDIT_MODE__.get():
            self.scale(x_factor=1.0, y_factor=1.0, world=True)
            return
        
        # Define factors
        x_factor = 1.0*event.size().width()/event.oldSize().width()
        y_factor = 1.0*event.size().height()/event.oldSize().height()
        
        # Scale polygon 
        self.scale(x_factor, y_factor, world=True)
        
    def showEvent(self, event):
        '''Force correct position on show
        '''
        self.update_size()
        
    def toggle_handles_visility(self):
        '''Toggle handles display edit mode
        '''
        assert __EDIT_MODE__.get(), 'You must be in edit mode'
        
        if self.handles_visibility:
            self.handles_visibility = False
        else:
            self.handles_visibility = True

        # Update display
        self.update()
        
    def get_default_points(self):
        '''
        Generate default points coordinate for polygon
        (on circle)
        '''
        unit_scale = 20
        points = list()

        # Define angle step
        angle_step = pi * 2 / self.point_count
        
        # Generate point coordinates
        for i in range(0, self.point_count):
            x = sin(i * angle_step + pi/self.point_count) * unit_scale
            y = cos(i * angle_step + pi/self.point_count) * unit_scale
            points.append(QtCore.QPointF(x,y))
            
        # Circle case
        if len(points) == 2:
            points.reverse()
            points[0] = points[0] + (points[1] - points[0])/2
            
        return points
    
    def _get_working_points(self):
        '''Will return proper working points based on edit status
        '''
        data_points = self.data.anim_points
        if __EDIT_MODE__.get():
            data_points = self.data.points
        return data_points
            
    def paintEvent(self, event):
        '''Paint event that will draw the controls polygons
        '''
        # Init painter
        painter = QtGui.QPainter()
        painter.begin(self)
        
        # Set painter property
        if __USE_OPENGL__:
            painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        else:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Paint polygon
        self._paint_poly(painter)
            
        # Draw handles (after polygon to be on top)
        if __EDIT_MODE__.get() and self.handles_visibility:
            self._paint_poly_handles(painter)
        
        # Paint text
        self._paint_poly_text(painter)
        
        painter.end()
        event.accept()
    
    def _paint_poly(self, painter):
        '''Paint polygon shape
        '''
        # Define border color based on selected state
        border_color = QtGui.QColor(0, 0, 0, 255)
        if not self.selected:
            border_color.setAlpha(0)
        painter.setPen(QtGui.QPen(border_color))
        
        # Set Polygon background color
        painter.setBrush(QtGui.QBrush(self.data.color))
        
        # Get working points
        data_points = self._get_working_points()
        
        # Polygon case
        self.polygon = None
        if len(data_points)>2:
            # Define polygon points for closed loop
            shp_points = data_points[:]
            shp_points.append(shp_points[0])
        
            # Draw polygon
            self.polygon = QtGui.QPolygonF(shp_points)
            painter.drawPolygon(self.polygon)
        
        # Circle case
        else:
            center = data_points[0]
            radius = QtGui.QVector2D(data_points[0]-data_points[1]).length()
            painter.drawEllipse(center.x() - radius,
                                     center.y() - radius,
                                     radius * 2,
                                     radius * 2)
            
    def _paint_poly_handles(self, painter):
        '''Paint polygon edit handles
        '''
        self.handles = list()
        
        # Get working points
        data_points = self._get_working_points()
        
        # Set handle color
        border_pen = QtGui.QPen(QtCore.Qt.white)
        border_pen.setWidthF(0.5)
        painter.setPen(border_pen)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.black))
        
        for i in range(len(data_points)):
            handle = self.create_edit_handle(pos=data_points[i])
            painter.drawRect(handle)
            self.handles.append(handle)
            
    def _paint_poly_text(self, painter):
        '''Paint polygon text
        '''
        if not self.data.text:
            return
        
        # Get bounding box
        bound_box = self.get_bounding_box()
        
        # Define text size
        size = (bound_box.width() / 3) * self.data.text_size_factor
        
        # Set text properties
        painter.setPen(QtGui.QColor(self.data.text_color))
        painter.setFont(QtGui.QFont('Decorative', size))
        
        # Paint text
        painter.drawText(self.get_bounding_box(), QtCore.Qt.AlignCenter, self.data.text)
    
    def get_bounding_box(self):
        # Simple polygon case
        if self.polygon:
            return self.polygon.boundingRect()
        
        # Circle case
        else:
            data_points = self._get_working_points()
            
            center = data_points[0]
            radius = QtGui.QVector2D(data_points[0]-data_points[1]).length()
            
            return QtCore.QRectF(center.x() - radius,
                                 center.y() - radius,
                                 radius * 2,
                                 radius * 2)
        
    def create_edit_handle(self, pos=QtCore.QPointF()):
        '''Create the polygon "vtx" handle to edit it's shape
        '''
        return QtCore.QRectF(pos - QtCore.QPointF(3,3), QtCore.QSizeF(6, 6))
    
    def get_bary_center(self):
        '''Returns the bary-center point for the shape
        '''
        # Circle case:
        if len(self.data.points) == 2:
            return self.data.points[0]
        
        # Default poly case
        total = QtCore.QPointF()
        for point in self.data.points:
            total += point
        return total/len(self.data.points)
    
    @QPointToQPointF
    def move_to(self, point=QtCore.QPointF()):
        '''Move the polygon shape to specified point
        '''
        data_points = self._get_working_points()
        
        # Clamp point
        point = self.clamp_point_coordinates(point)
        
        # Get polygon bary-center
        bary_center = self.get_bary_center()
        
        # Move each polygon "vtx"
        for i in range(len(self.data.points)):
            offset = self.data.points[i] - bary_center
            data_points[i] = point + offset
        
        # Update option ui
        if self.edit_window:
            self.edit_window._update_position_infos()
        
        # Update painter
        self.update()
        
    def move_to_center(self, *args, **kwargs):
        '''Move polygon bary-center to center of field widget
        '''
        field_size = self.parentWidget().size()
        middle_pos = QtCore.QPointF(field_size.width(), field_size.height())/2
        self.move_to(middle_pos)
    
    def mirror_position(self):
        '''Mirror the polugon position based on fields center axis. 
        '''
        # Get middle axis X value 
        field_size = self.parentWidget().size()
        middle_axis = field_size.width()/2
        
        # Get polygon bary-center
        bary_center = self.get_bary_center()
        
        # Define position mirror
        mirror_pos = QtCore.QPointF(bary_center.x() - 2 * (bary_center.x() - middle_axis),
                                   bary_center.y())
        
        # Move to mirror position
        self.move_to(mirror_pos)
    
    @QPointToQPointF
    def clamp_point_coordinates(self, point=QtCore.QPointF()):
        '''
        '''
        # Get parent space rectangle
        widget_rect = self.frameGeometry()
        
        # Get parent boundaries
        left = widget_rect.left()
        right = widget_rect.right()
        top = widget_rect.top()
        bottom = widget_rect.bottom()
        
        # Apply clamp
        point.setX(max(left, min(point.x(), right)))
        point.setY(max(top, min(point.y(), bottom)))
        
        return point
    
    #===========================================================================
    # Checks
    @QPointToQPointF
    def poly_contains(self, point=QtCore.QPointF()):
        '''Check if associated polygon contains the point
        '''
        data_points = self._get_working_points()
        
        # Polygon case
        if len(data_points)>2:
            return self.polygon.containsPoint(point, 0)
        
        # Circle case
        center = data_points[0]
        radius = QtGui.QVector2D(data_points[0]-data_points[1]).length()
        return ((point.x()-center.x())**2 + (point.y() - center.y())**2) < radius**2
    
    @QPointToQPointF
    def handle_contains(self, point=QtCore.QPointF()):
        '''Check if the specified point is contained in a "vtx" handle
        '''
        if not self.get_point_handle(point=point) is None:
            return True
        return False
    
    @QPointToQPointF
    def get_point_handle(self, point=QtCore.QPointF()):
        '''Get "vtx" handle index for specified point
        '''
        for i in range(len(self.handles)):
            if self.handles[i].contains(point):
                return i
        return None

    #===========================================================================
    # Events
    def mousePressEvent(self, event):
        '''Event called on mouse press
        '''
        # Edit behavior event
        if __EDIT_MODE__.get():
            return self.mouse_press_edit_event(event)
    
        # Default event
        return self.mouse_press_default_event(event)
    
    def mouse_press_default_event(self, event):
        '''
        Default event on mouse press.
        Will select associated controls
        '''
        # Abort on invalid zone
        if not self.poly_contains(event.pos()):
            return
        
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
    
    def mouse_press_edit_event(self, event):
        '''Custom function used in edit mode (rigging) on mouse press event
        '''
        # Init values
        self._dragging_poly = False
        self._dragging_handle = False
        
        # Handle case
        handle_index = self.get_point_handle(point=event.pos())
        if not handle_index is None:
            self.drag_offset = self.data.points[handle_index] - to_qpoint_float(event.pos()) 
            self._handle_id = handle_index
            self._dragging_handle = True
            return
        
        # Polygon case
        if self.poly_contains(event.pos()):
            self._dragging_poly = True
            self.drag_offset = self.get_bary_center() - to_qpoint_float(event.pos())
            return
    
    def mouseMoveEvent(self, event):
        '''Event called when mouse moves while clicking
        '''
        if not __EDIT_MODE__.get():
            return
        self.mouse_move_edit_event(event)
    
    def mouse_move_edit_event(self, event):
        '''
        Custom function used in edit mode (rigging) on mouse move event
        Will either move the "vtx" handle, or the full polygon depending on context
        '''
        # Abort on non dragging event
        if not (self._dragging_poly or self._dragging_handle):
            return
        
        # Poly case
        if self._dragging_poly:
            point = self.clamp_point_coordinates(event.pos())
    
            bary_dest = point + self.drag_offset
            self.move_to(point=bary_dest)
            
        # Handle case
        if self._dragging_handle:
            point = to_qpoint_float(event.pos()) + self.drag_offset
            point = self.clamp_point_coordinates(point)
            
            self.data.points[self._handle_id] = point
            
            # Update painter
            self.update()
        
        # Update edit window
        if self.edit_window:
            self.edit_window._update_position_infos()
        
    def mouseReleaseEvent(self, event):
        '''Event called when mouse click is released
        '''
        self._dragging_poly = False
        self._dragging_handle = False
        
    def mouseDoubleClickEvent(self, event):
        '''Event called when mouse is double clicked
        '''
        if not __EDIT_MODE__.get():
            return
        
        # Init edit window 
        if not self.edit_window:
            self.edit_window = ShapeOptionsWindow(parent=self)
        
        # Show window
        self.edit_window.show()
        self.edit_window.raise_()
        
    #===========================================================================
    # Edit Options
    def edit_vtx_number(self, value=4):
        '''
        Change/edit the number of vtx for the polygon
        (that will reset the shape)
        '''
        # Update point count
        self.point_count = value
        
        # Get bary-center
        bary_center = self.get_bary_center()
        
        # Reset points
        self.data.set_points(self.get_default_points())
        
        # Move back to stored bary-center
        self.move_to(point=bary_center)
        
        # Update display
        self.update()
    
    def set_point_positions(self, positions):
        '''
        Will set point positions with input positions
        
        Arguments
        -positions (list): can be a list a QPointFs or of (x,y) value.
        '''
        # Assert list size
        self.edit_vtx_number(len(positions))
         
        # Parse points 
        for i in range(self.point_count):
            if isinstance(positions[i], QtCore.QPointF):
                self.data.points[i] = QtCore.QPointF(positions[i])
            else:
                try:
                    self.data.points[i] = QtCore.QPointF(positions[i][0], positions[i][1])
                except:
                    raise 'position %d data "%s" is invalid'%(i, positions[i])
        
        
    def set_color(self, color):
        '''Change polygon color
        '''
        self.data.color = QtGui.QColor(color)
        self.set_default_color(color)
        self.update()
    
    def get_color(self):
        return self.data.color
    
    def set_text_color(self, color):
        '''Change polygon color
        '''
        self.data.text_color = QtGui.QColor(color)
        self.update()
    
    def get_text(self):
        return self.data.text
        
    def get_text_color(self):
        return self.data.text_color
        
    def set_control_list(self, ctrls=list()):
        '''Update associated control list
        '''
        self.data.set_maya_nodes(ctrls)

    def search_replace_controls(self):
        pass
    
    def get_controls(self):
        '''Return associated controls 
        '''
        # Get namespace
        namespace = self.get_namespace()
        
        # Get nodes from data
        nodes_data = self.data.maya_nodes or list()
        
        # No namespace, return nodes
        if not namespace:
            return nodes_data
        
        # Prefix nodes with namespace
        nodes = list()
        for node in nodes_data:
            nodes.append('%s:%s'%(namespace, node))
        return nodes
    
    def append_control(self, ctrl):
        self.data.maya_nodes.append(ctrl)
    
    def remove_control(self, ctrl):
        if not ctrl in self.data.maya_nodes:
            return
        self.data.maya_nodes.remove(ctrl)
    
    def search_and_replace_controls(self):
        '''Will search and replace in maya node names
        '''
        # Open Search and replace dialog window
        search, replace, ok = SearchAndReplaceDialog.get()
        if not ok:
            return
        
        # Parse controls
        node_missing = False
        controls = self.get_controls()
        for i in range(len(controls)):
            controls[i] = re.sub(search, replace, controls[i])
            if not cmds.objExists(controls[i]):
                node_missing = True 
        
        # Print warning
        if node_missing:
            QtGui.QMessageBox.warning(self,
                                      "Warning",
                                      "Some target controls don't exists")
        
        # Update list
        self.set_control_list(controls)
        
    def mirror_shape(self, *args, **kwargs):
        '''Mirror polygon shape
        '''
        # Get polygon bary-center
        bary_center = self.get_bary_center()
        
        # Mirror each polygon "vtx"
        for i in range(len(self.data.points)):
            offset = self.data.points[i] - bary_center
            self.data.points[i] = bary_center - QtCore.QPointF(offset.x(), -offset.y())
        
        # Update painter
        self.update()
    
    def duplicate(self, *args, **kwargs):
        '''Will create a new ctrl picker and copy data over.
        '''
        # Create new poly ctrl
        ctrl = self.add_ctrl_callback()
        
        # Copy data over
        ctrl.set_point_positions(self.data.points)
        ctrl.set_color(self.data.color)
        ctrl.set_control_list(self.data.maya_nodes)
        ctrl.handles_visibility = self.handles_visibility
        
        return ctrl
    
    def duplicate_and_mirror(self, *args, **kwargs):
        '''Will duplicate then mirror shape/position based on filed center
        '''
        # Duplicate control poly
        ctrl = self.duplicate()
        
        # Mirror shape
        ctrl.mirror_shape()
        
        # Mirror position
        ctrl.mirror_position()
        
        # Mirror color
        ctrl.mirror_color()
        
        # Rename control nodes
        ctrl.search_and_replace_controls()
        
    def mirror_color(self, *args, **kwargs):
        '''Will reverse red/bleu rgb values for the poly color
        '''
        new_color = QtGui.QColor(self.data.color.blue(),
                                 self.data.color.green(),
                                 self.data.color.red(),
                                 alpha=self.data.color.alpha())
        self.set_color(new_color)
    
    def scale(self, x_factor=1.0, y_factor=1.0, world=False):
        '''Will scale shape based on axis x/y factors
        '''
        data_points = self._get_working_points()
        
        # Init transform
        factor = QtGui.QTransform().scale(x_factor, y_factor)
        
        # Process points
        for i in range(len(self.data.points)):
            # World case (from top left corner)
            if world:
                data_points[i] *= factor
            
            # Scale around bary center
            else:
                bary_center = self.get_bary_center()
                offset = data_points[i] - bary_center
                data_points[i] = bary_center + offset * factor

        self.update()    
    
    def set_text(self, text):
        '''Will set polygon text value
        '''
        self.data.set_text(text)
        self.update()
    
    def set_text_size(self, value):
        self.data.set_text_size_factor(value)
        self.update()
    
    #===========================================================================
    # Controls handling
    def get_namespace(self):
        '''Will return associated namespace
        '''
        return self.get_current_data_node().get_namespace()
    
    def select_associated_controls(self, modifier=None):
        '''Will select maya associated controls
        '''       
        maya_handlers.select_nodes(self.get_controls(),
                                   modifier=modifier)
        
    def is_selected(self):
        '''
        Will return True if the nod from maya_nodes is currently selected
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
        # Do nothing on same state
        if state == self.selected:
            return
            
        # Change state, and update
        self.selected = state
        self.update() 
        
    def run_selection_check(self):
        '''Will set selection state based on selection status
        '''
        self.set_selected_state(self.is_selected())
        
    def reset_to_bind_pose(self):
        '''Will reset associated maya node to bind pose if any is stored
        '''
        for ctrl in maya_handlers.get_flattened_nodes(self.get_controls()):
            maya_handlers.reset_node_attributes(ctrl)


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
        
        
class GraphicViewWidget(QtGui.QGraphicsView):
    '''Graphic view widget that display the "polygons" picker items 
    '''
    def __init__(self):
        QtGui.QGraphicsView.__init__(self)
        
        self.setScene(QtGui.QGraphicsScene())
        self.scene().setSceneRect( -100,-100, 200, 200 )
        
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
        
    def set_background(self):
        pass

#    def mouseMoveEvent(self, event):
#        print event.pos() # debug
#        return QtGui.QGraphicsView.mouseMoveEvent(self, event)

    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        print '### view context' 
        
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
        add_action = QtGui.QAction("Add Ctrl", None)
        add_action.triggered.connect(self.add_ctrl_event)
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
        

    def add_ctrl_event(self, event=None, load=False):
        '''Add new polygon control to current tab
        '''
        ctrl = PickerItem()
        ctrl.setParent(self)
        self.scene().addItem(ctrl)
        
        # Move ctrl
        if event:
            ctrl.setPos(event.pos())
        else:
            ctrl.setPos(0,0)
        
#        # Create new ctrl
#        ctrl = PolygonShapeWidget(self.get_active_field(),
#                                  color=self.default_color,
#                                  set_default_color_callback=self.set_default_color,
#                                  add_ctrl_callback=self.add_ctrl_event,
#                                  get_current_data_node_callback=self._get_current_data_node,)
#
#        # Do not add control to data list in load mode
#        if load:
#            return ctrl
#                   
#        
#        
#        # Get tab index
#        index = self.tab_widget.currentIndex()
#
#        # Update ctrl list
#        self.get_current_data().tabs[index].controls.append(ctrl.data)

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
        pass
    
    
class DefaultPolygon(QtGui.QGraphicsObject):
    '''Default polygon class, with move and hover support
    '''
    def __init__(self, parent=None):
        QtGui.QGraphicsObject.__init__(self, parent=parent)
        
        if parent:
            self.setParent(parent)
        
        # Hover feedback
        self.setAcceptHoverEvents(True)
        self._hovered = False
        
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
        
                
class PointHandle(DefaultPolygon):
    def __init__(self,
                 x=0,
                 y=0,
                 size=8,
                 color=QtGui.QColor(30,30,30,200),
                 parent=None):
        
        DefaultPolygon.__init__(self, parent)
        
        # make movable
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemSendsScenePositionChanges)

        self.setPos(x, y)
        
        self.size = size
        self.color = color
    
        # Hide by default
        self.setVisible(False)
        
    #===========================================================================
    # Add QPointF math support
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
    
    def _get_pos_for_input(self, input):
        if isinstance(input, PointHandle):
            return input.pos()
        return input
#        elif hasattr(other, 'pos'):
#            return other.pos()
#        elif hasattr(other, 'x') and hasattr(other, 'y'):
#            return QtCore.QPointF(other.x(), other.y())
#        elif type(input) in [float, int]:
#            return input
#        
#        raise 'invalid input "%s", does not support QPointF operations'%other
    
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
            print 'handle hovered'
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
        
    def itemChange(self, change, value):
        '''itemChange update behavior
        '''
        # Catch position update
        if change == self.ItemPositionChange:
            # Force update parent to prevent "ghosts"
            # ghosts will still happen if hadle is moved "fast"
            # (i suspecting that the ghost is out of the parent bounding rect when updating)
            self.parent().update()
        
        # Run default action
        return DefaultPolygon.itemChange(self, change, value)
    
    def mirror_x_position(self):
        '''will mirror local x position value
        '''
        self.setX(-1 * self.x())
    
    
class Polygon(DefaultPolygon):
    '''
    Picker controls visual graphic object
    (inherits from QtGui.QGraphicsObject rather than QtGui.QGraphicsItem for signal support)
    '''
    def __init__(self,
                 parent=None, # QGraphicItem
                 points=list(),
                 color=QtGui.QColor(200,200,200,180)):
        
        DefaultPolygon.__init__(self, parent=parent)
        self.points = points
        self.color = color
        
        self._edit_status = False
        
    def setup(self):
        '''Setup control 
        '''
        pass
    
    def set_edit_status(self, status=False):
        self._edit_status = status
        self.update()
          
#    def itemChange(self, change, value):
#        '''Event override to emit signal on movement
#        '''
#        if change == self.ItemPositionChange:
#            pass
#                
#        return QtCore.QVariant(value)
    
    
        
        
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
        
        # Set node background color
        if not self._hovered:
            brush = QtGui.QBrush(self.color)
        else:
            brush = QtGui.QBrush(self.color.lighter(130))
            print '### polygon hovered'
        
        # Paint background
        painter.fillPath(path, brush)
        
        # Set pen color
        border_pen = QtGui.QPen(QtGui.QColor(255,0,0,255))
#        border_pen.setWidthF(1)
        painter.setPen(border_pen)
        
        # Paint Borders
        painter.drawPath(path)
        
        if not self._edit_status:
            return
        
        # Paint center cross
        painter.setRenderHints(QtGui.QPainter.HighQualityAntialiasing, False)
        painter.setPen( QtGui.QColor(0,0,0,180) ) 
        painter.drawLine(-5, 0, 5, 0)
        painter.drawLine(0, 5, 0, -5)
             

class PickerItem(DefaultPolygon):
    def __init__(self,
                 parent=None,
                 point_count=4):
        
        DefaultPolygon.__init__(self, parent=parent)
        self.point_count = point_count
        
        self.setPos(25,30)
        
        # Make item movable
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemSendsScenePositionChanges)
        
        # Default vars
        self._edit_status = False
        self.edit_window = None
        
        # Add handles and polygon support
        self.handles = list() 
        self.polygon = Polygon(parent=self)
        self.set_handles(self.get_default_handles())
        
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
        print 'value', value
        # Update point count
        self.point_count = value
        
        # Reset points
        points = self.get_default_handles()
        self.set_points(points)
        
#        # Update display
#        self.update()
        
    def set_handles(self, handles=list()):
        '''Set polygon handles points
        '''
        # Remove existing handles
        for handle in self.handles:
            self.scene().removeItem(handle)
            
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
    
    def mouseDoubleClickEvent(self, event):
        '''Event called when mouse is double clicked
        '''
        if not __EDIT_MODE__.get():
            return
        
        self.edit_options()
        
    def contextMenuEvent(self, event):
        '''Right click menu options
        '''
        print '### picker item context'        
        # Context menu for edition mode
        if __EDIT_MODE__.get():
            self.edit_context_menu(event)
        
#        # Context menu for default mode
#        else:
#            self.default_context_menu(event)  
        
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
        
        move_action = QtGui.QAction("Move to center", None)
        move_action.triggered.connect(self.move_to_center)
        menu.addAction(move_action)
        
        shp_mirror_action = QtGui.QAction("Mirror shape", None)
        shp_mirror_action.triggered.connect(self.mirror_shape)
        menu.addAction(shp_mirror_action)
        
        color_mirror_action = QtGui.QAction("Mirror color", None)
        color_mirror_action.triggered.connect(self.mirror_color)
        menu.addAction(color_mirror_action)
        
#        menu.addSeparator()
#        
#        move_back_action = QtGui.QAction("Move to back", None)
#        move_back_action.triggered.connect(self.move_to_back_event)
#        menu.addAction(move_back_action)
#        
        menu.addSeparator()
        
        remove_action = QtGui.QAction("Remove", None)
        remove_action.triggered.connect(self.remove)
        menu.addAction(remove_action)
#        
#        duplicate_action = QtGui.QAction("Duplicate", None)
#        duplicate_action.triggered.connect(self.active_control.duplicate)
#        menu.addAction(duplicate_action)
#        
#        mirror_dup_action = QtGui.QAction("Duplicate/mirror", None)
#        mirror_dup_action.triggered.connect(self.active_control.duplicate_and_mirror)
#        menu.addAction(mirror_dup_action)
        
        # Open context menu under mouse
        offseted_pos = event.pos() + QtCore.QPointF(5,0) # offset position to prevent accidental mouse release on menu 
        scene_pos = self.mapToScene(offseted_pos)        
        view_pos = self.parent().mapFromScene(scene_pos)
        screen_pos = self.parent().mapToGlobal(view_pos)
        menu.exec_(screen_pos)
    
    def edit_options(self):
        '''Open Edit options window
        '''
        # Init edit window 
        if not self.edit_window:
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
    
    def get_color(self):
        '''Get polygon color
        '''
        return self.polygon.color
    
    def set_color(self, color=QtGui.QColor(200,200,200,180)):
        '''Set polygon color
        '''
        self.polygon.color = color
        self.update()
        
    def move_to_center(self):
        '''Move picker item to pos 0,0
        '''
        self.setPos(0,0)
        
    def remove(self):
        self.scene().removeItem(self)
        self.setParent(None)
        self.deleteLater()

    def mirror_position(self):
        '''Mirror picker position (on X axis)
        '''
        self.setX(-1 * self.pos().x())
    
    def mirror_shape(self):
        '''Will mirror polygon handles position on X axis
        '''
        for handle in self.handles:
            handle.mirror_x_position()
        self.mirror_position()
        self.mirror_color()
    
    def mirror_color(self):
        '''Will reverse red/bleu rgb values for the polygon color
        '''
        old_color = self.get_color()
        new_color = QtGui.QColor(old_color.blue(),
                                 old_color.green(),
                                 old_color.red(),
                                 alpha=old_color.alpha())
        self.set_color(new_color)
        
    def set_data(self, data):
        '''Set picker item from data dictionary
        '''
        # Set color
        if 'color' in data:
            color = QtGui.QColor(*data['color'])
            self.set_color(color)
        
        # Set position
        position = data.get('position', [0,0])
        self.setPos(*position)
        
        # Set handles
        if 'handles' in data:
            self.set_handles(data['handles'])
        
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
            handles_data.extend([handle.x(), handle.y()])
        data['handles'] = handles_data
        
        return data
        

class ItemOptionsWindow(QtGui.QMainWindow):
    '''Child window to edit shape options
    '''
    __OBJ_NAME__ = 'ctrl_picker_edit_window'
    __TITLE__ = 'Shape Options'
    
    #-----------------------------------------------------------------------------------------------
    #    constructor
    def __init__(self, parent=None, picker_item=None):
        QtGui.QWidget.__init__(self, parent=None)
        
        self.picker_item = picker_item
        
        # Define size
        self.default_width = 270
        self.default_height = 140
        
        # Run setup
        self.setup()
        
        # Other
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
#        self.add_scale_options()
#        self.add_text_options()
#        self.add_target_control_field()
#        self.add_custom_menus_field()
        
        # Add layouts stretch
        self.left_layout.addStretch()
        
        # Udpate fields
        self._update_shape_infos()
        self._update_position_infos()
        self._update_color_infos()
#        self._update_text_infos()
#        self._update_ctrls_infos()
#        self._update_menus_infos()
    
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
    
#    def _update_text_infos(self):
#        self.event_disabled = True
#        
#        # Retrieve et set text field
#        text = self.picker_item.get_text()
#        if text:
#            self.text_field.setText(text)
#        
#        # Set text color fields
#        self._set_text_color_button(self.picker_item.get_text_color())
#        self.text_alpha_sb.setValue(self.picker_item.get_text_color().alpha())
#        self.event_disabled = False
#        
#    def _update_ctrls_infos(self):
#        self._populate_ctrl_list_widget()
#    
#    def _update_menus_infos(self):
#        self._populate_menu_list_widget()
    
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
                                              value=position.x())
        spin_layout.addWidget(self.pos_x_sb)
        
        layout.addLayout(spin_layout)
        
        # Add Y position spin box
        spin_layout = QtGui.QHBoxLayout()
        
        label = QtGui.QLabel()
        label.setText('Y')
        spin_layout.addWidget(label)
        
        self.pos_y_sb = CallBackDoubleSpinBox(callback=self.edit_position_event,
                                              value=position.y())
        spin_layout.addWidget(self.pos_y_sb)
        
        layout.addLayout(spin_layout)
        
        # Add to main layout
        self.left_layout.addWidget(group_box)
    
    def _set_color_button(self, color):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Button, color)
        self.color_button.setPalette(palette)
        self.color_button.setAutoFillBackground(True)
    
#    def _set_text_color_button(self, color):
#        palette = QtGui.QPalette()
#        palette.setColor(QtGui.QPalette.Button, color)
#        self.text_color_button.setPalette(palette)
#        self.text_color_button.setAutoFillBackground(True)
            
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
                                         value=self.picker_item.get_color().alpha())
        layout.addWidget(self.alpha_sb)
        
        # Add to main layout
        self.left_layout.addWidget(group_box)
    
#    def add_text_options(self):
#        '''Add text option fields 
#        '''
#        # Create group box
#        group_box = QtGui.QGroupBox()
#        group_box.setTitle('Text options')
#        
#        # Add layout
#        layout = QtGui.QVBoxLayout(group_box)
#        
#        # Add Caption text field
#        self.text_field = CallbackLineEdit(self.set_text_event)
#        layout.addWidget(self.text_field)
#        
#        # Add size factor spin box
#        spin_layout = QtGui.QHBoxLayout()
#        
#        spin_label = QtGui.QLabel()
#        spin_label.setText('Size factor')
#        spin_layout.addWidget(spin_label)
#        
#        value_sb = CallBackDoubleSpinBox(callback=self.edit_text_size_event,
#                                         value=self.picker_item.data.text_size_factor)
#        spin_layout.addWidget(value_sb)
#        
#        layout.addLayout(spin_layout)
#        
#        # Add color layout
#        color_layout = QtGui.QHBoxLayout(group_box)
#        
#        # Add color button
#        self.text_color_button = CallbackButton(callback=self.change_text_color_event)
#        
#        color_layout.addWidget(self.text_color_button)
#        
#        # Add alpha spin box
#        color_layout.addStretch()
#        
#        label = QtGui.QLabel()
#        label.setText('Alpha')
#        color_layout.addWidget(label)
#        
#        self.text_alpha_sb = CallBackSpinBox(callback=self.change_text_alpha_event,
#                                         value=self.picker_item.get_text_color().alpha())
#        color_layout.addWidget(self.text_alpha_sb)
#
#        # Add color layout to group box layout
#        layout.addLayout(color_layout)
#        
#        # Add to main layout
#        self.left_layout.addWidget(group_box)
#        
#    def add_scale_options(self):
#        '''Add scale group box options
#        '''
#        # Create group box
#        group_box = QtGui.QGroupBox()
#        group_box.setTitle('Scale')
#        
#        # Add layout
#        layout = QtGui.QVBoxLayout(group_box)
#        
#        # Add edit check box
#        self.worldspace_box = QtGui.QCheckBox()
#        self.worldspace_box.setText('World space')
#        
#        layout.addWidget(self.worldspace_box)
#        
#        # Add alpha spin box
#        spin_layout = QtGui.QHBoxLayout()
#        layout.addLayout(spin_layout)
#        
#        label = QtGui.QLabel()
#        label.setText('Factor')
#        spin_layout.addWidget(label)
#        
#        self.scale_sb = QtGui.QDoubleSpinBox()
#        self.scale_sb.setValue(1.1)
#        self.scale_sb.setSingleStep(0.05)
#        spin_layout.addWidget(self.scale_sb)
#        
#        # Add scale buttons
#        btn_layout = QtGui.QHBoxLayout()
#        layout.addLayout(btn_layout)
#        
#        btn = CallbackButton(callback=self.scale_event, x=True)
#        btn.setText('X')
#        btn_layout.addWidget(btn)
#        
#        btn = CallbackButton(callback=self.scale_event, y=True)
#        btn.setText('Y')
#        btn_layout.addWidget(btn)
#        
#        btn = CallbackButton(callback=self.scale_event, x=True, y=True)
#        btn.setText('XY')
#        btn_layout.addWidget(btn)
#        
#        # Add to main left layout
#        self.left_layout.addWidget(group_box)
#        
#    def add_target_control_field(self):
#        '''Add target control association group box
#        '''
#        # Create group box
#        group_box = QtGui.QGroupBox()
#        group_box.setTitle('Control Association')
#        
#        # Add layout
#        layout = QtGui.QVBoxLayout(group_box)
#        
#        # Init list object
#        self.control_list = CallbackListWidget(callback=self.edit_ctrl_name_event)
#        layout.addWidget(self.control_list)
#        
#        # Add buttons
#        btn_layout1 = QtGui.QHBoxLayout()
#        layout.addLayout(btn_layout1)
#        
#        btn = CallbackButton(callback=self.add_selected_controls_event)
#        btn.setText('Add Selection')
#        btn_layout1.addWidget(btn)
#        
#        btn = CallbackButton(callback=self.remove_controls_event)
#        btn.setText('Remove')
#        btn_layout1.addWidget(btn)
#        
#        self.right_layout.addWidget(group_box)
#    
#    def add_custom_menus_field(self):
#        '''Add custom menu management groupe box
#        '''
#        # Create group box
#        group_box = QtGui.QGroupBox()
#        group_box.setTitle('Menus')
#        
#        # Add layout
#        layout = QtGui.QVBoxLayout(group_box)
#        
#        # Init list object
#        self.menus_list = CallbackListWidget(callback=self.edit_menu_event)
#        layout.addWidget(self.menus_list)
#        
#        # Add buttons
#        btn_layout1 = QtGui.QHBoxLayout()
#        layout.addLayout(btn_layout1)
#        
#        btn = CallbackButton(callback=self.new_menu_event)
#        btn.setText('New')
#        btn_layout1.addWidget(btn)
#        
#        btn = CallbackButton(callback=self.remove_menus_event)
#        btn.setText('Remove')
#        btn_layout1.addWidget(btn)
#        
#        self.right_layout.addWidget(group_box)
        
    #===========================================================================
    # Events    
    def handles_cb_event(self, value=False):
        '''Toggle edit mode for shape
        '''
        self.picker_item.set_edit_status(value)
        
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
        
#    def scale_event(self, x=False, y=False):
#        '''Will scale polygon on specified axis based on scale factor value from spin box
#        '''
#        # Get scale factor value
#        scale_factor = self.scale_sb.value()
#        
#        # Build kwargs
#        kwargs = {'x_factor':1.0, 'y_factor':1.0}
#        if x:
#            kwargs['x_factor'] = scale_factor
#        if y:
#            kwargs['y_factor'] = scale_factor
#        
#        # Check space
#        if self.worldspace_box.isChecked():
#            kwargs['world'] = True
#            
#        # Apply scale
#        self.picker_item.scale(**kwargs) 
#    
#    def set_text_event(self, text=None):
#        '''Will set polygon text to field 
#        '''
#        # Skip if event is disabled (updating ui value)
#        if self.event_disabled:
#            return
#        
#        text = unicode(text)
#        self.picker_item.set_text(text)
#    
#    def edit_text_size_event(self, value=1):
#        '''Will edit text size factor
#        '''
#        self.picker_item.set_text_size(value)
#        
#    def change_text_alpha_event(self, value=255):
#        '''Will edit the polygon transparency alpha value
#        '''
#        # Skip if event is disabled (updating ui value)
#        if self.event_disabled:
#            return
#        
#        # Get current color
#        color = self.picker_item.get_text_color()
#        color.setAlpha(value)
#        
#        # Update color
#        self.picker_item.set_text_color(color)
#        
#    def change_text_color_event(self):
#        '''Will edit polygon color based on new values
#        '''
#        # Skip if event is disabled (updating ui value)
#        if self.event_disabled:
#            return
#        
#        # Open color picker dialog
#        color = QtGui.QColorDialog.getColor(initial=self.picker_item.get_text_color(),
#                                            parent=self)
#        
#        # Abort on invalid color (cancel button)
#        if not color.isValid():
#            return
#        
#        # Update button color
#        palette = QtGui.QPalette()
#        palette.setColor(QtGui.QPalette.Button, color)
#        self.text_color_button.setPalette(palette)
#        
#        # Edit new color alpha
#        alpha = self.picker_item.get_text_color().alpha()
#        color.setAlpha(alpha)
#        
#        # Update color
#        self.picker_item.set_text_color(color)
#        
#    #===========================================================================
#    # Control management
#    def _populate_ctrl_list_widget(self):
#        '''Will update/populate list with current shape ctrls
#        '''        
#        # Empty list
#        self.control_list.clear()
#        
#        # Populate node list
#        controls = self.picker_item.get_controls() 
#        for i in range(len(controls)):
#            item = CtrlListWidgetItem(index=i)
#            item.setText(controls[i])
#            self.control_list.addItem(item)
#    
#    def edit_ctrl_name_event(self, item=None):
#        '''Double click event on associated ctrls list
#        '''
#        if not item:
#            return
#        
#        # Open input window
#        name, ok = QtGui.QInputDialog.getText(self,
#                                              self.tr("Ctrl name"),
#                                              self.tr('New name'),
#                                              QtGui.QLineEdit.Normal,
#                                              self.tr(item.text()))
#        if not (ok and name):
#            return
#        
#        # Update influence name
#        new_name = item.setText(name)
#        if new_name:
#            self.update_shape_controls_list()
#        
#        # Deselect item
#        self.control_list.clearSelection()
#        
#    def add_selected_controls_event(self):
#        '''Will add maya selected object to control list
#        '''
#        # Get selection
#        sel = cmds.ls(sl=True)
#        
#        # Add to stored list
#        for ctrl in sel:
#            if ctrl in self.picker_item.get_controls():
#                continue
#            self.picker_item.append_control(ctrl)
#        
#        # Update display
#        self._populate_ctrl_list_widget()
#    
#    def remove_controls_event(self):
#        '''Will remove selected item list from stored controls 
#        '''
#        # Get selected item
#        items = self.control_list.selectedItems()
#        assert items, 'no list item selected'
#        
#        # Remove item from list
#        for item in items:
#            self.picker_item.remove_control(item.node())
#            
#        # Update display
#        self._populate_ctrl_list_widget()
#              
#    def get_controls_from_list(self):
#        '''Return the controls from list widget
#        '''
#        ctrls = list()
#        for i in range(self.control_list.count()):
#            item = self.control_list.item(i)
#            ctrls.append(item.node()) 
#        return ctrls
#        
#    def update_shape_controls_list(self):
#        '''Update shape stored control list
#        '''        
#        ctrls = self.get_controls_from_list()
#        self.picker_item.set_control_list(ctrls)
#        
#    #===========================================================================
#    # Menus management
#    def _add_menu_item(self, text=None):
#        item = QtGui.QListWidgetItem()
#        item.index = self.menus_list.count()
#        if text:
#            item.setText(text)
#        self.menus_list.addItem(item)
#        return item
#            
#    def _populate_menu_list_widget(self):
#        '''
#        '''
#        # Empty list
#        self.menus_list.clear()
#        
#        # Populate node list
#        menus_data = self.picker_item.data.get_custom_menus() 
#        for i in range(len(menus_data)):
#            self._add_menu_item(text=menus_data[i][0])
#    
#    def _update_menu_data(self, index, name, cmd):
#        menu_data = self.picker_item.data.get_custom_menus()
#        if index> len(menu_data)-1:
#            menu_data.append([name, cmd])
#        else:
#            menu_data[index] = [name, cmd]
#        self.picker_item.data.set_custom_menus(menu_data)
#        
#    def edit_menu_event(self, item=None):
#        '''Double click event on associated menu list
#        '''
#        if not item:
#            return
#        
#        name, cmd = self.picker_item.data.get_custom_menus()[item.index]
#        
#        # Open input window
#        name, cmd, ok = CustomMenuEditDialog.get(name=name, cmd=cmd)
#        if not (ok and name and cmd):
#            return
#        
#        # Update menu display name
#        item.setText(name)
#        
#        # Update menu data
#        self._update_menu_data(item.index, name, cmd)
#        
#        # Deselect item
#        self.control_list.clearSelection()
#    
#    def new_menu_event(self):
#        '''
#        '''
#        # Open input window
#        name, cmd, ok = CustomMenuEditDialog.get()
#        if not (ok and name and cmd):
#            return
#        
#        # Update menu display name
#        item = self._add_menu_item(text=name)
#        
#        # Update menu data
#        self._update_menu_data(item.index, name, cmd)
#    
#    def remove_menus_event(self):
#        # Get selected item
#        items = self.control_list.selectedItems()
#        assert items, 'no list item selected'
#        
#        # Remove item from list
#        menu_data = self.picker_item.data.get_custom_menus()
#        for i in range(len(items)):
#            menu_data.pop(items[i].index -i)
#        self.picker_item.data.set_custom_menus(menu_data)
#        
#        # Update display
#        self._populate_ctrl_list_widget()
        
    
class MainDockWindow(QtGui.QDockWidget):
    __OBJ_NAME__ = 'ctrl_picker_window'
    __TITLE__ = 'Ctrl Picker'
    __EDIT_MODE__ = handlers.__EDIT_MODE__
    
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
        self.default_color = QtGui.QColor(200,200,200,180)
        self.childs = list()
        self.char_node = node.DataNode()
        self.status = False
        
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
        
        # Add bottom vertical spacer to main layout
#        self.main_vertical_layout.addStretch()
        
        # Add main widget to window
        self.setWidget(self.main_widget)
        
        # Add docking event signet
        self.connect(self,
                     QtCore.SIGNAL('topLevelChanged(bool)'),
                     self.dock_event)
        
    def reset_default_size(self):
        '''Reset window size to default
        '''
        self.resize(self.default_width, self.default_height)
    
    def get_current_data(self):
        return self.char_node.data
    
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
        box_layout = QtGui.QHBoxLayout(box)
        
        # Add combo box
        self.char_selector_cb = CallbackComboBox(callback=self.selector_change_event)
        box_layout.addWidget(self.char_selector_cb)
        
        # Init combo box data
        self.char_selector_cb.nodes = list()
        
        # Add Refresh  button
        self.char_refresh_btn = CallbackButton(callback=self.refresh)
        self.char_refresh_btn.setText('Refresh')
        self.char_refresh_btn.setFixedWidth(55)
        
        box_layout.addWidget(self.char_refresh_btn)
        
        # Edit buttons
        self.new_char_btn = None
        self.save_char_btn = None
        if __EDIT_MODE__.get():
            # Add New  button
            self.new_char_btn = CallbackButton(callback=self.new_character)
            self.new_char_btn.setText('New')
            self.new_char_btn.setFixedWidth(40)
        
            box_layout.addWidget(self.new_char_btn)
            
            # Add Save  button
            self.save_char_btn = CallbackButton(callback=self.save_character_event)
            self.save_char_btn.setText('Save')
            self.save_char_btn.setFixedWidth(40)
        
            box_layout.addWidget(self.save_char_btn)
            
        # Create character picture widget
        self.pic_widget = SnapshotWidget(get_current_data_callback=self.get_current_data)
        layout.addWidget(self.pic_widget)
        
    def add_tab_widget(self, name = 'default'):
        '''Add control display field
        '''
        self.tab_widget = ContextMenuTabWidget(self)
        self.main_vertical_layout.addWidget(self.tab_widget)
        
        # Add default first tab
        self.view = GraphicViewWidget()
        self.tab_widget.addTab(self.view, name)
        
#        # Add mouse event catcher widget
#        self.mouse_catcher = MouseEventCatcherWidget(parent=self,
#                                                     get_ctrls_callback=self.get_ctrl_list,
#                                                     field_widget_callback = self.get_active_field,
#                                                     add_ctrl_callback=self.add_ctrl_event,
#                                                     remove_ctrl_callback=self.remove_ctrl,
#                                                     set_tab_background_callback=self.tab_widget.set_background_event,
#                                                     reset_tab_background_callback=self.tab_widget.reset_background_event,
#                                                     move_to_back_callback=self.move_ctrl_to_back_event)
        
    def get_active_field(self):
        '''Return the active ctrl field
        '''
        return self.tab_widget.currentWidget()
    
    def get_ctrl_list(self):
        # Get tab index
        index = self.tab_widget.currentIndex()
        
        # Remove from control list
        return self.get_current_data().tabs[index].controls
#        return self.data['tabs'][index].get('ctrls', list())
    
    def dock_event(self, area=None):
        '''Disable resizing to force proper size and reenable after docking
        '''
        new_size = self.size()
        
        # Prevent docking update in edit mode to preserve controls
        if __EDIT_MODE__.get():
            return
        
#        self.mouse_catcher.toggle_edit_mode()
#        self.mouse_catcher.toggle_edit_mode()
        
        if not self.isFloating():
            self.resize(new_size)
        
#    def resizeEvent(self, event=None):
#        '''Resize ctrl field infos
#        '''
##        # Resize mouse event catcher widget
##        self.mouse_catcher.update_size()
#        
#        # Parse tabs
#        for tab in self.get_current_data().tabs:
#            for ctrl in tab.controls:
#                ctrl.get_widget().update_size()
#        
#        if event:
#            event.accept()
    
    def closeEvent(self, *args, **kwargs):
        '''Overwriting close event to close child windows too
        '''
        # Delete script jobs
        self.kill_script_jobs()
        
        # Close childs
        for child in self.childs:
            child.close()
        
        # Close ctrls options windows
        for ctrl in self.get_ctrl_list():
            ctrl_widget = ctrl.get_widget()
            if not ctrl_widget.edit_window:
                continue
            ctrl_widget.edit_window.close()
        
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
        
    def set_default_color(self, color):
        '''Will set default color for new polygons
        '''
        self.default_color = QtGui.QColor(color)
        
#    def add_ctrl_event(self, event=None, load=False):
#        '''Add new polygon control to current tab
#        '''
#        ctrl = PickerItem()
#        scene = self.get_active_field().scene()
#        scene.addItem(ctrl)
#        
##        # Create new ctrl
##        ctrl = PolygonShapeWidget(self.get_active_field(),
##                                  color=self.default_color,
##                                  set_default_color_callback=self.set_default_color,
##                                  add_ctrl_callback=self.add_ctrl_event,
##                                  get_current_data_node_callback=self._get_current_data_node,)
##
##        # Do not add control to data list in load mode
##        if load:
##            return ctrl
##                   
##        # Move ctrl
##        if event:
##            ctrl.move_to(event.pos())
##        else:
##            ctrl.move_to_center()
##        
##        # Get tab index
##        index = self.tab_widget.currentIndex()
##
##        # Update ctrl list
##        self.get_current_data().tabs[index].controls.append(ctrl.data)
#
#        return ctrl
    
    def remove_ctrl(self, ctrl):
        '''Delete ctrl and remove from data
        '''
        # Get tab index
        index = self.tab_widget.currentIndex()
        
        # Remove from control list
        control_widgets = self.get_current_data().tabs[index].get_control_widgets()
        if not ctrl in control_widgets:
            return
        
        # Close ctrl edit window if open
        if ctrl.edit_window:
            ctrl.edit_window.close()
        
        # Delete widget
        ctrl.deleteLater()
        self.get_current_data().tabs[index].controls.pop(control_widgets.index(ctrl))
        ctrl.close()
        ctrl = None
    
    def move_ctrl_to_back_event(self, ctrl):
        '''Move control to background layer
        '''
        # Get tab index
        index = self.tab_widget.currentIndex()
        
        control_widgets = self.get_current_data().tabs[index].get_control_widgets()
        poly_data = self.get_current_data().tabs[index].controls.pop(control_widgets.index(ctrl))
        self.get_current_data().tabs[index].controls.insert(0, poly_data)
        
        # Refresh display
        tab_widget = self.get_active_field()
        for control in self.get_current_data().tabs[index].controls:
            widget = control.get_widget()
            widget.setParent(None)
            widget.setParent(tab_widget)
            widget.show()

    #===========================================================================
    # Character selector handlers
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
#        self.mouse_catcher.setEnabled(self.status)
        if self.save_char_btn:
            self.save_char_btn.setEnabled(self.status)
        
        # Reset tabs
        if not self.status:
            self.load_default_tabs()
            
    def load_default_tabs(self):
        '''Will reset and load default empty tabs
        '''
        self.tab_widget.reset()
        self.tab_widget.addTab(QtGui.QWidget(), 'None')
            
    def refresh(self):
        '''Refresh char selector and window
        '''
        # Re-populate selector
        self.populate_char_selector()
            
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
        if self._get_current_data_node():
            self.save_character()
        
        # Create new data node
        data_node = node.DataNode(name=unicode(name))
        data_node.create()
        self.char_node = data_node
        self.refresh()
    
    #===========================================================================
    # Data
    def _get_current_namespace(self):
        return self._get_current_data_node().get_namespace()
    
    def _get_current_data_node(self):
        '''Return current character data node
        '''
        # Empty list case
        if not self.char_selector_cb.count():
            return None
        
        # Return node from combo box index 
        index = self.char_selector_cb.currentIndex()
        return self.char_selector_cb.nodes[index]
        
    def _load_polygon_ctrl(self, data):
        
        ctrl = self.add_ctrl_event(load=True)
        ctrl.set_data(data)
        
        return ctrl
    
    def _load_tab(self, tab_data):
        # Add tab to display
        widget = GraphicViewWidget()
        self.tab_widget.addTab(widget, tab_data.name, load=True)
        
        # Make new tab active
        self.tab_widget.setCurrentIndex(self.tab_widget.count()-1)
        
        # Set tab background
        path = tab_data.background
        widget.set_background(path)
        
        # Load tab controls
        for ctrl_data in tab_data.controls:
            self._load_polygon_ctrl(ctrl_data)
        
        # Return to first tab
        self.tab_widget.setCurrentIndex(0)
        
    def load_character(self):
        '''Load currently selected data node
        '''
        # Get DataNode
        data_node = self._get_current_data_node()
        if not data_node:
            return
        
        self.char_node = data_node
        self.char_node.read_data()
        
        # Load snapshot
        path = self.char_node.data.snapshot
        self.pic_widget.set_background(path)
        
        # Reset tabs
        self.tab_widget.reset()
        
        # Load data in default size
        self.tab_widget.set_fixed_size()
    
        # Parse tabs
        for tab_data in self.char_node.data.tabs:
            self._load_tab(tab_data)
        
        # Default tab
        if not self.tab_widget.count():
            self.tab_widget.addTab(GraphicViewWidget(), 'default')
        
        # Stretch size to layout
        self.tab_widget.set_stretchable_size()
        
    
    def save_character_event(self):
        '''Save character button event, will show a warning in anim mode
        '''
        # Block save in anim mode
        if not __EDIT_MODE__.get():
            QtGui.QMessageBox.warning(self,
                                      "Warning",
                                      "Save is not permited in anim mode")
            return
        
        self.save_character()
        
    def save_character(self):
        '''Save data to current selected data_node
        '''
        # Get DataNode
        data_node = self._get_current_data_node()
        assert data_node, 'No data_node found/selected'
        
        # Abord in anim (switching mode)
        if not __EDIT_MODE__.get():
            return
        
        # Write data to node
        data_node.write_data()
    
    #===========================================================================
    # Script jobs handling
    def add_script_jobs(self):
        '''Will add maya scripts job events
        '''
        self.script_jobs = list()
        
        ui_id = sip.unwrapinstance(self)
        ui_name = OpenMayaUI.MQtUtil.fullName( long(ui_id) )
        job_id = cmds.scriptJob(p=ui_name, cu=True, kws=False, e=['SelectionChanged', self.selection_change_event])
        self.script_jobs.append(job_id)
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
        for ctrl in self.get_ctrl_list():
            ctrl.get_widget().run_selection_check()
            
        
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
    