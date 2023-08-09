import os
import random
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore, QtGui
from NodeGraphQt import NodeGraph, BaseNode


class RuntimeNode(BaseNode):

	# unique node identifier domain.
	__identifier__ = 'runtime_domain'

	# initial default node name.
	NODE_NAME = 'Default name'

	#custom node data
	metadata = {}

	def __init__(self):
		super(RuntimeNode, self).__init__()


	#TODO add events addStringInput, addCheckbox, event listener etc

	def addStringInput(self, name, label='', text='', tab=None):
		self.add_text_input(name, label, text, tab)
		self.update()

	def addCheckboxInput(self,name, label='', text='', state=False, tab=None):
		self.add_checkbox(name, label, text, state, tab)
		self.update()

	def addComboboxInput(self,name, label='', items=None, tab=None):
		self.add_combo_menu(name, label, items, tab)

	