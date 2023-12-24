

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
	def getFolderScripts():
		return os.path.join(FileManagerHelper.getWorkDir(),"scripts")
	
	@staticmethod
	def find_files(root_dir, extension):
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
		
		