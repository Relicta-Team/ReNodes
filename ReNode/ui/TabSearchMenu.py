import typing
from collections import OrderedDict
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *
from Qt.QtCore import Signal
from PyQt5.QtWidgets import QWidget, QTreeWidget
import asyncio
from NodeGraphQt.constants import ViewerEnum, ViewerNavEnum
from NodeGraphQt.qgraphics.pipe import PipeItem
from NodeGraphQt.widgets.tab_search import TabSearchLineEditWidget


class TabSearchMenu(QWidget):
    def __init__(self,parent=None):
        super(TabSearchMenu, self).__init__(parent)

        self.nodeGraphComponent = None

        baseWidget = self
        #self.move(0,0)
        sizeXFull = 400
        sizeYFull = 350
        baseWidget.setMinimumSize(sizeXFull+2, sizeYFull+2)
        baseWidget.setMaximumSize(sizeXFull+2, sizeYFull+2)
        self.setVisible(False)
        baseWidget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.background = baseWidget
        #baseWidget.setStyleSheet('background-color: red;')
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               ViewerEnum.BACKGROUND_COLOR.value))
        selected_color = self.palette().highlight().color().getRgb()
        baseWidget.setStyleSheet(f".TabSearchMenu {{ background-color: {'rgb({0},{1},{2})'.format(*ViewerNavEnum.BACKGROUND_COLOR.value)}; border-radius: 2px; border: 2px solid #353535; }}")

        ofsY = 0
        text = QLabel(baseWidget)
        self.text = text
        text.move(1,1)
        text.setMinimumSize(sizeXFull,25)
        text.setMaximumSize(sizeXFull,25)
        ofsY += 25 + 5
        self.setText("Выберите тип узла из всех доступных")
        #self.setStyleSheet("padding: 10px 50px 20px;")

        inputX = int(sizeXFull/100*80)
        checkX = sizeXFull - inputX
        self.edit = TabSearchLineEdit(baseWidget)
        self.edit.setPlaceholderText("Поиск")
        self.edit.move(1, ofsY)
        self.edit.setMinimumSize(inputX,34)
        self.edit.setMaximumSize(inputX,34)
        
        self.edit.tab_pressed.connect(self._close)
        self.edit.returnPressed.connect(self._on_search_submitted)
        self.edit.textChanged.connect(self._on_text_changed)

        self.contextSense = QCheckBox(baseWidget)
        self.contextSense.move(1+inputX,ofsY)
        self.contextSense.setMinimumSize(checkX,34)
        self.contextSense.setMaximumSize(checkX,34)
        self.contextSense.setText("Контекст")
        self.contextSense.setToolTip("Если эта опция включена, то в поиске будут доступны узлы, подходящие к текущему контексту.")

        ofsY += 34

        treeWidget = QTreeWidget(baseWidget)
        treeWidget.move(1,ofsY)
        self.tree = treeWidget
        treeWidget.setColumnCount(1)
        treeWidget.setMinimumSize(sizeXFull, sizeYFull-ofsY)
        treeWidget.setMaximumSize(sizeXFull, sizeYFull-ofsY)
        treeWidget.setWindowTitle("NodeSearch")
        treeWidget.setHeaderHidden(True)
        treeWidget.setAnimated(True)
        treeWidget.setIndentation(10)

        treeWidget.itemDoubleClicked.connect(self.itemDoubleClicked)
        
        self.lastMousePos = None

        #treeWidget.setDragEnabled(True)

        self.delegate = HighlightingDelegate(self.tree)
        self.delegate.editor = self.edit
        self.tree.setItemDelegate(self.delegate)

        
        treeWidget.headerItem().setText(0,"Select node")
        
        self._existsTrees = {}

        #debug test nodes
        test = {
            "Операторы.Контрольные структуры": ["operators.while","operators.if_branch"],
            "Операторы.Системные": ["sys.push","sys.pop"],
            "Тесты.Системные": ["debug_test_create"],
            "Списки": ["list.create","list.resize"],
            "Строки": ["string.create"],
            "Структуры.Дата": [],
            "ВСЕ": ['item_create','item_delete']
        }

        #sort test
        self.dictTreeGen = OrderedDict(sorted(test.items()))
        #self.build_tree(test)
        self.tree.sortItems(0,Qt.SortOrder.AscendingOrder)

    
    def onChangeVisible(self,newMode,centerpos=None):
        if newMode:
            self.tree.collapseAll() #fix collapse all on load
            self.edit.setText("") #fix plain text
            if centerpos:
                centerpos = self.nodeGraphComponent.graph._viewer.mapToScene(centerpos)
                self.lastMousePos = [centerpos.x(),centerpos.y()]
                return
            ps = self.nodeGraphComponent.graph.viewer().scene_cursor_pos()
            ps = self.nodeGraphComponent.graph._viewer.mapToScene(ps)
            self.lastMousePos = [ps.x(),ps.y()]

    def generate_treeDict(self):
        self.dictTreeGen = self.nodeGraphComponent._generateSearchTreeDict()

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

    def __containsFilter(self,string,filter):
        for i in filter:
            if i in string:
                return True
        return False

    def build_tree(self, data: OrderedDict, parent_item:QTreeWidgetItem=None,path=None,deepMode = 1):
        item = None
        for key, values in data.items():
            key_parts = key.split(".")
            cur_section = key_parts[0]
            if not path:
                path = key_parts   
            cur_cat = ".".join(path[:deepMode])
            

            #if searchFilter and self.__containsFilter(cur_section,searchFilter):
            if self._existsTrees.get(cur_cat):
                item = self._existsTrees[cur_cat]
            else:
                item = QTreeWidgetItem(parent_item, [cur_section])
                self._existsTrees[cur_cat] = item

            if len(key_parts) > 1:
                self.build_tree({ ".".join(key_parts[1:]): values }, parent_item=item, path=path, deepMode=deepMode+1)
            else:
                if len(values) > 0:
                    for value in values:
                        #if searchFilter and self.__containsFilter(value,searchFilter):
                        item_name = value
                        if self.nodeGraphComponent:
                            item_name = self._getAssociatedNodeName(value)
                        value_item = QTreeWidgetItem(item, [item_name])
                        value_item.setData(0, QtCore.Qt.UserRole, value)

            if parent_item is None:
                self.tree.addTopLevelItem(item)
            
            path=None

    def _getAssociatedNodeName(self,nodesysname):
        itm = self.nodeGraphComponent.getFactory().nodes.get(nodesysname,None)
        if itm:
            return itm.get('name',nodesysname)
        return nodesysname

    def setText(self,data):
        self.text.setText(f'<p style=\"font-size:20px;padding: 2% 2%;\">{data}</p>')

    def _close(self):
        self.setVisible(False)

    def _on_search_submitted(self):
        print("search submitted")

    def _on_text_changed(self, text):
        print("changed to "+text)
        self.buidSearchTree(text)

    #dbl click event
    def itemDoubleClicked(self, item : QTreeWidgetItem, column):
        name = item.text(0)
        data = item.data(0,QtCore.Qt.UserRole)
        if data:
            self._close()
            self.nodeGraphComponent.nodeFactory.instance(data,pos=self.lastMousePos,graphref=self.nodeGraphComponent.graph)
    
    def onDragFromPipeContext(self,pipe: PipeItem):
        self.nodeGraphComponent.toggleNodeSearch()
        print(f"TODO context drag logic {pipe}")


