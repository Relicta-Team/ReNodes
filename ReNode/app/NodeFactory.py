import json
from NodeGraphQt.nodes.base_node import BaseNode
from ReNode.app.Logger import *
from NodeGraphQt import (NodeGraph, GroupNode, NodeGraphMenu)
from ReNode.ui.NodePainter import getDrawPortFunction
from ReNode.app.VirtualLib import VirtualLib
from ReNode.app.Constants import NodeRenderType
import logging
import re

class NodeFactory:
	
	defaultColor = (13,18,23,255)

	def __init__(self):
		self.logger = RegisterLogger("NodeFactory")
		
		self.vlib = VirtualLib(self)

		self.graph = None

		self.version = 0
		self.nodes = {}
		self.classes = {}
		self.classNames = set() #all classnames in lowercase
		self.loadFactoryFromJson("lib.json")
		pass

	def loadFactoryFromJson(self,file_path):
		self.logger.info(f"Loading factory from json file {file_path}")
		self.nodes = {}
		self.classes = {}

		try:
			with open(file_path,encoding='utf-8') as data_file:
				layout_data = json.load(data_file)
		except Exception as e:
			layout_data = None
			self.logger.error('Cannot read data from file.\n{}'.format(e))

		if not layout_data:
			return
		
		self.deserializeLib(layout_data)
		
		def default(obj):
			if isinstance(obj, set):
				return list(obj)
			if callable(obj):
				return obj.__name__
			return obj
		self.logger.info(f"version lib {self.version}")
		
		from ReNode.app.application import Application
		if Application.isDebugMode() or Application.hasArgument('-outlib'):
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
			self.logger.info(f"Loading category: {nodecat}")
			for node,dataNode in nodelist.items():
				self.logger.info(f"	Loading node '{node}'")
				self.registerNodeInLib(nodecat,node,dataNode)

		#load classes
		classDict = data.get('classes',{})

		#inheritance process (baseList generate)
		self.inheritanceProcess(classDict)

		i = 1
		for classname,classmembers in classDict.items():
			if (i%100 == 0):
				self.logger.info(f"Loading class {i}/{len(classDict)}")
			classmembers['__childList'] = []
			classmembers['__inhChild'] = [] #прямые дети
			self.classes[classname] = classmembers
			i += 1


		self.logger.info(f'Native classes count: {len(self.classes)}')

		#validate names
		self.logger.info('Validating class names')
		for classname,classmembers in classDict.items():
			bList = classmembers['baseList']
			for bName in bList:
				if not self.getClassAllParents(bName,False):
					raise Exception(f'Class {classname} has invalid base class {bName} ({"->".join(bList)})')


		# collect class child list
		self.logger.info('Collecting class child list')
		for classname in classDict.keys():
			curData = self.getClassData(classname)
			bList = self.getClassAllParents(classname,False) #родительская иерархия
			for b in bList:
				bData = self.getClassData(b)
				bData['__childList'].append(classname)
		
		# второй проход для проброса детей из родителей
		self.logger.info("Passing children from parents")
		for classname,curData in classDict.items():
			if classname != "object":
				parent = curData["baseClass"]
				parData = self.getClassData(parent)
				parData['__inhChild'].append(classname)
		
		# генерация имен в нижнем регистре
		self.logger.info("Adding lowercase names")
		self.classNames = set([x.lower() for x in classDict.keys()])
		
		# загрузка пользовательской библиотеки
		self.logger.info("Loading user lib")
		self.vlib.generateUserLib()

		pass

	def reloadNativeGeneratedInfo(self):

		classDict = self.classes

		self.inheritanceProcess(classDict)

		#reset all
		self.logger.info("Reset...")
		for cls,dat in classDict.items():
			dat['__childList'] = []
			dat['__inhChild'] = []
		
		self.logger.info('Childlist collect')
		for classname in classDict.keys():
			curData = self.getClassData(classname)
			bList = self.getClassAllParents(classname,False) #родительская иерархия
			for b in bList:
				bData = self.getClassData(b)
				bData['__childList'].append(classname)
		
		# второй проход для проброса детей из родителей
		self.logger.info("Inhchild process")
		for classname,curData in classDict.items():
			if classname != "object":
				parent = curData["baseClass"]
				parData = self.getClassData(parent)
				parData['__inhChild'].append(classname)
		
		# генерация имен в нижнем регистре
		self.logger.info("Lowercase names")
		self.classNames = set([x.lower() for x in classDict.keys()])


	def inheritanceProcess(self,classDict):
		const_baseClass = ''
		classDict['object']['baseClass'] = ""

		for cls,dat in classDict.items():
			bList = [cls]
			curObj = cls
			while curObj != const_baseClass:
				curObj = classDict[curObj]["baseClass"]
				if curObj == const_baseClass: break #second pass
				bList.append(curObj)
			
			dat['baseList'] = bList

	def getColorByType(self,type_name,retAsQColor=False):
		from ReNode.ui.NodeGraphComponent import NodeGraphComponent
		varMgr = NodeGraphComponent.refObject.variable_manager

		if re.findall('[\[\]\,]',type_name):
			portType = f'array[{type_name}]'
			typeinfo = re.findall('[\w\.]+\^?',portType)
			type_name = typeinfo[1]

		#temporary fix
		if type_name.endswith("^"):
			type_name = "object"

		for objInfo in varMgr.variableTempateData:
			if objInfo.variableType == type_name:
				if retAsQColor:
					return objInfo.color
				else:
					return [objInfo.color.red(),objInfo.color.green(),objInfo.color.blue(),objInfo.color.alpha()]
		
		return NodeFactory.defaultColor

	# Синхронизирует цвета нодов в библиотеке с цветом типов 
	def updateLibTypes(self):
		raise Exception("Obsoleted function")
	
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
						typeinfo = re.findall('[\w\.]+\^?',portType)
						portType = typeinfo[1]

					if portType.endswith("^"): portType = "object" #temp fix object colors
					
					isDefaultColor = v['color']== list(NodeFactory.defaultColor) or v['color'] == [255,255,255,255]
					if portType in typecolor and isDefaultColor:
						v['color'] = typecolor[portType]
						v['border_color'] = None
			
			if val['outputs']:
				for v in val['outputs'].values():
					portType = v['type']

					if re.findall('[\[\]\,]',portType):
						typeinfo = re.findall('[\w\.]+\^?',portType)
						portType = typeinfo[1]

					if portType.endswith("^"): portType = "object" #temp fix object colors

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
		
		struct['name'] = data.get('name','')
		struct['namelib'] = data.get('namelib',struct['name'])
		struct['path'] = data.get('path','')
		struct['desc'] = data.get('desc', '')
		struct['icon'] = self._nodeIconPrepare(data.get('icon'))
		struct['color'] = data.get('color',defcolor)
		struct['border_color'] = data.get('border_color',defborder)
		struct['code'] = data.get('code',"")
		
		struct['returnType'] = data.get('returnType')
		struct['returnDesc'] = data.get('returnDesc')

		clsInfo = data.get('classInfo')
		if clsInfo:
			struct['classInfo'] = clsInfo
		memType = data.get('memtype')
		if memType: 
			struct['memtype'] = memType

		struct['runtime_ports'] = data.get('runtime_ports',False)
		struct['auto_color_icon'] = data.get('auto_color_icon',False)
		struct['render_type'] = data.get('render_type',NodeRenderType.Default.name)

		struct['visible'] = data.get('isVisibleInLib',True)

		#struct['states'] = data.get('states',[]) #list: event(as entrypoint), onlydebug etc... (for codegen)

		if self.nodes.get(typename):
			raise Exception(f"node {typename} already exists")
		
		#inputs generate
		struct['inputs'] = self._deserializeConnectors(data.get('inputs'),True)
		#outputs generate
		struct['outputs'] = self._deserializeConnectors(data.get('outputs'),False)

		#custom node options
		struct['options'] = self._deserializeOptions(data.get('options'),struct['inputs'])

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
			if 'allowtypes' in val:
				valdata['allowtypes'] = val.get('allowtypes')
			valdata['type'] = val.get('type',key)
			valdata['typeget'] = val.get('typeget',"")
			valdata['desc'] = val.get('desc','')
			valdata['require_connection'] = val.get('require_connection',True)
			if not val.get("gen_param",True): #без генерации параметра
				valdata['gen_param'] = False
			if 'default_value' in val:
				valdata['default_value'] = val.get('default_value')

			if not isInput:
				valdata['accepted_paths'] = val.get('accepted_paths',["@any"])
			cons[key] = valdata
		return cons	

	def _deserializeOptions(self,cnts: dict,refInputs: dict):
		opts = {}
		if not cnts: return opts

		for key,val in cnts.items():
			valdat = {}
			
			typeopt = val.get('type')
			if not typeopt:
				raise Exception(f"no type for option {key}")
			
			for keyopt,valopt in val.items():
				valdat[keyopt] = valopt

			if key in refInputs and 'default_value' in refInputs[key]:
				valdat['default'] = refInputs[key]['default_value']
			
			opts[key] = valdat
				
		return opts

	#region internal deserialize lib helpers

	def _nodeIconPrepare(self,iconpath):
		if isinstance(iconpath,list):
			for i in range(0,len(iconpath),2):
				iconpath[i] = self._nodeIconPrepare(iconpath[i])
			return iconpath
		else:
			return self._nodeIconPrepare_Internal(iconpath)
		

	def _nodeIconPrepare_Internal(self,path):
		if path is None:
			return None
		if path == '': return None
		if "data\\" in path.lower():
			return path
		return "data\\" + path

	_kindPortStyleTypes = {
		"default": None,
		"triangle": 1,
		"square": 2
	}
	def _kindPortStyle(self,kind):
		return NodeFactory._kindPortStyleTypes.get(kind,0)

	#endregion

	#region factory instances

	def instance(self,nodename,graphref: NodeGraph = None,pos=None,isInstanceCreate=False,forwardDeserializeData=None):
		graphref.incrementId += 1
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

		node.uid = graphref.incrementId

		node._view._node_render_type = NodeRenderType[cfg['render_type']]
		if node._view._node_render_type in [NodeRenderType.NoHeaderText,NodeRenderType.NoHeader]:
			node._view._default_font_size *= 2
		#node.create_property("class_",nodename)

		if "internal." in nodename:
			node.set_property("name",cfg["name"],False)
		else:
			nametext = cfg['name']
			#nametext = f'<span style=\'font-family: Arial; font-size: 11pt;\'><b>{cfg["name"]}</b></span>'
			#if cfg.get('desc')!="":
			#	nametext += f'<br/><font size=""4"><i>{cfg["desc"]}</i></font>'
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
		ptrFnc = getDrawPortFunction(inputvals['style'])
		port = node.add_input(
			name=inputkey,
			color=inputvals['color'],
			display_name=inputvals['display_name'],
			multi_input=inputvals['mutliconnect'],
			painter_func=ptrFnc,
			portType=inputvals.get('type')
		)
		#self._prepAccessPortTypes(node,port,inputvals,'out')

	def addOutput(self,node,outputkey,outputvals):
		ptrFnc = getDrawPortFunction(outputvals['style'])
		port = node.add_output(
			name=outputkey,
			color=outputvals['color'],
			display_name=outputvals['display_name'],
			multi_output=outputvals['mutliconnect'],
			painter_func=ptrFnc,
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
		if type=="objcaller":
			node.add_text_input(name=optname,label=optvals.get('text',''),text="Этот объект",isObjCaller=True)
		if type=='makeport_in' or type=='makeport_out':
			node.add_makeport(port_type='in' if type=='makeport_in' else 'out',name=optname,srcName=optvals.get('src',''),text_format=optvals.get('text_format'))
		if type=='typeselect':
			node.add_typeselect(name=optname,label=optvals.get('text',''),value=optvals.get('default','object'))

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
		if key not in self.nodes: return None
		return self.nodes[key]

	def getClassData(self,className):
		if not self.classes: return None
		return self.classes.get(className,None)
	
	def getClassAllParents(self,className,retCopy=True):
		cd = self.getClassData(className)
		if not cd: return []
		if retCopy:
			return list(cd.get("baseList",[]))
		else:
			return cd.get("baseList",[])
	
	def getClassAllChilds(self,className,retCopy=True):
		cd = self.getClassData(className)
		if not cd: return []
		if retCopy:
			return list(cd.get("__childList",[]))
		else:
			return cd.get("__childList",[])
	
	# получение прямых предков
	def getClassParent(self,className):
		cd = self.getClassData(className)
		if not cd: return None
		return cd.get('baseClass',None)

	def getClassChilds(self,className,retCopy=True):
		cd = self.getClassData(className)
		if not cd: return []
		if retCopy:
			return list(cd.get("__inhChild",[]))
		else:
			return cd.get("__inhChild",[])

	def getClassAllChildsTree(self,className):
		"""
			Собирает все дочерние классы от указанного className в виде дерева

			{
				"name": "",
				"childs": [] #name,childs tree
			}
		"""
		lst = self.getClassChilds(className)
		dta = self.getClassData(className)
		vname = dta.get('name')
		if not lst: 
			emptyDict = {"name":className, "childs": []}
			if vname:
				emptyDict["vname"] = vname
			if dta.get('desc'):
				emptyDict["desc"] = dta.get('desc')
			return emptyDict
		ret = {
			"name": className,
			"childs": []
		}
		if vname:
			ret["vname"] = vname
		if dta.get('desc'):
			ret["desc"] = dta.get('desc')
		for ch in lst:
			tree = self.getClassAllChildsTree(ch)
			#if tree['name']:
			ret["childs"].append(tree)
		return ret
	
	def isTypeOf(self,typecheck,baseClassName):
		parents = self.getClassAllParents(typecheck,False)
		return baseClassName in parents
	
	def isObjectType(self,type):
		"""
			Проверяет является ли тип типом объекта (унаследованного от object)

			Допускается использование типов с постфиксом наследования (^)
		"""
		if type.endswith("^"): #remove postfix
			type = type[:-1]
		
		if self.isTypeOf(type,"object"):
			return True
		return False

	def classNameExists(self,className):
		return className.lower() in self.classNames
	
	def getClassAllFields(self,className):
		cd = self.getClassAllParents(className)
		if not cd: return []
		retList = []
		for className in cd:
			cd = self.getClassData(className)
			if cd:
				retList.extend(cd['fields']['defined'].keys())
		return retList
	
	def getClassAllMethods(self,className):
		cd = self.getClassAllParents(className)
		if not cd: return []
		retList = []
		for className in cd:
			cd = self.getClassData(className)
			if cd:
				retList.extend(cd['methods']['defined'].keys())
		return retList
	
	def getClassAllInspectorProps(self,className):
		"""Возвращаемый массив не должен быть изменяемым"""
		cd = self.getClassAllParents(className)
		if not cd: return {}
		retList = {
			"fields": {},
			"methods": {}
		}
		for className in cd:
			cd = self.getClassData(className)
			if cd:
				iprops = cd.get('inspectorProps')
				if iprops:
					for k,v in iprops.get('fields',{}).items():
						retList['fields'][k] = v
					for k,v in iprops.get('methods',{}).items():
						retList['methods'][k] = v
		return retList
	
	#region Enumerator helpers

	def getEnumDict(self):
		"""Возвращает словарь перечислений. 
			Имя каждого элемента равно типу и узлу для создания свитчера по этому перечислению
			Каждый элемент имеет значения: name, values (list[str])
		"""
		return self.getClassData("ReNode_AbstractEnum")['allEnums']
	
	def getEnumData(self,enumName):
		"""Возвращает словарь перечислений. 
			Если не найден - возвращает None
		"""
		return self.getEnumDict().get(enumName)
	
	def isEnumType(self,enumName):
		"""Проверяет существование перечисления в библиотеке"""
		return self.getEnumData(enumName) != None
	
	def getEnumValues(self,enumName):
		return self.getEnumData(enumName)['values']

	#endregion

	#region Structure helpers

	def getStructDict(self):
		"""
			Возвращает словарь структур.
			Каждый элемент имеет значения: name, values (list[dict(name,type,value,?desc)])
		"""
		return self.getClassData("ReNode_AbstractEnum")['allStructs']
	
	def getStructData(self,structName):
		"""Возвращает словарь структур. 
			Если не найден - возвращает None
		"""
		return self.getStructDict().get(structName)
	
	def isStructType(self,structName):
		"""Проверяет существование структуры в библиотеке"""
		return self.getStructData(structName) != None
	
	def getStructFields(self,structName):
		"""Возвращает список полей структуры (name,type,value,?desc)
		Возвращает реальное значение из библиотеки (не должно изменяться)
		"""
		return self.getStructData(structName)['values']

	#endregion
