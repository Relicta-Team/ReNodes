import typing
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from Qt import QtWidgets, QtCore
from ReNode.app.Logger import RegisterLogger
from ReNode.app.FileManager import FileManagerHelper
from ReNode.ui.GraphTypes import GraphTypeFactory
import os
import uuid

class TabData:
    def __init__(self,name='',file='') -> None:
        """
            - name - имя (класс) графа
            - file - относительный путь до файла
        """
        self.filePath = file
        self.name = name
        #self.serializedData = None
        #self.isActive = False
        self.isUnsaved = False

        # Here located all graph backend for this session
        self.graph = SessionManager.refObject.newInstanceGraph()

        self.variables = {}
        self.infoData = {}

        if self.filePath:
            try:
                self.graph.load_session(self.filePath,loadMouse=True)
            except Exception as e:
                import traceback
                strex = traceback.format_exc()
                SessionManager.refObject.logger.error(f"Ошибка при загрузке \"{self.filePath}\". Описание: {strex}")
            finally:
                self.variables = self.graph.variables #SessionManager.refObject.graphSystem.variable_manager.variables
                self.infoData = self.graph.infoData #SessionManager.refObject.graphSystem.inspector.infoData
        if self.infoData.get('classname'):
            self.name = self.infoData.get('classname')
        
        self.lastCompileGUID = self.getLastCompileGUID()

    def onGraphOpened(self):
            info = self.infoData
            
            if info and 'firstInitMethods' in info:
                initMethods:list[str] = info.get('firstInitMethods')
                makerList = ['' for _ in range(len(initMethods))]
                del info['firstInitMethods']
                fact = SessionManager.refObject.graphSystem.getFactory()
                parents = fact.getClassAllParents(info.get('classname')) or []
                for par in parents:
                    classData = fact.getClassData(par) or {}
                    nodeClasses = classData.get('methods',{}).get('nodes',[])
                    for node in nodeClasses:
                        nodeSysName = 'methods.' + node
                        nodeData = fact.getNodeLibData(nodeSysName) or {}
                        classMemberName = nodeData.get('classInfo',{}).get('name','')
                        if classMemberName in initMethods and nodeData.get('memtype','') in ['def','event']:
                            indexOf = initMethods.index(classMemberName)
                            makerList[indexOf] = nodeSysName
                
                # create nodes
                self.graph.begin_undo("Иницализация начальных узлов")
                newNodes = []
                for maker in makerList:
                    iObj = fact.instance(maker,self.graph)
                    if iObj:
                        newNodes.append(iObj)
                if newNodes:
                    self.graph.auto_layout_nodes(newNodes)
                self.graph.end_undo()
                self.graph.clear_undo_stack()

                cg = SessionManager.refObject.graphSystem.codegen
                cg.generateProcess(graph=self.graph,addComments=True,silentMode=True)

    def createCompilerGUID(self):
        guid = SessionManager.CreateCompilerGUID()
        self.lastCompileGUID = guid
        SessionManager.refObject.syncTabName(self.getIndex())
        return guid

    def __repr__(self) -> str:
        from sys import getsizeof
        return f'{self.name} {hex(id(self))} {getsizeof(self.graph)}'
    
    def getIndex(self):
        for idx, it in enumerate(SessionManager.refObject.tabData):
            if it == self: return idx
        return -1

    def save(self):
        if not self.filePath:
            return
        self.infoData['compiledGUID'] = self.lastCompileGUID
        self.graph.save_session(self.filePath,saveMouse=True)
        self.isUnsaved = False
        SessionManager.refObject.syncTabName(self.getIndex())

    def getLastCompileGUID(self):
        file = os.path.join(FileManagerHelper.getFolderCompiledScripts(),FileManagerHelper.getCompiledScriptFilename(self.infoData))
        if not os.path.exists(file):
            return ""
        prefixLen = "//src:8c2a235c-9997-49f9-8b58-04694ce2ae20"
        with open(file,'r',encoding='utf-8') as f:
            #read first bytes
            data = f.read(len(prefixLen))
            f.close()
        if len(data) < len(prefixLen):
            return ''
        dels = data.split(':')
        if len(dels) != 2:
            return ''
        return dels[1]

    #выгрузка и очистка вкладки
    def unloadTabLogic(self):
        graphComponent = SessionManager.refObject.graphSystem
        graphComponent.editorDock.setWidget(None)#!DONT DO THIS 
        
        self.graph.clear_undo_stack()
        self.graph.undo_stack().indexChanged.disconnect(self._historyChangeEvent)
        self.graph.clear_session()
        self.graph.close()
        self.graph.widget.deleteLater()
        self.graph.deleteLater()
        QApplication.processEvents()

        graphComponent.variable_manager.clearVariables()
        graphComponent.inspector.cleanupPropsVisual()

        graphComponent.graph = None
        graphComponent.tabSearch = None

    def loadTabLogic(self):
        from PyQt5.sip import isdeleted
        graphComponent = SessionManager.refObject.graphSystem
        #hide old graph
        if graphComponent.graph and graphComponent.graph.widget and not isdeleted(graphComponent.graph.widget):
            graphComponent.graph.widget.hide()
        
        #update graph reference
        graphComponent.graph = self.graph

        #reassign tabSearch
        graphComponent.tabSearch = self.graph._viewer._tabSearch

        # set to dock
        graphComponent.editorDock.setWidget(self.graph.widget)

        #show this graph
        self.graph.show()

        #load variables
        graphComponent.variable_manager.variables = self.variables
        graphComponent.variable_manager.syncVariableManagerWidget()

        #load graph info
        graphComponent.inspector.infoData = self.infoData
        graphComponent.inspector.updateProps()

        #load history widget
        graphComponent.undoView_dock.setWidget(self.graph.undo_view)

        pass
    
    def registerEvents(self):
        self.graph.undo_stack().indexChanged.connect(self._historyChangeEvent)
        self.graph.node_selection_changed.connect(self._nodeSelectionChanged)

    def _nodeSelectionChanged(self):
        if self and not self.isUnsaved:
            self.isUnsaved = True
            SessionManager.refObject.syncTabName(self.getIndex())

    def _historyChangeEvent(self):
        if self and not self.isUnsaved:
            self.isUnsaved = True
            SessionManager.refObject.syncTabName(self.getIndex())



