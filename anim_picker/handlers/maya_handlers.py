import sys
from maya import cmds
from maya import OpenMaya

def get_flattened_nodes(nodes):
    '''Will 'flatten' sets to get all nodes
    '''
    # Init results
    results = list()
    
    # Parse nodes
    for node in nodes:
        # Skip if not doesn't exists 
        if not cmds.objExists(node):
            continue
        
        # Object set type
        if cmds.nodeType(node) == 'objectSet':
            content = cmds.sets(node, q=True, no=True)
            set_nodes = get_flattened_nodes(content)
            
            for set_node in set_nodes:
                if set_node in results:
                    continue
                results.append(set_node)
            
            continue
        
        # Append not to results
        results.append(node)
        
    return results

def select_nodes(nodes, namespace=None, modifier=None):
    '''Select maya node handler with specific modifier behavior
    '''
    # Parse nodes
    filtered_nodes = list()
    for node in nodes:
        # Add namespace to node name
        if namespace:
            node = '%s:%s'%(namespace, node)
            
        # skip invalid nodes
        if not cmds.objExists(node):
            sys.stderr.write(' node "%s" not found, skipping\n'%node)
            continue
        
        # Set case
        if cmds.nodeType(node) == 'objectSet':
            content = get_flattened_nodes([node])
            filtered_nodes.extend(content)
            continue
        
        filtered_nodes.append(node)
    
    # Stop here on empty list
    if not filtered_nodes:
        return
    
    # Remove duplicates
    filtered_nodes = list(set(filtered_nodes))
    
    # No modifier case selection
    if not modifier:
        return cmds.select(filtered_nodes)
        
    # Control case (toggle)
    if modifier == 'control':
        return cmds.select(filtered_nodes, tgl=True)
        
    # Alt case (remove)
    elif modifier == 'alt':
        return cmds.select(filtered_nodes, d=True)
    
    # Shift case (add) and none
    else:
        return cmds.select(filtered_nodes, add=True)
            
def reset_node_attributes(node, attr='rigBindPose'):
    '''Will reset attribute to stored values
    '''
    # Sanity check
    if not cmds.objExists(node):
        sys.stderr.write(' reset_node_attributes -> node "%s" not found, skipping\n'%node)
        return
    
    # Check for attribute
    if not cmds.attributeQuery(attr, n=node, ex=True):
        sys.stderr.write(' reset_node_attributes -> node "%s" has no attribute named "%s", skipping\n'%(node, attr))
        return
    
    # Get attributes dictionary
    str_values =cmds.getAttr("%s.%s"%(node, attr))
    if not str_values:
        return
    attr_values = eval(str_values)
    
    # Check type
    if not type(attr_values) == dict:
        sys.stderr.write(' reset_node_attributes -> stored data for node "%s" are not a dictionary\n'%node)
        return
    
    # Apply values
    for attr_key in attr_values:
        # Check if attribute exists
        if not cmds.attributeQuery(attr_key, n=node, ex=True):
            continue
        
        # Apply stored value
        try:
            cmds.setAttr('%s.%s'%(node, attr_key), attr_values[attr_key])
        except:
            sys.stderr.write(' reset_node_attributes -> failed to set attribute "%s.%s" to %s\n'%(node, attr, unicode(attr_values[attr_key])))
            
    return True


class SelectionCheck():
    def __init__(self):
        self.sel = OpenMaya.MSelectionList() 
    
    def update(self):
        '''Will update selection data
        '''
        # Get current selection 
        self.sel.clear()
        OpenMaya.MGlobal.getActiveSelectionList(self.sel)
    
    @staticmethod
    def get_node_mobject(node):
        '''Will return node mobject if possible
        '''
        # Sanity check
        if not cmds.objExists(node):
            return
        
        # Cast node to MSelectionList
        nodes = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getSelectionListByName(node, nodes)
        
        # Get node mobject
        mobject = OpenMaya.MObject()
        nodes.getDependNode( 0, mobject )
        return mobject
    
    @classmethod
    def get_node_mdagpath(cls, node):
        '''Return node MDagPath if possible
        '''
        mobject = cls.get_node_mobject(node)
        if not mobject:
            return
        
        # Abort if not a Dag object
        if not mobject.hasFn(OpenMaya.MFn.kDagNode):
            return
        
        return OpenMaya.MDagPath.getAPathTo(mobject)
    
    def is_selected(self, node):
        '''Will check if node is currently selected
        '''
        # Get node MDagPath
        node = self.get_node_mdagpath(node)
        if not node:
            return False
        
        # Check if node is in selection lest
        return self.sel.hasItem(node)
        
        