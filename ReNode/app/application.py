import sys

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication
from ReNode.app.VERSION import global_version
from ReNode.app.REVISION import global_revision

class Application:
	
	appName = "ReNodes"
	appVersion = (global_version[0],global_version[1])
	appRevision = global_revision

	# string representation of version
	def getVersionString():
		return f"{Application.appVersion[0]}.{Application.appVersion[1]}.{Application.appRevision}"

	#construct
	def __init__(self):

		self.mainWindow = QtWidgets.QMainWindow()
		self.mainWindow.show()



def AppMain():
	print(f"Loading {Application.appName} (version {Application.getVersionString()})")

	app = QApplication(sys.argv)
	QApplication.setStyle( "Fusion" )
	application = Application() 

	sys.exit(app.exec_())