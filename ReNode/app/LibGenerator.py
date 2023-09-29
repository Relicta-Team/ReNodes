
import re
import os
import json

def checkRegionName(content,regname : str):
	upperName = regname.upper()
	return f"$REGION:{upperName}" in content and f"$ENDREGION:{upperName}" in content

def getRegionData(content:str,region_name:str) -> dict | None:
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
	decoded_data = json.loads(region_data)

	return decoded_data

# generate lib (using flag -genlib)
def GenerateLibFromObj():
	objFile = os.path.join("lib_obj.json")
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
	print(f"Version objfile: {versionNum}")

	print("---------- Prep functions region ----------")
	if not checkRegionName(content,"functions"):
		print(f"Corrupted functions region")
		return -3

	functions = getRegionData(content,"functions")
	if not functions: return -404

	commonValues = None
	for cat_or_region,data in functions.items():
		#cat_or_region:str = cat_or_region
		if cat_or_region.startswith("@"):
			commonValues:dict = data
			data:dict = commonValues['list']
			commonValues.pop('list')
			cat_or_region = commonValues.get('cat',"SystemCategory")
			commonValues.pop('cat')

		catlist = outputData['nodes'].get(cat_or_region)
		if not catlist:
			catlist = {}
			outputData['nodes'][cat_or_region] = catlist
		
		def applybase(curval,replacercommon = ""):
			if not isinstance(curval,str): return curval

			if "@base" in curval:
				return re.sub("\@base",replacercommon,curval)
			return curval

		for nodename,nodedata in data.items():
			nodedata:dict=nodedata
			if commonValues:
				nodedata = {key: applybase( nodedata.get(key, commonValues.get(key)) , commonValues.get(key)) for key in set(nodedata) | set(commonValues)}

			# override port keynames
			if nodedata.get('in'):
				nodedata['inputs'] = nodedata.get('in')
				nodedata.pop('in')
			
			if nodedata.get('out'):
				nodedata['outputs'] = nodedata.get('out')
				nodedata.pop('out')

			catlist[nodename] = nodedata

		commonValues = None

	print("---------- Prep class members region ----------")

	print("---------- Prep class metadata region ----------")

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