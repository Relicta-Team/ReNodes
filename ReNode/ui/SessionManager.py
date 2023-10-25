import typing
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *
from Qt import QtWidgets, QtCore

class TabData:
    def __init__(self,name='',file='') -> None:
        self.filePath = file
        self.name = name
        self.serializedData = None
        self.isActive = False
        self.isUnsaved = True

    def __repr__(self) -> str:
        return f'{self.name} {hex(id(self))}'

class SessionManager(QTabWidget):
    def __init__(self,graph) -> None:
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

    def _initEvents(self):
        #self.currentChanged.connect(self.handleTabChange)
        self.tabCloseRequested.connect(self.handleTabClose)
        self.tabBarClicked.connect(self.handleTabChange)
        self.tabBar().tabMoved.connect(self.handleMoved)

    @property
    def tabData(self) -> list[TabData]:
        tdat = []

        for i in range(0,self.count() - 1):
            tdat.append(self.tabBar().tabData(i))
        return tdat

    def getTabData(self,index) -> TabData:
        return self.tabBar().tabData(index)

    def syncTabName(self,idx):
        tdata = self.getTabData(idx)
        unsafe = ""
        if tdata.isUnsaved:
            unsafe = "*"
        self.tabBar().setTabText(idx,f'{tdata.name}{unsafe}')

    def handleMoved(self,index):
        #print(f"moved to {index}")
        pass

    def newTab(self):
        idx = self.addTab(QWidget(),"tab")
        tabCtx = TabData("Новый граф")
        self.tabBar().setTabData(idx,tabCtx)
        self.syncTabName(idx)

    def openFile(self):
        pass

    def saveFile(self):
        pass

    def validateExit(self):
        if any([tab.isUnsaved for tab in self.tabData if tab.isUnsaved]):
            from ReNode.app.application import Application
            
            reply = QMessageBox.warning(self, 'Закрытие', f'Вы уверены, что хотите закрыть {Application.appName}?\nВсе несохраненные данные будут утеряны.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            return reply == QMessageBox.Yes
        return True

    def registerFileWatch(self,path):
        import os
        fs_watcher = QtCore.QFileSystemWatcher()
        fs_watcher.addPath(os.path.abspath(path))
        #print fws files
        fs_watcher.fileChanged.connect(path)
        fs_watcher.file
        return fs_watcher

    def handleTabChange(self, index):
        print(f'Активная вкладка изменилась на {index} {self.getTabData(index)}')

    def handleTabClose(self, index):
        tabData = self.getTabData(index)
        if tabData.isUnsaved:
            # В этом методе вы можете запросить подтверждение пользователя перед закрытием вкладки
            reply = QMessageBox.question(self, 'Закрыть вкладку', 'Вы уверены, что хотите закрыть эту вкладку?\nВсе несохраненные данные будут утеряны.',
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