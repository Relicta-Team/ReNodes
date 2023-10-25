import typing
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from Qt import QtWidgets, QtCore

class TabData:
    def __init__(self) -> None:
        self.filePath = ""
        self.name = ""
        self.serializedData = None
        self.isActive = False
        self.isUnsaved = False

class SessionManager(QTabWidget):
    def __init__(self,graph,dock) -> None:
        super().__init__()
        
        self.graphSystem = graph

        self.setMovable(True)  # Разрешите перетаскивание вкладок.
        self.setTabsClosable(True)

        # Устанавливаем политику размеров для растяжения в вертикальном направлении.
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Изменяем минимальную высоту вкладки.
        self.tabBar().setMinimumHeight(50)  # Измените значение по вашему усмотрению.
        
        # Создайте и добавьте вкладки в верхнюю док-зону.
        #for i in range(1,20):
        #    self.addTab(QWidget(), 'Вкладка ' + str(i))

        self._initEvents()
        self.tabData : list[TabData] = [] #TODO replace to property and calculate tabs runtime

    def _initEvents(self):
        #self.currentChanged.connect(self.handleTabChange)
        self.tabCloseRequested.connect(self.handleTabClose)
        self.tabBarClicked.connect(self.handleTabChange)
        self.tabBar().tabMoved.connect(self.handleMoved)

    def handleMoved(self,index):
        print(f"moved to {index}")

    def newTab(self):
        idx = self.addTab(QWidget(),"tab")
        tabCtx = TabData()
        self.tabData.insert(idx,tabCtx)
        self.tabBar().setTabData(idx,tabCtx)

    def handleTabChange(self, index):
        print(f'Активная вкладка изменилась на {index}')

    def handleTabClose(self, index):
        # В этом методе вы можете запросить подтверждение пользователя перед закрытием вкладки
        reply = QMessageBox.question(self, 'Закрыть вкладку', 'Вы уверены, что хотите закрыть эту вкладку?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.removeTab(index)

    def showContextMenu(self):
            menu = QMenu(self)

            # Создайте действия для каждой вкладки
            for i in range(self.count()):
                action = QAction(self.tabText(i), self)
                action.triggered.connect(lambda checked, index=i: self.switchToTab(index))
                menu.addAction(action)

            # Отобразите контекстное меню рядом с кнопкой внутри док-зоны
            self.dock.setWidget(self)
            menu.exec_(self.context_menu_button.mapToGlobal(self.context_menu_button.rect().bottomRight()))
    
    def switchToTab(self, index):
        self.setCurrentIndex(index)