from enum import Enum

class CompileStatus(Enum):
    Compiled = 0
    Errors = 1
    Warnings = 2
    NotCompiled = 3

    @staticmethod
    def statusToString(stat):
        return stat.name
    @staticmethod
    def stringToStatus(str):
        for n in CompileStatus:
            if str == n.name:
                return n
        return CompileStatus.NotCompiled

    @staticmethod
    def getCompileIconByStatus(stat):
        if stat == CompileStatus.Compiled:
            return "data\\icons\\CompileStatus_Good"
        elif stat == CompileStatus.Errors:
            return "data\\icons\\CompileStatus_Fail"
        elif stat == CompileStatus.Warnings:
            return "data\\icons\\CompileStatus_Warning"
        else:
            return "data\\icons\\CompileStatus_Working"
        
    @staticmethod
    def getCompileTextByStatus(stat,withColor=False):
        rez = CompileStatus.getCompileTextByStatus_Internal(stat)
        if not withColor:
            return rez
        else:
            return f"<font color={CompileStatus.getCompileColorByStatus(stat)}>{rez}</font>"
        
    @staticmethod
    def getCompileColorByStatus(stat):
        if stat == CompileStatus.Compiled:
            return "green"
        elif stat == CompileStatus.Errors:
            return "red"
        elif stat == CompileStatus.Warnings:
            return "orange"
        else:
            return "#99742B"

    @staticmethod
    def getCompileTextByStatus_Internal(stat):
        if stat==CompileStatus.Compiled:
            return "Скомпилирован"
        elif stat==CompileStatus.Errors:
            return "Не скомпилирован, есть ошибки"
        elif stat==CompileStatus.Warnings:
            return"Скомпилирован, есть предупреждения"
        elif stat==CompileStatus.NotCompiled:
            return "Ожидает компиляции"
        else:
            return f"НЕИЗВЕСТНЫЙ СТАТУС {stat.name}"

