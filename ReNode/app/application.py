import sys

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication
from ReNode.app.VERSION import global_version
from ReNode.app.REVISION import global_revision
from ReNode.ui.AppWindow import MainWindow
from NodeGraphQt import NodeGraph, BaseNode

class Application:
	
	appName = "ReNodes"
	appVersion = (global_version[0],global_version[1])
	appRevision = global_revision

	# string representation of version
	def getVersionString():
		return f"{Application.appVersion[0]}.{Application.appVersion[1]}.{Application.appRevision}"

	#construct
	def __init__(self):

		self.mainWindow = MainWindow()
		self.mainWindow.setWindowTitle(f"{Application.appName} (v.{Application.getVersionString()})")
		self.mainWindow.show()
		self.mainWindow.showMaximized()

'''class NodeGraphPanel(QtWidgets.QDockWidget):
    """
    Widget wrapper for the node graph that can be docked to
    the main window.
    """

    def __init__(self, graph, parent=None):
        super(NodeGraphPanel, self).__init__(parent)
        self.setObjectName('nodeGraphQt.NodeGraphPanel')
        self.setWindowTitle('Редактор логики')
        self.setWidget(graph.widget)

class FooNode(BaseNode):

    # unique node identifier domain.
    __identifier__ = 'testident'

    # initial default node name.
    NODE_NAME = 'Foo Node'

    def __init__(self):
        super(FooNode, self).__init__()

        # create an input port.
        self.add_input('in', color=(180, 80, 0))

        # create an output port.
        self.add_output('out')'''

def AppMain():
	print(f"Loading {Application.appName} (version {Application.getVersionString()})")

	app = QApplication(sys.argv)
	QApplication.setStyle( "Fusion" )
	application = Application() 
        
	"""graph = NodeGraph()
	graph.show()

	graph.register_node(FooNode)
	#create random 50 nodes 
	for i in range(50):
		#random colo
		graph.create_node('testident.FooNode', name='Узел ' + str(i))
	sfx_graph_panel = NodeGraphPanel(graph)
	application.mainWindow.addDockWidget(QtCore.Qt.TopDockWidgetArea,sfx_graph_panel)"""

	# при обновлении файла стиля вызывает метод onReloadStyle
	# filewatcher
	fs_watcher = QtCore.QFileSystemWatcher()
	fs_watcher.addPath("./data/qss/default.qss")
	#print fws files
	fs_watcher.fileChanged.connect(application.mainWindow.onReloadStyle)

	print("Application loaded. Start main loop")
	sys.exit(app.exec_())