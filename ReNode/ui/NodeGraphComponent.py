import uuid
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *

from NodeGraphQt import (NodeGraph, GroupNode, NodeGraphMenu)
from NodeGraphQt.base.menu import NodesMenu,ContextMenu
from NodeGraphQt.custom_widgets.properties_bin.node_property_widgets import PropertiesBinWidget
from NodeGraphQt.qgraphics.node_base import NodeItem
from NodeGraphQt.widgets.viewer import NodeViewer
from ReNode.ui.Nodes import RuntimeNode, RuntimeGroup
from ReNode.ui.NodeContextMenuUtility import *
from ReNode.app.utils import *
from ReNode.app.NodeFactory import NodeFactory
from ReNode.app.CodeGen import CodeGenerator
from ReNode.app.NodeSync import NodeSyncronizer
from ReNode.ui.LoadingScreen import LoadingScreen

from NodeGraphQt.nodes.base_node import *
from ReNode.ui.TabSearchMenu import TabSearchMenu

from ReNode.ui.VariableManager import VariableManager
from ReNode.app.config import Config
from ReNode.app.DebuggerServer import DebuggerServer,DummyDebuggerServer
from ReNode.app.Constants import NodeLambdaType

class NodeGraphComponent:

	refObject = None

	def __init__(self,mainWindow) -> None:
		from ReNode.ui.AppWindow import MainWindow
		from ReNode.app.application import Application
		from ReNode.ui.ScriptMaker import ScriptMakerManager
		from threading import Lock

		# global reference to object instance		
		NodeGraphComponent.refObject = self

		#thread locker and debugger server init
		if Application.hasArgument("-noapp"):
			self.debuggerServer = DummyDebuggerServer()
		else:
			self.debuggerServer = DebuggerServer(nodeGraphRef=self)
			self.debuggerServer.start()

		#common props
		self.variable_manager = None
		self.mainWindow : MainWindow = mainWindow
		self.nodeFactory : NodeFactory = mainWindow.nodeFactory

		#graph setup
		graph = NodeGraph()
		self.graph = graph
		self.dummyGraph = graph #first loaded graph 
		
		#ref from native graph to custom factory
		graph._factoryRef = self.nodeFactory

		self.tabSearch : TabSearchMenu = graph._viewer._tabSearch
		graph._viewer._tabSearch.nodeGraphComponent = self

		self.codegen = CodeGenerator()
		self.codegen.graphsys = self

		self.script_maker = ScriptMakerManager(self)

		self.node_sync = NodeSyncronizer(self)

		#notNested = self.mainWindow.dockOptions() & ~QMainWindow.DockOption.AllowNestedDocks
		#notNested = notNested & ~QMainWindow.DockOption.AllowTabbedDocks
		#self.mainWindow.setDockOptions(notNested)

		self.mdiArea = QMdiArea()
		self.mdiArea.setBackground(QtGui.QColor(0, 0, 0, 0))
		self.mdiArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.mdiArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.mdiArea.setViewMode(QMdiArea.TabbedView)
		self.mdiArea.setDocumentMode(True)
		self.mdiArea.setTabsClosable(True)
		self.mdiArea.setTabsMovable(True)

		dock = QDockWidget("Editor main")
		self.editorDock = dock
		dock.setWidget(graph.widget)
		#dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
		#dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
		#dock.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
		dock.setWindowTitle("Граф")#upper title
		#dock.setWindowFlags(Qt.Widget)
		# Скройте заголовок и кнопки закрытия, максимизации и сворачивания.
		#dock.setTitleBarWidget(QWidget())
		mainWindow.addDockWidget(Qt.RightDockWidgetArea, dock)
		graph.show()

		self.mainWindow.setCentralWidget(self.editorDock)

		self._initTabs(dock)

		self._initVariableManager()
		self._initInspector()
		self._initLoggerDock()
		self._initHistoryDock()
		
		#для сброса на настройки по умолчанию
		self._defaultState = self.mainWindow.saveState()
		self._defaultGeometry = self.mainWindow.saveGeometry()

		self._addEvents()
		self.contextMenuLoad()
		self.registerNodes()

		graph.auto_layout_nodes() 
		#n_backdrop = graph.create_node('Backdrop')
		#n_backdrop.wrap_nodes([groupnode, node])

		self.generateTreeDict()
		
		self.editorDock.setWidget(None)

		#! test compilation
		#self.compileAllGraphs()

	def compileAllGraphs(self,useLoadingScreen=False,onlyNotActual = False,compileFlags={}):
		import concurrent.futures
		import threading
		import time
		import datetime
		from ReNode.app.FileManager import FileManagerHelper
		from ReNode.ui.LoggerConsole import LoggerConsole
		graphList = []
		if onlyNotActual:
			graphList = FileManagerHelper.getBuildRequiredGraphs(returnFullData=True)
		else:
			graphList = FileManagerHelper.getCompareCompiledGraphsInfo() #FileManagerHelper.getAllGraphPathes()
		allGraphsWithIndex = [(path['graph_path'],i+1) for i,path in enumerate(graphList)]

		nonActualList = []
		for d in graphList:
			if not d['gver_actual']:
				nonActualList.append(d['graph_path'])

		if onlyNotActual and not graphList:
			CodeGenerator.refLogger.info("Все графы собраны. Сборка пропущена")
			return True

		timestamp = int(time.time()*1000.0)

		self._compileGraphList_useLoadingScreen = useLoadingScreen
		if useLoadingScreen:
			self._compileGraphList_lockerObject = threading.Lock()
			self._compileGraphList_loadingScreen = LoadingScreen()
			self._compileGraphList_increment = 0
			self._compileGraphList_oneItemLoad = len(allGraphsWithIndex)
			self._compileGraphList_loadingScreen.setMessage("Сборка")
		
		cFlags = {"-skipgenloader","-logexcept"} #,"-exceptinfo" для подробного вывода исключений
		cFlags.update(compileFlags)

		def __compile(path_with_idx):
			path, index = path_with_idx
			
			#remove root dir from path
			if path.startswith(".\\"):
				path = path[2:]
			
			if self._compileGraphList_useLoadingScreen:
				self._compileGraphList_loadingScreen.setMessage("Сборка " + path)
			
			cgObj = CodeGenerator()
			rez = cgObj.generateProcess(path, silentMode=True,compileParams=cFlags,prefixGen=f"({index}/{len(allGraphsWithIndex)}) ")
			del cgObj

			if self._compileGraphList_useLoadingScreen:
				with self._compileGraphList_lockerObject:
					self._compileGraphList_increment += 1
					self._compileGraphList_loadingScreen.setProgress(
						self._compileGraphList_increment * 100 / self._compileGraphList_oneItemLoad
					)

			if not rez:
				if not FileManagerHelper.graphPathIsRoot(path):
					path = FileManagerHelper.graphPathToRoot(path)
				CodeGenerator.refLogger.error(f'Граф \"{LoggerConsole.createNodeGraphReference(path,text=path)}\" не собран.')

			return rez
		with concurrent.futures.ThreadPoolExecutor() as executor:
			executor._thread_name_prefix = "CGCompiler"
			results = list(executor.map(__compile,allGraphsWithIndex))
		
		if useLoadingScreen:
			self._compileGraphList_loadingScreen.finalize()

		if all(results):
			FileManagerHelper.generateScriptLoader()
		else:
			CodeGenerator.refLogger.error("Обнаружены ошибки при сборке")
		
		FileManagerHelper.saveAllCompiledGUIDs() #saving all guids after compilation

		compFinalDt = datetime.datetime.now().strftime("%H:%M:%S.%f")
		CodeGenerator.refLogger.info(f"Скомпилировано {len([x for x in results if x])} из {len(results)}")
		CodeGenerator.refLogger.info(f'Выполнено в {compFinalDt} за {int(time.time()*1000.0) - timestamp} мс')
		CodeGenerator.refLogger.info("-" * 30)

		if nonActualList:
			CodeGenerator.refLogger.warn(f"Обнаружены устаревшие версии графов. Откройте и сохраните следующие графы для обновления версии.")
			CodeGenerator.refLogger.warn("Обратите внимание, что при обновлении версии графов некоторые связи могут быть отозваны.")
			for path in nonActualList:
				if not FileManagerHelper.graphPathIsRoot(path):
					path = FileManagerHelper.graphPathToRoot(path)
				CodeGenerator.refLogger.warn("Обновите версию "+LoggerConsole.createNodeGraphReference(path,text=path))

		return all(results)

	def _loadWinStateFromConfig(self): #TODO rename
		from ReNode.app.application import Application
		
		# stateStr:str = Config.get("winstate","internal")
		# winposStr:str = Config.get("winpos","internal")
		# if stateStr:
		# 	#convert from str to bytes
		# 	stateBytes = QByteArray(eval(stateStr))
		# 	winposBytes = QByteArray(eval(winposStr))

		# 	if not self.mainWindow.restoreGeometry(winposBytes):
		# 		Application.refObject.logger.error("Failed to restore window position")
		# 	else:
		# 		Application.refObject.logger.info("Loaded windows geometry")
		# 	if not self.mainWindow.restoreState(stateBytes):
		# 		Application.refObject.logger.error("Failed to restore window state")
		# 	else:
		# 		Application.refObject.logger.info("Loaded windows state")
		
		ng = self
		dictDocks = {
			"main":ng.mainWindow,
			# "inspector":ng.inspector,
			# "variable_manager":ng.variable_manager,
			# "logger":ng.log_dock,
			# "history":ng.undoView_dock,
		}
		for k,v in dictDocks.items():
			Config.logger.debug("Loading widget " + k)
			geo = Config.vSettings.value("geometry_"+k)
			if geo:
				if v.restoreGeometry(geo):
					Config.logger.info("Loaded geometry for " + k)
					if k == 'main' and v.isMaximized():
						v.setGeometry(Application.refObject.appInstance.desktop().availableGeometry())
				else:
					Config.logger.error("Failed to load geometry for " + k)
			
			state = Config.vSettings.value("state_"+k)
			if state:
				if hasattr(v,"saveState"):
					if v.restoreState(state):
						Config.logger.info("Loaded state for " + k)
					else:
						Config.logger.error("Failed to load state for " + k)

		
		# load opened sessions
		sessions = Config.get_str("opened_sessions","internal")
		if sessions:
			self.sessionManager.loadSessionPathes(sessions)

	#region Subcomponents getter
	def getGraphSystem(self) -> NodeGraph:
		"""Get NodeGraph API object"""
		return self.graph
	def getFactory(self) -> NodeFactory:
		"""Get NodeFactory object"""
		return self.nodeFactory #self.graph._factoryRef
	def getTabSearch(self) -> TabSearchMenu:
		"""Get TabSearchMenu object"""
		return self.graph._viewer._tabSearch
	#endregion

	def update(self,optNode = None):
		if optNode:
			optNode.update()
			return
		for node in self.graph.graph.all_nodes():
			node.update()

	def getNodeById(self,id):
		return self.graph.get_node_by_id(id)

	def registerNodes(self):
		self.graph.register_node(RuntimeNode)
		self.graph.register_node(RuntimeGroup)
		pass

	def setHistoryCollectLock(self,state: bool):
		self.graph.undo_view.blockSignals(state)
	
	def showHistory(self):
		self.graph.undo_view.show()
	
	def hideHistory(self):
		self.graph.undo_view.hide()

	def _addEvents(self):
		# wire function to "node_double_clicked" signal.
		self.graph.node_double_clicked.connect(self.onNodeDoubleClickedEvent)
		
		# Эти события не вызываются при откате истории
		#self.graph.port_connected.connect(self.onPortConnectedEvent)
		#self.graph.port_disconnected.connect(self.onPortDisconnectedEvent)

		#!only for debug
		"""properties_bin = PropertiesBinWidget(node_graph=self.graph)
		properties_bin.setWindowFlags(QtCore.Qt.Tool)
		# example show the node properties bin widget when a node is double clicked.
		def display_properties_bin(node):
			if not properties_bin.isVisible():
				properties_bin.show()
		# wire function to "node_double_clicked" signal.
		self.graph.node_double_clicked.connect(display_properties_bin)"""

	def onPortConnectedEvent(self,port_in : Port,port_out : Port):
		#? port_in.model.node < for get node
		in_node : RuntimeNode = port_in.model.node
		out_node : RuntimeNode = port_out.model.node

		custom_node = None 
		source_port = None #куда подключаемся. Должен быть пустым портом для успеха
		dest_port = None 
		if in_node.has_property("autoportdata"): 
			custom_node = in_node
			dest_port = port_in
			source_port = port_out
			if custom_node and dest_port.view.port_typeName == "" and len(custom_node.get_property("autoportdata")) == 0:
				custom_node.onAutoPortConnected(source_port)
		if out_node.has_property("autoportdata"): 
			custom_node = out_node
			dest_port = port_out
			source_port = port_in
			if custom_node and dest_port.view.port_typeName == "" and len(custom_node.get_property("autoportdata")) == 0:
				custom_node.onAutoPortConnected(source_port)
			pass
		
		if port_out.view.port_type == 'in':
			outernode = out_node
			outerport = port_out
			innerport = port_in
		else:
			outernode = in_node
			outerport = port_in
			innerport = port_out
		
		if outernode.has_property(outerport.name()):
			odat = outernode.getFactoryData()['options'].get(outerport.name(),{})
			if "typeset_out" in odat:
				outernode.set_property(outerport.name(),odat.get('default',"object"))
		
		if 'operators.call_lambda' in outernode.nodeClass and outerport.view.port_typeName == "function_ref" and \
			innerport.view.port_typeName.startswith("function[") and len(outernode.inputs()) == len(outernode.getFactoryData().get('inputs',[])):
				self.onFunctionRefPorts(outernode,innerport.view.port_typeName)

		pass

	def onPortDisconnectedEvent(self,port_in : Port,port_out : Port):
		in_node : RuntimeNode = port_in.model.node
		out_node : RuntimeNode = port_out.model.node

		custom_node = None 
		source_port = None #куда подключаемся. Должен быть пустым портом для успеха
		dest_port = None 
		if in_node.has_property("autoportdata"): 
			custom_node = in_node
			dest_port = port_in
			source_port = port_out
			if custom_node and len(custom_node.get_property("autoportdata")) > 0:
				custom_node.onAutoPortDisconnected(source_port)
		if out_node.has_property("autoportdata"): 
			custom_node = out_node
			dest_port = port_out
			source_port = port_in
			if custom_node and len(custom_node.get_property("autoportdata")) > 0:
				custom_node.onAutoPortDisconnected(source_port)
			pass
		
		if port_out.view.port_type == 'in':
			outernode = out_node
			outerport = port_out
			innerport = port_in
		else:
			outernode = in_node
			outerport = port_in
			innerport = port_out
		
		if 'operators.call_lambda' in outernode.nodeClass and outerport.view.port_typeName == "function_ref" and \
			innerport.view.port_typeName.startswith("function[") and len(outernode.inputs()) > len(outernode.getFactoryData().get('inputs',[])):
				self.onFunctionRefPorts(outernode,"",True)


	def onNodeDoubleClickedEvent(self,node : BaseNode):
		print("NODE DOUBLECLICK EVENT:"+node.type_)
		if "RuntimeGroup" in node.type_:
			print("expand")
			#node.expand()
		pass
	
	def contextMenuLoad(self):
		gmenu : NodeGraphMenu = self.graph.get_context_menu("graph")
		nmenu : NodesMenu = self.graph.get_context_menu("nodes")
		ctxmenu : ContextMenu = self.graph.get_context_menu("context")

		# def test_func(graph, node):
		# 	print('Clicked on node: {}'.format(node.name()))
		# nmenu.add_menu("TEST NODE MENU")
		# nmenu.add_command("testcmd",func=test_func,node_type='all') #,node_type='operators.if_branch'
		
		nmenu.add_command("Изменить цвет",func=change_color,node_type='internal.backdrop|internal.sticker')
		self.registerSwitchOnContext(nmenu)
		self.registerLambdaContext(nmenu)
		
		nmenu.add_command("Скопировать",func=copy_nodes,node_type="all")
		nmenu.add_command("Вырезать",func=cut_nodes,node_type="all")
		nmenu.add_command("Вставить",func=paste_nodes,node_type="all")
		nmenu.add_command("Удалить",func=delete_nodes,node_type="all")
		nmenu.add_command("Извлечь",func=extract_nodes,node_type="all")
		nmenu.add_command("Очистить подключения",func=clear_node_connections,node_type='all')
		nmenu.add_command("Сбросить все свойства",func=reset_all_node_props,node_type='all')
		nmenu.add_separator()
		nmenu.add_command("Снять выделение",func=clear_node_selection,node_type='all')

		def tsc__(graph: NodeGraph):
			#pos = QtGui.QCursor.pos()
			#print([(w.underMouse(),w) for w in self.widgets_at(pos)])
			graph.toggle_node_search(True,self.nodeFactory)
		gmenu.add_command("Библиотека узлов",tsc__,"Tab")
		# gmenu.add_command("showhistory",self.showHistory)
		# gmenu.add_separator()
		#gmenu.add_menu("Файл")
		scm = gmenu.add_menu("Сцена")
		scm.add_command("Назад",func=undo,shortcut="Ctrl+Z")
		scm.add_command("Повторить",func=redo,shortcut="Ctrl+Y")
		scm.add_command("Выбрать все",func=select_all_nodes,shortcut="Ctrl+A")
		scm.add_command("Снять выделение",func=clear_node_selection,shortcut=None)
		scm.add_command("Инвертировать выделение",func=invert_node_selection,shortcut=None)
		scm.add_separator()
		scm.add_command("Скопировать",func=copy_nodes,shortcut="Ctrl+C")
		scm.add_command("Вырезать",func=cut_nodes,shortcut="Ctrl+X")
		scm.add_command("Вставить",func=paste_nodes,shortcut="Ctrl+V")
		scm.add_command("Удалить",func=delete_nodes,shortcut="Del")
		scm.add_command("Извлечь",func=extract_nodes)
		scm.add_command("Очистить подключения",func=clear_node_connections)
		scm.add_command("Сбросить все свойства",func=reset_all_node_props)


		# ------------ context menu ------------
		def __coyvar(actType,ctxDataMap,graph):
			print(f'{actType}:{ctxDataMap}; {graph}')

		def __createVar__(actType,ctxDataMap,graph):
			if not actType == "addVariable": return
			idvar = ctxDataMap["id"]
			pos = ctxDataMap['pos']
			type = ctxDataMap['actionCtx']
			self.createVariableIntoScene(type,idvar,pos)
		
		def __canViewActionVar__(ctxDataMap,checkvalue):
			idvar = ctxDataMap['id']
			catobj = self.variable_manager.getVariableCategoryById(idvar)
			if not catobj: return False
			return catobj.endswith(checkvalue)

		def __cavViewFunctionDefActionVar__(ctxDataMap,checkvalue):
			# определение будет видно только если в графе ещё нет определения этой функции
			idvar = ctxDataMap['id']
			# allFuncs = self.graph.get_nodes_by_class("function.def")
			# for node in allFuncs:
			# 	if node.get_property("nameid") == idvar:
			# 		return False
			# new logic
			catObj = self.variable_manager.getVariableCategoryById(idvar,retObject=True)
			if catObj:
				varData = self.variable_manager.getVariableDataById(idvar)
				if varData:
					catObjInstancer = catObj.instancer
					infoData = self.inspector.infoData
					instancerType = "deffunc"
					typename = catObjInstancer.getVariableInstancerClassName(instancerType,infoData,varData)
					if typename and len(self.graph.get_nodes_by_class(typename)) > 0:
						return False
		
			catobj = self.variable_manager.getVariableCategoryById(idvar)
			if not catobj: return False
			return catobj.endswith(checkvalue)

		cmd = ctxmenu.add_command("Получить \"{}\"",actionContext="getvar",func=__createVar__,actionKind="addVariable",condition=lambda ctxDataMap:__canViewActionVar__(ctxDataMap,"var"))
		cmd.set_icon("data\\icons\\FIB_VarGet.png")
		cmd = ctxmenu.add_command("Установить \"{}\"",actionContext='setvar',func=__createVar__,actionKind="addVariable",condition=lambda ctxDataMap:__canViewActionVar__(ctxDataMap,"var"))
		cmd.set_icon("data\\icons\\FIB_VarSet.png")
		cmd = ctxmenu.add_command("Определение \"{}\"",actionContext='deffunc',func=__createVar__,actionKind="addVariable",condition=lambda ctxDataMap:__cavViewFunctionDefActionVar__(ctxDataMap,"func"))
		cmd.set_icon("data\\icons\\icon_Blueprint_OverrideFunction_16x.png")
		cmd = ctxmenu.add_command("Вызвать \"{}\"",actionContext='callfunc',func=__createVar__,actionKind="addVariable",condition=lambda ctxDataMap:__canViewActionVar__(ctxDataMap,"func"))
		cmd.set_icon("data\\icons\\icon_BluePrintEditor_Function_16px.png")

		
		cmd = ctxmenu.add_command("TEST",func=__coyvar,actionKind="unk")
		

		pass
	
	def toggleNodeSearch(self):
		self.graph.toggle_node_search(False,self.nodeFactory)

	def onMouseClicked(self,posx,posy):
		print(f">>>>>>>>{self} {posx} {posy}")
		pass

	#debug func
	def widgets_at(self,pos):
		"""Return ALL widgets at `pos`

		Arguments:
			pos (QPoint): Position at which to get widgets

		"""

		widgets = []
		widget_at = QApplication.instance().widgetAt(pos)

		while widget_at:
			widgets.append(widget_at)

			# Make widget invisible to further enquiries
			widget_at.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
			widget_at = QApplication.instance().widgetAt(pos)

		# Restore attribute
		for widget in widgets:
			widget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)

		return widgets

	def generateTreeDict(self):
		tabSearch = self.getTabSearch()
		tabSearch.generate_treeDict()
		tabSearch.tree.clear()
		tabSearch._existsTrees.clear()
		tabSearch.build_tree(tabSearch.dictTreeGen)
		tabSearch.tree.sortItems(0,Qt.SortOrder.AscendingOrder)

	
	def _generateSearchTreeDict(self):
		"""Generator for search tree"""
		test = {}
		for key,val in self.getFactory().nodes.items():
			if not val.get('visible',True): continue
			path = val.get('path', '')
			if path in test:
				test[path].append(key)
			else:
				test[path] = [key]
		return OrderedDict(sorted(test.items()))


	def _initVariableManager(self):
		variable_manager = VariableManager(nodeSystem=self)
		self.variable_manager = variable_manager
		#dock.setWidget(self.mainWindow)
		#dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea | Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
		#variable_manager.setFeatures(QDockWidget.NoDockWidgetFeatures)
		#variable_manager.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		variable_manager.setObjectName("VariableManager")
		self.mainWindow.addDockWidget(QtCore.Qt.RightDockWidgetArea, variable_manager)
		#graph.set_pipe_slicing(True) #enabled by default

		pass

	def _initInspector(self):
		from ReNode.ui.PropertyInspector import Inspector
		self.inspector = Inspector(self)
		self.inspector.setObjectName("PropertyInspector")
		self.mainWindow.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.inspector)

	def _initLoggerDock(self):
		from ReNode.ui.LoggerConsole import LoggerConsole
		from ReNode.app.Logger import registerConsoleLoggers

		self.log_dock = LoggerConsole()

		#self.log_dock.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
		#self.log_dock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
		#self.log_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
		#upperDrag = QWidget()
		#self.log_dock.setTitleBarWidget(QWidget())
		#self.log_dock.titleBarWidget().setFixedHeight(3)
		#self.log_dock.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
		#self.log_dock.setMinimumHeight(1)
		self.log_dock.setObjectName("LoggerConsole")
		self.mainWindow.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.log_dock)
		registerConsoleLoggers(self.log_dock)

	def _initHistoryDock(self):
		self.undoView_dock = QDockWidget("История")

		self.undoView_dock.setObjectName("HistoryDock")
		self.mainWindow.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.undoView_dock)

	def createVariableIntoScene(self,instanceType,varid,pos):
		"""
			Создание переменной в графе
			instancerType - getvar,setvar,deffunc,callfunc
		"""
		from ReNode.app.application import Application
		from ReNode.ui.VarMgrWidgetTypes.Widgets import VarMgrBaseWidgetType
		catObj = self.variable_manager.getVariableCategoryById(varid,retObject=True)
		if not catObj:
			Application.refObject.logger.error(f'Cannot find variable category for \'{varid}\'')
			return
		varData = self.variable_manager.getVariableDataById(varid)
		if not varData:
			Application.refObject.logger.error(f'Cannot find variable data for \'{varid}\'')
			return
		catObjInstancer:VarMgrBaseWidgetType = catObj.instancer
		infoData = self.inspector.infoData
		typename = catObjInstancer.getVariableInstancerClassName(instanceType,infoData,varData)
		if not typename:
			Application.refObject.logger.error(f'Cannot find variable instancer for \'{instanceType}\'')
			return
		
		self.graph.undo_stack().beginMacro(f"Создание переменной {typename}")

		nodeObj = self.nodeFactory.instance(typename,self.graph,pos)

		if catObjInstancer.canUpdateNode:
			self.graph.undo_view.blockSignals(True)
			self.variable_manager._updateNode(nodeObj,varid,instanceType,catObjInstancer)
			self.graph.undo_view.blockSignals(False)

		self.graph.undo_stack().endMacro()
		pass

	def _initTabs(self,dock):
		from ReNode.ui.SessionManager import SessionManager
		tab_widget = SessionManager(self)
		self.sessionManager = tab_widget
		dock.setTitleBarWidget(tab_widget)

	def update_lambda_porttype(self,node,reloadNames=False,onlySync=False):
		"""Генерирует выходные порты и синхронизирует их типы"""
		port = node.outputs().get('lambda_ref')
		if not port: return
		ptp = port.view.port_typeName
		if not self.getFactory().isFuncSignType(ptp): return
		oldSIG = self.getFactory().parseFunctionSign(ptp)
		if len(oldSIG) < 2: return
		signature = f'function[{oldSIG[0]}={oldSIG[1]}'
		parameters = []
		parametersPacked = []
		toDel = []

		hasCallerPort = NodeLambdaType.hasObjectCallerPort(node.nodeClass)
		if hasCallerPort:
			p = node.outputs().get('Цель')
			if p and p.view.port_typeName:
				__tobjcall = p.view.port_typeName
			else:
				__tobjcall = "object^"
			parametersPacked.append(__tobjcall)

		canCollect = False
		for ix, (p,v) in enumerate(node.outputs().items()):
			if p.startswith("Параметр") and not canCollect:
				canCollect = True
			if not canCollect: continue

			pn = v.view.port_typeName
			parameters.append(pn)
			parametersPacked.append(pn.replace("[","(").replace("]",")"))
			if not onlySync:
				toDel.append(v)
		if parametersPacked:
			signature += "="+ "@".join(parametersPacked)
		signature += "]"
		port.view.setPortTypeName(signature)

		if onlySync: return

		if reloadNames:
			for pdl in toDel:
				node.delete_output(pdl)
			for i,pnew in enumerate(parameters):

				node.add_output(f'Параметр {i+1}',
					color=self.getFactory().getColorByType(pnew,False),
					display_name=True,
					multi_output=True,
					painter_func=None,
					portType=pnew
				)
		
		ccp = port.connected_ports()
		if ccp:
			for prtT in ccp:
				if "operators.call_lambda" in prtT.node().nodeClass:
					self.onFunctionRefPorts(prtT.node(),signature)
				else:
					if not port.view.validate_connection_to(prtT.view):
						port.disconnect_from(prtT,False) #donot push undo
		#if hasport target
		targ = node.outputs().get('Цель')
		if targ and targ.connected_ports():
			for prtT in targ.connected_ports():
				if not targ.view.validate_connection_to(prtT.view):
					targ.disconnect_from(prtT,False) #donot push undo

	def registerSwitchOnContext(self,nmenu:NodesMenu):
		nodeTypes = "operators.switch_on_int|operators.switch_on_float|operators.switch_on_string"
		def __add_value(graph,node:RuntimeNode):
			nClass = node.nodeClass
			globPos = QCursor.pos()
			m = QMenu()
			layout = QVBoxLayout()
			layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
			m.setLayout(layout)
			dlg = QtWidgets.QInputDialog()
			if nClass.endswith("int"):
				dlg.setIntValue(0)
				dlg.setIntRange(-999999,999999)
			elif nClass.endswith("float"):
				dlg.setDoubleRange(-999999,999999)
				dlg.setDoubleDecimals(6)
				dlg.setDoubleValue(0)
				dlg.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
			elif nClass.endswith("string"):
				dlg.setTextValue("")
				dlg.setOption(QtWidgets.QInputDialog.InputDialogOption.UsePlainTextEditForTextInput,True)
			m.layout().addWidget(dlg)
			dlg.setOkButtonText("Добавить")
			def __finalizeSelector():
				if dlg.result() == QtWidgets.QInputDialog.Accepted:
					val = None
					if nClass.endswith("int"):
						val = dlg.intValue()
					elif nClass.endswith("float"):
						val = dlg.doubleValue()
					elif nClass.endswith("string"):
						val = dlg.textValue().replace("\n","\\n").replace("\t","\\t")
					self.addNodeForSwitch(node,val)
				m.close()
			dlg.finished.connect(__finalizeSelector)
			m.exec_(globPos)
		
		def __remove_value(graph,node:RuntimeNode):
			from ReNode.ui.SearchMenuWidget import SearchComboButton,CustomMenu,createTreeDataContent,addTreeContent
			nClass = node.nodeClass
			menu = CustomMenu(parent=self,isRuntime=True)
			treeContent = createTreeDataContent()
			canCollect = False
			val = "Exec"
			if nClass.endswith("int"):
				val = "int"
			elif nClass.endswith("float"):
				val = "float"
			elif nClass.endswith("string"):
				val = "string"
			icnRef = self.variable_manager.getIconFromTypename(val)
			for i, (p,v) in enumerate(node.outputs().items()):
				if i == 0: continue
				addTreeContent(treeContent,p,p,icnRef)
			menu.tree.populate_tree(treeContent)

			def _prov(data,text,icn):
				node.delete_output(data)
				node.view.draw_node()
			menu.addOnClickEvent(_prov)

			menu.exec_(QCursor.pos())

		nmenu.add_command("Добавить значение",__add_value,node_type=nodeTypes)
		nmenu.add_command("Удалить значение",__remove_value,node_type=nodeTypes)
		pass
	def addNodeForSwitch(self,node:RuntimeNode,value):
		if value == None: return
		valname = '{}'.format(value)
		if node.get_output(valname):
			self.mainWindow.loggerRef.warn(f"Невозможно добавить \"{valname}\", так как указанное значение уже существует")
			return
		from ReNode.ui.NodePainter import draw_triangle_port
		node.add_output(
			name=valname,
			color=self.getFactory().execColor,
			display_name=True,
			multi_output=False,
			painter_func=draw_triangle_port,
			portType="Exec"
		)
		node.view.draw_node()

	def registerLambdaContext(self,nmenu:NodesMenu):
		from ReNode.ui.SearchMenuWidget import SearchComboButton,CustomMenu,createTreeDataContent,addTreeContent

		def __type_eval_add_lam(node,proc):
			globPos = QCursor.pos()
			#pos = self.sessionManager.mapFromGlobal(globPos)
			menu = CustomMenu(parent=self,isRuntime=True)
			treeContent = self.variable_manager.getAllTypesTreeContent()
			menu.tree.populate_tree(treeContent)
			def _prov(data,text,icn):
				#print(f'Clicked on {data} ({text})')

				data = self.getFactory().getBinaryType(data) #add postfix if need
				data = proc.format(data) #formatting

				idx = len([k for k in node.outputs().keys() if k.startswith('Параметр')])+1
				node.add_output(
					name='Параметр {}'.format(idx),
					color=self.getFactory().getColorByType(data,False),
					display_name=True,
					multi_output=True,
					painter_func=None,
					portType=data
				)
				self.update_lambda_porttype(node)
				node.view.draw_node()
			menu.addOnClickEvent(_prov)
			menu.exec_(globPos)

		#def _add_lambda_port(graph,node):
		#	__type_eval_add_lam(node)
		lport__ = "operators.lambda|operators.lambda_obj|operators.lambda_event|operators.lambda_eventlist"
		lport_setreturn__ = "operators.lambda|operators.lambda_obj|operators.lambda_event"
		lport_setobject__ = "operators.lambda_event|operators.lambda_eventlist"

		nmenu.add_command("Добавить порт",func=lambda gr,nod:__type_eval_add_lam(nod,"{}"),node_type=lport__)
		nmenu.add_command("Добавить порт (массив)",func=lambda gr,nod:__type_eval_add_lam(nod,"array[{}]"),node_type=lport__)
		nmenu.add_command("Добавить порт (сет)",func=lambda gr,nod:__type_eval_add_lam(nod,"set[{}]"),node_type=lport__)

		def _remove_lambda_port(graph,node:RuntimeNode):
			menu = CustomMenu(parent=self,isRuntime=True)
			treeContent = createTreeDataContent()
			canCollect = False
			for i, (p,v) in enumerate(node.outputs().items()):
				if p.startswith("Параметр") and not canCollect:
					canCollect = True
				if not canCollect: continue
				ftn = v.view.port_typeName
				addTreeContent(treeContent,p,p + f': {self.variable_manager.getTextTypename(ftn)}',
				self.variable_manager.getIconFromTypename(ftn))
			menu.tree.populate_tree(treeContent)

			def _prov(data,text,icn):
				node.delete_output(data)
				self.update_lambda_porttype(node,reloadNames=True)
				node.view.draw_node()
			menu.addOnClickEvent(_prov)

			menu.exec_(QCursor.pos())
		nmenu.add_command("Удалить порт",func=_remove_lambda_port,node_type=lport__)

		def _retval(graph,node):
			globPos = QCursor.pos()
			menu = CustomMenu(parent=self,isRuntime=True)
			treeContent = self.variable_manager.getAllTypesTreeContent()
			addTreeContent(treeContent,"null","Без возврата",QIcon(),0)
			menu.tree.populate_tree(treeContent)
			def _prov(data,text,icn):
				port = node.outputs().get('lambda_ref')
				if not port: return
				oldTPN = port.view.port_typeName
				ptp = self.getFactory().getBinaryType(data)
				newType = self.getFactory().updateFunctionSignature(oldTPN,1,ptp)
				port.view.setPortTypeName(newType,True)
				self.update_lambda_porttype(node)
				node.view.draw_node()
			menu.addOnClickEvent(_prov)
			menu.exec_(globPos)
		nmenu.add_command("Возвращаемое значение",func=_retval,node_type=lport_setreturn__)


		def _setobj(graph,node):
			from ReNode.ui.SearchMenuWidget import createTreeDataContent,addTreeContentItem
			globPos = QCursor.pos()
			menu = CustomMenu(parent=self,isRuntime=True)
			treeContent = createTreeDataContent()
			for objTree in self.getFactory().getClassAllChildsTree("object")['childs']:
				addTreeContentItem(treeContent,objTree)
			menu.tree.populate_tree(treeContent)
			def _prov(data,text,icn):
				port = node.outputs().get('Цель')
				if not port: return
				oldTPN = port.view.port_typeName
				# pts = oldTPN.split("=")
				# if len(pts)>=2:
				# 	pts[1]=data
				newType = data + "^"
				port.view.setPortTypeName(newType)
				self.update_lambda_porttype(node)
				node.view.draw_node()
			menu.addOnClickEvent(_prov)
			menu.exec_(globPos)
		nmenu.add_command("Установить тип объекта",func=_setobj,node_type=lport_setobject__)

	def onFunctionRefPorts(self,node:RuntimeNode,signature:str='function[anon=null]',isDeleteAction=False):
		"""Синхронизирует порты и их типы по сигнатуре для вызывающей функции"""
		if not signature: signature = 'function[anon=null]'
		sparts = self.getFactory().parseFunctionSign(signature)
		
		#if isDeleteAction:
		#	sign = 'anon=null'
		logicType = sparts[0]
		ftyperet = sparts[1]
		fparams = sparts[2]

		outp = node.outputs().get('Результат')
		if isDeleteAction:
			if outp: node.delete_output(outp)
		else:
			if outp:
				if ftyperet=='null':
					node.delete_output(outp)
				else:
					outp.view.setPortTypeName(ftyperet,True)
			else:
				if ftyperet!='null':
					node.add_output('Результат',
						color=self.getFactory().getColorByType(ftyperet,False),
						display_name=True,
						multi_output=True,
						painter_func=None,
						portType=ftyperet)

		paramTypes = []
		if fparams:
			for p in fparams:
				paramTypes.append(p.replace("(","[").replace(")","]"))
		lenInputsDefault = len(node.getFactoryData().get('inputs',[]))
		for idx, (k,v) in enumerate(node.inputs().items()):
			if (idx<=(lenInputsDefault-1)): continue

			node.delete_input(v)
		
		if not isDeleteAction:
			for i,p in enumerate(paramTypes):
				node.add_input('Параметр {}'.format(i+1),
					color=self.getFactory().getColorByType(p,False),
					display_name=True,
					multi_input=True,
					painter_func=None,
					portType=p
				)
