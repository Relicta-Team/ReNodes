
from typing import Any


class Logger:
    def __init__(self,object):
        self.category = str(object.__class__.__name__)

    def formatlog(self,cat,mes):
        return f"[{self.category}] ({cat})    {mes}"

    def log(self,msg):
        print(self.formatlog("LOG",msg))
    
    def warn(self,msg):
        print(self.formatlog("WARN",msg))
    
    def error(self,msg):
        print(self.formatlog("ERROR",msg))
    
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        print(self.formatlog("INFO",args[0]))