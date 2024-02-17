#!/usr/bin/python
from collections import OrderedDict

from Qt import QtGui, QtCore, QtWidgets

from NodeGraphQt.constants import (
    ITEM_CACHE_MODE,
    ICON_NODE_BASE,
    LayoutDirectionEnum,
    NodeEnum,
    PortEnum,
    PortTypeEnum,
    Z_VAL_NODE
)
from NodeGraphQt.errors import NodeWidgetError
from NodeGraphQt.qgraphics.node_abstract import AbstractNodeItem
from NodeGraphQt.qgraphics.node_overlay_disabled import XDisabledItem,XErrorItem
from NodeGraphQt.qgraphics.node_text_item import NodeTextItem
from NodeGraphQt.qgraphics.port import PortItem, CustomPortItem, ScriptedCustomPortItem

from PyQt5.QtCore import QPropertyAnimation, QRectF
from PyQt5.QtWidgets import QGraphicsItem, QWidget

from ReNode.app.utils import updatePixmapColor, mergePixmaps
from ReNode.ui.NodePainter import getDrawPortStyleId
from ReNode.app.Constants import NodeRenderType
#! use this for animated node
# class AnimatedItem(QGraphicsItem):
#     def __init__(self):
#         super().__init__()
#         self.rect = self.boundingRect()
#         self.color = Qt.red
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.animate)
#         self.timer.start(1000)  # Change color every second

#     def boundingRect(self):
#         return self.rect

#     def paint(self, painter, option, widget):
#         painter.fillRect(self.rect, self.color)

#     def animate(self):
#         # Toggle between red and blue
#         if self.color == Qt.red:
#             self.color = Qt.blue
#         else:
#             self.color = Qt.red
#         self.update()  # Redraw the item

