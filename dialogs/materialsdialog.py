import pickle

from module.core import *
from ui.MaterialsDialog import Ui_MaterialsDialog


class MaterialsDialog(QDialog):
    materials_return = pyqtSignal()

    def __init__(self, parent):
        super(MaterialsDialog, self).__init__(parent)

        self.parent = parent
        self.ui = Ui_MaterialsDialog()
        self.ui.setupUi(self)
        # self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        title = "Reference Materials"
        self.setWindowTitle(title)

        self.setup_position()
        self.setParent(parent)

        self.ui.btn_remove.setDefault(False)
        self.ui.btn_add.setDefault(True)

        self.database = None
        self.material_names = []
        self.selected = []
        self.data_table = {}

        self.ui.listWidget.currentItemChanged.connect(self.material_selected)
        self.ui.btn_remove.clicked.connect(self.btn_options_selected)
        self.ui.btn_replace.clicked.connect(self.btn_options_selected)
        self.ui.btn_add.clicked.connect(self.btn_options_selected)

        self.load_materials()
        self.populate_list_materials()

    def closeEvent(self, event):
        self.materials_return.emit()
        super().closeEvent(event)

    def setup_position(self):
        x = self.parent.pos().x() + self.parent.width() // 2 - self.width() // 2
        y = self.parent.pos().y() + self.parent.height() // 2 - self.height() // 2
        self.move(x, y)

    def load_materials(self):
        file = open('database.db', 'rb')
        self.database = pickle.load(file)
        file.close()

    def populate_list_materials(self):
        self.material_names = list(self.database.keys())
        self.ui.listWidget.blockSignals(True)
        self.ui.listWidget.clear()
        self.ui.listWidget.addItems(self.material_names)
        self.ui.listWidget.blockSignals(False)

    def material_selected(self):
        self.selected = self.ui.listWidget.currentItem().text()

        if len(self.selected) > 0:
            self.ui.lineEdit.setText(self.selected)
            data = self.database[self.selected]
            columns = list(data.keys())
            self.ui.tableWidget.setColumnCount(len(columns))
            self.ui.tableWidget.setHorizontalHeaderLabels(columns)
            self.ui.tableWidget.setRowCount(1)
            self.ui.tableWidget.setVerticalHeaderLabels(['Value'])
            for i, column in enumerate(columns):
                value = data[column]
                self.ui.tableWidget.setItem(0, i, QtWidgets.QTableWidgetItem(str(value)))
        else:
            self.ui.lineEdit.clear()
            self.ui.tableWidget.clear()
            self.ui.tableWidget.setColumnCount(0)
            self.ui.tableWidget.setRowCount(0)

    def btn_options_selected(self):
        sender = self.sender().objectName()
        name = self.ui.lineEdit.text()

        if name == '':
            self.ui.label_status.setStyleSheet("color: #ff5555;")
            QTimer.singleShot(0, lambda: self.ui.label_status.setText('No name added'))
            QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))
            return

        else:
            if sender == 'btn_add':
                if name in self.database.keys():
                    self.ui.label_status.setStyleSheet("color: #ff5555;")
                    QTimer.singleShot(0, lambda: self.ui.label_status.setText('Name already exists'))
                    QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))
                    return
                else:
                    self.data_from_table()
                    self.database[name] = self.data_table

            elif sender == 'btn_replace':
                self.data_from_table()
                self.database[name] = self.data_table

            else:
                self.database.pop(name)

            self.update_list_materials()

            file = open('database.db', 'wb')
            pickle.dump(self.database, file)
            file.close()

    def data_from_table(self):
        model = self.ui.tableWidget.model()
        columns = model.columnCount()
        headers = [model.headerData(c, QtCore.Qt.Horizontal) for c in range(columns)]
        self.data_table = {}
        for i in range(columns):
            item = model.data(model.index(0, i))
            try:
                item = float(item)
            except:
                pass
            header = headers[i]
            self.data_table[header] = item

    def update_list_materials(self):
        list = [self.ui.listWidget.item(i).text() for i in range(self.ui.listWidget.count())]
        key = self.database.keys()
        for name in key:
            if name not in list:
                self.ui.listWidget.addItem(name)

        for i, name in enumerate(list):
            if name not in key:
                self.ui.listWidget.takeItem(i)
