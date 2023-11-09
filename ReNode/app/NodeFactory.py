import json
from NodeGraphQt.nodes.base_node import BaseNode
from ReNode.app.Logger import *
from NodeGraphQt import (NodeGraph, GroupNode, NodeGraphMenu)
from ReNode.ui.NodePainter import draw_plus_port, draw_square_port,draw_triangle_port
import logging
import re
logger : logging.Logger = None
class NodeFactory:
	
	defaultColor = (13,18,23,255)

	def __init__(self):
		global logger
		logger = RegisterLogger("NodeFactory")
		
		self.graph = None

		self.version = 0
		self.nodes = {}
		self.loadFactoryFromJson("lib.json")
		pass

	def loadFactoryFromJson(self,file_path):
		logger.info(f"Loading factory from json file {file_path}")
		self.nodes = {}

		try:
			with open(file_path,encoding='utf-8') as data_file:
				layout_data = json.load(data_file)
		except Exception as e:
			layout_data = None
			logger.error('Cannot read data from file.\n{}'.format(e))

		if not layout_data:
			return
		
		self.deserializeLib(layout_data)
		
		def default(obj):
			if isinstance(obj, set):
				return list(obj)
			if callable(obj):
				return obj.__name__
			return obj
		logger.info(f"version lib {self.version}")
		with open("lib_output.json", 'w',encoding='utf-8') as file_out:
			json.dump(
				self.nodes,
				file_out,
				indent=2,
				separators=(',', ':'),
				default=default,
				ensure_ascii=False
			)
	
	def deserializeLib(self,data):
		sys = data["system"]
		self.version = sys["version"]

		#load nodes
		for nodecat,nodelist in data.get('nodes', {}).items():
			logger.info(f"Loading category: {nodecat}")
			for node,data in nodelist.items():
				logger.info(f"	Loading node '{node}'")
				self.registerNodeInLib(nodecat,node,data)


	def getColorByType(self,type_name,retAsQColor=False):
		from ReNode.ui.NodeGraphComponent import NodeGraphComponent
		varMgr = NodeGraphComponent.refObject.variable_manager

		if re.findall('[\[\]\,]',type_name):
			portType = f'array[{type_name}]'
			typeinfo = re.findall('\w+',portType)
			type_name = typeinfo[1]

		for objInfo in varMgr.variableTempateData:
			if objInfo.variableType == type_name:
				if retAsQColor:
					return objInfo.color
				else:
					return [objInfo.color.red(),objInfo.color.green(),objInfo.color.blue(),objInfo.color.alpha()]
		
		return NodeFactory.defaultColor

	# Синхронизирует цвета нодов в библиотеке с цветом типов 
	def updateLibTypes(self):
		from ReNode.ui.NodeGraphComponent import NodeGraphComponent
		if not NodeGraphComponent.refObject or not NodeGraphComponent.refObject.variable_manager:
			raise Exception(f"Graph component or variable manager not loaded: {NodeGraphComponent.refObject}; {NodeGraphComponent.variable_manager}")
		
		varMgr = NodeGraphComponent.refObject.variable_manager
		
		typecolor = {}
		for objInfo in varMgr.variableTempateData:
			clrList = [objInfo.color.red(),objInfo.color.green(),objInfo.color.blue(),objInfo.color.alpha()]
			typecolor[objInfo.variableType] = clrList

		isDefaultColor = None
		portType = None
		for val in self.nodes.values():
			if val['inputs']:
				for v in val['inputs'].values():
					portType = v['type']

					if re.findall('[\[\]\,]',portType):
						portType = f'array[{portType}]'
						typeinfo = re.findall('\w+',portType)
						portType = typeinfo[1]
					
					isDefaultColor = v['color']== list(NodeFactory.defaultColor) or v['color'] == [255,255,255,255]
					if portType in typecolor and isDefaultColor:
						v['color'] = typecolor[portType]
						v['border_color'] = None
			
			if val['outputs']:
				for v in val['outputs'].values():
					portType = v['type']

					if re.findall('[\[\]\,]',portType):
						typeinfo = re.findall('\w+',portType)
						portType = typeinfo[1]

					isDefaultColor = v['color']== list(NodeFactory.defaultColor) or v['color'] == [255,255,255,255]
					if portType in typecolor and isDefaultColor:
						v['color'] = typecolor[portType]
						v['border_color'] = None

	def registerNodeInLib(self,category,name,data : dict):
		
		if data.get('disabled',False): return
		
		struct = {}
		typename = category+"."+name
		defcolor = NodeFactory.defaultColor
		defborder = (255,0,0,255)
		kind = data.get('kind',None) # function,control,operator etc for define icon
		struct['name'] = data.get('name','')
		struct['path'] = data.get('path','')
		struct['desc'] = data.get('desc', '')
		struct['icon'] = self._nodeKindToIcon(kind)
		struct['color'] = data.get('color',defcolor)
		struct['border_color'] = data.get('border_color',defborder)
		struct['code'] = data.get('code',"")

		struct['runtime_ports'] = data.get('runtime_ports',False)

		struct['visible'] = data.get('isVisibleInLib',True)

		struct['states'] = data.get('states',[]) #list: event(as entrypoint), onlydebug etc... (for codegen)

		if self.nodes.get(typename):
			raise Exception(f"node {typename} already exists")
		
		#inputs generate
		struct['inputs'] = self._deserializeConnectors(data.get('inputs'),True)
		#outputs generate
		struct['outputs'] = self._deserializeConnectors(data.get('outputs'),False)

		#custom node options
		struct['options'] = self._deserializeOptions(data.get('options'))

		self.nodes[typename] = struct

	def _deserializeConnectors(self,cnts :dict,isInput = True):
		cons = {}
		
		if not cnts: return cons

		for key,val in cnts.items():
			defcolor = [255, 255, 255, 255]
			displayName = True
			isMulticonnect = False
			valdata = {}
			valdata['color'] = val.get('color',defcolor)
			valdata['display_name'] = val.get('display_name',displayName)
			valdata['mutliconnect'] = val.get('mutliconnect',isMulticonnect)
			valdata['style'] = self._kindPortStyle(val.get('style',"default"))
			valdata['allowtypes'] = val.get('allowtypes')
			valdata['type'] = val.get('type',key)
			valdata['typeget'] = val.get('typeget',"")
			if not isInput:
				valdata['accepted_paths'] = val.get('accepted_paths',["@any"])
			cons[key] = valdata
		return cons	

	def _deserializeOptions(self,cnts: dict):
		opts = {}
		if not cnts: return opts

		for key,val in cnts.items():
			valdat = {}
			
			typeopt = val.get('type')
			if not typeopt:
				raise Exception(f"no type for option {key}")
			
			for keyopt,valopt in val.items():
				valdat[keyopt] = valopt
			
			opts[key] = valdat
				
		return opts

	#region internal deserialize lib helpers
	_kindTypeIcons = {
		"function": "data\\function_sim.png",
		"event": "data\\function_sim.png"
	}
	def _nodeKindToIcon(self,kind):
		if kind is None:
			return None
		if "data\\" in kind.lower():
			return kind
		if not kind in self._kindTypeIcons:
			return None
		return NodeFactory._kindTypeIcons[kind]

	_kindPortStyleTypes = {
		"default": None,
		"triangle": 1,
		"square": 2
	}
	def _kindPortStyle(self,kind):
		return NodeFactory._kindPortStyleTypes.get(kind,0)
	
	def __getDrawPortFunction(self,number):
		if number == 1:return draw_triangle_port
		if number == 2:return draw_square_port
		return None

	#endregion

	#region factory instances

	def instance(self,nodename,graphref: NodeGraph = None,pos=None,isInstanceCreate=False,forwardDeserializeData=None):
		if not self.nodes.get(nodename): return None
		if not graphref: return None
		if not pos:
			pos_pre = graphref.viewer().scene_cursor_pos()
			pos = [pos_pre.x(),pos_pre.y()]
		graphref.undo_view.blockSignals(True)
		node = None
		
		cfg = self.nodes[nodename]
		
		if isInstanceCreate:
			#from ReNode.ui.Nodes import RuntimeNode
			node = graphref.node_factory.create_node_instance(nodename,customFactoryReference={'name':nodename})
		else:
			node = graphref.create_node(nodename,pos=pos,forwardedCustomFactory={'name':nodename},color=cfg.get('color'))
		
		node._graph = graphref #fix get graph from set_locked
		node.nodeClass = nodename
		node._view.nodeClass = nodename
		#node.create_property("class_",nodename)

		if "internal." in nodename:
			node.set_property("name",cfg["name"],False)
		else:
			nametext = f'<span style=\'font-family: Arial; font-size: 11pt;\'><b>{cfg["name"]}</b></span>'
			if cfg.get('desc')!="":
				nametext += f'<br/><font size=""4"><i>{cfg["desc"]}</i></font>'
			node.set_property("name",nametext,False,doNotRename=True)
			node.set_icon(cfg['icon'],False)

		if cfg.get('runtime_ports'):
			node.set_port_deletion_allowed(True)

		for inputkey,inputvals in cfg['inputs'].items():
			self.addInput(node,inputkey,inputvals)

		for outputkey,outputvals in cfg['outputs'].items():
			self.addOutput(node,outputkey,outputvals)
		
		#options
		for optname,optvals in cfg['options'].items():
			type = optvals['type']
			self.addProperty(node,type,optname,optvals)

		if isInstanceCreate:
			graphref.undo_view.blockSignals(False)
			return node
		
		node.update()
		graphref.undo_view.blockSignals(False)

		return node
	
	def addInput(self,node,inputkey,inputvals):
		port = node.add_input(
			name=inputkey,
			color=inputvals['color'],
			display_name=inputvals['display_name'],
			multi_input=inputvals['mutliconnect'],
			painter_func=self.__getDrawPortFunction(inputvals['style']),
			portType=inputvals.get('type')
		)
		#self._prepAccessPortTypes(node,port,inputvals,'out')

	def addOutput(self,node,outputkey,outputvals):
		port = node.add_output(
			name=outputkey,
			color=outputvals['color'],
			display_name=outputvals['display_name'],
			multi_output=outputvals['mutliconnect'],
			painter_func=self.__getDrawPortFunction(outputvals['style']),
			portType=outputvals.get('type')
		)
		#self._prepAccessPortTypes(node,port,outputvals,'in')

	def addProperty(self,node,type,optname,optvals):
		if type == "bool":
			node.add_checkbox(name=optname,text=optvals.get('text',""),label=optvals.get('label',""),state=optvals.get('default',False))
		if type=="input":
			node.add_text_input(name=optname,label=optvals.get('text',''),text=optvals.get('default',""))
		if type == "edit":
			node.add_multiline_text_input(name=optname,label=optvals.get('text',''),text=optvals.get('default',""))
		if type == "spin":
			node.add_spinbox(name=optname,label=optvals.get('text',''),text=optvals.get('default',0),range=optvals.get('range'))
		if type == "fspin":
			node.add_float_spinbox(name=optname,label=optvals.get('text',''),text=optvals.get('default',0),range=optvals.get('range'),floatspindata=optvals.get('floatspindata'))
		if type=="list":
			node.add_combo_menu(
				name=optname,label=optvals.get('text',''),items=optvals.get('values',[]),default=optvals.get('default'),
				disabledListInputs=optvals.get('disabledListInputs'),typingList=optvals.get('typingList'))
		if type=="vec2":
			node.add_vector2(name=optname,label=optvals.get('text',''),value=optvals.get('default',[0,0]))
		if type=="vec3":
			node.add_vector3(name=optname,label=optvals.get('text',''),value=optvals.get('default',[0,0,0]))
		if type=="rgb":
			node.add_rgb_palette(name=optname,label=optvals.get('text',''),value=optvals.get('default',[0,0,0]))
		if type == "rgba":
			node.add_rgba_palette(name=optname,label=optvals.get('text',''),value=optvals.get('default',[0,0,0,0]))
		if type == "file":
			node.add_filepath(name=optname,label=optvals.get('text',''),value=optvals.get('default',''),ext=optvals.get('ext'),root=optvals.get('root'),title=optvals.get('title'))
		if type=='hidden':
			node.create_property(name=optname,value=optvals.get('default',None))

	def _prepAccessPortTypes(self,node,port,inputvals,type='in'):
		#todo: change algorithm multitypes check
		if inputvals.get('allowtypes'):
				for item in inputvals.get('allowtypes'):
					if isinstance(item,dict):
						node.add_accept_port_type(port,{'port_name':item.get('name'),'port_type':item.get('port',type),'node_type':item.get('type',"runtime_domain.RuntimeNode")})
					else:
						node.add_accept_port_type(port,{'port_name':item,'port_type':type,'node_type':"runtime_domain.RuntimeNode"})

	
	#endregion

	def getNodesForSearch(self):
		if len(self.nodes) == 0: return {}
		retval = {}
		for type,props in self.nodes.items():
			retval[props['name']]=[type]
		
		#for i in range(1,200):
		#	retval['propname'+str(i)]=["propcat"+str(i)+".testcat.abc.def",'cat123.ptr'+str(i)]
		
		return retval
		#return {"backdrop": ["system.backdrop"],"test2":['x.v','t.e.ass']}
	
	#TODO pass param as node, key = node.class_
	def getNodeLibData(self,key):
		if not self.nodes: return None
		return self.nodes[key]