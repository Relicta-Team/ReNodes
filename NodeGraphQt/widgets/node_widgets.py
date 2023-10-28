#!/usr/bin/python
from Qt import QtCore, QtWidgets, QtGui

from NodeGraphQt.constants import ViewerEnum, Z_VAL_NODE_WIDGET
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_color_picker import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_file_paths import PropFilePathCustom
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_vectors import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_vectors import _PropVector
from NodeGraphQt.errors import NodeWidgetError


class _NodeGroupBox(QtWidgets.QGroupBox):

    def __init__(self, label, parent=None):
        super(_NodeGroupBox, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(1)
        self.setTitle(label)

    def setTitle(self, text):
        margin = (0, 2, 0, 0) if text else (0, 0, 0, 0)
        self.layout().setContentsMargins(*margin)
        super(_NodeGroupBox, self).setTitle(text)

        # Вычисляем ширину текста заголовка
        fm = self.fontMetrics()
        title_width = fm.width(text)

        # Устанавливаем минимальную и максимальную ширину виджета (QGroupBox)
        self.setMinimumWidth(title_width + 8) #+8 для полной видимости последней буквы

    def setTitleAlign(self, align='center'):
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               ViewerEnum.BACKGROUND_COLOR.value))
        style_dict = {
            'QGroupBox': {
                'background-color': 'rgba(0, 0, 0, 0)',
                'border': '0px solid rgba(0, 0, 0, 0)',
                'margin-top': '1px',
                'padding-bottom': '2px',
                'padding-left': '1px',
                'padding-right': '1px',
                'font-size': '8pt',
            },
            'QGroupBox::title': {
                'subcontrol-origin': 'margin',
                'subcontrol-position': 'top center',
                #'color': 'rgba({0}, {1}, {2}, 100)'.format(*text_color), # Цвет выключен
                'padding': '0px',
            }
        }
        if self.title():
            style_dict['QGroupBox']['padding-top'] = '14px'
        else:
            style_dict['QGroupBox']['padding-top'] = '2px'

        if align == 'center':
            style_dict['QGroupBox::title']['subcontrol-position'] = 'top center'
        elif align == 'left':
            style_dict['QGroupBox::title']['subcontrol-position'] += 'top left'
            style_dict['QGroupBox::title']['margin-left'] = '4px'
        elif align == 'right':
            style_dict['QGroupBox::title']['subcontrol-position'] += 'top right'
            style_dict['QGroupBox::title']['margin-right'] = '4px'
        stylesheet = ''

        if align == 'port':
            style_dict['QGroupBox::title']['subcontrol-position'] += 'top left'
            style_dict['QGroupBox::title']['margin-left'] = '4px'
            # Вертикальное выравнивание вверху (по высоте)
            #style_dict['QGroupBox::title']['subcontrol-position'] = 'top top'
            # Убираем вертикальные отступы
            style_dict['QGroupBox::title']['padding-top'] = '14px'
            style_dict['QGroupBox::title']['padding-bottom'] = '0px'
            style_dict['QGroupBox::title']['alignment'] = 'center'

        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        self.setStyleSheet(stylesheet)

    def add_node_widget(self, widget):
        self.layout().addWidget(widget)

    def get_node_widget(self):
        return self.layout().itemAt(0).widget()


