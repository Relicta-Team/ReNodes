from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

def loadStylesheet(filename: str):
    """
    Loads an qss stylesheet to the current QApplication instance

    :param filename: Filename of qss stylesheet
    :type filename: str
    """
    print('LOADING STYLE:', filename)
    file = QFile(filename)
    file.open(QFile.ReadOnly | QFile.Text)
    stylesheet = file.readAll()
    QApplication.instance().setStyleSheet(str(stylesheet, encoding='utf-8'))
    return str(stylesheet, encoding='utf-8')

def intTryParse(value):
    try:
        return int(value)
    except ValueError:
        return 0
    
def floatTryParse(value):
    try:
        return float(value)
    except ValueError:
        return 0.0
    
def boolTryParse(value):
    try:
        return bool(value)
    except ValueError:
        return False
    
def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n
    
def updateIconColor(icon : QIcon, color):
    size = icon.availableSizes()[0]
    pixmap = icon.pixmap(icon.actualSize(size))  # Указываете желаемый размер

    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return QIcon(pixmap)