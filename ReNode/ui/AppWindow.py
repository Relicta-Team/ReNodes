import os
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
		from ReNode.app.application import Application
		self.newAction = QAction('&Новый граф', self, triggered=self.onNewFile, shortcut="Ctrl+N", statusTip="Открывает менеджер создания нового графа")
		self.openAction = QAction('&Открыть', self, triggered=self.onOpenFile, shortcut="Ctrl+O", statusTip="Открыть")
		self.saveAction = QAction('&Сохранить', self, triggered=self.onSaveFile, shortcut="Ctrl+S", statusTip="Сохранить")
		self.exitAction = QAction('&Выход', self, triggered=self.onExit, shortcut="Ctrl+Q", statusTip="Выход")
		
		self.reloadStyle = None
		if Application.isDebugMode():
			self.reloadStyle = QAction('&Обновить стиль', self, triggered=self.onReloadStyle, shortcut="Ctrl+R")

		self.generateCode = QAction("&Генерировать код",self,triggered=self.generateCode,shortcut="F5")

		self.switchInspectorAction = QAction("Переключить окно &инспектора",self,triggered=self.switchInspectorVisual,shortcut="Alt+1",statusTip="Переключает видимость окна инспектора")
		self.switchVariableViewerAction = QAction("Переключить окно &пользовательских свойств",self,triggered=self.switchVariableViewer,shortcut="Alt+2",statusTip="Переключает видимость окна переменных")
		self.switchLoggerAction = QAction("Переключить окно &логирования",self,triggered=self.switchLoggerVisual,shortcut="Alt+3",statusTip="Переключает видимость окна консоли")
		self.switchHistoryAction = QAction("Переключить окно &истории",self,triggered=self.switchHistoryVisual,shortcut="Alt+4",statusTip="Переключает видимость окна истории")

		menubar = self.menuBar()
		self.fileMenu = menubar.addMenu('&ReNodes')
		self.fileMenu.setStatusTip("Основной раздел управления редактором")
		self.fileMenu.addAction(self.newAction)
		self.fileMenu.addAction(self.openAction)
		self.fileMenu.addAction(self.saveAction)
		
		self.fileMenu.addAction(QAction("Открыть папку графа",self,triggered=self.openCurrentGraphFolder))
		self.fileMenu.addAction(QAction("Настройки",self,triggered=self.openSettings))
		self.fileMenu.addAction(self.exitAction)
		
		if self.reloadStyle:
			self.fileMenu.addSeparator()
			self.fileMenu.addAction(self.reloadStyle)

		self.windows = menubar.addMenu("&Вид")
		self.windows.addAction(self.switchInspectorAction)
		self.windows.addAction(self.switchVariableViewerAction)
		self.windows.addAction(self.switchLoggerAction)
		self.windows.addAction(self.switchHistoryAction)
		self.windows.addAction(QAction("Скрыть все окна",self,triggered=self.hideAllWindows,shortcut="Alt+`"))
		self.windows.addAction(QAction("Сбросить позиции окон",self,triggered=self.resetWindows))
		self.windows.addAction(QAction("Очистить консоль",self,triggered=ConsoleCommand.getCommandDelegate(ClearConsoleCommand)))


		self.editMenu = menubar.addMenu("&Правка")
		self.editMenu.addAction(self.generateCode)
		
		
		for act in menubar.actions() + self.fileMenu.actions() + self.editMenu.actions() + self.windows.actions():
			act.setAutoRepeat(False)
		
	
	def onNewFile(self):
		#logger.info("Новый скрипт")
		#self.nodeGraph.sessionManager.newTab(switchTo=True)
		self.nodeGraph.script_maker.openMaker()
	
	def onOpenFile(self):
		#logger.info("Открыть")
		self.nodeGraph.sessionManager.openFile()
	
	def onSaveFile(self):
		#logger.info("Сохранить")
		self.nodeGraph.sessionManager.saveFile()
	
	def onExit(self):
		#logger.info("Выход")
		if self.nodeGraph.sessionManager.validateExit():
			sys.exit(0)

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
		if self.nodeGraph.sessionManager.getActiveTabData():
			self.nodeGraph.codegen.generateProcess()
		else:
			self.nodeGraph.codegen.logger.warning("Нет активной вкладки для генерации")

	def switchVariableViewer(self):
		self.nodeGraph.variable_manager.setVisible(not self.nodeGraph.variable_manager.isVisible())
	
	def switchLoggerVisual(self):
		self.nodeGraph.log_dock.setVisible(not self.nodeGraph.log_dock.isVisible())

	def switchHistoryVisual(self):
		self.nodeGraph.undoView_dock.setVisible(not self.nodeGraph.undoView_dock.isVisible())

	def switchInspectorVisual(self):
		self.nodeGraph.inspector.setVisible(not self.nodeGraph.inspector.isVisible())

	def resetWindows(self):
		self.restoreState(self.nodeGraph._defaultState)
		self.restoreGeometry(self.nodeGraph._defaultGeometry)

	def hideAllWindows(self):
		self.nodeGraph.variable_manager.setVisible(False)
		self.nodeGraph.log_dock.setVisible(False)
		self.nodeGraph.undoView_dock.setVisible(False)
		self.nodeGraph.inspector.setVisible(False)

	def openCurrentGraphFolder(self):
		tDat = self.nodeGraph.sessionManager.getActiveTabData()
		if tDat and tDat.filePath:
			os.system(f'explorer /select,"{os.path.realpath(tDat.filePath)}"')
		else:
			logger.warn("Нет активной вкладки или отсутствует путь к графу")

	def openSettings(self):
		pass