class NodeBaseWidget(QtWidgets.QGraphicsProxyWidget):
    """
    This is the main wrapper class that allows a ``QtWidgets.QWidget`` to be
    added in a :class:`NodeGraphQt.BaseNode` object.

    .. inheritance-diagram:: NodeGraphQt.NodeBaseWidget
        :parts: 1

    Args:
        parent (NodeGraphQt.BaseNode.view): parent node view.
        name (str): property name for the parent node.
        label (str): label text above the embedded widget.
    """

    value_changed = QtCore.Signal(str, object)
    """
    Signal triggered when the ``value`` attribute has changed.
    
    (This is connected to the :meth: `BaseNode.set_property` function when the 
    widget is added into the node.)

    :parameters: str, object
    :emits: property name, propety value
    """

    def __init__(self, parent=None, name=None, label=''):
        super(NodeBaseWidget, self).__init__(parent)
        self.setZValue(Z_VAL_NODE_WIDGET)
        self._name = name
        self._label = label
        self._node = None

    def setToolTip(self, tooltip):
        tooltip = tooltip.replace('\n', '<br/>')
        tooltip = '<b>{}</b><br/>{}'.format(self.name, tooltip)
        super(NodeBaseWidget, self).setToolTip(tooltip)

    def on_value_changed(self, *args, **kwargs):
        """
        This is the slot function that
        Emits the widgets current :meth:`NodeBaseWidget.value` with the
        :attr:`NodeBaseWidget.value_changed` signal.

        Args:
            args: not used.
            kwargs: not used.

        Emits:
            str, object: <node_property_name>, <node_property_value>
        """
        self.value_changed.emit(self.get_name(), self.get_value())

    @property
    def type_(self):
        """
        Returns the node widget type.

        Returns:
            str: widget type.
        """
        return str(self.__class__.__name__)

    @property
    def node(self):
        """
        Returns the node object this widget is embedded in.
        (This will return ``None`` if the widget has not been added to
        the node yet.)

        Returns:
            NodeGraphQt.BaseNode: parent node.
        """
        return self._node

    def get_icon(self, name):
        """
        Returns the default icon from the Qt framework.

        Returns:
            str: icon name.
        """
        return self.style().standardIcon(QtWidgets.QStyle.StandardPixmap(name))

    def get_name(self):
        """
        Returns the parent node property name.

        Returns:
            str: property name.
        """
        return self._name

    def set_name(self, name):
        """
        Set the property name for the parent node.

        Important:
            The property name must be set before the widget is added to
            the node.

        Args:
            name (str): property name.
        """
        if not name:
            return
        if self.node:
            raise NodeWidgetError(
                'Can\'t set property name widget already added to a Node'
            )
        self._name = name

    def get_value(self):
        """
        Returns the widgets current value.

        You must re-implement this property to if you're using a custom widget.

        Returns:
            str: current property value.
        """
        raise NotImplementedError

    def set_value(self, text):
        """
        Sets the widgets current value.

        You must re-implement this property to if you're using a custom widget.

        Args:
            text (str): new text value.
        """
        raise NotImplementedError

    def get_custom_widget(self):
        """
        Returns the embedded QWidget used in the node.

        Returns:
            QtWidgets.QWidget: nested QWidget
        """
        widget = self.widget()
        return widget.get_node_widget()

    def set_custom_widget(self, widget):
        """
        Set the custom QWidget used in the node.

        Args:
            widget (QtWidgets.QWidget): custom.
        """
        if self.widget():
            raise NodeWidgetError('Custom node widget already set.')
        group = _NodeGroupBox(self._label)
        group.add_node_widget(widget)
        self.setWidget(group)

    def get_label(self):
        """
        Returns the label text displayed above the embedded node widget.

        Returns:
            str: label text.
        """
        return self._label

    def set_label(self, label=''):
        """
        Sets the label text above the embedded widget.

        Args:
            label (str): new label ext.
        """
        if self.widget():
            self.widget().setTitle(label)
        self._label = label


