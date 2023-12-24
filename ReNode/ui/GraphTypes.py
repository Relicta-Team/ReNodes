from ReNode.app.CodeGenWarnings import *

class GraphTypeFactory:
    """
    Фабрика типов графа
    """

    instanceDict = None

    @staticmethod
    def createInstances():
        GraphTypeFactory.instanceDict = {}
        GraphTypeFactory.registerGraphType(GamemodeGraph)
        GraphTypeFactory.registerGraphType(RoleGraph)
        GraphTypeFactory.registerGraphType(GameObjectGraph)

    @staticmethod
    def registerGraphType(type):
        if not issubclass(type,GraphTypeBase):
            raise Exception(f"Type <{type}> must be subclass of <GraphTypeBase>")
        if not type.systemName:
            raise Exception(f"Type <{type}> must have <systemName> attribute")
        GraphTypeFactory.instanceDict[type.systemName] = type()

    @staticmethod
    def getAllInstances():
        """
            Возвращает все зарегистрированные типы графов\n
            Возвращаемый лист можно изменять (является копией)
        """
        if not GraphTypeFactory.instanceDict:
            GraphTypeFactory.createInstances()
        return list(GraphTypeFactory.instanceDict.values())

    @staticmethod
    def getInstanceByType(type_):
        if not GraphTypeFactory.instanceDict:
            GraphTypeFactory.createInstances()
        
        if type_ is type:
            if not issubclass(type_,GraphTypeBase):
                raise Exception(f"Type <{type_}> must be subclass of <GraphTypeBase>")
            
            type_ = type_.systemName
        instance : GraphTypeBase = GraphTypeFactory.instanceDict.get(type_)
        if not instance:
            raise Exception(f"Type <{type_}> not found")
        return instance

