import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class MainWindow(QMainWindow):
	def __init__(self,parent=None):
		super(MainWindow, self).__init__(parent)
		layout=QHBoxLayout()
		bar=self.menuBar()
		file=bar.addMenu('File')
		file.addAction('New')
		file.addAction('Save')
		file.addAction('quit')

		self.items=QDockWidget('Dockable',self)
		

		self.listWidget=QListWidget()
		self.listWidget.addItem('Item1')
		self.listWidget.addItem('Item2')
		self.listWidget.addItem('Item3')
		self.listWidget.addItem('Item4')

		self.items=QDockWidget('Dockable2',self)
		self.listWidget=QListWidget()
		self.listWidget.addItem('Item1')
		self.listWidget.addItem('Item2')
		self.listWidget.addItem('Item3')
		self.listWidget.addItem('Item4')

		self.items.setWidget(self.listWidget)
		self.items.setFloating(False)
		self.setCentralWidget(QTextEdit())
		self.addDockWidget(Qt.RightDockWidgetArea,self.items)

		self.setLayout(layout)
		self.setWindowTitle('Dock')