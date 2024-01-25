from ReNode.ui.LoggerConsole import LoggerConsole

class CGCompileAbortException(Exception):
    pass

class CGBaseException:
    id = 0
    text = "Неизвестная ошибка"
    desc = ""
    moreInfo = ""

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

        from ReNode.ui.LoggerConsole import LoggerConsole
        self.exRef = LoggerConsole.createErrorDescriptionLink("err",self,text=self.getShortErrorInfo(),color='#FFF2B0')
    
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

    def getExceptionTextBase(self):
        return self.__class__.text.format(
            src=self.src,
            portname=self.portname,
            targ=self.targ,
            ctx=self.ctx,
            entry=self.entry
        )
    
    def getExceptionMoreInfo(self):
        return self.__class__.moreInfo.format(
            src=self.src,
            portname=self.portname,
            targ=self.targ,
            ctx=self.ctx,
            entry=self.entry
        )
    
    def getExceptionText(self,addDesc = False):
        class_ = self.__class__
        postText = class_.desc if addDesc else ""

        if postText:
            postText = "<span style='color:#FFF2B0;'>"+self.getExceptionDescription()+"</span>"
            postText = "\n- Подробнее: " + postText
            #postText = '<p title="tootip">some block of text</p>'
        return f"<b>[{class_.__name__}:{self.exRef}]</b>: " + self.getExceptionTextBase() + postText
    
    def getMoreExceptionInfo(self,headerSize=25,contentSize=23):
        ret = []
        nextLine = "<br/>"
        ret.append("<span style='font-size:"+str(headerSize)+"px;'>")
        ret.append(f"<b>Имя исключения:</b> {self.__class__.__name__}")
        ret.append(nextLine)
        ret.append(f"<b>Код исключения:</b> {self.__class__.id} ({self.getShortErrorInfo()})")
        ret.append(nextLine)
        ret.append(nextLine)
        ret.append("</span>")
        
        ret.append("<span style='font-size:"+str(contentSize)+"px;'>")
        ret.append(f'<b>Содержание:</b> {self.getExceptionTextBase()}')
        ret.append(nextLine)
        ret.append(f'<b>Описание:</b> {self.getExceptionDescription()}')
        ret.append(nextLine)
        ret.append(f'<b>Подробная информация:</b> {self.getExceptionMoreInfo() or "Отсутствует"}')
        ret.append("</span>")

        return ''.join(ret)

# ----------------------------------------
#   1-100 - reserved critical exception
# ----------------------------------------

class CGUnhandledException(CGBaseException):
    id = 1
    text = "Необработанное исключение: {ctx}"
    desc = "Обратитесь к разработчику для решения данной проблемы"
    moreInfo = "Базовая ошибка, возникающая в особых случаях. Передайте информацию об этом исключении разработчику."

class CGUnhandledObjectException(CGUnhandledException):
    id = 2
    text = "Узел {src} вызвал необработанное исключение. Контекст: {ctx}"

class CGStackError(CGBaseException):
    id = 3
    text = "Ошибка стека генерации - отсутствует совместимая информация для генерации {entry}"
    desc = "При обработке отсортированного дерева узлов кодогенератор не смог найти допустимых замен без которых дальнейшая обработка невыполнима. Возможная проблема в {src}"
    moreInfo = "Обычно, эта ошибка результат других исключений. Возникает она из-за того, что генератор не смог выполнить подготовку кода узла из-за чего дальнейшая генерация стала невозможна."

class CGUnexistNodeError(CGBaseException):
    id = 4
    text = "Найдены несуществующие узлы. Генерация невозможна."
    desc = "Удалите все узлы, которых не существует в библиотеке. Каждый из таких узлов помечен предупреждающим сообщением в консоли."
    moreInfo = "На компилируемом графе найдены узлы, которых не существует в библиотеке узлов. Вам нужно удалить их из графа или переоткрыть граф (при этом все несуществующие узлы пропадут из графа)."
class CGInternalValueCompileError(CGBaseException):
    id = 5
    text = "Внутренняя ошибка преобразований"
    desc = "Обнаружена ошибка преобразования значений. Смотрите последнее предупреждение."
    moreInfo = "Данная ошибка возникает, когда компилятор не смог преобразовать значения редактора в игровые данные. Ознакомьтесь с последним предупреждением, чтобы узнать точную причину ошибки, а затем передайте эту информацию разработчику."
