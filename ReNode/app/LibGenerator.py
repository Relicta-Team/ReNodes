
import re
import os
import json
import copy
from ReNode.app.utils import intTryParse
from ReNode.ui.VariableManager import VariableLibrary
from ReNode.app.Constants import *
from ReNode.app.application import Application
from ReNode.app.Constants import NodeRenderType

def hexToRGBA(hex):
	hex = hex.lstrip("#")
	if len(hex) == (6):
		hex += "ff"
	return list(int(hex[i:i+2], 16) for i in (0, 2, 4, 6))

def unescape(text):
	return text.replace('\\n','\n').replace('\\t','\t')

def checkRegionName(content,regname : str):
	upperName = regname.upper()
	return f"$REGION:{upperName}" in content and f"$ENDREGION:{upperName}" in content

def getRegionData(content:str,region_name:str,returnDict=False) -> dict | str | None:
	region_name = region_name.upper()
	# Ищем начало и конец указанного региона
	start_marker = f"$REGION:{region_name}\n"
	end_marker = f"$ENDREGION:{region_name}\n"

	start_index = content.find(start_marker)
	end_index = content.find(end_marker)

	if start_index == -1 or end_index == -1:
		return None  # Регион не найден

	# Извлекаем и декодируем JSON для указанного региона
	region_data = content[start_index + len(start_marker):end_index].strip()
	if returnDict:
		decoded_data = json.loads(region_data)

		return decoded_data
	else:
		return region_data

def printDebug(str):
	if Application.isDebugMode():
		print(f"DEBUG: {str}")


def getTokens(content):
	return re.split(r'(?<!\\):', content)