class NodeComboBox(NodeBaseWidget):
    """
    Displays as a ``QComboBox`` in a node.

    .. inheritance-diagram:: NodeGraphQt.widgets.node_widgets.NodeComboBox
        :parts: 1

    .. note::
        `To embed a` ``QComboBox`` `in a node see func:`
        :meth:`NodeGraphQt.BaseNode.add_combo_menu`
    """

    def __init__(self, parent=None, name='', label='', items=None):
        super(NodeComboBox, self).__init__(parent, name, label)
        self.setZValue(Z_VAL_NODE_WIDGET + 1)
        
        combo_view = QtWidgets.QListView()
        #combo_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        
        combo = QtWidgets.QComboBox()
        combo.setView(combo_view)
        combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        combo.view().setMinimumWidth(300)
        """combo.setMinimumHeight(24)
        combo.setMinimumWidth(130)
        combo.setMaximumWidth(400)"""
        combo.setMinimumContentsLength(30)
        combo.addItems(items or [])
        combo.currentIndexChanged.connect(self.on_value_changed)
        combo.clearFocus()
        self.set_custom_widget(combo)
        #updated scroll
        combo.setStyleSheet("combobox-popup: 0;")
        combo.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

    @property
    def type_(self):
        return 'ComboNodeWidget'

    def on_value_changed(self, *args, **kwargs):
        combo_box = self.get_custom_widget()
        if not combo_box:
            return super().on_value_changed(*args,**kwargs)

        def is_text_fitting(combo_box):
            font_metrics = combo_box.fontMetrics()
            max_width = combo_box.width() - combo_box.view().verticalScrollBar().width()  # Учитываем вертикальную полосу прокрутки
            current_text = combo_box.currentText()
            text_width = font_metrics.width(current_text)
            return text_width <= max_width
        text = combo_box.itemText(args[0])
        if is_text_fitting(combo_box):
            combo_box.setToolTip("")
        else:
            combo_box.setToolTip(f'{text}')
        return super().on_value_changed(*args, **kwargs)

    def get_value(self):
        """
        Returns the widget current text.

        Returns:
            str: current text.
        """
        combo_widget = self.get_custom_widget()
        return str(combo_widget.currentText())

    def set_value(self, text=''):
        combo_widget = self.get_custom_widget()
        if type(text) is list:
            combo_widget.clear()
            combo_widget.addItems(text)
            return
        if text != self.get_value():
            index = combo_widget.findText(text, QtCore.Qt.MatchExactly)
            combo_widget.setCurrentIndex(index)

    def add_item(self, item):
        combo_widget : QtWidgets.QComboBox = self.get_custom_widget()
        combo_widget.addItem(item)

    def add_items(self, items=None):
        if items:
            combo_widget = self.get_custom_widget()
            combo_widget.addItems(items)

    def all_items(self):
        combo_widget = self.get_custom_widget()
        return [combo_widget.itemText(i) for i in range(combo_widget.count())]

    def sort_items(self, reversed=False):
        items = sorted(self.all_items(), reverse=reversed)
        combo_widget = self.get_custom_widget()
        combo_widget.clear()
        combo_widget.addItems(items)

    def clear(self):
        combo_widget = self.get_custom_widget()
        combo_widget.clear()


class NodeLineEdit(NodeBaseWidget):
    """
    Displays as a ``QLineEdit`` in a node.

    .. inheritance-diagram:: NodeGraphQt.widgets.node_widgets.NodeLineEdit
        :parts: 1

    .. note::
        `To embed a` ``QLineEdit`` `in a node see func:`
        :meth:`NodeGraphQt.BaseNode.add_text_input`
    """

    def __init__(self, parent=None, name='', label='', text=''):
        super(NodeLineEdit, self).__init__(parent, name, label)
        bg_color = ViewerEnum.BACKGROUND_COLOR.value
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               bg_color))
        text_sel_color = text_color
        style_dict = {
            'QLineEdit': {
                'background': 'rgba({0},{1},{2},20)'.format(*bg_color),
                'border': '1px solid rgb({0},{1},{2})'
                          .format(*ViewerEnum.GRID_COLOR.value),
                'border-radius': '3px',
                'color': 'rgba({0},{1},{2},150)'.format(*text_color),
                'selection-background-color': 'rgba({0},{1},{2},100)'
                                              .format(*text_sel_color),
            }
        }
        stylesheet = ''
        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        ledit = QtWidgets.QLineEdit()
        ledit.setText(text)
        ledit.setToolTip(text)
        ledit.setStyleSheet(stylesheet)
        ledit.setAlignment(QtCore.Qt.AlignLeft)
        ledit.editingFinished.connect(self.on_value_changed)
        ledit.clearFocus()
        self.set_custom_widget(ledit)
        self.widget().setMaximumWidth(140)

    @property
    def type_(self):
        return 'LineEditNodeWidget'

    def get_value(self):
        """
        Returns the widgets current text.

        Returns:
            str: current text.
        """
        return str(self.get_custom_widget().text())

    def set_value(self, text=''):
        """
        Sets the widgets current text.

        Args:
            text (str): new text.
        """
        if text != self.get_value():
            self.get_custom_widget().setText(text)
            self.on_value_changed()
    
    def on_value_changed(self, *args, **kwargs):
        custom = self.get_custom_widget()
        custom.setToolTip(custom.text())
        return super().on_value_changed(*args, **kwargs)

