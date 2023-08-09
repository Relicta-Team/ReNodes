from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *

from NodeGraphQt import NodeGraph



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
	
	def GetGraphSystem(self) -> NodeGraph:
		return self.graphSystem