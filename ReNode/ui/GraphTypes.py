
class GraphTypeFactory:
    """
    Фабрика типов графа
    """

    instanceDict = None

    @staticmethod
    def createInstances():
        GraphTypeFactory.instanceDict = {}
        GraphTypeFactory.registerGraphType(ClassGraphType)
        GraphTypeFactory.registerGraphType(RoleGraph)

    @staticmethod
    def registerGraphType(type):
        if not issubclass(type,GraphTypeBase):
            raise Exception(f"Type <{type}> must be subclass of <GraphTypeBase>")
        GraphTypeFactory.instanceDict[type.systemName] = type()
        pass

    @staticmethod
    def getInstanceByType(type_):
        if not GraphTypeFactory.instanceDict:
            GraphTypeFactory.createInstances()
        
        if type_ is type:
            if not issubclass(type_,GraphTypeBase):
                raise Exception(f"Type <{type_}> must be subclass of <GraphTypeBase>")
            
            type_ = type_.systemName

        return GraphTypeFactory.instanceDict[type_]        

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
    parent_classText = "object" #type

    canCreateFromWizard = False #что можно создать через визард

    # Где хранятся графы
    savePath = "graphs\\Base" 
    createFolder = False #создает папку при сохранении (используется имя типа, например имя класса режима)

    def createInfoDataProps(self):
        return {
            "fields": {},
            "methods": {}
        }


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
        return ""
    
    def cgHandleVariables(self):
        """
            Обработчик переменных для кодогенератора.
        """
        return ""
    
    def cgHandleInspectorProps(self):
        """
            Обработчик свойств инспектора.
        """
        return ""
    

    #endregion


    def handleReadyNode(self,nodeObject,rule):
        """
            Обработчик готового узла при кодогенерации и правило, которое следует проверять.

            Этот метод вызывается сразу когда узел помечается как готовый на подстановку
        """
        pass

class ClassGraphType(GraphTypeBase):
    pass


class GamemodeGraph(ClassGraphType):
    name = "Режим"
    desc = "Игровой режим предназначен для реализации состояния игры."
    systemName = "gamemode"
    
    create_headerText = "Создание режима"
    create_nameText = "Имя режима"
    create_classnameText = "Имя класса режима"
    path_nameText = "Путь к файлу режима"
    parent_nameText = "Родительский режим"
    parent_classText = "GMBase"
    
    canCreateFromWizard = True
    createFolder = True

    pass

class RoleGraph(ClassGraphType):
    name = "Роль"
    desc = "Роль для игрового режима. В роли определяется снаряжение, стартовая позиция и навыки персонажа."
    systemName = "role"
    
    create_headerText = "Создание роли"
    create_nameText = "Имя роли"
    create_classnameText = "Имя класса роли"
    path_nameText = "Путь к файлу роли"
    parent_nameText = "Родительская роль"
    parent_classText = "BasicRole"
    
    pass

# TODO: add more:
# ["Игровой объект","gobject","Игровой объект с пользовательской логикой является переопределенным (унаследованным) от другого объекта. Например, мы можем создать игровой объект, унаследованный от двери и переопределить событие её открытия."],
# ["Скриптовый объект","scriptedobject","Скриптовый игровой объект с поддержкой компонентов. Это более гибкий инструмент создания игровых объектов, использующий общий класс и реализующий широкий спектр компонентов. С помощью него мы, например, можем создать контейнер, который можно съесть и из которого можно стрелять."],
# ["Компонент","component","Пользовательский компонент, добавляемый в скриптовый объект."],
# ["Сетевой виджет","netdisplay","Клиентский виджет для взаимодействия с игровыми и скриптовыми объектами. Например, можно сделать виджет с кнопкой, при нажатии на которую будет происходить какое-то действие."],
# ["Объект","object","Объект общего назначения."],