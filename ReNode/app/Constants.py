from enum import Enum
from PyQt5.QtGui import QColor

def hexToRGBA(hex):
        hex = hex.lstrip("#")
        if len(hex) == (6):
            hex += "ff"
        return list(int(hex[i:i+2], 16) for i in (0, 2, 4, 6))

def hexToQColor(hex):
    return QColor(*hexToRGBA(hex))

def rgbaToHex(r,g,b,a=255):
    return f"#{r:02x}{g:02x}{b:02x}{a:02x}"

class NodeRenderType(Enum):
    Default = 0
    NoHeader = 1
    NoHeaderText = 2
    NoHeaderIcon = 3

    Reroute = 4

    @staticmethod
    def getNoHeaderTypes():
        return [NodeRenderType.NoHeaderIcon,NodeRenderType.NoHeaderText,NodeRenderType.NoHeader,NodeRenderType.Reroute]

    @staticmethod
    def typeExists(value):
        if value in NodeRenderType.__members__:
            return True
        if value in [v.value for v in NodeRenderType.__members__.values()]:
            return True
        return False


class NodeColor(Enum):
    Operator = rgbaToHex(119,119,119,255) #white

    Event = rgbaToHex(255,0,0,255) #red #5b0802
    Function = "#004568" #rgbaToHex(121,201,255,255) #blue #004568
    PureFunction = "#346B2B"#rgbaToHex(170,238,160,255) #green
    EntryFunction = "#955e00" #yellow
    Constant = "#124d41"
    Getter = "#25888F"
    EnumSwitch = '#8C7516'
    StructMake = "#011594"

    @staticmethod
    def getMethodMapAssoc():
        return {
            "method": {
                "color": NodeColor.Function.value,
                "icon": "data\\icons\\icon_BluePrintEditor_Function_16px"
            },
            "event": {
                "color": NodeColor.Event.value,
                "icon": "data\\icons\\icon_Blueprint_Event_16x",
                "code": "func(@thisName) {@thisParams; @out.1};"
            },
            "get": {
                "color": NodeColor.Getter.value,
                "icon": "data\\icons\\FIB_VarGet"
            },
            "const": {
                "color": NodeColor.Constant.value,
                "icon": "data\\icons\\Icon_Sequencer_Key_Part_24x"
            },
            "def": {
                "color": NodeColor.EntryFunction.value,
                "icon": "data\\icons\\icon_Blueprint_OverrideFunction_16x",
                "code": "func(@thisName) {@thisParams; @out.1};"
            }
        }

    @staticmethod
    def isConstantColor(nodeclass):
        """Узел с неизменяемым цветом"""
        return nodeclass.startswith("operators.")



class NodeLambdaType(Enum):
    """Типы (имена классов узлов) пользовательских функций времени выполнения"""

    Lambda = 'operators.lambda'
    LambdaObj = 'operators.lambda_obj'
    LambdaEvent = 'operators.lambda_event'
    LambdaEventList = 'operators.lambda_eventlist'

    @staticmethod
    def hasObjectCallerPort(typename):
        """Допускается ли порт Цель для проверяемого имени класса узла"""
        return typename in [NodeLambdaType.LambdaObj.value,NodeLambdaType.LambdaEvent.value,NodeLambdaType.LambdaEventList.value]
    
    @staticmethod
    def isLambdaEntryNode(typename):
        """Перечисление всех типов узлов: локальные функции, делегаты, события"""
        return typename in [v.value for v in NodeLambdaType.__members__.values()]
    
    @staticmethod
    def isCallLambdaNode(typename):
        return typename.startswith("operators.call_lambda")
    
    @staticmethod
    def hasContextInLambdaType(typename):
        return typename == NodeLambdaType.LambdaObj.value