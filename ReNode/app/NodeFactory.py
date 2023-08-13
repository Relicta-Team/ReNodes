import json
from ReNode.app.Logger import Logger
from NodeGraphQt import (NodeGraph, GroupNode, NodeGraphMenu)
from ReNode.ui.NodePainter import draw_square_port,draw_triangle_port

logger = None

class NodeFactory:
	
	def __init__(self):
		global logger
		logger = Logger(self)
		
		self.graph = None

		self.version = 0
		self.nodes = {}
		self.loadFactoryFromJson("lib.json")
		pass

	def loadFactoryFromJson(self,file_path):
		self.nodes = {}
		self.version = 0

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
			return obj
		logger.log(f"version lib {self.version}")
		with open("lib_output.json", 'w') as file_out:
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
			logger.log(f"Loading category: {nodecat}")
			for node,data in nodelist.items():
				logger.log(f"	Loading node {node}")
				self.registerNodeInLib(nodecat,node,data)

		

	def registerNodeInLib(self,category,name,data : dict):
		struct = {}
		typename = category+"."+name
		defcolor = (13,18,23,255)
		defborder = (255,0,0,255)
		kind = data['kind'] # function,control,operator etc for define icon
		struct['name'] = data['name']
		struct['desc'] = data.get('desc', '')
		struct['icon'] = self._nodeKindToIcon(kind)
		struct['color'] = data.get('color',defcolor)
		struct['border_color'] = data.get('border_color',defborder)

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
			displayName = False
			isMulticonnect = False
			valdata = {}
			valdata['color'] = val.get('color',defcolor)
			valdata['display_name'] = val.get('display_name',displayName)
			valdata['mutliconnect'] = val.get('mutliconnect',isMulticonnect)
			valdata['style'] = self._kindPortStyle(val.get('style',"default"))
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
			valdat['type'] = typeopt
			valdat['default'] = val.get('default')
			valdat['text'] = val.get('text')

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

	def instance(self,nodename,graphref: NodeGraph = None,pos=None):
		if not self.nodes[nodename]: return None
		if not graphref: return None
		if not pos:
			pos = graphref.viewer().scene_cursor_pos()
		graphref.undo_view.blockSignals(True)
		node = graphref.create_node(nodename,pos=[pos.x(),pos.y()],forwardedCustomFactory={'name':nodename})
		cfg = self.nodes[nodename]
		nametext = f'<b>{cfg["name"]}</b>'
		if cfg.get('desc')!="":
			nametext += f'<br/><font size=""4"><i>{cfg["desc"]}</i></font>'
		node.set_property("name",nametext,False,doNotRename=True)
		node.set_icon(cfg['icon'],False)

		for inputkey,inputvals in cfg['inputs'].items():
			node.add_input(
				name=inputkey,
				color=inputvals['color'],
				display_name=inputvals['display_name'],
				multi_input=inputvals['mutliconnect'],
				painter_func=self.__getDrawPortFunction(inputvals['style'])
			)
			
		for outputkey,outputvals in cfg['outputs'].items():
			node.add_output(
				name=outputkey,
				color=outputvals['color'],
				display_name=outputvals['display_name'],
				multi_output=outputvals['mutliconnect'],
				painter_func=self.__getDrawPortFunction(outputvals['style'])
			)
		
		#options
		for optname,optvals in cfg['options'].items():
			type = optvals['type']
			if type == "bool":
				node.add_checkbox(name=optname,text=optvals.get('text',""),state=optvals.get('default',False))

		node.update()
		graphref.undo_view.blockSignals(False)
	#endregion