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

        self.definedNodeName = None
        
        self.path = []

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
        self.variablePortName = {}
        self.typesVarNames = {}
        self.varCategoryInfo = {}

        self._finalizedCode = {} #k,v: nodeid, code (only finalized) !(work in _optimizeCodeSize)

        for vcat,vval in self.getVariableDict().items():
            for i, (k,v) in enumerate(vval.items()):
                self.typesVarNames[v['systemname']] = v['type']
                
                self.varCategoryInfo[v['systemname']] = vcat
                self.variablePortName[v['systemname']] = v['name']
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

        self.__generateNames(entrys)

        if self.graphsys.graph.question_dialog("Generate order?","Generator"):
            generated_code = self.generateOrderedCode(entrys)
            code += "\n" + generated_code
        #for nodeid in entrys:
            #self.localVariablesUsed = set()
            #data,startPoints = self.generateDfs(nodeid)
            #print(data)
            #code += "\n" + self.buildCodeFromData(data,startPoints)
            #code += "\n" + self.formatCode(self.generateCode(nodeid))
        #print(code)
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(code)

    def __generateNames(self,entry : list):
        import copy
        unicalNameDict = dict()
        uniIdx = 0
        for k,v in copy.copy(self.serialized_graph['nodes']).items():
            newname = f'[{uniIdx}]{v["class_"]}'
            unicalNameDict[k] = newname
            self.serialized_graph['nodes'][newname] = v
            self.serialized_graph['nodes'].pop(k)
            uniIdx += 1

            self.graphsys.graph.get_node_by_id(k).set_name(newname)
        pass
        
        #entry update
        for its in copy.copy(entry):
            entry.append(unicalNameDict[its])
            entry.remove(its)

        for conn in self.serialized_graph['connections']:
            inOld = conn['in'][0]
            outOld = conn['out'][0]

            conn['in'][0] = unicalNameDict[inOld]
            conn['out'][0] = unicalNameDict[outOld]

    def generateOrderedCode(self, entrys):
        # Создание графа зависимостей
        graph = self.createDependencyGraph()

        code = ""

        for ent in entrys:
            self.localVariablesUsed = set()
            # Топологическая сортировка узлов
            topological_order = self.topologicalSort(ent, graph)
            code += self.generateFromTopology(topological_order,ent)

        return self.formatCode(code)

    def createDependencyGraph(self):
        graph = defaultdict(list)
        for connection in self.serialized_graph['connections']:
            input_node, _ = connection["in"]
            output_node, _ = connection["out"]
            graph[input_node].append(output_node)
            graph[output_node].append(input_node)
        return graph

    def topologicalSort(self, entry, graph):
        stack = []
        visited = {node: False for node in graph}
        
        def topological_sort(node):
            visited[node] = True
            for neighbor in graph.get(node, []):  # Проверка на существование ключа
                if not visited[neighbor]:
                    topological_sort(neighbor)
            stack.append(node)
        
        topological_sort(entry)
        
        # реверсим стек от начала к последней точке
        stack.reverse()
        
        return stack

    class NodeData:
        def __init__(self, nodeid, refGraph):
            self.nodeId : str = nodeid
            self.refCodegen : CodeGenerator = refGraph
            self.nodeClass : str = ""
            self.isReady : bool = False
            self.classLibData : dict = None
            self.objectData : dict = None

            self.code = ""

            self.generatedVars = []

            self.usedGeneratedVars = []

            self._initNodeClassData()

        def _initNodeClassData(self):
            node_data = self.refCodegen.serialized_graph['nodes'][self.nodeId]
            self.objectData = node_data
            self.nodeClass = node_data['class_']
            self.classLibData = self.refCodegen.getNodeLibData(self.nodeClass)

            self.code = self.classLibData['code']

        def getConnectionInputs(self) -> dict[str,str]:
            return self.refCodegen.getInputs(self.nodeId)
        
        def getConnectionOutputs(self):
            return self.refCodegen.getExecPins(self.nodeId)


    def generateFromTopology(self, topological_order, entryId):

        codeInfo = {nodeid:CodeGenerator.NodeData(nodeid,self) for nodeid in topological_order}

        readyCount = 0
        hasAnyChanges = True # true for enter
        iteration = 0
        stackGenerated = []

        while len(codeInfo) != readyCount and hasAnyChanges:
            hasAnyChanges = False #reset
            iteration += 1

            stackGenerated = []

            for index_stack, node_id in enumerate(topological_order):
                obj : CodeGenerator.NodeData = codeInfo[node_id]
                node_code = obj.code

                if obj.isReady: continue

                node_className = obj.nodeClass
                obj_data = obj.objectData
                class_data = obj.classLibData

                
                node_inputs = class_data['inputs']
                node_outputs = class_data['outputs']

                isLocalVar = node_code == "RUNTIME" or obj_data.get('custom',{}).get('nameid')

                inputs_fromLib = node_inputs.items()
                outputs_fromLib = node_outputs.items()

                if isLocalVar:
                    nameid = obj_data['custom']['nameid']
                    #define variable code
                    node_code, portName, isGet = self.getVariableData(node_className,nameid)
                    self.localVariablesUsed.add(nameid)
                    node_code = node_code.replace(nameid,self.aliasVarNames[nameid])
                    #find key if not "nameid" and "code"
                    addedName = next((key for key in obj_data['custom'].keys() if key not in ['nameid','code']),None)
                    if addedName:
                        inputs_fromLib = list(inputs_fromLib)
                        inputs_fromLib.append((addedName,{'type':self.typesVarNames.get(nameid,None)}))
                    if isGet:
                        outputs_fromLib = list(outputs_fromLib)
                        outName = "Значение"
                        outputs_fromLib.append((outName,{'type':self.typesVarNames.get(nameid,None)}))

                createdStackedVars = False        
                if "@genvar." in node_code:
                    genList = re.findall(r"@genvar\.(\w+\.\d+)", node_code)
                    dictKeys = [k for i,(k,v) in enumerate(outputs_fromLib)]
                    dictValues = [v for i,(k,v) in enumerate(outputs_fromLib)]
                    for replClear in genList:
                        lvar = f'_lvar_{index_stack}'
                        wordpart = re.sub('\.\d+','',replClear)
                        numpart = re.sub('\w+\.','',replClear)
                        indexOf = int(numpart)-1

                        node_code = node_code.replace(f'@genvar.{wordpart}.{numpart}',lvar)

                        gvObj = GeneratedVariable(lvar,node_id)
                        gvObj.acceptedPaths = dictValues[indexOf]['accepted_paths']
                        gvObj.fromName = dictKeys[indexOf]
                        gvObj.definedNodeName = node_id
                        obj.generatedVars.append(gvObj)
                        createdStackedVars = True

                inputDict = obj.getConnectionInputs()
                execDict = obj.getConnectionOutputs()

                # Переберите все входы и замените их значения в коде
                for index, (input_name, input_props) in enumerate(inputs_fromLib):
                    inpId = inputDict.get(input_name)

                    # Данных для подключения нет - берем информацию из опции
                    if not inpId:
                        inlineValue = obj_data['custom'].get(input_name,' NULL ')
                        inlineValue = self.updateValueDataForType(inlineValue,input_props['type'])
                        node_code = node_code.replace(f'@in.{index+1}', f"{inlineValue}" )
                        continue


                    inpObj = codeInfo[inpId]
                    if len(inpObj.generatedVars) > 0:
                        for v in inpObj.generatedVars:
                            if inpId == v.definedNodeId:
                                v.isUsed = True
                                obj.usedGeneratedVars.append(v)
                                node_code = node_code.replace(f"@in.{index+1}", f"{v.localName}")
                            pass

                    # нечего заменять
                    if f'@in.{index+1}' not in node_code: 
                        continue

                    if inpObj.isReady:
                        node_code = node_code.replace(f"@in.{index+1}", inpObj.code)

                # Переберите все выходы и замените их значения в коде
                for index, (output_name, output_props) in enumerate(outputs_fromLib):
                    outId = execDict.get(output_name)

                    # Выход не подключен
                    if not outId: 
                        node_code = node_code.replace(f"@out.{index+1}", "")
                        continue

                    outputObj = codeInfo[outId]

                    # Пробрасываем переменные созданные на стеке если они в допустимом пути
                    if createdStackedVars:
                        for v in obj.generatedVars:
                            if output_name in v.acceptedPaths or "@any" in v.acceptedPaths or v.fromName == output_name:
                                outputObj.generatedVars.append(v)
                            pass
                    else:
                        for v in obj.generatedVars:
                            if v.definedNodeId != node_id:
                                if v not in outputObj.generatedVars:
                                    outputObj.generatedVars.append(v)

                    # нечего заменять
                    if f'@out.{index+1}' not in node_code:
                        continue

                    if outputObj.isReady:
                        
                        usedInScopeList = outputObj.usedGeneratedVars # Используемые переменные стека
                        passedVars = obj.generatedVars #доступные переменные на стеке
                        owners = [usedVar for usedVar in usedInScopeList if usedVar not in passedVars]
                        # [usedVar for usedVar in usedInScopeList if usedVar in passedVars] - for get restricted nodes
                        if len(owners) > 0:
                            ownText = ", ".join([codeInfo[v.definedNodeId].nodeId for v in owners])
                            self.error(f"{outputObj.nodeId} не может быть использован из-за ограничений, наложенных: {ownText}")
                            continue
                        node_code = node_code.replace(f"@out.{index+1}", outputObj.code)

                # prepare if all replaced
                if "@in." not in node_code and "@out." not in node_code:
                    obj.isReady = True

                #update code
                if not hasAnyChanges:
                    hasAnyChanges = obj.code != node_code
                obj.code = node_code

            # --- post check stack
            readyCount = 0
            for i in codeInfo.values():
                if i.isReady:
                    readyCount += 1
        
        #post while events
        if not hasAnyChanges and readyCount != len(codeInfo):
            self.error('Ошибка генерации - невозможно найти порты для генерации')

        entryObject = codeInfo[entryId]
        if not entryObject.isReady:
            return "NOT_READY:" + entryObject.code
        
        return entryObject.code

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

    def __gethexid(self,v):
        return hex(id(v))

    def getVariableData(self,className,nameid) -> tuple[str,str,bool]:
        """
        Возвращает код и тип аксессора переменной
            :param className: класснейм переменной
            :param nameid: имя переменной
            :return: код, имя порта, является ли получением
        """
        varCat = self.varCategoryInfo[nameid]
        varPortName = self.variablePortName[nameid]
        isGet = False

        if ".get" in className:
            isGet = True
        elif ".set" in className:
            isGet = False
        else:
            raise Exception(f"Unknown variable accessor classname: {className}")
        code = ""
        if varCat == "local":
            code = f"{nameid}" if isGet else f"{nameid} = @in.2; @out.1"
        elif varCat == "class":
            code = f"this getVariable \"{nameid}\"" if isGet else f"this setVariable [\"{nameid}\", @in.2]; @out.1"
        else:
            raise Exception(f'Unknown variable getter type {varCat}')
        
        return code,varPortName,isGet

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
    
    def log(self,text):
        print(f'[LOG]: {text}')

    def error(self,text):
        print(f'[ERROR]: {text}')

    def warning(self,text):
        print(f'[WARNING]: {text}')

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