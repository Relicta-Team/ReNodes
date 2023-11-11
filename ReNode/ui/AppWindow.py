
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
		self.setWindowTitle("Main")
		self.setWindowIcon(QtGui.QIcon('./data/pic.png'))

		#style setup
		self.setStyleSheet(loadStylesheet("./data/qss/default.qss"))
		#self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		# maybee need custom winframe??

		#setwindows size at screensize
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		
		
		self.createMenu()
		self.createStatusBar()

		#moved to NodeGraphComponent.mdiArea
		# self.mdiArea = QMdiArea()
		# self.mdiArea.setBackground(QtGui.QColor(0, 0, 0, 0))
		# self.mdiArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		# self.mdiArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		# self.mdiArea.setViewMode(QMdiArea.TabbedView)
		# self.mdiArea.setDocumentMode(True)
		# self.mdiArea.setTabsClosable(True)
		# self.mdiArea.setTabsMovable(True)
		#self.setCentralWidget(self.mdiArea)

		self.createWindowGraphEditor()
	
	def createMenu(self):
		from ReNode.ui.LoggerConsole import ConsoleCommand,ClearConsoleCommand
		self.newAction = QAction('&Новый скрипт', self, triggered=self.onNewFile, shortcut="Ctrl+N", statusTip="Новый скрипт")
		self.openAction = QAction('&Открыть', self, triggered=self.onOpenFile, shortcut="Ctrl+O", statusTip="Открыть")
		self.saveAction = QAction('&Сохранить', self, triggered=self.onSaveFile, shortcut="Ctrl+S", statusTip="Сохранить")
		self.exitAction = QAction('&Выход', self, triggered=self.onExit, shortcut="Ctrl+Q", statusTip="Выход")
		self.reloadStyle = QAction('&Обновить стиль', self, triggered=self.onReloadStyle, shortcut="Ctrl+R")

		self.generateCode = QAction("&Генерировать код",self,triggered=self.generateCode,shortcut="F5")

		self.switchVariableViewerAction = QAction("Переключить окно &переменных",self,triggered=self.switchVariableViewer,shortcut="Alt+1",statusTip="Переключает видимость окна переменных")
		self.switchLoggerAction = QAction("Переключить окно &логирования",self,triggered=self.switchLoggerVisual,shortcut="Alt+2",statusTip="Переключает видимость окна консоли")
		self.switchHistoryAction = QAction("Переключить окно &истории",self,triggered=self.switchHistoryVisual,shortcut="Alt+3",statusTip="Переключает видимость окна истории")

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
		self.windows.addAction(self.switchLoggerAction)
		self.windows.addAction(self.switchHistoryAction)
		self.windows.addAction(QAction("Очистить консоль",self,triggered=ConsoleCommand.getCommandDelegate(ClearConsoleCommand)))
	
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
	
	def switchLoggerVisual(self):
		self.nodeGraph.log_dock.setVisible(not self.nodeGraph.log_dock.isVisible())

	def switchHistoryVisual(self):
		self.nodeGraph.undoView_dock.setVisible(not self.nodeGraph.undoView_dock.isVisible())