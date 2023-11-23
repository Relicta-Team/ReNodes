from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class SeachComboButton(QPushButton):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        #self.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.customContextMenuRequested.connect(self.onOpenContextMenu)
        #self.activated.connect(self.onOpenContextMenu)
        #self.completer().popup().activated.connect(self.onOpenContextMenu)
        self.clicked.connect(self.showPopup)
        
        self.setMinimumHeight(25)
        font = self.font()
        font.setPixelSize(25)
        self.setFont(font)

        self.setStyleSheet("QPushButton { text-align: left; text-indent: 5px; }")
        
    def showPopupOld(self) -> None:
        #pos is mouse positon
        pos = self.mapFromGlobal(QCursor.pos())
        self.onOpenContextMenu(pos)
        #return super().showPopup()

    def showPopup(self) -> None:
        globPos = QCursor.pos()
        pos = self.mapFromGlobal(globPos)
        menu = CustomMenu(parent=self)
        menuSize = menu.layout().sizeHint()
        availableGeometry = QApplication.screenAt(globPos).availableGeometry()
        screenRect = availableGeometry.contains(QRect(QPoint(globPos.x(), globPos.y()), menuSize))
        if not screenRect:
            menu.adjustSize()
            globPos.setY(globPos.y() - menu.height())
        menu.exec_(globPos)

    def onOpenContextMenu(self, pos):
        menu = CustomMenu(parent=self)
        #menu.pos
        menu.exec_(self.mapToGlobal(pos))

    def onSetItem(self,item):
        self.setText(item)
        icn = QIcon("data\\icons\\ArrayPin.png")
        siz = self.size()
        
        #self.setIconSize(QSize(25,25))
        #self.setIcon(icn)
        

class CustomMenu(QMenu):
    def __init__(self,objList=None, parent=None):
        super().__init__(parent=parent)
        #menu can drop from down,up,left,right
        self.widget = parent

        #setup deletion attribute
        self.setAttribute(Qt.WA_DeleteOnClose,True)

        sizeXFull = 400
        sizeYFull = 350
        ofsY = 0

        self.edit = SeachMenuLineEditWidget()
        self.tree = SearchMenuTreeWidget()
        
        self.tree.itemClicked.connect(self.onClickItem)

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

    def onClickItem(self,item):
        self.widget.onSetItem(item.text(0))
        self.close()

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