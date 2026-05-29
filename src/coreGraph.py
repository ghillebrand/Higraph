""" Core Graph Classes
V01:
This implements directed hyper multigraphs in a class Graph.
This is the "sort-of-pure maths" implementation. there are redundant links from
   nodes->edges as well as edges-> nodes, to make graphical editing & drawing a bit easier
The graphical representation for higraphs will be added later

Nodes as sets will be added later - inclusion is easier than n-ary edges.

"""

#from typing import ClassVar
import copy
from  HGConstants import *

class Graph:
    """ a set of nodes and edges"""
    
    #A graph-global ID. Allows for hyperedges (edges start XOR end on edges)
    #nextID:int = 0 JH
    nextID:int = 1
    #A set of used IDs. Allows loading of files with existing IDs
    #TODO: Clear on FileNew
    IDsUsed = set()
    
    # a container class of nodes. Mostly exists as a place to hold metadata, and some optimisations 
    class node():
      
        def __init__(self,metadata=None,id=None, parents = [], children = []):
            #Check for unique ID
            if id:
                if not id in Graph.IDsUsed:
                    self.nodeID = id
                    Graph.IDsUsed.add(id)
            else:
                while Graph.nextID in Graph.IDsUsed:
                    Graph.nextID += 1
                self.nodeID = Graph.nextID
                Graph.IDsUsed.add(self.nodeID)
                Graph.nextID += 1

            self.metadata = metadata
            self.startsEdges = []  
            self.endsEdges = []
            self.parents = parents   #Technically redundant, as this can be inferred from walking through self.children
            self.children = children  #Loosely equivalent to Harels sub-blob function σ^1


        def __repr__(self):
            return f"nodeID:{self.nodeID},metadata:{self.metadata},startsEdges:{self.startsEdges},"\
                    f"endsEdges:{self.endsEdges}, parents:{self.parents}, children:{self.children}\n"

        #TODO Make a better str function
        __str__ = __repr__
        
        def addStarts(self,edge):
            """add that this node starts <edge>  """
            self.startsEdges.append(edge)
        
        def addEnds(self,edge):
            """add that this node ends <edge>  """
            self.endsEdges.append(edge)
    
        def addParent(self,parent):
            #TODO: Add checks for self-parenting - loops are bad here.
            self.parents.append(parent)
        
        def delParent(self,parent):
            if parent in self.parents:
                self.parents.remove(parent)

        def resetParents(self,parentList):
            """ Overwrites the parents with a new list"""
            self.parents = parentList

        def addChild(self,child):
            self.children.append(child)

        def delChild(self,child):
            if child in self.children:
                self.children.remove(child)
        
        def resetChildren(self,childList):
            """overwrites the children list with a new set of values"""
            self.children = childList
    #-------------------------------------------------------------------------------------#
    
    class edge():
       
        def __init__(self,start:int,end:int,metadata:dict|None=None,id=None):
            """new edge, must have start = nodeID or tuple, end = nodeID, optional metadata   """
            #TODO: For re-creating from file/ paste, ID will need to be a param?
             #Check for unique ID
            if id and not id in Graph.IDsUsed:
                    self.edgeID = id
                    Graph.IDsUsed.add(id)
            else:
                while Graph.nextID in Graph.IDsUsed:
                    Graph.nextID += 1
                self.edgeID = Graph.nextID
                Graph.IDsUsed.add(self.edgeID)
                Graph.nextID += 1           

            self.metadata = metadata
            self.startNodes = [] 
            self.endNodes = []


        def __repr__(self):
            return f"edgeID:{self.edgeID},metadata:{self.metadata},startNodes:{self.startNodes},endNodes:{self.endNodes}\n"

        __str__ = __repr__
        
        def updateMeta(self,metadata:list[dict]):
            """ updates (overwriting) metadata of the edge. metadata must be list """
            for m in metadata:
                self.metadata.update(m)
                

    #-------------------------------------------------------------------------------------#
    
    # Parent Graph methods
        
    def __init__(self):
        #TODO: can this be one list, with a flag indicating the type?
        self.nodeD = {}  #Dictionary of nodes
        self.edgeD = {}  #Dictionary of edges
        Graph.IDsUsed = set()
        #Store default edge type. CAn be overridden on individual edges
        #TODO: Make this a per-model editable param.
        self.isDirected = ISDIGRAPH
        #TODO: Add in the global dictionary of metadata attribs the graph holds. Node vs Edge metadata?
        # adding metadata to items must update this list
        self.metadataKeys = {}

    def __repr__(self):
        return(f"nodes:\n{self.nodeD}\nedges:\n{self.edgeD}")
    
    __str__ = __repr__

    def resetIDs(self):
        """reset the Class vars. Not all new instances may want to do this """
        Graph.nextID:int = 1
        Graph.IDsUsed = set()

    def addNode(self,name=None, id=None)->int: 
        """ Add a new Node to the graph, passing a name and ID"""
        n = self.node({"name" : name},id=id,parents = [], children = [])
        self.nodeD.update({n.nodeID : n})
        return n.nodeID
        
    def addEdge(self,start,end,name=None,id=None)->int|None:
        """ Add a new edge to the graph, passing a name and ID"""
        #standard n-n edge
        if start in self.nodeD and end in self.nodeD:
            #create a new one
            e = self.edge(start,end,{"name":name},id=id)
            
            #Tell the nodes they have new edges
            self.nodeD[start].startsEdges.append(e.edgeID)
            self.nodeD[end].endsEdges.append(e.edgeID)
            
            #Store the nodes on the edge
            e.startNodes.append(start)
            e.endNodes.append(end)
            
            #Add to the graph's edge Dict
            self.edgeD.update({e.edgeID:e})
            return e.edgeID
        
        #check for a hyperedge create. NB: This is _not_ a new edge, just additional starts and ends
        #    and update metadata
        #In the editor, this will require adding an additional arc to the edge at (segment:proportion)
        #TODO: should this not be a separate method addToEdge(), since the edge itself already exists? Semantically cleaner, I think?
        #   This is easier? No additional logic required?
        
        # edge -> node
        if start in self.edgeD and end in self.nodeD:
            e = self.edgeD[start]
            if name:
                e.updateMeta([{'name':name}])
            e.endNodes.append(end)
            self.nodeD[end].endsEdges.append(e.edgeID)
            return e.edgeID

        #node -> edge
        if start in self.nodeD and end in self.edgeD:    
            e = self.edgeD[end]
            if name:
                e.updateMeta([{'name':name}])
            e.startNodes.append(start)
            self.nodeD[start].startsEdges.append(e.edgeID)     
            return e.edgeID
        
        #edge1 -> edge2 not allowed (requires merging 2 edges
        if start in self.edgeD and end in self.edgeD:
            print(f"***Error adding edge: edge->edge connections {start}->{end} require merging edges - not allowed")
            return None
        #else:
        print(f"***Error adding edge: No nodes found for edge {start}->{end}")
        return None
            
    def delNodeFromEdge(self,nodeID:int, edgeID:int)->bool:
        """ For a hyperEdge, remove a node, so long as it is not the only start/ end node """

        if nodeID in self.edgeD[edgeID].startNodes:
            if len(self.edgeD[edgeID].startNodes) > 1:
                #Not the last node, OK to delete
                #Tell the node:
                self.nodeD[nodeID].startsEdges.remove(edgeID)
                self.edgeD[edgeID].startNodes.remove(nodeID)
                return True
            else:
                print(f"coreGraph Error - cannot delete the last start node {nodeID} for edge {edgeID}")
                return False

        elif nodeID in self.edgeD[edgeID].endNodes:
            if len(self.edgeD[edgeID].endNodes) > 1:
                #Not the last node, OK to delete
                self.nodeD[nodeID].endsEdges.remove(edgeID)
                self.edgeD[edgeID].endNodes.remove(nodeID)
                return True
            else:
                print(f"coreGraph Error - cannot delete the last end node {nodeID} for edge {edgeID}")
                return False
        else:
            print(f"coreGraph Error - node {nodeID} not part of {edgeID}")
            return False

    
    def delNode(self,nodeID:int):
        """ Delete a node. If the node is the only start/ end for an edge, 
            the edge is deleted too
        """
        #print(nodeID)
        if nodeID in self.nodeD:
            n = self.nodeD[nodeID]
            #print(f"In coreGraph \n{self =}")
            #check for edges where this is a start/ end
            stEd = copy.deepcopy(n.startsEdges)
            for stEdge in stEd:
                if len(self.edgeD[stEdge].startNodes) == 1:
                    #This node is the *only* start, so delete the edge
                    self.delEdge(stEdge)
                else: #remove this node from the startlist
                    self.edgeD[stEdge].startNodes.remove(nodeID)
            
            enEd = copy.deepcopy(n.endsEdges)
            for endEdge in enEd:
                if len(self.edgeD[endEdge].endNodes) == 1:
                    #This is the *only* node ending edge
                    self.delEdge(endEdge)
                else: #remove from the endlist
                    self.edgeD[endEdge].endNodes.remove(nodeID)
            
            #Check and relink for parents/children
            for p in self.nodeD[nodeID].parents:
                self.nodeD[p].delChild(nodeID)
                for c in self.nodeD[nodeID].children:
                    self.nodeD[p].addChild(c)

            #Reparent to "grandparents"
            for c in self.nodeD[nodeID].children:
                self.nodeD[c].delParent(nodeID)
                for gp in self.nodeD[nodeID].parents:
                    self.nodeD[c].addParent(gp)

               
            #delete the node
            Graph.IDsUsed.remove(nodeID)
            self.nodeD.pop(nodeID)
        else:
            print(f"coreGraph *** Error Can't delete {delNode =} - does not exist")
            return

    def delEdge(self,edgeID:int):
        """delete an Edge, inc updating all the reverse lists"""
        #Note - for graphics, check for additional sub arcs starting or ending at the edge to be deleted
        
        if edgeID in self.edgeD:
            e = self.edgeD[edgeID]
            #remove from nodeLists:
            for StNode in e.startNodes:
                self.nodeD[StNode].startsEdges.remove(edgeID)
            for EndNode in e.endNodes:
                self.nodeD[EndNode].endsEdges.remove(edgeID)
            Graph.IDsUsed.remove(edgeID)
            self.edgeD.pop(edgeID)
        else:
            print(f"***Error deleting edge <{edgeID}> - does not exist")

    def updateEdge(self, edgeID:int ,oldID:int, end:str, newID:int):
        """ Allows an edge to be moved from one node to another.
            Relinks `edgeID` from oldID (node) to newID (node) at end ("start" or "end" )
        """
        if not end in ["start", "end"]:
            #TODO: make this an exception
            print(f"error - end must be 'start' or 'end' , not '{end}'")
            return None
        if edgeID in self.edgeD:
            e = self.edgeD[edgeID]
        else:
            print(f"***Error updating edge <{edgeID}> - does not exist")
            return None
        
        if oldID not in self.nodeD:
            print(f"***Error updating edge <{edgeID}> - node {oldID = } does not exist")
            return None            

        if newID not in self.nodeD:
            print(f"***Error updating edge <{edgeID}> - node {newID = } does not exist")
            return None
        
        if end == "start":
            #Unlink old node:
            self.nodeD[oldID].startsEdges.remove(edgeID)
            e.startNodes.remove(oldID)
            #Relink newnode:
            self.nodeD[newID].startsEdges.append(edgeID)
            e.startNodes.append(newID)
        else: #end
            #Unlink old node:
            self.nodeD[oldID].endsEdges.remove(edgeID)
            e.endNodes.remove(oldID)
            #Relink newnode:
            self.nodeD[newID].endsEdges.append(edgeID)
            e.endNodes.append(newID)
        return True
    
    def resetParents(self, nodeID:int, parentList):
        self.nodeD[nodeID].parents = parentList
    
    def resetChildren(self, nodeID:int, childrenList):
        self.nodeD[nodeID].children = childrenList

    def addNodeChild(self,nodeID:int, childID:int):
        self.nodeD[nodeID].addChild(childID)

    def getDescendents(self, nodeID):
            #gets children and subsequent generations
            """ Return a list of all children and childrens children etc """
            descendants = []
            for c in self.nodeD[nodeID].children:
                descendants.append(c)
                descendants.extend(self.getDescendents(c))
            return descendants