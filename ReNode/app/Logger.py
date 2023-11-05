from PyQt5.QtGui import QTextDocument
import sys
from typing import Any
import logging
from bs4 import BeautifulSoup

class StdOutLoggerHandler(logging.StreamHandler):
    def __init__(self, stream):
        self.doc = QTextDocument()
        super().__init__(stream)
    
    def emit(self, record):
        try:
            msg = self.format(record)
            #msg = msg.replace('\t', '&nbsp;' * 4)
            #msg = msg.replace('\n', '<br/>')
            #self.doc.setHtml(msg)
            #msg = self.doc.tex
            msg = BeautifulSoup(msg, 'html.parser').text
            
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

class OutputLoggerHandler(logging.Handler):
    def __init__(self, console, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = console

    def emit(self, record):
        if self and self.widget:
            message = self.format(record)
            self.widget.addLog(message,record.levelname,record.name)
            

def RegisterLoggerStdoutHandler(logobject : logging.Logger):
    #stdout handler
    if len(logobject.handlers) == 0:
        stdout_hndl = StdOutLoggerHandler(sys.stdout) # logging.StreamHandler(sys.stdout) #
        stdout_hndl.setFormatter(logging.Formatter('[%(name)s::%(levelname)s] - %(message)s'))
        logobject.addHandler(stdout_hndl)

def getAllLoggers():
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    return loggers	

def registerConsoleLoggers(conref):
    for logobject in getAllLoggers():
        logobject.addHandler(OutputLoggerHandler(conref))

def RegisterLogger(logname="main"):
    logobject = logging.getLogger(logname)
    logobject.setLevel(logging.DEBUG)
    RegisterLoggerStdoutHandler(logobject)
    return logobject
