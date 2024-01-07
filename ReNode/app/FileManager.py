

import os
import json
from ReNode.app.config import Config

class FileManagerHelper:
	@staticmethod
	def getWorkDir():
		return Config.get_str("workdir","main")
	
	@staticmethod
	def getGraphPathRelative(path):
		if os.path.isdir(path):
			raise Exception(f"Path must be file: {path}")
		if os.path.isabs(path):
			return os.path.relpath(path, FileManagerHelper.getWorkDir())
		return ""


	@staticmethod
	def getFolderCompiledScripts():
		"""Получает путь скомпилирвоанных скриптов"""
		return os.path.join(FileManagerHelper.getWorkDir(),"compiled")
	
	@staticmethod
	def getCompiledScriptFilename(iData):
		return f'{iData["type"]}.{iData["parent"]}.{iData["classname"]}.sqf'

	@staticmethod
	def generateScriptLoader():
		from ReNode.app.application import Application
		compiled_folder_path = FileManagerHelper.getFolderCompiledScripts()
		loader_path = os.path.join(compiled_folder_path,"script_list.hpp")
		with open(loader_path, "w+", encoding="utf-8") as file:
			file.write("//generated by ReNode {}".format(Application.getVersionString()))
			files = FileManagerHelper.find_files(compiled_folder_path,"sqf")
			for filepath in files:
				file.write(f'\n{filepath}')
		

	@staticmethod
	def find_files(root_dir, extension):
		"""Поиск всех файлов с указанным расширенем, начиная от папки root_dir. Расширение указывается без точки"""
		files = []
		for dirpath, dirnames, filenames in os.walk(root_dir):
			for filename in filenames:
				if filename.endswith(f".{extension}"):
					files.append(os.path.join(dirpath, filename))
		return files

	# получить пути всех графов
	@staticmethod
	def getAllGraphPathes():
		rootDir = FileManagerHelper.getWorkDir()
		return FileManagerHelper.find_files(rootDir,"graph")
	
	@staticmethod
	def loadSessionJson(file_path) -> dict|None:
		"""Загружает граф из json файла в словарь и возвращает его"""
		layout_data = None
		try:
			with open(file_path) as data_file:
				layout_data = json.load(data_file)
		except Exception as e:
			layout_data = None

		return layout_data
		
		