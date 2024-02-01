from PyQt5 import QtGui
from PyQt5.QtWidgets import QTextBrowser,QMainWindow,QTextEdit,QMessageBox,QAction,QCompleter,QListView,QMenu,QLabel, QDockWidget, QWidget, QHBoxLayout,QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QDialog, QDialogButtonBox
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QPixmap,QColor, QPainter
import logging
import re
from ReNode.app.Logger import RegisterLogger
from PyQt5.sip import *
from PyQt5.QtCore import QTimer

class ClickableTextBrowser(QTextBrowser):
    clicked = pyqtSignal(str,object)

    def __init__(self, parent=None):
        super(ClickableTextBrowser, self).__init__(parent)
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)

    def mousePressEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor:
            if anchor.startswith("ref::"):
                text = anchor.replace("ref::", "")
                self.clicked.emit("ref",text)
            elif anchor.startswith("gref::"):
                patterns = anchor.replace("gref::", "").split(":")
                self.clicked.emit("gref",patterns)
            elif anchor.startswith("errinfo::"):
                patterns = anchor.replace("errinfo::", "").split(":")
                self.clicked.emit("errinfo",patterns)
        else:
            super().mousePressEvent(event)

class NewWindow(QDialog):
    def __init__(self, classType, objRef):
        super().__init__()

        self.setWindowTitle("Описание")  # Установите заголовок окна
        self.setWindowIcon(QIcon("data/icon.ico"))  # Установите иконку окна
        self.setWindowModality(Qt.ApplicationModal)  # Установите модальность окна на уровне приложения
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout()

        text_browser = QTextBrowser()
        text_browser.setOpenLinks(False)
        text_browser.setOpenExternalLinks(False)

        exTxt = objRef.getMoreExceptionInfo()
        text_browser.setHtml(exTxt)
        
        layout.addWidget(text_browser)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.setFixedSize(700,500)

class CmdInputLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(CmdInputLineEdit, self).__init__(parent)
        self.stackCommands = []
        self.maxStackCommands = 1000
        self.cmdIndex = 0
        self._enableHistory = False
    
    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key_Return:
            LoggerConsole.refObject.execute_command()
            self.stackCommands.append(self.text())
            if len(self.stackCommands) > self.maxStackCommands:
                self.stackCommands.pop(0)
            self.cmdIndex = len(self.stackCommands)
            return
        if self._enableHistory and a0.key() == Qt.Key_Up and not LoggerConsole.refObject.command_completer.popup().isVisible():
            self.cmdIndex -= 1
            if self.cmdIndex < 0:
                self.cmdIndex = 0
            self.setText(self.stackCommands[self.cmdIndex])
            return
        if self._enableHistory and a0.key() == Qt.Key_Down and not LoggerConsole.refObject.command_completer.popup().isVisible():
            self.cmdIndex += 1
            if self.cmdIndex >= len(self.stackCommands):
                self.cmdIndex = len(self.stackCommands)
                self.setText("")
            else:
                self.setText(self.stackCommands[self.cmdIndex])
            return
        self.cmdIndex = len(self.stackCommands)
        return super().keyPressEvent(a0)

