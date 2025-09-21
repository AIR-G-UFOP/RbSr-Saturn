import numpy as np

from module.core import *
from module.utils import get_unique_name
from ui.driftDialog import Ui_Drift


class DriftDialog(QDialog):
    drift_return = pyqtSignal(bool)

    def __init__(self, parent, DRS, database, groups, method, rm, all_names, link):
        super(DriftDialog, self).__init__(parent)

        self.ui = Ui_Drift()
        self.ui.setupUi(self)

        self.parent = parent
        self.setParent(parent)

        self.setup_position()

        self.ui.graphicsView.setBackground('w')
        self.ui.graphicsView.showGrid(x=True, y=True)
        self.ui.comboBox_method.setCurrentText(method)

        self.groups = groups
        self.DRS = DRS
        self.database = database
        self.all_names = all_names
        self.links = link
        self.factors = None
        self.x = None
        self.y = None
        self.drift_applied = False

        self.fill_combobox()
        self.ui.comboBox_rm.setCurrentText(rm)
        self.ui.comboBox_method.setCurrentText(method)

        if method == 'Smoothing spline':
            self.ui.spinBox_smoothing.setEnabled(True)
            self.ui.label_smoothing.setEnabled(True)
        elif method == 'Polynomial':
            self.ui.comboBox_degree.setEnabled(True)
            self.ui.label_degree.setEnabled(True)

        self.ui.comboBox_rm.currentTextChanged.connect(self.interpolate_drift)
        self.ui.comboBox_method.currentTextChanged.connect(self.interpolate_drift)
        self.ui.comboBox_degree.currentTextChanged.connect(self.interpolate_drift)
        self.ui.spinBox_smoothing.textChanged.connect(self.interpolate_drift)
        self.ui.btn_apply.clicked.connect(self.apply_correction)
        self.ui.btn_proceed.clicked.connect(self.btn_clicked)
        self.ui.btn_cancel.clicked.connect(self.btn_clicked)

        self.interpolate_drift()

    def closeEvent(self, event):
        if self.sender().objectName() != 'btn_cancel' and self.sender().objectName() != 'btn_proceed':
            self.drift_return_return.emit(False)
        self.close()

    def setup_position(self):
        x = self.parent.pos().x() + self.parent.width() // 2 - self.width() // 2
        y = self.parent.pos().y() + self.parent.height() // 2 - self.height() // 2
        self.move(x, y)

    def fill_combobox(self):
        self.ui.comboBox_rm.clear()
        self.ui.comboBox_rm.addItems(self.database.keys())

    def check_method(self, method):
        if method == 'Smoothing spline':
            self.ui.spinBox_smoothing.setEnabled(True)
            self.ui.label_smoothing.setEnabled(True)
            self.ui.comboBox_degree.setEnabled(False)
            self.ui.label_degree.setEnabled(False)

        elif method == 'Polynomial':
            self.ui.comboBox_degree.setEnabled(True)
            self.ui.label_degree.setEnabled(True)
            self.ui.spinBox_smoothing.setEnabled(False)
            self.ui.label_smoothing.setEnabled(False)

        else:
            self.ui.comboBox_degree.setEnabled(False)
            self.ui.label_degree.setEnabled(False)
            self.ui.spinBox_smoothing.setEnabled(False)
            self.ui.label_smoothing.setEnabled(False)

    def btn_clicked(self):
        btn = self.sender().objectName()

        if btn == 'btn_cancel':
            self.drift_return.emit(False)
        else:
            self.drift_return.emit(self.drift_applied)

        self.close()

    def plot_data(self):
        def _calc_y_model(mtd, dg, r):
            if mtd == 'Polynomial':
                y = []
                for x in self.x:
                    y_i = 0
                    for i, f_i in enumerate(self.factors[r]):
                        y_i += f_i * x ** (dg - i)
                    y.append(y_i)
                return np.array(y)
            else:
                spline = self.factors[r]
                return spline(self.x)

        method = self.ui.comboBox_method.currentText()
        rm = self.ui.comboBox_rm.currentText()
        degree = int(self.ui.comboBox_degree.currentText())
        db = self.database[rm]

        self.ui.graphicsView.clear()
        view = self.ui.graphicsView
        layout = pg.GraphicsLayout()
        view.setCentralItem(layout)
        view.show()

        for i, ratio in enumerate(['Rb87/Sr86', 'Sr87/Sr86']):
            true_value = db[ratio]
            plotR = layout.addPlot(row=i, col=0, labels={'left': ratio})
            error = pg.ErrorBarItem(x=self.x, y=self.y[ratio], top=self.y_std[ratio], bottom=self.y_std[ratio], beam=0.5)
            plotR.addItem(error)
            true = pg.InfiniteLine(movable=False, angle=0, pen='g', pos=true_value,
                                   label=f'True value: {true_value:.2f}',
                                   labelOpts={'rotateAxis': [1, 0], 'movable': False, 'color': 'g', 'position': 0.9}
                                   )
            plotR.addItem(true)
            plotR.addLegend(offset=(1, 0.1))
            plotR.plot(self.x, self.y[ratio], pen=None, symbol='o', symbolBrush='k', name=ratio + ' ± ' + 'std')

            if method == 'Average':
                f = self.factors[ratio]
                if f < 1:
                    angle = -90
                else:
                    angle = 90
                for i, x_i in enumerate(self.x):
                    y_i = self.y[ratio][i]
                    new_y = f * y_i  # scaled value
                    # Draw a line in plot coordinates
                    plotR.plot([x_i, x_i], [y_i, new_y], pen=pg.mkPen('r'))
                    # Add arrowhead at the new point
                    arrow = pg.ArrowItem(angle=angle, headLen=4, headWidth=4, brush='r', pen='r')
                    arrow.setPos(x_i, new_y)
                    plotR.addItem(arrow)
                    if i == 0:
                        label = pg.TextItem(text=f"Correction: {f:.2f}", color="r", anchor=(0, .5))
                        label.setPos(x_i, (new_y + y_i)/2)
                        plotR.addItem(label)
            else:
                y = _calc_y_model(method, degree, ratio)
                if method == 'Polynomial':
                    name = 'Polynomial ' + str(degree)
                else:
                    name = 'Spline'
                plotR.plot(self.x, y, pen='r', name=name)

    def interpolate_drift(self):
        method = self.ui.comboBox_method.currentText()
        rm = self.ui.comboBox_rm.currentText()
        degree = int(self.ui.comboBox_degree.currentText())
        s = self.ui.spinBox_smoothing.value()

        self.check_method(method)

        if method == 'Average':
            self.factors, self.x, self.y, self.y_std = self.DRS.average_factor(self.groups, rm, self.database,
                                                                               self.all_names, self.links)
        elif method == 'Polynomial':
            self.factors, self.x, self.y, self.y_std = self.DRS.polynomial_factor(self.groups, rm, self.all_names,
                                                                                  degree, self.links)
        else:
            self.factors, self.x, self.y, self.y_std = self.DRS.spline_factor(self.groups, rm, self.all_names, s,
                                                                              self.links)

        self.plot_data()

    def plot_data_corrected(self):
        rm = self.ui.comboBox_rm.currentText()
        db = self.database[rm]
        selections = self.groups[rm]

        self.ui.graphicsView.clear()
        view = self.ui.graphicsView
        layout = pg.GraphicsLayout()
        view.setCentralItem(layout)
        view.show()

        for i, ratio in enumerate(['Rb87/Sr86', 'Sr87/Sr86']):
            true_value = db[ratio]
            ratioCorr = ratio + '_drift'

            y = []
            y_std = []
            for name in selections:
                y_i = self.DRS.intermediate_data[name][ratioCorr].mean()
                y_std_i = self.DRS.intermediate_data[name][ratioCorr].std()
                y.append(y_i)
                y_std.append(y_std_i)
            y = np.array(y)
            y_std = np.array(y_std)

            plotR = layout.addPlot(row=i, col=0, labels={'left': ratioCorr})
            error = pg.ErrorBarItem(x=self.x, y=y, top=y_std, bottom=y_std, beam=0.5)
            plotR.addItem(error)
            true = pg.InfiniteLine(movable=False, angle=0, pen='g', pos=true_value,
                                   label=f'True value: {true_value:.2f}',
                                   labelOpts={'rotateAxis': [1, 0], 'movable': False, 'color': 'g', 'position': 0.9}
                                   )
            plotR.addItem(true)
            plotR.addLegend(offset=(1, 0.1))
            plotR.plot(self.x, y, pen=None, symbol='o', symbolBrush='g', name=ratioCorr + ' ± ' + 'std')

    def apply_correction(self):
        method = self.ui.comboBox_method.currentText()
        degree = int(self.ui.comboBox_degree.currentText())
        rm = self.ui.comboBox_rm.currentText()
        true_values = self.database[rm]

        self.DRS.drift_correction(method, self.groups, self.factors, degree, true_values, self.all_names, self.links)
        self.drift_applied = True

        self.plot_data_corrected()
