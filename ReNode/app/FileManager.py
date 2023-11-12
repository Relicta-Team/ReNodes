

import os
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