
class GraphTypeFactory:
    """
    Фабрика типов графа
    """

    instanceDict = None

    @staticmethod
    def createInstances():
        GraphTypeFactory.instanceDict = {}
        GraphTypeFactory.registerGraphType(GamemodeGraph)
        GraphTypeFactory.registerGraphType(RoleGraph)
        GraphTypeFactory.registerGraphType(GameObjectGraph)

    @staticmethod
    def registerGraphType(type):
        if not issubclass(type,GraphTypeBase):
            raise Exception(f"Type <{type}> must be subclass of <GraphTypeBase>")
        if not type.systemName:
            raise Exception(f"Type <{type}> must have <systemName> attribute")
        GraphTypeFactory.instanceDict[type.systemName] = type()

    @staticmethod
    def getAllInstances():
        """
            Возвращает все зарегистрированные типы графов\n
            Возвращаемый лист можно изменять (является копией)
        """
        if not GraphTypeFactory.instanceDict:
            GraphTypeFactory.createInstances()
        return list(GraphTypeFactory.instanceDict.values())

    @staticmethod
    def getInstanceByType(type_):
        if not GraphTypeFactory.instanceDict:
            GraphTypeFactory.createInstances()
        
        if type_ is type:
            if not issubclass(type_,GraphTypeBase):
                raise Exception(f"Type <{type_}> must be subclass of <GraphTypeBase>")
            
            type_ = type_.systemName
        instance : GraphTypeBase = GraphTypeFactory.instanceDict.get(type_)
        if not instance:
            raise Exception(f"Type <{type_}> not found")
        return instance

class GraphTypeBase:
    """
        Базовый тип графа. Тут текстовая информация, метаинформация для кодогенератора и обработчик узлов
    """
    
    systemName = ""

    name = "Неизвестный тип"
    description = "Без описания"

    create_headerText = "Создание графа"
    create_nameText = "Имя графа"
    create_classnameText = "Имя класса графа"
    path_nameText = "Путь до графа"
    parent_nameText = "Родительский граф"
    parent_classnameText = "object" #type

    canCreateFromWizard = False #что можно создать через визард

    # Где хранятся графы
    savePath = "graphs\\Base" 
    createFolder = False #создает папку при сохранении (используется имя типа, например имя класса режима)

    def resolvePath(self,checkedPath):
        """Обработчик пути до графа. К примеру роли могут лежать в папке режима"""
        return checkedPath

    def createInfoDataProps(self,options:dict):
        newDict = {}
        return newDict,f"Метод генератора настроек для {self.__class__.__name__} не переопределен"


    def getName(self):
        return self.name
    
    def getDescription(self):
        return self.description
    
    #region Code handlers

    def cgHandleWrapper(self):
        """
            Получает обертку графа для кодогенератора.
            
            Это базовый метод для получения тела инструкций кода (например, заголовка класса)
        """
        raise NotImplementedError("cgHandleWrapper is not implemented")
        return ""
    
    def cgHandleVariables(self):
        """
            Обработчик переменных для кодогенератора.
        """
        raise NotImplementedError("cgHandleVariables is not implemented")
        return ""
    
    def cgHandleInspectorProps(self):
        """
            Обработчик свойств инспектора.
        """
        raise NotImplementedError("cgHandleInspectorProps is not implemented")
        return ""
    

    #endregion


    def handleReadyNode(self,nodeObject,rule):
        """
            Обработчик готового узла при кодогенерации и правило, которое следует проверять.

            Этот метод вызывается сразу когда узел помечается как готовый на подстановку
        """
        raise NotImplementedError("handleReadyNode is not implemented")
        pass

class ClassGraphType(GraphTypeBase):
    
    def createInfoDataProps(self, options: dict):
        opts = {}

        if not options:
            return None,"Опции не установлены"

        name_ = options.get('name')
        classname_ = options.get('classname')
        parCls_ = options.get('parent')
        if not name_:
            return opts,"Имя не установлено"
        if not classname_:
            return opts,"Имя класса не установлено"
        if not parCls_:
            return opts,"Родительский граф не установлен"
        
        opts['type'] = self.systemName
        opts['name'] = name_
        opts['classname'] = classname_
        opts['parent'] = parCls_
        opts['props'] = {
            "fields": {},
            "methods": {}
        }

        return opts,""



class GamemodeGraph(ClassGraphType):
    name = "Режим"
    description = "Игровой режим предназначен для реализации состояния игры."
    systemName = "gamemode"
    
    create_headerText = "Создание режима"
    create_nameText = "Имя режима"
    create_classnameText = "Имя класса режима"
    path_nameText = "Путь к файлу режима"
    parent_nameText = "Родительский режим"
    parent_classnameText = "GMBase"
    
    canCreateFromWizard = True
    createFolder = True

    pass

class RoleGraph(ClassGraphType):
    name = "Роль"
    description = "Роль для игрового режима. В роли определяется снаряжение, стартовая позиция и навыки персонажа."
    systemName = "role"
    
    create_headerText = "Создание роли"
    create_nameText = "Имя роли"
    create_classnameText = "Имя класса роли"
    path_nameText = "Путь к файлу роли"
    parent_nameText = "Родительская роль"
    parent_classnameText = "BasicRole"

    canCreateFromWizard = True
    
class GameObjectGraph(ClassGraphType):
    name = "Игровой объект"
    description = "Игровой объект с пользовательской логикой является переопределенным (унаследованным) от другого объекта. Например, мы можем создать игровой объект, унаследованный от двери и переопределить событие её открытия."
    systemName = "gobject"

    canCreateFromWizard = False
# TODO: add more:
# ["Скриптовый объект","scriptedobject","Скриптовый игровой объект с поддержкой компонентов. Это более гибкий инструмент создания игровых объектов, использующий общий класс и реализующий широкий спектр компонентов. С помощью него мы, например, можем создать контейнер, который можно съесть и из которого можно стрелять."],
# ["Компонент","component","Пользовательский компонент, добавляемый в скриптовый объект."],
# ["Сетевой виджет","netdisplay","Клиентский виджет для взаимодействия с игровыми и скриптовыми объектами. Например, можно сделать виджет с кнопкой, при нажатии на которую будет происходить какое-то действие."],
# ["Объект","object","Объект общего назначения."],