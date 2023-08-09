import uuid
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *

from NodeGraphQt import NodeGraph
from NodeGraphQt.custom_widgets.properties_bin.node_property_widgets import PropertiesBinWidget
from NodeGraphQt.qgraphics.node_base import NodeItem
from ReNode.ui.Nodes import RuntimeNode
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
		node.set_property("name","<align=\"left\"><b>Действие</b><br/><font size=""4""><i>Дополнительные данные</i></font></align>",False)
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
		pass

	def setHistoryCollectLock(self,state: bool):
		self.graph.undo_view.blockSignals(state)
	
	def showHistory(self):
		self.graph.undo_view.show()
	
	def hideHistory(self):
		self.graph.undo_view.hide()