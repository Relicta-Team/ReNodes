import sys
import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication
from ReNode.app.VERSION import global_version
from ReNode.app.REVISION import global_revision
from ReNode.ui.AppWindow import MainWindow
from NodeGraphQt import NodeGraph, BaseNode
from ReNode.app.config import Config
from ReNode.app.Logger import *
from ReNode.app.NodeFactory import NodeFactory
import logging

class SplashScreenHandler(logging.Handler):
	def __init__(self, splash_screen, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.splash_screen : QtWidgets.QSplashScreen = splash_screen

	def emit(self, record):
		if self and self.splash_screen:
			message = self.format(record)
			self.splash_screen.showMessage(message, QtCore.Qt.AlignmentFlag.AlignBottom, QtCore.Qt.GlobalColor.white)
			QApplication.processEvents()

"""class CustomSplashScreen(QtWidgets.QSplashScreen):
	def __init__(self, pixmap,flags):
		super().__init__(pixmap,flags)
		self.gradient = QtGui.QLinearGradient(0, self.height() * 0.5, 0, self.height())
		self.gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
		self.gradient.setColorAt(1, QtGui.QColor(0, 0, 0, 255))

	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		painter.drawPixmap(0, 0, self.pixmap())
		painter.fillRect(0, int(self.height() * 0.5), self.width(), self.height(), self.gradient)
		super(CustomSplashScreen,self).paintEvent(event)"""

class Application:
	
	appName = "ReNodes"
	appVersion = (global_version[0],global_version[1])
	appRevision = global_revision

	# string representation of version
	def getVersionString():
		return f"{Application.appVersion[0]}.{Application.appVersion[1]}.{Application.appRevision}"

	#construct
	def __init__(self,args):
		
		pixmap = QtGui.QPixmap("data/splash.png").scaled(600, 400) #, QtCore.Qt.KeepAspectRatio
		#pixmap.fill(QtGui.QColor(0,0,0))
		splash = QtWidgets.QSplashScreen(pixmap,QtCore.Qt.WindowStaysOnTopHint)
		
		label = QtWidgets.QLabel(splash)
		label.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: white; padding: 5px;")
		label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
		label.setGeometry(0, pixmap.height() - 30, pixmap.width(), 30)
		label.setText(f'{self.appName} {Application.getVersionString()}')
		splashEnabled =  not "-nosplash" in args
		if splashEnabled: splash.show()

		handler = SplashScreenHandler(splash)
		formatter = logging.Formatter('%(levelname)s - %(message)s')
		handler.setFormatter(formatter)

		logger = logging.getLogger("main")
		logger.setLevel(logging.DEBUG)
		logger.addHandler(handler)

		#stdout handler
		stdout_hndl = logging.StreamHandler(sys.stdout)
		stdout_hndl.setFormatter(logging.Formatter('[%(name)s::%(levelname)s] - %(message)s'))
		logger.addHandler(stdout_hndl)

		logger.info(f"Start loading {self.appName}")
		# Test smooth 
		"""splash.show()
		opaqueness = 0.0
		splash.setWindowOpacity(opaqueness)
		step = 0.01
		while opaqueness < 1:
			splash.setWindowOpacity(opaqueness)
			time.sleep(step) # Gradually appears
			opaqueness+=step
		time.sleep(1) # hold image on screen for a while
		splash.close()"""
		Config.init()

		self.nodeFactory = NodeFactory()

		self.mainWindow = MainWindow(self.nodeFactory)
		self.mainWindow.setWindowTitle(f"{Application.appName} (v.{Application.getVersionString()})")
		
		if splashEnabled: time.sleep(3)
		splash.finish(self.mainWindow)
		logger.removeHandler(handler)
		

		self.mainWindow.show()
		self.mainWindow.showMaximized()


	#destructor
	def __del__(self):
		Config.saveConfig()
		pass

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
	global logger
	app = QApplication(sys.argv)
	QApplication.setStyle( "Fusion" )
	application = Application(sys.argv) 
	logger = RegisterLogger('main')
	logger.info(f"Loading {Application.appName} (version {Application.getVersionString()})")
		
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

	logger.info("Application loaded. Start main loop")
	sys.exit(app.exec_())