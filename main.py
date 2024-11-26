import os
import sys

from module.core import *
from module.handlefile import HandleFiles
from module.rds import RDS
from ui.RbSrWindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.graphicsView.setBackground('w')
        self.ui.graphicsView.showGrid(x=True, y=True)
        self.ui.graphicsView.setLogMode(x=False, y=True)

        self.datafilespath = None   # path of all folders from imported folder
        self.logfile = None     # laser log file
        self.batchlog = None    # path of the icp-ms log file
        self.plotted = {}
        self.penDic = {}
        self.runselected = []

        self.handlefiles = HandleFiles(self.datafilespath, self.batchlog)
        self.RDS = RDS()

        self.ui.btn_add.clicked.connect(self.load_folder)
        self.ui.btn_log.clicked.connect(self.load_log)
        # self.ui.listWidget_names.itemSelectionChanged.connect(self.plot_data)
        # self.ui.listWidget_masses.itemSelectionChanged.connect(self.plot_data)
        self.ui.checkBox.clicked.connect(self.log_yaxis)
        self.ui.btn_export.clicked.connect(self.export_data)
        self.ui.radioButton_raw.clicked.connect(self.populate_table)
        self.ui.radioButton_DF.clicked.connect(self.populate_table)
        self.ui.radioButton_convertion.clicked.connect(self.populate_table)
        self.ui.radioButton_corrected.clicked.connect(self.populate_table)

    def load_folder(self):
        directory = tk.filedialog.askdirectory(title='Load Data Folder')

        if directory != '':
            if 'BatchLog.csv' in next(os.walk(directory))[2]:
                self.batchlog = pd.read_csv(os.path.join(directory, 'BatchLog.csv'))

            self.datafilespath = []
            folders = next(os.walk(directory))[1]
            for folder in folders:
                folderpath = os.path.join(directory, folder)
                files = next(os.walk(folderpath))[2]
                for file in files:
                    file_name, file_extension = os.path.splitext(file)
                    if file_extension == '.csv':
                        file_path = os.path.join(folderpath, file)
                        self.datafilespath.append(file_path)

            if len(self.datafilespath) > 0:
                self.handlefiles.datapath = self.datafilespath
                self.handlefiles.batchlog = self.batchlog
                self.handlefiles.open_datafiles()

                self.populate_list_masses()
                self.populate_list_names()
                self.reduction_scheme()

            else:
                print('ERROR')

    def load_log(self):
        file = tk.filedialog.askopenfilename(title='Load Log File', filetypes=[("CSV", "*.csv")])
        if file != '':
            extention = os.path.splitext(os.path.basename(file))[1]
            if extention == '.csv':
                self.logfile = pd.read_csv(file)
            else:
                print('ERROR')

    def export_data(self):
        pass
        # if len(self.handlefiles.alldatafiles.keys()) > 0:
        #     signal = self.signal.reindex(self.batchlog.loc[:, 'Sample Name'])
        #     background = self.background.reindex(self.batchlog.loc[:, 'Sample Name'])
        #     ratios = self.ratios.reindex(self.batchlog.loc[:, 'Sample Name'])
        #     convertion = self.convertion_rate.reindex(self.batchlog.loc[:, 'Sample Name'])
        #
        #     path = tk.filedialog.asksaveasfilename(title="Export Data", filetypes=[('Excel file', '*.xlsx')])
        #
        #     with pd.ExcelWriter(path + '.xlsx') as writer:
        #         signal.to_excel(writer, sheet_name='Average_signal', index=True)
        #         background.to_excel(writer, sheet_name='Average_background', index=True)
        #         ratios.to_excel(writer, sheet_name='ratio', index=True)
        #         convertion.to_excel(writer, sheet_name='Convertion_rate', index=True)

    def populate_list_names(self):
        self.ui.listWidget_names.blockSignals(True)
        self.ui.listWidget_names.clear()
        self.ui.listWidget_names.addItems(self.batchlog.loc[:, 'Sample Name'])
        self.ui.listWidget_names.blockSignals(False)
        self.ui.listWidget_names.setCurrentRow(0)

    def populate_list_masses(self):
        elements = self.handlefiles.data_head[1:]
        self.ui.listWidget_masses.blockSignals(True)
        self.ui.listWidget_masses.clear()
        self.ui.listWidget_masses.addItems(elements)
        self.ui.listWidget_masses.blockSignals(False)

    def populate_table(self):
        if self.ui.radioButton_DF.isChecked():
            if len(self.RDS.DF_data) > 0:
                self.ui.tableWidget.clear()
                self.ui.tableWidget.setColumnCount(1)
                self.ui.tableWidget.setRowCount(len(self.RDS.DF_data))
                columns = self.RDS.DF_data.columns.to_list()
                rows = self.RDS.DF_data.index.to_list()
                self.ui.tableWidget.setHorizontalHeaderLabels(columns)
                self.ui.tableWidget.setVerticalHeaderLabels(rows)
                for i, row in enumerate(rows):
                    value = str(round(self.RDS.DF_data.loc[row, 'Convertion rate'], 2))
                    self.ui.tableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(value))

                # Change plot to df pattern and check list selection

        if self.ui.radioButton_convertion.isChecked():
            if len(self.RDS.convertion_rate_data) > 0:
                self.ui.tableWidget.clear()
                self.ui.tableWidget.setColumnCount(1)
                self.ui.tableWidget.setRowCount(len(self.RDS.convertion_rate_data))
                columns = self.RDS.convertion_rate_data.columns.to_list()
                rows = self.RDS.convertion_rate_data.index.to_list()
                self.ui.tableWidget.setHorizontalHeaderLabels(columns)
                self.ui.tableWidget.setVerticalHeaderLabels(rows)
                for i, row in enumerate(rows):
                    value = str(round(self.RDS.convertion_rate_data.loc[row, 'Convertion rate'], 2))
                    self.ui.tableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(value))

        if self.ui.radioButton_raw.isChecked():
            if len(self.RDS.ratios_data) > 0:
                self.ui.tableWidget.clear()

                # Check list selection

    def plot_data(self):
        def _colorgen(run):
            color = "#" + ''.join([random.choice('ABCDE0123456789') for i in range(6)])
            if run not in self.penDic.keys():
                self.penDic[run] = color

        selectedruns = [item.text() for item in self.ui.listWidget.selectedItems()]
        for run in selectedruns:
            data = self.handlefiles.alldatafiles[run]
            mass = self.ui.comboBox_mass.currentText()
            xdata = data.loc[:, data.columns[0]]
            ydata = data.loc[:, mass]

            if run in self.plotted.keys():
                plot = self.plotted[run]
                plot.setData(xdata, ydata)
            else:
                _colorgen(run)
                pen = pg.mkPen(color=self.penDic[run], width=2)
                plot = self.ui.graphicsView.plot(xdata, ydata, pen=pen)
                self.plotted[run] = plot
        for run in self.runselected:
            if run not in selectedruns:
                self.ui.graphicsView.removeItem(self.plotted[run])
                self.plotted.pop(run)
        self.runselected = selectedruns

    def log_yaxis(self):
        if self.ui.checkBox.isChecked():
            self.ui.graphicsView.setLogMode(x=False, y=True)
        else:
            self.ui.graphicsView.setLogMode(x=False, y=False)

    def reduction_scheme(self):
        Rb_85 = self.ui.lineEdit_85Rb.text()
        Sr_86 = self.ui.lineEdit_86Sr.text()
        Sr_87 = self.ui.lineEdit_87Sr.text()
        Sr_88 = self.ui.lineEdit_88Sr.text()

        self.RDS.background(self.handlefiles.alldatafiles, Sr_88)
        self.RDS.background_subtraction()
        self.RDS.Rb_calculation()
        self.RDS.raw_ratios(Sr_86, Sr_87, Sr_88)

        if self.ui.checkBox_convertion.isChecked():
            self.RDS.convertion_rate(Sr_88)
        if self.ui.checkBox_DF.isChecked():
            self.RDS.downhole_fractionation()
        if self.ui.checkBox_massbias.isChecked():
            pass
        if self.ui.checkBox_drift.isChecked():
            pass
        if self.ui.checkBox_fractionation.isChecked():
            pass
        if self.ui.checkBox_SD.isChecked():
            pass
        if self.ui.checkBox_SE.isChecked():
            pass
        if self.ui.checkBox_RSD.isChecked():
            pass

        self.populate_table()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())