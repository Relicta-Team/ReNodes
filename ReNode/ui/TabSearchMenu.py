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
        
        #treeWidget.setDragEnabled(True)
        
        treeWidget.headerItem().setText(0,"Select node")
        
        test = {
            "Операторы.Контрольные структуры": ["operators.while","operators.if_branch"],
            "Списки": ["list.create","list.resize"],
            "Строки": ["string.create"],
            "Структуры.Дата": [],
            "ВСЕ": ['item_create','item_delete']
        }

        #sort test
        self.test = OrderedDict(sorted(test.items()))
        
        self.build_tree(test)
        self.tree.sortItems(0,Qt.SortOrder.AscendingOrder)

        """data = ['folder1/file1', 'file2', 'file3', 'folder2/file4']
        for i in range(1,1000):
            data.append(f'fld/test/num'+str(i))
        items = []
        for item in data:
            itemparts = item.split('/')

            entry = QTreeWidgetItem(None, [itemparts[0]])
            
            partentitem = entry
            if itemparts[0] == 'fld':
                entry.setIcon(0,QtGui.QIcon('./data/function_sim.png'))
                entry.setHidden(True)

            if len(itemparts) > 1:
                idx = 0
                for i in itemparts[1:]:
                    childitem = QTreeWidgetItem(None, [i])
                    if idx%2==0:
                        childitem.setIcon(0,QtGui.QIcon('./data/function_sim.png'))
                    partentitem.addChild(childitem)
                    partentitem = childitem
                    idx+=1

            items.append(entry)

        treeWidget.insertTopLevelItems(0, items)"""
    
    def build_tree(self, data: OrderedDict, parent_item:QTreeWidgetItem=None, searchFilter=None):
        for key, values in data.items():
            key_parts = key.split(".")

            item = QTreeWidgetItem(parent_item, [key_parts[0]])
           
            if len(key_parts) > 1:
                self.build_tree({ ".".join(key_parts[1:]): values }, parent_item=item)
            else:
                if len(values) > 0:
                    for value in values:
                        value_item = QTreeWidgetItem(item, [value])

            if parent_item is None:
                self.tree.addTopLevelItem(item)

    def setText(self,data):
        self.text.setText(f'<p style=\"font-size:20px;padding: 2% 2%;\">{data}</p>')

    def _close(self):
        self.setVisible(False)

    def _on_search_submitted(self):
        print("search submitted")

    def _on_text_changed(self, text):
        print("changed to "+text)
        self.tree.clear()
        self.build_tree(self.test,searchFilter=text)

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