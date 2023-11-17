
import re
import os
import json
import copy
from ReNode.app.utils import intTryParse

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
	print(f"DEBUG: {str}")


def getTokens(content):
	return re.split(r'(?<!\\):', content)

class NodeObjectHandler:
	def __init__(self,objName,objectType,nodeLibDict,classMetadata,__lineList):
		self.nodeLib = nodeLibDict #ссылка на базовый словарь узлов
		self.classMetadata = classMetadata #ссылка на словарь метаданных классов
		self.objectNameFull = objName #базовое полное имя члена
		self.objectType = objectType #тип-категория члена (метод, поле, функция)

		self.lineList : list = __lineList #ссылка на список обрабатываемых строк

		self.isClass = self.objectType == 'c'
		self.isField = self.objectType == 'f'
		self.isMethod = self.objectType == 'm'
		self.isSystem = self.objectType == 'node'

		self.refAllObjects : list = None #Ссылка на все объекты
		self.counterCopy = 0

		self.execTypes = 'all' #all,in,out,none

		self.path = "" # путь до узла в дереве

		self.defCode = "" #код инициализации (опциональный). помещается 

		self.memberData = {
			# порты при финализации конвертируются в словарь
			# записанные значения: tuple(name:str,data:dict)
			"inputs": [],#{},
			"outputs": [],#{},
			"options": [],#{}
		}
		self.lastPortRef = None

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
		
		dst.memberClass = src.memberClass
		dst.memberName = src.memberName
		dst.memberNameFull = src.memberNameFull

		dst.refAllObjects = src.refAllObjects
		if addToAllObjects:
			if len(dst.refAllObjects) <= 1:
				dst.refAllObjects.append(dst)
			else:
				dst.refAllObjects.insert(1,dst)
		return dst

	def preparePath(self,path):
		return path.replace('\\\\','\\').replace('\\','\\\\')

	def prepareCode(self,code):
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
		code = '[@in.2'
		addingParams = []
		for i, (k,v) in enumerate(self['inputs'].items()):
			if v['type'] != "Exec" and v['type'] != "":
				addingParams.append(f'@in.{i+1}')
		
		paramString = ", ".join(addingParams)
		if paramString: paramString = ", " + paramString
		code += paramString + f"] call ((@in.2) getVariable PROTOTYPE_VAR_NAME getVariable \"{self.memberName}\")"
		
		#TODO записываем возвращаемое значение в переменную только если нода возвращаемого значения мультивыход
		#if self.memberData.get('returnType') not in ['void','null','']:
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
			self.memberData['desc'] = tokens[1]
		elif tokenType == "path":
			self.memberData['path'] = tokens[1]
		# возвращаемое значение
		elif tokenType == "return":
			self.memberData['returnType'] = tokens[1]
			if len(tokens) > 2:
				self.memberData['returnDesc'] = tokens[2]
		elif tokenType == 'prop':
			propType = tokens[1]
			if propType not in ['all','get','set','none']:
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
		#method specific data

		#method type: method,event,get,const
		elif tokenType == 'type':
			mtype = tokens[1]
			self.memberData['type'] = mtype
			if mtype in ['event','get','const']:
				self.execTypes = 'out'
			if mtype == "const":
				self.memberData['classProp'] = 1
		elif tokenType == 'exec':
			execType = tokens[1]
			self.execTypes = execType
		elif tokenType == "in":
			
			self.lastPortRef = {
				'type': tokens[1],
			}
			if len(tokens) > 3:
				self.lastPortRef['desc'] = tokens[3]
			#self.memberData['inputs'][tokens[2]] = self.lastPortRef
			self.memberData['inputs'].append((tokens[2],self.lastPortRef))
		elif tokenType == "out":
			
			self.lastPortRef = {
				'type': tokens[1],
				'mutliconnect':True
			}
			if len(tokens) > 3:
				self.lastPortRef['desc'] = tokens[3]
			#self.memberData['outputs'][tokens[2]] = self.lastPortRef
			self.memberData['outputs'].append((tokens[2],self.lastPortRef))
		elif tokenType == 'opt':
			for tInside in tokens[1:]:
				if tInside.startswith("mul"):
					self.lastPortRef['mutliconnect'] = intTryParse(tInside.split('=')[1]) > 0
				if tInside.startswith("dname"):
					self.lastPortRef['display_name'] = intTryParse(tInside.split('=')[1]) > 0
				if tInside.startswith('allowtypes'):
					self.lastPortRef['allowtypes'] = tInside.split('|')
		
		# -------------------- common spec options -------------------- 
		
		# redef node name
		elif tokenType == 'node':
			self.objectNameFull = tokens[1]
		# def visible node in treeview
		elif tokenType == "libvisible":
			if intTryParse(tokens[1]) == 0:
				self.memberData['isVisibleInLib'] = False
		# enable ports with autotypes
		elif tokenType == "runtimeports":
			if intTryParse(tokens[1]) > 0:
				self.memberData['runtime_ports'] = True
		# add specific option to node
		elif tokenType == "option":
			_cont :str= tokens[1]
			if not _cont.strip(' \t\n\r').startswith("{"):
				_cont = "{"+_cont+"}"
			_ser = json.loads(_cont)
			for k,v in _ser.items():
				if k in self['options']:
					self.exThrow(f"Duplicate option: {k}")
				self['options'][k] = v

		pass

	def finalizeClass(self):
		classDict = self.classMetadata[self.memberClass]
		#saving pathes etc.
		if 'name' in self.memberData: classDict['name'] = self['name']
		if 'desc' in self.memberData: classDict['desc'] = self['desc']
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
		elif self.isSystem:
			memberRegion = self.objectType #internal,operators,etc
		else:
			raise Exception(f'Unknown member type: {self.objectType}')

		if memberRegion not in self.nodeLib:
			self.nodeLib[memberRegion] = {}

		# Проверка возвращаемого типа и его автоопределение
		if 'returnType' not in memberData:
			
			if self.isField:
				memberData['returnType'] = classmeta[self.memberClass]['fields']['defined'].get(self.memberName,'NULLTYPE_ALLOC')
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

			tableTypes = ["method","event","get","const"]
			if mtype not in tableTypes:
				raise ValueError(f"[{self.objectNameFull}]: Wrong method type: {mtype}")

			# register member ports
			#if mtype

			_canOverrideCodeDef = self.defCode == ''
			_canOverrideColor = "color" not in self.memberData
			_canOverrideIcon = 'icon' not in self.memberData
			if _canOverrideCodeDef:
				if mtype == "get":
					newcode = 'func(@thisName) {@thisParams; @out.1}'
				elif mtype == "const":
					newcode = 'func(@thisName) { @propvalue }'
				else:
					newcode = 'func(@thisName) {@thisParams; @out.1}'
				self.defCode = newcode
			if _canOverrideColor:
				nodeColorList = [
					[255,255,255],#method
					[255,255,255],#event
					[255,255,255],#getter
					[255,255,255],#constant
				]
				newColor = nodeColorList[tableTypes.index(mtype)]
				self['color'] = newColor
			if _canOverrideIcon:
				iconList = [
					"test.png",#method
					"test.png",#event
					"test.png",#getter
					"test.png",#constant
				]
				self['icon'] = iconList[tableTypes.index(mtype)]


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

			if curPropType == 'none':
				memberData = None
			elif curPropType in ['all','get','set']:
				_hasGet = curPropType in ['all','get']
				_hasSet = curPropType in ['all','set']
				if _hasGet:
					newobj = self.copy(True)
					newobj.objectNameFull += f".get"
					newobj['code'] = f'this getVariable "{newobj.memberName}"'
					newobj.execTypes = 'all'
					newobj.pushBackLines([
						f'out:{newobj["returnType"]}:Значение'
					])
				if _hasSet:
					newobj = self.copy(True)
					newobj.objectNameFull += f".set"
					newobj['code'] = f'this setVariable ["{newobj.memberName}",@in.2]; @out.1'
					newobj.execTypes = 'all'
					_setterLines = [
						f"in:{newobj['returnType']}:Значение",
						f'out:{newobj["returnType"]}:Новое значение'
					]
					if newobj.memberData.get('classProp',0) > 0 and _hasGet:
						_setterLines.append('classprop:0') #disable classprop for setter because getter already setup
					newobj.pushBackLines(_setterLines)
					
				
				#set memdata to null 
				memberData = None
		

		# регистрация узла
		if memberData:
			
			#Если пути нет - генерируем его
			if 'path' not in memberData:
				memberData['path'] = classmeta[self.memberClass].get('path','')

			#prep ports
			if self.execTypes in ['all','in']:
				self['inputs'].insert(0,('Вход',{
							'type':"Exec",
							'mutliconnect':True
				}))
			if self.execTypes in ['all','out']:
				self['outputs'].insert(0,('Выход',{
							'type':"Exec",
							'mutliconnect':False
				}))
			
			# Помещаем инстансер
			if self.isMethod:
				self['inputs'].insert(1,("Цель", {"type": "self", 'desc':"Инициатор вызова метода, функции или события."}))
				instanceOption = ("Цель", {
						"type":"list",
						"disabledListInputs": ["Этот объект"],
						"text": "Вызывающий",
						"default": "Этот объект",
						"values": [["Этот объект","this"], "Объект"],
						"typingList": ["self",f"{self.memberClass}^"]
					})
				self['options'].insert(0,instanceOption)

			dataInputs = dict(self['inputs'])
			dataOutputs = dict(self['outputs'])
			self['inputs'] = dataInputs
			self['outputs'] = dataOutputs
			self['options'] = dict(self['options'])

			if 'code' not in memberData:
				self['code'] = self.generateMethodCodeCall()

			isInspectorProp = memberData.get('classProp',0) > 0
			if 'classProp' in memberData: del memberData['classProp']

			#prep code and icon
			if 'icon' in memberData: self['icon'] = self.preparePath(self['icon'])
			if 'code' in memberData: self['code'] = self.prepareCode(self['code'])
			self.defCode = self.prepareCode(self.defCode)

			#register inspector prop
			if isInspectorProp:
				# регистрируем свойство для видимости в инспекторе
				prps__ = classmeta[self.memberClass]
				if not 'inspectorProps' in prps__: prps__['inspectorProps'] = {
					"fields": {}, #поля, доступные в инспекторе
					"methods": {} #методы, доступные в инспекторе
				}
				propData = {
					'node': self.objectNameFull,
					'return': self['returnType'],
					'defCode': self.defCode,
				}
				if self.isField:
					prps__['inspectorProps']['fields'][self.memberName] = propData
				elif self.isMethod:
					prps__['inspectorProps']['methods'][self.memberName] = propData

			# add to main lib
			self.nodeLib[memberRegion][self.objectNameFull] = memberData

			#add node inside class zone
			if self.isField:
				flds = classmeta[self.memberClass]['fields']
				
				if 'nodes' not in flds: flds['nodes'] = []
				flds['nodes'].append(self.objectNameFull)

			if self.isMethod:
				mtds = classmeta[self.memberClass]['methods']
				
				if 'nodes' not in mtds: mtds['nodes'] = []
				mtds['nodes'].append(self.objectNameFull)

def compileRegion(members,nodeLib,classmeta):
	curMember = None
	
	collectLines = []
	objectList = []

	# collecting tokens
	for __line in members.splitlines():
		line = __line.lstrip('\t ')
		if not line: continue
		printDebug(f'compile line: {line}')
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

	while len(objectList) > 0:
		obj = objectList[0]
		obj.generateJson() #generate main

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
	#compileRegion(functions,nodeLib,classmeta)
	
	print("---------- Prep class members region ----------")
	if not checkRegionName(content,"CLASSMEM"):
		print(f"Corrupted class members region")
		return -4
	
	members = getRegionData(content,"CLASSMEM")
	compileRegion(members,nodeLib,classmeta)

	return 0
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