import os.path
from module.core import *
from module.utils import get_log_name, get_unique_name
from ui.GroupDialog import Ui_GroupDialog


class GroupDialog(QDialog):
    group_return = pyqtSignal(dict)

    def __init__(self, parent, run_names, database, name_links, log_names):
        super(GroupDialog, self).__init__(parent)

        self.parent = parent
        self.ui = Ui_GroupDialog()
        self.ui.setupUi(self)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        title = "Group selection"
        self.setWindowTitle(title)

        self.setup_position()
        self.setParent(parent)

        self.ui.btn_group.setDefault(False)
        self.ui.btn_ok.setDefault(True)
        self.ui.btn_group.setDefault(False)

        self.ui.btn_group.clicked.connect(self.create_group)
        self.ui.btn_ok.clicked.connect(self.close_dialog)
        self.ui.btn_cancel.clicked.connect(self.close_dialog)
        self.ui.lineEdit_search.textChanged.connect(self.search)
        self.ui.listWidget.itemSelectionChanged.connect(self.extract_text)

        self.defined_groups = {}
        self.run_names = run_names
        self.database = database
        self.name_links = name_links
        self.log_names = log_names

        self.populate_list_and_combo()

    def keyPressEvent(self, event):
        if event.type() == QEvent.KeyPress:
            if event.modifiers() & Qt.ControlModifier:
                if event.key() == Qt.Key_A:
                    self.select_visible()

    def setup_position(self):
        x = self.parent.pos().x() + self.parent.width() // 2 - self.width() // 2
        y = self.parent.pos().y() + self.parent.height() // 2 - self.height() // 2
        self.move(x, y)

    def close_dialog(self):
        sender = self.sender().objectName()

        if sender == "btn_ok":
            self.group_return.emit(self.defined_groups)
        else:
            self.group_return.emit({})

        self.close()

    def populate_list_and_combo(self):
        names = get_log_name(self.name_links, self.run_names, self.log_names)
        self.ui.listWidget.addItems(names)
        self.ui.comboBox_name.addItems(self.database.keys())

    def create_group(self):
        items = [item.text() for item in self.ui.listWidget.selectedItems() if not item.isHidden()]
        items = get_unique_name(self.name_links, items)
        name = self.ui.comboBox_name.currentText()

        if items:
            self.defined_groups[name] = items
            self.ui.listWidget.clearSelection()
            self.ui.label_status.setStyleSheet('color: black')
            QTimer.singleShot(0, lambda: self.ui.label_status.setText(f'Group {name} created'))
            QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))
        else:
            self.ui.label_status.setStyleSheet("color: #ff5555;")
            QTimer.singleShot(0, lambda: self.ui.label_status.setText('Group failed'))
            QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))

    def search(self):
       text = self.ui.lineEdit_search.text()

       for i in range(self.ui.listWidget.count()):
           item = self.ui.listWidget.item(i)
           item.setHidden(text.lower() not in item.text().lower())

    def select_visible(self):
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            if not item.isHidden():
                item.setSelected(True)

    def extract_text(self):
        selections_text = [item.text() for item in self.ui.listWidget.selectedItems()]
        common = os.path.commonprefix(selections_text)
        self.ui.comboBox_name.setCurrentText(common)

