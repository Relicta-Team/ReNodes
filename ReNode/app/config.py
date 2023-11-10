import iniparser2
from os.path import *
import ReNode.app.Logger
import logging

configValues = {
    "main": {
        "version": 2,
        #"tempvalue": True
    },
    "internal": {
        # geometry and state mainWindow
        "winstate": None,
        "winpos": None
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
            Config.createConfig()
        
        Config.logger.info(f"Config initialized (version {ver})")
        Config.isLoaded = True
    
    @staticmethod
    def readConfig():
        Config.logger.info("Reading config")
        Config.parser.read_file(Config.cfgPath)
        #TODO update loaded config
        # check existen values
        # for cfgSection,cfgItems in configValues.items():
        #     # delete nonexisten sections
        #     if cfgSection not in Config.parser.sections():
        #         Config.parser.remove_section(cfgSection)
        #         Config.logger.info(f"Removed old section {cfgSection}")
        #     # add nonexisten section items
        #     for propKey,propVal in cfgItems.items():
        #         if not Config.parser.has_property(propKey,cfgSection):
        #             Config.parser.set(propKey,propVal,section=cfgSection)
        #             Config.logger.info(f"Added new property {propKey} in section {cfgSection}")

    
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

        Config.parser.write(Config.cfgPath)
        Config.logger.info("Config saved")
    
    @staticmethod
    def get(key,section="main"):
        return Config.parser.get(key,section)
    
    @staticmethod
    def set(key,value,section="main"):
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