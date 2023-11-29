from ReNode.ui.LoggerConsole import LoggerConsole

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
    
    def getShortErrorInfo(self):
        return f'ERR-{self.__class__.id}'

    def getExceptionDescription(self):
        desc = self.__class__.desc
        if desc:
            desc = desc.format(
                src=self.src,
                portname=self.portname,
                targ=self.targ,
                ctx=self.ctx,
                entry=self.entry
            )
        return desc

    def getExceptionText(self,addDesc = False):
        class_ = self.__class__
        postText = class_.desc if addDesc else ""

        if postText:
            postText = "<span style='color:#FFF2B0;'>"+self.getExceptionDescription()+"</span>"
            postText = "\n- Подробнее: " + postText
            #postText = '<p title="tootip">some block of text</p>'
        return f"<b>ERR-{class_.id}</b>: " + class_.text.format(
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
    text = "Узел {src} вызвал необработанное исключение. Контекст: {ctx}"

class CGStackError(CGBaseException):
    id = 3
    text = "Ошибка стека генерации - отсутствует совместимая информация для генерации {entry}"
    desc = "При обработке отсортированного дерева узлов кодогенератор не смог найти допустимых замен без которых дальнейшая обработка невыполнима. Возможная проблема в {src}"

# ----------------------------------------
#   101-300 - ports exceptions
# ----------------------------------------

class CGPortTypeRequiredException(CGBaseException):
    id = 101
    desc = "Некоторые узлы получают типы своих портов при подключении к ним других узлов. Подключите к {src} узел, который определит тип портов"

class CGInputPortTypeRequiredException(CGPortTypeRequiredException):
    text = "Входной порт \"{portname}\" узла {src} требует подключения, так как не имеет типа"

class CGOutputPortTypeRequiredException(CGPortTypeRequiredException):
    text = "Выходной порт \"{portname}\" узла {src} требует подключения, так как не имеет типа"

class CGPortRequiredConnectionException(CGBaseException):
    id = 102
    text = "Входной порт \"{portname}\" узла {src} требует подключения, так как не имеет пользовательского свойства"
    desc = "Порт \"{portname}\" в узле не имеет опции пользовательских данных и требует подключенного значения."

# ----------------------------------------
#   301-600 - nodes exceptions
# ----------------------------------------

class CGVariablePathAccessException(CGBaseException):
    id = 301
    text = "Узел {src} не может быть использован из-за ограничений пути, наложенных {targ}"
    desc = "Проверьте пути до узла {src}. Вероятно, до него идёт два или более конфликтующих порта, например из цилка"

    checkedNodes = {
        "operators.foreach_loop": ["При завершении"],
        "operators.for_loop": ["При завершении"]
    }

    @staticmethod
    def checkNode(node):
        return True
    
    @staticmethod
    def canCheckNode(node):
        return True

class CGVariableUnhandledPathAccessException(CGVariablePathAccessException):
    id = 302
    text = "<span style='color:darkred;'>[Необработанная ошибка]</span> Узел {src} не может быть использован из-за ограничений пути, наложенных {targ}"
    desc = "<span style='color:darkorange;'> Обратитесь к разработчику для решения данной проблемы.</span> Проверьте пути до узла {src}. Вероятно, до него идёт два или более конфликтующих порта, например из цилка"
    

class CGLogicalOptionListEvalException(CGBaseException):
    id = 303
    text = "Узел {src} вызвал необработанную ошибку опции листа"
    desc = "Для элемента \"{ctx}\" листа \"{portname}\" не найдено значения для замены. Обратитесь к разработчику для решения этой проблемы"

class CGDuplicateEntryException(CGBaseException):
    id = 304
    text = "Множественное использование точки входа {entry}"
    desc = "Точка входа типа {entry} уже существует в этом графе. Удалите {src}"

# ----------------------------------------
#   601-700 - variables exceptions
# ----------------------------------------

class CGLocalVariableDuplicateUseException(CGBaseException):
    id = 601
    text = "Локальная переменная {src} ({ctx}) уже используется в событии {targ}"
    desc = "Локальные переменные можно использовать только внутри одного события. Создайте новую переменную для использования в {entry}"

class CGLocalVariableMetaKeywordNotFound(CGBaseException):
    id = 602
    text = "Точка входа {entry} не имеет определения мета-оператора для локальных переменных."
    desc = "<span style='color:darkorange;'> Обратитесь к разработчику для решения данной проблемы.</span> В точке входа не найден мета-оператор <b>initvars</b>. Вероятнее всего проблема вызывана ошибкой генерации кода."