class LoggerConsole(QDockWidget):    
	
    refObject = None

    def __init__(self):
        LoggerConsole.refObject = self
        super().__init__("Консоль")

        self.logger : logging.Logger = RegisterLogger("Console")

        self.log_text = ClickableTextBrowser() #QTextEdit()
        self.log_text.setReadOnly(True)
        #self.log_text.setMinimumHeight(20)
        self.command_input = CmdInputLineEdit()
        self.send_button = QPushButton("Отправить")

        self.messages = []
        self.maxMessages = 1024*2

        self.visibilityChanged.connect(self.update)

        # debug messages
        #for i in range(self.maxMessages):
        #    self.messages.append(f'Тест сообщение {i}')

        def on_link_clicked(clickType,args):
            from ReNode.ui.NodeGraphComponent import NodeGraphComponent
            print(f"Node Link clicked ({clickType}): {args}")
            if clickType == "ref":
                graphObj = NodeGraphComponent.refObject.graph
                node = graphObj.get_node_by_id(args)
                if node:
                    graphObj.clear_selection()
                    node.set_selected(True)
                    graphObj.viewer().center_selection([node.view])
            elif clickType == "gref":
                try:
                    graphId = args[0]
                    nodeUid = int(args[1])
                    tabMgr = NodeGraphComponent.refObject.sessionManager
                    curTabDat = None
                    for t in tabMgr.getAllTabs():
                        if hex(id(t.graph)) == graphId:
                            curTabDat = t
                    if not curTabDat: return
                    tabMgr.setActiveTab(curTabDat.getIndex())
                    for node in curTabDat.graph.all_nodes():
                        if node.uid == nodeUid:
                            graphObj = curTabDat.graph
                            graphObj.clear_selection()
                            node.set_selected(True)
                            graphObj.viewer().center_selection([node.view])
                except Exception as e:
                    self.logger.error(f"Ошибка перехода к {graphId}->{nodeUid}: {e}")
                    return
            elif clickType == "errinfo":
                try:
                    from gc import get_objects
                    address = int(args[1])
                    objList = [o for o in get_objects() if address == id(o)]

                    if len(objList) > 1: raise Exception("Too much objects at address " + address)
                    if not objList:
                        self.logger.warning("Не удалось открыть описание - информация не актуальна.")
                        return

                    wind = NewWindow(args[0],objList[0])
                    wind.exec_()
                    
                except Exception as e:
                    self.logger.error(f"Ошибка открытия окна описания {clickType}: {args}")
                    return


        text_browser = self.log_text
        text_browser.setOpenExternalLinks(False)
        text_browser.setOpenLinks(False)
        text_browser.setWordWrapMode(QtGui.QTextOption.WordWrap)
        text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #text_browser.setLineWrapMode(QTextBrowser.NoWrap)
        text_browser.clicked.connect(on_link_clicked)
        
        text_browser.setStyleSheet('''
            QTextBrowser {
                font-family: "Consolas";
                font-size: 14px;
                padding: 1px;
            }

            a {
                text-decoration: underline;
                color: yellow;
            }

            a:hover {
                color: yellow;
            }
                                   
            
            
            ''')
        self.init_ui()

        self.styleText = f'''
        <style>
            pre {{
                white-space: wrap;
            }}
        </style>
        '''

    dictColorCat = {
        "INFO": "white",
        "WARNING": "#E6E202",
        "ERROR": "#D60000",
        "CRITICAL": "red",
        "DEBUG": "blue",
    }

    def addLog(self, text,levelname="INFO",logname=""):
        text = text.replace('\n', '<br/>')
        text = text.replace('\t', '&nbsp;' * 4)

        prefix = f"[{logname}::{levelname}]: "

        if levelname in self.dictColorCat:
            color = self.dictColorCat[levelname]
            prefix = f'<font color="{color}">{prefix}</font>'

        text = prefix + text

        self.messages.append(text)
        if len(self.messages) > self.maxMessages:
            self.messages.pop(0)
        
        # call in next frame
        if self.isVisible():
            if self.getGraphSystem().getFactory().loading: return
            QTimer.singleShot(0, self.update)

    def update(self):
        if not self.log_text: return
        if isdeleted(self.log_text): return
        self.log_text.setHtml(self.styleText + "<br/>".join(self.messages))
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def clearConsole(self):
        self.messages = []
        if not self.log_text: return
        if isdeleted(self.log_text): return
        self.log_text.setHtml(self.styleText + "")

    @staticmethod
    def wrapNodeLink(nodeid,text=None,color='#17E62C'):
        if not text: text = nodeid
        return f'<a href="ref::{nodeid}" style="text-decoration: underline; white-space: pre-wrap; color: {color};">{text}</a>'

    @staticmethod
    def createNodeLink(graphRef,nodeid,text=None,color='#17E62C'):
        if not text: text = nodeid
        return f'<a href="gref::{hex(id(graphRef))}:{nodeid}" style="text-decoration: underline; white-space: pre-wrap; color: {color};">{text}</a>'

    @staticmethod
    def createErrorDescriptionLink(typesearch,errobj,text='Подробнее',color='#17E62C'):
        addr = id(errobj)
        return f'<a href="errinfo::{typesearch}:{addr}" style="text-decoration: underline; white-space: pre-wrap; color: {color};">{text}</a>'

    def init_ui(self):
        widget = QWidget()
        layout = QVBoxLayout()

        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_text)
        layout.addLayout(log_layout)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.command_input)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        widget.setLayout(layout)
        self.setWidget(widget)

        #! now input in debug not enabled
        #log_layout.removeItem(input_layout)

        #self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.editingFinished.connect(lambda: self.showStatusTipMessage())

        self.command_completer = QCompleter(self)
        self.command_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.command_completer.setFilterMode(Qt.MatchContains)
        self.command_completer.setWrapAround(False)
        self.command_input.setCompleter(self.command_completer)
        def __onselectcmd(text):
            cmd = self._findCmdByName(text)
            if cmd:
                self.showStatusTipMessage(cmd.desc)
        
        #self.command_completer.activated.connect(lambda text: self.showStatusTipMessage(""))
        self.command_completer.highlighted.connect(__onselectcmd)
        
        self._commands = []
        self.completer_model :QSortFilterProxyModel = QStringListModel()
        self.command_completer.setModel(self.completer_model)
        self.command_completer.setCaseSensitivity(Qt.CaseInsensitive)

        self.send_button.clicked.connect(self.execute_command)

        #for i in range(1,1000):
            #cmd = ConsoleCommand(f'command {i}')
            #self._registerCommand(cmd)
        self._registerStandartCommands()

    def showStatusTipMessage(self,mes=""):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        NodeGraphComponent.refObject.mainWindow.statusBar().showMessage(mes)

    def getGraphSystem(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        return NodeGraphComponent.refObject

    def execute_command(self):
        
        if self.command_completer.popup().isVisible(): 
            self.command_completer.popup().setVisible(False)
            #self.showStatusTipMessage("")
            #return
        
        # Получаем введенную команду
        command = self.command_input.text()
        
        # Очищаем поле ввода команды
        self.command_input.clear()
        
        baseCmdData = command
        cmdname = ''
        args = [] 

        cmdList = command.split(' ')
        if len(cmdList) == 0:
            return
        cmdname = cmdList[0]
        if cmdname == '' or cmdname.strip(' ') == "":
            return
        if len(cmdList) > 1:
            args = cmdList[1:]

        cmd = self._findCmdByName(cmdname)
        if not cmd:
            self.logger.error(f"<span style=\"color:yellow\">Unknown command: {cmdname}</span>")
            return
        
        if cmd.__class__.argsAsString:
            args = command.removeprefix(cmdname)

        # Выполняем команду (замените этот код на реальную логику выполнения команд)
        self.logger.debug(f"Executing command: {cmdname} with args {args}")
        cmd.onCall(args)

    def _registerCommand(self, command_type):
        command = command_type() if isinstance(command_type,type) else command_type
        self._commands.append(command)

        cmdlist = [f"{cmd.name}" for cmd in self._commands]
        self.completer_model.setStringList(cmdlist)
    
    def _findCmdByInfo(self,info):
        for cmd in self._commands:
            if cmd.getCmdInfo() == info:
                return cmd.name
        return ""
    
    def _findCmdByName(self,name):
        for cmd in self._commands:
            if cmd.name == name:
                return cmd
        return None

    def _registerStandartCommands(self):
        for class_ in ConsoleCommand.__subclasses__():
            self._registerCommand(class_)

# Обертка для вызова команд, например через QAction
class CommandDelegate:
    def __init__(self,object,args) -> None:
        self.cls = object
        self.args = args
    def __call__(self):
        return self.cls.refObject.onCall(self.args)


class ConsoleCommand:
    name = ""
    desc = "no description"
    argsAsString = False
    refObject = None
    def __init__(self,name=None,desc=None) -> None:
        self.__class__.refObject = self

        if not name:
            _name = self.__class__.name
            if _name == "":
                _name = self.__class__.__name__
                # split remove command from end name (if exists)
                if _name.endswith("Command"):
                    _name = _name.rstrip("Command")
                
                # change command: split words and add _ (example: TestCall -> test_call)
                name = '_'.join(re.findall(r'[A-Z][^A-Z]*', _name)).lower()
            else:
                name = _name
        if not desc:
            desc = self.__class__.desc
        self.name = name
        self.desc = desc


        self.logger = LoggerConsole.refObject.logger
    
    def getCommandDelegate(class_,args = None):
        """
            Возвращает делегат для команды
            class_ - класс команды
            args - аргументы команды
        """
        if not issubclass(class_,ConsoleCommand):
            return None
        return CommandDelegate(class_,args)

    def getCmdInfo(self):
        return f'{self.name} - {self.desc}'

    def getLoggerInstance(self) -> LoggerConsole:
        return LoggerConsole.refObject

    def onCall(self,args):
        pass

class HelpCommand(ConsoleCommand):
    name = "help"
    desc = "Выводит описание всех доступных команд"

    def onCall(self,args):
        cmdData = "\tДоступные комадны:"
        for cmd in self.getLoggerInstance()._commands:
            cmdData += f'\n\t{cmd.name} - {cmd.desc}'
        self.logger.info(f'<span style="color:lightblue">{cmdData}</span>')

class ClearConsoleCommand(ConsoleCommand):
    desc = "Очищает консоль"
    def onCall(self,args):
        self.getLoggerInstance().clearConsole()

class GetConsoleMessageCount(ConsoleCommand):
    desc = "Возвращает количество сообщений в консоли"
    def onCall(self,args):
        self.logger.info(f'Количество сообщений в консоли: {len(self.getLoggerInstance().messages)}')

class SaveConfig(ConsoleCommand):
    name = "save_config"
    desc = "Сохраняет конфигурацию в файл"
    def onCall(self,args):
        from ReNode.app.config import Config
        Config.saveConfig()

class SessionClipSaveCommand(ConsoleCommand):
    name = "clip_save"
    desc = "Сохраняет сессию в буфер обмена"
    def onCall(self,args):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        if NodeGraphComponent.refObject:
            graph = NodeGraphComponent.refObject.graph
            nodes = graph.all_nodes()
            data = graph.serializedGraphToString(graph._serialize(nodes,serializeMouse=True))
            if data:
                from PyQt5.QtWidgets import QApplication
                QApplication.clipboard().setText(data)
                self.logger.info("Данные сохранены")

class SessionClipLoadCommand(ConsoleCommand):
    name = "clip_load"
    desc = "Загружает сессию из буфера обмена"
    def onCall(self,args):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        from PyQt5.QtWidgets import QApplication
        
        raise NotImplementedError()
    
        if NodeGraphComponent.refObject:
            graph = NodeGraphComponent.refObject.graph
            data = QApplication.clipboard().text()
            if data:
                graph.loadGraphFromString(data,loadMousePos=True)
                NodeGraphComponent.refObject.variable_manager.loadVariables(graph.variables)
                self.logger.info("Данные загружены")

class EvalCodeCommand(ConsoleCommand):
    name = "run"
    desc = "Отладочное выполнение кода"
    argsAsString = True
    def onCall(self,args):
        code = args
        try:
            from sys import getsizeof
            evalueated = eval(code,globals(),locals())
            self.logger.debug(f"ret:{evalueated}")
        except Exception as e:
            self.logger.error(f"exept:{e}")

class GetVisualInfoCommand(ConsoleCommand):
    name = "get_visual_info"
    desc = "Получает информацию о созданных виджетах и окнах в приложении"

    def onCall(self,args):
        from ReNode.app.application import Application
        qapp = Application.refObject.appInstance
        self.logger.info(f'Все - виджетов {len(qapp.allWidgets())}; окон {len(qapp.allWindows())};')
        self.logger.info(f'Верх - виджетов {len(qapp.topLevelWidgets())}; окон {len(qapp.topLevelWindows())}')

class JumpToNodeCommand(ConsoleCommand):
    name = "jump_to_node"
    desc = "Перемещает сцену к указанному узлу. Вызов команды без аргументов отобразит количество узлов в сцене"
    argsAsString = True
    def onCall(self,args):
        try:
            from ReNode.ui.NodeGraphComponent import NodeGraphComponent
            if NodeGraphComponent.refObject:
                graph = NodeGraphComponent.refObject.graph
                nodeList = graph.all_nodes()
                if not args:
                    self.logger.info("Узлов: " + str(len(nodeList)))
                    return
                curIdx = int(args.replace(' ',''))
                #clamping in range
                curIdx = max(0,min(len(nodeList)-1,curIdx))
                for idx,n in enumerate(nodeList):
                    if idx == curIdx:
                        graph.viewer().center_selection([n.view])
                        break
        except Exception as e:
            self.logger.error(f"Ошибка перехода:{e}")

class DumpLib(ConsoleCommand):
    name = "dump_lib"
    desc = "Дамп библиотеки в json. Агрументы (могут быть комбинированы): classes, nodes"
    def onCall(self,args):
        import json
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        if not args:
            args = ['classes','nodes']
        def default(obj):
            if isinstance(obj, set):
                return list(obj)
            if callable(obj):
                return obj.__name__
            return obj
        
        for arg in args:
            if arg in ["classes","nodes"]:
                with open("_dump_"+arg+".json", 'w',encoding='utf-8') as file_out:
                    json.dump(
                        getattr(NodeGraphComponent.refObject.getFactory(),arg),
                        file_out,
                        indent=2,
                        separators=(',', ':'),
                        default=default,
                        ensure_ascii=False
                    )
            else:
                self.logger.error("Неизвестный агрумент " + arg)
                continue

#region Memory helpers -  https://docs.python.org/3/library/tracemalloc.html#module-tracemalloc
class StartTracemalloc(ConsoleCommand):
    name = "start_mem_info"
    desc = "Запуск отслеживания памяти"

    def onCall(self,args):
        import tracemalloc
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        tracemalloc.start()

class StopTracemalloc(ConsoleCommand):
    name = "stop_mem_info"
    desc = "Остановка отслеживания памяти"

    def onCall(self,args):
        import tracemalloc
        tracemalloc.stop()


class GetTraceSnapshot(ConsoleCommand):
    name = "get_mem_info"
    desc = "Вывод строк с информацией о памяти"
    argsAsString = True
    def onCall(self,args):
        import tracemalloc
        
        if not tracemalloc.is_tracing():
            self.logger.warning("Tracemalloc не запущен")
            return

        if not args:
            args = 10
        else:
            args = max(int(args),1)

        import tracemalloc
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        for stat in top_stats[:min(args, len(top_stats))]:
            stat = str(stat).replace("<",'&lt;').replace('>','&gt;')
            self.logger.info(stat)

#endregion