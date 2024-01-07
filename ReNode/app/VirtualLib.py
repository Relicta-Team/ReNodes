from ReNode.app.FileManager import FileManagerHelper
from ReNode.app.Logger import RegisterLogger
from ReNode.app.utils import transliterate
from ReNode.ui.VarMgrWidgetTypes.Widgets import VarMgrBaseWidgetType
import time
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler

class VirtualLib:

	class MyHandler(FileSystemEventHandler):
		def __init__(self) -> None:
			super().__init__()
			self.vlib = VirtualLib.refObject
			self.logger = VirtualLib.refObject.logger

		def reloadLibFull(self):
			self.vlib.factory.loadFactoryFromJson("lib.json")

		def on_modified(self, event):
			if not event.is_directory and event.src_path.endswith('.graph'):
				self.logger.debug(f"File modified: {event.src_path}")
				self.reloadLibFull()

		def on_created(self, event):
			if not event.is_directory and event.src_path.endswith('.graph'):
				self.logger.debug(f"File created: {event.src_path}")
				self.reloadLibFull()

		def on_deleted(self, event):
			if not event.is_directory and event.src_path.endswith('.graph'):
				self.logger.debug(f"File deleted: {event.src_path}")
				self.reloadLibFull()
		

	refObject = None
	def __init__(self,factory):
		from ReNode.app.NodeFactory import NodeFactory
		
		self.logger = RegisterLogger("VirtualLib")
		VirtualLib.refObject = self
		self.factory : NodeFactory = factory

		path = '.'  # Замените на путь к вашей директории
		event_handler = VirtualLib.MyHandler()
		observer = Observer()
		observer.schedule(event_handler, path, recursive=True)
		observer.start()

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
					#baseList, __childList, __inhChild
				}
				self.factory.classes[infoData['classname']] = newclass
				return
			
			if stage == 1:
				newclass = self.factory.classes[infoData['classname']]

			basePath = "Пользовательские"
			className = infoData['classname']
			baseObj = className
			while baseObj:
				baseObj = self.factory.getClassParent(baseObj)
				if not baseObj: break

				cdict = self.factory.getClassData(baseObj)
				if cdict.get('path'):
					basePath = cdict['path']
					break

			newclass['path'] = basePath+'.'+infoData['name']

			self._regenerateUserLib(vars,className,newclass)
	
	def _regenerateUserLib(self,vars,className,newclass):
		from ReNode.app.LibGenerator import compileRegion
		mdataAll = []
		for cat,varlist in vars.items():

				gType = VarMgrBaseWidgetType.getInstanceByType(cat)
				if gType:
					for v,dat in varlist.items():
						sysname = transliterate(dat['name'])
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