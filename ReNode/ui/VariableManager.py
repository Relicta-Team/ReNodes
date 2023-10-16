from PyQt5.QtWidgets import QMainWindow,QLabel, QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem

class VariableManager(QDockWidget):
    def __init__(self,actionVarViewer = None):
        
        super().__init__("Variables")
        self.variable_type_combo = None
        self.variable_name_input = None
        self.default_value_input = None
        self.variable_tree = None

        self.actionVarViewer = actionVarViewer
        
        self.initUI()
        
    def syncActionText(self,initState=None):
        condition = self.isVisible()
        if initState:
            condition = initState
        newtext = "&Скрыть окно переменных" if condition else "&Показать окно переменных"
        self.actionVarViewer.setText(newtext)

    def initUI(self):
        # Создайте центральный виджет для док-зоны
        central_widget = QWidget(self)
        self.setWidget(central_widget)

        # Создайте вертикальный макет для центрального виджета
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Variable Type"))
        # Выпадающий список для выбора типа переменной
        variable_type_combo = QComboBox()
        variable_type_combo.addItems(["int", "float", "string", "bool"])
        layout.addWidget(variable_type_combo)
        self.variable_type_combo = variable_type_combo

        layout.addWidget(QLabel("Variable Name"))
        # Поле для ввода имени переменной
        variable_name_input = QLineEdit()
        layout.addWidget(variable_name_input)
        self.variable_name_input = variable_name_input

        layout.addWidget(QLabel("Default Value"))
        # Поле для ввода дефолтного значения
        default_value_input = QLineEdit()
        layout.addWidget(default_value_input)
        self.default_value_input = default_value_input

        # Кнопка создания переменной
        create_variable_button = QPushButton("Create Variable")
        create_variable_button.clicked.connect(self.createVariable)
        layout.addWidget(create_variable_button)

        # Дерево для отображения списка переменных
        variable_tree = QTreeWidget()
        variable_tree.setHeaderLabels(["Name", "Type", "Default Value"])
        layout.addWidget(variable_tree)
        self.variable_tree = variable_tree

        central_widget.setLayout(layout)

    def createVariable(self):
        # Получите значения типа переменной, имени и дефолтного значения
        variable_type = self.variable_type_combo.currentText()
        variable_name = self.variable_name_input.text()
        default_value = self.default_value_input.text()

        # Создайте новый элемент дерева для переменной и добавьте его в дерево
        item = QTreeWidgetItem([variable_name, variable_type, default_value])
        self.variable_tree.addTopLevelItem(item)