class NodeTextEdit(NodeBaseWidget):

    def __init__(self, parent=None, name='', label='', text=''):
        super(NodeTextEdit, self).__init__(parent, name, label)
        bg_color = ViewerEnum.BACKGROUND_COLOR.value
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               bg_color))
        text_sel_color = text_color
        style_dict = {
            'QPlainTextEdit': {
                'background': 'rgba({0},{1},{2},20)'.format(*bg_color),
                'border': '1px solid rgb({0},{1},{2})'
                          .format(*ViewerEnum.GRID_COLOR.value),
                'border-radius': '3px',
                'color': 'rgba({0},{1},{2},150)'.format(*text_color),
                'selection-background-color': 'rgba({0},{1},{2},100)'
                                              .format(*text_sel_color),
            }
        }
        stylesheet = ''
        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        ledit = QtWidgets.QPlainTextEdit()
        ledit.setPlainText(text)
        ledit.setPlaceholderText("...")
        ledit.setStyleSheet(stylesheet)
        ledit.textChanged.connect(self.on_value_changed)
        ledit.clearFocus()
        self.set_custom_widget(ledit)
        #self.widget().setMaximumSize(140,120)
        self.widget().setFixedSize(200,120)

    @property
    def type_(self):
        return 'PlainTextEditNodeWidget'

    def get_value(self):
        """
        Returns the widgets current text.

        Returns:
            str: current text.
        """
        return str(self.get_custom_widget().toPlainText())

    def set_value(self, text=''):
        """
        Sets the widgets current text.

        Args:
            text (str): new text.
        """
        if text != self.get_value():
            self.get_custom_widget().setPlainText(text)
            self.on_value_changed()

class NodeSpinBox(NodeBaseWidget):

    def __init__(self, parent=None, name='', label='', value=0,range={"min":0,"max":1}):
        super(NodeSpinBox, self).__init__(parent, name, label)
        bg_color = ViewerEnum.BACKGROUND_COLOR.value
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               bg_color))
        text_sel_color = text_color
        style_dict = {
            'QSpinBox': {
                'background': 'rgba({0},{1},{2},20)'.format(*bg_color),
                'border': '1px solid rgb({0},{1},{2})'
                          .format(*ViewerEnum.GRID_COLOR.value),
                'border-radius': '3px',
                'color': 'rgba({0},{1},{2},150)'.format(*text_color),
                'selection-background-color': 'rgba({0},{1},{2},100)'
                                              .format(*text_sel_color),
            }
        }
        stylesheet = ''
        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        spin = QtWidgets.QSpinBox()
        spin.setValue(value)
        spin.setRange(range['min'],range['max'])
        spin.setStyleSheet(stylesheet)
        spin.valueChanged.connect(self.on_value_changed)
        spin.clearFocus()
        self.set_custom_widget(spin)
        #self.widget().setMaximumSize(140,120)
        #self.widget().setFixedSize(200,120)
        self.widget().setMinimumWidth(self.widget().geometry().width())

    @property
    def type_(self):
        return 'SpinBoxNodeWidget'

    def get_value(self):
        return int(self.get_custom_widget().value())

    def set_value(self, text=0):
        if text != self.get_value():
            self.get_custom_widget().setValue(text)
            self.on_value_changed()

class NodeFloatSpinBox(NodeBaseWidget):

    def __init__(self, parent=None, name='', label='', value=0,range={"min":0,"max":1},floatspindata={'step': 0.01,"decimals": 3}):
        super(NodeFloatSpinBox, self).__init__(parent, name, label)
        bg_color = ViewerEnum.BACKGROUND_COLOR.value
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               bg_color))
        text_sel_color = text_color
        style_dict = {
            'QDoubleSpinBox': {
                'background': 'rgba({0},{1},{2},20)'.format(*bg_color),
                'border': '1px solid rgb({0},{1},{2})'
                          .format(*ViewerEnum.GRID_COLOR.value),
                'border-radius': '3px',
                'color': 'rgba({0},{1},{2},150)'.format(*text_color),
                'selection-background-color': 'rgba({0},{1},{2},100)'
                                              .format(*text_sel_color),
            }
        }
        stylesheet = ''
        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        spin = QtWidgets.QDoubleSpinBox()
        spin.setValue(value)
        spin.setRange(range['min'],range['max'])
        spin.setStyleSheet(stylesheet)
        locale = QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates)
        spin.setLocale(locale)
        spin.valueChanged.connect(self.on_value_changed)
        spin.clearFocus()
        spin.setSingleStep(floatspindata.get('step',1))
        spin.setDecimals(floatspindata.get('decimals',2))
        self.set_custom_widget(spin)
        #self.widget().setMaximumSize(140,120)
        #self.widget().setFixedSize(200,120)

    @property
    def type_(self):
        return 'SpinBoxFloatNodeWidget'

    def get_value(self):
        return float(self.get_custom_widget().value())

    def set_value(self, text=0):
        if text != self.get_value():
            self.get_custom_widget().setValue(text)
            self.on_value_changed()

