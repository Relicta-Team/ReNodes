
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
        self.entry = kwargs.get('entry') or ""
    
    def getExceptionText(self,addDesc = False):
        class_ = self.__class__
        postText = class_.desc if addDesc else ""

        if postText:
            postText = "\n--- Описание:\n\t" + postText.format(
                src=self.src,
                portname=self.portname,
                targ=self.targ,
                ctx=self.ctx,
                entry=self.entry
            )

        return f"ERR-{class_.id}: " + class_.text.format(
            src=self.src,
            portname=self.portname,
            targ=self.targ,
            ctx=self.ctx,
            entry=self.entry
        ) + postText

# ----------------------------------------
#   1-100 - reserved critical exception
# ----------------------------------------

class CGUnhandledException(CGBaseException):
    id = 1
    text = "Необработанное исключение: {ctx}"
    desc = "Обратитесь к разработчику для решения данной проблемы"

class CGUnhandledObjectException(CGUnhandledException):
    id = 2
    text = "Узел \"{src}\" вызвал необработанное исключение. Контекст: {ctx}"

class CGStackError(CGBaseException):
    id = 3
    text = "Ошибка стека генерации - отсутствует совместимая информация для генерации"
    desc = "При обработке отсортированного дерева узлов кодогенератор не смог найти допустимых замен без которых обработка не может выполняться."

# ----------------------------------------
#   101-300 - ports exceptions
# ----------------------------------------

class CGPortTypeRequiredException(CGBaseException):
    id = 101
    desc = "Некоторые узлы получают типы своих портов при подключении к ним других узлов. Подключите к узлу \"{src}\" определяющий узел"

class CGInputPortTypeRequiredException(CGPortTypeRequiredException):
    text = "Входной порт \"{portname}\" узла \"{src}\" требует подключения, так как не имеет типа"

class CGOutputPortTypeRequiredException(CGPortTypeRequiredException):
    text = "Выходной порт \"{portname}\" узла \"{src}\" требует подключения, так как не имеет типа"

class CGPortRequiredConnectionException(CGBaseException):
    id = 102
    text = "Входной порт \"{portname}\" узла \"{src}\" требует подключения, так как не имеет пользовательского свойства"
    desc = "Порт \"{portname}\" в узле не имеет опции пользовательских данных и требует подключенного значения."

# ----------------------------------------
#   301-600 - nodes exceptions
# ----------------------------------------

class CGVariablePathAccessException(CGBaseException):
    id = 301
    text = "Порт \"{portname}\" узла \"{src}\" не может быть использован из-за ограничений пути, наложенных \"{targ}\""
    desc = "Проверьте пути до узла \"{portname}\". Вероятно, до него идёт два или более конфликтующих порта, например из цилка"

# ----------------------------------------
#   601-700 - variables exceptions
# ----------------------------------------

class CGLocalVariableDuplicateUseException(CGBaseException):
    id = 601
    text = "Локальная переменная \"{src}\" ({ctx}) уже используется в событии \"{targ}\""
    desc = "Локальные переменные можно использовать только внутри одного события. Создайте новую переменную для использования в \"{entry}\""