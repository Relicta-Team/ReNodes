from collections import defaultdict
import json
import re
import enum
import asyncio
from ReNode.app.CodeGenExceptions import *
from ReNode.app.Logger import *
from ReNode.ui.LoggerConsole import LoggerConsole
from ReNode.ui.GraphTypes import *
from ReNode.ui.VariableManager import VariableManager
from ReNode.app.NodeFactory import NodeFactory
import traceback

class GeneratedVariable:
    def __init__(self,locname,definedNodeId,acceptedPaths = None):
        self.localName = locname 
        self.definedNodeId = definedNodeId
        self.acceptedPaths = acceptedPaths
        self.isUsed = False
        
        self.active = True
        self.fromName = None
        self.definedNodeName = None
        
        self.path = [] #ноды доступные в пути
        self.lockedPath = [] #ноды, запрещенные в пути
    
    def __repr__(self):
        return f"{self.definedNodeName}({self.localName})"

class CodeGenerator:
    def __init__(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        self.logger = RegisterLogger("CodeGen")

        self.generated_code = ""
        self.graphsys = NodeGraphComponent.refObject

        self.serialized_graph = None

        self._addComments = False # Добавляет мета-информацию внутрь кодовой структуры

        self._debug_info = True # Включать только для отладки: переименовывает комменты и имена узлов для проверки правильности генерации
        self._debug_rename = False #отладочная переименовка узлов

        #TODO: need write
        self._optimizeCodeSize = False # включает оптимизацию кода. Меньше разрмер 

        # те переменные, которые хоть раз используют установку или получение должны быть сгенерены
        self.localVariablesUsed = set()

        self.gObjType : GraphTypeBase = None
        self.gObjMeta :dict[str:object]= None

    def getGraphTypeObject(self):
        """Получает объект типа графа"""
        gtype = self.graphsys.graph.infoData['type']
        return GraphTypeFactory.getInstanceByType(gtype)

    def getNodeLibData(self,cls):
        return self.getFactory().getNodeLibData(cls)

    def getVariableManager(self) -> VariableManager:
        return self.graphsys.variable_manager

    def getVariableDict(self) -> dict:
        return self.getVariableManager().variables
    
    def getFactory(self) -> NodeFactory:
        return self.graphsys.nodeFactory

    def generateProcess(self,addComments=True):
        
        self._exceptions : list[CGBaseException] = [] #список исключений
        
        self._addComments = addComments
        
        layout_data = self.graphsys.graph._serialize(self.graphsys.graph.all_nodes())

        if not layout_data:
            return
        if not layout_data.get('nodes'):
            self.warning("Добавьте узлы в граф")
            return
        if not layout_data.get('connections'):
            self.warning("Добавьте связи в граф")
            return
        
        self.serialized_graph = layout_data

        entrys = self.getAllEntryPoints()
        if not entrys:
            self.warning("Добавьте точки входа в граф (события, определения методов, и т.д.)")
            return
        
        self._resetNodesError()

        self.log("Старт генерации...")
        
        code = "// Code generated:\n"
        # Данные локальных переменных: type(int), alias(_lv1), portname(Enumval), category(class,local)
        self.localVariableData = {}
        self.gObjType = self.getGraphTypeObject()
        self.gObjMeta = self.gObjType.createGenMetaInfoObject(self,self.graphsys.graph.infoData)

        # generated lvdata for graph user vars (local,class, methods)
        for vcat,vval in self.getVariableDict().items():
            for i, (k,v) in enumerate(vval.items()):
                lvData = {}
                self.localVariableData[k] = lvData
                lvData['type'] = v['type']
                lvData['usedin'] = None
                
                lvData['category'] = vcat
                lvData['portname'] = v['name']
                lvData['varname'] = v['name']
                #transliterate(v['name']) for get transliterate name
                if vcat=='local':
                    lvData['alias'] = f"_LVAR{i+1}"
                    lvData['initvalue'] = self.updateValueDataForType(v['value'],v['type'])
                elif vcat=='class':
                    lvData['alias'] = f"classMember_{i+1}"
                else:
                    continue


        # generate classvars
        code += self.gObjType.cgHandleVariables(self.gObjMeta)

        # generate inspector props
        code += self.gObjType.cgHandleInspectorProps(self.gObjMeta)

        self._originalReferenceNames = dict() #тут хранятся оригинальные айди нодов при вызове генерации имен
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

        

        if self._exceptions:
            self.log(f"\t- Ошибок: {len(self._exceptions)}")
            self.log("- <span style=\"color:red;\">Генерация завершена с ошибками</span>")
        else:
            self.log("- <span style=\"color:green;\">Генерация завершена</span>")
        
        self.log("================================")
        
            

    def __generateNames(self,entry : list):
        import copy
        unicalNameDict = dict()
        self._originalReferenceNames = dict()
        uniIdx = 0
        for k,v in copy.copy(self.serialized_graph['nodes']).items():
            newname = f'[{uniIdx}]{v["class_"]}'
            unicalNameDict[k] = newname
            self.serialized_graph['nodes'][newname] = v
            self._originalReferenceNames[newname] = k
            self.serialized_graph['nodes'].pop(k)
            uniIdx += 1

            if self._debug_rename:
                self.graphsys.graph.get_node_by_id(k).set_name(newname)
        
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
        try:
            # Создание графа зависимостей
            graph = self.createDependencyGraph()

            code = ""

            for ent in entrys:
                self.localVariablesUsed = set()
                # Топологическая сортировка узлов
                topological_order = self.topologicalSort(ent, graph)
                code += self.generateFromTopology(topological_order,ent)

            return self.formatCode(code)
        except Exception as e:
            strFullException = traceback.format_exc()

            styleinfo = '''
                background: #13f4f4f4;
                border: 1px solid #ddd;
                border-left: 3px solid #ffD90000;
                border-right: 3px solid #ffD90000;
                border-top: 3px solid #ffD90000;
                border-bottom: 30px solid #ffD90000;
                border-radius: 10px;
                color: #EBEBEB;
                font-size: 15px;
                line-height: 1.2;
                max-width: 100%;
                overflow: auto;
                padding: 1em 1.5em;
                display: block;
                page-break-inside: avoid;
                word-wrap: normal;
            '''
            styleinfo = styleinfo.replace("\n","")
            strFullException = f'{e.__class__.__name__}<pre style="{styleinfo}">\n{strFullException}</pre>'
            self.exception(CGUnhandledException,context=strFullException)
            return f"//unhandled exception\n"

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

            self.hasError = False

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

        def getConnectionType(self,inout,portname):
            return self.refCodegen.getNodeConnectionType(self.nodeId,inout,portname)
        
        def getNodeObject(self):
            cg = self.refCodegen
            nodeid = cg._sanitizeNodeName(self.nodeId)
            return cg.graphsys.graph.get_node_by_id(nodeid)
    
        def markAsError(self):
            if not self.hasError:
                self.hasError = True
                return True
            return False


    def generateFromTopology(self, topological_order, entryId):

        codeInfo = {nodeid:CodeGenerator.NodeData(nodeid,self) for nodeid in topological_order}

        readyCount = 0
        hasAnyChanges = True # true for enter
        iteration = 0

        while len(codeInfo) != readyCount and hasAnyChanges:
            hasAnyChanges = False #reset
            iteration += 1

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

                hasRuntimePorts = class_data.get('runtime_ports')

                inputs_fromLib = node_inputs.items()
                outputs_fromLib = node_outputs.items()

                createdStackedVars = False

                if isLocalVar:
                    nameid = obj_data['custom']['nameid']
                    #define variable code
                    generated_code, portName, isGet,varCat = self.getVariableData(node_className,nameid)
                    isSet = not isGet
                    # update generated code only first time
                    if node_code == "RUNTIME":
                        if varCat == "local":
                            usedIn = self.localVariableData[nameid]['usedin']
                            entryObj = codeInfo[entryId]
                            if not usedIn or usedIn == entryObj:
                                self.localVariablesUsed.add(nameid)
                                self.localVariableData[nameid]['usedin'] = entryObj
                            else:
                                self.exception(CGLocalVariableDuplicateUseException,source=obj,context=self.localVariableData[nameid]['varname'],entry=entryObj,target=usedIn)
                        lvar_alias = self.localVariableData[nameid]['alias']
                        node_code = generated_code.replace(nameid,lvar_alias)
                        if isSet:
                            #generate variable out
                            gvObj = GeneratedVariable(lvar_alias,node_id)
                            gvObj.acceptedPaths = ["@any"] #constant
                            gvObj.fromName = portName
                            gvObj.definedNodeName = node_id
                            obj.generatedVars.append(gvObj)
                            createdStackedVars = True

                    
                    #find key if not "nameid" and "code"
                    #addedName = next((key for key in obj_data['custom'].keys() if key not in ['nameid','code']),None)
                    if isSet:
                        inputs_fromLib = list(inputs_fromLib)
                        inputs_fromLib.append((portName,{'type':self.localVariableData[nameid]['type']}))
                        outputs_fromLib = list(outputs_fromLib)
                        outputs_fromLib.append((portName,{'type':self.localVariableData[nameid]['type']}))
                    if isGet:
                        outputs_fromLib = list(outputs_fromLib)
                        outName = "Значение"
                        outputs_fromLib.append((outName,{'type':self.localVariableData[nameid]['type']}))
        
                if "@genvar." in node_code:
                    genList = re.findall(r"@genvar\.(\w+\.\d+)", node_code)

                    dictKeys = [k for i,(k,v) in enumerate(outputs_fromLib)]
                    dictValues = [v for i,(k,v) in enumerate(outputs_fromLib)]
                    for _irepl, replClear in enumerate(genList):
                        lvar = f'_lvar_{index_stack}_{_irepl}'
                        wordpart = re.sub('\.\d+','',replClear)
                        numpart = re.sub('\w+\.','',replClear)
                        indexOf = int(numpart)-1

                        node_code = re.sub(f'@genvar\.{wordpart}\.{numpart}(?=\D|$)',lvar,node_code)

                        #replacing @locvar.out.1
                        node_code = re.sub(f'@locvar\.{wordpart}\.{numpart}(?=\D|$)',lvar,node_code)

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
                        if 'custom' not in obj_data: 
                            #self.warning(f"{node_id} не имеет специальных публичных данных")
                            continue
                        # нечего заменять в этом порте
                        if not re.findall(f'@in\.{index+1}(?=\D|$)',node_code):
                            continue
                        if hasRuntimePorts:
                            if not obj.getConnectionType("in",input_name):
                                self.exception(CGInputPortTypeRequiredException,source=obj,portname=input_name)
                            
                        inlineValue = obj_data['custom'].get(input_name,'NULL')

                        if re.findall(f'@in\.{index+1}(?=\D|$)',node_code) and inlineValue == "NULL":
                            self.exception(CGPortRequiredConnectionException,source=obj,portname=input_name)

                        libOption = class_data['options'].get(input_name)
                        if libOption and libOption['type'] == "list":
                            for optList in libOption['values']:
                                if isinstance(optList,list):
                                    if optList[0] == inlineValue:
                                        inlineValue = optList[1]
                                else:
                                    if optList == inlineValue:
                                        self.exception(CGLogicalOptionListEvalException,source=obj,portname=libOption.get('text',input_name),context=optList)
                                        break

                        inlineValue = self.updateValueDataForType(inlineValue,input_props['type'])
                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)', f"{inlineValue}", node_code)
                        continue

                    # нечего заменять
                    if not re.findall(f'@in\.{index+1}(?=\D|$)',node_code):
                        continue

                    inpObj = codeInfo[inpId]
                    if len(inpObj.generatedVars) > 0:
                        for v in inpObj.generatedVars:
                                owningGeneratedVar = v in obj.generatedVars
                                pathCondition = node_id in v.path and node_id not in v.lockedPath
                                pathUse = node_id in v.path 
                                pathLock = node_id not in v.lockedPath
                                isNearParent = inpId == v.definedNodeId

                                if self._debug_rename:
                                    uvc = f"{inpId}:{input_name}=" + str([owningGeneratedVar,pathUse,pathLock,isNearParent])
                                    self._debug_setName(node_id,f' <br/><span style ="color:yellow; padding-bottom:10px">uvc:{uvc}</span>')
                                
                                if not pathLock and isNearParent: pathLock = not pathLock
                                usableVariable = owningGeneratedVar and pathUse and pathLock
                                
                                if usableVariable:
                                        v.isUsed = True
                                        obj.usedGeneratedVars.append(v)
                                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)', f"{v.localName}", node_code)

                    if inpObj.isReady:
                        for v in inpObj.generatedVars:
                            intersections = self.intersection(v.path,v.lockedPath)
                            
                            existsPathThis = obj.nodeId in v.path
                            existsFromGenerated = v in obj.generatedVars
                            outputNotInPath = inpObj.nodeId not in v.path
                            definedInOut = v.definedNodeId == inpObj.nodeId
                            
                            secCond = not (existsPathThis or existsFromGenerated or outputNotInPath) and not definedInOut
                            
                            if self._debug_rename:
                                prefx = ""#"ERRORED" if secCond else ""
                                nmn = re.sub(r'[a-zA-Z\.\_]+','',inpObj.nodeId)
                                self._debug_setName(obj.nodeId,f'!!!FUCKED {nmn}<<<{prefx}({existsPathThis},{existsFromGenerated},{outputNotInPath},{definedInOut})')

                            if secCond:
                                self.exception(CGUnhandledObjectException,source=obj,context=f"Ошибка входного порта \'{input_name}\'")

                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)',inpObj.code,node_code) 

                # Переберите все выходы и замените их значения в коде
                for index, (output_name, output_props) in enumerate(outputs_fromLib):
                    outId = execDict.get(output_name)

                    # Выход не подключен
                    if not outId: 
                        if hasRuntimePorts:
                            if not obj.getConnectionType("out",output_name):
                                self.exception(CGOutputPortTypeRequiredException,source=obj,portname=output_name)
                        
                        node_code = re.sub(f'@out\.{index+1}(?=\D|$)',"",node_code) 
                        continue

                    outputObj = codeInfo[outId]

                    # Пробрасываем переменные созданные на стеке если они в допустимом пути
                    if createdStackedVars:
                        for v in obj.generatedVars:
                            if output_name in v.acceptedPaths or "@any" in v.acceptedPaths or v.fromName == output_name:
                                if v not in outputObj.generatedVars:
                                    outputObj.generatedVars.append(v)
                                    v.path.append(obj.nodeId)
                                    if outputObj.nodeId not in v.path:
                                        v.path.append(outputObj.nodeId)
                            else:
                                if outputObj.nodeId not in v.lockedPath:
                                    v.lockedPath.append(outputObj.nodeId)
                    else:
                        for v in obj.generatedVars:
                            if v.definedNodeId != node_id:
                                if v not in outputObj.generatedVars:
                                    outputObj.generatedVars.append(v)
                                
                                if len(v.lockedPath) > 0 and outputObj.nodeId not in v.lockedPath:
                                    v.lockedPath.append(outputObj.nodeId)

                                if outputObj.nodeId not in v.path:
                                    v.path.append(outputObj.nodeId)

                    # нечего заменять
                    if not re.findall(f'@out\.{index+1}(?=\D|$)',node_code):
                        continue

                    if outputObj.isReady:
                        
                        def btext(val):
                            return "TRUE" if val else "FALSE"
                        
                        for v in outputObj.generatedVars:
                            #!!!! ============== переписать ==============
                            intersections = self.intersection(v.path,v.lockedPath)
                            
                            existsPathThis = obj.nodeId in v.path
                            existsFromGenerated = v in obj.generatedVars
                            outputNotInPath = outputObj.nodeId not in v.path

                            definedInOut = v.definedNodeId == outputObj.nodeId

                            outInLocked = outputObj.nodeId in v.lockedPath
                            
                            secCond = not (existsPathThis or existsFromGenerated or outputNotInPath) and not definedInOut
                            
                            if not secCond:
                                if len(outputObj.usedGeneratedVars) > 0 and outInLocked and v.definedNodeId == obj.nodeId:
                                    secCond = True
                            secCond = secCond and len(outputObj.usedGeneratedVars) > 0

                            if self._debug_rename:
                                prefx = "ERRORED" if secCond else ""
                                clr = "red" if secCond else "#1aff00"
                                nmn = re.sub(r'[a-zA-Z\.\_]+','',obj.nodeId)
                                sg_ = "    &nbsp;"
                                alldata__ = f'({btext(existsPathThis)},{btext(existsFromGenerated)},{btext(outputNotInPath)},{btext(definedInOut)},{btext(outInLocked)} i:{len(intersections)}+lp:{len(v.lockedPath)}+o.ugv:{outputObj.usedGeneratedVars})'
                                self._debug_setName(outId,f' <br/><span style ="color:{clr}; padding-bottom:10px;">{nmn}>{prefx}{alldata__}')
                            
                            if secCond:
                                # oname = "НЕИЗВЕСТНО"
                                # for kin,vin in outputObj.getConnectionInputs().items():
                                #     if vin == node_id:
                                #         oname = kin
                                #         break
                                self.exception(CGVariablePathAccessException,source=outputObj,portname=output_name,target=codeInfo[v.definedNodeId])
                            else:
                                # дополнительная проверка с отловом локальных переменных за пределами цикла
                                if output_name in CGVariableUnhandledPathAccessException.checkedNodes.get(node_className,[]):
                                    varNames = [varObj.localName for varObj in obj.generatedVars if node_id == varObj.definedNodeId]
                                    if len(varNames) > 0:
                                        for varName_ in varNames:
                                            if varName_ in outputObj.code:
                                                self.exception(CGVariableUnhandledPathAccessException,source=outputObj,portname=output_name,target=codeInfo[v.definedNodeId])
                                                break   
                                         
                        node_code = re.sub(f"\@out\.{index+1}(?=\D|$)", outputObj.code, node_code) 

                # prepare if all replaced
                if "@in." not in node_code and "@out." not in node_code:
                    obj.isReady = True

                if obj.isReady and "@initvars" in node_code:
                    initVarsCode = ""
                    for nameid in self.localVariablesUsed:
                        initVarsCode += f'private {self.localVariableData[nameid]["alias"]} = {self.localVariableData[nameid]["initvalue"]};\n'
                    node_code = node_code.replace("@initvars",initVarsCode)

                #update code
                if not hasAnyChanges:
                    hasAnyChanges = obj.code != node_code
                obj.code = node_code

            # --- post check stack
            readyCount = 0
            for i in codeInfo.values():
                if i.isReady:
                    readyCount += 1
        
        errList = []
        topoNodes = list(codeInfo.values())
        if len(topoNodes) > 0:
            topoNodes.pop(0)
        topoNodes.reverse()
        firstNonGenerated = None
        if len(topoNodes) > 0:
            firstNonGenerated = topoNodes.pop()
        for obj in topoNodes:
            if obj.hasError: 
                errList.append(obj)

        hasNodeError = next((o for o in codeInfo.values() if o.hasError),None)
        stackGenError = not hasAnyChanges and readyCount != len(codeInfo)

        entryObj = codeInfo[entryId]

        #post while events
        if stackGenError:
            self.exception(CGStackError,entry=entryObj,source=firstNonGenerated)

        if hasNodeError:
            strInfo = "\n\t".join([LoggerConsole.wrapNodeLink(self._sanitizeNodeName(s.nodeId),s.nodeId) for s in errList])
            if not strInfo: 
                strInfo = "-отсутствуют-" 
            else: 
                strInfo = "\n\t" + strInfo
            self.error(f'Узлы, требующие проверки/исправления из события {LoggerConsole.wrapNodeLink(self._sanitizeNodeName(entryObj.nodeId),entryObj.nodeId)} (всего {len(errList)}):{strInfo}')


        entryObj = codeInfo[entryId]
        if not entryObj.isReady:
            return "NOT_READY:" + entryObj.code
        
        return entryObj.code

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

    def intersection(self,list_a, list_b):
        return [ e for e in list_a if e in list_b ]

    def getVariableData(self,className,nameid) -> tuple[str,str,bool]:
        """
        Возвращает код и тип аксессора переменной
            :param className: класснейм переменной
            :param nameid: имя переменной
            :return: код, имя порта, является ли получением, категория переменной
        """
        varData = self.localVariableData[nameid]
        varCat = varData['category']
        varPortName = varData['portname']
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
        
        return code,varPortName,isGet,varCat

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

    def _resetNodesError(self):
        for node_id in self.serialized_graph['nodes'].keys():
            self.graphsys.graph.get_node_by_id(node_id).resetError()

    def findNodesByClass(self, class_to_find):
        node_ids = []
        for node_id, node_data in self.serialized_graph["nodes"].items():
            if node_data["class_"] == class_to_find:
                node_ids.append(node_id)
        return node_ids

    def getAllEntryPoints(self):
        node_ids = []
        for node_id, node_data in self.serialized_graph["nodes"].items():
            libData = self.getNodeLibData(node_data['class_'])
            isClassMember = "classInfo" in libData
            if isClassMember:
                isMethod = libData["classInfo"]["type"] == "method"
                if isMethod:
                    # сбор методов: только те у которых memtype -> def, event
                    memType = libData.get("memtype")
                    if not memType:
                        raise Exception(f"Corrupted memtype for method '{node_data['class_']}'; Info: {libData}")
                    if memType in ["def","event"]:
                        node_ids.append(node_id)
        return node_ids

    def updateValueDataForType(self,value,tname):
        if not tname: return value
        if tname == "string": 
            return "\"" + value.replace("\"","\"\"") + "\""
        elif tname == "bool":
            return str(value).lower()
        elif tname in ['float','int']:
            return value
        elif self.getVariableManager().isObjectType(tname):
            return value
        else:
            if not self.isDebugMode(): 
                raise Exception(f"Unknown type {tname} (value: {value})")

        return value
    
    def isDebugMode(self):
        from ReNode.app.application import Application
        return Application.isDebugMode()

    def log(self,text):
        self.logger.info(text)

    def error(self,text):
        self.logger.error(text)

    def warning(self,text):
        self.logger.warning(text)

    def exception(self,
                  exType,source:NodeData | None=None,
                  portname:str|None=None,
                  target:NodeData | None=None, 
                  entry:NodeData | None=None,
                  context=None):
        sourceId = None
        targetId = None
        entryId = None

        linkSourceId = None
        linkTargetId = None
        linkEntryId = None

        if source: 
            sourceId = source.nodeId
            linkSourceId = LoggerConsole.wrapNodeLink(self._sanitizeNodeName(sourceId),sourceId)
        if target: 
            targetId = target.nodeId
            linkTargetId = LoggerConsole.wrapNodeLink(self._sanitizeNodeName(targetId),targetId)
        if entry: 
            entryId = entry.nodeId
            linkEntryId = LoggerConsole.wrapNodeLink(self._sanitizeNodeName(entryId),entryId)

        params = {
            "src": linkSourceId,
            "portname": portname,
            "targ": linkTargetId,
            "ctx": context,
            "entry": linkEntryId
        }
        ex : CGBaseException = exType(**params)

        self.error(ex.getExceptionText(addDesc=True))
        #self.error(f)

        if sourceId:
            if source.markAsError():
                source.getNodeObject().addErrorText(f'Узел {sourceId}:\nОшибка {ex.getShortErrorInfo()}')
            else:
                source.getNodeObject().addErrorText(f'Ошибка {ex.getShortErrorInfo()}')
        if targetId:
            if target.markAsError():
                target.getNodeObject().addErrorText(f'Узел {targetId}:\n> Ошибка в {sourceId}')
            else:
                target.getNodeObject().addErrorText(f'> Ошибка в {sourceId}')
        if entryId:
            if entry.markAsError():
                entry.getNodeObject().addErrorText(f'Старт {entryId}:\n> Ошибка в {sourceId}')
            else:
                entry.getNodeObject().addErrorText(f'> Ошибка в {sourceId}')


        self._exceptions.append(ex)
    def _sanitizeNodeName(self,node_id):
        if node_id in self._originalReferenceNames:
            node_id = self._originalReferenceNames[node_id]
        return node_id
    
    def getNodeConnectionType(self,node_id,inout,portname):
        node_id = self._sanitizeNodeName(node_id)
        obj = self.graphsys.graph.get_node_by_id(node_id)
        if inout == "in":
            return obj.inputs()[portname].view.port_typeName
        elif inout == "out":
            return obj.outputs()[portname].view.port_typeName
        else:
            raise Exception(f"Unknown connection type: {inout}")

    def _debug_setName(self,node_id,name):
        node_id = self._sanitizeNodeName(node_id)
        
        orig = self.graphsys.graph.get_node_by_id(node_id)
        oldName = orig.name()
        orig.set_name(oldName+name)
        #orig.set_property("name",oldName + name,False,doNotRename=True)

    def prepareMemberCode(self,dictLib,code):
        """
        Метод для подготовки кода. Формирует список параметров, заменяет имя члена и класса с помощью специальных метатегов
        """
        isClassMember = "classInfo" in dictLib
        if isClassMember:
            className = dictLib['classInfo']['class']
            memName = dictLib['classInfo']['name']
            memType = dictLib['classInfo']['type']

            code = code.replace('@thisClass',className)
            
            code = code.replace('@thisName',memName)
            if "@thisParams" in code:
                
                paramList = ['\'this\'']
                for indexVar, (outKey,outValues) in enumerate(dictLib['outputs'].items()):
                    if outValues['type'] != "Exec" and outValues['type'] != "":
                        paramList.append('\"@genvar.out.{}\"'.format(indexVar+1))
                
                paramCtx = f'params [{", ".join(paramList)}]'
                code = code.replace('@thisParams',paramCtx)
        
        return code