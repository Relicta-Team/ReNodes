import iniparser2
from os.path import *
import ReNode.app.Logger

configValues = {
    "main": {
        "version": 1,
        "tempvalue": True
    },
    "visual": {
        "testvalue": "test stringg"
    }
}
class CONFIG:
    pass
class Config:
    
    parser : iniparser2.INI
    cfgPath : str = "config.ini"
    isLoaded : bool = False
    logger = ReNode.app.Logger.Logger(CONFIG())
    

    @staticmethod
    def init():
        Config.logger.log("Initialize config reader")
        Config.parser = iniparser2.INI()
        
        #check if config file exists
        if exists(Config.cfgPath):
            Config.readConfig()
        else:
            Config.createConfig()
        ver = Config.parser.get_int("version","main")
        Config.logger.log(f"Config version: {ver}")
        if (ver != configValues["main"]["version"]):
            Config.logger.log("Version not actual")
            Config.createConfig()
        
        Config.logger.log("Config initialized")
        Config.isLoaded = True
    
    @staticmethod
    def readConfig():
        Config.logger.log("Reading config")
        Config.parser.read_file(Config.cfgPath)
    
    @staticmethod
    def createConfig():
        Config.logger.log("Creating new config")
        parser = Config.parser
        # insert config values from configValues
        for key in configValues:
            parser.set_section(key)
            for kint in configValues[key]:
                parser.set(kint,configValues[key][kint],section=key)
        #print(parser)
    @staticmethod
    def saveConfig():
        if not Config.isLoaded: return
        Config.parser.write(Config.cfgPath)
        Config.logger.log("Config saved")
    
    @staticmethod
    def get(key,section="main"):
        return Config.parser.get(section,key)
    
    @staticmethod
    def set(key,value,section="main"):
        Config.parser.set(section,key,value)
    
    @staticmethod
    def get_int(key,section="main"):
        return Config.parser.get_int(section,key)
    
    @staticmethod
    def get_float(key,section="main"):
        return Config.parser.get_float(section,key)

    @staticmethod
    def get_str(key,section="main"):
        return Config.parser.get_str(section,key)

    @staticmethod
    def get_bool(key,section="main"):
        return Config.parser.get_bool(section,key)