from collections import defaultdict
import json
import re
import enum
import os
from copy import deepcopy
import asyncio
from ReNode.app.CodeGenExceptions import *
from ReNode.app.CodeGenWarnings import *
from ReNode.app.Logger import *
from ReNode.ui.LoggerConsole import LoggerConsole
from ReNode.ui.GraphTypes import *
from ReNode.ui.VariableManager import VariableManager
from ReNode.app.NodeFactory import NodeFactory
from ReNode.app.FileManager import FileManagerHelper
from ReNode.app.Constants import NodeLambdaType
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
    def getScopedLoopNodes(): return ["operators.for_loop","operators.foreach_loop","operators.while_loop"]

    @staticmethod
    def getNodeType(classname:str):
        if classname in NodeDataType.getScopedLoopNodes():
            return NodeDataType.SCOPED_LOOP
        elif classname.startswith("operators."):
            return NodeDataType.OPERATOR
        
        return NodeDataType.NODE

class NodeGraphProxyObject:
    def __init__(self,graphPath):

        sergraph = FileManagerHelper.loadSessionJson(graphPath)

        self.serialized_graph = sergraph
        if sergraph != None:
            self.infoData = sergraph['graph']['info']
            self.variables = sergraph['graph']['variables']
        else:
            self.infoData = {}
            self.variables = {}
        
        if not FileManagerHelper.graphPathIsRoot(graphPath):
            graphPath = FileManagerHelper.graphPathToRoot(graphPath)
        
        self.graph_path = graphPath

    def get_nodes_by_class(self,cls):
        idlist = []
        for nid,ndat in self.serialized_graph['nodes'].items():
            if ndat['class_'] == cls:
                idlist.append(nid)
        return idlist
    
    def get_node_by_id(self,id):
        for nid,ndat in self.serialized_graph['nodes'].items():
            if nid == id:
                return ndat
        return None

class GeneratedVariable:
    def __init__(self,locname,definedNodeId):
        self.localName = locname #+ f'/*NODE:{definedNodeId}*/' #postcommnet for old parser validator
        self.definedNodeId = definedNodeId
        self.isUsed = False
        
        self.active = True
        self.fromPort = None
        self.definedNodeName = None
    
    def __repr__(self):
        return f"{self.definedNodeName}:{self.fromPort}({self.localName})"

