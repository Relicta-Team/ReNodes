import iniparser2
from os.path import *

configValues = {
    "main": {
        "version": 1,
        "tempvalue": True
    },
    "visual": {
        "testvalue": "test stringg"
    }
}

class Config:
    
    parser : iniparser2.INI
    cfgPath : str = "config.ini"
    isLoaded : bool = False

    @staticmethod
    def init():
        print("Initialize config reader")
        Config.parser = iniparser2.INI()
        
        #check if config file exists
        if exists(Config.cfgPath):
            Config.readConfig()
        else:
            Config.createConfig()
        ver = Config.parser.get_int("version","main")
        print(f"Config version: {ver}")
        if (ver != configValues["main"]["version"]):
            print("Version not actual")
            Config.createConfig()
        
        print("Config initialized")
        Config.isLoaded = True
    
    @staticmethod
    def readConfig():
        print("Reading config")
        Config.parser.read_file(Config.cfgPath)
    
    @staticmethod
    def createConfig():
        print("Creating new config")
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
        print("Config saved")