
from PyQt5 import QtWidgets, QtCore, QtGui

def initialize(main_window,app):
    # Create a menu.
	menubar = main_window.menuBar()
	file_menu = menubar.addMenu(QtGui.QIcon('./data/pic.png'),'Файл')
	menubar.addMenu("Прочее")


	# Create an action for the menu.
	exit_action = QtWidgets.QAction('Выход', file_menu)
	

	# create confirm message
	def confirm_exit():
		msg_box = QtWidgets.QMessageBox(main_window)
		msg_box.setIcon(QtWidgets.QMessageBox.Question)
		msg_box.setWindowTitle("Подтверждение выхода")
		msg_box.setText('Вы точно хотите выйти?')
		msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
		msg_box.button(QtWidgets.QMessageBox.Yes).setText('Да')
		msg_box.button(QtWidgets.QMessageBox.No).setText('Нет')
		reply = msg_box.exec()

		if reply == QtWidgets.QMessageBox.Yes:
			app.quit()
	
	exit_action.triggered.connect(confirm_exit)
	# Add the action to the menu.
	file_menu.addAction(exit_action)