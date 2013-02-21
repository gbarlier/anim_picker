# Author: Guillaume Barlier

import sys
from maya import cmds

import data


class DataNode():
    # Pipeline
    __NODE__ = 'PICKER_DATAS'
    __TAG__ = 'rig_picker_datas_node'

    # Attributes names
    __DATAS_ATTR__ = 'rig_ctrl_infos'
    
    
    def __init__(self, name=None):
        self.name = name
        if not name:
            self.name = self.__NODE__
        self.data = data.CharacterData()
    
    def __repr__(self):        
        return "%s.%s(u'%s')"%(self.__class__.__module__,
                              self.__class__.__name__,
                              self.name)
    def __lt__(self, other):
        '''override for "sort" function
        '''
        return self.name < other.name
     
    def __str__(self):
        return self.name
    
    def __melobject__(self):
        '''return maya mel friendly string result'''
        return self.name
    
    def _assert_exists(self):
        assert cmds.objExists(self.name), 'Data node "%s" not found.'

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
        if cmds.referenceQuery(self.name, inr=True):
            return
        
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
    def write_data(self):
        data_dict = self.data.get_data()
        self._set_str_attr(self.__DATAS_ATTR__, value=data_dict)
    
    def read_data(self):
        self._assert_exists()
        
        # Reset node data
        self.data = data.CharacterData()
        
        # Get data from attribute
        attr_data = self._get_attr(self.__DATAS_ATTR__)
        if not attr_data:
            return self.data
        data_dict = eval(attr_data)
        
        # Init data node
        self.data.load_data(data_dict)
        
        return self.data
    
    
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
    
    