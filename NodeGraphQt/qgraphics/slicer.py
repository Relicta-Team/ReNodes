#!/usr/bin/python
import math

from Qt import QtCore, QtGui, QtWidgets

from NodeGraphQt.constants import Z_VAL_NODE_WIDGET, PipeSlicerEnum
from NodeGraphQt.qgraphics.node_abstract import AbstractNodeItem


class SlicerPipeItem(QtWidgets.QGraphicsPathItem):
    """
    Base item used for drawing the pipe connection slicer.
    """

    def __init__(self):
        super(SlicerPipeItem, self).__init__()
        self.setZValue(Z_VAL_NODE_WIDGET + 2)

    def paint(self, painter, option, widget):
        """
        Draws the slicer pipe.

        Args:
            painter (QtGui.QPainter): painter used for drawing the item.
            option (QtGui.QStyleOptionGraphicsItem):
                used to describe the parameters needed to draw.
            widget (QtWidgets.QWidget): not used.
        """
        color = QtGui.QColor(*PipeSlicerEnum.COLOR.value)
        p1 = self.path().pointAtPercent(0)
        p2 = self.path().pointAtPercent(1)
        size = 6.0
        offset = size / 2
        arrow_size = 4.0

        painter.save()
        painter.setRenderHint(painter.Antialiasing, True)

        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        text = 'slice'
        text_x = painter.fontMetrics().width(text) / 2
        text_y = painter.fontMetrics().height() / 1.5
        text_pos = QtCore.QPointF(p1.x() - text_x, p1.y() - text_y)
        text_color = QtGui.QColor(*PipeSlicerEnum.COLOR.value)
        text_color.setAlpha(80)
        painter.setPen(QtGui.QPen(
            text_color, PipeSlicerEnum.WIDTH.value, QtCore.Qt.SolidLine
        ))
        painter.drawText(text_pos, text)

        painter.setPen(QtGui.QPen(
            color, PipeSlicerEnum.WIDTH.value, QtCore.Qt.DashDotLine
        ))
        painter.drawPath(self.path())

        pen = QtGui.QPen(
            color, PipeSlicerEnum.WIDTH.value, QtCore.Qt.SolidLine
        )
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(color)

        rect = QtCore.QRectF(p1.x() - offset, p1.y() - offset, size, size)
        painter.drawEllipse(rect)

        arrow = QtGui.QPolygonF()
        arrow.append(QtCore.QPointF(-arrow_size, arrow_size))
        arrow.append(QtCore.QPointF(0.0, -arrow_size * 0.9))
        arrow.append(QtCore.QPointF(arrow_size, arrow_size))

        transform = QtGui.QTransform()
        mid_point = QtCore.QPointF((p2.x() + p1.x()) / 2, (p2.y() + p1.y()) / 2)
        transform.translate(mid_point.x(), mid_point.y()) #prev: transform.translate(p2.x(), p2.y())
        radians = math.atan2(p2.y() - p1.y(),
                             p2.x() - p1.x())
        degrees = math.degrees(radians) + 90 #prev:  degrees = math.degrees(radians) - 90
        transform.rotate(degrees)

        painter.drawPolygon(transform.map(arrow))
        painter.restore()

    def draw_path(self, p1, p2):
        path = QtGui.QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        self.setPath(path)


class descriptionTextItem(QtWidgets.QGraphicsTextItem):
    def paint(self, painter, option, a):
        option.state = QtWidgets.QStyle.State_None
        return super(descriptionTextItem, self).paint(painter,option,a)

