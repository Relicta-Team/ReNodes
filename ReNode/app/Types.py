from NodeGraphQt.qgraphics.port import PortItem
from NodeGraphQt.constants import PortTypeEnum
from re import findall


def validate_connections(fromPort : PortItem,toPort : PortItem):
    fp = make_portvalidation_request(fromPort)
    tp = make_portvalidation_request(toPort)

    return validate_connections_serialized(fp,tp)

def generate_ONdata_fromNodeLibData(fdat):
    """Генератор темплейт значений ноды по классу"""
    port_deletion_allowed = fdat.get("runtime_ports",False)
    
    custom_values = {}
    for optK, optDV in fdat.get("options",{}).items():
        custom_values[optK] = optDV.get('default',None)

    rdat = {
      "type_":"runtime_domain.RuntimeNode",
      "icon":None,
      "name":fdat['name'],
      "color":None,
      "border_color":None,
      "text_color":None,
      "disabled":False,
      "selected":False,
      "visible":True,
      "width":0,
      "height":0,
      "pos":None,
      "layout_direction":0,
      "port_deletion_allowed":port_deletion_allowed,
      "subgraph_session":{},
      "custom":custom_values,
      "class_":fdat['class_']
    }

    if port_deletion_allowed:
        iprts = []
        oprts = []
        for k,v in fdat.get("inputs",{}).items():
            iprts.append({
                "name":k,
                "type":v['type'],
                'multi_connection': v.get('mutliconnect',False),
            })
        for k,v in fdat.get("outputs",{}).items():
            oprts.append({
                "name":k,
                "type":v['type'],
                'multi_connection': v.get('mutliconnect',False),
            })
        rdat['input_ports'] = iprts
        rdat['output_ports'] = oprts

    return rdat

def make_portvalidation_request(port:PortItem|dict,nodeCtxInp=None,ptypeCtx=None):
    isPobj = isinstance(port,PortItem)
    
    from ReNode.ui.NodeGraphComponent import NodeGraphComponent
    fact = NodeGraphComponent.refObject.getFactory()

    if isPobj:
        nodeCtx = port.refPort.model.node
    else:
        if isinstance(nodeCtxInp,dict):
            nodeCtxInp = generate_ONdata_fromNodeLibData(nodeCtxInp)
        else:
            raise Exception("Unhandled type of nodeCtxInp: {}".format(type(nodeCtxInp)))
        
        nodeCtx = nodeCtxInp
    _isAPNode = nodeCtx.isAutoPortNode() if isPobj else "autoportdata" in nodeCtx.get("custom",{})
    pname = port.name if isPobj else port['name']
    ptype = port.port_type if isPobj else ptypeCtx
    ncls = nodeCtx.nodeClass if isPobj else nodeCtx['class_']
    
    if isPobj:
        _ldat = nodeCtx.getFactoryData()
    else:
        _ldat = fact.getNodeLibData(ncls)

    pall_dat = _ldat['inputs' if ptype == 'in' else 'outputs']
    if pname in pall_dat:
        nlib_pdat = pall_dat[pname]
    else:
        _opts = _ldat.get('options',{})
        if "makeport_in" in _opts:
            pnamechecked = _ldat['options']['makeport_in']['src']
            nlib_pdat = pall_dat[pnamechecked]
        else:
            nlib_pdat = {"accepted_paths":["@any"],
                         "typeget": ""
                         }
        #else: <--- nothrow
        #    raise Exception("Cant resolve port data for node {} (port {})".format(ncls,pname))

    return {
        "name": pname,
        "port_typeName": port.port_typeName if isPobj else port['type'],
        "isAutoPortNode": _isAPNode,
        "isAutoPortPrepared": nodeCtx.isAutoPortPrepared() if isPobj else _isAPNode and len(nodeCtx['custom']['autoportdata']) > 0,
        "portType": ptype,
        "node": nodeCtx if isPobj else nodeCtx,
        "nodeLibPortData": nlib_pdat,
        "nodeClass": ncls
    }