class CodeGenerator:
    refLogger = None
    def __init__(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        if not CodeGenerator.refLogger:
            CodeGenerator.refLogger = RegisterLogger("CodeGen")
        self.logger = CodeGenerator.refLogger

        self.generated_code = ""
        self.graphsys = NodeGraphComponent.refObject
        self.graph = None #ref to graph qt

        self.serialized_graph = None

        self.compileParams = {}

        self._addComments = False # Добавляет мета-информацию внутрь кодовой структуры

        self._debug_info = False # Включать только для отладки: переименовывает комменты и имена узлов для проверки правильности генерации
        self._debug_rename = False #отладочная переименовка узлов

        #TODO: need write
        self._optimizeCodeSize = False # включает оптимизацию кода. Меньше разрмер 

        # те переменные, которые хоть раз используют установку или получение должны быть сгенерены
        self.localVariablesUsed = set()
        # любые локальные данные пишутся в это хранилище
        self.contextVariablesUsed = set()
        # ссылка на все созданные объекты локальных переменных в точке входа
        self.allGeneratedVarsInEntry = []

        self.gObjType : GraphTypeBase = None
        self.gObjMeta :dict[str:object]= None

        self.isGenerating = False
        self.successCompiled = False

    def getGraphTypeObject(self):
        """Получает объект типа графа"""
        gtype = self.graph.infoData['type']
        return GraphTypeFactory.getInstanceByType(gtype)

    def getNodeLibData(self,cls):
        return self.getFactory().getNodeLibData(cls)

    def getVariableManager(self) -> VariableManager:
        return self.graphsys.variable_manager

    def getVariableDict(self) -> dict:
        return self.graph.variables
    
    def getFactory(self) -> NodeFactory:
        return self.graphsys.nodeFactory

    def hasCompileParam(self,paramName):
        for kname,vdata in self.getAllCompileParams().items():
            if paramName == vdata.get("alias"):
                paramName = kname
                break
        return paramName in self.compileParams

    @staticmethod
    def getAllCompileParams():
        return {
            "-errbreak": {
                "alias": "-ebr",
                "desc": "Останавливает сборку при возникновении исключений во вермя генерации точек входа."
            },
            "-showgenpath": {
                "alias": "-sgp",
                "desc": "Показывает путь до графа при генерации."
            },
            "-failonwarn": {
                "alias": "-fow",
                "desc": "С этим флагом компиляция еденицы завершится провалом, если будет хотя бы одно предупреждение при генерации."
            },
            "-skipgenloader": {
                "alias": "-sld",
                "desc": "При указании этого флага пропускает генерацию загрузчика."
            },
            "-logexcept": {
                "alias": "-lgex",
                "desc": "Показывает исключения при генерации."
            },
            "-exceptinfo": {
                "alias": "-exinfo",
                "desc": "Выводит полные исключения при генерации."
            },
            "-logwarn": {
                "alias": "-lgwn",
                "desc": "Показывает предупреждения при генерации."
            },
            "-noupdatecguid": {
                "alias": "-nucg",
                "desc": "Отключает обновление гуида компиляции. Записывает текущий гуид в скомпилированный граф"
            }
        }

    def generateProcess(self,graph=None,addComments=True,silentMode=False,compileParams={},prefixGen=""):
        
        self._exceptions : list[CGBaseException] = [] #список исключений
        self._warnings : list[CGBaseWarning] = [] #список предупреждений
        self.dpdGraphExt = {}
        self.dependencyGraph = {} #обычные зависимости. Реальная ссылка
        self.gObjMeta = {}
        self.compileParams = compileParams
        
        self._addComments = addComments
        self._silentMode = silentMode

        if not graph:
            self.graph = self.graphsys.graph
        else:
            if isinstance(graph,str):
                self.graph = NodeGraphProxyObject(graph)
            else:
                self.graph = graph

        self.successCompiled = False

        try:
            timestamp = int(time.time()*1000.0)

            if isinstance(self.graph,NodeGraphProxyObject):
                layout_data = self.graph.serialized_graph
            else:
                layout_data = self.graph._serialize(self.graph.all_nodes())

            if not layout_data:
                self.exception(CGGraphSerializationError,context="Не найдена информация для генерации")
                raise CGCompileAbortException()
            if not layout_data.get('nodes'):
                self.warning("Добавьте узлы в граф")
                layout_data['nodes'] = {}
            if not layout_data.get('connections'):
                self.warning("Добавьте связи в граф")
                layout_data['connections'] = {}
            
            self.serialized_graph = layout_data
            #removing backdrops
            delIdList = []
            for name,node in layout_data['nodes'].items():
                if 'internal.backdrop' == node['class_']:
                    delIdList.append(name)
            for name in delIdList:
                del layout_data['nodes'][name]

            self._originalReferenceNames = dict() #тут хранятся оригинальные айди нодов при вызове генерации имен

            entrys = self.getAllEntryPoints()
            if not entrys:
                self.warning("Добавьте точки входа в граф (события, определения методов, и т.д.)")
            self.entryIdList = entrys #лист для валидации точек входа
            
            self.isGenerating = True
            
            if not self._silentMode: self._resetNodesError() 

            iData = self.graph.infoData
            if not self._silentMode: 
                self.log(f"Старт генерации графа \"{iData['name']}\"",True)
            else:
                pref__ = f" \"{self.graph.graph_path}\"" if self.hasCompileParam("-showgenpath") else ""
                self.log(f"{prefixGen}Генерация {iData['name']}{pref__}",True)
            
            code = "// Code generated:\n"
            # Данные локальных переменных: type(int), alias(_lv1), portname(Enumval), category(class,local)
            self.localVariableData = {}
            self.gObjType = self.getGraphTypeObject()
            self.gObjMeta = self.gObjType.createGenMetaInfoObject(self,iData)

            self.log("Генерация переменных")

            # generated lvdata for graph user vars (local,class, methods)
            for vcat,vval in self.getVariableDict().items():
                if vcat not in ["localvar","classvar"]:
                    continue
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
                        lvData['initvalue'] = self.updateValueDataForType(v['value'],v['type'],"lvar_init:"+v['name'])
                    ##elif vcat=='classvar':
                    #    lvData['alias'] = f"classMember_{i+1}"
                    else:
                        continue


            # generate classvars
            code += self.gObjType.cgHandleVariables(self.gObjMeta)

            self.log("Генерация свойств инспектора")

            # generate inspector props
            code += self.gObjType.cgHandleInspectorProps(self.gObjMeta)

            self.__generateNames(entrys)

            
            self._validateEntrys(entrys)

            self.log("Генерация связей")
            self.dpdGraphExt = self.createDpdGraphExt()

            self.log("Генерация кода узлов")
            generated_code = self.generateOrderedCode(entrys)
            code += "\n" + generated_code
            
            codeReal = self.gObjType.cgHandleWrapper(code,self.gObjMeta)
            #adding header
            code = f'//gdate:{datetime.datetime.now()}\n\n' + \
                    f'#include ".\\resdk_graph.h"\n'

            if self._exceptions:
                raise CGCompileAbortException()
            if self.hasCompileParam("-failonwarn") and self._warnings:
                raise CGCompileAbortException()

            iData = self.gObjMeta['infoData']
            graphName = FileManagerHelper.getCompiledScriptFilename(iData)
            
            #getting graph tab
            ssmgr = self.graphsys.sessionManager
            tDat = None
            if not self._silentMode:
                tDat = ssmgr.getTabByPredicate(lambda tab:tab.infoData.get('classname'),iData['classname'])
            if tDat:
                guidCompile = tDat.createCompilerGUID()
                code = f'//src:{guidCompile}:{tDat.filePath}\n' + code
                code += f'#define __THIS_GRAPH__ {tDat.filePath}\n\n\n'
            else:
                if not self._silentMode:
                    raise Exception("Cannot generate code in non-existen tab")
                fp__ = self.graph.graph_path
                guidCompile = ssmgr.CreateCompilerGUID()
                if self.hasCompileParam("-noupdatecguid"):
                    _oldcguid = FileManagerHelper.getCompiledGUIDByClass(iData['classname'])
                    if _oldcguid:
                        guidCompile = _oldcguid
                def __updEv(sergraph):
                    FileManagerHelper.allCompiledGUIDs[iData['classname']] = guidCompile
                    sergraph['graph']['info']['compileStatus'] = "Compiled"
                    #! только при ручном обновлении sergraph['graph']['info']['graphVersion'] = self.graphsys.getFactory().graphVersion
                    return True
                if not FileManagerHelper.updateSessionJson(FileManagerHelper.graphPathGetReal(fp__),__updEv):
                    raise self.exception(CGUnhandledException,context="Cant udpdate GUID inside graph")
                #save new graph with generated compile guid
                code = f'//src:{guidCompile}:{fp__}\n' + code
                code += f'#define __THIS_GRAPH__ {fp__}\n\n\n'
            
            code = code + codeReal

            if self.isDebugMode() and not self._silentMode:
                from PyQt5.QtWidgets import QApplication
                QApplication.clipboard().setText(code)

            #saving compiled code
            file_path = os.path.join(FileManagerHelper.getFolderCompiledScripts(),graphName)
            directory = os.path.dirname(file_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
            with open(file_path, "w+", encoding="utf-8") as file:
                file.write(code)

            #regen loaderlist
            if not self.hasCompileParam("-skipgenloader"):
                FileManagerHelper.generateScriptLoader(excludeGuid=guidCompile)

            self.successCompiled = True

        except CGCompileAbortException:
            pass
        except PermissionError as pererr:
            if pererr.errno == 13:
                self.exception(CGFileLockedError,context=pererr.filename or file_path)
            else:
                raise
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
            
        finally:
            
            self.log(f"\t- Предупреждений: {len(self._warnings)}; Ошибок: {len(self._exceptions)}")
            if self._exceptions:
                self.log("- <span style=\"color:red;\">Генерация завершена с ошибками</span>")
            else:
                self.log("- <span style=\"color:green;\">Генерация завершена</span>")
            
            timeDiff = int(time.time()*1000.0) - timestamp
            if not self.successCompiled or self._exceptions:
                self.warning("Граф не скомпилирован")
            else:
                self.log("Граф скомпилирован и сохранён")
            dtcomp = datetime.datetime.now().strftime("%H:%M:%S.%f")
            self.log(f"Процедура завершена в {dtcomp} за {timeDiff} мс")
            self.log("================================")
            self.isGenerating = False
            iData = self.graph.infoData

            if self._silentMode:
                pref__ = f" PATH:\"{self.graph.graph_path}\"" if self.hasCompileParam("-showgenpath") else ""
                notCompiled__ = not self.successCompiled or bool(self._exceptions)
                pfunc_ = self.error if notCompiled__ else self.log
                basetex_ = f"[{'ERR' if notCompiled__ else 'OK'}] Результат сборки {iData['name']}"
                # multiply to 40
                basetex_ += max(80-len(basetex_),0)*"-"
                pfunc_(f"{basetex_}: {timeDiff}ms; ERR:{len(self._exceptions)};WRN:{len(self._warnings)};{pref__}",True)

                if self.hasCompileParam("-logexcept") and self._exceptions:
                    elst__ = ','.join(list(set([e.id.__str__() for e in self._exceptions])))
                    self.log(f"\tИсключения для {iData['name']}: {elst__}",True)
                if self.hasCompileParam("-logwarn") and self._warnings:
                    elst__ = ','.join(list(set([e.id.__str__() for e in self._warnings])))
                    self.log(f"\tПредупреждения для {iData['name']}: {elst__}",True)

                hasErrors__ = bool(self._exceptions)
                if self.hasCompileParam("-failonwarn"):
                    hasErrors__ = hasErrors__ or bool(self._warnings)
                return not hasErrors__ #is success compiled (true)

            ssmgr = self.graphsys.sessionManager
            tDat = ssmgr.getTabByPredicate(lambda tab:tab.infoData.get('classname'),iData['classname'])
            if tDat:
                tDat.setCompileState(self.successCompiled,bool(self._exceptions),bool(self._warnings))

            if self.successCompiled and not self._exceptions:
                if tDat:
                    tDat.save() #saving on success compile
                #self.warning("Сохраните ваш граф после успешной компиляции")

            if self._warnings or self._exceptions:
                self.graphsys.log_dock.setVisible(True)

            #cleanup data
            #self._exceptions.clear()
            #self._warnings.clear()
            self.gObjMeta.clear()
            self.dpdGraphExt.clear()
            
            return self.successCompiled

    def __generateNames(self,entry : list):
        import copy
        unicalNameDict = dict()
        self._originalReferenceNames = dict()
        uniIdx = 0

        nameCounter = {}
        idat = self.gObjMeta['infoData']
        thisName = idat['name']
        thisClassname = idat['classname']
        increment = -1
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

            increment += 1
            v['increment_uid'] = increment

            if self._debug_rename and not self._silentMode:
                #self.graphsys.graph.get_node_by_id(k).set_name(newname)
                node = self.graph.get_node_by_id(k)
                
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

        #check defined functions
        for vid,vdat in self.getVariableDict().get("classfunc",{}).items():
            instTypename = self.getVariableManager().getVariableNodeNameById(vid,"deffunc",
                refVarDict=self.graph.variables,
                refInfoData=self.graph.infoData)
            if instTypename:
                nodeList = self.graph.get_nodes_by_class(instTypename)
                if not nodeList:
                    ctxInfo = f'{vdat["name"]} ({instTypename})'
                    self.exception(CGUserEntryNotDefinedException,context=ctxInfo)

        for ent in entrys:
            entData = self.serialized_graph['nodes'][ent]
            checkedKey = entData['class_']

            #skip check for lambda entry's
            if NodeLambdaType.isLambdaEntryNode(checkedKey): continue

            #userfunc validate
            nodeObj = entNodeData[ent]
            if nodeObj.getUserNodeId():
                userId = nodeObj.getUserNodeId()
                checkedKey = userId

            if checkedKey in entDict:
                src = entNodeData[ent]
                entObj = entNodeData[entDict[checkedKey]]
                self.exception(CGDuplicateEntryException,source=src,entry=entObj)
            entDict[checkedKey] = ent
        del entDict

    def generateOrderedCode(self, entrys):
    
        self.log("    Создание зависимостей")
        # Создание графа зависимостей
        graph = self.createDependencyGraph(collectOnlyExecutePins=True)
        self.dependencyGraph = graph

        code = ""

        for i,ent in enumerate(entrys):
            self.log(f"    -------- Генерация точки входа \"{ent}\" {i+1}/{len(entrys)}")

            self.localVariablesUsed = set()
            self.contextVariablesUsed = set()
            
            graph = self.dependencyGraph #get original reference

            entryObj = self.serialized_graph['nodes'][ent]
            entryClass = entryObj['class_']
            
            isLambdaEntry = NodeLambdaType.isLambdaEntryNode(entryClass)
            restoredConnections = []

            if isLambdaEntry:
                #Если в лямбде нет подключений - пропускаем её компиляцию
                if not self.getConnectionsMap(CodeGenerator.ConnectionType.Input,ent) and \
                    not self.getConnectionsMap(CodeGenerator.ConnectionType.Output,ent):
                    self.nodeWarn(CGLocalFunctionNotUsed,source=ent)
                    continue
                
                #remove connections and regenerate dependency graph
                _connectionsList :list[dict] = self.serialized_graph.get('connections',[])
                for connDict in _connectionsList:
                    if connDict['out'][0] == ent and connDict['out'][1] == 'lambda_ref':
                        restoredConnections.append(connDict)
                    elif connDict['in'][0] == ent and connDict['in'][1] == 'lambda_ref':
                        restoredConnections.append(connDict)
                #second pass: removing connections
                for cdel in restoredConnections:
                    _connectionsList.remove(cdel)
                #generate new graph
                graph = self.createDependencyGraph(collectOnlyExecutePins=True)

            topological_order = self.topologicalSort(ent, graph)
            
            generatedCode = ""
            if self._addComments:
                generatedCode += f"\n//p_entry: {entryClass}\n"
            generatedCode += self.generateFromTopology(topological_order,ent)
            if not isLambdaEntry:
                code += generatedCode

            if self.hasCompileParam("-errbreak"):
                break

            #restore connection
            if restoredConnections:
                if not isLambdaEntry:
                    raise Exception("Restore connection error logic - entry is not lambda")
                for c in restoredConnections:
                    self.serialized_graph['connections'].append(c)

        self.log("Форматирование")

        return self.formatCode(code)

    def getPortInputType(self,node,port): 
        ndata = self.serialized_graph['nodes'][node]
        if ndata.get("port_deletion_allowed"):
            return next((pinfo['type'] for pinfo in ndata['input_ports'] if pinfo['name'] == port),None)
        else:
            return self.getNodeLibData(ndata['class_']) ['inputs'][port].get("type")
    def getPortOutputType(self,node,port): 
        ndata = self.serialized_graph['nodes'][node]
        prez = 'null_type_get_port_out'
        if ndata.get("port_deletion_allowed"):
            prez = next((pinfo['type'] for pinfo in ndata['output_ports'] if pinfo['name'] == port),None)
        else:
            nld__ = self.getNodeLibData(ndata['class_']) 
            prez =  nld__['outputs'][port].get("type")
            
            if prez == "auto_object_type":
                for k,v in nld__.get('outputs',{}).items():
                    if v['type'] == 'auto_object_type' and k == port:
                        for o_name,o_vals in nld__.get("options").items():
                            if o_vals.get("type") == "typeselect" and o_vals.get('typeset_out') == k:
                                newptype = ndata.get('custom',{}).get(o_name,"")
                                if newptype:
                                    if not newptype.endswith("^"):
                                        newptype += "^"
                                    prez = newptype
                                    break

        return prez

    def getPortNames_Runtime(self,node,tps):
        ndata = self.serialized_graph['nodes'][node]
        if ndata.get("port_deletion_allowed"):
            return [pinfo['name'] for pinfo in ndata['input_ports' if tps=='in' else 'output_ports'] ]
        else:
            return [pinfo for pinfo in self.getNodeLibData(ndata['class_']) ['inputs' if tps=='in' else 'outputs'].keys() ]

    def createDependencyGraph(self,collectOnlyExecutePins=False):

        graph = defaultdict(list)
        for connection in self.serialized_graph['connections']:
            input_node, portInName = connection["in"]
            output_node, portOutName = connection["out"]
            if collectOnlyExecutePins:
                #typeIn = self.getPortInputType(input_node, portInName)
                #typeOut = self.getPortOutputType(output_node, portOutName)
                pass
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

        idat = self.gObjMeta['infoData']
        thisName = idat['name']
        thisClassname = idat['classname']
        classData = self.getNodeLibData(self.serialized_graph['nodes'][nodename]['class_'])
        #todo fix types and names for objects.thisObject

        inNodeInfo = self.getPortNames_Runtime(nodename,'in')
        for portName in inNodeInfo:
            _realName = portName.replace("thisName",thisName).replace("thisClassname",thisClassname)
            _realType = self.getPortInputType(nodename,portName).replace("thisName",thisName).replace("thisClassname",thisClassname)
            ref['typein'][_realName] = _realType
        outNodeInfo = self.getPortNames_Runtime(nodename,'out')
        for portName in outNodeInfo:
            _realName = portName.replace("thisName",thisName).replace("thisClassname",thisClassname)
            _realType = self.getPortOutputType(nodename,portName).replace("thisName",thisName).replace("thisClassname",thisClassname)
            if _realType == "auto_object_type":
                pass
            ref['typeout'][_realName] = _realType

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

    class ExecScope:
        def __init__(self,src,port,scopeLevel=0):
            self.scopeLevel = scopeLevel
            self.sourceObj = src
            self.portName = port
            self.isLoopScope = False

            self.generatedVars = []

        def __repr__(self) -> str:
            return f'[LV:{self.scopeLevel}] {self.sourceObj} ({self.portName})'
        #overload comparison
        def __eq__(self, __value: object) -> bool:
            if isinstance(__value, self.__class__):
                return self.sourceObj == __value.sourceObj
            else:
                return False
        def __ne__(self, __value: object) -> bool:
            return not (self == __value)

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

            self.scopes = [] #области видимости в узле

            self.hasError = False

            self._initNodeClassData()
            self._defineNodeType()

            #user nodes section
            self.userNodeType = None

            #системные данные, генерируемые при сборке графа
            self._uid = -1
            self._pure = False

        def getUserNodeType(self):
            """Получает тип пользовательской переменной"""
            nameid = self.objectData.get("custom",{}).get("nameid")
            if not nameid: return None
            cat = self.refCodegen.getVariableManager().getVariableCategoryById(nameid,refVarDict=self.graph.variables)
            if not cat: return
            return cat

        def getUserNodeId(self):
            return self.objectData.get("custom",{}).get("nameid")

        def __repr__(self) -> str:
            return f'ND:{self.nodeId} ({self.nodeClass})'

        def _initNodeClassData(self):
            node_data = self.refCodegen.serialized_graph['nodes'][self.nodeId]
            self.objectData = node_data
            self.nodeClass = node_data['class_']
            
            self.classLibData = deepcopy(self.refCodegen.getNodeLibData(self.nodeClass)) #копирвание потому что исходная дата может измениться при runtime_ports и т.д.

            for k,v in self.classLibData.get('outputs',{}).items():
                if v['type'] == 'auto_object_type':
                    for o_name,o_vals in self.classLibData.get("options").items():
                        if o_vals.get("type") == "typeselect" and o_vals.get('typeset_out') == k:
                            newptype = node_data.get('custom',{}).get(o_name,"")
                            if newptype:
                                if not newptype.endswith("^"):
                                    newptype += "^"
                                v['type'] = newptype
                                break


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
            return cg.graph.get_node_by_id(nodeid)
    
        def markAsError(self):
            if not self.hasError:
                self.hasError = True
                return True
            return False

    def getNodeObjectById(self,nodeid):
            cg = self
            nodeid = cg._sanitizeNodeName(nodeid)
            return cg.graph.get_node_by_id(nodeid)

    def getAllNodesFromPort(self,fromNodeId,ptype,portname):
        """Получает все узлы, подключенные прямо или косвенно к порту portname узла fromNodeId. ptype - in/out"""
        baseConnList = self.dpdGraphExt[fromNodeId][ptype].get(portname,[])#list of dicts {nodeId:portconn}
        listref = []
        visitedNodes = {node: False for node in self.dpdGraphExt.keys()}
        visitedNodes[fromNodeId] = True

        def __recNodeGet(nodeId):
            ndeplist = self.dependencyGraph[nodeId]
            if not visitedNodes[nodeId]:
                visitedNodes[nodeId] = True
                listref.append(nodeId)
                for cnid in ndeplist:
                    __recNodeGet(cnid)
        
        for connElem in baseConnList:
            for nod in connElem.keys():
                __recNodeGet(nod)

        return listref

    def generateFromTopology(self, topological_order, entryId):

        curExceptions = len(self._exceptions)
        curWarnings = len(self._warnings)

        codeInfo = {nodeid:CodeGenerator.NodeData(nodeid,self) for nodeid in topological_order}
        entryObj = codeInfo[entryId]

        readyCount = 0
        hasAnyChanges = True # true for enter
        iteration = 0
        

        allGeneratedVars = [] #список всех сгенерированных локальных переменных
        self.allGeneratedVarsInEntry = allGeneratedVars #refset
        isLambdaEntry = NodeLambdaType.isLambdaEntryNode(codeInfo[entryId].nodeClass)
        isContextLambdaEntry = NodeLambdaType.hasContextInLambdaType(codeInfo[entryId].nodeClass)

        #check selfobject
        if isLambdaEntry and not isContextLambdaEntry:
            for nObj in codeInfo.values():
                if nObj.nodeClass == "objects.thisObject":
                    self.exception(CGEntrySelfObjectRefUnsupported,source=nObj,entry=codeInfo[entryId])

        # Проверка на присутствие использования одних точек входа в других
        for ent in self.entryIdList:
            if ent in topological_order[1:]:
                if not NodeLambdaType.isLambdaEntryNode(codeInfo[ent].nodeClass) and not isLambdaEntry:
                    self.exception(CGEntryCrossCompileException,source=codeInfo[ent],entry=codeInfo[entryId])
                    hasAnyChanges = False
                    break
        
        refLambdaNodes = [] #то что подключено к lambda_ref
        if isLambdaEntry:
            #remove lambda_ref from entry
            lambdaRefPortname = "lambda_ref"
            refLambdaNodes = self.getAllNodesFromPort(entryId,"out",lambdaRefPortname)
            lr__ = self.dpdGraphExt[entryId]['out']['lambda_ref']
            if lr__:
                #lambdaSource = list(self.dpdGraphExt[entryId]['out']['Цель'][0].keys())[0]
                pass 
            else:
                self.nodeWarn(CGLambdaRefNotUsedWarning,source=entryObj,portname=lambdaRefPortname)

            #validate invalid node in anonfunc entry
            for o in codeInfo.values():
                ncl_ = o.nodeClass
                
                if "control.callafter" in ncl_:
                    self.exception(CGEntryLocalFunctionInvalidNode,source=o,entry=codeInfo[entryId])
                if 'operators.flipflop' in ncl_ and not NodeLambdaType.hasContextInLambdaType(ncl_):
                    self.exception(CGEntryLocalFunctionInvalidNode,source=o,entry=codeInfo[entryId])

        self.gObjType.handlePreStartEntry(codeInfo[entryId],self.gObjMeta)

        #генерация переменных
        for k,obj in codeInfo.items():
            clsName = obj.nodeClass
            if clsName.startswith("fields.") and clsName.endswith("_0.set"):
                # умная генерация локальной переменной выхода
                if obj.getConnectionOutputs().get("Новое значение"):
                    oldCode = obj.code
                    obj.code = "private @genvar.out.2 = @in.3;" + re.sub(f'@in\.3(?=\D|$)', f"@locvar.out.2", oldCode)
            
            if clsName == "control.supercall":
                rempart = "private @genvar.out.2 = "
                if isLambdaEntry:
                    self.exception(CGEntryLambdaSuperNotSupported,source=obj,entry=codeInfo[entryId])
                    break
                rtp = entryObj.classLibData['returnType']
                if rtp=='null':
                    obj.code = obj.code.replace(rempart,"")
                    if obj.getConnectionOutputs().get("Значение"):
                        self.exception(CGSuperVoidReturnException,source=obj)
                        return "//ex:CGSuperVoidReturnException\n"
            
            isPure = True
            if "Exec" in [t.get("type") for t in obj.classLibData['inputs'].values()] or \
                "Exec" in [t.get("type") for t in obj.classLibData['outputs'].values()]:
                isPure = False
            nobj = obj.getNodeObject()
            increment = -1
            if isinstance(nobj,dict):
                increment =  nobj.get('increment_uid',-2)
            else:
                increment = nobj.uid
            
            # ! это вызовет ошибку для runtime nodes
            obj._isPure = isPure
            obj._uid = increment
            #if isPure:
            #    obj.code = f'\nBP_PS({increment}) {obj.code} BP_PE'
            #else:
            #    obj.code = f'BP_EXEC({increment})\n {obj.code}'

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

                isCustomVariable = False
                isCustomFunction = False
                isFunctionCall = node_className.startswith("func.")

                #определяем является ли эта переменная кастомной
                if obj_data.get('custom',{}).get('nameid'):
                    catvar = self.getVariableManager().getVariableCategoryById(obj_data['custom'].get('nameid'),refVarDict=self.graph.variables)
                    isCustomVariable = catvar in ['localvar','classvar']
                    isCustomFunction = catvar in ["classfunc"]

                hasRuntimePorts = class_data.get('runtime_ports')

                inputs_fromLib = class_data['inputs'].items()
                outputs_fromLib = class_data['outputs'].items()

                if isCustomVariable:
                    nameid = obj_data['custom']['nameid']
                    #define variable code
                    generated_code, portName, isGet,varCat = self.getVariableData(node_className,nameid,optObj=obj)
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
                                if not NodeLambdaType.hasContextInLambdaType(entryObj.nodeClass):
                                    self.exception(CGLocalVariableDuplicateUseException,source=obj,context=self.localVariableData[nameid]['varname'],entry=entryObj,target=usedIn)
                        lvar_alias = self.localVariableData[nameid]['alias']
                        node_code = generated_code.replace(nameid,lvar_alias)
                        if isGet:
                            self.contextVariablesUsed.add(lvar_alias)
                        if isSet:
                            #for pass local variables
                            self.contextVariablesUsed.add(lvar_alias)
                            
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
        
                if isCustomFunction:
                    isEntryPoint = node_id == entryId
                    nameid = obj_data['custom']['nameid']
                    
                    #first alloc entry
                    if node_code == "RUNTIME":
                        if isEntryPoint:
                            self.exception(CGUnhandledObjectException,source=obj,context="Пользовательская точка входа не содержит сгенерированного кода")
                        
                        userdata = self.getVariableManager().getVariableDataById(nameid,refVarDict=self.graph.variables)
                        
                        # обновление портов
                        newInputs = {}
                        newOutputs = {}
                        
                        for portDict in obj_data['input_ports']:
                            newInputs[portDict['name']] = {
                                'type': portDict['type']
                            }
                        for portDict in obj_data['output_ports']:
                            newOutputs[portDict['name']] = {
                                'type': portDict['type']
                            }
                        class_data['inputs'] = newInputs
                        class_data['outputs'] = newOutputs

                        #update classmeta
                        class_data['classInfo'] = {
                            "class": self.gObjMeta['classname'],
                            "name": userdata['name'].lower(),
                            "type": "method",
                        }
                        #update return type
                        class_data['returnType'] = userdata['returnType']

                        #update local vars
                        inputs_fromLib = newInputs.items()
                        outputs_fromLib = newOutputs.items()

                        # первичная генерация
                        newcode = self.getFunctionData(node_className,nameid,obj)
                        node_code = newcode

                if isFunctionCall and "@cfParams" in node_code:
                    inputDict = obj.getConnectionInputs(True)
                    paramList = []
                    for _idxPort, (pname,pdat) in enumerate(inputs_fromLib):
                        iInfo = inputDict.get(pname)
                        _tpval = pdat['type']
                        #needConn = pdat.get('require_connection',True)
                        #_hasConnected = iInfo
                        if _tpval!="Exec": #and  _tpval!="":
                            paramList.append(f"@in.{_idxPort+1}")
                    
                    replcode_ = "[" + ", ".join(paramList) + "]"
                    node_code = re.sub(f'@cfParams',lambda _:replcode_,node_code)

                if "@genport." in node_code and hasRuntimePorts:
                    # обновление портов
                    #TODO вынести в функцию с проверками
                    newInputs = {}
                    newOutputs = {}
                    
                    for portDict in obj_data['input_ports']:
                        newInputs[portDict['name']] = {
                            'type': portDict['type']
                        }
                    for portDict in obj_data['output_ports']:
                        newOutputs[portDict['name']] = {
                            'type': portDict['type']
                        }
                    class_data['inputs'] = newInputs
                    class_data['outputs'] = newOutputs
                    #update types
                    inputs_fromLib = newInputs.items()
                    outputs_fromLib = newOutputs.items()
                    
                    #------------- genvar ports process ---------------
                    while True:
                        rez = re.search(r'(@genport\.(in|out)\.(\d+)\((.*?)\))',node_code)
                        if not rez: break
                        fullPattern,portType, portNumber, delimConnector = rez.groups()

                        # prep ports
                        mpInfo = class_data['options'].get('makeport_'+portType,{})
                        formatter = mpInfo.get('text_format')
                        sourcePort = mpInfo.get('src')
                        portNumber = int(portNumber)
                        basePortIndex = portNumber-1
                        isParamMaker = delimConnector == 'paramGen'
                        if isParamMaker: delimConnector = ", "
                        resultReplacerList = []
                        collectionPorts = class_data['inputs' if portType == 'in' else 'outputs'].keys()
                        for _iPort, _portColName in enumerate(collectionPorts):
                            _baseIPort = _iPort
                            if _iPort>=basePortIndex:
                                _iPort-=basePortIndex
                            if formatter == None or formatter.format(value=_iPort+1,index=_iPort) == _portColName:
                                if _baseIPort+1 >= portNumber:
                                    if isParamMaker:
                                        if portType != "out":
                                            self.exception(CGInternalCompilerError,source=obj,context=f'Code genport connection type error: {fullPattern}')
                                            break
                                        resultReplacerList.append(f'\'@genvar.{portType}.{_baseIPort+1}\'')
                                    else:
                                        resultReplacerList.append(f'@{portType}.{_baseIPort+1}')
                        
                        replStr = delimConnector.join(resultReplacerList)
                        if isParamMaker:
                            if replStr: 
                                replStr = f'/*gp-gen*/params[{replStr}]; SCOPEname \"exec\";'
                            else:
                                replStr = 'SCOPEname \"exec\";'
                        
                        node_code = node_code.replace(fullPattern,replStr)

                    pass

                if "@genvar." in node_code:
                    #pat = r'@genvar\.(\w+\.\d+)(\.internal\((.*?)\))?'
                    pat = r'(@genvar\.(\w+\.\d+)((?:\.\w+\([^()]*\))*))'
                    patParams = r'(\w+)\(([^()]*)\)'
                    dictKeys = [k for i,(k,v) in enumerate(outputs_fromLib)]
                    dictValues = [v for i,(k,v) in enumerate(outputs_fromLib)]
                    genCount = 0
                    while True:
                        matchObj = re.search(pat, node_code)
                        if not matchObj: break
                        fullTextTemplate, ptypeInfo, optionals = matchObj.groups()

                        lvar = f'_lvar_{index_stack}_{genCount}' #do not change
                        wordpart = re.sub('\.\d+','',ptypeInfo)
                        if wordpart != 'out':
                            self.exception(CGInternalCompilerError,source=obj,context=f'Pattern port type error (expected "out"): {fullTextTemplate}')
                            break
                        numpart = re.sub('\w+\.','',ptypeInfo)
                        indexOf = int(numpart)-1
                        genCount += 1
                        replacerInfo = lvar

                        if optionals:
                            for opt in optionals[1:].split('.'):
                                matchParamsObj = re.search(patParams, opt)
                                if not matchParamsObj: 
                                    self.exception(CGInternalCompilerError,source=obj,context=f'Pattern param error: {fullTextTemplate}')
                                    break
                                if len(matchParamsObj.groups()) != 2: 
                                    self.exception(CGInternalCompilerError,source=obj,context=f'Pattern param count error: {fullTextTemplate}')
                                    break
                                paramName, paramValue = matchParamsObj.groups()
                                if paramName == 'internal':
                                    replacerInfo = ''
                                    lvar = paramValue
                                elif paramName == 'iterator':
                                    lvar = f"__it{paramValue}{index_stack}_{genCount}"
                                    replacerInfo = f'private {lvar} = {paramValue};'
                                else:
                                    self.exception(CGInternalCompilerError,source=obj,context=f'Unknown option {paramName} in pattern: {fullTextTemplate}')
                                    break
                        #replacers
                        node_code = node_code.replace(fullTextTemplate, replacerInfo)
                        node_code = re.sub(f'@locvar\.{wordpart}\.{numpart}(?=\D|$)',lambda _:replacerInfo,node_code)
                        
                        # create var
                        gvObj = GeneratedVariable(lvar,node_id)
                        gvObj.fromPort = dictKeys[indexOf]
                        gvObj.definedNodeName = node_id
                        if gvObj.fromPort in obj.generatedVars:
                            raise Exception(f'Unhandled case: node {obj.nodeClass} from port {gvObj.fromPort} in {obj.generatedVars}')
                        obj.generatedVars[gvObj.fromPort] = gvObj
                        
                        allGeneratedVars.append(gvObj)

                if "@gettype." in node_code:
                    pat = r'(@gettype\.(\w+\.\d+)((?:\.\w+\([^()]*\))*))'
                    patParams = r'(\w+)\(([^()]*)\)'
                    while True:
                        matchObj = re.search(pat, node_code)
                        if not matchObj: break
                        fullTextTemplate, ptypeInfo, optionals = matchObj.groups()

                        portType = re.sub('\.\d+','',ptypeInfo)
                        portIndex = int(re.sub('\w+\.','',ptypeInfo))-1
                        

                        #allocate port
                        storagePorts_ = inputs_fromLib if portType == 'in' else outputs_fromLib
                        curPortData = list(storagePorts_)[portIndex]
                        curPortName = curPortData[0]
                        curPortInfo = curPortData[1] #not actual info...
                        factType = obj.getConnectionType(portType,curPortName)

                        replacerInfo = f'{factType}'

                        if optionals:
                            for opt in optionals[1:].split('.'):
                                matchParamsObj = re.search(patParams, opt)
                                if not matchParamsObj: 
                                    self.exception(CGInternalCompilerError,source=obj,context=f'Gettype pattern param error: {fullTextTemplate}')
                                    break
                                if len(matchParamsObj.groups()) != 2: 
                                    self.exception(CGInternalCompilerError,source=obj,context=f'Gettype pattern param count error: {fullTextTemplate}')
                                    break
                                paramName, paramValue = matchParamsObj.groups()
                                if paramName == "clear_type":
                                    tpv = factType
                                    if not tpv: continue
                                    if tpv.startswith("enum."): tpv = tpv[5:]
                                    if tpv.endswith("^"): tpv = tpv[:-1]
                                    replacerInfo = tpv
                        
                        #replacers
                        node_code = node_code.replace(fullTextTemplate, replacerInfo)

                if "@gen_switch_on(" in node_code:
                    # __sv for 
                    pat = r'(@gen_switch_on\(([_\w]*)\))'
                    matchObj = re.search(pat, node_code)
                    switchType = None
                    if obj.nodeClass.endswith("int"): switchType = "int"
                    elif obj.nodeClass.endswith("float"): switchType = "float"
                    elif obj.nodeClass.endswith("string"): switchType = "string"
                    else:
                        raise Exception("Unhandled exception; Unknown switch type: " + obj.nodeClass)
                    
                    if matchObj:
                        fullTextTemplate, varComparer = matchObj.groups()

                        #update outputs for stack generator works...
                        newInputs = {}
                        newOutputs = {}
                        
                        for portDict in obj_data['input_ports']:
                            newInputs[portDict['name']] = {
                                'type': portDict['type']
                            }
                        for portDict in obj_data['output_ports']:
                            newOutputs[portDict['name']] = {
                                'type': portDict['type']
                            }
                        class_data['inputs'] = newInputs
                        class_data['outputs'] = newOutputs
                        #update types
                        inputs_fromLib = newInputs.items()
                        outputs_fromLib = newOutputs.items()

                        #for allports
                        allport_values__ = []
                        for i,(k) in enumerate(obj.objectData.get('output_ports',[])):
                            if i==0: continue
                            k = k['name']
                            if switchType=="string":
                                k = k.replace("\\n","\n").replace("\\t","\t")
                            k = self.updateValueDataForType(k,switchType)
                            allport_values__.append(f'if({varComparer}=={k})exitWith{{ @out.{i+1} }};')
                        __replCode = 'call {'+ "".join(allport_values__) + " @out.1}"
                        node_code = node_code.replace(fullTextTemplate, __replCode)


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
                        isOptionalPort = not input_props.get('require_connection',True)
                        if hasRuntimePorts:
                            if not obj.getConnectionType("in",input_name) and not isOptionalPort:
                                self.exception(CGInputPortTypeRequiredException,source=obj,portname=input_name)
                            
                        inlineValue = obj_data['custom'].get(input_name,'NULL')
                        
                        if re.findall(f'@in\.{index+1}(?=\D|$)',node_code) and inlineValue == "NULL" and not isOptionalPort:
                            self.exception(CGPortRequiredConnectionException,source=obj,portname=input_name)

                        libOption = class_data['options'].get(input_name)
                        if libOption and libOption['type'] == "list":
                            if not self.getFactory().isEnumType(obj.getConnectionType("in",input_name)):
                                # валидация стандартных листов (не нумераторы)
                                for optList in libOption['values']:
                                    if isinstance(optList,list):
                                        if optList[0] == inlineValue:
                                            inlineValue = optList[1]
                                    else:
                                        if optList == inlineValue:
                                            self.exception(CGLogicalOptionListEvalException,source=obj,portname=libOption.get('text',input_name),context=optList)
                                            break
                        #disable emplace nil's on 'emplace_value'
                        if input_props.get('emplace_value',False):
                            isOptionalPort = False 

                        if isOptionalPort and input_props.get("default_value",inlineValue) == inlineValue:
                            inlineValue = 'NIL'
                        else:
                            inlineValue = self.updateValueDataForType(inlineValue,input_props['type'],obj)
                        
                        # validate canuse member
                        if inlineValue == 'this' and libOption['type'] == "objcaller":
                            catchErrThis = True
                            memname = "*class_info_not_found"
                            if "classInfo" in class_data:
                                clsInfo = class_data['classInfo']
                                memtype = clsInfo['type']
                                memname = clsInfo['name']
                                memparclass = clsInfo['class']
                                selfGraphClass = self.gObjMeta['classname']
                                if memtype == 'field':
                                    if memname in self.getFactory().getClassAllFields(selfGraphClass) and \
                                        memparclass in self.getFactory().getClassAllParents(selfGraphClass):
                                        catchErrThis = False
                                if memtype == 'method':
                                    if memname in self.getFactory().getClassAllMethods(selfGraphClass) and \
                                        memparclass in self.getFactory().getClassAllParents(selfGraphClass):
                                        catchErrThis = False
                            if catchErrThis:
                                self.exception(CGMemberNotExistsException,source=obj,context=[memname,selfGraphClass,clsInfo['class']],portname=input_name)
                            if isLambdaEntry and not isContextLambdaEntry:
                                self.exception(CGEntrySelfObjectPortUnsupported,source=obj,portname=input_name,entry=entryObj)
                        _str_inlineValue = f"{inlineValue}"
                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)', lambda _:_str_inlineValue, node_code)
                        continue

                    # нечего заменять
                    if not re.findall(f'@in\.{index+1}(?=\D|$)',node_code):
                        continue

                    inpId, portNameConn = inpId #unpack list

                    inpObj = codeInfo[inpId]


                    # проверка типов self
                    if input_props['type'] == "self":
                        typeFrom = self.dpdGraphExt[inpId]['typeout'][portNameConn]
                        typeRealFrom = self.getFactory().getRealType(typeFrom)
                        if "classInfo" in class_data:
                            srcNodeType = class_data["classInfo"]['class']
                            allowedTypes = self.getFactory().getClassAllParents(typeRealFrom)
                            #входной объект должен быть унаследован от источника
                            # key -> item
                            # key -> gameobject
                            # Если входной тип выше типа источника проверяем есть ли член
                            #if srcNodeType not in allowedTypes:
                            #todo: проверка типов исправить. вниз проверка стандартна а вверх иная
                            if not self.getFactory().isTypeOf(srcNodeType,typeRealFrom) and \
                                srcNodeType not in allowedTypes: #проверка вниз
                                self.exception(CGPortTypeClassMissmatchException,
                                    source=obj,
                                    portname=input_name,
                                    target=inpObj,
                                    context=srcNodeType
                                )
                        else:
                            checkedClass = self.gObjMeta['classname']
                            if typeFrom != checkedClass:
                                self.exception(CGPortTypeMissmatchException,
                                            source=obj,
                                            portname=input_name,
                                            target=inpObj,
                                            context=checkedClass)

                    if inpObj.generatedVars.get(portNameConn):

                        lvarObj = inpObj.generatedVars.get(portNameConn)
                        if not lvarObj.isUsed:
                            self.contextVariablesUsed.add(lvarObj.localName)
                        lvarObj.isUsed = True
                        _lvrObjLocNm = lvarObj.localName
                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)', lambda _:_lvrObjLocNm, node_code)

                    if inpObj.isReady:
                        #if re.findall(f'@in\.{index+1}(?=\D|$)',node_code):
                        codeIn = None
                        realIndex = -1
                        for index_real__, pname in enumerate(self.dpdGraphExt[obj.nodeId]['in'].keys()):
                            if pname == input_name:
                                realIndex = index_real__
                        if inpObj._isPure:
                            codeIn = f'\nBP_PS({inpObj._uid},{realIndex}) {inpObj.code} BP_PE'
                        else:
                            if NodeLambdaType.isLambdaEntryNode(inpObj.nodeClass): #function is not exec
                                codeIn = inpObj.code
                            else:
                                codeIn = f'BP_EXEC({inpObj._uid},{realIndex})\n /*bp-inp-exec*/ {inpObj.code}'
                        node_code = re.sub(f'@in\.{index+1}(?=\D|$)',lambda _:codeIn,node_code) 

                # Переберите все выходы и замените их значения в коде
                for index, (output_name, output_props) in enumerate(outputs_fromLib):
                    outId = execDict.get(output_name)

                    # Выход не подключен
                    if not outId: 
                        if hasRuntimePorts:
                            if not obj.getConnectionType("out",output_name) and obj.nodeClass != "control.supercall":
                                self.exception(CGOutputPortTypeRequiredException,source=obj,portname=output_name)
                        
                        node_code = re.sub(f'@out\.{index+1}(?=\D|$)',"",node_code) 
                        continue

                    outId, portNameConn = outId #unpack list

                    outputObj = codeInfo[outId]

                    # нечего заменять
                    if not re.findall(f'@out\.{index+1}(?=\D|$)',node_code):
                        continue

                    if outputObj.isReady:
                        self.gObjType.handleReturnNode(codeInfo[entryId],obj,outputObj,self.gObjMeta)
                        codeOut = None
                        if outputObj._isPure:
                            codeOut = f"\nBP_PS({outputObj._uid}) {outputObj.code} BP_PE"  
                        else:
                            codeOut = f"BP_EXEC({obj._uid},{index})\n {outputObj.code}"
                        node_code = re.sub(f"\@out\.{index+1}(?=\D|$)", lambda _:codeOut, node_code) 

                # prepare if all replaced
                if "@in." not in node_code and "@out." not in node_code:
                    obj.isReady = True

                #update code
                if not hasAnyChanges:
                    hasAnyChanges = obj.code != node_code
                obj.code = node_code

                if obj.isReady:
                    if '@nodeStackId' in obj.code:
                        obj.code = obj.code.replace('@nodeStackId',str(index_stack))
                    self.gObjType.handleReadyNode(obj,codeInfo[entryId],self.gObjMeta)

            # --- post check stack
            readyCount = 0
            for i in codeInfo.values():
                if i.isReady:
                    readyCount += 1
        
        contextGetStr = self.gObjType.handlePostReadyEntry(codeInfo[entryId],self.gObjMeta,codeInfo)

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

        if not stackGenError:
            if not self.postCheckCode(codeInfo,entryId,contextGetStr):
                hasNodeError = True

        if hasNodeError:
            errLen = len(self._exceptions) - curExceptions
            warnLen = len(self._warnings) - curWarnings
            self.error(f'Точка входа {LoggerConsole.wrapNodeLink(self._sanitizeNodeName(entryObj.nodeId),entryObj.nodeId)} не обработана: <b><span style="color:red">{errLen} ошибок,</span> <span style="color:yellow">{warnLen} предупреждений</span></b><br/>')


        entryObj = codeInfo[entryId]
        if not entryObj.isReady:
            return "NOT_READY:" + entryObj.code
        
        return entryObj.code

    def postCheckCode(self,codeInfo,entryId,contextGetStr):
        """Постпроверка кода"""
        dpdGraphExt = self.dpdGraphExt
        entryObj = codeInfo[entryId]
        retType = entryObj.classLibData['returnType']
        if NodeLambdaType.isLambdaEntryNode(entryObj.nodeClass):
            fsign = entryObj.getConnectionType('out','lambda_ref')
            if not self.getFactory().isFuncSignType(fsign):
                self.exception(CGEntryFunctionSignatureException,source=entryObj,context=f"Тип \"{fsign}\" не является типом сигнатуры функции")
            retType = self.getFactory().getFuncSignReturnType(fsign)
        needReturn = retType != "null"
        retTypenameExpect = self.getVariableManager().getTextTypename(retType)

        def enterScope(nodeId,scopeStack:list):

            idat = self.dpdGraphExt[nodeId]
            srcObj: CodeGenerator.NodeData = codeInfo[nodeId]
            execsPorts = [e for e,tp in idat['typeout'].items() if tp == "Exec"]
            isMultiExec = len(execsPorts) > 1
            hasOutConnected = len(idat['out']) > 0 #есть выходные порты
            connectedOutExecPorts = [k for k in execsPorts if len(idat['out'][k]) > 0]
            
            noLoops = True
            loopObj = None
            for scpCheck in scopeStack:
                if scpCheck.isLoopScope:
                    noLoops = False
                    loopObj = scpCheck.sourceObj
                    break

            # проверка требования возвращаемого типа
            if len(connectedOutExecPorts) == 0 or not hasOutConnected:
                
                if needReturn:
                    if noLoops:
                        if 'control.return' != srcObj.nodeClass:
                            self.exception(CGReturnNotAllBranchesException,source=srcObj,entry=entryObj,context=retTypenameExpect)
                        else:
                            #type checking
                            realType = srcObj.getConnectionType('in',"Возвращаемое значение")
                            if realType != retType:
                                ctxType = f'{retTypenameExpect} ({retType})'
                                rtName = self.getVariableManager().getTextTypename(realType)
                                self.exception(CGReturnTypeMismatchException,source=srcObj,entry=entryObj,context=ctxType,portname=rtName)
                else:
                    if 'control.return' == srcObj.nodeClass:
                        self.exception(CGReturnTypeUnexpectedException,source=srcObj,entry=entryObj)
            
            # проверка возвращаемого значения для мультивыходных портов выполнения (castto,branch)
            elif needReturn and noLoops and hasOutConnected and len(connectedOutExecPorts) != len(execsPorts):
                self.exception(CGReturnNotAllBranchesException,source=srcObj,entry=entryObj,context=retTypenameExpect)

            # проверка операторов контроля цикла
            if srcObj.nodeClass in ["operators.break_loop","operators.continue_loop"] and noLoops:
                self.exception(CGLoopControlException,source=srcObj)
            # проверка таймеров внутри циклов и возвращаемого значения
            if srcObj.nodeClass in ["control.callafter","control.callaftercond"]:
                if not noLoops:
                    self.exception(CGLoopTimerException,source=srcObj,target=loopObj)
                if needReturn:
                    self.exception(CGTimerUnallowedReturnException,source=srcObj,entry=entryObj)



            srcObj.scopes = scopeStack.copy()
            className = srcObj.nodeClass

            for k,v in idat['typeout'].items():
                if v == "Exec":
                    scopePopNeed = False
                    hasConnection = len(idat['out'][k]) > 0

                    if "if_branch" in className or isMultiExec:
                        newLvl = scopeStack[-1].scopeLevel + 1
                        scp = CodeGenerator.ExecScope(srcObj,k,newLvl)

                        if className in NodeDataType.getScopedLoopNodes():
                            if k == "Тело цикла":
                                scp.isLoopScope = True
                            else:
                                # проверка не подключенных выходов циклов
                                if not hasConnection and needReturn:
                                    self.exception(CGReturnNotAllBranchesException,source=srcObj,entry=entryObj,context=retTypenameExpect)

                        scopeStack.append(scp)
                        scopePopNeed = True
                    if hasConnection:
                        src = list(idat['out'][k][0])[0]
                        enterScope(src,scopeStack)
                    
                    if scopePopNeed:
                        scopeStack.pop()
        
        scopes = [CodeGenerator.ExecScope(entryObj,"entry")]
        
        if not dpdGraphExt.get(entryId):
            if needReturn:
                self.exception(CGReturnTypeNotFoundException,source=entryObj,entry=entryObj,context=retTypenameExpect)
            return True

        enterScope(entryId,scopes)

        #parse syntax
        from sqf.analyzer import analyze
        from sqf.parser import parse
        from sqf.base_type import BaseTypeContainer
        from sqf.base_type import get_coord
        enCode = entryObj.code
        # enCode = "#define class(v) NOP\n"\
        #     +"#define extends(v) NOP\n"\
        #     +"#define editor_attribute(v) NOP\n"\
        #     +"#define endclass NOP\n"\
        #     +"#define NOP ;\n"\
        #     +"#define this locationNull\n"\
        #     +"#define func(v) v = \n"\
        #     +enCode

        #replace for debugger
        enCode = enCode.replace("@IFDEF_DEBUG","").replace("@ENDIF","")
        enCode = re.sub("(BP_EXEC\([\d,-]+\)|BP_PS\([\d,-]+\)|BP_PE)","",enCode)

        pr = parse(enCode)
        resultAnalyze = analyze(pr)

        #collect allvars
        allVars = []
        for v in codeInfo.values():
            if v.generatedVars:
                allVars.extend([varObj for varObj in v.generatedVars.values()])

        # реализация проверки переменных
        hasFoundLvarExeptions = False
        mapIdToCode = {k:c.code for k,c in codeInfo.items()}
        clines : list[str] = enCode.splitlines()
        for ex in resultAnalyze.exceptions:
            
            lvarNameAsList = re.findall("Local variable \"(_lvar_\d+_\d+|_LVAR\d+|_foreachindex|_x|_y|__it_\w+\d+_\d+)\" is not from this scope \(not private\)",ex.args[1],re.IGNORECASE)
            if lvarNameAsList:
                #TODO warning for: warning:Variable "_lvar_21_0" not used
                lvarName = lvarNameAsList[0]
                line_num, col_count = ex.position

                #! OLD ALG
                # search next to lvar /*NODE:NAME*/ and get name (example: "_lvar_3_65/*NODE:Test node name*/" -> returns "Test node name") 
                # line_num -= 1 # from index to line
                # startIndex = len(lvarName) + len("/*NODE:")
                # nodeIdName = clines[line_num][col_count+startIndex-1:]
                # endIndex = nodeIdName.find("*/")
                # nodeIdName = nodeIdName[:endIndex]
                # self.exception(CGScopeVariableNotFoundException,source=codeInfo[nodeIdName])

                #new alg (optimized)
                line_num -= 1
                for lvarObj in allVars:
                    if lvarObj.localName == lvarName:
                        defId = lvarObj.definedNodeId      
                        defPort = lvarObj.fromPort
                        probTargError = None
                        minLen = len(enCode)
                        for idErr,codeCheck in mapIdToCode.items():
                            lenCode = len(codeCheck)
                            mathedIdx = clines[line_num].find(codeCheck,max(col_count-lenCode,0))
                            if mathedIdx == -1: continue
                            founder = clines[line_num][mathedIdx:]
                            newLen = len(founder)
                            if newLen < minLen and lvarName in founder:
                                minLen = newLen
                                probTargError = idErr
                        if probTargError == entryId or probTargError == None:
                            probTargError = None
                        else:
                            probTargError = codeInfo[probTargError]
                        
                        self.exception(CGScopeLocalVariableException,source=codeInfo[defId],portname=defPort,target=probTargError)
                        break
        if hasFoundLvarExeptions: return False

        # postprocess replace debug preprocessor
        entryObj.code = entryObj.code \
            .replace("@IFDEF_DEBUG","\n#ifdef DEBUG\n") \
            .replace("@ENDIF","\n#endif\n") \
            .replace("@context.get",contextGetStr)

        return True

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

    def getVariableData(self,className,nameid,optObj:NodeData=None) -> tuple[str,str,bool]:
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

    def getFunctionData(self,className,nameid,optObj:NodeData=None) -> str:
        """Получает информацию о пользовательской функции
            :param className: имя функции
            :param nameid: имя функции
            :return: код, список входных параметров, список выходных параметров
        """
        data = self.getVariableManager().getVariableDataById(nameid,refVarDict=self.graph.variables)
        isDef = className.endswith(".def")
        if isDef:
            code = "func(@thisName) {@thisParams; @out.1};"
            raise Exception(f"Code not ready for node " + className+"; Custom functions not supported")
            return code
        else:
            code = "[{}] call (this getVariable PROTOTYPE_VAR_NAME getVariable \"@thisName\")"
            params = ['this']
            for i, (k,v) in enumerate(optObj.classLibData['inputs'].items()):
                if v['type']=="Exec": continue
                params.append(f"@in.{i+1}")
            code = code.format(', '.join(params))

            isPure = data.get("isPure")

            if isPure:
                code = f"({code})"
            else:
                code = code + "; @out.1"

            #copypaste from libgenerator.py -> generateMethodCodeCall
            returnId = -1
            if optObj.classLibData.get('returnType') not in ['void','null',''] and not isPure:
                for i, (k,v) in enumerate(optObj.classLibData['outputs'].items()):
                    if v['type'] != "Exec" and v['type'] == optObj.classLibData.get('returnType'):
                        returnId = i+1
                        break
            if returnId >= 0:
                code = f'private @genvar.out.{returnId} = {code}'

            code = self.prepareMemberCode(optObj.classLibData,code)
            return code

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
            node = self.graph.get_node_by_id(node_id)
            if hasattr(node, 'resetError'):
                node.resetError()

    def findNodesByClass(self, class_to_find):
        node_ids = []
        for node_id, node_data in self.serialized_graph["nodes"].items():
            if node_data["class_"] == class_to_find:
                node_ids.append(node_id)
        return node_ids

    def getAllEntryPoints(self):
        node_ids = []
        cleanupList = []
        for node_id, node_data in self.serialized_graph["nodes"].items():
            nodeClass = node_data['class_']
            libData = self.getNodeLibData(nodeClass)
            if not libData:
                self.nodeWarn(CGNodeNullWarning,source=node_id)
                cleanupList.append(node_id)
                continue
            isClassMember = "classInfo" in libData
            if isClassMember:
                isMethod = libData["classInfo"]["type"] == "method"
                if isMethod:
                    # сбор методов: только те у которых memtype -> def, event
                    memType = libData.get("memtype")
                    if not memType:
                        raise Exception(f"Corrupted memtype for method '{nodeClass}'; Info: {libData}")
                    if memType in ["def","event"]:
                        node_ids.append(node_id)
            if nodeClass == "function.def":
                node_ids.append(node_id)
            if NodeLambdaType.isLambdaEntryNode(nodeClass): #and not NodeLambdaType.hasContextInLambdaType(nodeClass):
                node_ids.append(node_id)
        
        for nclenup in cleanupList:
            self.serialized_graph["nodes"].pop(nclenup)
        for conn in self.serialized_graph['connections']:
            if conn['in'][0] in cleanupList or conn['out'][0] in cleanupList:
                self.serialized_graph['connections'].remove(conn)
        
        if cleanupList:
            self.exception(CGUnexistNodeError)
        
        return node_ids

    def vtWarn(self,optObj=None,mes=''):
        if isinstance(optObj,str):
            mes = f'Внутреннее предупреждение {optObj}; {mes}'
            optObj = None 
        if optObj:
            self.nodeWarn(CGValueCompileWarning,source=optObj,context=mes)
        else:
            self.warning(mes)
            self._warnings.append(None)
        if self.isGenerating:
            self.exception(CGInternalValueCompileError)
            raise CGCompileAbortException()


    def updateValueDataForType(self,value,tname,optObj=None):
        if value is None: return "null"
        if value == "NULL": return value
        if value == "this": return value
        #for selfcall/selfset/get
        #! removed: value == 'Этот объект' and
        if  tname == "self": return "this"
        if not tname: return value

        vObj,dtObj = self.getVariableManager().getVarDataByType(tname,True)
        dtName = dtObj.dataType

        if dtName != "value":
            if dtName == "array":
                evaluated = ["[ "]
                for v in value:
                    if len(evaluated) > 1: evaluated.append(", ")
                    evaluated.append(self.updateValueDataForType(v,vObj.variableType,optObj))
                evaluated.append(" ]")
                return "".join(evaluated)
            elif dtName == "dict":
                evaluated = ["(createHASHMAPfromArray[ "]
                objStack = []
                if not isinstance(vObj,list): raise Exception(f"Wrong dict type: {vObj}")

                #TODO реализовать хэширование (и возможно дехеширование) ключей
                if vObj[0].variableType != "string":
                    self.vtWarn(optObj,"Недопустимый тип ключей словаря {} (ожидатеся тип - строка)".format(vObj[1]))

                for key,val in value.items():
                    if objStack: objStack.append(", ")

                    objStack.append("[")
                    objStack.append(self.updateValueDataForType(key,vObj[0].variableType,optObj))
                    objStack.append(", ")
                    objStack.append(self.updateValueDataForType(val,vObj[1].variableType,optObj))
                    objStack.append("]")
                
                evaluated.extend(objStack)
                evaluated.append(" ])")
                return "".join(evaluated)
            elif dtName == "set":
                evaluated = ["([ "]
                for v in value:
                    if len(evaluated) > 1: evaluated.append(", ")
                    evaluated.append(self.updateValueDataForType(v,vObj.variableType,optObj))
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
                    strData = "("+strData.replace("\n","\"+endl+\"")+")"
                    #removing empty strings
                    #todo implement for performance
                    return strData
            else: 
                return strData
        elif tname == "bool":
            return str(value).lower()
        elif tname in ['float','int']:
            gval = str(value)
            
            pts = gval.split(".")
            if len(pts[0]) > 6:
                self.vtWarn(optObj,f"Превышено количество знаков для {tname} ({gval}). Возможна потеря точности")
            if len(pts) > 1 and len(pts[1]) > 6:
                self.vtWarn(optObj,f"Превышено количество знаков после запятой для {tname} ({gval}). Возможна потеря точности")
                    
            return gval
        elif self.getVariableManager().isObjectType(tname):
            return value
        elif self.getVariableManager().isEnumType(tname):
            efDat = self.getFactory().getEnumData(tname)
            enumVals = efDat['enumList']
            factValue = None
            factKey = '$unk_key$'
            for enumItem in enumVals:
                if enumItem['name'] == value:
                    factValue = str(enumItem['val'])
                    factKey = enumItem['name']
                    break
                if enumItem['val'] == value:
                    factValue = str(enumItem['val'])
                    factKey = enumItem['name']
                    break
            if factValue == None:
                self.vtWarn(optObj,f'Неизвестное значение перечисления {efDat["name"]}: {value}')
            if efDat['enumtype']!="int":
                factValue = self.updateValueDataForType(factValue,efDat['enumtype'],optObj)
            return f'{factValue}/*{tname}:{factKey}*/'
        elif self.getVariableManager().isStructType(tname):
            from ast import literal_eval
            retVals = []
            for indexVal, sDict in enumerate(self.getFactory().getStructFields(tname)):
                sDictType_ = sDict['type']
                decType_ = self.getFactory().decomposeType(sDictType_)
                valParse = value[indexVal]
                if decType_[0] != "value":
                    valParse = literal_eval(valParse)
                retVals.append(self.updateValueDataForType(valParse,sDictType_,optObj))
            return f'[{", ".join(retVals)}]'
        elif tname in ['class','classname']: #объект тип и имя класса (строка)
            if not self.getFactory().classNameExists(value):
                pref = "Тип объекта" if 'class'==tname else "Имя класса"
                self.vtWarn(optObj,f'{pref} не существует: {value}')
            else:
                if tname == 'class': return f'pt_{value}'
                elif tname == 'classname': return f'"{value}"'
        elif re.match('vector\d+',tname):
            return self.updateValueDataForType(value,"array[float]",optObj)
        elif tname == "color":
            return self.updateValueDataForType(value,"array[float]",optObj)
        elif tname in ['handle','model']:
            gval = str(value)
            if tname == 'handle':
                if value < -1:
                    self.vtWarn(optObj,f'Недопустимый тип неопределенного {tname}: {value}')
                if value >= 3.4028235e38:
                    self.vtWarn(optObj,f'Слишком большое значение для {tname}: {value}')
                if '.' in gval:
                    self.vtWarn(optObj,f'Неверное значение для {tname}: {value}')
            return gval
        elif tname == 'function_ref' or self.getFactory().isFuncSignType(tname): #anonfunc or funcsign
            return f'{value}'
        else:
            if not self.isDebugMode(): 
                raise Exception(f"Unknown type {tname} (value: {value} ({type(value)}))")
            else:
                self.vtWarn(optObj,"Cant repr type value: {} = {} ({})".format(tname,value,type(value)))

        return value
    
    def isDebugMode(self):
        from ReNode.app.application import Application
        return Application.isDebugMode()

    def log(self,text,forceAdd=False):
        if self._silentMode and not forceAdd: return
        self.logger.info(text)

    def error(self,text,forceAdd=False):
        #!errors always printing
        #if self._silentMode and not forceAdd: return
        self.logger.error(text)

    def warning(self,text,forceAdd=False):
        if self._silentMode and not forceAdd: return
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
    
        if self._silentMode:
            if not self.hasCompileParam("-exceptinfo"):
                self._exceptions.append(exType())
            else:
                if source: 
                    sourceId = source.nodeId
                    linkSourceId = LoggerConsole.createNodeGraphReference(self.graph.graph_path,self._getNodeIncrementId(sourceId),sourceId)
                if target: 
                    targetId = target.nodeId
                    linkTargetId = LoggerConsole.createNodeGraphReference(self.graph.graph_path,self._getNodeIncrementId(targetId),targetId)
                if entry: 
                    entryId = entry.nodeId
                    linkEntryId = LoggerConsole.createNodeGraphReference(self.graph.graph_path,self._getNodeIncrementId(entryId),entryId)

                params = {
                    "src": linkSourceId,
                    "portname": portname,
                    "targ": linkTargetId,
                    "ctx": context,
                    "entry": linkEntryId
                }
                ex : CGBaseException = exType(**params)

                exText = ex.getExceptionText(addDesc=False,exRef=False) + f' ({LoggerConsole.createNodeGraphReference(self.graph.graph_path,text="открыть граф")})'
                if exText in [regEx.getExceptionText(addDesc=False,exRef=False) for regEx in self._exceptions]:
                    self.warning(f"<span style='font-size:8px;'>Подавление дубликата исключения ({ex.__class__.__name__})</span>")
                    return
                self.error(exText)

                self._exceptions.append(ex)
            
            return

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
        
        #exText += exRef
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
                    exType,source:NodeData |str| None=None,
                    portname:str|None=None,
                    target:NodeData |str| None=None, 
                    entry:NodeData |str| None=None,
                    context=None):
        """
        Предупреждающее сообщение для узлов
        """
        if self._silentMode:
            self._warnings.append(exType())
            return
        sourceId = None
        targetId = None
        entryId = None

        linkSourceId = None
        linkTargetId = None
        linkEntryId = None

        if source: 
            if isinstance(source,CodeGenerator.NodeData):
                sourceId = source.nodeId
            else:
                sourceId = source
            linkSourceId = LoggerConsole.wrapNodeLink(self._sanitizeNodeName(sourceId),sourceId)
        if target: 
            if isinstance(target,CodeGenerator.NodeData):
                targetId = target.nodeId
            else:
                targetId = target
            linkTargetId = LoggerConsole.wrapNodeLink(self._sanitizeNodeName(targetId),targetId)
        if entry: 
            if isinstance(entry,CodeGenerator.NodeData):
                entryId = entry.nodeId
            else:
                entryId = entry
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
        if self._silentMode:
            return node_id #because all nodes in silent mode is dictreferences
        if node_id in self._originalReferenceNames:
            node_id = self._originalReferenceNames[node_id]
        return node_id
    
    def _getNodeIncrementId(self,node_id):
        nodeobj = self.graph.get_node_by_id(node_id)
        if self._silentMode:
            return nodeobj['increment_uid'] if nodeobj else -2
        else:
            return nodeobj.uid if nodeobj else -2
    
    def getNodeConnectionType(self,node_id,inout,portname):
        origNodeId = node_id
        node_id = self._sanitizeNodeName(node_id)
        obj = self.graph.get_node_by_id(node_id)
        if inout == "in":
            if self._silentMode:
                return self.getPortInputType(origNodeId,portname)
            else:
                return obj.inputs()[portname].view.port_typeName
        elif inout == "out":
            if self._silentMode:
                return self.getPortOutputType(origNodeId,portname)
            else:
                return obj.outputs()[portname].view.port_typeName
        else:
            raise Exception(f"Unknown connection type: {inout}")

    def _debug_setName(self,node_id,name):
        node_id = self._sanitizeNodeName(node_id)
        
        orig = self.graph.get_node_by_id(node_id)
        
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
            fullName = className + "." + memName
            #returnType = dictLib.get('returnType','null')

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
                        if outValues.get('gen_param',True):
                            isOptParam = not outValues.get("require_connection",True)
                            newParam = '\"@genvar.out.{}\"'.format(indexVar+1)
                            if isOptParam:
                                if 'default_value' not in outValues:
                                    raise Exception(f"Missing default_value property for port {outKey} in member {fullName}")
                                optVal = self.updateValueDataForType(outValues['default_value'],outValues['type'],"prep_param:"+fullName+"."+outKey)
                                newParam = f'[{newParam},{optVal}]'
                            paramList.append(newParam)
                
                paramCtx = f'params [{", ".join(paramList)}]'
                #adding initvars keyword
                paramCtx += "; @initvars"
                code = code.replace(metaKeyword,paramCtx)
        
        return code

    def makeScopeChecker(self, entryId, codeInfo):
        dpdGraphExt = self.dpdGraphExt
        entryObj = codeInfo[entryId]

        def enterScope(nodeId,scopeStack:list):

            idat = self.dpdGraphExt[nodeId]
            srcObj: CodeGenerator.NodeData = codeInfo[nodeId]
            execsPorts = [e for e,tp in idat['typeout'].items() if tp == "Exec"]
            isMultiExec = len(execsPorts) > 1
            hasOutConnected = len(idat['out']) > 0 #есть выходные порты
            connectedOutExecPorts = [k for k in execsPorts if len(idat['out'][k]) > 0]

            srcObj.scopes = scopeStack.copy()
            className = srcObj.nodeClass

            for k,v in idat['typeout'].items():
                if v == "Exec":
                    scopePopNeed = False
                    hasConnection = len(idat['out'][k]) > 0

                    if isMultiExec:
                        newLvl = scopeStack[-1].scopeLevel + 1
                        scp = CodeGenerator.ExecScope(srcObj,k,newLvl)

                        if className in NodeDataType.getScopedLoopNodes():
                            if k == "Тело цикла":
                                scp.isLoopScope = True

                        scopeStack.append(scp)
                        scopePopNeed = True
                    if hasConnection:
                        src = list(idat['out'][k][0])[0]
                        enterScope(src,scopeStack)
                    
                    if scopePopNeed:
                        scopeStack.pop()
        
        scopes = [CodeGenerator.ExecScope(entryObj,"entry")]
        
        if not dpdGraphExt.get(entryId):
            return None

        enterScope(entryId,scopes)

        return scopes