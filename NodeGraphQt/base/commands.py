#!/usr/bin/python
from Qt import QtWidgets

from NodeGraphQt.constants import PortTypeEnum

class UndoCommand(QtWidgets.QUndoCommand):
    def __init__(self):
        QtWidgets.QUndoCommand.__init__(self)
        self.compileInfo = None
        """Информация о компиляции. Словарь, lastResult:CompileResult"""

class PropertyChangedCmd(UndoCommand):
    """
    Node property changed command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        name (str): node property name.
        value (object): node property value.
    """

    def __init__(self, node, name, value):
        UndoCommand.__init__(self)
        self.setText('property "{}:{}"'.format(node.name(), name))
        self.node = node
        self.name = name
        self.old_val = node.get_property(name)
        self.new_val = value

    def set_node_property(self, name, value):
        """
        updates the node view and model.
        """
        # set model data.
        model = self.node.model
        model.set_property(name, value)

        # set view data.
        view = self.node.view

        # view widgets.
        if hasattr(view, 'widgets') and name in view.widgets.keys():
            # check if previous value is identical to current value,
            # prevent signals from causing a infinite loop.
            if view.widgets[name].get_value() != value:
                view.widgets[name].set_value(value)

        # view properties.
        if name in view.properties.keys():
            # remap "pos" to "xy_pos" node view has pre-existing pos method.
            if name == 'pos':
                name = 'xy_pos'
            setattr(view, name, value)

        # emit property changed signal.
        graph = self.node.graph
        graph.property_changed.emit(self.node, self.name, value)

    def undo(self):
        if self.old_val != self.new_val:
            self.set_node_property(self.name, self.old_val)

    def redo(self):
        if self.old_val != self.new_val:
            self.set_node_property(self.name, self.new_val)


class NodeVisibleCmd(UndoCommand):
    """
    Node visibility changed command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        visible (bool): node visible value.
    """

    def __init__(self, node, visible):
        UndoCommand.__init__(self)
        self.node = node
        self.visible = visible
        self.selected = self.node.selected()

    def set_node_visible(self, visible):
        model = self.node.model
        model.set_property('visible', visible)

        node_view = self.node.view
        node_view.visible = visible

        # redraw the connected pipes in the scene.
        ports = node_view.inputs + node_view.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.update()

        # restore the node selected state.
        if self.selected != node_view.isSelected():
            node_view.setSelected(model.selected)

        # emit property changed signal.
        graph = self.node.graph
        graph.property_changed.emit(self.node, 'visible', visible)

    def undo(self):
        self.set_node_visible(not self.visible)

    def redo(self):
        self.set_node_visible(self.visible)


class NodeWidgetVisibleCmd(UndoCommand):
    """
    Node widget visibility command.

    Args:
        node (NodeGraphQt.NodeObject): node object.
        name (str): node widget name.
        visible (bool): initial visibility state.
    """

    def __init__(self, node, name, visible):
        UndoCommand.__init__(self)
        label = 'show' if visible else 'hide'
        self.setText('{} node widget "{}"'.format(label, name))
        self.view = node.view
        self.node_widget = self.view.get_widget(name)
        self.visible = visible

    def undo(self):
        self.node_widget.setVisible(not self.visible)
        self.view.draw_node()

    def redo(self):
        self.node_widget.setVisible(self.visible)
        self.view.draw_node()


class NodeMovedCmd(UndoCommand):
    """
    Node moved command.

    Args:
        node (NodeGraphQt.NodeObject): node.
        pos (tuple(float, float)): new node position.
        prev_pos (tuple(float, float)): previous node position.
    """

    def __init__(self, node, pos, prev_pos):
        UndoCommand.__init__(self)
        self.node = node
        self.pos = pos
        self.prev_pos = prev_pos

    def undo(self):
        self.node.view.xy_pos = self.prev_pos
        self.node.model.pos = self.prev_pos

    def redo(self):
        if self.pos == self.prev_pos:
            return
        self.node.view.xy_pos = self.pos
        self.node.model.pos = self.pos


class NodeAddedCmd(UndoCommand):
    """
    Node added command.

    Args:
        graph (NodeGraphQt.NodeGraph): node graph.
        node (NodeGraphQt.NodeObject): node.
        pos (tuple(float, float)): initial node position (optional).
    """

    def __init__(self, graph, node, pos=None):
        UndoCommand.__init__(self)
        self.setText('added node')
        self.viewer = graph.viewer()
        self.model = graph.model
        self.node = node
        self.pos = pos

    def undo(self):
        self.pos = self.pos or self.node.pos()
        self.model.nodes.pop(self.node.id)
        self.node.view.delete()

    def redo(self):
        self.model.nodes[self.node.id] = self.node
        self.viewer.add_node(self.node.view, self.pos)

        # node width & height is calculated when it's added to the scene,
        # so we have to update the node model here.
        self.node.model.width = self.node.view.width
        self.node.model.height = self.node.view.height


