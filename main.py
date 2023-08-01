
import os
import random
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore, QtGui
from NodeGraphQt import NodeGraph, BaseNode
from Menu import menu_init
from Widgets import MainWindow

# create the widget wrapper that can be docked to the main window.
class NodeGraphPanel(QtWidgets.QDockWidget):
    """
    Widget wrapper for the node graph that can be docked to
    the main window.
    """

    def __init__(self, graph, parent=None):
        super(NodeGraphPanel, self).__init__(parent)
        self.setObjectName('nodeGraphQt.NodeGraphPanel')
        self.setWindowTitle('Редактор логики')
        self.setWidget(graph.widget)

class FooNode(BaseNode):

    # unique node identifier domain.
    __identifier__ = 'testident'

    # initial default node name.
    NODE_NAME = 'Foo Node'

    def __init__(self):
        super(FooNode, self).__init__()

        # create an input port.
        self.add_input('in', color=(180, 80, 0))

        # create an output port.
        self.add_output('out')

# create a simple test node class.
class TestNode(BaseNode):

    __identifier__ = 'nodes.silhouettefx'
    NODE_NAME = 'test node'

    def __init__(self):
        super(TestNode, self).__init__()
        self.add_input('in')
        self.add_output('out')


#define global variable
appName = "ReNode"
appVer = 0.1

app = QtWidgets.QApplication([])
#main_window = MainWindow.MainWindow()
#main_window.show()


# create the node graph controller and register our "TestNode"
graph = NodeGraph()
graph.register_node(TestNode)
graph.show()

graph.register_node(FooNode)
#create random 50 nodes 
for i in range(50):
    #random color
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    graph.create_node('testident.FooNode', name='Узел ' + str(i),color=color,pos=(random.randrange(-500,500), random.randrange(-500,500)))

main_window = QtWidgets.QMainWindow()
main_window.setWindowTitle(f"{appName} (v.{appVer})")


main_window.setWindowIcon(QtGui.QIcon('./data/pic.png'))
main_window.show()
main_window.setMenuBar(QtWidgets.QMenuBar())
main_window.setStyleSheet("background-color: #1F1F29; color: #FAFAFF;")

menu_init.initialize(main_window,app)

sfx_graph_panel = NodeGraphPanel(graph)
main_window.addDockWidget(QtCore.Qt.BottomDockWidgetArea,sfx_graph_panel)

graph = NodeGraph()
graph.register_node(TestNode)
graph.show()

graph.register_node(FooNode)
#create random 50 nodes 
for i in range(50):
    #random color
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    graph.create_node('testident.FooNode', name='Узел ' + str(i),color=color,pos=(random.randrange(-500,500), random.randrange(-500,500)))
main_window.addDockWidget(QtCore.Qt.TopDockWidgetArea,NodeGraphPanel(graph))
main_window.dockOptions()

app.exec_()