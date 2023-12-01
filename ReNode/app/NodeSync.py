

from ReNode.app.Logger import RegisterLogger
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
    
    def getFactory(self): return self.graphRef.getFactory()

    def wrapNodeLink(self,node_id,optText=None,clr="#17E62C"): return self.graphRef.log_dock.__class__.wrapNodeLink(node_id,optText)
    def createNodeLink(self,graphRef,node_id,otext=None,clr="#17E62C"): return self.graphRef.log_dock.__class__.createNodeLink(graphRef,node_id,otext,clr)

    def log(self,msg): self.logger.info(msg)
    def warn(self,msg): self.logger.warn(msg)

    def validateGraph(self,graphRef,graphDict):

        self.refValidatedGraph = graphRef
        self.refDict = graphDict

        nodes = graphDict['nodes']
        startIndex = graphRef.incrementId + 1
        for k,v in nodes.items():
            uniName = f'{v["name"]} ({startIndex})' #, {v["class_"]}
            link = self.createNodeLink(graphRef,startIndex,uniName)
            #self.log(f'Loaded {link}')
            self.validateNode(k,v,link)
            startIndex += 1
        
        self.log(f"Validated {len(nodes)} nodes!")

        self.refValidatedGraph = None
        self.refDict = None
    
    def unpackData(self,dictValues):
        className = dictValues['class_']
        classInfo = self.getFactory().getNodeLibData(className)
        objOptions = dictValues.get('custom')

        return className, classInfo, objOptions

    def validateNode(self,nodeId,dictValues,link):
        # defines
        className = dictValues['class_']
        classInfo = self.getFactory().getNodeLibData(className)
        objOptions = dictValues.get('custom')
        if not classInfo:
            self.warn("Skipping unknown class: " + className)
        #rulesets
        # Проверка портов
        #   Даже если это автопорт то у нас должны соответствовать типы портов (рендер, цвет, тип и тд)

        #временная проверка variable get и set
        self.validateVarGetSetRtPorts(nodeId,dictValues,link)
        
        # Проверка узла
        # Имя должно соответствовать названию из класса только если это не геттер/сеттер для переменной

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
            if ".set" in className:
                oldPorts = deepcopy(classInfo['inputs'])
                oldPortsArr = []
                #convert old inputs to runtime
                for k,v in oldPorts.items():
                    v['name'] = k
                    v['multi_connection'] = v['mutliconnect']
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
                del v['mutliconnect']
                oldPortsArr.append(v)
            raise Exception("TODO: exec style triangle required")
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