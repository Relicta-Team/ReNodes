from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from ReNode.app.utils import clamp

def createTreeDataContent(baseChilds=None):
    if not baseChilds: 
        baseChilds = []
    else:
        baseChilds = [baseChilds]
    return {
        "rootFlag": True,
        "childs": baseChilds
    }

def addTreeContent(srcDict,data,name,icon):
    if not data: return None

    childs = srcDict['childs']

    addedSpan = {
        'name': data,
        'vname': name,
        'icon': icon,
        'childs': []
    }

    childs.append(addedSpan)
    return addedSpan

def createTreeContentItem(data,name,icon):
    if not data: return None
    return {
        'name': data,
        'vname': name,
        'icon': icon,
        'childs': []
    }

def addTreeContentItem(srcDict,rootItem):
    if not rootItem: return None
    childs = srcDict['childs']
    childs.append(rootItem)
    return rootItem

def findVec3TreeItemByProperty(tree,name,pname='name'):
    
    if tree.get(pname) == name:
        return [tree.get('name'),tree.get('vname'),tree.get('icon')]
    
    for item in tree['childs']:
        if item.get(pname) == name:
            return [item.get('name'),item.get('vname'),item.get('icon')]
        it = findVec3TreeItemByProperty(item,name,pname)
        if it: return it
    return None

class SeachComboButton(QPushButton):

    changed_event = pyqtSignal(str,str,QIcon)

    def __init__(self,parent=None):
        super().__init__(parent=parent)
        #self.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.customContextMenuRequested.connect(self.onOpenContextMenu)
        #self.activated.connect(self.onOpenContextMenu)
        #self.completer().popup().activated.connect(self.onOpenContextMenu)
        self.clicked.connect(self.showPopup)

        self.setStyleSheet("QPushButton { text-align: left; padding-left: 5px; }")

        self.dictTree = {}
        self.generateDictRuntime = False
        self.defaultListValue = ["",None,None] #data,visible name,icon object
       

    def resize(self,newsize):
        self.setMinimumHeight(newsize) #25
        font = self.font()
        font.setPixelSize(newsize)
        self.setFont(font)

    def loadContents(self,contents={},defaultValue=None):
        if contents and isinstance(contents,dict):
            if "rootFlag" not in contents:
                raise Exception("Corrupted data - rootFlag")
            if "childs" not in contents:
                raise Exception("Corrupted data - childs")
        if isinstance(contents,str):
            self.generateDictRuntime = True
        self.dictTree = contents
        if not defaultValue:
            firstValue = self.dictTree['childs'][0]['name']
            defaultValueTemp = findVec3TreeItemByProperty(self.dictTree,firstValue)
            if defaultValueTemp:
                defaultValue = defaultValueTemp
        
        self.defaultListValue = defaultValue

        if not self.text():
            self.onSetItemData(*self.defaultListValue)

    def showPopup(self) -> None:
        globPos = QCursor.pos()
        pos = self.mapFromGlobal(globPos)
        menu = CustomMenu(parent=self)
        if self.generateDictRuntime:
            from ReNode.ui.NodeGraphComponent import NodeGraphComponent
            menu.dictTree = NodeGraphComponent.refObject.getFactory().getClassAllChildsTree(self.dictTree)
        menu.tree.populate_tree(menu.dictTree)
        menuSize = menu.layout().sizeHint()
        availableGeometry = QApplication.screenAt(globPos).availableGeometry()
        screenRect = availableGeometry.contains(QRect(QPoint(globPos.x(), globPos.y()), menuSize))
        if not screenRect:
            menu.adjustSize()
            curX = globPos.x() + menu.width()
            curY = globPos.y()
            globPos.setX(clamp(curX, 0, availableGeometry.width() - menuSize.width()))
            globPos.setY(clamp(curY, 0, availableGeometry.height() - menuSize.height()))
            # globPos.setY(globPos.y() - menu.height())
        menu.exec_(globPos)

    def onSetItemData(self,data,text,optIcon):
        self.set_text(text or data)
        self.set_value(data)
        if optIcon:
            #icn = QIcon("data\\icons\\ArrayPin.png")
            siz = self.font().pixelSize()
            self.setIconSize(QSize(siz,siz))
            self.setIcon(optIcon)
        else:
            self.setIcon(QIcon())

        self.changed_event.emit(data,text,self.icon())
    
    def get_text(self):
        return self.text()
    
    def get_value(self):
        return self.property("data")

    def set_value(self,data):
        self.setProperty("data",data)

    def set_text(self,value):
        self.setText(value)

class CustomMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        #menu can drop from down,up,left,right
        self.widget = parent

        self.dictTree = self.widget.dictTree
        self.defaultListValue = self.widget.defaultListValue

        #setup deletion attribute
        self.setAttribute(Qt.WA_DeleteOnClose,True)

        sizeXFull = 400
        sizeYFull = 350
        ofsY = 0

        self.edit = SeachMenuLineEditWidget()
        self.tree = SearchMenuTreeWidget()
        
        self.tree.itemClicked.connect(self.onClickItem)
        #self.tree.activated.connect(self.onClickItem)

        self.edit.textChanged.connect(self._on_text_changed)

        editWidget = self.edit
        editWidget.setFixedSize(sizeXFull, 25)
        editWidget.setPlaceholderText("Поиск...")

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

        self.delegate = HighlightingDelegate(self.tree)
        self.delegate.editor = self.edit
        self.tree.setItemDelegate(self.delegate)

        # debug items 
        # for i in range(1000):
        #     item = QTreeWidgetItem()
        #     item.setText(0, "Объект {}".format(i))
        #     self.tree.addTopLevelItem(item)

    def get_value(self):
        return self.widget.get_value()
    
    def set_value(self,val):
        self.widget.set_value(val)

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        if a0.key() == Qt.Key_Alt:
            a0.ignore()
            return
        
        return super().keyPressEvent(a0)

    def onClickItem(self,item : QModelIndex):
        if isinstance(item,QModelIndex):
            self.widget.onSetItemData(item.data(Qt.UserRole),item.data(Qt.DisplayRole),item.data(Qt.DecorationRole)) #item.text(0)
        else:
            self.widget.onSetItemData(item.data(0,Qt.UserRole),item.data(0,Qt.DisplayRole),item.data(0,Qt.DecorationRole))
        self.close()

    # internal

    def _on_text_changed(self, text):
        self.buidSearchTree(text)

    def buidSearchTree(self,search_text):
        #hideall = searcher != ""
        search_words = search_text.lower().split()
        self.delegate.set_search_words(search_words)
        self.tree.viewport().update()
        self.reset_visibility(self.tree.invisibleRootItem())
        self.tree.collapseAll()
        if search_words:
            self.hide_items(self.tree.invisibleRootItem(), search_words)

    def hide_items(self, item, search_words):
        for idx in range(item.childCount()):
            child = item.child(idx)
            if self.item_contains_words(child, search_words):
                child.setHidden(False)
                child.setExpanded(True)
                self.show_parents(child)
                self.hide_items(child, search_words)
            else:
                child.setHidden(True)
                self.hide_items(child, search_words)

    def item_contains_words(self, item, search_words):
        item_text = item.text(0).lower()
        contains = False
        for word_group in search_words:
            if word_group in item_text:
                contains = True
                break
        return contains

    def show_parents(self, item):
        parent = item.parent()
        while parent:
            parent.setExpanded(True)
            parent.setHidden(False)
            parent = parent.parent()

    def reset_visibility(self, item):
        item.setHidden(False)
        item.setExpanded(False)
        for idx in range(item.childCount()):
            child = item.child(idx)
            self.reset_visibility(child)

class SeachMenuLineEditWidget(QLineEdit):
    pass

class SearchMenuTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.dictTree = None
    
    def populate_tree(self,ref,parent=None,level=0):
        if not ref: return

        if level == 0:
            if 'rootFlag' in ref:
                for refitem in ref['childs']:
                    item = QTreeWidgetItem()
                    item.setText(0, refitem.get('vname') or refitem.get('name'))
                    item.setData(0,Qt.UserRole, refitem["name"])
                    if "desc" in refitem:
                        item.setToolTip(0, refitem["desc"])
                    if 'icon' in refitem:
                        item.setIcon(0, refitem['icon'])
                    self.addTopLevelItem(item)
                    self.populate_tree(refitem.get('childs'),item,level+1)
        else:
            for refitem in ref:
                item = QTreeWidgetItem()
                item.setText(0, refitem.get('vname') or refitem.get('name'))
                item.setData(0,Qt.UserRole, refitem["name"])
                if "desc" in refitem:
                    item.setToolTip(0, refitem["desc"])
                if 'icon' in refitem:
                    item.setIcon(0, refitem['icon'])
                parent.addChild(item)
                self.populate_tree(refitem.get('childs'),item,level+1)
    
class HighlightingDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_words = []
        self.editor : QLineEdit = None

    def set_search_words(self, search_words):
        self.search_words = search_words

    def paint(self, painter, option, index):
        if index.isValid():
            text = index.data(Qt.DisplayRole)
            for search_word in self.search_words:
                start_pos = 0
                while start_pos < len(text):
                    start_pos = text.lower().find(search_word, start_pos)
                    if start_pos == -1:
                        break
                    end_pos = start_pos + len(search_word)
                    highlight_rect = option.rect
                    #highlight_rect.setX(option.rect.x() + start_pos * self.editor.fontMetrics().width(" "))
                    #highlight_rect.setWidth(len(search_word) * self.editor.fontMetrics().width(" "))
                    painter.fillRect(highlight_rect, option.palette.highlight().color())
                    start_pos = end_pos

            super().paint(painter, option, index)