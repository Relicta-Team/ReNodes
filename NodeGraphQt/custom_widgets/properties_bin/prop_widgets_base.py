#!/usr/bin/python
from Qt import QtWidgets, QtCore, QtGui


class PropLabel(QtWidgets.QLabel):
    """
    Displays a node property as a "QLabel" widget in the PropertiesBin widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def get_value(self):
        return self.text()

    def set_value(self, value):
        if value != self.get_value():
            self.setText(str(value))
            self.value_changed.emit(self.toolTip(), value)


class PropObject(QtWidgets.QLabel):
    value_changed = QtCore.Signal(str, object)
    def __init__(self, parent=None):
        super(PropObject, self).__init__(parent)
        self.setTextInteractionFlags(self.textInteractionFlags() | QtCore.Qt.TextSelectableByMouse)
        self.set_value("nullPtr")

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def get_value(self):
        return self.text()
    def set_value(self, value):
        if value != self.get_value():
            self.setText(value)
            self.value_changed.emit(self.toolTip(), value)
    
    def get_value(self):
        return self.text()

class PropAbstract(QtWidgets.QLabel):
    value_changed = QtCore.Signal(str, object)
    def __init__(self, parent=None):
        super(PropAbstract, self).__init__(parent)
        self.setTextInteractionFlags(self.textInteractionFlags() | QtCore.Qt.TextSelectableByMouse)
        self.set_value("nullPtr")

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def get_value(self):
        return self.text()
    def set_value(self, value):
        if value != self.get_value():
            _strVal = value
            if not isinstance(value, str):
                _strVal = str(value)
            self.setText(_strVal)
            self.value_changed.emit(self.toolTip(), value)
    
    def get_value(self):
        return self.text()

class PropLineEdit(QtWidgets.QLineEdit):
    """
    Displays a node property as a "QLineEdit" widget in the PropertiesBin
    widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropLineEdit, self).__init__(parent)
        self.editingFinished.connect(self._on_editing_finished)

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def _on_editing_finished(self):
        self.value_changed.emit(self.toolTip(), self.text())

    def get_value(self):
        return self.text()

    def set_value(self, value):
        _value = str(value)
        if _value != self.get_value():
            self.setText(_value)
            self.value_changed.emit(self.toolTip(), _value)


class AutoResizingTextEdit(QtWidgets.QTextEdit):
    on_geometry_updated = QtCore.Signal()
    def __init__(self, parent = None,createUpdateEvent=True):
        super(AutoResizingTextEdit, self).__init__(parent)

        self.setWordWrapMode(QtGui.QTextOption.WrapAnywhere) #custom wrap update

        # This seems to have no effect. I have expected that it will cause self.hasHeightForWidth()
        # to start returning True, but it hasn't - that's why I hardcoded it to True there anyway.
        # I still set it to True in size policy just in case - for consistency.
        size_policy = self.sizePolicy()
        size_policy.setHeightForWidth(True)
        size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Preferred)
        self.setSizePolicy(size_policy)

        if createUpdateEvent:
            self.textChanged.connect(lambda: self.updateGeometry())

    def updateGeometry(self) -> None:
        super().updateGeometry()
        self.on_geometry_updated.emit()

    def setMinimumLines(self, num_lines):
        """ Sets minimum widget height to a value corresponding to specified number of lines
            in the default font. """

        self.setMinimumSize(self.minimumSize().width(), self.lineCountToWidgetHeight(num_lines))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        margins = self.contentsMargins()

        if width >= margins.left() + margins.right():
            document_width = width - margins.left() - margins.right()
        else:
            # If specified width can't even fit the margin, there's no space left for the document
            document_width = 0

        # Cloning the whole document only to check its size at different width seems wasteful
        # but apparently it's the only and preferred way to do this in Qt >= 4. QTextDocument does not
        # provide any means to get height for specified width (as some QWidget subclasses do).
        # Neither does QTextEdit. In Qt3 Q3TextEdit had working implementation of heightForWidth()
        # but it was allegedly just a hack and was removed.
        #
        # The performance probably won't be a problem here because the application is meant to
        # work with a lot of small notes rather than few big ones. And there's usually only one
        # editor that needs to be dynamically resized - the one having focus.
        document = self.document().clone()
        document.setTextWidth(document_width)

        return margins.top() + int(document.size().height()) + margins.bottom()

    def sizeHint(self):
        original_hint = super(AutoResizingTextEdit, self).sizeHint()
        return QtCore.QSize(original_hint.width(), self.heightForWidth(original_hint.width()))

    def lineCountToWidgetHeight(self, num_lines):
        """ Returns the number of pixels corresponding to the height of specified number of lines
            in the default font. """
        from PyQt5 import QtGui
        # ASSUMPTION: The document uses only the default font

        assert num_lines >= 0

        widget_margins  = self.contentsMargins()
        document_margin = self.document().documentMargin()
        font_metrics    = QtGui.QFontMetrics(self.document().defaultFont())

        # font_metrics.lineSpacing() is ignored because it seems to be already included in font_metrics.height()
        return (
            widget_margins.top()                      +
            document_margin                           +
            max(num_lines, 1) * font_metrics.height() +
            self.document().documentMargin()          +
            widget_margins.bottom()
        )

        return QSize(original_hint.width(), minimum_height_hint)

