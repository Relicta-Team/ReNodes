from PyQt5 import QtGui
from PyQt5.QtWidgets import QTextBrowser,QMainWindow,QTextEdit,QMessageBox,QAction,QCompleter,QListView,QMenu,QLabel, QDockWidget, QWidget, QHBoxLayout,QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QPixmap,QColor, QPainter
import logging
import re

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


class LoggerWidget(QDockWidget):    
	
    def __init__(self):
        super().__init__("Консоль")

        self.log_text = ClickableTextBrowser() #QTextEdit()
        self.log_text.setReadOnly(True)
        self.command_input = QLineEdit()
        self.send_button = QPushButton("Отправить")

        self.messages = []
        self.maxMessages = 400

        def on_link_clicked(link):
            print("Link clicked:", link)
        text_browser = self.log_text
        text_browser.setOpenExternalLinks(False)
        text_browser.setOpenLinks(False)
        text_browser.setWordWrapMode(QtGui.QTextOption.WordWrap)
        text_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #text_browser.setLineWrapMode(QTextBrowser.NoWrap)
        text_browser.clicked.connect(on_link_clicked)
        
        text_browser.setStyleSheet('''
            QTextBrowser {
                font-family: "Consolas"; /* Шрифт, похожий на тот, что используется в терминале VS Code */
                font-size: 14px; /* Размер шрифта */
                padding: 1px; /* Отступы вокруг текста */
            }

            a {
                text-decoration: underline; /* Подчеркивание ссылок */
                color: yellow; /* Цвет ссылок (по умолчанию в VS Code) */
            }

            a:hover {
                color: yellow; /* Цвет ссылки при наведении (по умолчанию в VS Code) */
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
        loggerAct.setText(newtext)

    def addLog(self, text,levelname="INFO",logname=""):
        text = text.replace('\n', '<br/>')
        text = text.replace('\t', '&nbsp;' * 4)

        prefix = f"[{logname}::{levelname}]: "

        if levelname in self.dictColorCat:
            color = self.dictColorCat[levelname]
            prefix = f'<font color="{color}">{prefix}</font>'
        
        html_code = """
<tcode>
// Ваш код здесь
def my_function():
    return "Hello, World!"
</tcode>
"""

        text = prefix + text

        self.messages.append(text)
        if len(self.messages) > self.maxMessages:
            self.messages.pop(0)
        fulltext = "<br/>".join(self.messages)
        fulltext = self.styleText + fulltext
        #fulltext = f'<pre>{fulltext}</pre>'
        
        if not self.log_text: return
        
        self.log_text.setHtml(fulltext)

        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

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
        log_layout.removeItem(input_layout)