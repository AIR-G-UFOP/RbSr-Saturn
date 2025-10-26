from module.core import *
from ui.exportDataDialog import Ui_ExportDataDialog

class ExportDataDialog(QDialog):
    export_return = pyqtSignal(bool, dict)

    def __init__(self, parent, groups, channels):
        super(ExportDataDialog, self).__init__(parent)

        self.ui = Ui_ExportDataDialog()
        self.ui.setupUi(self)

        self.parent = parent
        self.setParent(parent)
        self.groups = groups
        self.channels = channels
        self.menu_opt = None
        self.actions = []
        self.clear = None
        self.selected_groups = []
        self.selected_channels = []

        self.setup_position()
        self.ui.menu_groups.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.ui.menu_channels.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        self.ui.btn_ok.clicked.connect(self.btn_clicked)
        self.ui.btn_cancel.clicked.connect(self.btn_clicked)
        self.ui.menu_groups.clicked.connect(self.get_groups)
        self.ui.menu_channels.clicked.connect(self.get_channels)

    def closeEvent(self, event):
        if self.sender().objectName() != 'btn_ok' and self.sender().objectName() != 'btn_cancel':
            self.export_return.emit(False, {})
        self.close()

    def setup_position(self):
        x = self.parent.pos().x() + self.parent.width() // 2 - self.width() // 2
        y = self.parent.pos().y() + self.parent.height() // 2 - self.height() // 2
        self.move(x, y)

    def btn_clicked(self):
        sender = self.sender().objectName()
        opts = self.get_opts()
        if sender == 'btn_ok':
            self.export_return.emit(True, opts)
        elif sender == 'btn_cancel':
            self.export_return.emit(False, opts)
        self.close()

    def setup_menu(self, opt):
        if opt == 'Groups':
            names = self.groups.keys()
        else:
            names = self.channels

        menu = QtWidgets.QMenu(self)
        self.actions = []
        for name in names:
            checkB = QtWidgets.QCheckBox(name)
            checkB.stateChanged.connect(self.update_selection)
            action = QtWidgets.QWidgetAction(menu)
            action.setDefaultWidget(checkB)
            menu.addAction(action)
            self.actions.append(checkB)
        return menu

    def get_groups(self):
        self.menu_opt = 'Groups'
        menu = self.setup_menu(self.menu_opt)
        self.ui.menu_groups.setMenu(menu)

    def get_channels(self):
        self.menu_opt = 'Channels'
        menu = self.setup_menu(self.menu_opt)
        self.ui.menu_channels.setMenu(menu)

    def update_selection(self):
        if self.menu_opt == 'Groups':
            lineedit = self.ui.lineEdit_groups
            placeholder = "Select groups using the menu to the right"
        elif self.menu_opt == 'Channels':
            lineedit = self.ui.lineEdit_channels
            placeholder = "Select channels using the menu to the right"

        selected = [action.text() for action in self.actions if action.isChecked()]
        if selected:
            lineedit.setText("; ".join(selected))
        else:
            lineedit.setText("")
            lineedit.setPlaceholderText(placeholder)

        if self.menu_opt == 'Groups':
            self.selected_groups = selected
        elif self.menu_opt == 'Channels':
            self.selected_channels = selected

    def get_opts(self):
        return {'Time Series': self.ui.checkBox_raw.isChecked(),
                'Signal': self.ui.checkBox_signal.isChecked(),
                'Results': self.ui.checkBox_results.isChecked(),
                'Groups': self.selected_groups,
                'Channels': self.selected_channels}
