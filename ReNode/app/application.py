import sys
import time
import os
import uuid

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMessageBox
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
	
	appName = "ReNode"
	appVersion = (global_version[0],global_version[1])
	appRevision = global_revision
	arguments = []
	debugMode = False

	refObject = None

	# string representation of version
	def getVersionString():
		return f"{Application.appVersion[0]}.{Application.appVersion[1]}.{Application.appRevision}"

	def getArguments():
		return Application.arguments

	def hasArgument(arg):
		return arg in Application.arguments

	def isExecutable():
		return getattr(sys, 'frozen', False)
	
	def isDebugMode():
		return Application.debugMode

	_configInitialized = False
	@staticmethod
	def initializeConfig():
		if Application._configInitialized: return
		Application._configInitialized = True
		Config.init()

	#construct
	def __init__(self,appInstance : QApplication):
		Application.refObject = self
		self.appInstance = appInstance
		self._initArguments()
		self._initExitEvents()

		pixmap = QtGui.QPixmap("data/splash.png").scaled(600, 400) #, QtCore.Qt.KeepAspectRatio
		#pixmap.fill(QtGui.QColor(0,0,0))
		splash = QtWidgets.QSplashScreen(pixmap,QtCore.Qt.WindowStaysOnTopHint)
		
		label = QtWidgets.QLabel(splash)
		label.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: white; padding: 5px;")
		label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
		label.setGeometry(0, pixmap.height() - 30, pixmap.width(), 30)
		label.setText(f'{self.appName} {Application.getVersionString()}')
		splashEnabled =  not Application.hasArgument("-nosplash")
		if splashEnabled: splash.show()

		handler = SplashScreenHandler(splash)
		formatter = logging.Formatter('%(levelname)s - %(message)s')
		handler.setFormatter(formatter)

		logger = logging.getLogger("main")
		self.logger = logger
		logger.setLevel(logging.DEBUG if Application.isDebugMode() else logging.INFO)
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
		
		Application.initializeConfig()

		# check objlib
		if Application.requireLibUpdate(logger):
			logger.info("Updating library...")
			Application.updateLibrary(logger)
			logger.info(f"Library updated. Hash {Config.get_str('lib_guid')}")

		self.nodeFactory = NodeFactory()

		self.mainWindow = MainWindow(self.nodeFactory)
		debugText = " [DEBUG]" if Application.isDebugMode() else ""
		self.mainWindow.setWindowTitle(f"{Application.appName} (v.{Application.getVersionString()}){debugText}")
		
		if not Application.hasArgument("-prep_code"):
			self.mainWindow.generateAllCode(allUpdate=False,loadingScreen=False,compileFlags={"-noupdatecguid"})

		#if splashEnabled: time.sleep(3)		

		self.mainWindow.show()
		#self.mainWindow.showMaximized()

		self.mainWindow.nodeGraph._loadWinStateFromConfig()

		splash.finish(self.mainWindow)
		logger.removeHandler(handler)
	
	def _initArguments(self):
		args = self.appInstance.arguments()
		Application.arguments = args
		Application.debugMode = Application.hasArgument("-debug")
		pass

	def _initExitEvents(self):
		import atexit
		from ReNode.app.DebuggerServer import DebuggerServer
		atexit.register(Config.saveConfig)
		atexit.register(lambda: self.mainWindow.nodeGraph.debuggerServer.stop())

	@staticmethod
	def requireLibUpdate(logger=None):
		"""Если возвращает false, то будет выполнено обновление библиотеки"""
		needUpdate = False
		if not os.path.exists(".\\lib_guid"):
			logger.warning("File \"lib_guid\" not found")
			needUpdate = True
		else:
			with open(".\\lib_guid", "r") as f:
				needUpdate = f.readline() != Config.get_str('lib_guid')
		return needUpdate
			

	@staticmethod
	def updateLibrary(logger=None,onlyCreateGuid=False):
		"""Генератор библиотеки. Если указать onlyCreateGuid, то будет генерироваться гуид объектной библиотеки (без сборки)"""
		from ReNode.app.LibGenerator import GenerateLibFromObj
		
		def _genGUID():
			#mode for generating guid
			with open(".\\lib.obj", "r",encoding="utf-8") as f:
				objlibContent = f.read()
				if logger: logger.debug("Content size ".format(len(objlibContent)))
			guid = str(uuid.uuid5(namespace=uuid.NAMESPACE_OID,name=objlibContent))
		
			if logger: logger.debug("Guid for library: {}".format(guid))

			with open(".\\lib_guid","w") as gf:
				gf.write(guid)
			return guid

		if onlyCreateGuid:
			_genGUID()
		else:
			#mode for updating guid from guid file to config
			#if not file exists do generate guid
			guid = "UNDEFINED"
			if not os.path.exists(".\\lib_guid"):
				guid = _genGUID()
			else:
				with open(".\\lib_guid", "r") as f:
					guid = f.readline()
			
			GenerateLibFromObj()

			Config.set("lib_guid",guid)
			Config.saveConfig()

		return

		
		

		
		if onlyCreateGuid:
			with open(".\\lib_guid","w") as gf:
				gf.write(guid)
		else:
			Config.set("lib_guid",guid)
		
		#regenerate library
		if not onlyCreateGuid:
			GenerateLibFromObj()