class NodeCheckBox(NodeBaseWidget):
    """
    Displays as a ``QCheckBox`` in a node.

    .. inheritance-diagram:: NodeGraphQt.widgets.node_widgets.NodeCheckBox
        :parts: 1

    .. note::
        `To embed a` ``QCheckBox`` `in a node see func:`
        :meth:`NodeGraphQt.BaseNode.add_checkbox`
    """

    def __init__(self, parent=None, name='', label='', text='', state=False):
        super(NodeCheckBox, self).__init__(parent, name, label)
        _cbox = QtWidgets.QCheckBox(text)
        text_color = tuple(map(lambda i, j: i - j, (255, 255, 255),
                               ViewerEnum.BACKGROUND_COLOR.value))
        style_dict = {
            'QCheckBox': {
                'color': 'rgba({0},{1},{2},150)'.format(*text_color),
            }
        }
        stylesheet = ''
        for css_class, css in style_dict.items():
            style = '{} {{\n'.format(css_class)
            for elm_name, elm_val in css.items():
                style += '  {}:{};\n'.format(elm_name, elm_val)
            style += '}\n'
            stylesheet += style
        _cbox.setStyleSheet(stylesheet)
        _cbox.setChecked(state)
        _cbox.setMinimumWidth(80)
        font = _cbox.font()
        font.setPointSize(11)
        _cbox.setFont(font)
        _cbox.stateChanged.connect(self.on_value_changed)
        self.set_custom_widget(_cbox)
        self.widget().setMaximumWidth(140)

    @property
    def type_(self):
        return 'CheckboxNodeWidget'

    def get_value(self):
        """
        Returns the widget checked state.

        Returns:
            bool: checked state.
        """
        return self.get_custom_widget().isChecked()

    def set_value(self, state=False):
        """
        Sets the widget checked state.

        Args:
            state (bool): check state.
        """
        if state != self.get_value():
            self.get_custom_widget().setChecked(state)


class NodeVector(NodeBaseWidget):
    def __init__(self, parent=None, name='', label='', value=None,dimensions = 2):
        super(NodeVector, self).__init__(parent, name, label)
        if not value:
            raise NodeWidgetError("Empty value")
        itm = _PropVector(fields=dimensions)
        
        #setup dot style
        locale = QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates)
        for itmiter in itm._items:
            itmiter: QtWidgets.QLineEdit
            itmiter.setLocale(locale)
        
        itm.set_value(value)
        self.propertyVector : _PropVector = itm
        self.set_custom_widget(itm)
        #_cbox.stateChanged.connect(self.on_value_changed)
        #self.set_custom_widget(_cbox)

    @property
    def type_(self):
        return 'NodeVectorWidget'

    def get_value(self):
        return self.propertyVector.get_value()

    def set_value(self, value=None):
        if not value or value != self.get_value():
            self.propertyVector.set_value(value)


class NodeColorPicker(NodeBaseWidget):
    def __init__(self, parent=None, name='', label='', value=None,useAlpha = False):
        super(NodeColorPicker, self).__init__(parent, name, label)
        wid = None
        if useAlpha:
            wid = PropColorPickerRGBA()
            wid.customizedColorbox = 2
        else:
            wid = PropColorPickerRGB()
            wid.customizedColorbox = 1
        
        self.set_custom_widget(wid)

    @property
    def type_(self):
        return 'NodeColorPickerWidget'

    def get_value(self):
        return self.get_custom_widget().get_value()

    def set_value(self, value=None):
        if value != self.get_value():
            self.get_custom_widget().set_value(value)


class NodeFileOpen(NodeBaseWidget):
    def __init__(self, parent=None, name='', label='', value=None,extensionPattern=None,rootDir=None,title=None):
        super(NodeFileOpen, self).__init__(parent, name, label)
        wid = PropFilePathCustom()
        
        if extensionPattern:
            wid.set_file_ext(extensionPattern)
        
        if rootDir:
            wid.set_file_directory(rootDir)
        
        if title:
            wid.set_file_title(title)

        self.set_custom_widget(wid)

    @property
    def type_(self):
        return 'FileOpenWidget'

    def get_value(self):
        return self.get_custom_widget().get_value()

    def set_value(self, value=None):
        if value != self.get_value():
            self.get_custom_widget().set_value(value)