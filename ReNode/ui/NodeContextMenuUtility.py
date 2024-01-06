from Qt import QtWidgets, QtCore, QtGui

def get_real_used_nodes(graph,node):
    selNodes = graph.selected_nodes()
    if node:
        if node in selNodes:
            node = selNodes
        else:
            selNodes.append(node)
            node = selNodes
    else:
        node = selNodes
    if not node: return None
    return node

def copy_nodes(graph,node=None):
    """
    Copy nodes to the clipboard.
    """
    node = get_real_used_nodes(graph,node)
    if not node: return
    graph.copy_nodes(node)


def cut_nodes(graph,node):
    """
    Cut nodes to the clip board.
    """
    node = get_real_used_nodes(graph,node)
    if not node: return
    graph.cut_nodes(node)


def paste_nodes(graph):
    """
    Pastes nodes copied from the clipboard.
    """
    graph.paste_nodes()


def delete_nodes(graph,node=None):
    """
    Delete selected node.
    """
    node = get_real_used_nodes(graph,node)
    if not node: return
    graph.delete_nodes(node)


def extract_nodes(graph,node=None):
    """
    Extract selected nodes.
    """
    node = get_real_used_nodes(graph,node)
    if not node: return
    graph.extract_nodes(node)

def reset_all_node_props(graph,node=None):
    
    classLib = graph._factoryRef.getNodeLibData(node.nodeClass)
    if classLib:
        graph.undo_stack().beginMacro('Сброс свойств узла ' + node.nodeClass)
        for propName,propData in classLib.get("options",{}).items():
            if 'default' in propData:
                node.set_property(propName,propData['default'])
        graph.undo_stack().endMacro()

        


def clear_node_connections(graph):
    """
    Clear port connection on selected nodes.
    """
    graph.undo_stack().beginMacro('clear selected node connections')
    for node in graph.selected_nodes():
        for port in node.input_ports() + node.output_ports():
            port.clear_connections()
    graph.undo_stack().endMacro()


def select_all_nodes(graph):
    """
    Select all nodes.
    """
    graph.select_all()


def clear_node_selection(graph):
    """
    Clear node selection.
    """
    graph.clear_selection()


def invert_node_selection(graph):
    """
    Invert node selection.
    """
    graph.invert_selection()

def undo(graph):
    stack = graph._undo_stack
    if stack.canUndo():
        stack.undo()
    pass

def redo(graph):
    stack = graph._undo_stack
    if stack.canRedo():
        stack.redo()
    pass

def change_color(graph,node):
    if not node: return
    curcol = node.color()
    opts = QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog
    #opts |= QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
    color = QtWidgets.QColorDialog.getColor(
        QtGui.QColor(*curcol),
        parent=None,
        title="Выбор цвета",
        options=opts
    )
    cl = color.getRgb()
    node.set_color(cl[0],cl[1],cl[2])
    node._view.update(node._view.boundingRect())