class NodeObjectHandler:
	varLib = None
	def __init__(self,objName,objectType,nodeLibDict,classMetadata,__lineList):
		self.nodeLib = nodeLibDict #ссылка на базовый словарь узлов
		self.classMetadata = classMetadata #ссылка на словарь метаданных классов
		"""Ссылка на словарь метаданных классов (наследование, члены)"""
		self.objectNameFull = objName #базовое полное имя члена
		self.objectType = objectType #тип-категория члена (метод, поле, функция)

		self.lineList : list = __lineList #ссылка на список обрабатываемых строк

		if NodeObjectHandler.varLib is None:
			NodeObjectHandler.varLib = VariableLibrary()

		self.isClass = self.objectType == 'c'
		self.isField = self.objectType == 'f'
		self.isMethod = self.objectType == 'm'
		self.isSystem = self.objectType == 'node'
		self.isEnum = self.objectType == 'enum'
		self.isStruct = self.objectType == "struct"
		self.isFunc = self.objectType == "func"

		self.isClassMember = self.isField or self.isMethod

		self.refAllObjects : list = None #Ссылка на все объекты
		self.counterCopy = 0

		self.execTypes = 'all' #all,in,out,pure,none
		if self.isSystem or self.isEnum or self.isStruct:
			self.execTypes = "none" #by default system nodes and enums has no exectypes
			if self.isEnum:
				self.enumList = []
			if self.isStruct:
				self.structList = []
				self.structSerializedValues = {}

		self.path = "" # путь до узла в дереве
		#TODO remove var
		self.defCode = "" #код инициализации (опциональный). помещается 

		self.memberData = {
			# порты при финализации конвертируются в словарь
			# записанные значения: tuple(name:str,data:dict)
			"inputs": [],#{},
			"outputs": [],#{},
			"options": [],#{}
		}
		self.lastPortRef = None
		self.hasAutoPort = False #при true добавляется автопортдата

		# Определение имени класса и имени члена
		self.memberClass = None
		self.memberName = None
		self.memberNameFull = None

		if self.isClass:
			self.memberClass = objName

		if self.isMethod or self.isField:
			if re.findall('_\d+$',objName): #if curMember endswith regex _\d+ then remove postfix
				clearMem = re.sub(r'_\d+$',"",objName)#curMember[:curMember.rfind('_')]
			else:
				clearMem = objName
			className_, memName_ = clearMem.split('.',1)
			self.memberClass = className_
			self.memberName = memName_
			self.memberNameFull = f'{className_}.{memName_}'

	def __repr__(self) -> str:
		return f'Node:{self.objectNameFull} at {hex(id(self))}'

	def exThrow(self,msg='Unhandled exception'):
		raise Exception(f'[{self.objectNameFull}]: {msg}')

	def __getitem__(self, key):
		return self.memberData[key]
	def __setitem__(self, key, value):
		self.memberData[key] = value

	def getSpecialTypesStorage(self,typeprefix,typename):
		dat = self.classMetadata['ReNode_AbstractEnum']
		if not dat:
			raise Exception("Empty special type storage")
		propId = ''
		if typeprefix == "enum":
			propId = 'allEnums'
		elif typeprefix == "struct":
			propId = 'allStructs'
		else:
			raise Exception(f"Unknown typeprefix: {typeprefix}")
		return dat[propId][typename]

	def getVarlibOptionByType(self,type,textName=None):
		typeList = NodeObjectHandler.varLib.typeList
		dictInfo = {}
		# (portEnumName, {
		# 			"type":"list",
		# 			"text": portEnumName,
		# 			"default": self.enumList[0]['name'],
		# 			"values": values,
		# 		})
		if type.startswith("enum."):
			stor = self.getSpecialTypesStorage("enum",type)
			return {
				"type":"list",
				"text":textName or stor['name'],
				"default":stor['values'][0],
				"values":stor['values']
			}

		for objVar in typeList:
			if objVar.variableType == type:
				props = objVar.dictProp
				for pname,pvals in props.items():
					dictInfo.update(pvals)
					dictInfo['type'] = pname
					if textName:
						dictInfo['text'] = textName
					break
				break
		return dictInfo

	def getVarlibColorByType(self,type):
		typeList = NodeObjectHandler.varLib.typeList
		if type.endswith("^"):
			type = 'object'
		for objVar in typeList:
			if objVar.variableType == type:
				return objVar.color.name()
		return '#ffffff'

	def generateJson(self):
		for tokens in self.lineList:
			self.handleTokens(tokens)
		self.finalizeObject()
		self.refAllObjects.remove(self)

	#for add line once
	def insertLine(self,string):
		self.lineList.insert(1,getTokens(string))
	#for add lines (example: input)
	def insertLines(self,stringList):
		self.lineList[1:1] = [getTokens(o) for o in stringList]
	
	def pushBackLines(self,stringList):
		self.lineList.extend([getTokens(o) for o in stringList])

	def removeLine(self,setting):
		remtoks = None
		for toks in self.lineList:
			if toks[0] == setting:
				remtoks = toks
				break
		if remtoks:
			self.lineList.remove(remtoks)
			return True
		return False

	#object copy
	def copy(self,addToAllObjects=True):
		src = self
		src.counterCopy += 1
		dst = NodeObjectHandler(self.objectNameFull,self.objectType,self.nodeLib,self.classMetadata,self.lineList.copy())
		dst.counterCopy = src.counterCopy
		dst.memberData = copy.deepcopy(src.memberData)

		dst.defCode = src.defCode
		
		dst.memberClass = src.memberClass
		dst.memberName = src.memberName
		dst.memberNameFull = src.memberNameFull

		dst.hasAutoPort = src.hasAutoPort

		dst.refAllObjects = src.refAllObjects
		if addToAllObjects:
			if len(dst.refAllObjects) <= 1:
				dst.refAllObjects.append(dst)
			else:
				dst.refAllObjects.insert(1,dst)
		return dst

	def safecopy(self):
		dst = NodeObjectHandler(self.objectNameFull,self.objectType,self.nodeLib,self.classMetadata,self.lineList.copy())
		
		dst.refAllObjects = self.refAllObjects
		
		if len(dst.refAllObjects) <= 1:
			dst.refAllObjects.append(dst)
		else:
			dst.refAllObjects.insert(1,dst)
		return dst

	def findLinesByToken(self,tok):
		ltokList = []

		for ltok_it in self.lineList:
			if ltok_it[0] == tok:
				ltokList.append(ltok_it)

		return ltokList

	def removeLinesByToken(self,tok):
		raise NotImplementedError("TODO: implement removeLinesByToken")

	def preparePath(self,path):
		return path.replace('\\\\','\\').replace('\\','\\\\')

	def prepareCode(self,code):
		raise DeprecationWarning("This function is deprecated. Use this from CodeGen.prepareMemberCode")
		if self.isMethod:
			code = code.replace('@thisName',self.memberName)
			if "@thisParams" in code:
				
				paramList = ['\'this\'']
				for indexVar, (outKey,outValues) in enumerate(self['outputs'].items()):
					if outValues['type'] != "Exec" and outValues['type'] != "":
						paramList.append('\"@genvar.out.{}\"'.format(indexVar+1))
				code = code.replace('@thisClass',self.memberClass)
				paramCtx = f'params [{", ".join(paramList)}]'
				code = code.replace('@thisParams',paramCtx)
		
		return code

	def generateMethodCodeCall(self):
		addingParams = []
		objCaller = '@in.2'
		for i, (k,v) in enumerate(self['inputs'].items()):
			if v['type'] != "Exec" and v['type'] != "":
				addingParams.append(f'@in.{i+1}')
			if v['type'] == 'self':
				objCaller = f'@in.{i+1}'
		
		paramString = ", ".join(addingParams)
		if paramString == objCaller: #no params
			paramString = f'({objCaller})'
		else:
			paramString = f'[{paramString}]'
		#if paramString: paramString = ", " + paramString
		code = f"{paramString} call (({objCaller}) getVariable PROTOTYPE_VAR_NAME getVariable \"@thisName\")"
		
		#TODO записываем возвращаемое значение в переменную только если нода возвращаемого значения мультивыход
		returnId = -1
		if self.memberData.get('returnType') not in ['void','null','']:
			for i, (k,v) in enumerate(self['outputs'].items()):
				if v['type'] != "Exec" and v['type'] == self.memberData.get('returnType'):
					returnId = i+1
					break
		isPureCalling = self.memberData['memtype'] in ['const','get']
		if returnId >= 0 and not isPureCalling:
			code = f'private @genvar.out.{returnId} = {code}'
		if not isPureCalling:
			code += "; @out.1"

		#	code = f'@genvar.out.2 = {code}; @locvar.out.2'
		return code

	def handleTokens(self,tokens):
		tokenType = tokens[0]
		# Имя ноды
		if tokenType == "name":
			self.memberData['name'] = tokens[1]
			pass
		# имя ноды в дереве выбора
		elif tokenType == "namelib":
			self.memberData['namelib'] = tokens[1]
			pass
		# описание ноды
		elif tokenType == "desc":
			self.memberData['desc'] = unescape(tokens[1])
		elif tokenType == "path":
			self.memberData['path'] = tokens[1]
		# возвращаемое значение
		elif tokenType == "return":
			self.memberData['returnType'] = tokens[1]
			if len(tokens) > 2:
				self.memberData['returnDesc'] = unescape(tokens[2])
		elif tokenType == 'prop':
			propType = tokens[1]
			if propType not in ['all','get','set','none','pure']:
				raise ValueError(f"[{self.objectNameFull}]: Wrong prop type: {propType}")
			self.memberData['prop'] = propType
			pass
		elif tokenType == 'code':
			self.memberData['code'] = tokens[1]
		elif tokenType == 'defcode':
			self.defCode = tokens[1]
		# видимость ноды в инспекторе
		elif tokenType == 'classprop':
			clsprop = intTryParse(tokens[1])
			self.memberData['classProp'] = clsprop
		#значение по умолчанию
		elif tokenType == 'defval':
			self.memberData['defval'] = unescape(tokens[1]).replace("\\:",":")
		#method specific data

		#method type: method,event,get,const
		elif tokenType == 'type':
			mtype = tokens[1]
			self.memberData['type'] = mtype
			if mtype in ['event','def']:
				self.execTypes = 'out'
			if mtype == "const":
				self.execTypes = 'pure'
				self.memberData['classProp'] = 1
			if mtype == 'get': #for getters no override
				self.execTypes = 'pure'
		elif tokenType == 'exec':
			execType = tokens[1]
			self.execTypes = execType
		elif tokenType == 'lockoverride':
			self['lockoverride'] = intTryParse(tokens[1])
		elif tokenType == "in":
			
			self.lastPortRef = {
				'type': tokens[1],
				"use_custom": tokens[1] not in ['Exec',"","void","null"]
			}
			if len(tokens) > 3:
				self.lastPortRef['desc'] = unescape(tokens[3])
			self.memberData['inputs'].append((tokens[2],self.lastPortRef))
			if tokens[1] == 'auto' and not self.hasAutoPort:
				self.pushBackLines(["runtimeports:1"])
		elif tokenType == "out":
			self.lastPortRef = {
				'type': tokens[1],
				'mutliconnect':True
			}
			if len(tokens) > 3:
				self.lastPortRef['desc'] = unescape(tokens[3])
			self.memberData['outputs'].append((tokens[2],self.lastPortRef))
			if tokens[1] == 'auto' and not self.hasAutoPort:
				self.pushBackLines(["runtimeports:1"])
		elif tokenType == 'opt':
			for tInside in tokens[1:]:
				if tInside.startswith("mul"):
					self.lastPortRef['mutliconnect'] = intTryParse(tInside.split('=')[1]) > 0
				elif tInside.startswith("dname"):
					self.lastPortRef['display_name'] = intTryParse(tInside.split('=')[1]) > 0
				elif tInside.startswith('allowtypes'):
					self.lastPortRef['allowtypes'] = tInside.split('=')[1].split('|')
				elif tInside.startswith("custom_type"):
					self.lastPortRef['custom_type'] = tInside.split("=")[1]
				elif tInside.startswith("custom"):
					self.lastPortRef['use_custom'] = intTryParse(tInside.split('=')[1]) > 0
				elif tInside.startswith("pathes"):
					parts_ = tInside.split('=')
					listParts_ = parts_[1].split('|') if len(parts_) > 1 and not parts_[1].isspace() else []
					self.lastPortRef['accepted_paths'] = listParts_
				elif tInside.startswith("typeget"):
					self.lastPortRef['typeget'] = tInside.split('=')[1]
				elif tInside.startswith("require"):
					ival__ = intTryParse(tInside.split("=")[1])
					self.lastPortRef['require_connection'] = ival__ > 0
					self.lastPortRef['emplace_value'] = ival__ <= -1
				elif tInside.startswith("gen_param"):
					self.lastPortRef['gen_param'] = intTryParse(tInside.split("=")[1]) > 0
				elif tInside.startswith("def="):
					serVal = tInside[4:].replace("\\:",":")
					typePort = self.lastPortRef['type']
					if typePort == 'auto' and self.lastPortRef.get('allowtypes',[]):
						typePort = self.lastPortRef['allowtypes'][0]
					dval = self.varLib.parseGameValue(serVal,typePort,self.classMetadata)
					self.lastPortRef['default_value'] = dval
				elif tInside.startswith("typeset_out"):
					self.lastPortRef['typeset_out'] = tInside.split("=")[1]
				elif tInside.startswith("port_rename"):
					self.lastPortRef["port_rename"] = tInside.split("=")[1]
				else:
					raise Exception(f"Unsupported option: {tInside}")
		# -------------------- common spec options -------------------- 
		elif tokenType == 'eval' and (self.isEnum or self.isStruct): #enum node value
			if self.isEnum:
				eName = tokens[1]
				eVal = intTryParse(tokens[2])
				enumCase = {
					'name': eName,
					'val':eVal,
				}
				if len(tokens) > 3:
					enumCase['desc'] = unescape(tokens[3])
				self.enumList.append(enumCase)
			elif self.isStruct:
				sType = tokens[1]
				sName = tokens[2]
				structInfo = {
					'type':sType,
					'name': sName
				}
				if len(tokens) > 3:
					sVal = tokens[3]
					if sVal == '':
						sVal = "$NULL$" #auto detect default value
				else:
					sVal = "$NULL$"
				
				self.structSerializedValues[sName] = sVal

				sVal = self.varLib.parseGameValue(unescape(sVal),sType,self.classMetadata)
				structInfo['val'] = sVal
				if len(tokens) > 4:
					structInfo['desc'] = unescape(tokens[4])
				self.structList.append(structInfo)
				
		# redef node name
		elif tokenType == 'node':
			if self.isSystem:
				self.objectType = self.objectNameFull
			self.objectNameFull = tokens[1]
		elif tokenType == "icon":
			self['icon'] = tokens[1]
		elif tokenType == "color":
			clrTok = tokens[1]
			for n in NodeColor:
				if clrTok == n.name:
					clrTok = hexToRGBA(n.value)
					break
			self['color'] = clrTok
		# def visible node in treeview
		elif tokenType == "libvisible":
			if intTryParse(tokens[1]) == 0:
				self.memberData['isVisibleInLib'] = False
		# enable ports with autotypes
		elif tokenType == "runtimeports":
			if intTryParse(tokens[1]) > 0:
				self.memberData['runtime_ports'] = True
				if self.isSystem:
					self['options'].append(("autoportdata", {
						"type": "hidden",
						"default": {}
					}))
				#do not override if exists
				self.memberData['auto_color_icon'] = self.memberData.get('auto_color_icon',False)
		elif tokenType == "autocoloricon":
			self.memberData['auto_color_icon'] = intTryParse(tokens[1]) > 0
		elif tokenType == "rendertype":
			if not NodeRenderType.typeExists(tokens[1]):
				raise Exception(f"Unknown render type: {tokens[1]}")
			self.memberData['render_type'] = NodeRenderType[tokens[1]].name
		# add specific option to node
		elif tokenType == "option":
			_cont :str= tokens[1]
			#removing \\: to :
			_cont = _cont.replace("\\:",":")
			if not _cont.strip(' \t\n\r').startswith("{"):
				_cont = "{"+_cont+"}"
			_ser = json.loads(_cont)
			for k,v in _ser.items():
				if k in self['options']:
					self.exThrow(f"Duplicate option: {k}")
				self['options'].append((k,v))

		pass

	def finalizeClass(self):
		classDict = self.classMetadata[self.memberClass]
		#saving pathes etc.
		if 'name' in self.memberData: classDict['name'] = self['name']
		if 'desc' in self.memberData: classDict['desc'] = unescape(self['desc'])
		if 'path' in self.memberData: classDict['path'] = self['path']

	def finalizeObject(self):
		if self.isClass:
			self.finalizeClass()
			return
		classmeta = self.classMetadata
		memberData = self.memberData

		memberRegion = "unknown"
		if self.isField:
			memberRegion = "fields"
		elif self.isMethod:
			memberRegion = "methods"
		elif self.isSystem or self.isEnum or self.isStruct or self.isFunc:
			memberRegion = self.objectType #internal,operators,etc
		else:
			raise Exception(f'Unknown member type: {self.objectType}')

		if memberRegion not in self.nodeLib:
			self.nodeLib[memberRegion] = {}

		# Проверка возвращаемого типа и его автоопределение
		if 'returnType' not in memberData:
			
			if self.isField:
				memberData['returnType'] = classmeta[self.memberClass]['fields']['defined'].get(self.memberName,{}).get('return','NULLTYPE_ALLOC')
			else:
				memberData['returnType'] = "null"

		# Проверка типа и его автоопределение
		if 'type' not in memberData:
			if self.isMethod:
				memberData['type'] = "method"

		#validate color, icon, code
		if self.isMethod:
			mtype = self['type']

			#! fix type for nodes
			self['memtype'] = mtype
			del memberData['type']
			
			hasLockedOverride = 'lockoverride' in memberData
			if hasLockedOverride:
				hasLockedOverride = memberData['lockoverride'] == 1
				del memberData['lockoverride']

			tableTypes = NodeColor.getMethodMapAssoc()
			if mtype not in tableTypes:
				raise ValueError(f"[{self.objectNameFull}]: Wrong method type: {mtype}")

			# register member ports
			#if mtype

			_canOverrideCode = 'code' not in self.memberData
			_canOverrideColor = "color" not in self.memberData
			_canOverrideIcon = 'icon' not in self.memberData
			if _canOverrideCode:
				curCode_ = tableTypes[mtype].get('code')
				if curCode_: self['code'] = curCode_

			if _canOverrideColor:
				# nodeColorList = [
				# 	hexToRGBA("004568"),#method
				# 	hexToRGBA("5b0802"),#event old:6d0101
				# 	hexToRGBA("25888F"),#getter
				# 	hexToRGBA("124d41"),#constant
				# 	hexToRGBA("955e00"),#def
				# ]
				newColor = tableTypes[mtype].get('color')
				self['color'] = newColor
			if _canOverrideIcon:
				self['icon'] = tableTypes[mtype].get('icon')

			#if mtype method or getter then add method def prop
			if mtype in ['method','get'] and not hasLockedOverride:
				cpyObj = self.safecopy()
				#adding postfix to method define
				cpyObj.objectNameFull += ".def"

				#change name
				names = cpyObj.findLinesByToken("name")
				origName = names[0][1] if len(names) > 0 else ""
				for name in names: 
					origName = name[1]
					name[1] = f"Определение \"{name[1]}\""
				
				#change namelib
				nlibs = cpyObj.findLinesByToken("namelib")
				if not nlibs:
					if origName: cpyObj.pushBackLines([f"namelib:{origName} (опред.)"])
				else:
					for nlib in nlibs: nlib[1] = f"{nlib[1]} (опред.)"

				#change execs
				execs = cpyObj.findLinesByToken('exec')
				if not execs:
					cpyObj.insertLines(["exec:out"])
				else:
					for execLine in execs: execLine[1] = 'out'

				#change inputs to outputs
				ins = cpyObj.findLinesByToken('in')
				for line in ins: line[0] = 'out'
				
				#change type from method/get to def
				types_ = cpyObj.findLinesByToken('type')
				if not types_:
					cpyObj.pushBackLines(["type:def"])
				else:
					for type_ in types_: type_[1] = 'def'

				#todo add more override options

		if "classProp" in memberData:
			if 'returnType' not in memberData:
				raise Exception(f'[{self.objectNameFull}]: classProp must have returnType')

		# Определение свойств поля (геттеры, сеттеры)
		if self.isField and self.counterCopy == 0:
			if 'prop' not in memberData:
				memberData['prop'] = 'all'
			curPropType = memberData['prop']
			del memberData['prop']
			#removing lines for update generated
			self.lineList.clear()

			if curPropType in ['none','pure']:
				memberData = None
			elif curPropType in ['all','get','set']:
				_hasGet = curPropType in ['all','get']
				_hasSet = curPropType in ['all','set']
				if _hasGet:
					newobj = self.copy(True)
					newobj.objectNameFull += f".get"
					newobj['code'] = f'@in.1 getVariable "{newobj.memberName}"'
					newobj.execTypes = 'pure'
					newobj.pushBackLines([
						f'out:{newobj["returnType"]}:Значение'
					])
				if _hasSet:
					newobj = self.copy(True)
					newobj.objectNameFull += f".set"
					newobj['code'] = f'@in.2 setVariable ["{newobj.memberName}",@in.3]; @out.1'
					newobj.execTypes = 'all'
					_setterLines = [
						f"in:{newobj['returnType']}:Значение",
						f'out:{newobj["returnType"]}:Новое значение',
						"opt:mul=1"
					]
					if newobj.memberData.get('defval') != None:
						dval__ = newobj.memberData.get('defval')
						serval = str(dval__).replace(':',"\:")
						_setterLines.insert(1,f"opt:def={serval}")
					if newobj.memberData.get('classProp',0) > 0 and _hasGet:
						_setterLines.append('classprop:0') #disable classprop for setter because getter already setup
					newobj.pushBackLines(_setterLines)
					
				
				#set memdata to null 
				memberData = None
		

		# регистрация узла
		if memberData:
			self.registerNode(memberRegion)

	def _preregField(self):
		memberData = self.memberData
		classmeta = self.classMetadata

		# подписываем приписку к полю (если есть)
		if self.objectNameFull.endswith('.get'):
			memberData['namelib'] = memberData.get('namelib',memberData.get('name',self.memberName)) + " (Получить)"
		elif self.objectNameFull.endswith('.set'):
			memberData['namelib'] = memberData.get('namelib',memberData.get('name',self.memberName)) + " (Установить)"

		retType = memberData['returnType']

		# Устанавливаем цвет поля
		if 'color' not in memberData:
			self['color'] = self.varLib.getColorByType(retType)
		if 'icon' not in memberData:
			icnList = self.varLib.getIconFromTypename(retType,True)
			self['icon'] = icnList

		portColor = [*self.varLib.getVarTypedefByType("object").color.getRgb()]
		self['inputs'].insert(1,("Цель", {"type": "self", 'desc':"Владелец значения свойства.", "color": portColor}))
		instanceOption = ("Цель", {
				"type":"objcaller",
		})
		self['options'].insert(0,instanceOption)
	
	def _preregMethod(self):
		memberData = self.memberData
		classmeta = self.classMetadata

		# Помещаем инстансер
		if self['memtype'] not in ['event',"def"]:
			#старый владелец объекта
			# self['inputs'].insert(1,("Цель", {"type": "self", 'desc':"Инициатор вызова метода, функции или события."}))
			# instanceOption = ("Цель", {
			# 		"type":"list",
			# 		"disabledListInputs": ["Этот объект"],
			# 		"text": "Вызывающий",
			# 		"default": "Этот объект",
			# 		"values": [["Этот объект","this"], "Цель"],
			# 		"typingList": ["self",f"{self.memberClass}^"]
			# 	})
			# self['options'].insert(0,instanceOption)
			portColor = [*self.varLib.getVarTypedefByType("object").color.getRgb()]
			self['inputs'].insert(0 if self['memtype'] == "get" else 1,("Цель", {"type": "self", 'desc':"Инициатор вызова метода, функции или события.","color": portColor}))
			instanceOption = ("Цель", {
					"type":"objcaller",
			})
			self['options'].insert(0,instanceOption)

			#if get and const insert return value
			if self['returnType'] not in ['null','void','Exec','']:
				retTpDict = {
					"type": self['returnType'],
					'mutliconnect': True # мы можем использовать возвращаемое значение где угодно (мульти)
				}
				self['outputs'].insert(1,("Результат", retTpDict))
				if 'returnDesc' in memberData:
					retTpDict['desc'] = memberData['returnDesc']

	def _preregClassMember(self):
		memberData = self.memberData
		classmeta = self.classMetadata

		#Если пути нет - генерируем его
		if 'path' not in memberData:
			memberData['path'] = classmeta[self.memberClass].get('path','')
		
		if self.isClassMember:
			
			#add node inside class zone
			if self.isField:
				flds = classmeta[self.memberClass]['fields']
				
				if 'nodes' not in flds: flds['nodes'] = []
				flds['nodes'].append(self.objectNameFull)

			if self.isMethod:
				mtds = classmeta[self.memberClass]['methods']
				
				if 'nodes' not in mtds: mtds['nodes'] = []
				mtds['nodes'].append(self.objectNameFull)

		# set node class info
		memberData['classInfo'] = {
			"class": self.memberClass,
			"name": self.memberName,
			"type": "field" if self.isField else "method"
		}
		
	def _preregSystemNode(self):
		memberData = self.memberData
		if 'icon' in memberData:
			memberData['icon'] = memberData['icon'].replace('\\\\','\\') #self.preparePath(memberData['icon'])

		overrideRuntime = 'runtime_ports' in memberData

		if overrideRuntime:
			#register autoportdata if not exists
			if 'autoportdata' not in dict(memberData['options']):
				memberData['options'].append(('autoportdata', {
					"type":"hidden",
        			"default":{}
				}))

		# автоматическое выключение отображения имен портов если рендер тип подходит и пользователь не задал вручную режим отображения имени узлу
		#? Логику можно улучшить, сделав проверку определения для каждого порта
		canAutoSetDisplayNames = memberData.get('render_type',NodeRenderType.Default.name) in [n.name for n in NodeRenderType.getNoHeaderTypes()]
		if canAutoSetDisplayNames:
			#если найдены порты с определенным типом то мы не можем рендерить автоматически порты
			if [vData[1] for vData in self['inputs'] if vData[1].get('display_name') != None]:
				canAutoSetDisplayNames = False
			if [vData[1] for vData in self['outputs'] if vData[1].get('display_name') != None]:
				canAutoSetDisplayNames = False
		
		for k,v in self['inputs']:
			if overrideRuntime and v['type'] == 'auto':
				if not v.get('typeget'):
					v['typeget'] = 'ANY;@type'
				v['type'] = ''
			if v['type'] == "Exec":
				v["style"] = "triangle"
			if canAutoSetDisplayNames: #and 'display_name' not in v:
				v['display_name'] = False
		for k,v in self['outputs']:
			if overrideRuntime and v['type'] == 'auto':
				if not v.get('typeget'):
					v['typeget'] = 'ANY;@type'
				v['type'] = ''
			if v['type'] == "Exec":
				v["style"] = "triangle"
			if canAutoSetDisplayNames:
				v['display_name'] = False

	def _preregFunction(self):
		memberData = self.memberData
		classmeta = self.classMetadata
		functionName = self.objectNameFull
		isPure = self.execTypes in ['none','pure']
		if 'code' not in memberData:
			codecall = f'@cfParams call {functionName}'
			if not isPure:
				ldat = [idx for idx,(pn,pdat) in enumerate(memberData['outputs']) if pdat['type']!="Exec"]
				if len(ldat) > 1:
					raise Exception(f'Error on generate output info for function {functionName}')
				if len(ldat) == 1:
					codecall = f"private @genvar.out.{ldat[0]+1} = "+codecall
				codecall += "; @out.1"
			memberData['code'] = codecall
		if 'color' not in memberData:
			memberData['color'] = NodeColor.PureFunction.value if isPure else NodeColor.Function.value
		if 'icon' not in memberData:
			memberData['icon'] = "data\\icons\\icon_BluePrintEditor_Function_16px"
		
		#return type info
		for pn,pdat in memberData['outputs']:
			if pdat.get('type')!="Exec":
				memberData['returnType'] = pdat.get("type","null")
				if pdat.get('desc'):
					memberData['returnDesc'] = pdat.get('desc')
				break
			
	def _preregEnumNode(self):
		"""
			Подготовка свитча по перечислению
			Выполняет генерацию портов и кода свитчера по перечислению
			Регистрирует новый тип перечисления
		"""
		memberData = self.memberData
		self['inputs'].append(('Вход',{"type":"Exec","mutliconnect":True,"style":"triangle"}))
		enumTypeFull = f'{self.objectType}.{self.objectNameFull}'
		portEnumName = memberData.get('name') or self.objectNameFull
		self['inputs'].append(	(portEnumName,{
			"type":f'{enumTypeFull}',"mutliconnect":False
		})	)
		codegen = "call {private _eIt = @in.2;"
		for ienum,eDat in enumerate(self.enumList):
			enumItem = {
				"type":"Exec",
				"mutliconnect":False,
				"style":"triangle",
			}
			if eDat.get('desc'):
				enumItem['desc'] = eDat.get('desc')
			self['outputs'].append((eDat['name'],enumItem))
			#code generation
			codegen += f"if (_eIt == {eDat['val']} /*{self.objectNameFull}.{eDat['name']}*/) exitWith {{@out.{ienum+1}}};"
		codegen += "};"
		self['code'] = codegen
		self['name'] = f'Выбрать из {portEnumName}'
		self['namelib'] = f'Выбрать из перечисления {portEnumName}'
		self['icon'] = 'data\\icons\\icon_Blueprint_Switch_16x'
		self['color'] = NodeColor.EnumSwitch.value
		
		values = [[e['name'],e['val']] for e in self.enumList]

		enumListOption = (portEnumName, {
					"type":"list",
					"text": portEnumName,
					"default": self.enumList[0]['name'],
					"values": values,
				})
		self['options'].append(enumListOption)

		# регистрация информации об перечислении внутри спец.класса ReNode_AbstractEnum
		classmeta = self.classMetadata
		enumStorage = classmeta['ReNode_AbstractEnum']
		if 'allEnums' not in enumStorage: enumStorage['allEnums'] = {}
		enumStorage['allEnums'][enumTypeFull] = {
			'name': portEnumName,
			'values': [e['name'] for e in self.enumList],
			'enumList': self.enumList
		}

	def _preregStruct(self):
		memberData = self.memberData
		classmeta = self.classMetadata
		structStorage = classmeta['ReNode_AbstractEnum']
		if 'allStructs' not in structStorage: structStorage['allStructs'] = {}

		structTypeFull = f'{self.objectType}.{self.objectNameFull}'
		structName = memberData.get('name') or self.objectNameFull
		structList = self.structList #name,type,value,?desc

		structStorage['allStructs'][structTypeFull] = {
			'name': structName,
			'values': structList
		}

		# генерация make struct, break struct
		for helperType in ["make","break"]:
			newobj = self.copy(True)
			newobj.objectType = 'node'
			newobj.isStruct = False
			newobj.isSystem = True
			newobj.objectNameFull = f"structHelper"
			isMake = helperType == "make"
			newobj.execTypes = 'pure' if isMake else 'all'
			
			newobj.lineList.clear()
			structLines = [f"node:{structTypeFull}_{helperType}"]
			namebase_ = "Создать" if isMake else "Разобрать"
			structLines.append(f'name:{namebase_} {structName}')
			structLines.append(f'namelib:{namebase_} структуру {structName}')
			icnPath = 'icon_Blueprint_MakeStruct_16x' if isMake else 'icon_Blueprint_BreakStruct_16x'
			structLines.append(f'icon:data\\icons\\{icnPath}')
			clr__ = "StructMake" if isMake else "PureFunction"
			structLines.append(f'color:{clr__}')
			structLines.append(f'{"out" if isMake else "in"}:{structTypeFull}:{structName}{":" + memberData["desc"] if memberData.get("desc") else ""}')
			i_ = 1 if isMake else 2
			code = []
			for pInfo in structList:
				structLines.append(f'{"in" if isMake else "out"}:{pInfo["type"]}:{pInfo["name"]}{":" + pInfo["desc"] if pInfo.get("desc") else ""}')
				if isMake:
					structLines.append(f'opt:custom=1:def={self.structSerializedValues[pInfo["name"]]}')
					code.append(f'@in.{i_}')
				else:
					code.append(f'\"@genvar.out.{i_}\"')
				i_ += 1
			newobj.pushBackLines(structLines)
			__preCode = f'[{", ".join(code)}]'
			if not isMake:
				__preCode = "(@in.2)params " + __preCode + "; @out.1"
			newobj['code'] = __preCode

	def _portTypesPrepare(self):
		memberData = self.memberData
		classmeta = self.classMetadata
		vlib = self.varLib
		
		#ports check
		for ptype in ['inputs','outputs']:
			for pn,pv in memberData[ptype]:
				if 'type' in pv:
					tpval = pv['type']
					pv['type'] = self.__portTypeValidate(tpval)
					# if vlib.isObjectType(tpval,classmeta) and not tpval.endswith("^"):
					# 	pv['type'] = tpval + "^"
		#rtypecheck
		if 'returnType' in memberData:
			tpval = memberData['returnType']
			memberData['returnType'] = self.__portTypeValidate(tpval)
			# if vlib.isObjectType(tpval,classmeta) and not tpval.endswith("^"):
			# 	memberData['returnType'] = tpval + "^"

	def __portTypeValidate(self,fulltype):
		classmeta = self.classMetadata
		vlib = self.varLib
		typelist = vlib.decomposeType(fulltype)
		for idx, tname in enumerate(typelist):
			if idx == 0: continue
			if vlib.isObjectType(tname,classmeta) and not tname.endswith("^"):
				typelist[idx] += "^"
		return vlib.composeType(typelist)

	def registerNode(self,memberRegion):
		memberData = self.memberData
		classmeta = self.classMetadata

		#prep ports
		if self.execTypes in ['all','in']:
			self['inputs'].insert(0,('Вход',{
						'type':"Exec",
						'mutliconnect':True,
						"style": "triangle",
			}))
		if self.execTypes in ['all','out']:
			self['outputs'].insert(0,('Выход',{
						'type':"Exec",
						'mutliconnect':False,
						"style": "triangle"
			}))
		
		#проход по портам и опциям
		self._portTypesPrepare()

		if self.isClassMember: self._preregClassMember()
		if self.isField: self._preregField()
		if self.isMethod: self._preregMethod()

		if self.isEnum:
			self._preregEnumNode()
		if self.isStruct:
			self._preregStruct()
		if self.isSystem or self.isFunc:
			self._preregSystemNode()
		if self.isFunc:
			self._preregFunction()

		dataInputs = dict(self['inputs'])
		dataOutputs = dict(self['outputs'])
		self['inputs'] = dataInputs
		self['outputs'] = dataOutputs
		self['options'] = dict(self['options'])

		#обработка инпутов и отупутов
		typeLib = self.varLib
		typeLib.prepPortColors(memberData)

		# Добавляем опции
		for k,v in dataInputs.items():				
			if v.get('use_custom',False):
				ctype = v.get('type')
				if 'custom_type' in v:
					ctype = v.get('custom_type')
					del v['custom_type']
				del v['use_custom']
				opt = self.getVarlibOptionByType(ctype,k)
				if opt:
					self['options'][k] = opt
					if "typeset_out" in v:
						tSetPort = v['typeset_out']
						del v['typeset_out']
						opt['typeset_out'] = tSetPort
					if "port_rename" in v:
						tSetPort = v['port_rename']
						del v['port_rename']
						opt['port_rename'] = tSetPort

		if 'code' not in memberData and self.isMethod:
			self['code'] = self.generateMethodCodeCall()

		isInspectorProp = memberData.get('classProp',0) > 0
		if 'classProp' in memberData: del memberData['classProp']

		#prep code and icon
		#if 'icon' in memberData: self['icon'] = self.preparePath(self['icon'])
		#! код генерируется в рантайме при сборке
		#if 'code' in memberData: self['code'] = self.prepareCode(self['code'])
		#self.defCode = self.prepareCode(self.defCode)

		#register inspector prop
		if isInspectorProp:
			# регистрируем свойство для видимости в инспекторе
			prps__ = classmeta[self.memberClass]
			if not 'inspectorProps' in prps__: prps__['inspectorProps'] = {
				"fields": {}, #поля, доступные в инспекторе
				"methods": {} #методы, доступные в инспекторе
			}
			defvalue = memberData.get('defval',"$NULL$")
			rettype = self['returnType']

			parsedValue = self.varLib.parseGameValue(defvalue,rettype,self.classMetadata)

			propData = {
				'node': self.objectNameFull,
				'return': rettype,
				'defval': parsedValue
			}
			if self.isField:
				prps__['inspectorProps']['fields'][self.memberName] = propData
			elif self.isMethod:
				prps__['inspectorProps']['methods'][self.memberName] = propData

		# add to main lib
		self.nodeLib[memberRegion][self.objectNameFull] = memberData

		if self.defCode:
			memberData['defCode'] = self.defCode