class GraphTypeBase:
    """
        Базовый тип графа. Тут текстовая информация, метаинформация для кодогенератора и обработчик узлов
    """
    
    systemName = ""

    name = "Неизвестный тип"
    description = "Без описания"

    create_headerText = "Создание графа"
    create_nameText = "Имя графа"
    create_classnameText = "Имя класса графа"
    path_nameText = "Путь до графа"
    parent_nameText = "Родительский граф"
    parent_classnameText = "object" #type

    canCreateFromWizard = False #что можно создать через визард

    # Где хранятся графы
    savePath = "graphs\\Base" 
    createFolder = False #создает папку при сохранении (используется имя типа, например имя класса режима)

    def resolvePath(self,checkedPath):
        """Обработчик пути до графа. К примеру роли могут лежать в папке режима"""
        return checkedPath

    def createInfoDataProps(self,options:dict):
        newDict = {}
        return newDict,f"Метод генератора настроек для {self.__class__.__name__} не переопределен"


    def getName(self):
        return self.name
    
    def getDescription(self):
        return self.description
    
    #region Code handlers
        

    def createGenMetaInfoObject(self,cg,idat) -> dict[str,object]:
        """
            Создает контекст базовых данных для генератора. В исходной версии возвращаемый словарь хранит ссылку на инстанс генератора и словарь infoData из графа
        """
        return {
            "codegen":cg,
            "infoData":idat
        }

    def cgHandleWrapper(self,sourceCode,metaObj):
        """
            Получает обертку графа для кодогенератора.
            
            Это базовый метод для получения тела инструкций кода (например, заголовка класса)
        """
        raise NotImplementedError("cgHandleWrapper is not implemented")
        return ""
    
    def cgHandleVariables(self,metaObj):
        """
            Обработчик переменных для кодогенератора.
        """
        raise NotImplementedError("cgHandleVariables is not implemented")
        return ""
    
    def cgHandleInspectorProps(self,metaObj):
        """
            Обработчик свойств инспектора.
        """
        raise NotImplementedError("cgHandleInspectorProps is not implemented")
        return ""
    
    def handlePostReadyEntry(self,nodeObject,metaObj):
        """Постобработчик готовой точки входа"""
        from ReNode.app.CodeGen import CodeGenerator
        nodeObject :CodeGenerator.NodeData = nodeObject
        code = ""
        cgObj : CodeGenerator = metaObj.get('codegen')
        node_code = nodeObject.code
        classLibData = nodeObject.classLibData
        
        if not nodeObject.isReady: return ""

        hasConnections = nodeObject.getConnectionOutputs()
        
        if "@initvars" in node_code:
                initVarsCode = ""
                for nameid in cgObj.localVariablesUsed:
                    
                    if cgObj._addComments:
                        initVarsCode += f"//init_lv:{cgObj.localVariableData[nameid]['varname']}\n"
                    initVarsCode += f'private {cgObj.localVariableData[nameid]["alias"]} = {cgObj.localVariableData[nameid]["initvalue"]};\n'
                
                #register scopename for function
                from ReNode.app.CodeGenExceptions import CGReturnTypeUnexpectedException,CGReturnTypeMismatchException,CGReturnTypeNotFoundException,CGReturnNotAllBranchesException
                hasReturns = False
                retTypeExpect = nodeObject.classLibData.get("returnType","")
                executedReturns = [ret for ret in nodeObject.returns if ret.visitedExecFlow]
                if executedReturns:
                    hasReturns = True
                    if retTypeExpect in ['null','']:
                        cgObj.exception(CGReturnTypeUnexpectedException,source=nodeObject,entry=nodeObject)
                    else:
                        #validate returns
                        retTypenameExpect = cgObj.getVariableManager().getTextTypename(retTypeExpect)
                        for retNode in executedReturns:
                            retType = retNode.objectData['input_ports'][1]['type']
                            if retType and retType != retTypeExpect:
                                retTypename = cgObj.getVariableManager().getTextTypename(retType)
                                cgObj.exception(CGReturnTypeMismatchException,source=retNode,entry=nodeObject,context=retTypenameExpect,portname=retTypename)
                            pass
                else:
                    if retTypeExpect not in ['null','']:
                        retTypenameExpect = cgObj.getVariableManager().getTextTypename(retTypeExpect)
                        cgObj.exception(CGReturnTypeNotFoundException,source=nodeObject,entry=nodeObject,context=retTypenameExpect)

                if retTypeExpect not in ['null','']:
                    lastEx = cgObj._exceptions
                    canCheckAllEnds = True
                    if lastEx:
                        lastEx = lastEx[-1]
                        # дополнительная проверка. если нет ни одного возвращаемого значения то не будем выполнять проверки конца веток
                        if not isinstance(lastEx,CGReturnTypeNotFoundException):         
                            canCheckAllEnds = False

                    if canCheckAllEnds:
                        noRetList = nodeObject.endsWithNoReturns
                        retTypenameExpect = cgObj.getVariableManager().getTextTypename(retTypeExpect)
                        #в теле циклов возвращение значения не ожидаем...
                        # если есть хотябы один возврат
                        for noRetobj in noRetList:
                            scope = noRetobj.getScopeObj()
                            if scope and scope.nodeType.name == "SCOPED_LOOP":
                                # если цикловых скоупов больше 1 значит возврат требуется из другого места
                                #if len(noRetList) > 1:
                                continue
                            if not noRetobj.visitedExecFlow:
                                cgObj.nodeWarn(CGNodeNeverCalledWarning,source=noRetobj)
                                continue
                            cgObj.exception(CGReturnNotAllBranchesException,source=noRetobj,entry=nodeObject,context=retTypenameExpect)

                if hasReturns:
                    initVarsCode += "\nSCOPENAME \"exec\";"

                node_code = node_code.replace("@initvars",initVarsCode)
        else:
            
            if hasConnections:
                from ReNode.app.CodeGenExceptions import CGLocalVariableMetaKeywordNotFound
                cgObj.exception(CGLocalVariableMetaKeywordNotFound,entry=nodeObject,source=nodeObject)

        # check if node not overriden code
        if not hasConnections:
            cgObj.nodeWarn(CGEntryNodeNotOverridenWarning,source=nodeObject)

        nodeObject.code = node_code

    def handlePreStartEntry(self,nodeObjec,metaObj):
        """Предварительная обработка точки входа"""
        pass
    #endregion


    returnNodeType = "control.return"
    def handleReturnNode(self,entryObject,nodeObject,returnObject,metaObj):
        if returnObject.nodeClass == self.returnNodeType:
            entryObject.returns.append(returnObject)
        elif not returnObject.getConnectionOutputs():
            #прописываем узлы без возвращаемого значения
            entryObject.endsWithNoReturns.append(returnObject)

    def handleReadyNode(self,nodeObject,entryObj,metaObj):
        from ReNode.app.CodeGen import CodeGenerator
        
        """
            Обработчик готового узла при кодогенерации.
            Этот метод вызывается сразу когда узел помечается как готовый на подстановку.
            При вызове этого метода внутри объекта узла уже содержится актуальный код
        """
        cgObj : CodeGenerator = metaObj.get('codegen')
        
        # подготовка метода
        if "classInfo" in nodeObject.classLibData:
            mtype = nodeObject.classLibData['classInfo']['type']
            if mtype == 'method':
                nodeObject.code = cgObj.prepareMemberCode(nodeObject.classLibData,nodeObject.code)

        libOuts = nodeObject.classLibData['inputs']
        if libOuts:
            connInp = nodeObject.getConnectionInputs()
            usedExec = False
            lastExec = ""
            hasExec = False
            for k,v in libOuts.items():
                if v.get('type')=="Exec":
                    hasExec = True
                    if not lastExec: lastExec = k   
                    conId = connInp.get(k)
                    if conId:
                        usedExec = True
                        break
            if not usedExec:
                if nodeObject == entryObj:
                    cgObj.nodeWarn(CGEntryNodeNotOverridenWarning,source=nodeObject)
                    raise Exception("Unsupported rule: Entry node not overriden")
                else:
                    #if nodeObject.visitedExecFlow:
                    if hasExec:
                        cgObj.nodeWarn(CGNodeNotUsedWarning,source=nodeObject,portname=lastExec)