class CGInternalCompilerError(CGBaseException):
    id = 6
    text = "Внутренняя ошибка компилятора"
    desc = "Обнаружена ошибка компилятора при обработке узла {src}: {ctx}"
    moreInfo = "Данная ошибка возникает, когда компилятор не смог выполнить операции по подготовке кода узла. Чаще всего, эта ошибка является результатом внутренних некорректных операций."

class CGGraphSerializationError(CGBaseException):
    id = 7
    text = "Ошибка сериализации графа"
    desc = "Обнаружена ошибка сериализации графа. Информация: {ctx}"
    moreInfo = "Данная ошибка возникает при невозможности или ошибках сериализации графа узлов."

# ----------------------------------------
#   101-300 - ports exceptions
# ----------------------------------------

class CGPortTypeRequiredException(CGBaseException):
    id = 101
    desc = "Некоторые узлы получают типы своих портов при подключении к ним других узлов. Подключите к {src} узел, который определит тип портов"
    #moreInfo = "Узел {src} и его порт \"{portname}\" находятся в состоянии неопределенных портов, закрашенных белым цветом. Подключите к одному из этих белых портов другие узлы для того, чтобы тип "
    moreInfo = "Указанный порт требует обязательно подключения. Подключите к этому порту другой узел с совместимым типом данных."
class CGInputPortTypeRequiredException(CGPortTypeRequiredException):
    text = "Входной порт \"{portname}\" узла {src} требует подключения, так как не имеет типа"

class CGOutputPortTypeRequiredException(CGPortTypeRequiredException):
    text = "Выходной порт \"{portname}\" узла {src} требует подключения, так как не имеет типа"

class CGPortRequiredConnectionException(CGBaseException):
    id = 102
    text = "Входной порт \"{portname}\" узла {src} требует подключения, так как не имеет пользовательского свойства"
    desc = "Порт \"{portname}\" в узле не имеет опции пользовательских данных и требует подключенного значения."
    moreInfo = "Порт указанного узла не имеет виджета для ручной настройки данных, а потому требует подключенного узла с совместимым типом данных."

class CGPortTypeMissmatchException(CGBaseException):
    id = 103
    text = "Недопустимый тип для порта \"{portname}\" узла {src}"
    desc = "Узел {src} не может принять тип порта, полученный от {targ}. Требуется тип \'{ctx}\'"
    moreInfo = ""

class CGPortTypeClassMissmatchException(CGBaseException):
    id = 104
    text = "Недопустимый тип для порта \"{portname}\" узла {src}"
    desc = "Узел {src} не может принять тип порта, полученный от {targ}. Ожидался тип: {ctx}"
    moreInfo = "Узел {src} не может быть вызыван из объекта, в котором он не определён."

# ----------------------------------------
#   301-600 - nodes exceptions
# ----------------------------------------

#!NOT USED
class CGScopeLoopException(CGBaseException):
    id = 301
    text = "Узел {src} не может быть использован из-за ограничений области видимости, наложенных {targ}"
    desc = "Узел {targ} используетя в области видимости {ctx}, который накладывает ограничения для внешней области узла {src}. Уберите связь."

#!NOT USED
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
    moreInfo = "Каждая точка входа явдяется определением вызываемой функции, которые не могут быть определены более 1 раза. Удалите дубликаты с графа."

class CGReturnTypeUnexpectedException(CGBaseException):
    id = 305
    text = "Не требуемое возвращаемое значение для {src}"
    desc = "Точка входа {entry} не возвращает никаких значений. Уберите все возвраты значений из этой точки входа."

class CGReturnTypeMismatchException(CGBaseException):
    id = 306
    text = "Несоответствие возвращаемых значений для {entry}"
    desc = "Тип допустимого возвращаемого значения для {entry} ({ctx}) не совпадает с типом возвращаемого значения в {src}: {portname}. Точка входа должна принимать возвращаемый тип: {ctx}"

class CGReturnTypeNotFoundException(CGBaseException):
    id = 307
    text = "Отсутствие возвращаемого значения {src}"
    desc = "Точка входа {entry} должна возвращать значение типа ({ctx})."

class CGReturnNotAllBranchesException(CGBaseException):
    id = 308
    text = "Ожидается возврат значения после {src}"
    desc = "Все ветви точки входа {entry} должны возвращать значение типа ({ctx}). Подключите к {src} узел возврата значения."

#!NOT USED
class CGReturnNotExecutedException(CGBaseException):
    id = 309
    text = "Возвращаемое значение в {src} никогда не будет выполнено"
    desc = "К входным портам выполнения узла {src} не подключены узлы, либо один из подключенных узлов не имеет подключения входных портов."