def compileRegion(members,nodeLib,classmeta):
	curMember = None
	
	collectLines = []
	objectList = []

	# collecting tokens
	for __line in members.splitlines():
		line = __line.lstrip('\t ')
		if not line: continue
		#printDebug(f'compile line: {line}')
		tokens = getTokens(line) # def,type,memname
		if not tokens: raise ValueError(f"Wrong member line: {line}")
		tokenType = tokens[0]
		if tokenType == "def":
			#new define
			if curMember:
				objectList.append(curMember)
				collectLines = []
				curMember = None
			if len(tokens) < 3: raise ValueError(f"Wrong define member line: {line}")
			
			printDebug(f'compile node: {line}')

			memName = tokens[2]
			memType = tokens[1]
			collectLines = []
			curMember = NodeObjectHandler(memName,memType,nodeLib,classmeta,collectLines)
			curMember.refAllObjects = objectList
			continue
		
		collectLines.append(tokens)

	# adding last member
	if curMember:
		objectList.append(curMember)

	nextPath = ""
	while len(objectList) > 0:
		obj = objectList[0]
		
		# проброс пути
		if nextPath and obj.isSystem:
			obj['path'] = nextPath
		
		obj.generateJson() #generate main
		
		if obj.isSystem:
			nextPath = obj.memberData.get('path','')