class ClassGraphType(GraphTypeBase):

    def createInfoDataProps(self, options: dict):
        opts = {}

        if not options:
            return None,"Опции не установлены"

        name_ = options.get('name')
        classname_ = options.get('classname')
        parCls_ = options.get('parent')
        if not name_:
            return opts,"Имя не установлено"
        if not classname_:
            return opts,"Имя класса не установлено"
        if not parCls_:
            return opts,"Родительский граф не установлен"
        
        opts['type'] = self.systemName
        opts['name'] = name_
        opts['classname'] = classname_
        opts['parent'] = parCls_
        opts['props'] = {
            "fields": {},
            "methods": {}
        }

        return opts,""


    def createGenMetaInfoObject(self, cg, idat):
        data = super().createGenMetaInfoObject(cg, idat)

        data['classname'] = idat['classname']
        data['parent'] = idat['parent']

        return data
    
    def cgHandleVariables(self, metaObj):
        from ReNode.app.CodeGen import CodeGenerator
        code = ""
        cgObj : CodeGenerator = metaObj.get('codegen')

        for vid,vdat in cgObj.getVariableDict().get('classvar',{}).items():
            varvalue = cgObj.updateValueDataForType(vdat["value"],vdat['type'])
            
            if cgObj._addComments:
                code += f"\n//cv_init:{vdat['name']}"
            code += "\n" + f'var({cgObj.localVariableData[vid]["alias"]},{varvalue});'
        
        return code
    
    def cgHandleInspectorProps(self, metaObj):
        from ReNode.app.CodeGen import CodeGenerator
        code = ""
        cgObj : CodeGenerator = metaObj.get('codegen')
        baseClass = metaObj.get('parent')
        infoDataProps = metaObj['infoData']['props']
        classInfo = cgObj.getFactory().getClassData(baseClass)
        inspectorProps = classInfo['inspectorProps']

        for fieldSystemName,fieldValue in infoDataProps['fields'].items():
            if cgObj._addComments:
                code += f"\n//p_var: {fieldSystemName}"
            varvalue = cgObj.updateValueDataForType(fieldValue, inspectorProps['fields'][fieldSystemName]['return'])
            #TODO custom variable defcode
            code += "\n" + f"[\"{fieldSystemName}\",{varvalue}] call pc_oop_regvar;"
        
        for constSystemname, constval in infoDataProps['methods'].items():
            if cgObj._addComments:
                code += f"\n//p_const: {constSystemname}"
            constProp = inspectorProps['methods'][constSystemname]
            sigName = 'methods.' + constProp['node']
            varvalue = cgObj.updateValueDataForType(constval, constProp['return'])
            constLibInfo = cgObj.getFactory().getNodeLibData(sigName)
            defCode = constLibInfo.get('defcode',"func(@thisName) { @propvalue };")
            defCode = cgObj.prepareMemberCode(constLibInfo,defCode)

            defCode = defCode.replace("@propvalue",varvalue)

            code += "\n" + defCode

        return code
    
    def handlePreStartEntry(self, nodeObject, metaObj):
        from ReNode.app.CodeGen import CodeGenerator
        from copy import deepcopy
        nodeObject :CodeGenerator.NodeData = nodeObject
        code = ""
        cgObj : CodeGenerator = metaObj.get('codegen')
        node_code = nodeObject.code
        classLibData = nodeObject.classLibData
        objData = nodeObject.objectData

        userid = nodeObject.getUserNodeId()
        if objData.get("port_deletion_allowed") and userid:
            userdata = cgObj.getVariableManager().getVariableDataById(userid)
            #pathing classLib
            #classLibData = deepcopy(classLibData) #!копирование не требуется
            
            inps = {}
            for dictPort in objData['input_ports']:
                inps[dictPort['name']] = {
                    'type': dictPort['type'],
                }
            outs = {}
            for dictPort in objData['output_ports']:
                outs[dictPort['name']] = {
                    'type': dictPort['type'],
                }
            classLibData['inputs'] = inps
            classLibData['outputs'] = outs

            #update classmeta
            classLibData['classInfo'] = {
                "class": metaObj['classname'],
                "name": userdata['name'].lower(),
                "type": "method",
            }
            #update return type
            classLibData['returnType'] = userdata['returnType']

        # пользовательское определение функции
        uservar = nodeObject.getUserNodeType()
        if uservar and uservar == "classfunc":
            node_code = cgObj.getFunctionData(nodeObject.nodeClass,nodeObject.getUserNodeId())

        node_code = cgObj.prepareMemberCode(classLibData,node_code)

        nodeObject.code = node_code

    def cgHandleWrapper(self, sourceCode, metaObj):
        from ReNode.app.CodeGen import CodeGenerator
        cgObj : CodeGenerator = metaObj.get('codegen')
        className = metaObj['classname']
        parentName = metaObj['parent']

        wrapperCode = f'editor_attribute(\"NodeClass\")\nclass({className}) extends({parentName})\n' + sourceCode + "\nendclass"
        
        return wrapperCode

