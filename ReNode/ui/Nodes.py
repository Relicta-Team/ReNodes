import os
import random
import re
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore, QtGui
from NodeGraphQt import NodeGraph, BaseNode,GroupNode
from Qt import QtCore
from NodeGraphQt.base.port import Port
from NodeGraphQt.constants import PortTypeEnum
from NodeGraphQt.qgraphics.port import PortItem
from ReNode.app.NodeFactory import *

class RuntimeNode(BaseNode):

	# unique node identifier domain.
	__identifier__ = 'runtime_domain'

	# initial default node name.
	NODE_NAME = 'Default name'

	def __init__(self):
		super(RuntimeNode, self).__init__()

	def on_input_connected(self, in_port, out_port):
		if in_port.name() in self.widgets():
			wid = self.widgets()[in_port.name()]
			wid.get_custom_widget().setEnabled(False)
			wid.get_custom_widget().setVisible(False)
			wid.widget()._connectedPort = True
			wid.widget().setTitleAlign('port')
			#wid.widget().setWindowOpacity(0.2)		
		super(RuntimeNode,self).on_input_connected(in_port, out_port)
		return

	def on_input_disconnected(self, in_port, out_port):
		if in_port.name() in self.widgets():
			wid = self.widgets()[in_port.name()]
			wid.get_custom_widget().setEnabled(True)
			wid.get_custom_widget().setVisible(True)
			alignval = "left" if in_port.view.port_type == PortTypeEnum.IN.value else "right"
			wid.widget()._connectedPort = False
			wid.widget().setTitleAlign(alignval)
			#wid.widget().setWindowOpacity(1)
		super(RuntimeNode,self).on_input_connected(in_port, out_port)
		return

	def getFactoryData(self):
		from ReNode.ui.NodeGraphComponent import NodeGraphComponent
		return NodeGraphComponent.refObject.getFactory().getNodeLibData(self.nodeClass)

	def isAutoPortNode(self):
		return self.has_property('autoportdata')
	
	def isAutoPortPrepared(self):
		if self.isAutoPortNode():
			return len(self.get_property('autoportdata')) > 0
		else:
			return False

	def canConnectAutoPort(self,fromPort : PortItem,toPort : PortItem):
		if fromPort.port_typeName != "": return False
		if toPort.port_typeName == "": return False
		if "Exec" in [fromPort.port_typeName,toPort.port_typeName]: return False

		data = self.getFactoryData()
		portDataName = "inputs" if fromPort.port_type == PortTypeEnum.IN.value else "outputs"
		evalType = self._calculate_autoport_type(toPort.port_typeName,data[portDataName].get(fromPort.name))

		if evalType != toPort.port_typeName:
			return False

		equalDataTypes = self._calculate_autoport_type(toPort.port_typeName,data[portDataName].get(fromPort.name),True)

		if not equalDataTypes:
			return False

		return True

	#
	def _calculate_autoport_type(self,sourceType:str,libCalculator:dict,chechDatatype=False):
		if not libCalculator: return sourceType

		#libCalculator['typeget'] -> @type(for all), @typeref(for typeref (array,dict etc)), @value.1, @value.2

		getterData = libCalculator['typeget']
		dataType,getter = getterData.split(';')

		if not re.findall('[\[\]\,]',sourceType):
			preSource = sourceType
			sourceType = f'{dataType}[{sourceType}]'
			if dataType == "value":
				sourceType = preSource

		typeinfo = re.findall('\w+\^?',sourceType)
		
		if chechDatatype:
			return dataType == typeinfo[0]

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
		
	def onAutoPortConnected(self,src_port_info : Port):
		clr = src_port_info.view.color
		brdclr = src_port_info.view.border_color
		tp = src_port_info.view.port_typeName
		data = self.getFactoryData()

		anySet = False
		for name, port in self.inputs().items():
			if port.view.port_typeName == '':
				if not anySet:
					anySet = True
					self.set_property("autoportdata",{
						"color": port.view.color,
						"border_color": port.view.border_color
					},False)
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
					},False)
				port.view.color = clr
				port.view.border_color = brdclr
				port.view.port_typeName = self._calculate_autoport_type(tp,data['outputs'].get(name))
				port.view.update()
				port.view._syncTooltip()

		if anySet:
			self.update_icon_part_color(0,QtGui.QColor(*clr),False)

	def onAutoPortDisconnected(self,src_port_info : Port):
		# Задача: если все порты, указанные в библиотеке отключены - сбросить цвет и тип
		#tp = src_port_info.view.port_typeName
		data = self.getFactoryData()
		portList = []
		for name,port in self.inputs().items():
			# Узнаем является порт автоматическим
			if data['inputs'].get(name) and data['inputs'].get(name).get("type") == "":
				# Если порт не подключен коллекционируем, иначе выходим
				if len(port.view.connected_ports) == 0:
					portList.append(port)
				else:
					return
				
		for name,port in self.outputs().items():
			# Узнаем является порт автоматическим
			if data['outputs'].get(name) and data['outputs'].get(name).get("type") == "":
				# Если порт не подключен коллекционируем, иначе выходим
				if len(port.view.connected_ports) == 0:
					portList.append(port)
				else:
					return

		data = self.get_property('autoportdata')
		self.set_property("autoportdata",{},False)
		self.update_icon_part_color(0,None,False)
		for port in portList:
			port.color = data['color']
			port.border_color = data['border_color']
			port.view.port_typeName = ''
			port.view.update()
			port.view._syncTooltip()

		pass
	
	def update_icon_part_color(self,index=0,clr=None,push_undo=True):
		dat = self.icon()
		if not isinstance(dat,list):
			dat = [dat,None]
		dat[index+1] = clr
		#validation: if 2 items and color is none 
		if len(dat) == 2 and dat[1] is None:
			dat = dat[0]
		self.set_icon(dat,push_undo)

	def update_icon_part_picture(self,index=0,picture=None,push_undo=True):
		dat = self.icon()
		if not isinstance(dat,list):
			dat = [dat,None]
		dat[index] = picture
		if len(dat) == 2 and dat[1] is None:
			dat = dat[0]
		self.set_icon(dat,push_undo)

	def update_icon_parts(self,parts,push_undo=True):
		
		if not isinstance(parts,list):
			parts = [parts,None]
		
		if len(parts)%2 != 0:
			raise Exception(f"(update_icon_parts) - parts must be even: {parts}")
		for i in range(0,len(parts),2):
			if not isinstance(parts[i],str):
				raise Exception(f"(update_icon_parts) - part picture (index {i}) must be string: <{parts[i]}>")
			clr = parts[i+1]
			if not isinstance(clr,QtGui.QColor) and not isinstance(clr,str):
				raise Exception(f"(update_icon_parts) - part color (index {i+1}) must be color or string: <{clr}>")
		
		self.set_icon(parts,push_undo)

	def set_icon_part_count(self,count,push_undo=True):
		raise NotImplementedError("TODO: implement set_icon_part_count")
		if count <= 1:
			raise Exception("(set_icon_part_count) - Count must be greater than 1")
		dat = self.icon()
		if not isinstance(dat,list):
			dat = [dat,None]
		for i in range(0,count):
			dat.append("")
			dat.append(None)
		self.set_icon(dat,push_undo)

	#region Ошибки
	def setErrorText(self,text="",head=None):
		self.view.setErrorText(text,head)
	
	def addErrorText(self,text="",head=None):
		self.view.addErrorText(text,head)

	def resetError(self):
		self.view.resetError()

	#endregion

class RuntimeGroup(GroupNode):
	__identifier__ = 'runtime_domain'
	