class ExceptionHandler:
	def __init__(self):
		self.logger = logging.getLogger('main')  # Имя вашего логгера
		self.handler = None

	def handle_exception(self, exctype, value, traceback_obj):
		import traceback
		self.logger.error("Unhandled exception", exc_info=(exctype, value, traceback_obj))
		
		tb_text = "".join(traceback.format_exception(exctype, value, traceback_obj))
		error_message = f"\n{Application.appName} {Application.getVersionString()}\nНеобработанное исключение: {exctype.__name__}\n{value}\n\n{tb_text}"
		#TODO copy error message to clipboard
		QMessageBox.critical(None, "Критическая ошибка", error_message)
		

		# Вы можете выполнить другие действия здесь, например, показать диалог с сообщением об ошибке.
		sys.__excepthook__(exctype, value, traceback_obj)  # Вызов стандартного обработчика исключений
		sys.exit(-1)

	def enable(self):
		self.handler = sys.excepthook
		sys.excepthook = self.handle_exception

	def disable(self):
		if self.handler is not None:
			sys.excepthook = self.handler



def AppMain():
	from ReNode.app.LibGenerator import GenerateLibFromObj
	global logger
	arguments = sys.argv

	if "-sign_lib" in arguments:
		Application.updateLibrary(None,True)
		sys.exit(0)

	if "-genlib" in arguments:
		sys.exit(GenerateLibFromObj())
	
	if "-genlib_run" in arguments:
		GenerateLibFromObj()	

	if getattr(sys, 'frozen', False):
		# Инициализация обработчика исключений
		exception_handler = ExceptionHandler()
		exception_handler.enable()

	app = QApplication(arguments)
	
	QtCore.QSettings.setPath(QtCore.QSettings.Format.IniFormat, QtCore.QSettings.Scope.SystemScope, ".")

	trans = QtCore.QTranslator()
	trans.load('.\data\qtbase_ru.qm')
	app.installTranslator(trans)

	QApplication.setStyle( "Fusion" )
	application = Application(app) 
	logger = RegisterLogger('main')
	appload_text = f"Loading {Application.appName} (version {Application.getVersionString()})"
	if Application.isDebugMode():
		appload_text += " [DEBUG MODE]"
	logger.info(appload_text)

	# при обновлении файла стиля вызывает метод onReloadStyle
	if Application.isDebugMode():
		# filewatcher
		fs_watcher = QtCore.QFileSystemWatcher()
		fs_watcher.addPath("./data/qss/default.qss")
		#print fws files
		fs_watcher.fileChanged.connect(application.mainWindow.onReloadStyle)

	logger.info("Application loaded.")

	std_exit_result = 0
	if Application.hasArgument('-prep_code'):
		obj = Application.refObject.mainWindow
		#obj.generateAllCode(allUpdate=True)
		if not obj.nodeGraph.compileAllGraphs(useLoadingScreen=False,onlyNotActual=False,compileFlags={
			"-showgenpath",
			"-logexcept",
			"-exceptinfo"
		}):
			std_exit_result = -20901
		
	
	#debug maker
	#ng = application.mainWindow.nodeGraph.script_maker.openMaker()
	#ng.next()
	#ng.next()
	if Application.hasArgument("-noapp"):
		sys.exit(std_exit_result)

	sys.exit(app.exec_())