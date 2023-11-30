

from ReNode.app.Logger import RegisterLogger

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

        nodes = graphDict['nodes']
        startIndex = graphRef.incrementId + 1
        for k,v in nodes.items():
            uniName = f'{v["name"]} ({startIndex})' #, {v["class_"]}
            link = self.createNodeLink(graphRef,startIndex,uniName)
            self.log(f'Loaded {link}')
            startIndex += 1
        
        self.log(f"Validated {len(nodes)} nodes!")

        self.refValidatedGraph = None
    
    def validateNode(self,nodeId,dictValues,link):
        # defines
        className = dictValues['class_']
        classInfo = self.getFactory().getNodeLibData(className)
        #rulesets
        # Проверка портов
        #   Даже если это автопорт то у нас должны соответствовать типы портов (рендер, цвет, тип и тд)
        objOptions = dictValues.get('custom')
        if objOptions:
            pass


        #input_ports, output_ports для port_deletion_allowed
        
        # Проверка узла
        # Имя должно соответствовать названию из класса только если это не геттер/сеттер для переменной


    def _disconnectPort(self,nodeId,inout,portName):
        pass