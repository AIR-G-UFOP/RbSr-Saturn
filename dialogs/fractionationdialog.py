from module.core import *
from module.utils import get_unique_name, get_log_name
from ui.FractionationDialog import Ui_Fractionation


class FractionationDialog(QDialog):
    fractionation_return = pyqtSignal(bool)

    def __init__(self, parent, groups, DRS, method, handlelog):
        super(FractionationDialog, self).__init__(parent)

        self.ui = Ui_Fractionation()
        self.ui.setupUi(self)

        self.parent = parent
        self.setParent(parent)

        self.setup_position()

        self.ui.graphicsView.setBackground('w')
        self.ui.graphicsView.showGrid(x=True, y=True)
        self.ui.graphicsView.setLabel('left', '87Rb/86Sr fractionation')
        self.ui.graphicsView.setLabel('bottom', 'Time (sec)')
        self.ui.comboBox_method.setCurrentText(method)

        if method == 'Smoothing spline':
            self.ui.spinBox_smoothing.setEnabled(True)
            self.ui.label_smoothing.setEnabled(True)

        self.groups = groups
        self.DRS = DRS
        self.handlelog = handlelog
        self.parameters = None
        self.cov = None
        self.selections_mean_r = None
        self.selections_mean_t = None
        self.frac_applied = False

        self.ui.btn_cancel.clicked.connect(self.btn_clicked)
        self.ui.btn_proceed.clicked.connect(self.btn_clicked)
        self.ui.comboBox_group.textActivated.connect(self.interpolate_data)
        self.ui.comboBox_method.textActivated.connect(self.interpolate_data)
        self.ui.spinBox_smoothing.textChanged.connect(self.interpolate_data)
        self.ui.btn_applyModel.clicked.connect(self.apply_model)

        self.fill_combobox_groups()
        self.interpolate_data()

    def closeEvent(self, event):
        if self.sender().objectName() != 'btn_cancel' and self.sender().objectName() != 'btn_proceed':
            self.fractionation_return.emit(False)
        self.close()

    def setup_position(self):
        x = self.parent.pos().x() + self.parent.width() // 2 - self.width() // 2
        y = self.parent.pos().y() + self.parent.height() // 2 - self.height() // 2
        self.move(x, y)

    def btn_clicked(self):
        btn = self.sender().objectName()

        if btn == 'btn_cancel':
            self.fractionation_return.emit(False)
        else:
            self.fractionation_return.emit(self.frac_applied)

        self.close()

    def fill_combobox_groups(self):
        self.ui.comboBox_group.clear()
        self.ui.comboBox_group.addItems(self.groups.keys())

    def _calc_y_interp(self, x, method):
            if method == 'Exponential':
                return self.parameters[0] + self.parameters[1] * np.exp(-self.parameters[2] * x)
            elif method == 'Linear':
               return self.parameters[0] + self.parameters[1] * x
            elif method == 'Linear+exponential':
                return self.parameters[0] + self.parameters[1]*x + self.parameters[2]*np.exp(-self.parameters[3]*x)
            elif method == 'Smoothing spline':
                return self.parameters(x)

    def plot_data(self):
        group = self.ui.comboBox_group.currentText()
        group_selections = self.groups[group]
        group_selections_show = get_log_name(self.handlelog.name_links, group_selections, self.handlelog.names_log)
        method = self.ui.comboBox_method.currentText()

        self.ui.graphicsView.clear()
        legend = self.ui.graphicsView.addLegend(offset=(-1, 1), labelTextColor='k')

        for i, name in enumerate(group_selections):
            selection_data = self.DRS.intermediate_data[name]
            x = selection_data.iloc[:, 0].to_numpy()
            y = selection_data.loc[:, 'Rb87/Sr86_raw'].to_numpy()
            self.ui.graphicsView.plot(x, y, name=group_selections_show[i])

        x_mean = self.selections_mean_t
        y_mean = self.selections_mean_r
        y_interp = self._calc_y_interp(x_mean, method)
        self.ui.graphicsView.plot(x_mean, y_mean, pen=pg.mkPen(color='black', width=1), name=group + '_mean')
        self.ui.graphicsView.plot(x_mean, y_interp, pen=pg.mkPen(color='red', width=1), name=group + '_DF')

    def plot_data_corrected(self):
        group = self.ui.comboBox_group.currentText()
        group_selections = self.groups[group]

        self.ui.graphicsView.clear()
        for i, name in enumerate(group_selections):
            selection_data = self.DRS.intermediate_data[name]
            x = selection_data.iloc[:, 0].to_numpy()
            y_corr = selection_data.loc[:, 'Rb87/Sr86_DFcorr'].to_numpy()
            y_uncorr = selection_data.loc[:, 'Rb87/Sr86_raw'].to_numpy()
            self.ui.graphicsView.plot(x, y_corr, pen=pg.mkPen(color='green', width=1))
            self.ui.graphicsView.plot(x, y_uncorr)

    def interpolate_data(self):
        group = self.ui.comboBox_group.currentText()
        group_selections = self.groups[group]
        method = self.ui.comboBox_method.currentText()
        s = self.ui.spinBox_smoothing.value()

        if method == 'Smoothing spline':
            self.ui.spinBox_smoothing.setEnabled(True)
            self.ui.label_smoothing.setEnabled(True)
        else:
            self.ui.spinBox_smoothing.setEnabled(False)
            self.ui.label_smoothing.setEnabled(False)

        self.parameters, self.cov, self.selections_mean_t, self.selections_mean_r = self.DRS.downhole_fractionation(group_selections, method, s)

        self.ui.lineEdit_parameterA.clear()
        self.ui.lineEdit_parameterB.clear()
        self.ui.lineEdit_parameterC.clear()
        self.ui.lineEdit_parameterD.clear()
        try:
            self.ui.lineEdit_parameterC.setText(str(self.parameters[2]))
            self.ui.lineEdit_parameterA.setText(str(self.parameters[0]))
            self.ui.lineEdit_parameterB.setText(str(self.parameters[1]))
            self.ui.lineEdit_parameterD.setText(str(self.parameters[3]))
        except (IndexError, TypeError):
            pass

        self.plot_data()

    def apply_model(self):
        selections = self.groups[self.ui.comboBox_group.currentText()]
        method = self.ui.comboBox_method.currentText()
        self.DRS.downhole_fractionation_correction(selections, method, self.parameters)
        self.frac_applied = True

        self.plot_data_corrected()
