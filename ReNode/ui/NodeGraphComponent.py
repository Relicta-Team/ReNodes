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

from NodeGraphQt.nodes.base_node import *
from ReNode.ui.TabSearchMenu import TabSearchMenu

from ReNode.ui.VariableManager import VariableManager
from ReNode.app.config import Config

class NodeGraphComponent:

	refObject = None

	def __init__(self,mainWindow) -> None:
		from ReNode.ui.AppWindow import MainWindow
		from ReNode.ui.ScriptMaker import ScriptMakerManager

		# global reference to object instance		
		NodeGraphComponent.refObject = self

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
		
		from ReNode.app.application import Application
		if Application.isDebugMode():
			#self.graph.load_session(".\\session.json")
			# with  open(".\\templates_tests.txt",encoding='utf-8') as f:
			# 	QtWidgets.QApplication.clipboard().setText('\n'.join(f.readlines()))
			# self.variable_manager.loadVariables(self.graph.variables)
			# #todo load info
			# self.graph.infoData['classname'] = 'debug_session'
			# self.graph.paste_nodes()
			self.editorDock.setWidget(None)
		else:
			self.editorDock.setWidget(None)

	def _loadWinStateFromConfig(self): #TODO rename
		from ReNode.app.application import Application
		
		stateStr:str = Config.get("winstate","internal")
		winposStr:str = Config.get("winpos","internal")
		if stateStr:
			#convert from str to bytes
			stateBytes = QByteArray(eval(stateStr))
			winposBytes = QByteArray(eval(winposStr))

			if not self.mainWindow.restoreGeometry(winposBytes):
				Application.refObject.logger.error("Failed to restore window position")
			if not self.mainWindow.restoreState(stateBytes):
				Application.refObject.logger.error("Failed to restore window state")
			
		
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
		if out_node.has_property("autoportdata"): 
			custom_node = out_node
			dest_port = port_out
			source_port = port_in
		if custom_node and dest_port.view.port_typeName == "" and len(custom_node.get_property("autoportdata")) == 0:
			custom_node.onAutoPortConnected(source_port)
			pass

		
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
		if out_node.has_property("autoportdata"): 
			custom_node = out_node
			dest_port = port_out
			source_port = port_in
		if custom_node and len(custom_node.get_property("autoportdata")) > 0:
			custom_node.onAutoPortDisconnected(source_port)
			pass

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

		def test_func(graph, node):
			print('Clicked on node: {}'.format(node.name()))
		nmenu.add_menu("TEST NODE MENU")
		nmenu.add_command("testcmd",func=test_func,node_type='all') #,node_type='operators.if_branch'
		
		nmenu.add_command("Изменить цвет",func=change_color,node_type='nodeGraphQt.nodes.BackdropNode')
		
		nmenu.add_command("Скопировать",func=copy_nodes,node_type="all",shortcut="Ctrl+C")
		nmenu.add_command("Вырезать",func=cut_nodes,node_type="all",shortcut="Ctrl+X")
		nmenu.add_command("Вставить",func=paste_nodes,node_type="all",shortcut="Ctrl+V")
		nmenu.add_command("Удалить",func=delete_nodes,node_type="all",shortcut="Del")
		nmenu.add_command("Извлечь",func=extract_nodes,node_type="all")
		nmenu.add_command("Очистить подключения",func=clear_node_connections,node_type='all')
		nmenu.add_separator()
		nmenu.add_command("Снять выделение",func=clear_node_selection,node_type='all')

		def __debaddport(graph, node):
			import random
			rname = f"random name {random.randrange(1,100000)}"
			node.add_input(
				name=rname,
				color=None,
				display_name=True,
				multi_input=True,
				painter_func=None,
				portType=f'allof'
			)
		nmenu.add_command("DEBUG ADD PORT",func=__debaddport,node_type='all')
		def __debaddvalue(graph,node):
			import random
			rname = f"random name {random.randrange(1,100000)}"
			node.add_text_input(
				name=rname,
				label=rname,
				text=rname
			)
		nmenu.add_command("DEBUG ADD VALUE",func=__debaddvalue,node_type='all')

		def my_test(graph):
			ps = graph.viewer().scene_cursor_pos()
			pos = [ps.x(),ps.y()]
			self.nodeFactory.instance("operators.testnode",pos=pos,graphref=graph)
			"""node : RuntimeNode = graph.create_node('runtime_domain.RuntimeNode', pos=[ps.x(),ps.y()])
			node.add_input('Входные данные', color=(0, 80, 0))
			node.add_output('Выходные данные',False,False)
			node.add_text_input('text1',"testlable",'default',"displaytab")"""

			"""node.add_text_input('text2',"testlable")
			node.add_text_input('text3',"testlable")
			node.add_checkbox("cb",text="this is value a testing data")
			node.add_combo_menu("cm","combo",["фыфыфыфы","ЙЙЙЙ ","СЕСЕСЕС"])
			node.set_icon("data\\function_sim.png")
			node.set_property("name","<b>Действие</b><br/><font size=""4""><i>Дополнительные данные</i></font>",False)
			node.update()"""

			"""groupnode : GroupNode = graph.create_node("runtime_domain.RuntimeGroup")
			groupnode.add_input("input")
			groupnode.add_output("ouput")"""
		
		gmenu.add_command('Create testobj', my_test, 'Shift+t')
		def sertest__(graph):
			graph.save_session(".\\session.json")
			print("SERIALIZED")
		gmenu.add_command("serializetest",sertest__)
		def desertest__(graph):
			graph.load_session(".\\session.json")
			print("LOADED")
		gmenu.add_command("DESER",desertest__)
		def tsc__(graph: NodeGraph):
			#pos = QtGui.QCursor.pos()
			#print([(w.underMouse(),w) for w in self.widgets_at(pos)])
			graph.toggle_node_search(True,self.nodeFactory)
		gmenu.add_command("TOGGLESEARCH",tsc__,"Tab")
		gmenu.add_command("showhistory",self.showHistory)
		gmenu.add_separator()
		gmenu.add_menu("Файл")
		scm = gmenu.add_menu("Сцена")
		scm.add_command("Назад",func=undo,shortcut="Ctrl+Z")
		scm.add_command("Повторить",func=redo,shortcut="Ctrl+Y")
		scm.add_command("Выбрать все",func=select_all_nodes,shortcut="Ctrl+A")
		scm.add_command("Снять выделение",func=clear_node_selection,shortcut=None)
		scm.add_command("Инвертировать выделение",func=invert_node_selection,shortcut=None)

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
			allFuncs = self.graph.get_nodes_by_class("function.def")
			for node in allFuncs:
				if node.get_property("nameid") == idvar:
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
		variable_manager = VariableManager(actionVarViewer=self.mainWindow.switchVariableViewerAction,nodeSystem=self)
		self.variable_manager = variable_manager
		#dock.setWidget(self.mainWindow)
		#dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea | Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
		#variable_manager.setFeatures(QDockWidget.NoDockWidgetFeatures)
		#variable_manager.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		variable_manager.setObjectName("VariableManager")
		self.mainWindow.addDockWidget(QtCore.Qt.RightDockWidgetArea, variable_manager)
		#graph.set_pipe_slicing(True) #enabled by default

		self.getFactory().updateLibTypes()

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

	def addVariableToScene(self,getorset,varid,pos):
		nodeObj = self.nodeFactory.instance("variable."+getorset,self.graph,pos)
		self.graph.undo_view.blockSignals(True)
		self.variable_manager._updateNode(nodeObj,varid,getorset)
		self.graph.undo_view.blockSignals(False)
		pass

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
		catObjInstancer:VarMgrBaseWidgetType = catObj.instancer
		typename = catObjInstancer.getVariableInstancerClassName(instanceType)
		if not typename:
			Application.refObject.logger.error(f'Cannot find variable instancer for \'{instanceType}\'')
			return
		
		self.graph.undo_stack().beginMacro(f"Создание переменной {typename}")

		nodeObj = self.nodeFactory.instance(typename,self.graph,pos)
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