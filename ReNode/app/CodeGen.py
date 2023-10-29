from collections import defaultdict
import json
import re
import enum
import asyncio

class GeneratedVariable:
    def __init__(self,locname,definedNodeId,acceptedPaths = None):
        self.localName = locname 
        self.definedNodeId = definedNodeId
        self.acceptedPaths = acceptedPaths
        self.isUsed = False
        
        self.active = True
        self.fromName = None

class CodeGenerator:
    def __init__(self):
        self.generated_code = ""
        self.graphsys = None

        self.serialized_graph = None

        self._addComments = False # Добавляет мета-информацию внутрь кодовой структуры

        self._debug_info = True # Включать только для отладки: переименовывает комменты и имена узлов для проверки правильности генерации

        #TODO: need write
        self._optimizeCodeSize = False # включает оптимизацию кода. Меньше разрмер 

        self.aliasVarNames = {} # преобразовванные имена переменныъ
        self.typesVarNames = {} # тип данных переменной
        self.varCategoryInfo = {} # дикт с категориями переменных (класс, локальная)
        # те переменные, которые хоть раз используют установку или получение должны быть сгенерены
        self.localVariablesUsed = set()

    def getNodeLibData(self,cls):
        return self.graphsys.nodeFactory.getNodeLibData(cls)

    def getVariableDict(self) -> dict:
        return self.graphsys.variable_manager.variables

    def generateProcess(self,addComments=True):
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
        self.varCategoryInfo = {}

        self._finalizedCode = {} #k,v: nodeid, code (only finalized) !(work in _optimizeCodeSize)

        for vcat,vval in self.getVariableDict().items():
            for i, (k,v) in enumerate(vval.items()):
                self.typesVarNames[v['systemname']] = v['type']
                
                self.varCategoryInfo[v['systemname']] = vcat

                if vcat=='local':
                    self.aliasVarNames[v['systemname']] = f"_LVAR{i+1}"
                    #self.aliasVarNames[v['systemname']] = self.transliterate(v['name'])
                elif vcat=='class':
                    self.aliasVarNames[v['systemname']] = f"classMember_{i+1}"
                    #self.aliasVarNames[v['systemname']] = self.transliterate(v['name'])
                else:
                    continue

        # generate classvars
        for vid,vdat in self.getVariableDict().get('class',{}).items():
            varvalue = self.updateValueDataForType(vdat["value"],vdat['type'])
            
            if self._addComments:
                code += f"\n//cv_init:{vdat['name']}"
            code += "\n" + f'var({self.aliasVarNames[vdat["systemname"]]},{varvalue});'
            
        self._renamed = set()
        self._indexer = 0

        #debug reset node disables
        self._resetNodesDisable()

        for nodeid in entrys:
            self.localVariablesUsed = set()
            #data,startPoints = self.generateDfs(nodeid)
            #print(data)
            #code += "\n" + self.buildCodeFromData(data,startPoints)
            code += "\n" + self.formatCode(self.generateCode(nodeid))
        print(code)
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(code)

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
            #output = re.sub(r'\/\/[\s\/]*(.*)', r'# \1', text)
            output = normalize_brackets(text)
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

    #region Obsoleted
    
    def generateBfs(self, start_node_id):
        from collections import deque
        visited_nodes = set()
        result = []

        queue = deque()
        queue.append(start_node_id)
        visited_nodes.add(start_node_id)

        while queue:
            node_id = queue.popleft()
            node_object = self.serialized_graph['nodes'][node_id]

            exec_dict = self.getExecPins(node_id)
            input_dict = self.getInputs(node_id)

            node_info = {
                'node_id': node_id,
                'class': node_object['class_']
            }

            children = []

            for _, child_id in input_dict.items():
                if child_id not in visited_nodes:
                    queue.append(child_id)
                    visited_nodes.add(child_id)
                    children.append({'node_id': child_id, 'class': self.serialized_graph['nodes'][child_id]['class_']})

            for _, child_id in exec_dict.items():
                if child_id not in visited_nodes:
                    queue.append(child_id)
                    visited_nodes.add(child_id)
                    children.append({'node_id': child_id, 'class': self.serialized_graph['nodes'][child_id]['class_']})

            node_info['children'] = children
            result.append(node_info)

        return result

    def generateDfs(self,node_id, visited_nodes=None,baseRef=None,startPoints = None):
        if not visited_nodes:
            visited_nodes = set()
        
        if not startPoints:
            startPoints = []

        if node_id in visited_nodes:
            return {}

        visited_nodes.add(node_id)
        node_object = self.serialized_graph['nodes'][node_id]

        # Обходим все связи (exec и инпуты) текущего узла
        exec_dict = self.getExecPins(node_id)
        input_dict = self.getInputs(node_id)

        result = {
            'node_id': node_id,
            'class': node_object['class_'],
            'name': re.sub(r"\<[\w+\ 0-9\"\'\=\:\;\-\/]+\>","",node_object['name'])
        }
        tmap = []
        if baseRef in exec_dict.values():
            tmap.append("input")
        if baseRef in input_dict.values():
            tmap.append("output")
        if len(tmap) == 0:
            tmap.append("ERROR")

        result['type'] = ','.join(tmap)
        result['has_inputs'] = len(input_dict) > 0

        # Рекурсивно обходим дочерние узлы

        for _, child_id in input_dict.items():
            child_result = self.generateDfs(child_id, visited_nodes,node_id)
            if child_result:
                if 'children' not in result:
                    result['children'] = []
                result['children'].append(child_result)

        for _, child_id in exec_dict.items():
            child_result = self.generateDfs(child_id, visited_nodes,node_id)
            if child_result:
                if 'children' not in result:
                    result['children'] = []
                result['children'].append(child_result)


        return result, startPoints

    #endregion

    def generateCode(self, id,fromid=None,path=None,backwardConnections=None,stackedGenerated=None):

        if not path:
            path = []
            backwardConnections = []
        if not stackedGenerated:
            stackedGenerated = []

        if id in path: return "$CICLE_HANDLED$"

        #if self._finalizedCode.get(id):
        #    return f'call {self._finalizedCode[id]["value"]};'
        
        path.append(id)

        nodeObject = self.serialized_graph['nodes'][id]
        className = nodeObject['class_']
        libNode = self.getNodeLibData(className)
        codeprep = libNode['code']
        isLocalVar = codeprep == "RUNTIME"
        if self._addComments:
            if not self._debug_info:
                codeprep = f"//[{id}]:{className}\n" + codeprep
            else:
            #region debug rename nodes
                if not id in self._renamed:
                    nameseg = f'[{self._indexer}]:{className}'
                    codeprep = f'//{nameseg}\n' + codeprep
                    self.graphsys.graph.get_node_by_id(id).set_name(nameseg)
                    self._renamed.add(id)
                    self._indexer += 1
                else:
                    codeprep = f'//err_copy_gen\n' + codeprep
            #endregion

        execDict = self.getExecPins(id)
        inputDict = self.getInputs(id)
        
        inputsDictFromLib = libNode.get('inputs',{}).items()

        #if codeprep == RUNTIME them get nodeObject['custom']['code']
        if isLocalVar:
            #codeprep = nodeObject['custom']['code']
            nameid = nodeObject['custom']['nameid']
            #define variable code
            codeprep = self.getVariableCode(className,nameid)

            if self._addComments:
                if not self._debug_info:
                    codeprep = f"//[{id}]:{className}\n" + codeprep
                else:
                    #region debug rename nodes
                    nameinfo = f"[{self._indexer}]:{className}" if not id in self._renamed else "//err_copy_gen"
                    #codeprep = f'{nameinfo}\n' + codeprep
                    #endregion
            
            self.localVariablesUsed.add(nameid)
            codeprep = codeprep.replace(nameid,self.aliasVarNames[nameid])
            #find key if not "nameid" and "code"
            addedName = next((key for key in nodeObject['custom'].keys() if key not in ['nameid','code']),None)
            if addedName:
                inputsDictFromLib = list(inputsDictFromLib)
                inputsDictFromLib.append((addedName,{'type':self.typesVarNames.get(nameid,None)}))

        #process inputs
        for i,(k,v) in enumerate(inputsDictFromLib):
            inpId = inputDict.get(k)
            
            if f"@in.{i+1}" not in codeprep: continue

            # no input -> generate variable
            if not inpId:
                inlineValue = nodeObject['custom'].get(k,' NULL ')
                inlineValue = self.updateValueDataForType(inlineValue,v['type'])
                print(f"{i} < {k} is not defined, custom: {inlineValue}")
                codeprep = codeprep.replace(f'@in.{i+1}', f"{inlineValue}" )
                continue

            #stack check 
            if len(stackedGenerated) > 0:
                # ? как узнать какой элемент стека нужен?
                pat = next((it_ for it_ in stackedGenerated if it_.definedNodeId == inpId or it_.definedNodeId in path),None)
                #pat = stackedGenerated[-1] #! последний элемент не прокатит если цикл в цикле+ получение итератора верхнего цикла
                if pat and pat.definedNodeId in path:
                    # поднимаемся вверх по иерархии и находим допустимые пути
                    idBase = pat.definedNodeId
                    acp = None
                    cpyBkwrd = backwardConnections.copy()
                    cpyBkwrd.reverse()
                    for itm in cpyBkwrd:
                        if itm[0] == idBase:
                            acp = itm[3]
                            #path valid
                            if "@any" in acp:
                                acp = None
                            else:
                                #check name
                                acp = itm[1]
                                # есть ли в accepted_paths либо это этот же айди (если дургие есть)
                                if acp in itm[3] or (inpId == idBase and len(itm[3]) > 0):
                                    acp = None
                            break
                    if not acp:
                        #if idBase == fromid:
                            pat.isUsed = True
                            codeprep = codeprep.replace(f'@in.{i+1}',pat.localName)
                            continue
                        #else:    
                            #raise Exception(f"UNHANDLED CONDITION; ID MISSMATCH")
                        #    pass
                    else:
                        #! см ниже... (но с условиями)
                        node__ = self.graphsys.graph.get_node_by_id(id)
                        node__.set_disabled(True)
                        codeprep = codeprep.replace(f'@in.{i+1}',"[FAULT]")
                        codeprep = f"//ERROR GENERATOR - PATH NOT ACCEPTED \"{acp}\": {self.graphsys.graph.get_node_by_id(id).name()}" + "\n" + codeprep
                        continue
                        pass
                else:
                    #! Нельзя использовать inpId, так как на ноду id наложены ограничения из другого пути
                    node__ = self.graphsys.graph.get_node_by_id(id)
                    node__.set_disabled(True)
                    codeprep = codeprep.replace(f'@in.{i+1}',"[FAULT]")
                    codeprep = f"//ERROR STRUCTURE - WRONG REFERENCE \"{k}\": {self.graphsys.graph.get_node_by_id(inpId).name()}" + "\n" + codeprep
                    continue
            
            if (inpId == fromid): continue #do not generate from prev node

            outcode = self.generateCode(inpId,id,path,backwardConnections,stackedGenerated)
            print(f"{i} < {k} returns: {outcode}")
            if outcode == "$CICLE_HANDLED$": continue
            codeprep = codeprep.replace(f'@in.{i+1}',outcode)
            pass


        doremgenvar = False
        remCount = 0
        slotsStack = {}
        if "@genvar." in codeprep:
            clrvalList = re.findall(r'\@genvar\.(\w+\.\d+)',codeprep)
            dictValues = list(libNode.get('outputs',{}).values())
            for clrval in clrvalList:
                
                lvar = f'_gv_{len(stackedGenerated)}_{len(stackedGenerated)+1}_{hex(doremgenvar)}'
                wordpart = re.sub('\.\d+','',clrval)
                numpart = re.sub('\w+\.','',clrval)
                indexOf = int(numpart)-1 #because is not a index
                gvObj = GeneratedVariable(lvar,id)
                slotsStack[f'@{wordpart}.{numpart}'] = gvObj
                
                doremgenvar = True
                codeprep = codeprep.replace(f'@genvar.{wordpart}.{numpart}',lvar)

                #adding accepted paths
                gvObj.acceptedPaths = dictValues[indexOf]['accepted_paths']
                stackedGenerated.append(gvObj)
                remCount += 1

            print("---------> MATCHED")

        #process outputs
        for i,(k,v) in enumerate(libNode.get('outputs',{}).items()):
            #here we can update custom output
            
            if not execDict.get(k): continue

            nameprop = f"@out.{i+1}"
            stackGenDoRem = False

            #if nameprop in slotsStack:
            #    stackedGenerated.append(slotsStack[nameprop])
            #    stackGenDoRem = True

            backwardConnections.append([id,k,className,v.get('accepted_paths',['@any'])])
            outcode = self.generateCode(execDict.get(k),id,path,backwardConnections,stackedGenerated)
            backwardConnections.pop()

            #if stackGenDoRem:
            #    stackedGenerated.pop()

            print(f"{i} > {k} returns: {outcode}")
            if outcode == "$CICLE_HANDLED$": continue

            codeprep = codeprep.replace(f'@out.{i+1}',outcode)
            pass

        #postcheck
        if className == "operators.for_loop" and "@in." in codeprep:
            pass#raise Exception("UNHANDLED DEPRECATED")

        if doremgenvar:
            for i in range(1,remCount):
                stackedGenerated.pop()

        #postcheck outputs
        if "@out." in codeprep:
            codeprep = re.sub(r"@out.\d+","",codeprep)

        #if id not in self._finalizedCode:
        #    if "@out." not in codeprep and "@in." not in codeprep:
        #        self._finalizedCode[id] = {"code": codeprep, "value": f'_state_{self.__gethexid(codeprep)}'}

        if "@initvars" in codeprep:
            initlocalvars = ""
            for k,vdat in self.getVariableDict().get('local',{}).items():
                if not k in self.localVariablesUsed: continue
                lval = self.updateValueDataForType(vdat['value'],vdat['type'])
                if self._addComments:
                    initlocalvars += f"\n//[{id}]lv_init:{vdat['name']}"
                initlocalvars += f'\nprivate {self.aliasVarNames[vdat["systemname"]]} = {lval};'
            
            #states = ""
            #for nodeId, vdat in self._finalizedCode.items():
            #    if self._addComments:
            #        states += f"\n//state_init:{nodeId}"
            #    states += f'\nprivate {vdat["value"]} = {vdat["code"]};'
            #initlocalvars += states

            codeprep = codeprep.replace("@initvars",initlocalvars)


        path.pop()

        return codeprep

    def __gethexid(self,v):
        return hex(id(v))

    def getVariableCode(self,className,nameid):

        varCat = self.varCategoryInfo[nameid]
        isGet = False

        if ".get" in className:
            isGet = True
        elif ".set" in className:
            isGet = False
        else:
            raise Exception(f"Unknown variable accessor classname: {className}")
        
        if varCat == "local":
            return f"{nameid}" if isGet else f"{nameid} = @in.2; @out.1"
        elif varCat == "class":
            return f"this getVariable \"{nameid}\"" if isGet else f"this setVariable [\"{nameid}\", @in.2]; @out.1"
        else:
            raise Exception(f'Unknown variable getter type {varCat}')

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

    def _resetNodesDisable(self):
        for node_id in self.serialized_graph["nodes"].keys():
            self.graphsys.graph.get_node_by_id(node_id).set_disabled(False)

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
        if type == "bool":
            return str(value).lower()
        
        return value
    
    def transliterate(self,text):
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya',
        }
        
        result = []
        for char in text:
            if char.lower() in translit_dict:
                if char.isupper():
                    result.append(translit_dict[char.lower()].capitalize())
                else:
                    result.append(translit_dict[char])
            else:
                result.append(char)
        enStr = ''.join(result)
        return re.sub("[^\w]","_",enStr)