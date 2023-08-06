from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore, QtGui
from PyQt5 import *

import NodeGraphQt



class NodeGraphPanel(QDockWidget):
    """
    Widget wrapper for the node graph that can be docked to
    the main window.
    """

    def __init__(self, graph : NodeGraphQt.NodeGraph, parent=None):
        super(NodeGraphPanel, self).__init__(parent)
        self.setObjectName('nodeGraphQt.NodeGraphPanel')
        self.setWindowTitle('Редактор логики')
        self.setWidget(graph.widget)