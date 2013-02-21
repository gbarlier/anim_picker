# Author: Guillaume Barlier

from PyQt4 import QtCore, QtGui


class PolyData():
    '''Picker polygon data object
    '''
    __DEFAULT_COLOR__ = (200,200,200,180)
    __DEFAULT_TEXT_COLOR__ = (30,30,30,180)
    
    def __init__(self, data=None, widget=None):
        self.text = None
        self.text_size_factor = 1
        self.text_color = QtGui.QColor(self.__DEFAULT_TEXT_COLOR__)
        self.color = QtGui.QColor(self.__DEFAULT_COLOR__)
        self.points = list()
        self.anim_points = list()
        self.maya_nodes = list()
        self.custom_menus = list()
        self.widget = widget
        
        if data:
            self.load_data(data)
    
    def set_text(self, text):
        '''Set displayed text for polygon
        '''
        self.text = text
        
    def get_text(self):
        '''Get displayed text for polygon
        '''
        return self.text
    
    def set_text_color(self, color):
        '''Set polygon color data
        '''
        self.text_color = color
    
    def set_text_size_factor(self, factor):
        '''Set text scale factor for display
        '''
        self.text_size_factor = factor
        
    def set_widget(self, widget):
        '''Set associated widget for poly data
        '''
        self.widget = widget
    
    def get_widget(self):
        '''Return associated widget
        '''
        return self.widget
    
    def set_custom_menus(self, menus):
        '''Set custom menu list for current poly data
        '''
        self.custom_menus = list(menus)
    
    def get_custom_menus(self):
        '''Return current menu list for current poly data
        '''
        return self.custom_menus
            
    def set_color(self, color):
        '''Set polygon color data
        '''
        self.color = color
        
    def set_points(self, points):
        '''Set polygon points data
        '''
        self.points = list(points)
        self.update_anim_points()
        
    def set_maya_nodes(self, nodes):
        '''Set associrated maya node for polygon
        '''
        self.maya_nodes = list(nodes)
    
    def update_anim_points(self):
        '''Will update anim points list (for resizing) with stored points
        '''
        self.anim_points = list()
        for point in self.points:
            self.anim_points.append(QtCore.QPointF(point))
        
    def load_data(self, data=dict()):
        '''Load data dictionary to current polygon instance
        '''
        # Text data
        self.text = data.get('text', None)
        
        # Text color data
        color_data = data.get('text_color', self.__DEFAULT_TEXT_COLOR__)
        self.text_color = QtGui.QColor(*color_data)
        
        # Text size factor
        self.text_size_factor = data.get('text_size_factor', 1)
        
        # Color data
        color_data = data.get('color', self.__DEFAULT_COLOR__)
        self.color = QtGui.QColor(*color_data)
        
        # Points data
        points = list()
        for point in data.get('points', list()):
            points.append(QtCore.QPointF(*point))
        self.set_points(points)
        
        # Maya nodes data
        self.maya_nodes = data.get('ctrls', list())            
        
        # Custom menus
        self.custom_menus = data.get('menus', list())
        
    def get_data(self):
        '''Return polygon data as a dictionary
        '''
        data = dict()
        
        # Add points
        points = list()
        for point in self.points:
            points.append((point.x(), point.y()))
        data['points'] = points
        
        # Add text
        if self.text:
            data['text'] = self.text
        
        # Add text color
        color = self.text_color.getRgb()
        if not color == self.__DEFAULT_TEXT_COLOR__:
            data['text_color'] = self.text_color.getRgb()
            
        # Add text size
        if not self.text_size_factor == 1:
            data['text_size_factor'] = self.text_size_factor
        
        # Add color
        color = self.color.getRgb()
        if not color == self.__DEFAULT_COLOR__:
            data['color'] = self.color.getRgb()
        
        # Add associated controls
        data['ctrls'] = self.maya_nodes
        
        # Add menus
        if self.custom_menus:
            data['menus'] = self.custom_menus
        
        return data
    
    
class TabData():
    '''Picker tab data object
    '''
    def __init__(self, name='tab', data=None):
        self.name = name
        self.background = None
        self.controls = list()
        
        if data:
            self.load_data(data)
    
    def load_data(self, data):
        '''Load data dictionary to current tab instance
        '''
        self.name = data.get('name', self.name)
        self.background = data.get('background', None)
        
        self.controls = list()
        controls_data = data.get('controls', list())
        for control in controls_data:
            self.controls.append(PolyData(data=control))
            
    def get_controls_data(self):
        '''Return control list data dictionaries
        '''
        data = list()
        for ctrl in self.controls:
            data.append(ctrl.get_data())
        return data
    
    def get_data(self):
        '''Return Tab data dictionary
        '''
        data = dict()
        data['name'] = self.name
        
        if self.background:
            data['background']= self.background
        
        controls_data = self.get_controls_data()
        if controls_data:
            data['controls'] = controls_data
        
        return data
        
    def get_control_widgets(self):
        '''Return widget for every controls data
        '''
        widgets = list()
        for i in range(len(self.controls)):
            widgets.append(self.controls[i].get_widget())
        return widgets
                
        
class CharacterData():
    '''Picker character data object
    '''
    def __init__(self, data=None):
        self.snapshot = None
        self.tabs = list()
        
        if data:
            self.load_data(data)
            
    def load_data(self, data):
        '''Load data dictionary to current character instance
        '''
        # Snapshot data
        self.snapshot = data.get('snapshot', None)
        
        # Tabs data
        self.tabs = list()
        tabs = data.get('tabs', list())
        for tab in tabs:
            self.tabs.append(TabData(data=tab))
        
    def _get_tabs_data(self):
        '''Return tabs list data dictionary
        '''
        data = list()
        for tab in self.tabs:
            data.append(tab.get_data())
        return data
        
    def get_data(self):
        '''Return character instance data as a dictionary
        '''
        data = dict()
        
        if self.snapshot:
            data['snapshot'] = self.snapshot
        
        tabs_data = self._get_tabs_data()
        if tabs_data:
            data['tabs'] = tabs_data
            
        return data
    
    def add_tab(self, tab_data):
        '''Add a tab data to character data tab list
        '''
        self.tabs.append(tab_data)
    
    def clear(self):
        '''Reset character instance
        '''
        self.__init__()
        
        