class NodeRemovedCmd(UndoCommand):
    """
    Node deleted command.

    Args:
        graph (NodeGraphQt.NodeGraph): node graph.
        node (NodeGraphQt.BaseNode or NodeGraphQt.NodeObject): node.
    """

    def __init__(self, graph, node):
        UndoCommand.__init__(self)
        self.setText('deleted node')
        self.scene = graph.scene()
        self.model = graph.model
        self.node = node

    def undo(self):
        self.model.nodes[self.node.id] = self.node
        self.scene.addItem(self.node.view)

    def redo(self):
        self.model.nodes.pop(self.node.id)
        self.node.view.delete()


class NodeInputConnectedCmd(UndoCommand):
    """
    "BaseNode.on_input_connected()" command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
    """

    def __init__(self, src_port, trg_port):
        UndoCommand.__init__(self)
        if src_port.type_() == PortTypeEnum.IN.value:
            self.source = src_port
            self.target = trg_port
        else:
            self.source = trg_port
            self.target = src_port

    def undo(self):
        node = self.source.node()
        node.on_input_disconnected(self.source, self.target)

    def redo(self):
        node = self.source.node()
        node.on_input_connected(self.source, self.target)


class NodeInputDisconnectedCmd(UndoCommand):
    """
    Node "on_input_disconnected()" command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
    """

    def __init__(self, src_port, trg_port):
        UndoCommand.__init__(self)
        if src_port.type_() == PortTypeEnum.IN.value:
            self.source = src_port
            self.target = trg_port
        else:
            self.source = trg_port
            self.target = src_port

    def undo(self):
        node = self.source.node()
        node.on_input_connected(self.source, self.target)

    def redo(self):
        node = self.source.node()
        node.on_input_disconnected(self.source, self.target)


class PortConnectedCmd(UndoCommand):
    """
    Port connected command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
    """

    def __init__(self, src_port, trg_port):
        UndoCommand.__init__(self)
        self.source = src_port
        self.target = trg_port

    def undo(self):
        src_model = self.source.model
        trg_model = self.target.model
        src_id = self.source.node().id
        trg_id = self.target.node().id

        port_names = src_model.connected_ports.get(trg_id)
        if port_names is []:
            del src_model.connected_ports[trg_id]
        if port_names and self.target.name() in port_names:
            port_names.remove(self.target.name())

        port_names = trg_model.connected_ports.get(src_id)
        if port_names is []:
            del trg_model.connected_ports[src_id]
        if port_names and self.source.name() in port_names:
            port_names.remove(self.source.name())

        self.source.view.disconnect_from(self.target.view)

    def redo(self):
        src_model = self.source.model
        trg_model = self.target.model
        src_id = self.source.node().id
        trg_id = self.target.node().id

        src_model.connected_ports[trg_id].append(self.target.name())
        trg_model.connected_ports[src_id].append(self.source.name())

        self.source.view.connect_to(self.target.view)


class PortDisconnectedCmd(UndoCommand):
    """
    Port disconnected command.

    Args:
        src_port (NodeGraphQt.Port): source port.
        trg_port (NodeGraphQt.Port): target port.
    """

    def __init__(self, src_port, trg_port):
        UndoCommand.__init__(self)
        self.source = src_port
        self.target = trg_port

    def undo(self):
        src_model = self.source.model
        trg_model = self.target.model
        src_id = self.source.node().id
        trg_id = self.target.node().id

        src_model.connected_ports[trg_id].append(self.target.name())
        trg_model.connected_ports[src_id].append(self.source.name())

        self.source.view.connect_to(self.target.view)

    def redo(self):
        src_model = self.source.model
        trg_model = self.target.model
        src_id = self.source.node().id
        trg_id = self.target.node().id

        port_names = src_model.connected_ports.get(trg_id)
        if port_names is []:
            del src_model.connected_ports[trg_id]
        if port_names and self.target.name() in port_names:
            port_names.remove(self.target.name())

        port_names = trg_model.connected_ports.get(src_id)
        if port_names is []:
            del trg_model.connected_ports[src_id]
        if port_names and self.source.name() in port_names:
            port_names.remove(self.source.name())

        self.source.view.disconnect_from(self.target.view)


