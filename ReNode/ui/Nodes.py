import os
import random
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore, QtGui
from NodeGraphQt import NodeGraph, BaseNode,GroupNode
from Qt import QtCore
from NodeGraphQt.base.port import Port

class RuntimeNode(BaseNode):

	# unique node identifier domain.
	__identifier__ = 'runtime_domain'

	# initial default node name.
	NODE_NAME = 'Default name'

	def __init__(self):
		super(RuntimeNode, self).__init__()
		self.onConnected : QtCore.Signal = QtCore.Signal(object,Port,Port)
		self.onDisconnected :QtCore.Signal = QtCore.Signal(object,Port,Port)

	def on_input_connected(self, in_port, out_port):
		if in_port.name() in self.widgets():
			wid = self.widgets()[in_port.name()]
			wid.get_custom_widget().setEnabled(False)
			wid.get_custom_widget().setVisible(False)
			#wid.widget().setWindowOpacity(0.2)		
		super(RuntimeNode,self).on_input_connected(in_port, out_port)
		return

	def on_input_disconnected(self, in_port, out_port):
		if in_port.name() in self.widgets():
			wid = self.widgets()[in_port.name()]
			wid.get_custom_widget().setEnabled(True)
			wid.get_custom_widget().setVisible(True)
			#wid.widget().setWindowOpacity(1)
		super(RuntimeNode,self).on_input_connected(in_port, out_port)
		return


class RuntimeGroup(GroupNode):
	__identifier__ = 'runtime_domain'
	