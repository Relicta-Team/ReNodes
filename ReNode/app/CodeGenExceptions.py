

class CGBaseException:
    id = 0
    text = "Неизвестная ошибка"
    def __init__(self,**kwargs) -> None:
        self.sourceNode = kwargs.get('src') or ""
        self.portName = kwargs.get('portname') or ""
        self.targetNode = kwargs.get('targ') or ""
    
    def getExceptionText(self):
        class_ = self.__class__
        f"ERR-{class_.id} :" + class_.text.format(
            src=self.sourceNode,
            portname=self.portName,
            targ=self.targetNode
        )


class CGVariablePathAccessException(CGBaseException):
    id = 1
    text = "Порт \"{portname}\" узла \"{sourceNode}\" не может быть использован из-за ограничений пути"