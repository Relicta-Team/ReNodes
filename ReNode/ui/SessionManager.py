import typing
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.sip import isdeleted
from Qt import QtWidgets, QtCore
from NodeGraphQt.base.commands import UndoCommand
from ReNode.app.Logger import RegisterLogger
from ReNode.app.FileManager import FileManagerHelper
from ReNode.ui.GraphTypes import GraphTypeFactory
from ReNode.ui.SessionManager_CompileStatus import CompileStatus
import os
import uuid
import time
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler, EVENT_TYPE_DELETED,EVENT_TYPE_MODIFIED

class SingleFileEventWatcher(FileSystemEventHandler):
    def __init__(self) -> None:
        super().__init__()
        self.ssmgr:SessionManager = SessionManager.refObject

    def callFileEvent(self,path,evtype):
        self.ssmgr.on_update_file.emit(path,evtype)

    def validate_event(self,event: FileSystemEvent):
        return event.src_path.endswith('.graph')

    def on_modified(self, event: FileSystemEvent):
        if self.validate_event(event) and not event.is_directory:
            self.callFileEvent(event.src_path,event.event_type)
            pass

    def on_created(self, event: FileSystemEvent):
        if self.validate_event(event):
            pass

    def on_deleted(self, event: FileSystemEvent):
        if self.validate_event(event):
            self.ssmgr.on_update_file.emit(event.src_path,event.event_type)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        if self.validate_event(event):
            pass