def validate_connections_serialized(portFromDict,portToDict):
    """
        Копия от validate_connections
        port[From|To]Dict = {
            "name":str (nameof port)
            "port_typeName":str - тайпнейм порта
            "isAutoPortNode" :bool
            "isAutoPortPrepared":bool
            "portType": in | out - тип порта
            'node': object or .graph nodedict values,
            'nodeLibPortData':dict - данные порта из библиотеки
            'nodeClass':str - имя класса узла
        }
    """
    from ReNode.ui.NodeGraphComponent import NodeGraphComponent

    fromTypeName = portFromDict['port_typeName']
    toTypeName = portToDict['port_typeName']

    #fromNode = fromPort.refPort.model.node
    #toNode = toPort.refPort.model.node

    #check empty typename ports
    if not fromTypeName and fromTypeName == toTypeName:
        return False

    #check start
    if fromTypeName == toTypeName:
        return True

    # check selfports
    fact = NodeGraphComponent.refObject.getFactory()
    if fromTypeName == "self" or toTypeName == "self":#todo refactor (typecheck from memdata)
        # src - left, targ - right (self)
        if portToDict["portType"]=='in' and toTypeName == "self":
            src = portFromDict
            targ = portToDict
        elif portFromDict['portType']=='in' and fromTypeName == "self":
            src = portToDict
            targ = portFromDict
        cls = fact.getNodeLibData(targ['nodeClass']).get('classInfo')
        if cls:
            baseName = cls['class']
            checked = fact.getRealType(src['port_typeName'])
            if fact.isTypeOf(checked,baseName): return True

    #dynamic set
    #if one port has data and was empty
    """
        Если один из портов автопорт и не подготовлен то
        осуществляем проверку может ли быть подключен узел к автопорту
    """
    if portFromDict['isAutoPortNode'] and not portFromDict['isAutoPortPrepared']:
        if can_connect_auto_port_serialized(fact,portFromDict,portToDict,portFromDict['nodeClass'],portFromDict['nodeLibPortData']): return True

    if portToDict['isAutoPortNode'] and not portToDict['isAutoPortPrepared']:
        if can_connect_auto_port_serialized(fact,portToDict,portFromDict,portToDict['nodeClass'],portToDict['nodeLibPortData']): return True
    
    # проверка объектов. Только даункастинг
    if fact.isObjectType(fromTypeName) and fact.isObjectType(toTypeName):
        realOutType = fact.getRealType(toTypeName if portToDict['portType'] == 'out' else fromTypeName)
        realBaseType = fact.getRealType(fromTypeName if portFromDict['portType'] == 'in' else toTypeName)
        if realBaseType != realOutType:
            if fact.isTypeOf(realOutType,realBaseType):
                return True
    
    # проверка декомпозиции типа (объектов)
    fttFrom = toTypeName if portToDict['portType'] == 'out' else fromTypeName
    tttTo = fromTypeName if portFromDict['portType'] == 'in' else toTypeName

    ftDec = fact.decomposeType(fttFrom)
    ttDec = fact.decomposeType(tttTo)

    #функция к ссылке
    if ftDec[0]=='function' and ttDec[1]=='function_ref' or \
        ftDec[1]=='function_ref' and ttDec[0]=='function': return True

    if ftDec[0]!=ttDec[0] or len(ftDec)!=len(ttDec): return False
    allt_list = []
    for ofs in range(1,len(ftDec)):
        
        realOutType = fact.getRealType(ftDec[ofs])
        realBaseType = fact.getRealType(ttDec[ofs])
        
        if not fact.isObjectType(realOutType) or not fact.isObjectType(realBaseType):
            allt_list.append(False)
            continue
        allt_list.append(fact.isTypeOf(realOutType,realBaseType))
    if allt_list and all(allt_list): return True

    return False


def can_connect_auto_port_serialized(factory,fromPort,toPort,nodeClassnameSrc,dataPort):
    """По параметрам смотреть validate_connections_serialized"""
    if fromPort["port_typeName"] != "": return False
    if toPort["port_typeName"] == "": return False
    if "Exec" in [fromPort["port_typeName"],toPort["port_typeName"]]: 
        if nodeClassnameSrc != "internal.reroute":
            return False

    #prep self port
    #TODO make smart convert from self to objecttype (array.selectMin -> self)
    toPortTPN = toPort['port_typeName']
    # if toPortTPN == 'self':
    #     cinf = factory.getNodeLibData(toPort['nodeClass']).get('classInfo')
    #     if cinf:
    #         toPortTPN = cinf['class'] + "^"

    evalType = calculate_autoport_type_serialized(factory,toPortTPN,dataPort)
    
    if evalType.startswith("ANY"):
        evalType = toPortTPN
    if evalType != toPortTPN:
        return False
    if evalType == 'self': return False

    equalDataTypes = calculate_autoport_type_serialized(factory,toPortTPN,dataPort,True)

    if not equalDataTypes:
        return False

    return True

def calculate_autoport_type_serialized(fact,sourceType:str,libCalculator:dict,chechDatatype=False):
    if not libCalculator: return sourceType

    #libCalculator['typeget'] -> @type(for all), @typeref(for typeref (array,dict etc)), @value.1, @value.2

    getterData = libCalculator['typeget']
    dataType,getter = getterData.split(';')
    isMultitype = findall('[\[\]\,]',sourceType)
    if not isMultitype:
        preSource = sourceType
        sourceType = f'{dataType}[{sourceType}]'
        if dataType == "value":
            sourceType = preSource

    typeinfo = findall('[\w\.\=\@\(\)\<\>\^]+',sourceType)
    
    if chechDatatype:
        if dataType == "ANY": return True
        if not isMultitype and dataType == 'value': return True

        return dataType == typeinfo[0]

    #check type
    acceptedType = False
    _typeValidator = sourceType
    if dataType == "ANY" and typeinfo[0] == dataType:
        _typeValidator = typeinfo[1]
    for checkedType in libCalculator.get('allowtypes',[_typeValidator]):
        if checkedType == _typeValidator:
            acceptedType = True
            break
        if checkedType == "*enum":
            if fact.isEnumType(_typeValidator):
                acceptedType = True
                break
        if checkedType == "*struct":
            if fact.isStructType(_typeValidator):
                acceptedType = True
                break
    if not acceptedType: return "!not_accepted_type"

    if getter == '@type':
        if dataType == "ANY" and typeinfo[0] == dataType:
            return typeinfo[1] #тип значения редиректится в первый элемент типа
        return sourceType
    elif getter == '@typeref':
        return typeinfo[0]
    elif getter == '@value.1' and len(typeinfo) > 1:
        return typeinfo[1]
    elif getter == '@value.2' and len(typeinfo) > 2:
        return typeinfo[2]
    else :
        raise Exception(f"Invalid type getter {getter}; Source type info {typeinfo}")