class DescriptionItem(QtWidgets.QGraphicsItem):
    """
    Base item used for drawing the pipe description.
    """

    def __init__(self,view__):
        super(DescriptionItem, self).__init__()
        self.setZValue(Z_VAL_NODE_WIDGET + 2)
        self._width = 100
        self._height = 50
        self.view = view__
        
        self.setAcceptHoverEvents(True)
        #add text and background box
        text = 'Your text here 123 123 123 12 312 3123 124 213 123 '
        background_rect = QtCore.QRectF(0, 0, 100, 50)  # adjust the size as needed
        #background_color = QtGui.QColor(255, 255, 255)  # adjust the color as needed

        # Draw the text
        font = QtGui.QFont()
        font.setPointSize(12)  # adjust the font size as needed
        #font.setBold(True)  # adjust the font style as needed
        text_item = descriptionTextItem(text, self)
        #text_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        #text_item.e QtWidgets.QGraphicsTextItem.GraphicsItemFlag.
        text_item.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        text_item.setHtml('<span style="font-family: Arial; font-size: 12pt;">' + text + '</span><br>Description: <span style="font-family: Arial; font-size: 4pt;">Test description</span>')
        text_item.setFont(font)
        text_item.setDefaultTextColor(QtGui.QColor(255, 255, 255))  # adjust the text color as needed
        #text_item.setPos(background_rect.center().x() - text_item.boundingRect().width() / 2,
        #                 background_rect.center().y() - text_item.boundingRect().height() / 2)
        
        self.text_item = text_item

        self._lastItem = None
        self._pos = None
        self._lockUpdate = False
        self.setVisible(False)

        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        self._refFactory = NodeGraphComponent.refObject.getFactory()

        #run timer every 0.5 seconds
        from PyQt5.QtCore import QTimer
        timer = QTimer(view__)
        timer.setSingleShot(True)
        timer.setInterval(1000)
        timer.timeout.connect(self.onTimer)
        self.timer = timer

    def boundingRect(self):
        return QtCore.QRectF(0.0, 0.0, self._width, self._height)

    def loadText(self):
        if not self._lastItem: return
        className = self._lastItem.nodeClass
        libInfo = self._refFactory.getNodeLibData(className)
        text = f"Ошибка [{className}] "
        if libInfo:
            text = f'<span style="font-size: 24pt">{self._lastItem.name} ({className})</span>'
            # if hasattr(self._lastItem,"_error_item"):
            #     if self._lastItem._error_item.isVisible():
            #         text = '<span style="color: red; font-size:30pt">Ошибка при компиляции</span><br/>' + text
            text += f'<br/>Путь: {libInfo.get("path") or "нет"}<br/>'

            iTxt = ",".join([o.name for o in self._lastItem.inputs])
            text += f'<br/>Входные порты: {iTxt if iTxt else "отсутствуют"}'
            oTxt = ",".join([o.name for o in self._lastItem.outputs])
            text += f'<br/>Выходные порты: {oTxt if oTxt else "отсутствуют"}'
            text += f'<br/><br/>Описание: {libInfo.get("desc") or "отсутствует"}'

        self.text_item.setHtml('<span style="font-family: Arial; font-size: 12pt;">' + text + '</span>')

    def paint(self, painter, option, widget):
        option.state = QtWidgets.QStyle.State_None
        painter.save()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtCore.Qt.NoBrush)

        #resize background to text bounding rect
        text_rect = self.text_item.boundingRect()
        text_rect.adjust(-5,0,10,0)
        padding = 5, 5
        background_rect = QtCore.QRectF(text_rect.x() - padding[0], text_rect.y() - padding[1], text_rect.width() + padding[0] * 2, text_rect.height() + padding[1] * 2)
        
        painter.setBrush(QtGui.QBrush(QtGui.QColor(20, 20, 20, 140)))
        painter.drawRoundedRect(background_rect, 5, 5)

        #draw basic background
        #gradient color
        if self._lastItem:
            gradient = QtGui.QLinearGradient(text_rect.topLeft(), QtCore.QPointF(text_rect.bottomRight().x(), text_rect.bottomRight().y()*2))
            
            gradient.setSpread(QtGui.QGradient.PadSpread)
            gradient.setColorAt(0.2, QtGui.QColor(*self._lastItem.color))
            gradient.setColorAt(1.0, QtGui.QColor(80, 80, 80, 50))
        else:
            gradient = QtGui.QColor(80, 80, 80, 255)
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawRoundedRect(text_rect, 2, 2)

        painter.restore()
    
    def movingEvent(self,pos:QtCore.QPointF):
        
        if self._lockUpdate: return

        self._pos = pos
        near = self.view._items_near(pos, AbstractNodeItem, 1, 1)
        if len(near) > 0:
            if self.isVisible():
                if near[0] != self._lastItem:
                    self.onTimer()
            else:
                self.timer.start()
            self._lastItem = near[0]
        else:
            self._lastItem = None
            self.timer.stop()
            self.setVisible(False)
    
    def doRender(self):
        self.setVisible(True)
        self.setPos(self._pos + QtCore.QPointF(10, 10))
        self.loadText()
    def onTimer(self):
        print("Called timer")
        if self._lastItem:
            self.doRender()
        pass

    def hoverEnterEvent(self, event):
        #self.doRender()
        self._lockUpdate = True
        super(DescriptionItem, self).hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self.setVisible(False)
        self._lockUpdate = False
        super(DescriptionItem, self).hoverLeaveEvent(event)