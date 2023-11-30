from ReNode.ui.LoggerConsole import LoggerConsole

class CGBaseWarning:
    id = 0
    text = "Неизвестное предупреждение"
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
    
    def getShortWarnInfo(self):
        return f'WARN-{self.__class__.id}'

    def getWarningDescription(self):
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

    def getWarningText(self,addDesc = False):
        class_ = self.__class__
        postText = class_.desc if addDesc else ""

        if postText:
            warnDesc = self.getWarningDescription()
            if warnDesc:
                postText = "<span style='color:#FFF2B0;'>"+warnDesc+"</span>"
                postText = "\n- Подробнее: " + postText
                #postText = '<p title="tootip">some block of text</p>'
            return f"<b>WARN-{class_.id}</b>: " + class_.text.format(
                src=self.src,
                portname=self.portname,
                targ=self.targ,
                ctx=self.ctx,
                entry=self.entry
            ) + postText



# ----------------------------------------
#   1-100 - reserved warnings
# ----------------------------------------
class CGGenericWarning(CGBaseWarning):
    id = 1
    text = "{ctx}"
    desc = ""

# ----------------------------------------
#   101-300 - ports warnings
# ----------------------------------------

# ----------------------------------------
#   301-600 - nodes warnings
# ----------------------------------------
class CGNodeNotUsedWarning(CGBaseWarning):
    id = 301
    text = "Неиспользуемый узел {src}"
    desc = "Для того, чтобы код узла {src} был сгенерирован, необходимо подключить узел к входному порту \"{portname}\"."

class CGEntryNodeNotOverridenWarning(CGBaseWarning):
    id = 302
    text = "Отсутствие логики точки входа {src}"
    desc = "Реализуйте логику точки входа {src}, либо удалите её."

# ----------------------------------------
#   601-700 - variables warnings
# ----------------------------------------