class PortLockedCmd(UndoCommand):
    """
    Port locked command.

    Args:
        port (NodeGraphQt.Port): node port.
    """

    def __init__(self, port):
        UndoCommand.__init__(self)
        self.setText('lock port "{}"'.format(port.name()))
        self.port = port

    def undo(self):
        self.port.model.locked = False
        self.port.view.locked = False

    def redo(self):
        self.port.model.locked = True
        self.port.view.locked = True


class PortUnlockedCmd(UndoCommand):
    """
    Port unlocked command.

    Args:
        port (NodeGraphQt.Port): node port.
    """

    def __init__(self, port):
        UndoCommand.__init__(self)
        self.setText('unlock port "{}"'.format(port.name()))
        self.port = port

    def undo(self):
        self.port.model.locked = True
        self.port.view.locked = True

    def redo(self):
        self.port.model.locked = False
        self.port.view.locked = False


class PortVisibleCmd(UndoCommand):
    """
    Port visibility command.

    Args:
        port (NodeGraphQt.Port): node port.
    """

    def __init__(self, port, visible):
        UndoCommand.__init__(self)
        self.port = port
        self.visible = visible
        if visible:
            self.setText('show port {}'.format(self.port.name()))
        else:
            self.setText('hide port {}'.format(self.port.name()))

    def set_visible(self, visible):
        self.port.model.visible = visible
        self.port.view.setVisible(visible)
        node_view = self.port.node().view
        text_item = None
        if self.port.type_() == PortTypeEnum.IN.value:
            text_item = node_view.get_input_text_item(self.port.view)
        elif self.port.type_() == PortTypeEnum.OUT.value:
            text_item = node_view.get_output_text_item(self.port.view)
        if text_item:
            text_item.setVisible(visible)

        node_view.draw_node()

        # redraw the connected pipes in the scene.
        ports = node_view.inputs + node_view.outputs
        for port in node_view.inputs + node_view.outputs:
            for pipe in port.connected_pipes:
                pipe.update()

    def undo(self):
        self.set_visible(not self.visible)
        
    def redo(self):
        self.set_visible(self.visible)

# ========================= custom commands ===========================

class VariableCreatedCommand(UndoCommand):
    def __init__(self, varmgr, cat,variable,varId):
        super(VariableCreatedCommand, self).__init__()
        self.setText('Создание переменной "{}"'.format(variable['name']))
        self._variable = variable
        self._category = cat
        self._varmgr = varmgr
        self._varId = varId

    def undo(self):
        self._varmgr.variables[self._category].pop(self._varId)
        self._varmgr.syncVariableManagerWidget()
    
    def redo(self):
        self._varmgr.variables[self._category][self._varId] = self._variable
        self._varmgr.syncVariableManagerWidget()

class VariableDeletedCommand(UndoCommand):
    def __init__(self, varmgr, cat,varId):
        super(VariableDeletedCommand, self).__init__()
        variable = varmgr.variables[cat][varId]
        self.setText('Удаление переменной "{}"'.format(variable['name']))
        self._variable = variable
        self._category = cat
        self._varmgr = varmgr
        self._varId = varId

    def undo(self):
        self._varmgr.variables[self._category][self._varId] = self._variable
        self._varmgr.syncVariableManagerWidget()
    
    def redo(self):
        self._varmgr.variables[self._category].pop(self._varId)
        self._varmgr.syncVariableManagerWidget()

class VariableChangePropertyCommand(UndoCommand):

    blockedProps = set(["systemname","reprType","reprDataType"])

    def __init__(self, varmgr, cat,varId,prop,value,defaultvalue):
        super(VariableChangePropertyCommand, self).__init__()

        if prop in VariableChangePropertyCommand.blockedProps:
            raise Exception(f"Property {prop} is blocked for change")

        self._varStorage = varmgr.variables[cat][varId]
        self.setText('Изменение свойств переменной "{}"'.format(self._varStorage['name']))
        self._varmgr = varmgr
        self._name = prop
        self._value = value
        self._oldvaule = self._varStorage.get(self._name,defaultvalue)
    
    def undo(self):
        self._varStorage[self._name] = self._oldvaule
        self._varmgr.syncVariableManagerWidget()

    def redo(self):
        self._varStorage[self._name] = self._value
        self._varmgr.syncVariableManagerWidget()