class PropTextEdit(AutoResizingTextEdit): #prev inherit from QtWidgets.QTextEdit
    """
    Displays a node property as a "QTextEdit" widget in the PropertiesBin
    widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropTextEdit, self).__init__(parent)
        self._prev_text = ''

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def focusInEvent(self, event):
        super(PropTextEdit, self).focusInEvent(event)
        self._prev_text = self.toPlainText()

    def focusOutEvent(self, event):
        super(PropTextEdit, self).focusOutEvent(event)
        if self._prev_text != self.toPlainText():
            self.value_changed.emit(self.toolTip(), self.toPlainText())
        self._prev_text = ''

    def get_value(self):
        return self.toPlainText()

    def set_value(self, value):
        _value = str(value)
        if _value != self.get_value():
            self.setPlainText(_value)
            self.value_changed.emit(self.toolTip(), _value)


class PropComboBox(QtWidgets.QComboBox):
    """
    Displays a node property as a "QComboBox" widget in the PropertiesBin
    widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropComboBox, self).__init__(parent)
        self.currentIndexChanged.connect(self._on_index_changed)

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def _on_index_changed(self):
        self.value_changed.emit(self.toolTip(), self.get_value())

    def items(self):
        """
        Returns items from the combobox.

        Returns:
            list[str]: list of strings.
        """
        return [self.itemText(i) for i in range(self.count())]

    def set_items(self, items):
        """
        Set items on the combobox.

        Args:
            items (list[str]): list of strings.
        """
        self.clear()
        self.addItems(items)

    def get_value(self):
        return self.currentText()

    def set_value(self, value):
        if value != self.get_value():
            idx = self.findText(value, QtCore.Qt.MatchExactly)
            if value == '-1' and idx == -1: idx = 0 #set to first item
            self.setCurrentIndex(idx)
            if idx >= 0:
                self.value_changed.emit(self.toolTip(), value)

    def init_enum_values(self,typename):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        fact = NodeGraphComponent.refObject.getFactory()
        if fact.isEnumType(typename):
            evlsList = fact.getEnumValues(typename)
            self.addItems(evlsList)

class PropCheckBox(QtWidgets.QCheckBox):
    """
    Displays a node property as a "QCheckBox" widget in the PropertiesBin
    widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropCheckBox, self).__init__(parent)
        self.clicked.connect(self._on_clicked)

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def _on_clicked(self):
        self.value_changed.emit(self.toolTip(), self.get_value())

    def get_value(self):
        return self.isChecked()

    def set_value(self, value):
        _value = bool(value)
        if _value != self.get_value():
            self.setChecked(_value)
            self.value_changed.emit(self.toolTip(), _value)


class PropSpinBox(QtWidgets.QSpinBox):
    """
    Displays a node property as a "QSpinBox" widget in the PropertiesBin widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropSpinBox, self).__init__(parent)
        self.setButtonSymbols(self.NoButtons)
        self.valueChanged.connect(self._on_value_change)

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def _on_value_change(self, value):
        self.value_changed.emit(self.toolTip(), value)

    def get_value(self):
        return self.value()

    def set_value(self, value):
        if value != self.get_value():
            self.setValue(value)


class PropDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """
    Displays a node property as a "QDoubleSpinBox" widget in the PropertiesBin
    widget.
    """

    value_changed = QtCore.Signal(str, object)

    def __init__(self, parent=None):
        super(PropDoubleSpinBox, self).__init__(parent)
        self.setButtonSymbols(self.NoButtons)
        self.valueChanged.connect(self._on_value_change)

    def __repr__(self):
        return '<{}() object at {}>'.format(
            self.__class__.__name__, hex(id(self)))

    def _on_value_change(self, value):
        self.value_changed.emit(self.toolTip(), value)

    def get_value(self):
        return self.value()

    def set_value(self, value):
        if value != self.get_value():
            self.setValue(value)


# class PropPushButton(QtWidgets.QPushButton):
#     """
#     Displays a node property as a "QPushButton" widget in the PropertiesBin
#     widget.
#     """
#
#     value_changed = QtCore.Signal(str, object)
#     button_clicked = QtCore.Signal(str, object)
#
#     def __init__(self, parent=None):
#         super(PropPushButton, self).__init__(parent)
#         self.clicked.connect(self.button_clicked.emit)
#
#     def set_on_click_func(self, func, node):
#         """
#         Sets slot function for the PropPushButton widget.
#
#         Args:
#             func (function): property slot function.
#             node (NodeGraphQt.NodeObject): node object.
#         """
#         if not callable(func):
#             raise TypeError('var func is not a function.')
#         self.clicked.connect(lambda: func(node))
#
#     def get_value(self):
#         return
#
#     def set_value(self, value):
#         return