class TabSearchLineEdit(QtWidgets.QLineEdit):

    tab_pressed = Signal()

    def __init__(self, parent=None):
        super(TabSearchLineEdit, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_MacShowFocusRect, 0)
        self.setMinimumSize(200, 22)
        # text_color = self.palette().text().color().getRgb()
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               ViewerEnum.BACKGROUND_COLOR.value))
        selected_color = self.palette().highlight().color().getRgb()
        style_dict = {
            'QLineEdit': {
                'color': 'rgb({0},{1},{2})'.format(*text_color),
                'border': '1px solid rgb({0},{1},{2})'.format(
                    *selected_color
                ),
                'border-radius': '3px',
                'padding': '2px 4px',
                'margin': '2px 4px 8px 4px',
                'background': 'rgb({0},{1},{2})'.format(
                    *ViewerNavEnum.BACKGROUND_COLOR.value
                ),
                'selection-background-color': 'rgba({0},{1},{2},200)'
                                              .format(*selected_color),
            }
        }
        stylesheet = ''
        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        self.setStyleSheet(stylesheet)

    def keyPressEvent(self, event):
        super(TabSearchLineEdit, self).keyPressEvent(event)
        if event.key() == QtCore.Qt.Key_Tab:
            self.tab_pressed.emit()


class HighlightingDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_words = []
        self.editor : QLineEdit = None

    def set_search_words(self, search_words):
        self.search_words = search_words

    def paint(self, painter, option, index):
        if index.isValid():
            text = index.data(QtCore.Qt.DisplayRole)
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