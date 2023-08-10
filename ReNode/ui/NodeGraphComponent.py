import uuid
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *

from NodeGraphQt import (NodeGraph, GroupNode)
from NodeGraphQt.custom_widgets.properties_bin.node_property_widgets import PropertiesBinWidget
from NodeGraphQt.qgraphics.node_base import NodeItem
from NodeGraphQt.widgets.viewer import NodeViewer
from ReNode.ui.Nodes import RuntimeNode, RuntimeGroup
from ReNode.app.utils import *

from NodeGraphQt.nodes.base_node import *

class NodeGraphComponent:
	def __init__(self,mainWindow) -> None:
		graph = NodeGraph()
		self.graph = graph
		
		dock = QDockWidget("Editor main")
		dock.setWidget(graph.widget)
		#dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea | Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
		dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
		#dock.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		mainWindow.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
		#graph.set_pipe_slicing(True) #enabled by default
		
		dock.setWindowTitle("Editortab")#upper title
		
		#testing tabs system
		"""graph.widget.tabBar().addTab("testvalue")
		tabbar = graph.widget.tabBar()
		tabbar.setWindowTitle("titletest")
		tabbar.setTabsClosable(True)
		tabbar.removeTab(0)"""

		# add 20 tabs
		#for i in range(1,20):
		#	graph.widget.tabBar().addTab("testvalue")

		graph.show()
		self._addEvents()
		self.registerNodes()

		node : RuntimeNode = graph.create_node('runtime_domain.RuntimeNode')
		node.add_input('in', color=(0, 80, 0))
		node.add_output('out',False,False)
		node.add_text_input('text1',"testlable",'default',"displaytab")
		node.add_text_input('text2',"testlable")
		node.add_text_input('text3',"testlable")
		node.add_checkbox("cb",text="this is value a testing data")
		node.add_combo_menu("cm","combo",["фыфыфыфы","ЙЙЙЙ ","СЕСЕСЕС"])
		
		
		node.set_icon("data\\function_sim.png")
		node.set_property("name","<b>Действие</b><br/><font size=""4""><i>Дополнительные данные</i></font>",False)
		wd : NodeCheckBox = node.get_widget("cb")
		# add event on checked changed
		def on_value_changed(self, *args, **kwargs):
			if args[0]:
				node.add_output('out' + str(uuid.uuid4().hex),False,False)
			print(f"wid:{self} -> CHANGE: {args} AND:{kwargs}")
			pass
		wd.value_changed.connect(on_value_changed)
		
		def on_intchange(self, *args, **kwargs):
			val = args[0]
			intval = intTryParse(val)
			if str(intval)!=val:
				node.set_property(self,str("0"))
			pass

		node.get_widget("text1").value_changed.connect(on_intchange)

		graph.clear_selection()
		graph.fit_to_selection()
		#properties_bin = PropertiesBinWidget(node_graph=graph)
		#properties_bin.setWindowFlags(QtCore.Qt.Tool)
		self.update(node)
		
		groupnode : GroupNode = graph.create_node("runtime_domain.RuntimeGroup")
		groupnode.set_name("TESTNAME <b>TEST</b>")
		groupnode.add_input("input")
		groupnode.add_output("ouput")
		groupnode.expand()
		sg = graph.sub_graphs

		graph.auto_layout_nodes()

		n_backdrop = graph.create_node('Backdrop')
		n_backdrop.wrap_nodes([groupnode, node])
	
	def getGraphSystem(self) -> NodeGraph:
		return self.graph

	def update(self,optNode = None):
		if optNode:
			optNode.update()
			return
		for node in self.graph.graph.all_nodes():
			node.update()

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
		
		#!only for debug
		"""properties_bin = PropertiesBinWidget(node_graph=self.graph)
		properties_bin.setWindowFlags(QtCore.Qt.Tool)
		# example show the node properties bin widget when a node is double clicked.
		def display_properties_bin(node):
			if not properties_bin.isVisible():
				properties_bin.show()
		# wire function to "node_double_clicked" signal.
		self.graph.node_double_clicked.connect(display_properties_bin)"""

	def onNodeDoubleClickedEvent(self,node : BaseNode):
		print(node.type_)
		if "RuntimeGroup" in node.type_:
			print("expand")
			node.expand()
		pass
	
	def onMouseClicked(self,posx,posy):
		print(f">>>>>>>>{self} {posx} {posy}")
		pass