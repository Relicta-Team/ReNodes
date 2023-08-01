
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtWidgets, QtCore, QtGui
from ReNode.app.utils import loadStylesheet
from ReNode.ui.Widgets import *

class MainWindow( QMainWindow ):

	def __init__( self):
		super().__init__()
		
		self.initUI()


	def initUI(self):
		self.setWindowTitle("Unnamed window")
		self.setWindowIcon(QtGui.QIcon('./data/pic.png'))
		
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
		
		self.showMaximized()
		self.createMenu()
		self.createStatusBar()

		# при обновлении файла стиля вызывает метод onReloadStyle
		# filewatcher
		self.fs_watcher = QtCore.QFileSystemWatcher()
		self.fs_watcher.addPath("./data/qss/default.qss")
		#print fws files
		print(self.fs_watcher.files())
		self.fs_watcher.fileChanged.connect(self.onReloadStyle)
		
	
	def createMenu(self):
		self.newAction = QAction('&Новый скрипт', self, triggered=self.onNewFile, shortcut="Ctrl+N", statusTip="Новый скрипт")
		self.openAction = QAction('&Открыть', self, triggered=self.onOpenFile, shortcut="Ctrl+O", statusTip="Открыть")
		self.saveAction = QAction('&Сохранить', self, triggered=self.onSaveFile, shortcut="Ctrl+S", statusTip="Сохранить")
		self.exitAction = QAction('&Выход', self, triggered=self.onExit, shortcut="Ctrl+Q", statusTip="Выход")
		self.reloadStyle = QAction('&Обновить стиль', self, triggered=self.onReloadStyle, shortcut="Ctrl+R")

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
	
	def onNewFile(self):
		print("Новый скрипт")
	
	def onOpenFile(self):
		print("Открыть")
	
	def onSaveFile(self):
		print("Сохранить")
	
	def onExit(self):
		print("Выход")
		exit(0)

	def onReloadStyle(self,string):
		print("STYLE UPDATE")
		self.setStyleSheet(loadStylesheet("./data/qss/default.qss"))

	def createStatusBar(self):
		self.statusBar().showMessage("")
		self.status_mouse_pos = QLabel("")
		self.statusBar().addPermanentWidget(self.status_mouse_pos)
		
	