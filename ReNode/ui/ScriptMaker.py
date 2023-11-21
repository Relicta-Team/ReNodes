from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ReNode.app.Logger import RegisterLogger
from ReNode.app.utils import transliterate
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_file_paths import PropFileSavePath
import re
import sys
import os

class ScriptMakerManager(QWizard):
	"""
		Менеджер создания скриптов
	"""
	
	def __init__(self,gsys):
		super().__init__(gsys.mainWindow)
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
		self.setWindowTitle("Создание скрипта")
		
		#change background color
		bluepalette = QPalette()
		bluepalette.setColor(QPalette.Background,Qt.black)
		self.setPalette(bluepalette)


		self._lastPage = None
		self._lastPath = []
		self._dictPathes = {}
		self.currentIdChanged.connect(self.disable_back)
		
		self.create_wizard()



		self.show()

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

	def _addLineOption(self,text,optWidget,row=0,col=0):
		item = QGridLayout()
		#item.setSpacing(20)
		lab = QLabel(text)
		lab.setFixedWidth(200)
		item.addWidget(lab,0,0)
		item.addWidget(optWidget,0,1)
		self._lastLayout.addLayout(item)
		
		return lab,optWidget,item

	def createIntro(self):
		self._registerPage("Создание скриптов ReNode")
		self._lastLayout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
		self._addLabel("Добро пожаловать в менеджер создания скриптов ReNode!\n\n"+
			"Сейчас вам будет предложено создать новый скрипт.")
		
		self._addLabel(f"Для продолжения нажмите кнопку \"{self.button(QWizard.NextButton).text()}\".")
	
	def createSelectScriptType(self):
		page = self._registerPage("Общие настройки")

		combo = QComboBox()

		options = [
			["Игровой режим","gamemode","Игровой режим предназначен для реализации состояния игры."],
			["Роль","role","Роль для игрового режима. В роли определяется снаряжение, стартовая позиция и навыки персонажа."],
			["Игровой объект","gobject","Игровой объект с пользовательской логикой является переопределенным (унаследованным) от другого объекта. Например, мы можем создать игровой объект, унаследованный от двери и переопределить событие её открытия."],
			["Скриптовый объект","scriptedobject","Скриптовый игровой объект с поддержкой компонентов. Это более гибкий инструмент создания игровых объектов, использующий общий класс и реализующий широкий спектр компонентов. С помощью него мы, например, можем создать контейнер, который можно съесть и из которого можно стрелять."],
			["Компонент","component","Пользовательский компонент, добавляемый в скриптовый объект."],
			["Сетевой виджет","netdisplay","Клиентский виджет для взаимодействия с игровыми и скриптовыми объектами. Например, можно сделать виджет с кнопкой, при нажатии на которую будет происходить какое-то действие."],
			["Объект","object","Объект общего назначения."],
		]

		for o in options:
			combo.addItem(o[0])
			combo.setItemData(combo.count()-1,o[1])
			combo.setItemData(combo.count()-1,o[2],Qt.ToolTipRole)

		self._addLineOption("Тип скрипта:",combo)
		item = self._addLabel("")
		combo.setCurrentIndex(0)
		def setDesc():
			item.setText("Описание: " + options[combo.currentIndex()][2])
			sysname = options[combo.currentIndex()][1]
			for id  in self._dictPathes.get(sysname,[]):
				pass
		setDesc()
		combo.currentIndexChanged.connect(lambda: setDesc())

		def defineNextId():
			lst = self._dictPathes.get(options[combo.currentIndex()][1],[])
			if lst:
				return lst[0]
			else:
				return self.pageIds()[len(self.pageIds())-1]
		page.nextId = defineNextId

		self._addSpacer()
		postText = self._addLabel("",isRichText=True)

		def validate():
			data = combo.currentData()
			if data not in ['gamemode','role']:
				postText.setText(f"<span style=\"color:red; font-size:18pt\">На данный момент скрипт типа \"{combo.currentText()}\" не может быть создан.</span>")
				return False
			postText.setText("")
			return True
		
		page.validatePage = validate

	def createBasicClassSetup(self,pageClass,params={}):
		page = self._registerPage("Создание режима","",pageClass)
		
		gmname = QLineEdit()
		gmname.setMaxLength(64)
		name_opt_ = params.get('name','Название')
		gmname.setPlaceholderText(f"Введите {name_opt_.lower()}")
		self._addLineOption(f"{name_opt_}:",gmname)

		gmclass = QLineEdit()
		gmname.setMaxLength(64)
		class_opt_ = params.get('classname',"Класс")
		gmclass.setPlaceholderText(f"Введите {class_opt_.lower()}")
		self._addLineOption(f"{class_opt_}:",gmclass)

		gmparent = QComboBox()
		opt_parent_ = params.get('parentData',{"name":"Неизвестный name","class":""})
		self._addLineOption(f"{opt_parent_.get('name','Неопр.')}:",gmparent)
		parentClassname = opt_parent_.get('class','')
		parents = self.graphSystem.getFactory().getClassAllChilds(parentClassname)
		iSet__ = -1

		for idx, modename in enumerate(parents):
			
			gmparent.addItem(f"{modename}")
			if modename == parentClassname:
				iSet__ = idx
		if iSet__: gmparent.setCurrentIndex(iSet__)

		gmpath = PropFileSavePath()
		gmpath.set_file_ext("*.graph")
		opt_path_ = params.get('pathData',{"name":"Неизвестный путь","base":"Базовый путь"})
		#gmpath.setPlaceholderText("Введите путь к режиму")
		self._addLineOption(f"{opt_path_.get('name','Неопр.')}:",gmpath)

		self._addSpacer()

		postfixLabel = self._addLabel("Без примечаний",isRichText=True)

		path = "not_defined"
		def _validateAll():
			prefix = ""
			name = gmname.text()
			classname = gmclass.text()
			pathval = gmpath.get_value()
			errors = []

			if not name:
				errors.append(f"{name_opt_} не может быть пустым")
			if not classname:
				errors.append(f"{class_opt_} не может быть пустым")
			else:
				if not re.match(r'^[a-zA-Z0-9_]+$',classname):
					errors.append(f"{class_opt_} может содержать только английские буквы, цифры и нижнее подчеркивание")
				if len(classname) <= 4:
					errors.append(f"{class_opt_} должно содержать более 4 символов")

			if os.path.exists(pathval):
				errors.append(f"Файл \"{pathval}\" уже существует")

			if errors:
				prefix = "<span style='color:red; font-size: 14pt'>Ошибки:<br/>" + ('<br/>'.join(errors)) + "</span>"
			
			postfixLabel.setText(f"{prefix}<br/>Примечание: созданный файл графа будет хранится в \"{path}\"<br/>"+
			f"{class_opt_} генерируется автоматически, но вы можете переопределить его.")

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
			gmpath.set_value(f"GM_FOLDER/{text}.graph")
			_validateAll()
		gmname.textChanged.connect(__on_name_changed)
		gmclass.textChanged.connect(__on_classname_changed)
		page.validatePage = _validateAll

	def create_wizard(self):
		self.createIntro()
		self.createSelectScriptType()

		self.createBasicClassSetup(
			"gamemode", 
			params={
				"name": "Имя режима",
				"classname": "Имя класса режима",
				"pathData":{
					"name": "Путь к файлу режима",
					"base": ".\\src\\",
				},
				"parentData": {
					"name": "Родительский режим",
					"class": "GMBase",
				},
			}
		)
		self.createBasicClassSetup(
			"role", 
			params={
				"name": "Имя роли",
				"classname": "Имя класса роли",
				"pathData":{
					"name": "Путь к файлу роли",
					"base": ".\\src\\",
				},
				"parentData": {
					"name": "Родительская роль",
					"class": "BasicRole",
				},
			}
		)

		self._registerPage("Finish!!!")


		# self.setStartId(self.addPage(self.createIntroPage()))
		# self.addPage(self.createRegistrationPage())
		# self.addPage(self.createConclusionPage())



		#Первая страница: выбор типа скрипта
		# item = WizardScriptMakerPage(self.graphSystem)
		# self.addPage(item)
		# item.setTitle("Выбор типа скрипта")
		# item.setSubTitle("Выберите тип создаваемого скрипта")

		# itemGamemode = WizardScriptMakerPage(self.graphSystem)
		# self.addPage(itemGamemode)
		# itemGamemode.setTitle("Создание режима")
		# itemGamemode.setSubTitle("Укажите базовые настройки создания режима")
		
		# vlay = QVBoxLayout()
		# hlayname = QHBoxLayout()
		# hlayparent = QHBoxLayout()
		# vlay.addLayout(hlayname)
		# vlay.addLayout(hlayparent)
		# itemGamemode.setLayout(vlay)

		# # add gmname (input)
		# lable = QLabel("Название режима")
		# hlayname.addWidget(lable)
		# text = QLineEdit()
		# text.setPlaceholderText("Название режима")
		# itemGamemode.registerField("gmName",text)
		# hlayname.addWidget(text)
		
		# # add gm parent type (combobox)
		# label = QLabel("Родительский тип режима")
		# hlayparent.addWidget(label)
		# comboBox = QComboBox()
		# # Add the parent types to the combobox
		# parentTypes = ["Type 1", "Type 2", "Type 3"]
		# comboBox.addItems(parentTypes)
		# itemGamemode.registerField("gmParent", comboBox)
		# hlayparent.addWidget(comboBox)

	def createIntroPage(self):
		page = QWizardPage()
		
		page.setTitle("Introduction")
		#page.setSubTitle("This wizard will help you register your copy of Super Product Two.")

		label = QLabel(
				"This wizard will help you register your copy of Super Product "
				"Two.")
		label.setWordWrap(True)

		layout = QVBoxLayout()
		layout.addWidget(label)
		page.setLayout(layout)

		return page


	def createRegistrationPage(self):
		page = QWizardPage()
		page.setTitle("Registration")
		page.setSubTitle("Please fill both fields.")

		nameLabel = QLabel("Name:")
		nameLineEdit = QLineEdit()

		emailLabel = QLabel("Email address:")
		emailLineEdit = QLineEdit()

		layout = QGridLayout()
		layout.addWidget(nameLabel, 0, 0)
		layout.addWidget(nameLineEdit, 0, 1)
		layout.addWidget(emailLabel, 1, 0)
		layout.addWidget(emailLineEdit, 1, 1)
		page.setLayout(layout)

		return page


	def createConclusionPage(self):
		page = QWizardPage()
		page.setTitle("Conclusion")

		label = QLabel("You are now successfully registered. Have a nice day!")
		label.setWordWrap(True)

		layout = QVBoxLayout()
		layout.addWidget(label)
		page.setLayout(layout)

		return page


class WizardScriptMakerPage(QWizardPage):
	def __init__(self,gsys):
		super().__init__(gsys.mainWindow)