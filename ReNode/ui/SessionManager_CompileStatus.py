from enum import Enum

class CompileStatus(Enum):
    Compiled = 0
    Errors = 1
    Warnings = 2
    NotCompiled = 3


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