class SessionManager(QTabWidget):
    refObject = None

    def __init__(self,graph) -> None:
        super().__init__()
        self.setObjectName("SessionManagerWindow")
        SessionManager.refObject = self
        self.logger = RegisterLogger("Session")

        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        self.graphSystem : NodeGraphComponent = graph

        self.setMovable(True)  # Разрешите перетаскивание вкладок.
        self.setTabsClosable(True)

        # Устанавливаем политику размеров для растяжения в вертикальном направлении.
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Изменяем минимальную высоту вкладки.
        self.tabBar().setMinimumHeight(50)  # Измените значение по вашему усмотрению.
        
        # Создайте и добавьте вкладки в верхнюю док-зону.
        #for i in range(1,20):
        #    self.addTab(QWidget(), 'Вкладка ' + str(i))

        self._initEvents()

    def _initEvents(self):
        #self.currentChanged.connect(self.handleTabChange)
        self.tabCloseRequested.connect(self.handleTabClose)
        self.tabBarClicked.connect(self.handleTabChange)
        self.tabBar().tabMoved.connect(self.handleMoved)

    @property
    def tabData(self) -> list[TabData]:
        tdat = []
        for i in range(self.count()):
            tdat.append(self.tabBar().tabData(i))
        return tdat

    def getAllTabs(self): return self.tabData
    
    def getActiveTabData(self):
        if self.tabBar().count() == 0: return None
        return self.getTabData(self.currentIndex())

    def getTabData(self,index) -> TabData:
        return self.tabBar().tabData(index)
    
    def getTabByPredicate(self,predicate,checkedValue) -> TabData|None:
        if predicate and callable(predicate):
            for tab in self.getAllTabs():
                if predicate(tab) == checkedValue:
                    return tab
        return None
    
    @staticmethod
    def CreateCompilerGUID():
        return str(uuid.uuid4())

    def syncTabName(self,idx):
        tdata = self.getTabData(idx)
        
        if not tdata: return

        unsafe = ""
        if tdata.isUnsaved:
            unsafe = "*"
        self.tabBar().setTabText(idx,f'{tdata.name}{unsafe}')
        ttp = f"Расположение: {tdata.filePath}\n"
        ttp += f"Имя: {tdata.infoData.get('name')}\n"
        ttp += f"Описание: {tdata.infoData.get('desc') or 'Отсутствует'}\n"
        if tdata.infoData.get('type','') in ["gamemode","role"]:
            gTypeName = tdata.infoData.get('type')
            typeName = "НЕИЗВЕСТНО"
            gObj = GraphTypeFactory.getInstanceByType(gTypeName)
            if gObj: typeName = gObj.getName()
            ttp += f"Тип графа: {typeName}\n\n"
            ttp += f'Класс: {tdata.infoData.get("classname")}\n'
            ttp += f"Родитель: {tdata.infoData.get('parent')}\n"
            ttp += f'GUID сброки: {tdata.lastCompileGUID or "не скомпилирован"}'
            
        self.tabBar().setTabToolTip(idx,ttp)

    def handleMoved(self,index):
        #print(f"moved to {index}")
        pass

    def newTab(self,switchTo=False,loader='',optionsToCreate=None):
        idx = self.addTab(QWidget(),"tab")
        graphName = "Новый граф"
        if optionsToCreate:
            graphName = optionsToCreate.get("classname") or graphName

            
            defaultGraph = {
                "graph": {
                    "variables": {},
                    "info": optionsToCreate,
                },
                "nodes": {},
                "connections": []
            }
            
            os.makedirs(os.path.dirname(loader), exist_ok=True)
            self.graphSystem.graph.save_session(loader,defaultGraph)
            self.graphSystem.getFactory().vlib.file_event_handler.reloadLibFull()
        
        tabCtx = TabData(graphName,loader)
        self.tabBar().setTabData(idx,tabCtx)
        self.syncTabName(idx)

        tabCtx.onGraphOpened()
        
        tabCtx.registerEvents()
        if switchTo:
            self.setActiveTab(idx)
        
        return tabCtx

    def setActiveTab(self,index):
        if index < 0 or index >= self.count():
            return
        self.tabBar().setCurrentIndex(index)
        self.handleTabChange(index)

    def openFile(self):
        path = self.graphSystem.dummyGraph.load_dialog(FileManagerHelper.getWorkDir(),kwargs={"ext":"graph","customSave":True})
        if not path: return
        path = FileManagerHelper.getGraphPathRelative(path)
        allTabs = self.tabData
        if path in [tab.filePath for tab in allTabs]:
            self.setActiveTab([tab.filePath for tab in allTabs].index(path))
            self.logger.info(f"Граф {path} уже открыт. Переключение активной вкладки")
            return
        self.newTab(True,path)

    def saveFile(self,tabData:TabData=None):
        tdata = tabData or self.getActiveTabData()
        if not tdata:
            self.logger.warning("Нет активной вкладки для сохранения файла")
            return
        
        #save if filePath not empty
        if tdata.filePath:
            tdata.save()
            self.logger.info(f'Сохранение {tdata.filePath}')
            return

        path = self.graphSystem.dummyGraph.save_dialog(FileManagerHelper.getWorkDir(),kwargs={"ext":"graph","customSave":True})
        if not path:
            return
        path = FileManagerHelper.getGraphPathRelative(path)
        tdata.filePath = path
        tdata.save()
        self.logger.info(f'Сохранение {tdata.filePath}')
        pass

    def validateExit(self):
        if any([tab.isUnsaved for tab in self.tabData if tab.isUnsaved]):
            from ReNode.app.application import Application
            
            reply = QMessageBox.warning(self, 'Закрытие', f'Вы уверены, что хотите закрыть {Application.appName}?\nВсе несохраненные данные будут утеряны.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            return reply == QMessageBox.Yes
        return True

    def registerFileWatch(self,path):
        import os
        fs_watcher = QtCore.QFileSystemWatcher()
        fs_watcher.addPath(os.path.abspath(path))
        #print fws files
        fs_watcher.fileChanged.connect(path)
        fs_watcher.file
        return fs_watcher

    def handleTabChange(self, index):
        if index < 0:
            print("Теперь нет активной вкладки")
            return
        print(f'Активная вкладка изменилась на {index} {self.getTabData(index)}')  
        self.getTabData(index).loadTabLogic()

    def handleTabClose(self, index):
        tabData = self.getTabData(index)
        condition = True
        if tabData.isUnsaved:
            # В этом методе вы можете запросить подтверждение пользователя перед закрытием вкладки
            reply = QMessageBox.question(self, 'Закрыть вкладку', 'Вы уверены, что хотите закрыть эту вкладку?\nВсе несохраненные данные будут утеряны.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            condition = reply == QMessageBox.Yes

        if condition:
            self.removeTab(index)
            tabData.unloadTabLogic()
            del tabData
            self.setActiveTab(self.count()-1)
    def showContextMenu(self):
            menu = QMenu(self)

            # Создайте действия для каждой вкладки
            for i in range(self.count()):
                action = QAction(self.tabText(i), self)
                action.triggered.connect(lambda checked, index=i: self.switchToTab(index))
                menu.addAction(action)

            # Отобразите контекстное меню рядом с кнопкой внутри док-зоны
            self.dock.setWidget(self)
            menu.exec_(self.context_menu_button.mapToGlobal(self.context_menu_button.rect().bottomRight()))
    
    def switchToTab(self, index):
        self.setCurrentIndex(index)
        tabData = self.getTabData(index)

    def newInstanceGraph(self):
        """
            Create and initialize new graph backend object
        """
        from NodeGraphQt import NodeGraph
        graphComponent = self.graphSystem #.editorDock
        #graph : NodeGraph = self.graphSystem.graph
        #oldVwr = graph._viewer
        #oldModel = graph._model
        #factory = graph._node_factory #copyable
        #stack = graph._undo_stack
        #undoView = graph._undo_view
        
        #save old graphComponent props
        oldTabSearch = graphComponent.tabSearch
        oldGraph = graphComponent.graph

        #hide old graph
        #graphComponent.editorDock.setWidget(None)
        
        args = {
            #'factory': factory, #dont use it, factory get id's from model
        }
        graph = NodeGraph(**args)
        
        #here self is graphComponent
        graphComponent.graph = graph
        
        #ref from native graph to custom factory
        graph._factoryRef = graphComponent.nodeFactory

        graphComponent.tabSearch = graph._viewer._tabSearch
        graph._viewer._tabSearch.nodeGraphComponent = graphComponent
        
        #! do not add: graphComponent.editorDock.setWidget(graph.widget)
        
        #add events and common setup
        graphComponent._addEvents()
        graphComponent.contextMenuLoad()
        graphComponent.registerNodes()

        graphComponent.generateTreeDict()

        #show graph
        #! do not show: graph.show()

        #reset graphComponent props to old
        graphComponent.tabSearch = oldTabSearch
        graphComponent.graph = oldGraph

        return graph
    
    def getOpenedSessionPathes(self):
        pathes = []
        for tab in self.getAllTabs():
            if tab.filePath:
                pathes.append(tab.filePath)
        ret = "|".join(pathes)
        if not ret:
            ret = "empty"
        return ret
    
    def loadSessionPathes(self,pathes):
        if pathes == "empty": return

        for p in pathes.split("|"):
            if os.path.exists(p):
                self.newTab(True,p)
            else:
                self.logger.warning(f"Загрузка сессии \"{p}\" невозможна - файл не существует")