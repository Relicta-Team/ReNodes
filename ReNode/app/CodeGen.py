from collections import defaultdict
import json
import re
import enum
import asyncio
from ReNode.app.CodeGenExceptions import *
from ReNode.app.CodeGenWarnings import *
from ReNode.app.Logger import *
from ReNode.ui.LoggerConsole import LoggerConsole
from ReNode.ui.GraphTypes import *
from ReNode.ui.VariableManager import VariableManager
from ReNode.app.NodeFactory import NodeFactory
import traceback
import time
import datetime

#const enum for nodedata types

class NodeDataType(enum.Enum):
    """Тип узла в графе"""
    NODE = 0
    OPERATOR = 1
    SCOPED_LOOP = 2
    
    @staticmethod
    def getScopedLoopNodes(): return ["operators.for_loop","operators.foreach_loop"]

    @staticmethod
    def getNodeType(classname:str):
        if classname in NodeDataType.getScopedLoopNodes():
            return NodeDataType.SCOPED_LOOP
        elif classname.startswith("operators."):
            return NodeDataType.OPERATOR
        
        return NodeDataType.NODE

class GeneratedVariable:
    def __init__(self,locname,definedNodeId):
        self.localName = locname 
        self.definedNodeId = definedNodeId
        self.isUsed = False
        
        self.active = True
        self.fromPort = None
        self.definedNodeName = None
    
    def __repr__(self):
        return f"{self.definedNodeName}:{self.fromPort}({self.localName})"

