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