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


class NodeColor(Enum):
    Operator = rgbaToHex(119,119,119,255) #white

    Event = rgbaToHex(255,0,0,255) #red
    Function = rgbaToHex(121,201,255,255) #blue
    PureFunction = rgbaToHex(170,238,160,255) #green
    EntryFunction = rgbaToHex(204,0,255,255) #yellow

    @staticmethod
    def isConstantColor(nodeclass):
        return nodeclass.startswith("operators.")
