
import uuid
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtWidgets, QtCore, QtGui
from ReNode.app.utils import loadStylesheet
from ReNode.ui.Widgets import *
from ReNode.ui.NodeGraphComponent import *
from NodeGraphQt import NodeGraph
from ReNode.app.Logger import *

logger : logging.Logger = None

class MainWindow( QMainWindow ):

	def __init__( self, factory):
		super().__init__()
		global logger
		logger = RegisterLogger("main")
		self.nodeFactory = factory
		self.initUI()


	def initUI(self):
		self.setWindowTitle("Unnamed window")
		self.setWindowIcon(QtGui.QIcon('./data/pic.png'))
		
		#self.tabWidget = QTabWidget()
		#self.setCentralWidget(self.tabWidget)

		#style setup
		"""self.setStyleSheet('''
		    QMainWindow {
		     	border: 1px solid #ffffff; 
				background-color: #1F1F29; 
				color: #FAFAFF; 
				padding: 2px; 
				font-family: Arial, sans-serif; 
				font-size: 12px;
			}

		   	QMenuBar::item:selected {
				background-color: #ff0000;
				color: #ffffff;
			}
		    ''')"""
		self.setStyleSheet(loadStylesheet("./data/qss/default.qss"))
		#self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		# maybee need custom winframe??

		#setwindows size at screensize
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		
		
		self.createMenu()
		self.createStatusBar()

		self.mdiArea = QMdiArea()
		self.mdiArea.setBackground(QtGui.QColor(0, 0, 0, 0))
		self.mdiArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.mdiArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.mdiArea.setViewMode(QMdiArea.TabbedView)
		self.mdiArea.setDocumentMode(True)
		self.mdiArea.setTabsClosable(True)
		self.mdiArea.setTabsMovable(True)
		#self.setCentralWidget(self.mdiArea)

		self.createInspectorDock()
		self.createWindowGraphEditor()
	
	def createMenu(self):
		self.newAction = QAction('&Новый скрипт', self, triggered=self.onNewFile, shortcut="Ctrl+N", statusTip="Новый скрипт")
		self.openAction = QAction('&Открыть', self, triggered=self.onOpenFile, shortcut="Ctrl+O", statusTip="Открыть")
		self.saveAction = QAction('&Сохранить', self, triggered=self.onSaveFile, shortcut="Ctrl+S", statusTip="Сохранить")
		self.exitAction = QAction('&Выход', self, triggered=self.onExit, shortcut="Ctrl+Q", statusTip="Выход")
		self.reloadStyle = QAction('&Обновить стиль', self, triggered=self.onReloadStyle, shortcut="Ctrl+R")

		self.generateCode = QAction("&Генерировать код",self,triggered=self.generateCode,shortcut="F5")

		self.switchVariableViewerAction = QAction("&Переключить виджет переменных",self,triggered=self.switchVariableViewer,shortcut="Alt+1")

		menubar = self.menuBar()
		self.fileMenu = menubar.addMenu('&ReNodes')
		self.fileMenu.setStatusTip("Основной раздел управления редактором")
		self.fileMenu.addAction(self.newAction)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.openAction)
		self.fileMenu.addAction(self.saveAction)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.exitAction)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.reloadStyle)

		self.editMenu = menubar.addMenu("&Правка")
		self.editMenu.addAction(self.generateCode)

		self.windows = menubar.addMenu("&Окна")
		self.windows.addAction(self.switchVariableViewerAction)
	
	def onNewFile(self):
		#logger.info("Новый скрипт")
		self.nodeGraph.sessionManager.newTab()
	
	def onOpenFile(self):
		#logger.info("Открыть")
		self.nodeGraph.sessionManager.openFile()
	
	def onSaveFile(self):
		#logger.info("Сохранить")
		self.nodeGraph.sessionManager.saveFile()
	
	def onExit(self):
		#logger.info("Выход")
		if self.nodeGraph.sessionManager.validateExit():
			exit(0)

	def onReloadStyle(self,string):
		logger.info("STYLE UPDATE")
		self.setStyleSheet(loadStylesheet("./data/qss/default.qss"))

	def createStatusBar(self):
		self.statusBar().showMessage("")
		self.status_mouse_pos = QLabel("")
		self.statusBar().addPermanentWidget(self.status_mouse_pos)
		
	def createInspectorDock(self):
		return
		dockWidget = QDockWidget("Инспектор", self)
		dockWidget.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
		dockWidget.setFeatures(QDockWidget.DockWidgetMovable)
		#dockWidget.setFixedHeight(300)
		
		dockWidget.setMaximumWidth(400)
		dockWidget.setMinimumWidth(100)
		# Create a widget to hold the contents of the inspector
		inspectorWidget = QWidget()

		# Create a layout for the inspector widget
		layout = QVBoxLayout()
		layout.setObjectName('inspectorLayout')
		inspectorWidget.setLayout(layout)

		# Set the inspector widget as the contents of the dock widget
		dockWidget.setWidget(inspectorWidget)

		# Add the dock widget to the main window
		self.addDockWidget(Qt.LeftDockWidgetArea, dockWidget)

		# TEST--------
		#addButton = QPushButton("+")
		#addButton.clicked.connect(self.addTextBox)
		#layout.addWidget(addButton, alignment=Qt.AlignTop)
		# Keep track of the number of text boxes
		#self.textboxCount = 0
		
	def createWindowGraphEditor(self):
		self.nodeGraph = NodeGraphComponent(self)
		gr = self.nodeGraph.graph
		gr.widget.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		pass

	def generateCode(self):
		self.nodeGraph.codegen.generateProcess()
		pass

	def switchVariableViewer(self):
		self.nodeGraph.variable_manager.setVisible(not self.nodeGraph.variable_manager.isVisible())
		self.nodeGraph.variable_manager.syncActionText()
		