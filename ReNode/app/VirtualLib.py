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
		from ReNode.app.LibGenerator import compileRegion
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
			
			mdataAll = []

			newclass['path'] = basePath+'.'+infoData['name']

			for cat,varlist in vars.items():

				gType = VarMgrBaseWidgetType.getInstanceByType(cat)
				if gType:
					for v,dat in varlist.items():
						sysname = transliterate(dat['name'])
						classDict = {
							"className": className,
							"memberName": sysname,
							"path": basePath,
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
		