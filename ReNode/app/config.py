import iniparser2
from os.path import *
import ReNode.app.Logger
import logging
import re

configValues = {
    "main": {
        "version": 2,
        "workdir": "src\\ReNode",
        #"tempvalue": True
    },
    "internal": {
        # geometry and state mainWindow
        "winstate": None,
        "winpos": None,
        "opened_sessions": "empty",
    },
    "visual": {
        #"testvalue": "test stringg"
    }
}

class Config:
    
    parser : iniparser2.INI
    cfgPath : str = "config.ini"
    isLoaded : bool = False
    logger = logging.getLogger("main")
    

    @staticmethod
    def init():
        Config.logger.info("Initialize config reader")
        Config.parser = iniparser2.INI()
        
        #check if config file exists
        if exists(Config.cfgPath):
            Config.readConfig()
        else:
            Config.createConfig()
        ver = Config.parser.get_int("version","main")
        Config.logger.info(f"Loaded config version: {ver}")
        
        if (ver != configValues["main"]["version"]):
            Config.logger.info(f"Version not actual; Old: {ver}; New: {configValues['main']['version']}")
            Config.updateConfig()
        
        Config.logger.info(f"Config initialized (version {ver})")
        Config.isLoaded = True
    
    @staticmethod
    def readConfig():
        Config.logger.info("Reading config")
        Config.parser.read_file(Config.cfgPath)

    @staticmethod
    def updateConfig():

        # проход по секциям конфигов в файле. несуществующие удаляем
        allSections = configValues.keys()
        for sectionName in Config.parser.sections():
            if sectionName not in allSections:
                Config.parser.remove_section(sectionName)
                Config.logger.info(f"Removed old section {sectionName}")

        # проход по секциям конфигов в конфиге. несуществующие добавляем
        for sectionName,sectionItems in configValues.items():

            if not Config.parser.has_section(sectionName):
                Config.parser.set_section(sectionName)
                Config.logger.info(f"Added new section {sectionName}")
                #register values
                # Register values in the existing section
                for key, value in sectionItems.items():
                    Config.parser.set(key, value, section=sectionName)
                    Config.logger.info(f"Registered value {key} in section {sectionName}")
            else:
                Config.logger.info(f"Validating section {sectionName} values")
                for key, value in sectionItems.items():
                    existsProp = Config.parser.has_property(key, sectionName)
                    equalVals = existsProp and value == Config.parser.get(key, sectionName)
                    if not existsProp or not equalVals:
                        Config.parser.set(key, value, section=sectionName)
                        Config.logger.info(f"Property updated [{sectionName}]{key} -> (exists: {existsProp}, equals: {equalVals})")

        Config.logger.info("Config updated")


    
    @staticmethod
    def createConfig():
        Config.logger.info("Creating new config")
        parser = Config.parser
        #clear config
        for sect in Config.parser.sections().copy():
            parser.remove_section(sect)

        # insert config values from configValues
        for key in configValues:
            parser.set_section(key)
            for kint in configValues[key]:
                parser.set(kint,configValues[key][kint],section=key)
        #print(parser)
    @staticmethod
    def saveConfig():
        if not Config.isLoaded: return
        
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        obj = NodeGraphComponent.refObject
        Config.set("winstate",obj.mainWindow.saveState(),"internal")
        Config.set("winpos",obj.mainWindow.saveGeometry(),"internal")

        Config.set("opened_sessions",obj.sessionManager.getOpenedSessionPathes(),"internal")

        Config.parser.write(Config.cfgPath)
        Config.logger.info("Config saved")
    
    @staticmethod
    def get(key,section="main"):
        return Config.parser.get(key,section)
    
    @staticmethod
    def set(key,value,section="main"):
        if isinstance(value,str) and value=="":
            #raise ValueError(f"[{section}]{key}: Value can't be empty string")
            Config.logger.error(f"[{section}]{key}: Value can't be empty string")
        Config.parser.set(key,value,section)
    
    @staticmethod
    def get_int(key,section="main"):
        return Config.parser.get_int(key,section)
    
    @staticmethod
    def get_float(key,section="main"):
        return Config.parser.get_float(key,section)

    @staticmethod
    def get_str(key,section="main"):
        return Config.parser.get_str(key,section)

    @staticmethod
    def get_bool(key,section="main"):
        return Config.parser.get_bool(key,section)