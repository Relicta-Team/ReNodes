import os
import random
import re
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore, QtGui
from NodeGraphQt import NodeGraph, BaseNode,GroupNode
from Qt import QtCore
from NodeGraphQt.base.port import Port
from ReNode.app.NodeFactory import *

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

	#
	def _calculate_autoport_type(self,sourceType:str,libCalculator:dict):
		if not libCalculator: return sourceType

		#libCalculator['typeget'] -> @type(for all), @typeref(for typeref (array,dict etc)), @value.1, @value.2
		typeinfo = re.findall('\w+',sourceType)
		getter = libCalculator['typeget']
		if getter == '@type':
			return sourceType
		elif getter == '@typeref':
			return typeinfo[0]
		elif getter == '@value.1' and len(typeinfo) > 1:
			return typeinfo[1]
		elif getter == '@value.2' and len(typeinfo) > 2:
			return typeinfo[2]
		else :
			raise Exception(f"Invalid type getter {getter}; Source type info {typeinfo}")
		
	def onAutoPortConnected(self,src_port_info : Port, fact : NodeFactory):
		clr = src_port_info.view.color
		brdclr = src_port_info.view.border_color
		tp = src_port_info.view.port_typeName
		data = fact.getNodeLibData(self.nodeClass)

		anySet = False
		for name, port in self.inputs().items():
			if port.view.port_typeName == '':
				if not anySet:
					anySet = True
					self.set_property("autoportdata",{
						"color": port.view.color,
						"border_color": port.view.border_color
					})
				port.view.color = clr
				port.view.border_color = brdclr
				port.view.port_typeName = self._calculate_autoport_type(tp,data['inputs'].get(name))
				port.view.update()
				port.view._syncTooltip()


		for name, port in self.outputs().items():
			if port.view.port_typeName == '':
				if not anySet:
					anySet = True
					self.set_property("autoportdata",{
						"color": port.view.color,
						"border_color": port.view.border_color
					})
				port.view.color = clr
				port.view.border_color = brdclr
				port.view.port_typeName = self._calculate_autoport_type(tp,data['outputs'].get(name))
				port.view.update()
				port.view._syncTooltip()

	def onAutoPortDisconnected(self):
		pass


class RuntimeGroup(GroupNode):
	__identifier__ = 'runtime_domain'
	