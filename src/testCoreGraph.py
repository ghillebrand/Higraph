""" Test the core graph model"""
#TODO: put in more `assert` statements

from coreGraph import Graph


def test1():
    g:Graph = Graph()
    g.resetIDs()
    print("Test 1\n","="*50)

    #print(g)
    for i in range(5):
        print("node" ,i, " as", {g.addNode(f"n{i}")}  )

    #ordinary edges
    for i in range(3):
        print(f"edge {i} as", g.addEdge(i,i+1,f"e{i}->{i+1}"))
    expG1 = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[5],endsEdges:[], parents:[], children:[]
, 1: nodeID:1,metadata:{'name': 'n1'},startsEdges:[6],endsEdges:[5], parents:[], children:[]
, 2: nodeID:2,metadata:{'name': 'n2'},startsEdges:[7],endsEdges:[6], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[],endsEdges:[7], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[],endsEdges:[], parents:[], children:[]
}
edges:
{5: edgeID:5,metadata:{'name': 'e0->1'},startNodes:[0],endNodes:[1]
, 6: edgeID:6,metadata:{'name': 'e1->2'},startNodes:[1],endNodes:[2]
, 7: edgeID:7,metadata:{'name': 'e2->3'},startNodes:[2],endNodes:[3]
}"""
    #print(g)
    assert expG1 == str(g),  f"Expected:\n{expG1}\nGot\n{g}"

    #hyperedge
    g.addEdge(5,2,'5-2 (edge->node')
    #print(g)
    expG2 = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[5],endsEdges:[], parents:[], children:[]
, 1: nodeID:1,metadata:{'name': 'n1'},startsEdges:[6],endsEdges:[5], parents:[], children:[]
, 2: nodeID:2,metadata:{'name': 'n2'},startsEdges:[7],endsEdges:[6, 5], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[],endsEdges:[7], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[],endsEdges:[], parents:[], children:[]
}
edges:
{5: edgeID:5,metadata:{'name': '5-2 (edge->node'},startNodes:[0],endNodes:[1, 2]
, 6: edgeID:6,metadata:{'name': 'e1->2'},startNodes:[1],endNodes:[2]
, 7: edgeID:7,metadata:{'name': 'e2->3'},startNodes:[2],endNodes:[3]
}"""
    assert expG2 == str(g)

    g.addEdge(0,6, "0-6 (node->edge)")
    #print(g)
    expG3 = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[5, 6],endsEdges:[], parents:[], children:[]
, 1: nodeID:1,metadata:{'name': 'n1'},startsEdges:[6],endsEdges:[5], parents:[], children:[]
, 2: nodeID:2,metadata:{'name': 'n2'},startsEdges:[7],endsEdges:[6, 5], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[],endsEdges:[7], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[],endsEdges:[], parents:[], children:[]
}
edges:
{5: edgeID:5,metadata:{'name': '5-2 (edge->node'},startNodes:[0],endNodes:[1, 2]
, 6: edgeID:6,metadata:{'name': '0-6 (node->edge)'},startNodes:[1, 0],endNodes:[2]
, 7: edgeID:7,metadata:{'name': 'e2->3'},startNodes:[2],endNodes:[3]
}"""
    assert expG3 == str(g)

    print("Error expected:")
    g.addEdge(5,6,'5-6 (e-e) error')

    #invalid edge
    print("Error expected:")
    g.addEdge(99,98,"Invalid")
    #print(g)

    #print("\nDeleting edge 5:")
    g.delEdge(5)
    #print(g)
    expG4 = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[6],endsEdges:[], parents:[], children:[]
, 1: nodeID:1,metadata:{'name': 'n1'},startsEdges:[6],endsEdges:[], parents:[], children:[]
, 2: nodeID:2,metadata:{'name': 'n2'},startsEdges:[7],endsEdges:[6], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[],endsEdges:[7], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[],endsEdges:[], parents:[], children:[]
}
edges:
{6: edgeID:6,metadata:{'name': '0-6 (node->edge)'},startNodes:[1, 0],endNodes:[2]
, 7: edgeID:7,metadata:{'name': 'e2->3'},startNodes:[2],endNodes:[3]
}"""
    assert expG4 == str(g)
    
    #print("Deleting nodes:\n 2 is only node both ends: (Edge 7 & 6 should both go)")
    g.delNode(2)
    #print(g)
    
    e01 = g.addEdge(0,1,"e01:0-1")
    e13 = g.addEdge(1,3,"e13:1-3")
    e04 = g.addEdge(0,4,"e04:0-4")
    #print("G5")
    #print(g)
    expG5 = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[8, 10],endsEdges:[], parents:[], children:[]
