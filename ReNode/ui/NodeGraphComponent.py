import uuid
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *

from NodeGraphQt import NodeGraph
from NodeGraphQt.custom_widgets.properties_bin.node_property_widgets import PropertiesBinWidget
from NodeGraphQt.qgraphics.node_base import NodeItem
from ReNode.ui.Nodes import RuntimeNode

from NodeGraphQt.nodes.base_node import *

class NodeGraphComponent:
	def __init__(self,mainWindow) -> None:
		graph = NodeGraph()
		self.graphSystem = graph
		
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
		node.set_name("<b>Жирно</b> <i>наклон</i> и <font size=""20"">всё</font><br/><br/><br/><br/>nextline!")
		wd : NodeCheckBox = node.get_widget("cb")
		# add event on checked changed
		def on_value_changed(self, *args, **kwargs):
			if args[0]:
				node.add_output('out' + str(uuid.uuid4().hex),False,False)
			print(f"wid:{self} -> CHANGE: {args} AND:{kwargs}")
			pass
		wd.value_changed.connect(on_value_changed)
		graph.clear_selection()
		graph.fit_to_selection()
		#properties_bin = PropertiesBinWidget(node_graph=graph)
		#properties_bin.setWindowFlags(QtCore.Qt.Tool)
		self.update(node)
		
	
	def getGraphSystem(self) -> NodeGraph:
		return self.graphSystem

	def update(self,optNode = None):
		if optNode:
			optNode.update()
			return
		for node in self.graphSystem.graph.all_nodes():
			node.update()

	def registerNodes(self):
		self.graphSystem.register_node(RuntimeNode)
		pass