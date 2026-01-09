
from coreGraph02 import Graph

g:Graph = Graph()
def test1():
    global g
    print("Test 1\n","="*50)

    #print(g)
    for i in range(5):
        print("node" ,i, " as", {g.addNode(f"n{i}")}  )

    #print(g)
    #ordinary edges
    for i in range(3):
        print(f"edge {i} as", g.addEdge(i,i+1,f"e{i}->{i+1}"))

    #hyperedge
    g.addEdge(5,2,'5-2 (edge->node')

    g.addEdge(0,6, "0-6 (node->edge)")

    g.addEdge(5,6,'5-6 (e-e) error')

    #invalid edge
    g.addEdge(99,98,"Invalid")
    print(g)
    print("\nDeleting edge 5:")
    g.delEdge(5)
    print(g)
    
    print("Deleting nodes:\n 2 is only node both ends: (Edge 7 & 6 should both go)")
    g.delNode(2)
    print(g)
    
    e01 = g.addEdge(0,1,"e01:0-1")
    e13 = g.addEdge(1,3,"e13:1-3")
    e04 = g.addEdge(0,4,"e04:0-4")
    print(g)
    #Hyperedges
    he1 = g.addEdge(e01,3,f"{e01}-3 (01-3)")
    he2 = g.addEdge(4,e13,f"4-{e13} (1-34)")
    print(f"Adding hyper edges\n{g}")
    #Now deleting node 1 should leave 0-3, 0-4 and 4-3
    g.delNode(1)
    print(f"deleting node 1 should leave 0-3, 0-4 and 4-3\n{g}")
    
    #Update Edge
    #def updateEdge(self, edgeID:int ,oldID:int, end:str, newID:int):
    #start (0,1) -> (3,1)
    print(f" start (0,1) -> (3,1) on edge {e01}")
    g.updateEdge(e01,0,"start",3)
    print(f"{e01} = (3,1)?")
    #end
    
    print(f"\nFinal state \n{g}")
    
    return g



def test2():
    """
        https://en.wikipedia.org/wiki/Hypergraph
    """
    print("\n\nTest2")
    g2:Graph = Graph()
    for i in range(1,7):
        print(g2.addNode(str(i)))
    
    a1 = g2.addEdge(0,1,'a1')
    a2 = g2.addEdge(1,2,'a2')
    a3 = g2.addEdge(2,0,'a3')
    a4 = g2.addEdge(1,3,'a4')
    g2.addEdge(2,a4)
    g2.addEdge(a4,4)
    a5 = g2.addEdge(2,5,'a5')
    g2.addEdge(4,a5)
    
    print(g2)

def test3Update():
    print("T1:  1-2 ==> 1-3 ")
    g3:Graph = Graph()
    n0 = g3.addNode("0")
    n1 = g3.addNode("1")
    n2 = g3.addNode("2")
    n3 = g3.addNode("3")
    
    e1 = g3.addEdge(n1,n2)
    print(g3)
    print(g3.updateEdge(e1 ,oldID=2, end="end", newID=3))
    print(g3)
    print(g3.updateEdge(e1 ,oldID=1, end="start", newID=0))
    print(g3)
    
    
def test41_MultiEdgeNodesStarts():
    print("test41_MultiEdgeNodesStarts") 
    g4 = Graph()
    numEdges = 5
    for i in range(numEdges+1):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )
        
    #Multiple starts
    for i in range(1,numEdges+1):
        g4.addEdge(0,i,f"0->{i}")
    
    print(f"Before:\n{g4}")
    g4.delNode(0)
    print(f"After:\n{g4}")

def test42_MultiEdgeNodesEnds():
    print("test42_MultiEdgeNodes ENDS") 
    g4 = Graph()
    numEdges = 5
    for i in range(numEdges+1):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )
        
    #Multiple starts
    for i in range(0,numEdges):
        g4.addEdge(i,numEdges,f"{i}->{numEdges}")
    
    print(f"Before:\n{g4}")
    g4.delNode(numEdges)
    print(f"After:\n{g4}")

def test51_UpdateEdgeEnds():
    print("test51_UpdateEdgeEnds STARTS") 
    g4 = Graph()
 
    for i in range(3):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )
        
    for i in range(0,1):
        g4.addEdge(i,1,f"{i}-1")
    print(f"Before:\n{g4}")
    
    #updateEdge(self, edgeID:int ,oldID:int, end:str, newID:int)
    g4.updateEdge(3,0,"start",2)
    print(f"After 0-1 >>> 2-1 \n{g4}")

def test52_UpdateEdgeEnds():
    print("test51_UpdateEdgeEnds ENDS") 
    g4 = Graph()
 
    for i in range(3):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )
        
    for i in range(0,1):
        g4.addEdge(i,1,f"{i}-1")
    print(f"Before:\n{g4}")
    
    #updateEdge(self, edgeID:int ,oldID:int, end:str, newID:int)
    g4.updateEdge(3,1,"end",2)
    print(f"After 0-1 >>> 0-2 \n{g4}")

def test61_DeleteEdge():
    print("test51_UpdateEdgeEnds ENDS") 
    g4 = Graph()
 
    for i in range(3):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )

    eList = []   
    for i in range(0,1):
        eList.append(g4.addEdge(i,1,f"{i}-1"))
    print(f"Before:\n{g4}")
    
    #updateEdge(self, edgeID:int ,oldID:int, end:str, newID:int)
    g4.delEdge(eList[0])
    print(f"After edge {eList[0]} removed \n{g4}")

def test62_MultiEdge1NodeStartDeleteEdge():
    print("test62_MultiEdge1NodeStartDeleteEdge") 
    g4 = Graph()
    numEdges = 5
    for i in range(numEdges+1):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )
        
    #Multiple starts
    eList = []
    for i in range(1,numEdges+1):
        eList.append(g4.addEdge(0,i,f"0->{i}"))
    
    print(f"Before:\n{g4}")
    g4.delEdge(eList[2])
    print(f"After deleting edge {eList[2]}:\n{g4}")

def test63_MultiEdge1NodeENDDeleteEdge():
    print("test63_MultiEdge1NodeENDDeleteEdge") 
    g4 = Graph()
    numEdges = 5
    for i in range(numEdges+1):
        g4.addNode(f"n{i}")
        #print("node" ,i, " as", {g4.addNode(f"n{i}")}  )
        
    #Multiple starts
    eList = []
    for i in range(0,numEdges):
        eList.append(g4.addEdge(i,numEdges,f"{i}->{numEdges+1}") )
    
    print(f"Before:\n{g4}")
    g4.delEdge(eList[2])
    print(f"After deleting edge {eList[2]}:\n{g4}")


test63_MultiEdge1NodeENDDeleteEdge()
#test62_MultiEdge1NodeStartDeleteEdge()
#test61_DeleteEdge()
#test51_UpdateEdgeEnds()
#test52_UpdateEdgeEnds()
#test41_MultiEdgeNodesStarts()
#test42_MultiEdgeNodesEnds()

#test3Update()
    
#test2()
#test1()



    
