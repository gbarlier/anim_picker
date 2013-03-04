# Author: Guillaume Barlier

import sys
from maya import cmds

class DataNode():
    # Pipeline
    __NODE__ = 'PICKER_DATAS'
    __TAG__ = 'picker_datas_node'

    # Attributes names
    __DATAS_ATTR__ = 'picker_datas'
    
    
    def __init__(self, name=None):
        self.name = name
        if not name:
            self.name = self.__NODE__
        
        self.data = dict()
        if cmds.objExists(self.name):
            self.data = self.read_data()
    
    def __repr__(self):        
        return "%s.%s(u'%s')"%(self.__class__.__module__,
                              self.__class__.__name__,
                              self.name)
    def __lt__(self, other):
        '''Override for "sort" function
        '''
        return self.name < other.name
     
    def __str__(self):
        return self.name
    
    def __melobject__(self):
        '''Return maya mel friendly string result'''
        return self.name
        
    def exists(self):
        return cmds.objExists(self.name)
    
    def _assert_exists(self):
        assert self.exists(), 'Data node "%s" not found.'%self.name
    
    def _assert_not_referenced(self):
        assert not cmds.referenceQuery(self.name, inr=True), 'Data node "%s" is referenced, and can not be modified.'%self.name
        
    def create(self):
        '''Will create data node
        '''
        # Abort if node already exists
        if cmds.objExists(self.name):
            sys.stderr.write(' node "%s" already exists.\n'%self.name)
            return self.name
        
        # Create data node (render sphere for outliner "icon")
        shp = cmds.createNode('renderSphere')
        cmds.setAttr('%s.radius'%shp, 0)
        cmds.setAttr('%s.v'%shp, 0)
        
        # Rename data node
        node = cmds.listRelatives(shp, p=True)[0]
        node = cmds.rename(node, self.name)
    
        # Tag data node
        cmds.addAttr(node, ln=self.__TAG__, at='bool', dv=True)
        cmds.setAttr('%s.%s'%(node, self.__TAG__), k=False, l=True)

        # Add datas path attribute
        self._add_str_attr(node, self.__DATAS_ATTR__)
    
    #===========================================================================
    # Maya attributes
    def _get_attr(self, attr):
        '''Return node's attribute value
        '''
        self._assert_exists()
        
        return cmds.getAttr('%s.%s'%(self.name, attr)) or None
        
    def _add_str_attr(self, node, ln):
        '''Add string attribute to data node
        '''
        self._assert_exists()
        
        cmds.addAttr(node, ln=ln, dt='string')
        cmds.setAttr('%s.%s'%(node, ln), k=False, l=True, type='string')
    
    def _set_str_attr(self, attr, value=None):
        '''Set string attribute value
        '''
        # Sanity check
        self._assert_exists()
        self._assert_not_referenced()
        
        # Init value
        if not value:
            value = ''
        
        # Unlock attribute
        cmds.setAttr('%s.%s'%(self.name, attr), l=False, type='string')
        
        # Set value and re-lock attr
        cmds.setAttr('%s.%s'%(self.name, attr), value, l=True, type='string')
    
    def get_namespace(self):
        '''Return namespace for current node
        '''
        self._assert_exists()
        if not self.name.count(':'):
            return None
        return self.name.rsplit(':', 1)[0]
    
    #===========================================================================
    # Set attributes
    def get_data(self):
        return self.data
    
    def set_data(self, data):
        self.data = data
        
    def write_data(self, data=None):
        '''Write data to data node
        '''
        if not data:
            data = self.data
        self._set_str_attr(self.__DATAS_ATTR__, value=data)
    
    def read_data(self):
        '''Read data from data node
        '''
        self._assert_exists()
        
        # Reset node data
        data = dict()
        
        # Get data from attribute
        attr_data = self._get_attr(self.__DATAS_ATTR__)
        if attr_data:
            data = eval(attr_data)
        
        return data
    
    def countains(self, node):
        '''Will return True if data_node contains selected node in related controls data
        '''
        for tab_data in self.data['tabs']:
            for item_data in tab_data[1]:
                controls = item_data.get('controls', list())
                if controls.count(node):
                    return True
        return False
    
    
def get_nodes():
    '''Return data nodes found in scene
    '''
    data_nodes = list()
    for maya_node in cmds.ls('*.%s'%DataNode.__TAG__, o=True, r=True) or list():
        data_node = DataNode(maya_node)
        data_node.read_data()
        data_nodes.append(data_node)
    
    data_nodes.sort()
    return data_nodes
    
def get_node_for_object(item):
    '''Will try to return related picker data_node for specified object
    '''
    namespaces = list()
    
    # No namespace case
    if not cmds.referenceQuery(item, inr=True):
        namespaces.append(':')
    
    # Referenced node case
    else:
        prev_namespace = ':'
        for namespace in item.split(':')[:-1]:
            namespace = '%s%s:'%(prev_namespace, namespace)
            namespaces.append(namespace)
    
    # Parse namespaces
    for namespace in namespaces:
        for data_node in cmds.ls('%s*.%s'%(namespace, DataNode.__TAG__), o=True) or list():
            data_node = DataNode(data_node)
            if data_node.countains(item.replace(namespace[1:], '')):
                return data_node      
    return None
        
        
        
        
    