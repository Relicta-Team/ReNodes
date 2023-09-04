import os
import random
from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtCore, QtGui
from NodeGraphQt import NodeGraph, BaseNode,GroupNode


class RuntimeNode(BaseNode):

	# unique node identifier domain.
	__identifier__ = 'runtime_domain'

	# initial default node name.
	NODE_NAME = 'Default name'

	def __init__(self):
		super(RuntimeNode, self).__init__()


class RuntimeGroup(GroupNode):
	__identifier__ = 'runtime_domain'
	