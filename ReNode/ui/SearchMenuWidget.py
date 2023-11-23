from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class SeachMenuWidget(QWidget):
    def __init__(self):
        super().__init__()
        sizeXFull = 400
        sizeYFull = 350
        ofsY = 0

        self.edit = SeachMenuLineEditWidget()
        self.tree = SearchMenuTreeWidget()
        
        editWidget = self.edit
        editWidget.setFixedSize(sizeXFull, 25)

        treeWidget = self.tree
        treeWidget.setColumnCount(1)
        treeWidget.setMinimumSize(sizeXFull, sizeYFull-ofsY)
        treeWidget.setMaximumSize(sizeXFull, sizeYFull-ofsY)
        treeWidget.setWindowTitle("Searcher")
        treeWidget.setHeaderHidden(True)
        treeWidget.setAnimated(True)
        treeWidget.setIndentation(10)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        layout.addWidget(self.edit)
        layout.addWidget(self.tree)

        # debug items 
        for i in range(1000):
            item = QTreeWidgetItem()
            item.setText(0, "Объект {}".format(i))
            self.tree.addTopLevelItem(item)

    def get_value(self):
        return self.edit.text()
    
    def set_value(self,val):
        self.edit.setText(val)

class SeachMenuLineEditWidget(QLineEdit):
    pass

class SearchMenuTreeWidget(QTreeWidget):
    pass