class TabData:
    def __init__(self,name='',file='') -> None:
        """
            - name - имя (класс) графа
            - file - относительный путь до файла (содержит root:)
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

        self.undo_saved_index = self.getCurrentUndoStackIndex()

        # данные для успешной компиляции
        self.last_compile_undo_object = None
        self.has_compile_warnings = False
        self.has_compile_errors = False
        self.last_compile_success = False

        if self.filePath:
            try:
                self.graph.load_session(FileManagerHelper.graphPathGetReal(self.filePath),loadMouse=True)
            except Exception as e:
                import traceback
                strex = traceback.format_exc()
                SessionManager.refObject.logger.error(f"Ошибка при загрузке \"{self.filePath}\". Описание: {strex}")
            finally:
                self.variables = self.graph.variables #SessionManager.refObject.graphSystem.variable_manager.variables
                self.infoData = self.graph.infoData #SessionManager.refObject.graphSystem.inspector.infoData
        if self.infoData.get('classname'):
            self.name = self.infoData.get('classname')
        
        self.lastTimeSave = os.path.getmtime(FileManagerHelper.graphPathGetReal(self.filePath,True))

        _fileCompGuid = self.getLastCompileGUID()
        _graphCompGuid = self.infoData.get('compiledGUID','')
        _equalCompGuid = _fileCompGuid == _graphCompGuid
        self.lastCompileGUID = _graphCompGuid
        _status = CompileStatus.stringToStatus(self.infoData.get("compileStatus",'NotCompiled'))
        if not _equalCompGuid:
            _status = CompileStatus.NotCompiled
        self.lastCompileStatus = _status
        
        self._onOpenOrSaveLastCompileStatus = self.lastCompileStatus

        self.graph.undo_view.setEmptyLabel("<Открытие {}>".format(self.name))
        self.graph.undo_view.setCleanIcon(QtGui.QIcon(CompileStatus.getCompileIconByStatus(self.lastCompileStatus)))

        self._obsWatch = None
        if self.filePath:
            self._sessionFileHandler = SingleFileEventWatcher()
            obs:Observer = SessionManager.refObject.fileObserver
            self._obsWatch = obs.schedule(self._sessionFileHandler, FileManagerHelper.graphPathGetReal(self.filePath,returnAbsolute=True))
    
    def _session_unloadEvent_(self):
        obs:Observer = SessionManager.refObject.fileObserver
        if self._obsWatch:
            obs.unschedule(self._obsWatch)

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

                self.save()

    def getRealPath(self):
        return FileManagerHelper.graphPathGetReal(self.filePath)

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
    
    def isActiveTab(self):
        return SessionManager.refObject.getActiveTabData() == self

    def save(self):
        if not self.filePath:
            return
        self.infoData['compiledGUID'] = self.lastCompileGUID
        self.infoData['compileStatus'] = CompileStatus.statusToString(self.lastCompileStatus)
        self.infoData['graphVersion'] = SessionManager.refObject.graphSystem.getFactory().graphVersion
        
        self._onOpenOrSaveLastCompileStatus = self.lastCompileStatus

        self.graph.save_session(FileManagerHelper.graphPathGetReal(self.filePath),saveMouse=True)
        
        self.lastTimeSave = os.path.getmtime(FileManagerHelper.graphPathGetReal(self.filePath,True))
        self.undo_saved_index = self.getCurrentUndoStackIndex()
        self._syncHistoryEvent()
        SessionManager.refObject.syncTabName(self.getIndex())

    def getLastCompileGUID(self):
        file = os.path.join(FileManagerHelper.getFolderCompiledScripts(),FileManagerHelper.getCompiledScriptFilename(self.infoData))
        if not os.path.exists(file):
            return ""
        prefixLen = "//src:8c2a235c-9997-49f9-8b58-04694ce2ae20"
        with open(file,encoding='utf-8') as f:
            #read first bytes
            data = f.read(len(prefixLen))
            #f.close()
        if len(data) < len(prefixLen):
            return ''
        dels = data.split(':')
        if len(dels) != 2:
            return ''
        return dels[1]

    #выгрузка и очистка вкладки
    def unloadTabLogic(self):
        self._session_unloadEvent_()
        graphComponent = SessionManager.refObject.graphSystem
        graphComponent.editorDock.setWidget(None)#!DONT DO THIS 
        
        self.graph.clear_undo_stack()
        self.graph.undo_stack().indexChanged.disconnect(self._syncHistoryEvent)
        self.graph.clear_session()
        self.graph.close()
        self.graph.widget.deleteLater()
        self.graph.deleteLater()
        #QApplication.processEvents() #!this is really need?

        graphComponent.variable_manager.clearVariables()
        graphComponent.inspector.cleanupPropsVisual()

        graphComponent.graph = None
        graphComponent.tabSearch = None

    def loadTabLogic(self):
        
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
    
    def getCurrentUndoStackIndex(self): 
        if self.graph and not isdeleted(self.graph):
            return self.graph.undo_stack().index()
        else:
            return -1
    
    def getCurrentUndoStackObject(self,optIdx=None):
        if self.graph and not isdeleted(self.graph):
            if optIdx == None:
                optIdx = self.getCurrentUndoStackIndex() - 1 #zeroindex is empty command
            else:
                optIdx -= 1
            cmdImpl = self.graph.undo_stack().command(optIdx)
            if not cmdImpl: return None
            return cmdImpl
        else:
            return None

    def registerEvents(self):
        self.graph.undo_stack().indexChanged.connect(self._syncHistoryEvent)
        #self.graph.node_selection_changed.connect(self._nodeSelectionChanged)

    def _nodeSelectionChanged(self):
        if self and not self.isUnsaved:
            self.isUnsaved = True
            SessionManager.refObject.syncTabName(self.getIndex())

    def _syncHistoryEvent(self,idx=None):
        if self:
            cobj = self.getCurrentUndoStackObject(idx)
            self.isUnsaved = self.getCurrentUndoStackIndex() != self.undo_saved_index
            
            newState = CompileStatus.NotCompiled
            
            if cobj == self.last_compile_undo_object:
                if cobj == None:
                    newState = self._onOpenOrSaveLastCompileStatus
                if self.last_compile_success:
                    newState = CompileStatus.Compiled
                    if self.has_compile_warnings:
                        newState = CompileStatus.Warnings
                if self.has_compile_errors:
                    newState = CompileStatus.Errors


            self.lastCompileStatus = newState
            SessionManager.refObject.syncTabName(self.getIndex())

    def setCompileState(self,isSuccess,hasErrors,hasWarnings):        
        cobj = self.getCurrentUndoStackObject()
        self.has_compile_errors = hasErrors
        self.has_compile_warnings = hasWarnings
        self.last_compile_success = isSuccess
        self.last_compile_undo_object = cobj
        
        self._syncHistoryEvent()

        if isSuccess:
            self.graph.undo_stack().setClean()
            self.graph.undo_view.setCleanIcon(QtGui.QIcon(CompileStatus.getCompileIconByStatus(self.lastCompileStatus)))


class SessionManager(QTabWidget):
    refObject = None
    on_update_file = pyqtSignal(str,str)

    class TabBar(QTabBar):
        def mousePressEvent(self, event):    
            if event.button() == Qt.MouseButton.LeftButton:
                super().mousePressEvent(event)
                event.accept()
            elif event.button() == Qt.MouseButton.RightButton:
                SessionManager.refObject.showContextMenu()
                event.ignore()
        def wheelEvent(self,event):
            pass

    def __init__(self,graph) -> None:
        super().__init__()
        self.setObjectName("SessionManagerWindow")
        SessionManager.refObject = self
        self.logger = RegisterLogger("Session")

        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        self.graphSystem : NodeGraphComponent = graph

        self.setMovable(True)  # Разрешите перетаскивание вкладок.
        self.setTabsClosable(True)

        #self.setTabBar(SessionManager.TabBar())
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # Устанавливаем политику размеров для растяжения в вертикальном направлении.
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Изменяем минимальную высоту вкладки.
        self.tabBar().setMinimumHeight(50)  # Измените значение по вашему усмотрению.

        self._initEvents()

        self._lastOpenPath = FileManagerHelper.getWorkDir()
        
        self.fileObserver = Observer()
        self.fileObserver.start()
        self.fileObserver.name = "SessionManager_Observer"
        self.on_update_file.connect(self._session_fileChanged)

    def _initEvents(self):
        #self.currentChanged.connect(self.handleTabChange)
        self.tabCloseRequested.connect(self.handleTabClose)
        self.tabBarClicked.connect(self.handleTabChange_click)
        self.tabBar().tabMoved.connect(self.handleMoved)

    def _session_fileChanged(self,path:str,event_type:str):
        tdat = None
        lpat = path.lower()
        for t_ in self.getAllTabs():
            if FileManagerHelper.graphPathGetReal(t_.filePath,True).lower() == lpat:
                tdat = t_
                break
        
        if not tdat and event_type == EVENT_TYPE_MODIFIED: 
            self.logger.error(f'Не удалось перезагрузить \"{path}\" - вкладка не найдена')
            return
        if event_type == EVENT_TYPE_DELETED:
            self.logger.info("Файл удалён \"{}\"".format(tdat.filePath))
            self.handleTabClose(tdat.getIndex(),True)
            return
        if tdat.lastTimeSave == os.path.getmtime(FileManagerHelper.graphPathGetReal(tdat.filePath,True)):
            self.logger.debug(f'File cahnged inside tab {tdat.name}')
            return

        self.logger.info("Файл изменён \"{}\"".format(tdat.filePath))
        doReload = True
        if tdat.isUnsaved:
            rep = QMessageBox.warning(SessionManager.refObject, 'Обнаружено изменение', f'Вкладка \"{tdat.name}\" была изменена. Вы хотите обновить её? Все несохраненные данные будут утеряны.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep != QMessageBox.Yes:
                doReload = False
        if doReload:
            self.updateSession(tdat.getIndex())

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
                if tab and predicate(tab) == checkedValue:
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
        compstat = tdata.lastCompileStatus
        icnPath = CompileStatus.getCompileIconByStatus(compstat)
        self.tabBar().setTabIcon(idx,QtGui.QIcon(icnPath))
        self.tabBar().setIconSize(QtCore.QSize(18, 18))
        ttp = "<html><body>"
        ttp += f"Расположение: {tdata.filePath}\n"
        ttp += f"Имя: {tdata.infoData.get('name')}\n"
        ttp += f"Описание: {tdata.infoData.get('desc') or 'Отсутствует'}\n"
        ttp += f'Сборка: {CompileStatus.getCompileTextByStatus(compstat,withColor=True)}\n'
        if tdata.infoData.get('type','') in ["gamemode","role"]:
            gTypeName = tdata.infoData.get('type')
            typeName = "НЕИЗВЕСТНО"
            gObj = GraphTypeFactory.getInstanceByType(gTypeName)
            if gObj: typeName = gObj.getName()
            ttp += f"Тип графа: {typeName}\n\n"
            ttp += f'Класс: {tdata.infoData.get("classname")}\n'
            ttp += f"Родитель: {tdata.infoData.get('parent')}\n"
            ttp += f'GUID сброки: {tdata.lastCompileGUID or "не скомпилирован"}'
        
        ttp += "</body></html>"
        ttp = ttp.replace("\n","<br/>")

        self.tabBar().setTabToolTip(idx,ttp)

    def handleMoved(self,index):
        #print(f"moved to {index}")
        pass

    def newTab(self,switchTo=False,loader='',optionsToCreate=None):
        
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
            # здесь загрузчик не нужно очищать
            os.makedirs(os.path.dirname(loader), exist_ok=True)
            self.graphSystem.graph.save_session(loader,defaultGraph)
            #!!!self.graphSystem.getFactory().vlib.file_event_handler.reloadLibFull()
            
            cgUnit = SessionManager.refObject.graphSystem.codegen.__class__()
            crez = cgUnit.generateProcess(graph=loader,addComments=True,silentMode=True,compileParams={
				"-logexcept"
			})
            self.logger.debug(f'New graph compile result {crez}')
            del cgUnit

            if not FileManagerHelper.graphPathIsRoot(loader):
                loader = FileManagerHelper.graphPathToRoot(loader)
        
        idx = self.addTab(QWidget(),"Новая вкладка")

        #lg = SessionManager.refObject.logger
        #t_ = time.time()
        
        tabCtx = TabData(graphName,loader)
        
        #lg.debug(f"--- tab object create {time.time()-t_}")
        #t_ = time.time()
        
        self.tabBar().setTabData(idx,tabCtx)
        
        #lg.debug(f"--- tab data load {time.time()-t_}")
        #t_ = time.time()

        self.syncTabName(idx)
        tabCtx.registerEvents()

        #lg.debug(f'--- tab load other actions {time.time()-t_}')

        if switchTo:
            self.setActiveTab(idx)
        
        tabCtx.onGraphOpened()
        
        return tabCtx

    def setActiveTab(self,index):
        if index < 0 or index >= self.count():
            return
        self.tabBar().setCurrentIndex(index)
        self.handleTabChange(index)

    def handleTabChange_click(self,index):
        
        self.setActiveTab(index)

    def openFile(self):
        path = self.graphSystem.dummyGraph.load_dialog(self._lastOpenPath,kwargs={"ext":"graph","customSave":True})
        if not path: return
        self._lastOpenPath = os.path.dirname(path)
        path = FileManagerHelper.getGraphPathRelative(path)
        path = FileManagerHelper.graphPathToRoot(path) #add root prefix
        return self.openFileInternal(path)

    def openFileInternal(self,pathRoot):
        allTabs = self.tabData
        if pathRoot in [tab.filePath for tab in allTabs]:
            tInd = [tab.filePath for tab in allTabs].index(pathRoot)
            self.setActiveTab(tInd)
            self.logger.info(f"Граф {pathRoot} уже открыт. Переключение активной вкладки")
            return allTabs[tInd]
        return self.newTab(True,pathRoot)

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

    def handleTabChange(self, index):
        if index < 0:
            print("Теперь нет активной вкладки")
            return
        if self.getTabData(index).graph.widget.isVisible(): return
        print(f'Активная вкладка изменилась на {index} {self.getTabData(index)}')
        self.getTabData(index).loadTabLogic()

    def handleTabClose(self, index,forceClose=False):
        tabData = self.getTabData(index)
        condition = True
        if tabData.isUnsaved and not forceClose:
            # В этом методе вы можете запросить подтверждение пользователя перед закрытием вкладки
            reply = QMessageBox.question(self, 'Закрыть вкладку', 'Вы уверены, что хотите закрыть эту вкладку?\nВсе несохраненные данные будут утеряны.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            condition = reply == QMessageBox.Yes

        if condition:
            curIdx = self.currentIndex()
            isLatestTab = self.count()-1 == index
            isFirstTab = index == 0
            self.removeTab(index)
            tabData.unloadTabLogic()
            del tabData
            if isLatestTab:
                self.setActiveTab(self.count()-1)
            else:
                if not isFirstTab:
                    self.setActiveTab(curIdx - 1) #-1 because we removed tab
                else:
                    self.setActiveTab(0)
    def showContextMenu(self):
            

            
            curTabRect = self.tabBar().tabRect(self.currentIndex())
            cpos = self.mapFromGlobal(QtGui.QCursor.pos())
            insideCurrent = curTabRect.intersects(QRect(cpos,QSize(2,2)))
            idxClick = self.tabBar().tabAt(cpos)
            ctd = self.getTabData(idxClick)
            if not ctd: return
            
            menu = QMenu(self)
            # Создайте действия для каждой вкладки
            menu.addAction(f"Меню \"{ctd.name}\"" + (" (текущий)" if insideCurrent else "")).setEnabled(False)
            menu.addAction("").setEnabled(False)
            menu.addSeparator()
            actSwitch = menu.addMenu("Закладки")
            actsGraph = menu.addMenu("Граф")
            actOpts = menu.addMenu("Опции")
            
            for i in range(self.count()):
                if idxClick == i:
                    continue
                action = QAction("Переключиться на " + self.tabText(i), self)
                action.triggered.connect(lambda checked, index=i: self.setActiveTab(index))
                actSwitch.addAction(action)

            actsGraph.addAction(QAction("[ДОБАВИТЬ] Открыть расположение графа",self))
            actsGraph.addAction(QAction("[ДОБАВИТЬ] Открыть расположение скомпилированного графа",self))

            actOpts.addAction(QAction("[ДОБАВИТЬ] Закрыть все вкладки слева",self))
            actOpts.addAction(QAction("[ДОБАВИТЬ] Закрыть все вкладки справа",self))
                

            # Отобразите контекстное меню рядом с кнопкой внутри док-зоны
            #self.dock.setWidget(self)
            menu.exec_(QtGui.QCursor.pos())
    
    def switchToTab(self, index):
        #DO NOT USE THIS
        assert(False)
        self.setCurrentIndex(index)
        tabData = self.getTabData(index)

    def updateSession(self,index):
        tdata = self.getTabData(index)
        if tdata:
            curActive = self.currentIndex()
            fp_ = tdata.filePath
            needSwitch = self.currentIndex() == index
            st1 = time.time()
            self.handleTabClose(index,forceClose=True)
            self.logger.debug(f'Tab closed at {time.time()-st1}')
            st2 = time.time()
            ntObj = self.newTab(needSwitch,fp_)
            self.logger.debug(f'Tab opened at {time.time()-st2}')
            self.tabBar().moveTab(ntObj.getIndex(),index)
            #reset active tab
            if not needSwitch:
                self.setActiveTab(curActive)
        

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
                fp = tab.filePath
                if tab.isActiveTab():
                    fp = "active:"+fp
                pathes.append(fp)
        ret = "|".join(pathes)
        if not ret:
            ret = "empty"
        return ret
    
    def loadSessionPathes(self,pathes):
        if pathes == "empty": return
        hasActiveTab = len([x for x in pathes.split("|") if x.startswith("active:")]) > 0
        defaultActive = not hasActiveTab

        for p in pathes.split("|"):
            setActive = defaultActive
            if p.startswith("active:"):
                p = p[len("active:"):]
                setActive = True
            if FileManagerHelper.graphPathExists(p):
                self.newTab(setActive,p)
            else:
                self.logger.warning(f"Загрузка сессии \"{p}\" невозможна - файл не существует")