class NodeItem(AbstractNodeItem):
    """
    Base Node item.

    Args:
        name (str): name displayed on the node.
        parent (QtWidgets.QGraphicsItem): parent item.
    """
    constRefNodeGraph = None
    @staticmethod
    def loadConstRefNodeGraph():
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        NodeItem.constRefNodeGraph = NodeGraphComponent.refObject
    @staticmethod
    def getFactory(): return NodeItem.constRefNodeGraph.getFactory()

    def __init__(self, name='node', parent=None):
        super(NodeItem, self).__init__(name, parent)
        pixmap = QtGui.QPixmap(ICON_NODE_BASE)
        if pixmap.size().height() > NodeEnum.ICON_SIZE.value:
            pixmap = pixmap.scaledToHeight(
                NodeEnum.ICON_SIZE.value,
                QtCore.Qt.SmoothTransformation
            )
        self._properties['icon'] = ICON_NODE_BASE
        self._icon_item = QtWidgets.QGraphicsPixmapItem(pixmap, self)
        self._icon_item.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self._text_item = NodeTextItem(self.name, self)
        self._x_item = XDisabledItem(self, 'DISABLED')
        self._input_items = OrderedDict()
        self._output_items = OrderedDict()
        self._widgets = OrderedDict()
        self._proxy_mode = False
        self._proxy_mode_threshold = 70

        self._error_item = XErrorItem(self,"ОШИБКА","")

        if not NodeItem.constRefNodeGraph:
            NodeItem.loadConstRefNodeGraph()

        # тип рендера узла
        self._node_render_type = NodeRenderType.Default
        self._default_font_size = 11 #размер текста по умолчанию. требует перерендера при изменении

        # Tuple of (port,widget, sizeH)
        self._tupleWidgetData : list[tuple] = None

        self._blinkNode = False #true для мигания объекта
        self._blinkTimer = 0
        self._blinkTimeLeft = 0

    def doBlink(self,outIndex=-1):
        self._blinkNode = True
        self._blinkTimer = 0
        self._blinkTimeLeft = 1.5 * 1000
        pipe = self.get_output_pipe_to_node(outIndex)
        if pipe:
            pipe._blinkNode = True
            pipe._blinkTimer = 0
            pipe._blinkTimeLeft = 1.5 * 1000

    def setErrorText(self,text="",header="ОШИБКА"):
        self._error_item.setVisible(True)
        if not header: header = "ОШИБКА"
        self._error_item.desc = text
        self._error_item.text = header

        self.draw_node()
        pass

    def addErrorText(self,text="",header="ОШИБКА"):
        if not text: return
        oldText = self._error_item.desc
        if oldText:
            oldText += "\n"
        self.setErrorText(oldText+text,header)

    def resetError(self):
        self._error_item.desc = ""
        self._error_item.text = ""
        self._error_item.setVisible(False)

    def post_init(self, viewer, pos=None):
        """
        Called after node has been added into the scene.

        Args:
            viewer (NodeGraphQt.widgets.viewer.NodeViewer): main viewer
            pos (tuple): the cursor pos if node is called with tab search.
        """
        if self.layout_direction == LayoutDirectionEnum.VERTICAL.value:
            font = QtGui.QFont()
            font.setPointSize(15)
            self.text_item.setFont(font)

            # hide port text items for vertical layout.
            if self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
                for text_item in self._input_items.values():
                    text_item.setVisible(False)
                for text_item in self._output_items.values():
                    text_item.setVisible(False)

    def _paint_horizontal(self, painter, option, widget):
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        # base background.
        margin = 1.0
        rect = self.boundingRect()
        rect = QtCore.QRectF(rect.left() + margin,
                             rect.top() + margin,
                             rect.width() - (margin * 2),
                             rect.height() - (margin * 2))

        radius = 4.0
        #painter.setBrush(QtGui.QColor(*self.color))
        painter.setBrush(QtGui.QColor(20, 20, 20, 240))
        painter.drawRoundedRect(rect, radius, radius)

        if self._blinkNode:
            btm = self._blinkTimer
            allvals = 100+btm*30%250
            painter.setBrush(QtGui.QColor(40,100+btm*30%250,40,100))
            rectBlink = QtCore.QRectF(rect)
            blinkSize = btm * 20
            rectBlink.adjust(-blinkSize*2,-blinkSize*2,blinkSize,blinkSize)
            painter.drawRoundedRect(rectBlink,10,10)

        # light overlay on background when selected.
        # if self.selected:
        #     painter.setBrush(QtGui.QColor(*NodeEnum.SELECTED_COLOR.value))
        #     painter.drawRoundedRect(rect, radius, radius)

        # node name background.
        padding = 1.0,0.0 #3.0, 2.0
        text_rect = self._text_item.boundingRect()
        text_rect = QtCore.QRectF(text_rect.x() + padding[0],
                                  rect.y() + padding[1],
                                  rect.width() - padding[0] - margin,
                                  text_rect.height() - (padding[1] * 2))
        # if self.selected:
        #     painter.setBrush(QtGui.QColor(*NodeEnum.SELECTED_COLOR.value))
        # else:
        #     painter.setBrush(QtGui.QColor(0, 0, 0, 80))
        # painter.drawRoundedRect(text_rect, 3.0, 3.0)

        #p1 = QtCore.QPointF(text_rect.left(), text_rect.height()/2)
        #p2 = QtCore.QPointF(text_rect.right(), text_rect.height())
        if self._node_render_type in NodeRenderType.getNoHeaderTypes():
            # gradMain = QtGui.QRadialGradient(rect.center(), rect.width() / 2, rect.center())
            # gradMain.setSpread(QtGui.QGradient.PadSpread)
            # gradMain.setColorAt(0.0, QtGui.QColor(*self.color))
            # gradMain.setColorAt(0.8, QtGui.QColor(20, 20, 20, 0))
            # painter.setBrush(QtGui.QBrush(gradMain))
            # #elrect = QtCore.QRectF(rect.top()-4,rect.left()-4,rect.width()-4,rect.height()-4)
            # painter.drawEllipse(rect)
            #todo use focalPoint

            pass

        else:
            icnPad = self._icon_item.boundingRect().width() * 4
            p1 = QtCore.QPointF(text_rect.topLeft().x() + icnPad, text_rect.topLeft().y())
            p2 = text_rect.bottomRight()
            gradMain = QtGui.QLinearGradient(p1,p2)
            gradMain.setSpread(QtGui.QGradient.Spread.ReflectSpread)
            gradMain.setColorAt(0.0, QtGui.QColor(*self.color))
            gradMain.setColorAt(1, QtGui.QColor(20, 20, 20, 0))
            painter.setBrush(QtGui.QBrush(gradMain))
            painter.drawRoundedRect(text_rect, radius, radius)

        # node border
        if self.selected:
            border_width = 1.2
            border_color = QtGui.QColor(
                *NodeEnum.SELECTED_BORDER_COLOR.value
            )
        else:
            border_width = 1.2 #0.8
            border_color = QtGui.QColor(*self.border_color)

        border_rect = QtCore.QRectF(rect.left(), rect.top(),
                                    rect.width(), rect.height())

        pen = QtGui.QPen(border_color, border_width)
        pen.setCosmetic(self.viewer().get_zoom() < 0.0)
        path = QtGui.QPainterPath()
        path.addRoundedRect(border_rect, radius, radius)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # -----------------------------------------------------------------------------------------
        #! debug draw items
        # pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 80), 0.8)
        # pen.setStyle(QtCore.Qt.DotLine)
        # painter.setPen(pen)
        # #draw widgets
        # for wid in self._widgets.values():
        #     painter.drawRect(QRectF(wid.x(), wid.y(), wid.rect().width(), wid.rect().height()))

        # pen = QtGui.QPen(QtGui.QColor(255, 0, 0, 80), 0.8)
        # pen.setStyle(QtCore.Qt.DotLine)
        # painter.setPen(pen)
        # for prt,text in self._input_items.items():
        #     painter.drawRect(QRectF(text.pos().x(), text.pos().y(), text.boundingRect().width(), text.boundingRect().height()))
        #     painter.drawRect(QRectF(prt.x(), prt.y(), prt.boundingRect().width(), prt.boundingRect().height()))

        # for prt,text in self._output_items.items():
        #     painter.drawRect(QRectF(text.pos().x(), text.pos().y(), text.boundingRect().width(), text.boundingRect().height()))
        #     painter.drawRect(QRectF(prt.x(), prt.y(), prt.boundingRect().width(), prt.boundingRect().height()))
        #!end debug

        painter.restore()

    def _paint_vertical(self, painter, option, widget):
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        # base background.
        margin = 1.0
        rect = self.boundingRect()
        rect = QtCore.QRectF(rect.left() + margin,
                             rect.top() + margin,
                             rect.width() - (margin * 2),
                             rect.height() - (margin * 2))

        radius = 4.0
        painter.setBrush(QtGui.QColor(*self.color))
        painter.drawRoundedRect(rect, radius, radius)

        # light overlay on background when selected.
        if self.selected:
            painter.setBrush(
                QtGui.QColor(*NodeEnum.SELECTED_COLOR.value)
            )
            painter.drawRoundedRect(rect, radius, radius)

        # top & bottom edge background.
        padding = 2.0
        height = 10
        if self.selected:
            painter.setBrush(QtGui.QColor(*NodeEnum.SELECTED_COLOR.value))
        else:
            painter.setBrush(QtGui.QColor(0, 0, 0, 80))
        for y in [rect.y() + padding, rect.height() - height - 1]:
            edge_rect = QtCore.QRectF(rect.x() + padding, y,
                                     rect.width() - (padding * 2), height)
            painter.drawRoundedRect(edge_rect, 3.0, 3.0)

        # node border
        border_width = 0.8
        border_color = QtGui.QColor(*self.border_color)
        if self.selected:
            border_width = 1.2
            border_color = QtGui.QColor(
                *NodeEnum.SELECTED_BORDER_COLOR.value
            )
        border_rect = QtCore.QRectF(rect.left(), rect.top(),
                                    rect.width(), rect.height())

        pen = QtGui.QPen(border_color, border_width)
        pen.setCosmetic(self.viewer().get_zoom() < 0.0)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(pen)
        painter.drawRoundedRect(border_rect, radius, radius)

        painter.restore()

    def paint(self, painter, option, widget):
        """
        Draws the node base not the ports.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        self.auto_switch_mode()
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._paint_horizontal(painter, option, widget)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._paint_vertical(painter, option, widget)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def mousePressEvent(self, event):
        """
        Re-implemented to ignore event if LMB is over port collision area.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.button() == QtCore.Qt.LeftButton:
            for p in self._input_items.keys():
                if p.hovered:
                    event.ignore()
                    return
            for p in self._output_items.keys():
                if p.hovered:
                    event.ignore()
                    return
        super(NodeItem, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Re-implemented to ignore event if Alt modifier is pressed.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.modifiers() == QtCore.Qt.AltModifier:
            event.ignore()
            return
        super(NodeItem, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """
        Re-implemented to emit "node_double_clicked" signal.

        Args:
            event (QtWidgets.QGraphicsSceneMouseEvent): mouse event.
        """
        if event.button() == QtCore.Qt.LeftButton:
            if not self.disabled:
                # enable text item edit mode.
                items = self.scene().items(event.scenePos())
                if self._text_item in items:
                    self._text_item.set_editable(True)
                    self._text_item.setFocus()
                    event.ignore()
                    return

            viewer = self.viewer()
            if viewer:
                viewer.node_double_clicked.emit(self.id)
        super(NodeItem, self).mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        """
        Re-implemented to update pipes on selection changed.

        Args:
            change:
            value:
        """
        if change == self.ItemSelectedChange and self.scene():
            self.reset_pipes()
            if value:
                self.highlight_pipes()
            self.setZValue(Z_VAL_NODE)
            if not self.selected:
                self.setZValue(Z_VAL_NODE + 1)

        return super(NodeItem, self).itemChange(change, value)

    def _tooltip_disable(self, state):
        """
        Updates the node tooltip when the node is enabled/disabled.

        Args:
            state (bool): node disable state.
        """
        tooltip = '<b>{}</b>'.format(self.name)
        if state:
            tooltip += ' <font color="red"><b>(DISABLED)</b></font>'
        tooltip += '<br/>{}<br/>'.format(self.type_)
        self.setToolTip(tooltip)
        self.setToolTip("") #Yodes: disabled tooltip for node (also we can use custom ttp)

    def _set_base_size(self, add_w=0.0, add_h=0.0):
        """
        Sets the initial base size for the node.

        Args:
            add_w (float): add additional width.
            add_h (float): add additional height.
        """
        self._width, self._height = self.calc_size(add_w, add_h)
        if self._width < NodeEnum.WIDTH.value:
            self._width = NodeEnum.WIDTH.value
        if self._height < NodeEnum.HEIGHT.value:
            self._height = NodeEnum.HEIGHT.value
        if self._node_render_type == NodeRenderType.Reroute:
            self._height = 10
            self._width = 30

    def _set_text_color(self, color):
        """
        set text color.

        Args:
            color (tuple): color value in (r, g, b, a).
        """
        text_color = QtGui.QColor(*color)
        for port, text in self._input_items.items():
            text.setDefaultTextColor(text_color)
        for port, text in self._output_items.items():
            text.setDefaultTextColor(text_color)
        self._text_item.setDefaultTextColor(text_color)

    def activate_pipes(self):
        """
        active pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.activate()

    def get_outputs_pipes(self):
        alldat = []
        for port in self.outputs:
            for pipe in port.connected_pipes:
                alldat.append(pipe)
        return alldat
    
    def get_output_pipe_to_node(self,_id):
        if _id < 0: return None
        if _id >= len(self.outputs): return None
        srcPort = self.outputs[_id]
        for pipe in srcPort.connected_pipes:
            if pipe._output_port == srcPort:
                return pipe
        return None

    def highlight_pipes(self):
        """
        Highlight pipe color.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.highlight()

    def reset_pipes(self):
        """
        Reset all the pipe colors.
        """
        ports = self.inputs + self.outputs
        for port in ports:
            for pipe in port.connected_pipes:
                pipe.reset()

    
    def _calc_size_horizontal_temp(self):
        # Считаем ширину шапки
        tbr = self._text_item.boundingRect()
        _headTextWidth, _headTextHeight = tbr.width(), tbr.height()
        if self._node_render_type in NodeRenderType.getNoHeaderTypes():
            _headTextHeight = 0
        
        # Считаем ширину входных и выходных портов
        _portWidth = 0
        _portInputTextMaxWidht = 0
        _portInputHeight = 0
        for port, text in self._input_items.items():
            if not port.isVisible(): continue
            if not _portWidth: portWidth = port.boundingRect().width()
            _ptexWidth = text.boundingRect().width()
            if text.isVisible() and _ptexWidth > _portInputTextMaxWidht:
                _portInputTextMaxWidht = _ptexWidth
            _portInputHeight += port.boundingRect().height()


        return 10, 10


    def _calc_size_horizontal(self):
        # width, height from node name text.
        text_w = self._text_item.boundingRect().width()
        text_h = self._text_item.boundingRect().height()
        if self._node_render_type in NodeRenderType.getNoHeaderTypes():
            #text_w = 0
            text_h = 0

        # width, height from node ports.
        port_width = 0.0
        p_input_text_width = 0.0
        p_output_text_width = 0.0
        p_input_height = 0.0
        p_output_height = 0.0
        for port, text in self._input_items.items():
            if not port.isVisible():
                continue
            if not port_width:
                port_width = port.boundingRect().width()
            t_width = text.boundingRect().width()
            if text.isVisible() and t_width > p_input_text_width:
                p_input_text_width = text.boundingRect().width()
            p_input_height += port.boundingRect().height()
        for port, text in self._output_items.items():
            if not port.isVisible():
                continue
            if not port_width:
                port_width = port.boundingRect().width()
            t_width = text.boundingRect().width()
            if text.isVisible() and t_width > p_output_text_width:
                p_output_text_width = text.boundingRect().width()
            p_output_height += port.boundingRect().height()

        port_text_width = p_input_text_width + p_output_text_width

        # width, height from node embedded widgets.
        widget_width = 0.0
        widget_height = 0.0
        for widget in self._widgets.values():
            #if not widget.isVisible(): #collect all widgets because proxy mode...
            #    continue
            w_width = widget.boundingRect().width()
            w_height = widget.boundingRect().height()
            if w_width > widget_width:
                widget_width = w_width
            widget_height += w_height

        side_padding = 0.0
        if all([widget_width, p_input_text_width, p_output_text_width]):
            port_text_width = max([p_input_text_width, p_output_text_width])
            port_text_width *= 2
        elif widget_width:
            side_padding = 10

        #Yodes: custom code
        #calc maxheight for custom system
        p_amountHeightOpt = 0.0
        for prt,wid,sizeH in self._tupleWidgetData:
            accum = 0
            if prt:
                accum += 1 # because exists _align_ports_horizontal -> spacing = 1
            p_amountHeightOpt += accum + sizeH

        width = port_width + max([text_w, widget_width]) + side_padding #!prev code: max([text_w, port_text_width])
        height = max([text_h, p_input_height, p_output_height, widget_height , p_amountHeightOpt])
        if widget_width:
            # add additional width for node widget.
            #width += widget_width - p_output_text_width #!old code
            width += p_output_text_width
            pass
        if widget_height:
            # add bottom margin for node widget.
            if self._node_render_type not in NodeRenderType.getNoHeaderTypes():
                height += 4.0
        height *= 1.05
        return width, height

    def _calc_size_vertical(self):
        p_input_width = 0.0
        p_output_width = 0.0
        p_input_height = 0.0
        p_output_height = 0.0
        for port in self._input_items.keys():
            if port.isVisible():
                p_input_width += port.boundingRect().width()
                if not p_input_height:
                    p_input_height = port.boundingRect().height()
        for port in self._output_items.keys():
            if port.isVisible():
                p_output_width += port.boundingRect().width()
                if not p_output_height:
                    p_output_height = port.boundingRect().height()

        widget_width = 0.0
        widget_height = 0.0
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            if widget.boundingRect().width() > widget_width:
                widget_width = widget.boundingRect().width()
            widget_height += widget.boundingRect().height()

        width = max([p_input_width, p_output_width, widget_width])
        height = p_input_height + p_output_height + widget_height
        return width, height

    def calc_size(self, add_w=0.0, add_h=0.0):
        """
        Calculates the minimum node size.

        Args:
            add_w (float): additional width.
            add_h (float): additional height.

        Returns:
            tuple(float, float): width, height.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            width, height = self._calc_size_horizontal()
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            width, height = self._calc_size_vertical()
        else:
            raise RuntimeError('Node graph layout direction not valid!')

        # additional width, height.
        width += add_w
        height += add_h
        return width, height

    def _align_icon_horizontal(self, h_offset, v_offset):
        if self._node_render_type == NodeRenderType.NoHeader:
            scale = NodeEnum.ICON_CUSTOM_RENDER_SIZE.value
            pix = self._icon_item.pixmap()
            if pix.size().height() < scale:
                pix = pix.scaledToHeight(scale, QtCore.Qt.SmoothTransformation)
                self._icon_item.setPixmap(pix)
                self._icon_item.setOpacity(0.5)
            origRect = self.boundingRect()
            icnRect = self._icon_item.boundingRect()
            self._icon_item.setPos(origRect.center().x()-icnRect.width()/2,origRect.center().y()-icnRect.height()/2)
            return
        if self._node_render_type == NodeRenderType.NoHeaderIcon:
            scale = NodeEnum.ICON_CUSTOM_RENDER_SIZE.value
            pix = self._icon_item.pixmap()
            if pix.size().height() < scale:
                pix = pix.scaledToHeight(scale, QtCore.Qt.SmoothTransformation)
                self._icon_item.setPixmap(pix)
                self._icon_item.setOpacity(0.5)
            origRect = self.boundingRect()
            icnRect = self._icon_item.boundingRect()
            self._icon_item.setPos(origRect.center().x()-icnRect.width()/2,origRect.center().y()-icnRect.height()/2)
            return
        if self._node_render_type == NodeRenderType.NoHeaderText:
            self._icon_item.setOpacity(0.0)
            return
        icon_rect = self._icon_item.boundingRect()
        text_rect = self._text_item.boundingRect()
        x = self.boundingRect().left() + 2.0
        y = text_rect.center().y() - (icon_rect.height() / 2)
        self._icon_item.setPos(x + h_offset, y + v_offset)

    def _align_icon_vertical(self, h_offset, v_offset):
        center_y = self.boundingRect().center().y()
        icon_rect = self._icon_item.boundingRect()
        text_rect = self._text_item.boundingRect()
        x = self.boundingRect().right() + h_offset
        y = center_y - text_rect.height() - (icon_rect.height() / 2) + v_offset
        self._icon_item.setPos(x, y)

    def align_icon(self, h_offset=0.0, v_offset=0.0):
        """
        Align node icon to the default top left of the node.

        Args:
            v_offset (float): additional vertical offset.
            h_offset (float): additional horizontal offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_icon_horizontal(h_offset, v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_icon_vertical(h_offset, v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _align_label_horizontal(self, h_offset, v_offset):
        if self._node_render_type == NodeRenderType.NoHeader:
            text_rect = self._text_item.boundingRect()
            x = self.boundingRect().center().x() - (text_rect.width() / 2)
            y = self.boundingRect().center().y() - (text_rect.height() / 2)
            self._text_item.setOpacity(0.6)
            self._text_item.setPos(x + h_offset, y + v_offset)
            return
        if self._node_render_type == NodeRenderType.NoHeaderText:
            #draw text at center
            text_rect = self._text_item.boundingRect()
            x = self.boundingRect().center().x() - (text_rect.width() / 2)
            y = self.boundingRect().center().y() - (text_rect.height() / 2)
            self._text_item.setOpacity(0.5)
            self._text_item.setPos(x + h_offset, y + v_offset)
            return
        if self._node_render_type == NodeRenderType.NoHeaderIcon:
            self._text_item.setOpacity(0.0)
            return
        rect = self.boundingRect()
        text_rect = self._text_item.boundingRect()
        #x = rect.center().x() - (text_rect.width() / 2) #Yodes: here we can setup left offest
        icon_rect = self._icon_item.boundingRect()
        #v0.3
        #x = rect.center().x() - (text_rect.width() - icon_rect.width()) #customized value
        x = rect.left() + icon_rect.width() #* 1.3 #Yodes: fixed rect 
        #end custom
        self._text_item.setPos(x + h_offset, rect.y() + v_offset)

    def _align_label_vertical(self, h_offset, v_offset):
        rect = self._text_item.boundingRect()
        x = self.boundingRect().right() + h_offset
        y = self.boundingRect().center().y() - (rect.height() / 2) + v_offset
        self.text_item.setPos(x, y)

    def align_label(self, h_offset=0.0, v_offset=0.0):
        """
        Center node label text to the top of the node.

        Args:
            v_offset (float): vertical offset.
            h_offset (float): horizontal offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_label_horizontal(h_offset, v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_label_vertical(h_offset, v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _align_widgets_horizontal(self, v_offset):
        if not self._widgets:
            return
        rect = self.boundingRect()
        spacing = 1
        y = rect.y() + v_offset
        inputs = [p for p in self.inputs if p.isVisible()]
        inpDict = {p.name:p for p in inputs}
        outputs = [p for p in self.outputs if p.isVisible()]
        for prt,widget,height in self._tupleWidgetData: #self._widgets.items():
            if not widget:
                if prt:
                    y += spacing
                y += height
                continue
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            if widget._name in inpDict:
                x = rect.left() + 10 #inpDict[widget._name].boundingRect().width()/2
                widget.widget().setTitleAlign('left')
            elif not inputs:
                x = rect.left() + 10
                widget.widget().setTitleAlign('left')
            elif not outputs:
                x = rect.right() - widget_rect.width() - 10
                widget.widget().setTitleAlign('right')
            else:
                x = rect.center().x() - (widget_rect.width() / 2)
                widget.widget().setTitleAlign('center')
            widget.setPos(x, y)
            y += height #widget_rect.height()

    def _align_widgets_vertical(self, v_offset):
        if not self._widgets:
            return
        rect = self.boundingRect()
        y = rect.center().y() + v_offset
        widget_height = 0.0
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            widget_height += widget_rect.height()
        y -= widget_height / 2

        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            widget_rect = widget.boundingRect()
            x = rect.center().x() - (widget_rect.width() / 2)
            widget.widget().setTitleAlign('center')
            widget.setPos(x, y)
            y += widget_rect.height()

    def align_widgets(self, v_offset=0.0):
        """
        Align node widgets to the default center of the node.

        Args:
            v_offset (float): vertical offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_widgets_horizontal(v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_widgets_vertical(v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _align_ports_horizontal(self, v_offset):
        width = self._width
        txt_offset = PortEnum.CLICK_FALLOFF.value - 2
        spacing = 1

        disabledPortText = []

        if self._node_render_type == NodeRenderType.Reroute:
            v_offset = -self._height/3
        
        # adjust input position
        inputs = [p for p in self.inputs if p.isVisible()]
        if inputs:

            port_width = inputs[0].boundingRect().width()
            port_height = inputs[0].boundingRect().height()
            port_x = (port_width / 2) * -1
            port_y = v_offset
            # for port in inputs:
            #     baseY = port_y
            #     baseHeight = port_height
            #     port.setPos(port_x, baseY)
            #     port_y += baseHeight + spacing
            for prt,w,hsize in self._tupleWidgetData:
                if prt:
                    addval = 0
                    if w:
                        disabledPortText.append(prt)
                        addval = hsize/2-(port_height/2)
                    prt.setPos(port_x, port_y + addval)
                port_y += hsize + spacing
                
        # adjust input text position
        for port, text in self._input_items.items():
            if port.isVisible():
                if (port in disabledPortText):
                    port.display_name = False
                    text.setVisible(False)
                    continue
                txt_x = port.boundingRect().width() / 2 #- txt_offset #Yodes: removed const offset
                text.setPos(txt_x, port.y() - 1.5)

        # adjust output position
        outputs = [p for p in self.outputs if p.isVisible()]
        if outputs:
            port_width = outputs[0].boundingRect().width()
            port_height = outputs[0].boundingRect().height()
            port_x = width - (port_width / 2)
            port_y = v_offset
            for port in outputs:
                port.setPos(port_x, port_y)
                port_y += port_height + spacing
        # adjust output text position
        for port, text in self._output_items.items():
            if port.isVisible():
                txt_width = text.boundingRect().width() #- txt_offset #Yodes: removed const offset
                txt_x = port.x() - txt_width
                text.setPos(txt_x, port.y() - 1.5)

    def _align_ports_vertical(self, v_offset):
        # adjust input position
        inputs = [p for p in self.inputs if p.isVisible()]
        if inputs:
            port_width = inputs[0].boundingRect().width()
            port_height = inputs[0].boundingRect().height()
            half_width = port_width / 2
            delta = self._width / (len(inputs) + 1)
            port_x = delta
            port_y = (port_height / 2) * -1
            for port in inputs:
                port.setPos(port_x - half_width, port_y)
                port_x += delta

        # adjust output position
        outputs = [p for p in self.outputs if p.isVisible()]
        if outputs:
            port_width = outputs[0].boundingRect().width()
            port_height = outputs[0].boundingRect().height()
            half_width = port_width / 2
            delta = self._width / (len(outputs) + 1)
            port_x = delta
            port_y = self._height - (port_height / 2)
            for port in outputs:
                port.setPos(port_x - half_width, port_y)
                port_x += delta

    def align_ports(self, v_offset=0.0):
        """
        Align input, output ports in the node layout.

        Args:
            v_offset (float): port vertical offset.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._align_ports_horizontal(v_offset)
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._align_ports_vertical(v_offset)
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def _draw_node_horizontal(self):
        height = self._text_item.boundingRect().height() + 4.0

        if self._node_render_type in NodeRenderType.getNoHeaderTypes():
            height = 2

        # update port text items in visibility.
        for port, text in self._input_items.items():
            if port.isVisible():
                text.setVisible(port.display_name)
        for port, text in self._output_items.items():
            if port.isVisible():
                text.setVisible(port.display_name)

        self._calculate_items_positions(v_offset=height)

        # setup initial base size.
        self._set_base_size(add_h=height)
        # set text color when node is initialized.
        self._set_text_color(self.text_color)
        # set the tooltip
        self._tooltip_disable(self.disabled)

        # --- set the initial node layout ---
        # (do all the graphic item layout offsets here)

        # align label text
        self.align_label()
        # align icon
        self.align_icon(h_offset=2.0, v_offset=1.0)
        # arrange input and output ports.
        self.align_ports(v_offset=height)
        # arrange node widgets
        self.align_widgets(v_offset=height)

        self.update()

    def _draw_node_vertical(self):
        # hide the port text items in vertical layout.
        for port, text in self._input_items.items():
            text.setVisible(False)
        for port, text in self._output_items.items():
            text.setVisible(False)

        # setup initial base size.
        self._set_base_size()
        # set text color when node is initialized.
        self._set_text_color(self.text_color)
        # set the tooltip
        self._tooltip_disable(self.disabled)

        # --- setup node layout ---
        # (do all the graphic item layout offsets here)

        # align label text
        self.align_label(h_offset=6)
        # align icon
        self.align_icon(h_offset=6, v_offset=4)
        # arrange input and output ports.
        self.align_ports()
        # arrange node widgets
        self.align_widgets()

        self.update()

    def _calculate_items_positions(self, v_offset=0.0):
        allPorts = [p for p in self.inputs if p.isVisible()]

        retData : list[tuple] = []

        #sorting all widgets by port names
        widgetMap = {nm:w for nm,w in self._widgets.items()} #fix removed isivisble condition for get all widgets in proxymode
        
        for port in allPorts:
            if port.name in widgetMap.keys():
                retData.append((port, widgetMap[port.name]))
                widgetMap.pop(port.name)
            else:
                retData.append((port, None))

        for leftitem in widgetMap.values():
            retData.append((None, leftitem))

        
        curY = v_offset

        # Calcluate sizes
        tsizer : list[tuple] = []
        for port,wid in retData:
            maxadd = 0
            maxadd = port.boundingRect().height() if port else maxadd
            maxadd = max(maxadd, wid.boundingRect().height()) if wid else maxadd
            tsizer.append((port, wid, maxadd))
            pass
        
        self._tupleWidgetData = tsizer

    def draw_node(self):
        """
        Re-draw the node item in the scene with proper
        calculated size and widgets aligned.
        """
        if self.layout_direction is LayoutDirectionEnum.HORIZONTAL.value:
            self._draw_node_horizontal()
        elif self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            self._draw_node_vertical()
        else:
            raise RuntimeError('Node graph layout direction not valid!')

    def post_init(self, viewer=None, pos=None):
        """
        Called after node has been added into the scene.
        Adjust the node layout and form after the node has been added.

        Args:
            viewer (NodeGraphQt.widgets.viewer.NodeViewer): not used
            pos (tuple): cursor position.
        """
        self.draw_node()

        # set initial node position.
        if pos:
            self.xy_pos = pos

    def auto_switch_mode(self):
        """
        Decide whether to draw the node with proxy mode.
        (this is called at the start in the "self.paint()" function.)
        """
        if ITEM_CACHE_MODE is QtWidgets.QGraphicsItem.ItemCoordinateCache:
            return

        rect = self.sceneBoundingRect()
        l = self.viewer().mapToGlobal(
            self.viewer().mapFromScene(rect.topLeft()))
        r = self.viewer().mapToGlobal(
            self.viewer().mapFromScene(rect.topRight()))
        # width is the node width in screen
        width = r.x() - l.x()

        self.set_proxy_mode(width < self._proxy_mode_threshold)

    def set_proxy_mode(self, mode):
        """
        Set whether to draw the node with proxy mode.
        (proxy mode toggles visibility for some qgraphic items in the node.)

        Args:
            mode (bool): true to enable proxy mode.
        """
        if mode is self._proxy_mode:
            return
        self._proxy_mode = mode

        visible = not mode

        # disable overlay item.
        self._x_item.proxy_mode = self._proxy_mode

        self._error_item.proxy_mode = self._proxy_mode

        # node widget visibility.
        for w in self._widgets.values():
            w.widget().setVisible(visible)

        # port text is not visible in vertical layout.
        if self.layout_direction is LayoutDirectionEnum.VERTICAL.value:
            port_text_visible = False
        else:
            port_text_visible = visible

        # input port text visibility.
        for port, text in self._input_items.items():
            if port.display_name:
                text.setVisible(port_text_visible)

        # output port text visibility.
        for port, text in self._output_items.items():
            if port.display_name:
                text.setVisible(port_text_visible)

        self._text_item.setVisible(visible)
        self._icon_item.setVisible(visible)

    @property
    def icon(self):
        return self._properties['icon']

    @icon.setter
    def icon(self, path=None):
        
        path = path or ICON_NODE_BASE
        baseValue = path

        icondataList = []

        #update color icon
        if isinstance(path,list):
            baseValue = baseValue.copy()
            if not len(baseValue)%2==0:
                raise Exception(f'Invalid color structure: {baseValue}')
            for i in range(0,len(baseValue),2):
                clr = baseValue[i+1]
                icondataList.append((baseValue[i],clr))
                if isinstance(clr, QtGui.QColor):
                    baseValue[i+1] = clr.name()
        
        self._properties['icon'] = baseValue
        
        if not icondataList:
            icondataList = [(path,None)]

        pixmap = None
        pixList = []
        for pt_,clr_ in icondataList:
            #create pixmap
            pmCur = QtGui.QPixmap(pt_)
            if pmCur.size().height() > NodeEnum.ICON_SIZE.value:
                pmCur = pmCur.scaledToHeight(NodeEnum.ICON_SIZE.value,QtCore.Qt.SmoothTransformation)
            
            # update color
            if clr_:
                pmCur = updatePixmapColor(pmCur, clr_)

            pixList.append(pmCur)

        #merge colorized parts
        for pix in pixList:
            if not pixmap:
                pixmap = pix
            else:
                pixmap = mergePixmaps(pixmap, pix)

        self._icon_item.setPixmap(pixmap)
        if self.scene():
            self.post_init()

        self.update()
        del icondataList
        del pixList

    @AbstractNodeItem.layout_direction.setter
    def layout_direction(self, value=0):
        AbstractNodeItem.layout_direction.fset(self, value)
        self.draw_node()

    @AbstractNodeItem.width.setter
    def width(self, width=0.0):
        w, h = self.calc_size()
        width = width if width > w else w
        AbstractNodeItem.width.fset(self, width)

    @AbstractNodeItem.height.setter
    def height(self, height=0.0):
        w, h = self.calc_size()
        h = 70 if h < 70 else h
        height = height if height > h else h
        AbstractNodeItem.height.fset(self, height)

    @AbstractNodeItem.disabled.setter
    def disabled(self, state=False):
        AbstractNodeItem.disabled.fset(self, state)
        for n, w in self._widgets.items():
            w.widget().setDisabled(state)
        self._tooltip_disable(state)
        self._x_item.setVisible(state)

    @AbstractNodeItem.selected.setter
    def selected(self, selected=False):
        AbstractNodeItem.selected.fset(self, selected)
        if selected:
            self.highlight_pipes()

    #YODES: custom node header
    @AbstractNodeItem.name.setter
    def name(self, name=''):
        AbstractNodeItem.name.fset(self, name)
        if name == self._text_item.toPlainText():
            return
        desc = None
        if "@desc:" in name:
            name,desc = name.split("@desc:")
        
        #add bold
        if self._node_render_type in NodeRenderType.getNoHeaderTypes():
            name = f'<b>{name}</b>'    
        nametext = f'<span style=\'font-family: Arial; font-size: {self._default_font_size}pt;\'>{name}</span>'
        if self.nodeClass:
            data = self.getFactory().getNodeLibData(self.nodeClass)
            if data and 'classInfo' in data:
                data = data['classInfo']
                cdat = self.getFactory().getClassData(data['class'])
                origName = cdat.get("name",data.get("class",self.nodeClass))
                info = f'<b>{origName}</b> ({data.get("class",self.nodeClass)})'
                fm = QtGui.QFontMetrics(self._text_item.font())
                if fm.width(origName) > fm.width(name):
                    info = "<br/>" + info
                
                desc = f'Владелец ' + info
        if desc:
            nametext += f'<br/><font size=""4">{desc}</font>'
        
        if self.nodeClass == "internal.reroute":
            nametext = ""
        
        self._text_item.setHtml(nametext)
        if self.scene():
            self.align_label()
        self.update()

    @AbstractNodeItem.color.setter
    def color(self, color=(100, 100, 100, 255)):
        AbstractNodeItem.color.fset(self, color)
        if self.scene():
            self.scene().update()
        self.update()

    @AbstractNodeItem.text_color.setter
    def text_color(self, color=(100, 100, 100, 255)):
        AbstractNodeItem.text_color.fset(self, color)
        self._set_text_color(color)
        self.update()

    @property
    def text_item(self):
        """
        Get the node name text qgraphics item.

        Returns:
            NodeTextItem: node text object.
        """
        return self._text_item

    @property
    def inputs(self):
        """
        Returns:
            list[PortItem]: input port graphic items.
        """
        return list(self._input_items.keys())

    @property
    def outputs(self):
        """
        Returns:
            list[PortItem]: output port graphic items.
        """
        return list(self._output_items.keys())

    def _add_port(self, port):
        """
        Adds a port qgraphics item into the node.

        Args:
            port (PortItem): port item.

        Returns:
            PortItem: port qgraphics item.
        """
        text = QtWidgets.QGraphicsTextItem(port.name, self) #text = QtWidgets.QGraphicsTextItem(portName if portName else port.name, self)
        text.font().setPointSize(8)
        text.setFont(text.font())
        text.setVisible(port.display_name)
        text.setCacheMode(ITEM_CACHE_MODE)
        if port.port_type == PortTypeEnum.IN.value:
            self._input_items[port] = text
        elif port.port_type == PortTypeEnum.OUT.value:
            self._output_items[port] = text
        if self.scene():
            self.post_init()
        return port

    def add_input(self, name='input', multi_port=False, display_name=True,
                  locked=False,portType=None, painter_func=None,scripted_port=None):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        IN_PORT.

        Args:
            name (str): name for the port.
            multi_port (bool): allow multiple connections.
            display_name (bool): display the port name.
            locked (bool): locked state.
            painter_func (function): custom paint function.

        Returns:
            PortItem: input port qgraphics item.
        """
        if scripted_port:
            port = ScriptedCustomPortItem(self, painter_func)
        else:
            if painter_func:
                port = CustomPortItem(self, painter_func)
                port._port_painterStyle = getDrawPortStyleId(painter_func)
            else:
                port = PortItem(self)
        port.name = name
        port.port_type = PortTypeEnum.IN.value
        port.multi_connection = multi_port
        port.display_name = display_name
        port.locked = locked
        port.port_typeName = portType #Yobas: added port typename
        port._syncTooltip()
        return self._add_port(port)

    def add_output(self, name='output', multi_port=False, display_name=True,
                   locked=False,portType=None, painter_func=None):
        """
        Adds a port qgraphics item into the node with the "port_type" set as
        OUT_PORT.

        Args:
            name (str): name for the port.
            multi_port (bool): allow multiple connections.
            display_name (bool): display the port name.
            locked (bool): locked state.
            painter_func (function): custom paint function.

        Returns:
            PortItem: output port qgraphics item.
        """
        if painter_func:
            port = CustomPortItem(self, painter_func)
            port._port_painterStyle = getDrawPortStyleId(painter_func)
        else:
            port = PortItem(self)
        port.name = name
        port.port_type = PortTypeEnum.OUT.value
        port.multi_connection = multi_port
        port.display_name = display_name
        port.locked = locked
        port.port_typeName = portType #Yobas: added port typename
        port._syncTooltip()
        return self._add_port(port)

    def _delete_port(self, port, text):
        """
        Removes port item and port text from node.

        Args:
            port (PortItem): port object.
            text (QtWidgets.QGraphicsTextItem): port text object.
        """
        port.setParentItem(None)
        text.setParentItem(None)
        if self.scene(): #Yobas: fix remove port on scene not loaded (on deserialize graph)
            self.scene().removeItem(port)
            self.scene().removeItem(text)
        del port
        del text

    def delete_input(self, port):
        """
        Remove input port from node.

        Args:
            port (PortItem): port object.
        """
        self._delete_port(port, self._input_items.pop(port))

    def delete_output(self, port):
        """
        Remove output port from node.

        Args:
            port (PortItem): port object.
        """
        self._delete_port(port, self._output_items.pop(port))

    def get_input_text_item(self, port_item):
        """
        Args:
            port_item (PortItem): port item.

        Returns:
            QGraphicsTextItem: graphic item used for the port text.
        """
        return self._input_items[port_item]

    def get_output_text_item(self, port_item):
        """
        Args:
            port_item (PortItem): port item.

        Returns:
            QGraphicsTextItem: graphic item used for the port text.
        """
        return self._output_items[port_item]

    @property
    def widgets(self):
        return self._widgets.copy()

    def add_widget(self, widget):
        self._widgets[widget.get_name()] = widget

    def get_widget(self, name):
        widget = self._widgets.get(name)
        if widget:
            return widget
        raise NodeWidgetError('node has no widget "{}"'.format(name))

    def has_widget(self, name):
        return name in self._widgets.keys()

    def from_dict(self, node_dict):
        super(NodeItem, self).from_dict(node_dict)
        widgets = node_dict.pop('widgets', {})
        for name, value in widgets.items():
            if self._widgets.get(name):
                self._widgets[name].set_value(value)