, 1: nodeID:1,metadata:{'name': 'n1'},startsEdges:[9],endsEdges:[8], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[],endsEdges:[9], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[],endsEdges:[10], parents:[], children:[]
}
edges:
{8: edgeID:8,metadata:{'name': 'e01:0-1'},startNodes:[0],endNodes:[1]
, 9: edgeID:9,metadata:{'name': 'e13:1-3'},startNodes:[1],endNodes:[3]
, 10: edgeID:10,metadata:{'name': 'e04:0-4'},startNodes:[0],endNodes:[4]
}"""
    assert expG5 == str(g)

    #Hyperedges
    he1 = g.addEdge(e01,3,f"{e01}-3 (01-3)")
    he2 = g.addEdge(4,e13,f"4-{e13} (1-34)")
    #print(f"Adding hyper edges\n{g}")
    #Now deleting node 1 should leave 0-3, 0-4 and 4-3
    g.delNode(1)
    #print(f"deleting node 1 should leave 0-3, 0-4 and 4-3\n{g}")
    expG6 = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[8, 10],endsEdges:[], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[],endsEdges:[9, 8], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[9],endsEdges:[10], parents:[], children:[]
}
edges:
{8: edgeID:8,metadata:{'name': '8-3 (01-3)'},startNodes:[0],endNodes:[3]
, 9: edgeID:9,metadata:{'name': '4-9 (1-34)'},startNodes:[4],endNodes:[3]
, 10: edgeID:10,metadata:{'name': 'e04:0-4'},startNodes:[0],endNodes:[4]
}"""
    assert expG6 == str(g)

    #Update Edge
    #def updateEdge(self, edgeID:int ,oldID:int, end:str, newID:int):
    #start (0,1) -> (3,1)
    #print(f" start (0,1) -> (3,1) on edge {e01}")
    g.updateEdge(e01,0,"start",3)
    #print(f"{e01} = (3,1)?")
    #end
    
    #print(f"\nFinal state \n{g}")
    expGFin = """nodes:
{0: nodeID:0,metadata:{'name': 'n0'},startsEdges:[10],endsEdges:[], parents:[], children:[]
, 3: nodeID:3,metadata:{'name': 'n3'},startsEdges:[8],endsEdges:[9, 8], parents:[], children:[]
, 4: nodeID:4,metadata:{'name': 'n4'},startsEdges:[9],endsEdges:[10], parents:[], children:[]
}
edges:
{8: edgeID:8,metadata:{'name': '8-3 (01-3)'},startNodes:[3],endNodes:[3]
, 9: edgeID:9,metadata:{'name': '4-9 (1-34)'},startNodes:[4],endNodes:[3]
, 10: edgeID:10,metadata:{'name': 'e04:0-4'},startNodes:[0],endNodes:[4]
}"""
    assert expGFin == str(g)
    print("Test 1 - basic node & edge manipulation - passed")
    
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

def test7_BasicBlobs():
    g = Graph()
    for i in range(3):
        g.addNode(i)

    g.nodeD[0].addChild(1)
    g.nodeD[1].addChild(2)
    g.nodeD[1].addParent(0)
    g.nodeD[2].addParent(1)
    
    expG71 = """nodes:
{0: nodeID:0,metadata:{'name': 0},startsEdges:[],endsEdges:[], parents:[], children:[1]
, 1: nodeID:1,metadata:{'name': 1},startsEdges:[],endsEdges:[], parents:[0], children:[2]
, 2: nodeID:2,metadata:{'name': 2},startsEdges:[],endsEdges:[], parents:[1], children:[]
}
edges:
{}"""
    assert expG71 == str(g)

    g.delNode(1)
    #print(g)

    expG72="""nodes:
{0: nodeID:0,metadata:{'name': 0},startsEdges:[],endsEdges:[], parents:[], children:[2]
, 2: nodeID:2,metadata:{'name': 2},startsEdges:[],endsEdges:[], parents:[0], children:[]
}
edges:
{}"""
    assert expG72 == str(g)
    print("Test 7 test7_BasicBlobs passed")


print("="*50)

test7_BasicBlobs()

#test63_MultiEdge1NodeENDDeleteEdge()
#test62_MultiEdge1NodeStartDeleteEdge()
#test61_DeleteEdge()
#test51_UpdateEdgeEnds()
#test52_UpdateEdgeEnds()
#test41_MultiEdgeNodesStarts()
#test42_MultiEdgeNodesEnds()
#test3Update() 
#test2()
test1()



    
