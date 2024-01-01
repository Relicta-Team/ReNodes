from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from numpy import arange
try:
	class Window(QDialog):

		def __init__(self):
			super(Window, self).__init__()
			self.resize(600,400)

			self.mainLayout = QVBoxLayout(self)
			#self.mainLayout.setMargin(10)

			self.scroll = QScrollArea()
			self.scroll.setWidgetResizable(True)
			self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
			self.mainLayout.addWidget(self.scroll)

			scrollContents = QWidget()
			self.scroll.setWidget(scrollContents)

			self.textLayout = QVBoxLayout(scrollContents)
			#self.textLayout.setMargin(10)

			for _ in arange(5):
				text = GrowingTextEdit()
				#oneline height
				font = text.font().pixelSize()
				text.setMinimumHeight(font)
				self.textLayout.addWidget(text)


	class GrowingTextEdit(QTextEdit):

		def __init__(self, *args, **kwargs):
			super(GrowingTextEdit, self).__init__(*args, **kwargs)
			self.document().contentsChanged.connect(self.sizeChange)

			self.heightMin = 0
			self.heightMax = 65000
			self.widthMin = 20  # Минимальная ширина
			self.widthMax = 100  # Максимальная ширина

			self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
			self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)  # Включаем перенос по словам

		def sizeChange(self):
			docHeight = self.document().size().toSize().height()
			if self.heightMin <= docHeight <= self.heightMax:
				self.setMinimumHeight(docHeight)

			self.document().setTextWidth(self.widthMax) 

	app = QApplication([])
	wind = Window()
	wind.show()
	app.exec()
	
except Exception as e:
	print(e)
	input()