from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


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