class CodeGenerator:
    def __init__(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        self.logger = RegisterLogger("CodeGen")

        self.generated_code = ""
        self.graphsys = NodeGraphComponent.refObject

        self.serialized_graph = None

        self._addComments = False # Добавляет мета-информацию внутрь кодовой структуры

        self._debug_info = True # Включать только для отладки: переименовывает комменты и имена узлов для проверки правильности генерации
        self._debug_rename = not False #отладочная переименовка узлов

        #TODO: need write
        self._optimizeCodeSize = False # включает оптимизацию кода. Меньше разрмер 

        # те переменные, которые хоть раз используют установку или получение должны быть сгенерены
        self.localVariablesUsed = set()

        self.gObjType : GraphTypeBase = None
        self.gObjMeta :dict[str:object]= None

        self.isGenerating = False

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
        self._warnings : list[CGBaseWarning] = [] #список предупреждений
        
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
        
        self.isGenerating = True

        self._resetNodesError()

        self.log("Старт генерации...")
        timestamp = int(time.time()*1000.0)
        
        code = "// Code generated:\n"
        # Данные локальных переменных: type(int), alias(_lv1), portname(Enumval), category(class,local)
        self.localVariableData = {}
        self.gObjType = self.getGraphTypeObject()
        self.gObjMeta = self.gObjType.createGenMetaInfoObject(self,self.graphsys.graph.infoData)

        self.log("Генерация переменных")

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
                if vcat=='localvar':
                    lvData['alias'] = f"_LVAR{i+1}"
                    lvData['initvalue'] = self.updateValueDataForType(v['value'],v['type'])
                elif vcat=='classvar':
                    lvData['alias'] = f"classMember_{i+1}"
                else:
                    continue


        # generate classvars
        code += self.gObjType.cgHandleVariables(self.gObjMeta)

        self.log("Генерация свойств инспектора")

        # generate inspector props
        code += self.gObjType.cgHandleInspectorProps(self.gObjMeta)

        self._originalReferenceNames = dict() #тут хранятся оригинальные айди нодов при вызове генерации имен
        self.__generateNames(entrys)

        
        self._validateEntrys(entrys)

        self.log("Генерация связей")
        self.dpdGraphExt = self.createDpdGraphExt()

        self.log("Генерация кода узлов")
        generated_code = self.generateOrderedCode(entrys)
        code += "\n" + generated_code
        
        code = self.gObjType.cgHandleWrapper(code,self.gObjMeta)
        
        code = f'//gdate: {datetime.datetime.now()}\n' + code

        if self.isDebugMode():
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(code)

        

        self.log(f"\t- Предупреждений: {len(self._warnings)}; Ошибок: {len(self._exceptions)}")
        if self._exceptions:
            self.log("- <span style=\"color:red;\">Генерация завершена с ошибками</span>")
        else:
            self.log("- <span style=\"color:green;\">Генерация завершена</span>")
        
        timeDiff = int(time.time()*1000.0) - timestamp
        self.log(f"Процедура завершена за {timeDiff} мс")
        self.log("================================")
        
        self.isGenerating = False

        #cleanup data
        self._exceptions.clear()
        self._warnings.clear()
        self.gObjMeta.clear()
        self.dpdGraphExt.clear()

    def __generateNames(self,entry : list):
        import copy
        unicalNameDict = dict()
        self._originalReferenceNames = dict()
        uniIdx = 0

        nameCounter = {}

        for k,v in copy.copy(self.serialized_graph['nodes']).items():
            
            curName = v['name']
            if curName in nameCounter:
                nameCounter[curName] += 1
                curName = f'{curName} ({nameCounter[curName]})'
            else:
                nameCounter[curName] = 1
            
            #newname = f'[{uniIdx}]{v["class_"]}'
            newname = curName
            unicalNameDict[k] = newname
            self.serialized_graph['nodes'][newname] = v
            self._originalReferenceNames[newname] = k
            self.serialized_graph['nodes'].pop(k)
            uniIdx += 1

            if self._debug_rename:
                #self.graphsys.graph.get_node_by_id(k).set_name(newname)
                node = self.graphsys.graph.get_node_by_id(k)
                
                node.view.text_item.setHtml(newname)
                node.view.draw_node()
        
        #entry update
        for its in copy.copy(entry):
            entry.append(unicalNameDict[its])
            entry.remove(its)

        for conn in self.serialized_graph['connections']:
            inOld = conn['in'][0]
            outOld = conn['out'][0]

            conn['in'][0] = unicalNameDict[inOld]
            conn['out'][0] = unicalNameDict[outOld]

    def _validateEntrys(self,entrys):
        #find duplicates entry classes
        entDict = {}
        entNodeData = {_id: CodeGenerator.NodeData(_id,self) for _id in entrys}
        for ent in entrys:
            entData = self.serialized_graph['nodes'][ent]
            if entData['class_'] in entDict:
                src = entNodeData[ent]
                entObj = entNodeData[entDict[entData['class_']]]
                self.exception(CGDuplicateEntryException,source=src,entry=entObj)
            entDict[entData['class_']] = ent
        del entDict

    def generateOrderedCode(self, entrys):
        try:
            self.log("    Создание зависимостей")
            # Создание графа зависимостей
            graph = self.createDependencyGraph(collectOnlyExecutePins=True)

            code = ""

            for i,ent in enumerate(entrys):
                self.log(f"    -------- Генерация точки входа {i+1}/{len(entrys)}")

                self.localVariablesUsed = set()
                
                # Топологическая сортировка узлов
                #self.log("    -- Сортировка")
                topological_order = self.topologicalSort(ent, graph)

                #self.log(f"    -- Генерация {ent} (узлов: {len(topological_order)})")
                entryObj = self.serialized_graph['nodes'][ent]
                if self._addComments:
                    code += f"\n//p_entry: {entryObj['class_']}\n"
                code += self.generateFromTopology(topological_order,ent)

            self.log("Форматирование")

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

    def createDependencyGraph(self,collectOnlyExecutePins=False):
        def getPortInputType(node,port): 
            ndata = self.serialized_graph['nodes'][node]
            if ndata.get("port_deletion_allowed"):
                return next((pinfo['type'] for pinfo in ndata['input_ports'] if pinfo['name'] == port),None)
            else:
                return self.getNodeLibData(ndata['class_']) ['inputs'][port].get("type")
        def getPortOutputType(node,port): 
            ndata = self.serialized_graph['nodes'][node]
            if ndata.get("port_deletion_allowed"):
                return next((pinfo['type'] for pinfo in ndata['output_ports'] if pinfo['name'] == port),None)
            else:
                return self.getNodeLibData(ndata['class_']) ['outputs'][port].get("type")

        graph = defaultdict(list)
        for connection in self.serialized_graph['connections']:
            input_node, portInName = connection["in"]
            output_node, portOutName = connection["out"]
            if collectOnlyExecutePins:
                typeIn = getPortInputType(input_node, portInName)
                typeOut = getPortOutputType(output_node, portOutName)
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

    #region Dependency graph extension with relations

    def __initDPDConnectionTypes(self,nodename,ref):
        inNodeInfo = self.getNodeLibData(self.serialized_graph['nodes'][nodename]['class_'])
        for k,v in inNodeInfo['inputs'].items():
            ref['typein'][k] = v['type']
        outNodeInfo = self.getNodeLibData(self.serialized_graph['nodes'][nodename]['class_'])
        for k,v in outNodeInfo['outputs'].items():
            ref['typeout'][k] = v['type']

    def createDpdGraphExt(self):
        graph = {}
        for connection in self.serialized_graph['connections']:
            input_node, portIn = connection["in"]
            output_node, portOut = connection["out"]
            
            # create 
            if input_node not in graph:
                graph[input_node] = {
                    "in": defaultdict(list), # key:portname, value:{node:}
                    "out": defaultdict(list),
                    "typein": {}, # key:portname,value: porttype
                    "typeout": {}, # key:portname,value: porttype
                }
                self.__initDPDConnectionTypes(input_node,graph[input_node])
            if output_node not in graph:
                graph[output_node] = {
                    "in": defaultdict(list),
                    "out": defaultdict(list),
                    "typein": {},
                    "typeout": {},
                }
                self.__initDPDConnectionTypes(output_node,graph[output_node])

            graph[input_node]['in'][portIn].append({output_node:portOut})
            graph[output_node]['out'][portOut].append({input_node:portIn})


        return graph

    def scopePrepass(self,topological_order,codeInfo,entryId):
        """Создание скоупов для узлов и их связей"""
        scopesExec = defaultdict(list)

        if entryId not in self.dpdGraphExt: return #no connections -> no scopes
        loopScopes = NodeDataType.getScopedLoopNodes()
        def get_exec_outs(id_,scope=None):
            idat = self.dpdGraphExt[id_]
            codeObj : CodeGenerator.NodeData = codeInfo[id_]
            if isinstance(scope,list):
                codeObj.scopes.extend(scope)
            iclass = codeObj.nodeClass
            codeObj.visitedExecFlow = True
            for k,v in idat['typeout'].items():
                if v == "Exec":
                    isScopeStart = iclass in loopScopes and k == "Тело цикла"
                    if isScopeStart:
                        if scope and len(scope) > 0:
                            scope.append(codeObj)
                        else:
                            scope = [codeObj]

                    if len(idat['out'][k]) > 0:
                        src = list(idat['out'][k][0])[0]
                        get_exec_outs(src,scope)
                    
                    if isScopeStart:
                        scope.pop()
                        if len(scope) == 0:
                            scope = None

        get_exec_outs(entryId)
        #{n:o.scopes for n,o in codeInfo.items()}
        return scopesExec

    #endregion

    class NodeData:
        def __init__(self, nodeid, refGraph):
            self.nodeId : str = nodeid
            self.refCodegen : CodeGenerator = refGraph
            self.nodeClass : str = ""
            self.isReady : bool = False
            self.classLibData : dict = None
            self.objectData : dict = None

            self.code = ""

            self.generatedVars = {} #key: out portname, value:variable

            self.hasError = False

            self._initNodeClassData()
            self._defineNodeType()

            self.returns = [] #возвращаемые значения (используется для событий и функций)
            self.endsWithNoReturns = [] #сюда пишутся узлы без подключенных возвращаемых значений (только для энтрипоинтов)

            self.scopes = [] #области видимости

            self.visitedExecFlow = False

        def __repr__(self) -> str:
            return f'ND:{self.nodeId} ({self.nodeClass})'

        def getScopeObj(self):
            if len(self.scopes) == 0: return None
            return self.scopes[-1]

        def _initNodeClassData(self):
            node_data = self.refCodegen.serialized_graph['nodes'][self.nodeId]
            self.objectData = node_data
            self.nodeClass = node_data['class_']
            self.classLibData = self.refCodegen.getNodeLibData(self.nodeClass)

            self.code = self.classLibData['code']

        def _defineNodeType(self):
            self.nodeType = NodeDataType.getNodeType(self.nodeClass)
            pass

        def getConnectionInputs(self,retPortnames=False) -> dict[str,str]:
            return self.refCodegen.getInputs(self.nodeId,retPortnames)
        
        def getConnectionOutputs(self,retPortnames=False):
            return self.refCodegen.getExecPins(self.nodeId,retPortnames)

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

    def getNodeObjectById(self,nodeid):
            cg = self
            nodeid = cg._sanitizeNodeName(nodeid)
            return cg.graphsys.graph.get_node_by_id(nodeid)

    def generateFromTopology(self, topological_order, entryId):

        curExceptions = len(self._exceptions)
        curWarnings = len(self._warnings)

        codeInfo = {nodeid:CodeGenerator.NodeData(nodeid,self) for nodeid in topological_order}

        self.scopePrepass(topological_order,codeInfo,entryId)

        readyCount = 0
        hasAnyChanges = True # true for enter
        iteration = 0

        self.gObjType.handlePreStartEntry(codeInfo[entryId],self.gObjMeta)

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

                if isLocalVar:
                    nameid = obj_data['custom']['nameid']
                    #define variable code
                    generated_code, portName, isGet,varCat = self.getVariableData(node_className,nameid)
                    isSet = not isGet
                    outName = "Значение"
                    # update generated code only first time
                    if node_code == "RUNTIME":
                        if varCat == "localvar":
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
                            gvObj.fromPort = outName
                            gvObj.definedNodeName = node_id
                            if outName in obj.generatedVars:
                                raise Exception(f'Unhandled case: {outName} in {obj.generatedVars}')
                            obj.generatedVars[outName] = gvObj

                    
                    #find key if not "nameid" and "code"
                    #addedName = next((key for key in obj_data['custom'].keys() if key not in ['nameid','code']),None)
                    if isSet:
                        inputs_fromLib = list(inputs_fromLib)
                        inputs_fromLib.append((portName,{'type':self.localVariableData[nameid]['type']}))
                        outputs_fromLib = list(outputs_fromLib)
                        outputs_fromLib.append((outName,{'type':self.localVariableData[nameid]['type']}))
                    if isGet:
                        outputs_fromLib = list(outputs_fromLib)
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
                        gvObj.fromPort = dictKeys[indexOf]
                        gvObj.definedNodeName = node_id
                        if gvObj.fromPort in obj.generatedVars:
                            raise Exception(f'Unhandled case: {gvObj.fromPort} in {obj.generatedVars}')
                        obj.generatedVars[gvObj.fromPort] = gvObj

                inputDict = obj.getConnectionInputs(True)
                execDict = obj.getConnectionOutputs(True)

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

                    inpId, portNameConn = inpId #unpack list

                    inpObj = codeInfo[inpId]
                    if inpObj.generatedVars.get(portNameConn):
                        # если сгенерированная переменная скоуповая и obj не в скоупах inpObj то исключ.
                        if inpObj.nodeType.name == "SCOPED_LOOP":
                            if inpObj not in obj.scopes:
                                self.exception(CGScopeLoopPortException,
                                    source=obj,
                                    portname=portNameConn,
                                    target=inpObj)
                            # Вторая проверка на лоченные пути
                            connectedToSkipped = self.dpdGraphExt[inpObj.nodeId]['out']['При завершении']
                            if connectedToSkipped:
                                connTpsList = connectedToSkipped[0] #к завершающему условию всегда только один пайп
                                # конвертируем в айди узла и какому порту он подключен
                                connToId, connToPort = list(connTpsList.items())[0]
                                if codeInfo[connToId] == obj:
                                    if inpObj in obj.scopes:
                                        self.exception(CGScopeLoopPortException,
                                            source=obj,
                                            portname=portNameConn,
                                            target=inpObj)    
                                #else:
                                #    self.exception(CGUnhandledObjectException,source=obj,context="Несоответствие узла {src} при сравнении подключений и валидации логики области видимости")

                        lvarObj = inpObj.generatedVars.get(portNameConn)
                        lvarObj.isUsed = True
                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)', f"{lvarObj.localName}", node_code)

                    if inpObj.isReady:

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

                    outId, portNameConn = outId #unpack list

                    outputObj = codeInfo[outId]

                    # нечего заменять
                    if not re.findall(f'@out\.{index+1}(?=\D|$)',node_code):
                        continue

                    if outputObj.isReady:
                        
                        objScope = outputObj.getScopeObj()
                        #todo objScope is nearTo outputObj -> exception , other case noexception
                        
                        # !TODO-> REMOVE: 
                        # if obj.nodeType.name == "SCOPED_LOOP" and output_name == "При завершении" and objScope:
                        #     self.exception(CGScopeLoopPortException,
                        #         source=outputObj,
                        #         target=obj,
                        #         portname=output_name
                        #         )
                        isNotChildLoop = obj != objScope
                        if objScope and objScope not in obj.scopes and isNotChildLoop:
                            loopId = objScope.nodeId
                            self.exception(CGScopeLoopException,
                                source=obj,
                                target=outputObj,
                                context=LoggerConsole.wrapNodeLink(self._sanitizeNodeName(loopId),loopId)
                                )

                        self.gObjType.handleReturnNode(codeInfo[entryId],obj,outputObj,self.gObjMeta)
                                         
                        node_code = re.sub(f"\@out\.{index+1}(?=\D|$)", outputObj.code, node_code) 

                # prepare if all replaced
                if "@in." not in node_code and "@out." not in node_code:
                    obj.isReady = True

                #update code
                if not hasAnyChanges:
                    hasAnyChanges = obj.code != node_code
                obj.code = node_code

                if obj.isReady:
                    self.gObjType.handleReadyNode(obj,codeInfo[entryId],self.gObjMeta)

            # --- post check stack
            readyCount = 0
            for i in codeInfo.values():
                if i.isReady:
                    readyCount += 1
        
        self.gObjType.handlePostReadyEntry(codeInfo[entryId],self.gObjMeta)

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
            # strInfo = "\n\t".join([LoggerConsole.wrapNodeLink(self._sanitizeNodeName(s.nodeId),s.nodeId) for s in errList])
            # if not strInfo: 
            #     strInfo = "-отсутствуют-" 
            # else: 
            #     strInfo = "\n\t" + strInfo
            errLen = len(self._exceptions) - curExceptions
            warnLen = len(self._warnings) - curWarnings
            self.error(f'Точка входа {LoggerConsole.wrapNodeLink(self._sanitizeNodeName(entryObj.nodeId),entryObj.nodeId)} не обработана: <b><span style="color:red">{errLen} ошибок,</span> <span style="color:yellow">{warnLen} предупреждений</span></b><br/>')


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
        if varCat == "localvar":
            code = f"{nameid}" if isGet else f"{nameid} = @in.2; @out.1"
        elif varCat == "classvar":
            code = f"this getVariable \"{nameid}\"" if isGet else f"this setVariable [\"{nameid}\", @in.2]; @out.1"
        else:
            raise Exception(f'Unknown variable getter type {varCat}')
        
        return code,varPortName,isGet,varCat

    # returns map: key
    def getExecPins(self,id,retPortname=False):
        return self.getConnectionsMap(self.ConnectionType.Output,id,retPortname)
    
    def getInputs(self,id,retPortname=False):
        return self.getConnectionsMap(self.ConnectionType.Input,id,retPortname)

    class ConnectionType(enum.Enum):
        Input = 0,
        Output = 1

    def getConnectionsMap(self,ct : ConnectionType, nodeid,retPortName = False):
        connections = self.serialized_graph['connections']
        searchedKey = "out" if ct == self.ConnectionType.Output else "in"
        invertKey = "in" if ct == self.ConnectionType.Output else "out"
        dictret = {}
        for itm in connections:
            if (itm[searchedKey][0] == nodeid):
                if retPortName:
                    dictret[itm[searchedKey][1]] = itm[invertKey]
                else:
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
        if value is None: return "null"
        if value == "NULL": return value
        if not tname: return value

        vObj,dtObj = self.getVariableManager().getVarDataByType(tname)
        dtName = dtObj.dataType

        if dtName != "value":
            if dtName == "array":
                evaluated = ["[ "]
                for v in value:
                    if len(evaluated) > 1: evaluated.append(", ")
                    evaluated.append(self.updateValueDataForType(v,vObj.variableType))
                evaluated.append(" ]")
                return "".join(evaluated)
            elif dtName == "dict":
                evaluated = ["(createHASHMAPfromArray[ "]
                objStack = []
                if not isinstance(vObj,list): raise Exception(f"Wrong dict type: {vObj}")
                for key,val in value.items():
                    if objStack: objStack.append(", ")

                    objStack.append("[")
                    objStack.append(self.updateValueDataForType(key,vObj[0].variableType))
                    objStack.append(", ")
                    objStack.append(self.updateValueDataForType(val,vObj[1].variableType))
                    objStack.append("]")
                
                evaluated.extend(objStack)
                evaluated.append(" ])")
                return "".join(evaluated)
            elif dtName == "set":
                evaluated = ["([ "]
                for v in value:
                    if len(evaluated) > 1: evaluated.append(", ")
                    evaluated.append(self.updateValueDataForType(v,vObj.variableType))
                evaluated.append(" ]createHASHMAPfromArray [])")
                return "".join(evaluated)
            else:
                raise Exception(f"Unsupported data type: {dtName}")
        
        if tname == "string": 
            strData = "\"" + value.replace("\"","\"\"") + "\""
            if "\n" in strData:
                isBigString = False
                allAmount = 0
                # кастомный алгоритм определения метода аллокации строчки
                for idx,line in enumerate(strData.split("\n")):
                    if len(line) > 32:
                        isBigString = True
                        break
                    allAmount += len(line)
                    if allAmount > 255:
                        isBigString = True
                        break
                    if idx > 32:
                        isBigString = True
                        break
                
                if isBigString:
                    return "(["+strData.replace("\n","\",\"")+"]joinString ENDL)"
                else:
                    return "("+strData.replace("\n","\"+\"")+")"
            else: 
                return strData
        elif tname == "bool":
            return str(value).lower()
        elif tname in ['float','int']:
            return str(value)
        elif self.getVariableManager().isObjectType(tname):
            return value
        elif re.match('vector\d+',tname):
            return self.updateValueDataForType(value,"array[float]")
        elif tname == "color":
            return self.updateValueDataForType(value,"array[float]")
        elif tname in ['handle','model']:
            return str(value)
        else:
            if not self.isDebugMode(): 
                raise Exception(f"Unknown type {tname} (value: {value} ({type(value)}))")
            else:
                self.warning("Cant repr type value: {} = {} ({})".format(tname,value,type(value)))

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
        exText = ex.getExceptionText(addDesc=True)
        if exText in [regEx.getExceptionText(addDesc=True) for regEx in self._exceptions]:
            #skip exception duplicate
            self.warning(f"<span style='font-size:8px;'>Подавление дубликата исключения ({ex.__class__.__name__})</span>")
            return
        self.error(exText)
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

    def nodeWarn(self,
                    exType,source:NodeData | None=None,
                    portname:str|None=None,
                    target:NodeData | None=None, 
                    entry:NodeData | None=None,
                    context=None):
        """
        Предупреждающее сообщение для узлов
        """

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
        wrnObj : CGBaseWarning = exType(**params)
        self.warning(wrnObj.getWarningText(addDesc=True))

        self._warnings.append(wrnObj)
    
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
        
        orig.view.text_item.setHtml(orig.view.text_item.toHtml() + name)
        orig.view.draw_node()
        
        
        #oldName = orig.name()
        #orig.set_name(oldName+name)
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

                items = dictLib['outputs'].items()
                startIndex = 0
                lastIndex = len(items) - 1
                metaKeyword = "@thisParams"

                mRange = re.findall("\@thisParams\.(\d+)\-(\d+)",code)
                if mRange:
                    mItems = mRange[0]
                    metaKeyword += ".{}-{}".format(mItems[0],mItems[1])
                    startIndex = int(mItems[0])-1
                    lastIndex = int(mItems[1])-1

                if metaKeyword not in code: raise Exception(f"Meta keyword error: {metaKeyword} -> {code}")

                paramList = ['\'this\'']
                for indexVar, (outKey,outValues) in enumerate(items):
                    #((numberToCheck) >= bottom && (numberToCheck) <= top)
                    inRange = indexVar >= startIndex and indexVar <= lastIndex
                    if not inRange: continue

                    if outValues['type'] != "Exec" and outValues['type'] != "":
                        paramList.append('\"@genvar.out.{}\"'.format(indexVar+1))
                
                paramCtx = f'params [{", ".join(paramList)}]'
                #adding initvars keyword
                paramCtx += "; @initvars"
                code = code.replace(metaKeyword,paramCtx)
        
        return code