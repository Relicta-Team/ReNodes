import typing
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *
from PyQt5.QtWidgets import QWidget, QTreeWidget
import asyncio
from NodeGraphQt.constants import ViewerEnum, ViewerNavEnum
from NodeGraphQt.widgets.tab_search import TabSearchLineEditWidget


class TabSearchMenu(QWidget):
    def __init__(self,parent=None):
        super(TabSearchMenu, self).__init__(parent)
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
        self.edit = TabSearchLineEditWidget(baseWidget)
        self.edit.setPlaceholderText("Поиск")
        self.edit.move(1, ofsY)
        self.edit.setMinimumSize(inputX,34)
        self.edit.setMaximumSize(inputX,34)

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
            "Операторы" : {
                "Контрольные струкутры": {
                    "Ветка",
                    "Цикл",
                    "",
                },
                "Отладка" : {
                    "Тестовый оператор",
                    "Система"
                }
            },
            "Список": {
                "Создать",
                "Очистить"
            },
            "Строки": {
                "Создать",
                "Разделить"
            },
            "Элементы": "Создать элемент"
        }
        self.build_tree(test)
        """data = ['folder1/file1', 'file2', 'file3', 'folder2/file4']
        for i in range(1,1000):
            data.append(f'fld/test/num'+str(i))
        items = []
        for item in data:
            itemparts = item.split('/')

            entry = QTreeWidgetItem(None, [itemparts[0]])
            entry.setIcon(0,QtGui.QIcon('./data/function_sim.png'))
            partentitem = entry

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
    
    def build_tree(self,data : dict):
        data = dict or {}
        return
        
        toplvl = []
        for k,v in data.items():
            entry = QTreeWidgetItem(None, [k])
            toplvl.append(entry)
            print(f'parsetop: {k}')
            if v:
                self._build_recrusive(entry,v)

        self.tree.insertTopLevelItems(0,toplvl)

    def _build_recrusive(self,parent,vdict):
        for key,val in vdict.items():
            print(f'parse inside: {key}')
            itm = QTreeWidgetItem(None, key)
            parent.addChild(itm)
            if val:
                self._build_recrusive(itm,val)

    def setText(self,data):
        self.text.setText(f'<p style=\"font-size:20px;padding: 2% 2%;\">{data}</p>')
