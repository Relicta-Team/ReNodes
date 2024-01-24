from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ReNode.app.Logger import RegisterLogger
from ReNode.app.utils import transliterate
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_file_paths import PropFileSavePath
from ReNode.ui.SearchMenuWidget import SearchComboButton,addTreeContent,createTreeDataContent
from ReNode.ui.GraphTypes import GraphTypeFactory as gtf, GraphTypeBase
import re
import sys
import os

class ScriptMakerManager(QWizard):
	"""
		Менеджер создания скриптов
	"""
	refObject = None
	def __init__(self,gsys):
		super().__init__(gsys.mainWindow)
		ScriptMakerManager.refObject = self
		self.logger = RegisterLogger("ScriptMakerManager")
		self.graphSystem = gsys 
		pass

	def openMaker(self):
		# Страница выбора типа скрипта
		wiz = WizardScriptMaker(self.graphSystem)


class WizardScriptMaker(QWizard):
	
	def __init__(self,gsys):
		super().__init__(gsys.mainWindow)
		self.graphSystem = gsys 
		self.setAttribute(Qt.WA_DeleteOnClose,True)
		self.setFixedSize(800,600)

		#self.setPixmap(QWizard.WizardPixmap.LogoPixmap,QPixmap(".\\data\\pic.png").scaled(32,32,Qt.KeepAspectRatio))
		#self.setPixmap(QWizard.WizardPixmap.BackgroundPixmap,QPixmap(".\\data\\splash.png"))
		#self.setPixmap(QWizard.WizardPixmap.BannerPixmap,QPixmap(".\\data\\splash.png"))
		#self.setPixmap(QWizard.WizardPixmap.WatermarkPixmap,QPixmap(".\\data\\splash.png").scaled(128,128,Qt.KeepAspectRatio))

		#self.setWindowFlags(Qt.FramelessWindowHint)
		self.setWindowFlag(Qt.WindowContextHelpButtonHint,False)
		self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
		self.setWindowModality(Qt.ApplicationModal)
		self.setWindowTitle("Менеджер создания графов")
		
		#change background color
		bluepalette = QPalette()
		bluepalette.setColor(QPalette.Background,Qt.black)
		self.setPalette(bluepalette)

		self.setupDict = {} #all settings for graph

		self._lastPage = None
		self._lastPath = []
		self._dictPathes = {}
		self.currentIdChanged.connect(self.disable_back)
		
		self.create_wizard()



		self.show()

	def getSetupDict(self):
		"""
		- type - тип графа (gamemode, role, etc...)
		- name - имя графа
		- classname - имя класса графа
		- parent - родительский класс 
		- path - путь до файла с графом
		"""
		return self.setupDict

	def disable_back(self, ind):
		self.button(QWizard.BackButton).setVisible(ind > 0)

	def _registerPage(self,title,subtitle=None,dictPageId=None):
		item = WizardScriptMakerPage(self.graphSystem)
		self._lastPage = item
		self._lastLayout = QVBoxLayout()
		item.setTitle(title)
		item.setLayout(self._lastLayout)
		if subtitle:
			item.setSubTitle(subtitle)
		id = self.addPage(item)
		if dictPageId:
			if dictPageId not in self._dictPathes:
				self._dictPathes[dictPageId] = []
			self._dictPathes[dictPageId].append(id)
		return item

	def _addLabel(self,text,wordWrap=True,isRichText=False):
		item = QLabel(text)
		if isRichText:
			item.setTextFormat(Qt.RichText)
		item.setWordWrap(wordWrap)
		self._lastLayout.addWidget(item)
		return item

	def _addSpacer(self):
		item = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
		self._lastLayout.addItem(item)
		return item

	def _addLineOption(self,text,optWidget,row=0,col=0,rowspan=1,colspan=1):
		item = QGridLayout()
		#item.setSpacing(20)
		lab = QLabel(text)
		#lab.setFixedWidth(200)
		item.addWidget(lab,row,col,rowspan,colspan)
		item.addWidget(optWidget,row,col+1,rowspan,colspan)
		self._lastLayout.addLayout(item)
		#item.setSizeConstraint(QGridLayout.SizeConstraint.SetMinimumSize)
		
		return lab,optWidget,item

	def createIntro(self):
		self._registerPage("Создание графов ReNode")
		self._lastLayout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
		self._addLabel("Добро пожаловать в менеджер создания графов ReNode!\n\n"+
			"Сейчас вам будет предложено создать новый граф.")
		
		self._addLabel(f"Для продолжения нажмите кнопку \"{self.button(QWizard.NextButton).text().replace('&','')}\".")
	
	def createSelectScriptType(self):
		page = self._registerPage("Общие настройки")

		combo = QComboBox()

		options : list[GraphTypeBase] = gtf.getAllInstances()
		

		for o in options:
			combo.addItem(o.name)
			curIdx = combo.count()-1
			combo.setItemData(curIdx,o.systemName)
			combo.setItemData(curIdx,o.description,Qt.ToolTipRole)

		self._addLineOption("Тип графа:",combo)
		item = self._addLabel("",isRichText=True)
		combo.setCurrentIndex(0)
		def setDesc():
			item.setText("<span style=\"font-size:18pt\">Описание: " + options[combo.currentIndex()].getDescription() + "</span>")
			sysname = options[combo.currentIndex()].systemName
			for id  in self._dictPathes.get(sysname,[]):
				pass
		setDesc()
		combo.currentIndexChanged.connect(lambda: setDesc())

		def defineNextId():
			lst = self._dictPathes.get(options[combo.currentIndex()].systemName,[])
			if lst:
				return lst[0]
			else:
				return self.pageIds()[len(self.pageIds())-1]
		page.nextId = defineNextId

		self._addSpacer()
		postText = self._addLabel("",isRichText=True)

		def validate():
			data = combo.currentData()
			gobj = gtf.getInstanceByType(data)
			if not gobj.canCreateFromWizard:
				postText.setText(f"<span style=\"color:red; font-size:18pt\">На данный момент создание типа \"{gobj.name}\" не реализовано.</span>")
				return False
			postText.setText("")
			return True
		
		page.validatePage = validate

	def createBasicClassSetup(self,pageClass,params={}):
		
		gobj = gtf.getInstanceByType(pageClass)
		
		page = self._registerPage(gobj.create_headerText,"",pageClass)
		
		self.setupDict = {}

		def __init():
			self.setupDict.clear()
			self.setupDict['type'] = pageClass

		page.initializePage = __init

		gmname = QLineEdit()
		gmname.setMaxLength(64)
		name_opt_ = gobj.create_nameText
		gmname.setPlaceholderText(f"Введите {name_opt_.lower()}")
		self._addLineOption(f"{name_opt_}:",gmname)

		gmclass = QLineEdit()
		gmname.setMaxLength(64)
		class_opt_ = gobj.create_classnameText
		gmclass.setPlaceholderText(f"Введите {class_opt_.lower()}")
		self._addLineOption(f"{class_opt_}:",gmclass)

		gmparent = SearchComboButton()
		opt_parentName_ = gobj.parent_nameText
		self._addLineOption(f"{opt_parentName_}:",gmparent)
		parentClassname = gobj.parent_classnameText
		parents = self.graphSystem.getFactory().getClassAllChilds(parentClassname)

		if not parents:
			raise Exception(f"Класс \"{parentClassname}\" не найден или отсутствуют дочерние классы")

		vals = self.graphSystem.getFactory().getClassAllChildsTree(parentClassname)
		gmparent.loadContents(createTreeDataContent(vals))

		gmpath = PropFileSavePath()
		gmpath.set_file_ext("*.graph")
		opt_pathName_ = gobj.path_nameText
		#gmpath.setPlaceholderText("Введите путь к режиму")
		self._addLineOption(f"{opt_pathName_}:",gmpath)

		self._addSpacer()

		postfixLabel = self._addLabel("Без примечаний",isRichText=True)

		path = gobj.savePath
		def _validateAll():
			prefix = ""
			name = gmname.text()
			classname = gmclass.text()
			pathval = gmpath.get_value()
			parCls = gmparent.get_value()
			errors = []

			if not name:
				errors.append(f"{name_opt_} не может быть пустым")
			if not classname:
				errors.append(f"{class_opt_} не может быть пустым")
			else:
				if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]+$',classname):
					errors.append(f"{class_opt_} может содержать только английские буквы, цифры и нижнее подчеркивание, а так же не должно начиться с цифр")
				if len(classname) <= 4:
					errors.append(f"{class_opt_} должно содержать более 4 символов")
				if self.graphSystem.getFactory().classNameExists(classname):
					errors.append(f"Класс \"{classname}\" уже существует")

			if not parCls:
				errors.append(f"{opt_parentName_} не имеет значения")

			if os.path.exists(pathval):
				errors.append(f"Файл \"{pathval}\" уже существует")

			if errors:
				prefix = "<span style='color:red; font-size: 14pt'>Ошибки:<br/>" + ('<br/>'.join(errors)) + "</span>"
			
			postfixLabel.setText(f"{prefix}<br/>Примечание: созданный файл графа будет хранится в \"{path}\"<br/>"+
			f"{class_opt_} генерируется автоматически, но вы можете переопределить его.")

			settings = self.setupDict
			settings['name'] = name
			settings['classname'] = classname
			settings['parent'] = parCls
			settings['path'] = pathval

			#self.button(QWizard.WizardButton.NextButton).setVisible(len(errors) == 0)
			return len(errors) == 0
		
		def __on_name_changed():
			enText = transliterate(gmname.text())
			words = re.findall(r'[a-zA-Z0-9_]+',enText)
			gmclass.setText("".join([x.capitalize() for x in words]))
			gmclass.textChanged.emit(gmclass.text())
			_validateAll()
		def __on_classname_changed():
			text = gmclass.text()
			basePath = gobj.savePath
			fullpath = os.path.join(basePath,f"{text}.graph")
			gmpath.set_value(fullpath)
			_validateAll()
		gmname.textChanged.connect(__on_name_changed)
		gmclass.textChanged.connect(__on_classname_changed)
		page.validatePage = _validateAll

		page.nextId = lambda: self.pageIds()[-1]


	def createGraphTypeSetup(self,graphType):
		gobj = gtf.getInstanceByType(graphType)

		if gobj == None: return
		
		page = self._registerPage(gobj.scriptWizard_pageText,gobj.scriptWizard_pageSubtitle,graphType)
		
		self.setupDict = {}

		def __init():
			self.setupDict.clear()
			self.setupDict['type'] = graphType

		page.initializePage = __init

		_validateAll = gobj.createPageWizard(self,page)

		if _validateAll == None or not callable(_validateAll):
			raise Exception("Validate method error for " + graphType)
		
		page.validatePage = _validateAll

		page.nextId = lambda: self.pageIds()[-1]

	def createFinalPage(self):
		page = self._registerPage("Завершение")

		txt = self._addLabel("",isRichText=False)
		def __init():
			optlist = []
			for k,v in self.setupDict.items():
				optlist.append(f'{k}: {v}')
			
			txt.setText("Опции: " + "\n".join(optlist))
		page.initializePage = __init

		self.button(QWizard.WizardButton.FinishButton).clicked.connect(self.onFinish)

	def onFinish(self):
		logger = ScriptMakerManager.refObject.logger
		settings = self.getSetupDict()
		gobjType = settings.get('type')
		if not gobjType:
			return
		
		gobj = gtf.getInstanceByType(gobjType)
		filePath = settings.get('path')
		settings.pop('path') #removing path
		
		if not filePath:
			logger.error(f'Ошибка пути: {filePath}')
			return
		
		sets,msg = gobj.createInfoDataProps(settings)
		if sets:
			self.graphSystem.sessionManager.newTab(switchTo=True,loader=filePath,optionsToCreate=sets)
		else:
			logger.error(msg)

	def create_wizard(self):
		self.createIntro()
		self.createSelectScriptType()

		options : list[GraphTypeBase] = gtf.getAllInstances()
		for opt in options:
			self.createGraphTypeSetup(opt.systemName)

		# self.createBasicClassSetup(
		# 	"gamemode", 
		# 	params={
		# 		'header': "Создание режима",
		# 		"name": "Имя режима",
		# 		"classname": "Имя класса режима",
		# 		"pathData":{
		# 			"name": "Путь к файлу режима",
		# 			"base": ".\\src\\",
		# 		},
		# 		"parentData": {
		# 			"name": "Родительский режим",
		# 			"class": "ScriptedGamemode",
		# 		},
		# 	}
		# )
		# self.createBasicClassSetup(
		# 	"role", 
		# 	params={
		# 		'header': "Создание роли",
		# 		"name": "Имя роли",
		# 		"classname": "Имя класса роли",
		# 		"pathData":{
		# 			"name": "Путь к файлу роли",
		# 			"base": ".\\src\\",
		# 		},
		# 		"parentData": {
		# 			"name": "Родительская роль",
		# 			"class": "ScriptedRole",
		# 		},
		# 	}
		# )

		self.createFinalPage()


class WizardScriptMakerPage(QWizardPage):
	def __init__(self,gsys):
		super().__init__(gsys.mainWindow)