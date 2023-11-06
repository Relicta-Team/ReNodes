from PyQt5 import QtGui
from PyQt5.QtWidgets import QTextBrowser,QMainWindow,QTextEdit,QMessageBox,QAction,QCompleter,QListView,QMenu,QLabel, QDockWidget, QWidget, QHBoxLayout,QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QPixmap,QColor, QPainter
import logging
import re
from ReNode.app.Logger import RegisterLogger
from PyQt5.sip import *

class ClickableTextBrowser(QTextBrowser):
    clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super(ClickableTextBrowser, self).__init__(parent)
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)

    def mousePressEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor and anchor.startswith("ref::"):
            text = anchor.replace("ref::", "")
            self.clicked.emit(text)
        else:
            super().mousePressEvent(event)


class CmdInputLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(CmdInputLineEdit, self).__init__(parent)
    
    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == Qt.Key_Return:
            LoggerConsole.refObject.execute_command()
            return
        return super().keyPressEvent(a0)

class LoggerConsole(QDockWidget):    
	
    refObject = None

    def __init__(self):
        LoggerConsole.refObject = self
        super().__init__("Консоль")

        self.logger : logging.Logger = RegisterLogger("Console")

        self.log_text = ClickableTextBrowser() #QTextEdit()
        self.log_text.setReadOnly(True)
        self.command_input = CmdInputLineEdit()
        self.send_button = QPushButton("Отправить")

        self.messages = []
        self.maxMessages = 400

        def on_link_clicked(link):
            from ReNode.ui.NodeGraphComponent import NodeGraphComponent
            print("Node Link clicked:", link)
            graphObj = NodeGraphComponent.refObject.graph
            node = graphObj.get_node_by_id(link)
            if node:
                graphObj.clear_selection()
                node.set_selected(True)
                graphObj.viewer().center_selection([node.view])


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

    def syncActionText(self,initState=None):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent

        loggerAct = NodeGraphComponent.refObject.mainWindow.switchLoggerAction
        condition = self.isVisible()
        if initState:
            condition = initState
        newtext = "&Скрыть консоль" if condition else "&Показать консоль"
        if not condition:
            self.command_input.clearFocus()
        loggerAct.setText(newtext)

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
        fulltext = "<br/>".join(self.messages)
        fulltext = self.styleText + fulltext
        #fulltext = f'<pre>{fulltext}</pre>'
        
        if not self.log_text: return
        if isdeleted(self.log_text): return
        
        self.log_text.setHtml(fulltext)

        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

            

    def wrapNodeLink(nodeid,text=None,color='#17E62C'):
        if not text: text = nodeid
        return f'<a href="ref::{nodeid}" style="text-decoration: underline; white-space: pre-wrap; color: {color};">{text}</a>'

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
        self.completer_model :QStringListModel = QStringListModel()
        
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

    def execute_command(self):
        
        if self.command_completer.popup().isVisible(): 
            self.command_completer.popup().setVisible(False)
            #self.showStatusTipMessage("")
            #return
        
        # Получаем введенную команду
        command = self.command_input.text()
        
        # Очищаем поле ввода команды
        self.command_input.clear()
        
        cmdList = command.split(' ')
        if len(cmdList) == 0:
            return
        command = cmdList[0]
        args = []
        if len(cmdList) > 1:
            args = cmdList[1:]

        cmd = self._findCmdByName(command)
        if not cmd:
            self.logger.error(f"<span style=\"color:yellow\">Unknown command: {command}</span>")
            return
        # Выполняем команду (замените этот код на реальную логику выполнения команд)
        self.logger.debug(f"Executing command: {command} with args {args}")
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
        self._registerCommand(HelpCommand)
        self._registerCommand(SessionClipSaveCommand)
        self._registerCommand(SessionClipLoadCommand)

class ConsoleCommand:
    name = "default command"
    desc = "no description"
    def __init__(self,name=None,desc=None) -> None:
        if not name:
            name = self.__class__.name
        if not desc:
            desc = self.__class__.desc
        self.name = name
        self.desc = desc

        self.logger = LoggerConsole.refObject.logger
    
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

        if NodeGraphComponent.refObject:
            graph = NodeGraphComponent.refObject.graph
            data = QApplication.clipboard().text()
            if data:
                graph.loadGraphFromString(data,loadMousePos=True)
                self.logger.info("Данные загружены")