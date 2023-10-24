from collections import defaultdict
import json
import re
import enum

class CodeGenerator:
    def __init__(self):
        self.generated_code = ""
        self.graphsys = None

        self.serialized_graph = None

        self._addComments = False

        self.aliasVarNames = {}
        self.typesVarNames = {}
        # те переменные, которые хоть раз используют установку или получение должны быть сгенерены
        self.localVariablesUsed = set()

    def getNodeLibData(self,cls):
        return self.graphsys.nodeFactory.getNodeLibData(cls)

    def getVariableDict(self) -> dict:
        return self.graphsys.variable_manager.variables

    def generateProcess(self,addComments=False):
        self._addComments = addComments

        """ file_path = "./session.json"
        try:
            with open(file_path) as data_file:
                layout_data = json.load(data_file)
        except Exception as e:
            layout_data = None
            print('Cannot read data from file.\n{}'.format(e))"""
        
        layout_data = self.graphsys.graph._serialize(self.graphsys.graph.all_nodes())

        if not layout_data:
            return

        self.serialized_graph = layout_data
        entrys = self.findNodesByClass("events.onStart")
        code = "generated:"

        self.aliasVarNames = {}
        self.typesVarNames = {}

        for vcat,vval in self.getVariableDict().items():
            for i, (k,v) in enumerate(vval.items()):
                self.typesVarNames[v['systemname']] = v['type']

                if vcat=='local':
                    self.aliasVarNames[v['systemname']] = f"_LVAR{i+1}"
                elif vcat=='class':
                    self.aliasVarNames[v['systemname']] = f"classMember_{i+1}"
                else:
                    continue

        # generate classvars
        for vid,vdat in self.getVariableDict().get('class',{}).items():
            varvalue = self.updateValueDataForType(vdat["value"],vdat['type'])
            code += "\n" + f'var({self.aliasVarNames[vdat["systemname"]]},{varvalue});'

        for nodeid in entrys:
            self.localVariablesUsed = set()
            code += "\n" + self.formatCode(self.generateCode(nodeid))
        print(code)

    def formatCode(self, instructions):
        def make_prefix(level):
            return ' ' * 4 * level

        def normalize_brackets(text):
            text = re.sub(r'{\s*', '{\n', text)
            text = re.sub(r'\s*}', '\n}', text)
            text = re.sub(r'{\s*}', '{}', text)
            return text

        def normalize_command_structure(text):
            text = re.sub(r'if\s*\((.*)\)\s*then\s*{', 'if (\\1) then {', text)
            text = re.sub(r'}\s*else\s*{', '} else {', text)
            text = re.sub(r'if\s*\((.*)\)\s*exitwith\s*{', 'if (\\1) exitwith {', text)
            text = re.sub(r'while\s*\{\s*(.*[^\s]*)\s*\}\s*do\s*{', 'while {\\1} do {', text)
            return text

        def normalize_commas(text):
            text = re.sub(r', *([^,\n]+)', ', \\1', text)
            text = re.sub(r'\s*,', ',', text)
            return text

        def set_indents(text):
            level = 0
            empty_line_count = 0
            delete_next_empty_line = False
            lines = text.split('\n')
            result = []
            for line in lines:
                if line == '':
                    if delete_next_empty_line:
                        continue
                    empty_line_count += 1
                    if empty_line_count > 1:
                        continue
                else:
                    empty_line_count = 0
                delete_next_empty_line = False
                prefix = make_prefix(level)
                open_brackets = line.split('[')
                close_brackets = line.split(']')
                open_braces = line.split('{')
                close_braces = line.split('}')
                open_bracket_count = len(open_brackets)
                close_bracket_count = len(close_brackets)
                open_brace_count = len(open_braces)
                close_brace_count = len(close_braces)
                is_open_block = len(open_brackets[0].split(']')) > 1 or len(open_braces[0].split('}')) > 1
                if open_bracket_count > close_bracket_count or open_brace_count > close_brace_count:
                    level += 1
                    delete_next_empty_line = True
                elif open_bracket_count < close_bracket_count or open_brace_count < close_brace_count:
                    level = max(0, level - 1)
                    prefix = make_prefix(level)
                elif is_open_block:
                    prefix = make_prefix(level - 1)
                result.append(prefix + line)
            result = [line for line in result if line is not None]
            return '\n'.join(result).strip()

        def pretty(text):
            output = re.sub(r'\/\/[\s\/]*(.*)', r'# \1', text)
            output = normalize_brackets(output)
            output = normalize_commas(output)
            output = normalize_command_structure(output)
            output = re.sub(r' {2,}', ' ', output)
            output = re.sub(r'; *([^\n]+)', r';\n\1', output)
            output = re.sub(r'[\s;]*;', ';', output)
            output = re.sub(r'\(\s*(.*[^\s])\s*\)', r'(\1)', output)
            output = set_indents(output)
            return output

        result = pretty(instructions)
        return result

    def generateCode(self, id,fromid=None,path=None):

        if not path:
            path = []

        if id in path: return "CICLE_HANDLED"
        path.append(id)

        nodeObject = self.serialized_graph['nodes'][id]
        libNode = self.getNodeLibData(nodeObject['class_'])
        codeprep = libNode['code']
        if self._addComments:
            codeprep = f"//[{id}]:{nodeObject['class_']}\n" + codeprep

        execDict = self.getExecPins(id)
        inputDict = self.getInputs(id)
        
        inputsDictFromLib = libNode.get('inputs',{}).items()

        #if codeprep == RUNTIME them get nodeObject['custom']['code']
        isLocalVar = codeprep == "RUNTIME"
        nameid = None
        if isLocalVar: 
            codeprep = nodeObject['custom']['code']
            nameid = nodeObject['custom']['nameid']
            self.localVariablesUsed.add(nameid)
            codeprep = codeprep.replace(nameid,self.aliasVarNames[nameid])
            #find key if not "nameid" and "code"
            addedName = next((key for key in nodeObject['custom'].keys() if key not in ['nameid','code']),None)
            if addedName:
                inputsDictFromLib = list(inputsDictFromLib)
                inputsDictFromLib.append((addedName,{}))

        #process inputs
        for i,(k,v) in enumerate(inputsDictFromLib):
            inpId = inputDict.get(k)
            if (inpId == fromid): continue #do not generate from prev node
            
            if not inpId:
                inlineValue = nodeObject['custom'].get(k,' NULL ')
                inlineValue = self.updateValueDataForType(inlineValue,self.typesVarNames.get(nameid,None))
                print(f"{i} < {k} is not defined, custom: {inlineValue}")
                codeprep = codeprep.replace(f'@in.{i+1}', f"{inlineValue}" )
                continue

            outcode = self.generateCode(inpId,id,path)
            print(f"{i} < {k} returns: {outcode}")
            codeprep = codeprep.replace(f'@in.{i+1}',outcode)
            pass

        #process outputs
        for i,(k,v) in enumerate(libNode.get('outputs',{}).items()):
            #here we can update custom output
            
            if not execDict.get(k): continue

            outcode = self.generateCode(execDict.get(k),id,path)
            print(f"{i} > {k} returns: {outcode}")
            codeprep = codeprep.replace(f'@out.{i+1}',outcode)
            pass

        #postcheck outputs
        if "@out." in codeprep:
            codeprep = re.sub(r"@out.\d+","",codeprep)

        if "@initvars" in codeprep:
            initlocalvars = ""
            for k,vdat in self.getVariableDict().get('local',{}).items():
                if not k in self.localVariablesUsed: continue
                lval = self.updateValueDataForType(vdat['value'],vdat['type'])
                initlocalvars += f'\nprivate {self.aliasVarNames[vdat["systemname"]]} = {lval};'
            codeprep = codeprep.replace("@initvars",initlocalvars)

        path.pop()

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

    def updateValueDataForType(self,value,type):
        if not type: return value
        if type == "string": 
            return "\"" + value.replace("\"","\"\"") + "\""
        
        return value