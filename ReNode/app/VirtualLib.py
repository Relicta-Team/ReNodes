from ReNode.app.FileManager import FileManagerHelper
from ReNode.app.Logger import RegisterLogger
from ReNode.app.utils import transliterate
from ReNode.ui.VarMgrWidgetTypes.Widgets import VarMgrBaseWidgetType

class VirtualLib:
	refObject = None
	def __init__(self,factory):
		from ReNode.app.NodeFactory import NodeFactory
		self.logger = RegisterLogger("VirtualLib")
		VirtualLib.refObject = self
		self.factory : NodeFactory = factory
	
	def generateUserLib(self):
		self.logger.info("Start searching graphs...")
		pathes = FileManagerHelper.getAllGraphPathes()
		self.logger.info(f'Found {len(pathes)} graphs')

		for path in pathes:
			self.processLoadingUserGraph(path)

		self.factory.reloadNativeGeneratedInfo()

	def processLoadingUserGraph(self,path):
		data = FileManagerHelper.loadSessionJson(path)
		if data:
			vars = data['graph']['variables']
			infoData = data['graph']['info']

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

			basePath = "Пользовательские"
			className = infoData['classname']
			baseObj = className
			while baseObj:
				baseObj = self.factory.getClassParent(baseObj)
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
							"path": newclass['path'],
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
		
		#удаляем все пользовательские узлы для этого графа
		for nodename in classData['methods']['nodes']:
			del self.factory.nodes["methods."+nodename]
		for nodename in classData['fields']['nodes']:
			del self.factory.nodes["fields."+nodename]
		
		classData['methods']['defined'] = {}
		classData['methods']['nodes'] = []
		classData['fields']['defined'] = {}
		classData['fields']['nodes'] = []
		del classData['inspectorProps']

		self._regenerateUserLib(vars,cls,classData)

		graphObj.inspector.updateProps()

		pass