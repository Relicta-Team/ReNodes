

class CGBaseException:
    id = 0
    text = "Неизвестная ошибка"
    desc = ""

    def __init__(self,**kwargs) -> None:
        """
            `src` - узел источник проблемы
            `portname` - имя порта
            `targ` - узел цель
        """
        self.src = kwargs.get('src') or ""
        self.portname = kwargs.get('portname') or ""
        self.targ = kwargs.get('targ') or ""
        self.ctx = kwargs.get('ctx') or ""
    
    def getExceptionText(self,addText = False):
        class_ = self.__class__
        postText = class_.text if addText else ""

        return f"ERR-{class_.id} :" + class_.text.format(
            src=self.src,
            portname=self.portname,
            targ=self.targ,
            ctx=self.ctx
        ) + postText


class CGStackError(CGBaseException):
    id = 1
    text = "Ошибка стека генерации - отсутствует совместимая информация для генерации"
    desc = "При обработке отсортированного дерева узлов кодогенератор не смог найти допустимых замен без которых обработка не может выполняться."

class CGVariablePathAccessException(CGBaseException):
    id = 2
    text = "Порт \"{portname}\" узла \"{src}\" не может быть использован из-за ограничений пути"
    desc = "Проверьте пути до узла \"{portname}\". Вероятнее до него идёт два или более конфликтующих порта цилка"

class CGPortTypeRequiredException(CGBaseException):
    id = 3
    text = "Порт \"{portname}\" узла \"{src}\" требует подключения, так как не имеет типа"
    desc = "Некоторые узлы получают типы своих портов при подключении к ним других узлов. Подключите к узлу \"{src}\" определяющий узел"

class CGPortRequiredConnectionException(CGBaseException):
    id = 4
    text = "Порт \"{portname}\" узла \"{src}\" требует подключения, так как не имеет пользовательского свойства"
    desc = "Порт \"{portname}\" в узле не имеет опции пользовательских данных и требует подключенного значения."

class CGLocalVariableDuplicateUseException(CGBaseException):
    id = 5
    text = "Переменная \"{ctx}\" уже используется в событии \"{src}\""
    desc = "Локальные переменные можно использовать только в одном узле. Создайте другую переменную для \"{targ}\""