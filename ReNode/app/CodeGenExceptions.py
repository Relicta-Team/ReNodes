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

class CGPortTypeMissmatchException(CGBaseException):
    id = 103
    text = "Недопустимый тип для порта \"{portname}\" узла {src}"
    desc = "Узел {src} не может принять тип порта, полученный от {targ}. Требуется тип \'{ctx}\'"

# ----------------------------------------
#   301-600 - nodes exceptions
# ----------------------------------------

class CGScopeLoopException(CGBaseException):
    id = 301
    text = "Узел {src} не может быть использован из-за ограничений области видимости, наложенных {targ}"
    desc = "Узел {targ} используетя в области видимости {ctx}, который накладывает ограничения для внешней области узла {src}. Уберите связь."

class CGScopeLoopPortException(CGBaseException):
    id = 302
    text = "Узел {src} не может использовать порт \"{portname}\" узла {targ} из-за ограничений области видимости."
    desc = "Переменные, создаваемые внутри цикла не могут существовать вне тела цикла."

class CGLogicalOptionListEvalException(CGBaseException):
    id = 303
    text = "Узел {src} вызвал необработанную ошибку опции листа"
    desc = "Для элемента \"{ctx}\" листа \"{portname}\" не найдено значения для замены. Обратитесь к разработчику для решения этой проблемы"

class CGDuplicateEntryException(CGBaseException):
    id = 304
    text = "Множественное использование точки входа {entry}"
    desc = "Точка входа типа {entry} уже существует в этом графе. Удалите {src}"

class CGReturnTypeUnexpectedException(CGBaseException):
    id = 305
    text = "Не требуемое возвращаемое значение для {src}"
    desc = "Точка входа {entry} не возвращает никаких значений. Уберите все возвраты значений из этой точки входа."

class CGReturnTypeMismatchException(CGBaseException):
    id = 306
    text = "Несоответствие возвращаемых значений для {entry}"
    desc = "Тип допустимого возвращаемого значения для {entry} ({ctx}) не совпадает с типом возвращаемого значения в {src} ({portname}). Точка входа может принимать возвращаемый тип: {ctx}"

class CGReturnTypeNotFoundException(CGBaseException):
    id = 307
    text = "Отсутствие возвращаемого значения {src}"
    desc = "Точка входа {entry} должна возвращать значение типа ({ctx})."

class CGReturnNotAllBranchesException(CGBaseException):
    id = 308
    text = "Ожидается возврат значения после {src}"
    desc = "Все ветви точки входа {entry} должны возвращать значение типа ({ctx}). Подключите к {src} узел возврата значения."

class CGReturnNotExecutedException(CGBaseException):
    id = 309
    text = "Возвращаемое значение в {src} никогда не будет выполнено"
    desc = "К входным портам выполнения узла {src} не подключены узлы, либо один из подключенных узлов не имеет подключения входных портов."

class CGEntryCrossCompileException(CGBaseException):
    id = 310
    text = "Точка входа {entry} не может содержать связи с другими точками входа"
    desc = "Точка входа {entry} не может содержать подключения от другой точки входа {src}. Уберите связи между ними."

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

class CGScopeVariableNotFoundException(CGBaseException):
    id = 603
    text = "Недопустимое использование подключения узла {src}"
    desc = "Узел {src} не может получить данные из недоступной области видимости узла {targ}."