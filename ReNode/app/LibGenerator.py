
import re
import os
import json
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
	outputData['nodes'] = {}
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

	
	print("---------- Prep class members region ----------")
	if not checkRegionName(content,"CLASSMEM"):
		print(f"Corrupted class members region")
		return -4
	
	members = getRegionData(content,"CLASSMEM")
	global memberData
	global curMemberType
	global curMember
	memberData = None
	lastPortRef = None

	curMember = None
	curMemberType = None
	nodeList = {}
	def finalizeNode():
		global memberData
		global curMemberType
		global curMember

		if re.match(r'_\d+$',curMember):
			clearMem = curMember[:curMember.rfind('_')]
		else:
			clearMem = curMember
		className_, memName_ = clearMem.lower().split('.')

		# Проверка возвращаемого типа и его автоопределение
		if 'returnType' not in memberData:
			#if curMember endswith regex _\d+ then remove postfix
			
			if curMemberType == 'f':
				memberData['returnType'] = classmeta[className_]['fields']['defined'].get(memName_,'NULLTYPE_ALLOC')
			else:
				memberData['returnType'] = "return_void"

		# Определение свойств поля (геттеры, сеттеры)
		if curMemberType == 'f':
			if 'prop' not in memberData:
				memberData['prop'] = 'all'
			curPropType = memberData['prop']
			del memberData['prop']
			if curPropType == 'none':
				memberData = None
			elif curPropType in ['all','get','set']:
				orig_curMember = curMember
				curMember = [orig_curMember + ".get",orig_curMember + '.set']
				memberData = [memberData.copy(),memberData.copy()]
				memberData[0]['code'] = f'this getVariable "{memName_}"'
				memberData[1]['code'] = f'this setVariable ["{memName_}",@in.2]; @out.1'
				if curPropType != "all":
					__idx = 0 if curPropType == 'get' else 1
					curMember = curMember[__idx]
					memberData = memberData[__idx]
		
		if memberData:
			if isinstance(curMember,list):
				for i,cm in enumerate(curMember):
					nodeList[cm] = memberData[i]
			else: 
				nodeList[curMember] = memberData
		curMember = None
		
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
				finalizeNode()
			if len(tokens) < 3: raise ValueError(f"Wrong define member line: {line}")
			memberData = {
				"inputs": {},
				"outputs": {}
			}
			curMember = tokens[2]
			curMemberType = tokens[1]

		# Имя ноды
		if tokenType == "name":
			memberData['name'] = tokens[1]
			pass
		# имя ноды в дереве выбора
		elif tokenType == "namelib":
			memberData['namelib'] = tokens[1]
			pass
		# описание ноды
		elif tokenType == "desc":
			memberData['desc'] = tokens[1]
		# возвращаемое значение
		elif tokenType == "return":
			memberData['returnType'] = tokens[1]
			if len(tokens) > 2:
				memberData['returnDesc'] = tokens[2]
		elif tokenType == 'prop':
			propType = tokens[1]
			if propType not in ['all','get','set','none']:
				raise ValueError(f"[{curMember}]: Wrong prop type: {propType}")
			memberData['prop'] = propType
			pass
		# видимость ноды в инспекторе
		elif tokenType == 'classprop':
			clsprop = intTryParse(tokens[1])
			if clsprop:
				#todo need return type
				memberData['classProp'] = clsprop
			pass
		#method specific data

		#method type: method,event,get,const
		elif tokenType == 'type':
			mtype = tokens[1]
			if mtype not in ['method','event','get','const']:
				raise ValueError(f"[{curMember}]: Wrong method type: {mtype}")
			memberData['type'] = mtype
			#todo define icon and node color by type
			#const - add classProp
			if mtype == "const":
				memberData['classProp'] = 1
		elif tokenType == 'exec':
			execType = tokens[1]
			if execType not in ['in','out','none','all']:
				raise ValueError(f"[{curMember}]: Wrong exec type: {execType}")
			if execType == 'none':
				continue
			_addIn = execType in ['in','all']
			_addOut = execType in ['out','all']
			if _addIn:
				if memberData['inputs']:
					raise Exception(f'[{curMember}]: inputs must be empty after adding exec port')
				memberData['inputs']['Вход'] = {
					'type':"Exec",
					'mutliconnect':True
				}
			if _addOut:
				if memberData['outputs']:
					raise Exception(f'[{curMember}]: outputs must be empty after adding exec port')
				memberData['outputs']['Выход'] = {
					'type':"Exec",
					'mutliconnect':False
				}
		elif tokenType == "in":
			
			lastPortRef = {
				'type': tokens[1],
			}
			if len(tokens) > 3:
				lastPortRef['desc'] = tokens[3]
			memberData['inputs'][tokens[2]] = lastPortRef
		elif tokenType == "out":
			
			lastPortRef = {
				'type': tokens[1],
				'mutliconnect':True
			}
			if len(tokens) > 3:
				lastPortRef['desc'] = tokens[3]
			memberData['outputs'][tokens[2]] = lastPortRef
			pass
		elif tokenType == 'opt':
			for tInside in tokens[1:]:
				if tInside.startswith("mul"):
					lastPortRef['mutliconnect'] = intTryParse(tInside.split('=')[1]) > 0
				if tInside.startswith("dname"):
					lastPortRef['display_name'] = intTryParse(tInside.split('=')[1]) > 0
				if tInside.startswith('allowtypes'):
					lastPortRef['allowtypes'] = tInside.split('|')

	finalizeNode()

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