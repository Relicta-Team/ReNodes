
from ReNode.app.Constants import *
from ReNode.app.Logger import RegisterLogger
from ReNode.app.Types import validate_connections_serialized,make_portvalidation_request
from copy import deepcopy

class NodeSyncronizer:
    """
    Класс валидации и синхронизации узлов
    """
    def __init__(self,graphRef):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        self.graphRef : NodeGraphComponent = graphRef
        self.logger = RegisterLogger("NodeSync")

        self.refValidatedGraph = None
        self.cleanupConnList = set()
    
    def getFactory(self): return self.graphRef.getFactory()
    def getVarMgr(self): return self.graphRef.variable_manager

    def wrapNodeLink(self,node_id,optText=None,clr="#17E62C"): return self.graphRef.log_dock.__class__.wrapNodeLink(node_id,optText)
    def createNodeLink(self,graphRef,node_id,otext=None,clr="#17E62C"): return self.graphRef.log_dock.__class__.createNodeLink(graphRef,node_id,otext,clr)

    def log(self,msg): self.logger.info(msg)
    def warn(self,msg): self.logger.warn(msg)

    def validateGraph(self,graphRef,graphDict):
        
        # это скопированные данные и они не должны быть проверены
        if 'graph' not in graphDict: return

        self.refValidatedGraph = graphRef
        self.refDict = graphDict

        self.nodeLinkDict = {}
        self.cleanupConnList = set()

        for cat,vardata in graphDict['graph'].get('variables',{}).items():
            for varid,varprops in vardata.items():
                self.validateVariable(cat,varid,varprops)

        nodes = graphDict['nodes']
        startIndex = graphRef.incrementId + 1
        for k,v in nodes.items():
            uniName = f'{v["name"]} ({startIndex})' #, {v["class_"]}
            link = self.createNodeLink(graphRef,startIndex,uniName)
            self.nodeLinkDict[k] = link
            #self.log(f'Loaded {link}')
            self.validateNode(k,v,link)
            startIndex += 1
        
        if graphDict['graph']['info'].get('graphVersion',-1) != self.getFactory().graphVersion:
            for conn in graphDict.get('connections',{}).copy():
                self.validateConnection(conn)

        if self.cleanupConnList:
            for conn in graphDict.get('connections',{}).copy():
                fromNode,fromPort = conn['in']
                toNode,toPort = conn['out']
                if fromNode in self.cleanupConnList or toNode in self.cleanupConnList:
                    graphDict['connections'].remove(conn)


        #self.log(f"Validated {len(nodes)} nodes!")

        self.refValidatedGraph = None
        self.refDict = None
    
    def validateConnection(self,conn):
        fromNode,fromPort = conn['in']
        toNode,toPort = conn['out']
        fnObj = self.refDict['nodes'][fromNode]
        tnObj = self.refDict['nodes'][toNode]
        fcls = fnObj['class_']
        tcls = tnObj['class_']

        fdat = self.getFactory().getNodeLibData(fcls)
        tdat = self.getFactory().getNodeLibData(tcls)

        if tcls=='objects.thisObject' and toPort != "thisName":
            #toPort = "thisName"
            return #skip "this" node

        if fnObj['port_deletion_allowed']:
            fp = next((p for p in fnObj['input_ports'] if p['name'] == fromPort),None)
        else:
            fp = fdat['inputs'][fromPort]
        if tnObj['port_deletion_allowed']:
            tp = next((p for p in tnObj['output_ports'] if p['name'] == toPort),None)
        else:
            tp = tdat['outputs'][toPort]
        
        if fp == None or tp == None:
            if not fp: 
                self.warn(f'Устарешвий узел {self.nodeLinkDict[fromNode]}')
                self.removeAllConnectedPorts(fromNode)
            if not tp: 
                self.warn(f'Устарешвий узел {self.nodeLinkDict[toNode]}')
                self.removeAllConnectedPorts(toNode)
            
            return

        if tp.get('type')=="auto_object_type":
            return #skip castto

        tpType_ = tp['type']
        
        tscheck = [(k,f['typeset_out']) for k,f in tdat['options'].items() if 'typeset_out' in f]
        if tscheck:
            prtN,tpPortName_ = tscheck[0]
            if tpPortName_ == toPort:
                tpType_ = tnObj['custom'][prtN] + "^"

        fObj = make_portvalidation_request({'name':fromPort,'type':fp['type']},fdat,'in')
        tObj = make_portvalidation_request({'name':toPort,'type':tpType_},tdat,'out')
        if not validate_connections_serialized(fObj,tObj):
            sv = self.nodeLinkDict[fromNode]
            tv = self.nodeLinkDict[toNode]
            self.warn(f'Несоответствие подключений между {sv} ({fp["type"]}) и {tv} ({tpType_}). Подключения между ними очищены')
            
            self.removeAllConnectedPorts(fromNode)
            self.removeAllConnectedPorts(toNode)
    def unpackData(self,dictValues):
        className = dictValues['class_']
        classInfo = self.getFactory().getNodeLibData(className)
        objOptions = dictValues.get('custom')

        return className, classInfo, objOptions

    def validateVariable(self,category,varId,dictValues):
        if "systemname" in dictValues:
            sysname = dictValues["systemname"]
            if sysname.startswith("0x"):
                from ReNode.ui.VarMgrWidgetTypes.Widgets import prepVariableName
                newsysname = prepVariableName(dictValues['name'])
                dictValues["systemname"] = newsysname
                self.log(f"Renamed variable sysname {varId}: {sysname} -> {newsysname}")

    def validateNode(self,nodeId,dictValues,link):
        # defines
        className = dictValues['class_']
        classInfo = self.getFactory().getNodeLibData(className)
        objOptions = dictValues.get('custom')
        if not classInfo:
            self.warn("Skipping unknown class: " + className)

        if dictValues.get("port_deletion_allowed"):
            if className.startswith("math."):
                if classInfo['name'] != dictValues['name']:
                    self.log(f'Obsoleted name for runtime node: {link}')
                    dictValues['input_ports'] = []
                    dictValues['output_ports'] = []
                    dictValues['custom'] = {}
                    dictValues['name'] = f'<span style="color:red">ОБНОВИТЕ:</span> {dictValues["name"]}'

        #rulesets
        # Проверка портов
        #   Даже если это автопорт то у нас должны соответствовать типы портов (рендер, цвет, тип и тд)

        #временная проверка variable get и set
        self.validateVarGetSetRtPorts(nodeId,dictValues,link)

        self.validateColors(nodeId,dictValues,link)
        
        # Проверка узла
        # Имя должно соответствовать названию из класса только если это не геттер/сеттер для переменной

    def validateColors(self,nodeId,dictValues,link):
        """Стандартный валидатор цвета"""
        className = dictValues['class_']
        classInfo = self.getFactory().getNodeLibData(className)
        if not classInfo: return
        color = classInfo['color']
        if color != dictValues['color']:
            if NodeColor.isConstantColor(className):
                self.warn(f"Node {link} obsolete color. Updating...")
                dictValues['color'] = color

            # varcheck 
            #!disabled spam message
            # if className.startswith('variable.'):
            #     self.warn(f"Variable node {link} obsolete color. Updating...")
            #     vmgr = self.getVarMgr()
            #     nameid = dictValues['custom']['nameid']
            #     typename = None
            #     for cat,list in self.refDict['graph'].get('variables',{}).items():
            #         if nameid in list:
            #             typename = list[nameid]['type']
            #     if typename:
            #         newcolor = vmgr.getColorByType(typename)
            #         dictValues['color'] = newcolor


    def validateVarGetSetRtPorts(self,nodeId,dictValues,link):
        className, classInfo, objOptions = self.unpackData(dictValues)
        if (className == 'variable.get' or className == 'variable.set') and not dictValues.get('port_deletion_allowed',False):
            from PyQt5.QtGui import QColor
            self.warn(f"Node variable {link} obsolete structure. Updating...")
            
            dictValues['port_deletion_allowed'] = True

            varMgr = self.graphRef.variable_manager
            varName = dictValues['custom']['nameid']
            lvdata = next((vars[varName] for cat,vars in self.refDict['graph']['variables'].items() if varName in vars),None)
            if not lvdata:
                raise Exception(f"cannot find local variable data: {varName}")
            if dictValues.get('icon'):
                clr = QColor(dictValues['icon'][1])
            else:
                clr = QColor(255,255,255,255)
            portcolor = [*clr.getRgb()]
            realType = lvdata['type']

            # if lvdata['name'] in dictValues['custom']:
            #     #self.log("warn obsolete option from custom: {} with value {}".format(lvdata['name'],dictValues['custom'][lvdata['name']]))
            #     #del dictValues['custom'][lvdata['name']]
            #     pass
            # else:
            #     self.log("warn option not found: {} in class {}".format(lvdata['name'],className))

                

            if ".set" in className:
                oldPorts = deepcopy(classInfo['inputs'])
                oldPortsArr = []
                #convert old inputs to runtime
                for k,v in oldPorts.items():
                    v['name'] = k
                    v['multi_connection'] = v['mutliconnect']
                    if v['type'] == 'Exec': 
                        v['style'] = 1
                    del v['mutliconnect']
                    oldPortsArr.append(v)
                vardict = {
                    "name": lvdata['name'],
                    "type": realType,
                    "color": portcolor,
                    "display_name": True,
                    "multi_connection": False,
                }
                oldPortsArr.append(vardict)

                dictValues['input_ports'] = oldPortsArr
            else:
                dictValues['input_ports'] = []
            
            oldPorts = deepcopy(classInfo['outputs'])
            oldPortsArr = []
            #convert old inputs to runtime
            for k,v in oldPorts.items():
                v['name'] = k
                v['multi_connection'] = v['mutliconnect']
                if v['type'] == 'Exec': 
                    v['style'] = 1
                del v['mutliconnect']
                oldPortsArr.append(v)
            
            vardict = {
                "name": lvdata['name'] if ".get" in className else "Значение",
                "type": realType,
                "color": portcolor,
                "display_name": True,
                "multi_connection": True,
            }
            oldPortsArr.append(vardict)
            
            dictValues['output_ports'] = oldPortsArr

        #input_ports, output_ports для port_deletion_allowed

    def _disconnectPort(self,nodeId,inout,portName):
        pass

    def removeAllConnectedPorts(self,nodeId):
        self.cleanupConnList.add(nodeId)