import typing
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from Qt import QtWidgets, QtCore
from ReNode.app.Logger import RegisterLogger
from ReNode.app.FileManager import FileManagerHelper

class TabData:
    def __init__(self,name='',file='') -> None:
        self.filePath = file
        self.name = name
        self.serializedData = None
        self.isActive = False
        self.isUnsaved = True

        # Here located all graph backend for this session
        self.graph = SessionManager.refObject.newInstanceGraph()

        self.variables = {}

    def __repr__(self) -> str:
        from sys import getsizeof
        return f'{self.name} {hex(id(self))} {getsizeof(self.graph)}'
    
    def unloadTabLogic(self):
        graphComponent = SessionManager.refObject.graphSystem
        graphComponent.editorDock.setWidget(None)#!DONT DO THIS 
        
        self.graph.clear_undo_stack()
        self.graph.clear_session()
        self.graph.close()
        self.graph.widget.deleteLater()
        self.graph.deleteLater()
        QApplication.processEvents()

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

        #load history widget
        graphComponent.undoView_dock.setWidget(self.graph.undo_view)

        pass




class SessionManager(QTabWidget):
    refObject = None

    def __init__(self,graph) -> None:
        super().__init__()
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

    def getActiveTabData(self):
        if self.tabBar().count() == 0: return None
        return self.getTabData(self.currentIndex())

    def getTabData(self,index) -> TabData:
        return self.tabBar().tabData(index)

    def syncTabName(self,idx):
        tdata = self.getTabData(idx)
        unsafe = ""
        if tdata.isUnsaved:
            unsafe = "*"
        self.tabBar().setTabText(idx,f'{tdata.name}{unsafe}')
        self.tabBar().setTabToolTip(idx,"Без описания")

    def handleMoved(self,index):
        #print(f"moved to {index}")
        pass

    def newTab(self,switchTo=False):
        idx = self.addTab(QWidget(),"tab")
        tabCtx = TabData("Новый граф")
        self.tabBar().setTabData(idx,tabCtx)
        self.syncTabName(idx)
        if switchTo:
            self.setActiveTab(idx)

    def setActiveTab(self,index):
        if index < 0 or index >= self.count():
            return
        self.tabBar().setCurrentIndex(index)
        self.handleTabChange(index)

    def openFile(self):
        pass

    def saveFile(self):
        if not self.getActiveTabData():
            self.logger.warning("Нет активной вкладки для сохранения файла")
            return
        path = self.graphSystem.graph.save_dialog(FileManagerHelper.getWorkDir(),kwargs={"ext":"graph","customSave":True})
        if not path:
            return
        path = FileManagerHelper.getGraphPathRelative(path)
        self.logger.info(f'Сохранение в файл {path}')
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
        if tabData.isUnsaved:
            # В этом методе вы можете запросить подтверждение пользователя перед закрытием вкладки
            reply = QMessageBox.question(self, 'Закрыть вкладку', 'Вы уверены, что хотите закрыть эту вкладку?\nВсе несохраненные данные будут утеряны.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.removeTab(index)
                tabData.unloadTabLogic()
                #self.tabBar().removeTab(index)
                del tabData

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
            #'factory': factory,
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