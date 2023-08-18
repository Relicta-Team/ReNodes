
import sys
from typing import Any
import logging

def RegisterLoggerStdoutHandler(logobject : logging.Logger):
	#stdout handler
	if len(logobject.handlers) == 0:
		stdout_hndl = logging.StreamHandler(sys.stdout)
		stdout_hndl.setFormatter(logging.Formatter('[%(name)s::%(levelname)s] - %(message)s'))
		logobject.addHandler(stdout_hndl)

def RegisterLogger(logname="main"):
	logobject = logging.getLogger(logname)
	logobject.setLevel(logging.DEBUG)
	RegisterLoggerStdoutHandler(logobject)
	return logobject