class CGEntryCrossCompileException(CGBaseException):
    id = 310
    text = "Точка входа {entry} не может содержать связи с другими точками входа"
    desc = "Точка входа {entry} не может содержать подключения от другой точки входа {src}. Уберите связи между ними."

class CGUserEntryNotDefinedException(CGBaseException):
    id = 311
    text = "Точка входа {ctx} не определена"
    desc = "Пользовательская функция {ctx} не определена. Каждая пользовательская функция должна иметь определение."

class CGLoopControlException(CGBaseException):
    id = 312
    text = "Недопустимый контекст узла {src}"
    desc = "Узел {src} может быть использован только в циклах (в теле циклов)"

class CGSuperVoidReturnException(CGBaseException):
    id = 313
    text = "Базовый метод {src} не может возвращать значение"
    desc = "Базовый метод {src} не имеет возвращаемого значения. Уберите его выходное подключение к порту \'Значение\'"

class CGMemberNotExistsException(CGBaseException):
    id = 314
    text = "Узел {src} не относится к {ctx[1]}"
    desc = "Член \'{ctx[0]}\' не существует в классе \'{ctx[1]}\' (впервые определен в \'{ctx[2]}\'). Укажите явное подключение к порту \'{portname}\' типа \'{ctx[2]}\' или его дочерних типов."
    moreInfo = "Данная ошибка возникает, когда осуществляется попытка использования члена, не определенного и не унаследованного в указанном классе/графе. Необходимо указать явное подключение к порту \'{portname}\' узла {src} совместимого типа."

class CGLoopTimerException(CGBaseException):
    id = 315
    text = "Недопустимая пауза в {src}"
    desc = "Узел {src} является узлом с задержкой выполнения и не может быть использован в теле цикла {targ}."

class CGTimerUnallowedReturnException(CGBaseException):
    id = 316
    text = "Недопустимое возвращаемое значение для {src}"
    desc = "Узел {src} не может быть использован в {entry} с возвращаемым значением. Разрешается использование таймеров только в функциях, методах и событиях, которые не возвращают значений."
    moreInfo = "Любые асинхронные операции не вернут значение в вызываемой точке входа, так как вызывающий текущую точку входа никогда не ожидает результат операции в асинхронном виде."

class CGMethodOverrideNotFoundException(CGBaseException):
    id = 317
    text = "Недопустимая перегрузка {src}"
    desc = "Точка входа {entry} не может быть использована в этом графе (классе), так как не существует такого базового метода."
    moreInfo = "Переопределяемый метод или событие должно быть определено в базовом классе или его предках. Данная ошибка возникла из-за того, что предки класса \'{ctx}\' не содержат определения для {src}"

class CGCtorAndDtorSuperCallException(CGBaseException):
    id = 318
    text = "Узел {src} запрещён для {entry}"
    desc = "Точка входа {entry} является конструктором или деструктором и не может вызывать свои базовые версии."
    moreInfo = "Конструкторы и деструкторы автоматически вызывают все свои переопределенные базовые версии. Использование вызова базовых методов может привести к фатальным ошибкам программы. Уберите узел {src} из выполнения в {entry}."

# ----------------------------------------
#   601-700 - variables exceptions
# ----------------------------------------

class CGLocalVariableDuplicateUseException(CGBaseException):
    id = 601
    text = "Локальная переменная {src} ({ctx}) уже используется в {targ}"
    desc = "Локальные переменные можно использовать только внутри одной точки входа. Создайте новую переменную для использования в {entry}"
    moreInfo = "Локальные переменные создаются для конкретных точек входа и существуют пока выполняется точка входа."

class CGLocalVariableMetaKeywordNotFound(CGBaseException):
    id = 602
    text = "Точка входа {entry} не имеет определения мета-оператора для локальных переменных."
    desc = "<span style='color:darkorange;'> Обратитесь к разработчику для решения данной проблемы.</span> В точке входа не найден мета-оператор <b>initvars</b>. Вероятнее всего проблема вызывана ошибкой генерации кода."
    moreInfo = "Внутренняя ошибка компилятора. Рекомендуется обратиться к разработчику для решения данной проблемы."

#!NOT USED
class CGScopeVariableNotFoundException(CGBaseException):
    id = 603
    text = "Недопустимое использование подключения узла {src}"
    desc = "Узел {src} не может получить данные из недоступной области видимости узла {targ}."

class CGScopeLocalVariableException(CGBaseException):
    id = 604
    text = "Недопустимое использование {src}"
    desc = "Порт \"{portname}\" узла {src} не может получить данные из недоступной области видимости. Вероятнее всего ошибка вызывана попыткой множественного доступа узлом {targ}."