import typing
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *
from PyQt5.QtWidgets import QWidget, QTreeWidget
import asyncio
from NodeGraphQt.widgets.tab_search import TabSearchLineEditWidget


class TabSearchMenu(QWidget):
    def __init__(self,parent=None):
        super(TabSearchMenu, self).__init__(parent)
        baseWidget = self
        self.move(0,0)
        baseWidget.setMinimumSize(500, 300+22)
        self.setVisible(False)
        #self.show()
        #self.setFocus()

        baseWidget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        #baseWidget.setStyleSheet('background-color: red;')

        data = ['folder1/file1', 'file2', 'file3', 'folder2/file4']
        for i in range(1,1000):
            data.append(f'fld/test/inside/button/num'+str(i))
        treeWidget = QTreeWidget(baseWidget)
        treeWidget.setColumnCount(1)
        treeWidget.move(0, 25)
        treeWidget.setMinimumSize(500, 300)
        treeWidget.setWindowTitle("NodeSearch")
        treeWidget.setHeaderHidden(True)
        #treeWidget.setDragEnabled(True)
        
        treeWidget.headerItem().setText(0,"Select node")

        self.line_edit = TabSearchLineEditWidget(baseWidget)
        self.line_edit.move(0, 0)
        self.line_edit.setMinimumWidth(410)

        self.contextSense = QRadioButton(baseWidget)
        self.contextSense.move(410,2)
        self.contextSense.setMinimumSize(30,22)
        self.contextSense.setMaximumSize(80,22)
        self.contextSense.setText("Контекст")

        self.edit = self.line_edit
        self.tree = treeWidget

        items = []
        for item in data:
            itemparts = item.split('/')

            entry = QTreeWidgetItem(None, [itemparts[0]])
            entry.setIcon(0,QtGui.QIcon('./data/function_sim.png'))
            partentitem = entry

            if len(itemparts) > 1:
                for i in itemparts[1:]:
                    childitem = QTreeWidgetItem(None, [i])
                    #childitem.setIcon(0,QtGui.QIcon('./data/branch_sim.png'))
                    partentitem.addChild(childitem)
                    partentitem = childitem

            items.append(entry)

        treeWidget.insertTopLevelItems(0, items)