class ChangeGroupNameForVariables(UndoCommand):
    def __init__(self,varmgr,cat,oldgroup,newgroup):
        super(ChangeGroupNameForVariables, self).__init__()
        self.setText('Изменение имени группы переменных "{}" на "{}"'.format(oldgroup,newgroup))
        self._varmgr = varmgr
        self._category = cat
        self._oldgroup = oldgroup
        self._newgroup = newgroup
        vdatvals = self._varmgr.variables[self._category].items()
        self._changedvarsId = set([varId for varId,vardat in vdatvals if vardat.get('group',None) == oldgroup])
    
    def undo(self):
        for sysname,vardat in self._varmgr.variables[self._category].items():
            if sysname in self._changedvarsId:
                if self._oldgroup:
                    vardat['group'] = self._oldgroup
                else:
                    vardat.pop('group')
        self._varmgr.syncVariableManagerWidget()

    def redo(self):
        for sysname,vardat in self._varmgr.variables[self._category].items():
            if sysname in self._changedvarsId:
                if self._newgroup:
                    vardat['group'] = self._newgroup
                else:
                    vardat.pop('group')
        self._varmgr.syncVariableManagerWidget()

class DeleteGroupForVariables(UndoCommand):
    def __init__(self,varmgr,cat,group):
        super(DeleteGroupForVariables, self).__init__()
        self.setText('Удаление группы переменных "{}"'.format(group))
        self._varmgr = varmgr
        self._category = cat
        self._group = group
        vdatvals = self._varmgr.variables[self._category].items()
        self._changedvarsId = set([varid for varid,vardat in vdatvals if vardat.get('group',None) == group])
        self._variableData = {sysname:vardat for sysname,vardat in self._varmgr.variables[self._category].items() if sysname in self._changedvarsId}
    
    def deleteVariableInGraph(self):
        graph = self._varmgr.nodeGraphComponent.graph
        allNodes = graph.get_nodes_by_class(None)

        #Удаляем ноды с графа
        for node in allNodes:
            if node.has_property("nameid"):
                if node.get_property("nameid") in self._changedvarsId:
                    graph.delete_node(node,True)

    def undo(self):
        varstorage = self._varmgr.variables[self._category]
        graph = self._varmgr.nodeGraphComponent.graph
        
        #Возвращаем в хранилище удаленные переменные
        for sysname,vardat in self._variableData.items():
                varstorage[sysname] = vardat

        self._varmgr.syncVariableManagerWidget()

    def redo(self):
        varstorage = self._varmgr.variables[self._category]
        for sysname,dat in self._variableData.items():
            del varstorage[sysname]
        
        self._varmgr.syncVariableManagerWidget()


# для view модели
class __PropertyCommand(UndoCommand):
    def getPropertyTextName(self):
        pObj = self.propertyInspectorRef.getPropNameView(self.cat,self.sysname)
        if pObj:
            return pObj.property("defaultName")
        else:
            return self.sysname

class ChangeInspectorPropertyCommand(__PropertyCommand):
    def __init__(self,refPropInsp,props,cat,sysname,value):
        super(ChangeInspectorPropertyCommand, self).__init__()
        self.propertyInspectorRef = refPropInsp
        self.propsRef = props
        self.cat = cat
        self.sysname = sysname
        self.value = value
        self.oldvalue = props[cat].get(sysname,None)
        self.setText('Изменение свойства "{}"'.format(self.getPropertyTextName()))
        
    
    def undo(self):
        oldVal = self.oldvalue
        if oldVal:
            self.propsRef[self.cat][self.sysname] = oldVal
        else:
            del self.propsRef[self.cat][self.sysname]
        self.propertyInspectorRef.syncPropValue(self.cat,self.sysname,True)

    def redo(self):
        self.propsRef[self.cat][self.sysname] = self.value
        self.propertyInspectorRef.syncPropValue(self.cat,self.sysname,True)

class ResetToDefaultInspectorPropertyCommand(__PropertyCommand):
    def __init__(self,refPropInsp,props,cat,sysname):
        super(ResetToDefaultInspectorPropertyCommand, self).__init__()
        self.propertyInspectorRef = refPropInsp
        self.propsRef = props
        self.cat = cat
        self.sysname = sysname
        self.oldvalue = props[cat].get(sysname,None)
        self.setText('Сброс свойства "{}"'.format(self.getPropertyTextName()))
        
    
    def undo(self):
        oldVal = self.oldvalue
        
        self.propsRef[self.cat][self.sysname] = oldVal
        self.propertyInspectorRef.syncPropValue(self.cat,self.sysname,True)

    def redo(self):
        del self.propsRef[self.cat][self.sysname]
        self.propertyInspectorRef.syncPropValue(self.cat,self.sysname,True)