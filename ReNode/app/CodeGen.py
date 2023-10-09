from collections import defaultdict
import json
import re
import enum

class CodeGenerator:
    def __init__(self):
        self.generated_code = ""
        self.graphsys = None

        self.serialized_graph = None
        self.visited = None

    def getNodeLibData(self,cls):
        return self.graphsys.nodeFactory.getNodeLibData(cls)

    def generateProcess(self):
        file_path = "./session.json"
        try:
            with open(file_path) as data_file:
                layout_data = json.load(data_file)
        except Exception as e:
            layout_data = None
            print('Cannot read data from file.\n{}'.format(e))

        if not layout_data:
            return

        self.serialized_graph = layout_data
        entrys = self.findNodesByClass("events.onStart")
        code = "generated:"
        for nodeid in entrys:
            self.visited = set()
            code += "\n" + self.generateCode(nodeid)
        print(code)


    def generateCode(self, id):
        if id in self.visited: return ""
        self.visited.add(id)

        libNode = self.getNodeLibData(self.serialized_graph['nodes'][id]['class_'])
        codeprep = libNode['code']

        execDict = self.getExecPins(id)
        inputDict = self.getInputs(id)
        
        #process inputs
        for i,(k,v) in enumerate(libNode.get('inputs',{}).items()):
            if not inputDict.get(k): continue

            outcode = self.generateCode(inputDict.get(k))
            print(f"{i} < {k} returns: {outcode}")
            codeprep = codeprep.replace(f'@in.{i+1}',outcode)
            pass

        #process outputs
        for i,(k,v) in enumerate(libNode.get('outputs',{}).items()):
            #here we can update custom output
            
            if not execDict.get(k): continue

            outcode = self.generateCode(execDict.get(k))
            print(f"{i} > {k} returns: {outcode}")
            codeprep = codeprep.replace(f'@out.{i+1}',outcode)
            pass
    
        #postcheck outputs
        if "@out." in codeprep:
            codeprep = re.sub(r"@out.\d+","",codeprep)

        return codeprep

    # returns map: key
    def getExecPins(self,id):
        return self.getConnectionsMap(self.ConnectionType.Output,id)
    
    def getInputs(self,id):
        return self.getConnectionsMap(self.ConnectionType.Input,id)

    class ConnectionType(enum.Enum):
        Input = 0,
        Output = 1

    def getConnectionsMap(self,ct : ConnectionType, nodeid):
        connections = self.serialized_graph['connections']
        searchedKey = "out" if ct == self.ConnectionType.Output else "in"
        invertKey = "in" if ct == self.ConnectionType.Output else "out"
        dictret = {}
        for itm in connections:
            if (itm[searchedKey][0] == nodeid):
                dictret[itm[searchedKey][1]] = itm[invertKey][0]
        
        return dictret

    def findConnections(self,contyp : ConnectionType,nodeid, retFirst = False):
        connections = self.serialized_graph['connections']
        searchedKey = "out" if contyp == self.ConnectionType.Output else "in"
        invertKey = "in" if contyp == self.ConnectionType.Output else "out"
        listret = list()
        for itm in connections:
            if (itm[searchedKey][0] == nodeid):
                listret.append(itm[invertKey][0])
        if retFirst:
            if len(listret) > 0:
                return listret[0]
            else:
                return None
        else:
            return listret
    
    def findConnection(self,contype : ConnectionType,nodeid):
        return self.findConnections(contype,nodeid,True)

    def findNodesByClass(self, class_to_find):
        node_ids = []
        for node_id, node_data in self.serialized_graph["nodes"].items():
            if node_data["class_"] == class_to_find:
                node_ids.append(node_id)
        return node_ids