# generate lib (using flag -genlib)
def GenerateLibFromObj():
	objFile = os.path.join("lib.obj")
	if not os.path.exists(objFile):
		print(f"File not found: {objFile}")
		return -1
	
	content:str = None

	outputData = {}

	with open(objFile,encoding="utf-8",mode='r') as file_handle:
		content = file_handle.read()
	
	dat = re.match("^v(\d+)",content)
	if not dat:
		print(f"Wrong obj file: {objFile}")
		return -2

	versionNum = int(dat[1])
	outputData['system'] = {'version':versionNum}
	nodeLib = {}
	outputData['nodes'] = nodeLib
	outputData['classes'] = {}
	print(f"Version objfile: {versionNum}")

	print("---------- Prep class metadata region ----------")
	if not checkRegionName(content,"CLASSMETA"):
		print(f"Corrupted classes region")
		return -3
	classmeta = getRegionData(content,"CLASSMETA",True)
	if not classmeta: 
		print(f'Empty classmeta')
		return -404
	outputData['classes'] = classmeta

	print("---------- Prep functions region ----------")
	if not checkRegionName(content,"functions"):
		print(f"Corrupted functions region")
		return -3

	functions = getRegionData(content,"functions")
	if not functions: 
		print(f'Empty functions data')
	compileRegion(functions,nodeLib,classmeta)
	
	print("---------- Prep class members region ----------")
	if not checkRegionName(content,"CLASSMEM"):
		print(f"Corrupted class members region")
		return -4
	
	members = getRegionData(content,"CLASSMEM")
	compileRegion(members,nodeLib,classmeta)

	#return 0
	print("Writing lib.json")
	with open("lib.json", 'w',encoding="utf-8") as fp:
		json.dump(
			outputData,
			fp,
			indent='\t',
			ensure_ascii=False
		)

	print("Done...")
	return 0