class GamemodeGraph(ClassGraphType):
    name = "Режим"
    description = "Игровой режим предназначен для реализации состояния игры."
    systemName = "gamemode"
    
    create_headerText = "Создание режима"
    create_nameText = "Имя режима"
    create_classnameText = "Имя класса режима"
    path_nameText = "Путь к файлу режима"
    parent_nameText = "Родительский режим"
    parent_classnameText = "GMBase"
    
    canCreateFromWizard = True
    createFolder = True

    pass

class RoleGraph(ClassGraphType):
    name = "Роль"
    description = "Роль для игрового режима. В роли определяется снаряжение, стартовая позиция и навыки персонажа."
    systemName = "role"
    
    create_headerText = "Создание роли"
    create_nameText = "Имя роли"
    create_classnameText = "Имя класса роли"
    path_nameText = "Путь к файлу роли"
    parent_nameText = "Родительская роль"
    parent_classnameText = "BasicRole"

    canCreateFromWizard = True
    
class GameObjectGraph(ClassGraphType):
    name = "Игровой объект"
    description = "Игровой объект с пользовательской логикой является переопределенным (унаследованным) от другого объекта. Например, мы можем создать игровой объект, унаследованный от двери и переопределить событие её открытия."
    systemName = "gobject"

    canCreateFromWizard = False
# TODO: add more:
# ["Скриптовый объект","scriptedobject","Скриптовый игровой объект с поддержкой компонентов. Это более гибкий инструмент создания игровых объектов, использующий общий класс и реализующий широкий спектр компонентов. С помощью него мы, например, можем создать контейнер, который можно съесть и из которого можно стрелять."],
# ["Компонент","component","Пользовательский компонент, добавляемый в скриптовый объект."],
# ["Сетевой виджет","netdisplay","Клиентский виджет для взаимодействия с игровыми и скриптовыми объектами. Например, можно сделать виджет с кнопкой, при нажатии на которую будет происходить какое-то действие."],
# ["Объект","object","Объект общего назначения."],