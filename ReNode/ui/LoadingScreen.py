from PyQt5.QtWidgets import QApplication, QSplashScreen, QLabel,QProgressBar
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import *
from Qt import QtCore, QtWidgets, QtGui
import logging

class LoadingScreen(QSplashScreen):
    def __init__(self, pixmap: QPixmap=None):
        if pixmap is None:
            pixmap = QPixmap("data//loading.png").scaled(600,400)
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        #self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setEnabled(True)

        label = QtWidgets.QLabel(self)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: white; padding: 5px;")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        pmW = pixmap.width()
        pmH = pixmap.height()
        #label.setGeometry(0,pmH - int(label.height()/2),pmW,label.height())
        label.setText(f'<span style="font-size: 16px;">Загрузка</span>')

        lbl2 = QLabel(self)
        lbl2.setStyleSheet("background-color: rgba(0, 0, 0, 0); color: white; padding: 5px;")
        lbl2.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignCenter)
        lbl2.setGeometry(0,label.height(),pmW,pmH)
        self.lbl2 = lbl2

        self.progress = QProgressBar(self)
        self.progress.setMaximum(100)
        self.progress.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.progress.setFixedWidth(pmW)
        self.progress.setGeometry(0, pmH - self.progress.height(), pmW, self.progress.height())
        
        self.showMessage("<h1><font color='green'>Loading</font></h1>", Qt.AlignTop | Qt.AlignCenter, Qt.white)
        self.show()

        QApplication.processEvents()     

    def setMessage(self, message):
        self.showMessage(message,Qt.AlignmentFlag.AlignBottom | Qt.AlignCenter, Qt.white)
        self.lbl2.setText(message)
        QApplication.processEvents()

    def setProgress(self, progress):
        self.progress.setValue(int(progress))
    
    def done(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        NodeGraphComponent.refObject.log_dock.update()
        self.close()


class LoadingScreenHandler(logging.Handler):
	def __init__(self, loading, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.loading : LoadingScreen = loading

	def emit(self, record):
		if self and self.loading:
			message = self.format(record)
			self.loading.setMessage(message)
			QApplication.processEvents()