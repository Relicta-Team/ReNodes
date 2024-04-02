from ReNode.app.FileManager import FileManagerHelper
from ReNode.app.Logger import RegisterLogger
from ReNode.ui.VarMgrWidgetTypes.Widgets import VarMgrBaseWidgetType

import time
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from PyQt5.QtWidgets import QApplication, QSplashScreen, QLabel,QProgressBar
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import *
from copy import deepcopy
import threading


class VirtualLib(QObject):
	on_reload = pyqtSignal()

	def reload_impl(self):
		self.logger.debug("reload thread name: " + threading.currentThread().name)
		self.factory.loadFactoryFromJson("lib.json",True)

	class MyHandler(FileSystemEventHandler):
		def __init__(self) -> None:
			super().__init__()
			self.vlib = VirtualLib.refObject
			self.logger = VirtualLib.refObject.logger

		def reloadLibFull(self):
			self.vlib.logger.debug("reload call from " + threading.currentThread().name)
			self.vlib.on_reload.emit()

		def on_modified(self, event):
			if not event.is_directory and event.src_path.endswith('.graph'):
				self.logger.debug(f"File modified: {event.src_path}")
				#self.reloadLibFull()

		def on_created(self, event):
			if not event.is_directory and event.src_path.endswith('.graph'):
				self.logger.debug(f"File created: {event.src_path}")
				#self.reloadLibFull()

		def on_deleted(self, event):
			if not event.is_directory and event.src_path.endswith('.graph'):
				self.logger.debug(f"File deleted: {event.src_path}")
				#self.reloadLibFull()
		

	refObject = None
	def __init__(self,factory):
		super().__init__()
		from ReNode.app.NodeFactory import NodeFactory
		
		self.logger = RegisterLogger("VirtualLib")
		VirtualLib.refObject = self
		self.on_reload.connect(self.reload_impl)
		self.factory : NodeFactory = factory

		#! Пока глобальный обсервер выключен
		# path = '.'  # Замените на путь к вашей директории
		# self.file_event_handler = VirtualLib.MyHandler()
		# self.observer = Observer()
		# self.observer.schedule(self.file_event_handler, path, recursive=True)
		# self.observer.start()

	def generateUserLib(self):
		self.logger.info("Start searching graphs...")
		pathes = FileManagerHelper.getAllGraphPathes()
		self.logger.info(f'Found {len(pathes)} graphs')

		dataLib = []
		for path in pathes:
			data = FileManagerHelper.loadSessionJson(path)
			dataLib.append(data)
			self.processLoadingUserGraph(path,data,stage=0)
		
		#second pass (graph nodes generate)
		for i,path in enumerate(pathes):
			data = dataLib[i]
			self.processLoadingUserGraph(path,data,stage=1)

		self.factory.reloadNativeGeneratedInfo()

	def processLoadingUserGraph(self,path,data,stage=0):
		
		if data:
			vars = data['graph']['variables']
			infoData = data['graph']['info']



			if stage == 0:
				#class register
				newclass = {
					"baseClass": infoData['parent'],
					"defined": {"file":path,"line":1},
					"fields": {"defined": {}},
					"methods": {"defined": {}},
					"name": infoData['name'],
					"changedProps": infoData.get("props",{}),
					#baseList, __childList, __inhChild
				}
				if infoData.get('path'):
					newclass['path'] = infoData['path']
				if infoData.get('desc'):
					newclass['desc'] = infoData['desc']
				self.factory.classes[infoData['classname']] = newclass
				return
			
			if stage == 1:
				newclass = self.factory.classes[infoData['classname']]

			className = infoData['classname']
			redirectNeed = infoData.get('path','').startswith('.')
			if 'path' not in infoData or redirectNeed:
				basePath = "Пользовательские"
				if redirectNeed:
					basePath = infoData.get('path','')
				baseObj = className
				while baseObj:
					baseObj = self.factory.getClassParent(baseObj)
					if not baseObj: break

					cdict = self.factory.getClassData(baseObj)
					if cdict.get('path'):
						if redirectNeed:
							basePath = cdict['path'] + basePath
							if not basePath.startswith("."): break
						else:
							basePath = cdict['path']+'.'+infoData['name']
							break

				newclass['path'] = basePath

			self._regenerateUserLib(vars,className,newclass)
	
	def _regenerateUserLib(self,vars,className,newclass):
		from ReNode.app.LibGenerator import compileRegion
		mdataAll = []
		for cat,varlist in vars.items():

				gType = VarMgrBaseWidgetType.getInstanceByType(cat)
				if gType:
					for v,dat in varlist.items():
						sysname = dat['systemname']
						classDict = {
							"className": className,
							"memberName": sysname,
							"path": newclass.get('path',''),
							"classObject": newclass
						}
						mdata = gType.onCreateVLibData(self.factory,dat,classDict)
						mdataAll.append(mdata)
			
		memberData = '\n'.join(mdataAll)
		factRet = {}
		compileRegion(memberData,factRet,self.factory.classes)

		for cat,ndat in factRet.items():
			for nodename,nodedata in ndat.items():
				self.factory.registerNodeInLib(cat,nodename,nodedata)
		
		pass

	def onUpdateUserVariables(self,infoData,vars):
		"""Вызывается для перезагрузки библиотеки"""
		from ReNode.ui.NodeGraphComponent import NodeGraphComponent
		graphObj = NodeGraphComponent.refObject
		cls = infoData['classname']
		
		classData = graphObj.getFactory().getClassData(cls)
		if not classData:
			#full regenerate user library
			#self.generateUserLib() nodes and classes not empty
			#self.factory.loadFactoryFromJson("lib.json")
			return

		#удаляем все пользовательские узлы для этого графа
		for nodename in classData['methods'].get('nodes',[]):
			del self.factory.nodes["methods."+nodename]
		for nodename in classData['fields'].get('nodes',[]):
			del self.factory.nodes["fields."+nodename]
		
		classData['methods']['defined'] = {}
		classData['methods']['nodes'] = []
		classData['fields']['defined'] = {}
		classData['fields']['nodes'] = []
		if 'inspectorProps' in classData:
			del classData['inspectorProps']
		
		pps = classData.get('props',{})
		classData['changedProps'] = {
			"fields": deepcopy(pps.get('fields',{})),
			"methods": deepcopy(pps.get('methods',{})),
		}

		self._regenerateUserLib(vars,cls,classData)

		graphObj.inspector.updateProps()
		graphObj.generateTreeDict()

		newTree = graphObj.getTabSearch().dictTreeGen

		#update all tabs
		curtab = graphObj.sessionManager.getActiveTabData()
		for tObj in [tab for tab in graphObj.sessionManager.getAllTabs() if tab != curtab]:
			tObj.graph.isDirty = True
			tObj.graph.dirty_check(newTree)

		pass