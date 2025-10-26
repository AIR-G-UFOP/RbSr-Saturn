import os
import pickle
import re
import sys

import pandas as pd

from widgets import *
from module.core import *
from module.handlefile import HandleFiles
from module.handlelog import HandleLog
from module.utils import *
from module.drs import DRS
from ui.RbSrMainWindow import Ui_MainWindow
from dialogs.groupdialog import GroupDialog
from dialogs.materialsdialog import MaterialsDialog
from widgets.overlaywidget import LoadingOverlay
from dialogs.fractionationdialog import FractionationDialog
from dialogs.driftdialog import DriftDialog
from dialogs.signaldialog import SignalDialog
from dialogs.exportDataDialog import ExportDataDialog

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setWindowTitle("Rb-Sr Data Reduction")

        self.ui.graphicsView.setBackground('w')
        self.ui.graphicsView.showGrid(x=True, y=True)

        self.subScheme = None
        self.subTable = None
        self.subPlot = None
        self.subLists = None
        self.logfile = None     # laser log file
        self.plotted = {}
        self.penDic = {}
        self.runselected = []
        self.previous_runselected = []
        self.mselected = []
        self.previous_mselected = []
        self.globalcounter = 0  # to account for the number os data folder/file opened
        self.database = {}
        self.groups = {}
        self.gases = {'SF6': ['Rb85', 'Sr105', 'Sr106', 'Sr107'],
                      'O2': ['Rb85', 'Sr102', 'Sr103', 'Sr104'],
                      'N2O': ['Rb85', 'Sr102', 'Sr103', 'Sr104']}
        self.signal = False

        self.handlefiles = HandleFiles()
        self.handlelog = HandleLog()
        self.DRS = DRS()
        self.overlay = LoadingOverlay(self.ui.bgApp)
        self.overlay.hide()

        self.ui.btn_add.clicked.connect(self.load_folder)
        self.ui.btn_log.clicked.connect(self.load_log)
        self.ui.btn_new.clicked.connect(self.restart_app)
        self.ui.btn_addfile.clicked.connect(self.load_file)
        self.ui.btn_export.clicked.connect(self.open_exportDataDialog)
        self.ui.btn_signal.clicked.connect(self.open_signalDialog)
        self.ui.btn_RM.clicked.connect(self.open_materialsDialog)

        self.ui.listWidget_names.viewport().installEventFilter(self)
        self.ui.listWidget_masses.viewport().installEventFilter(self)
        self.ui.runSelectionMode.clicked.connect(self.lists_selection_mode)
        self.ui.massSelectionMode.clicked.connect(self.lists_selection_mode)
        self.ui.btn_groups.clicked.connect(self.open_groupDialog)
        self.ui.btn_run.clicked.connect(self.check_reduction_scheme)
        self.ui.checkBox_matrix.toggled.connect(self.check_drift_option)

        self.setupSubWindows()
        self.load_reference_material()

        # reference = {
        #     'NIST610': {'Sr87/Sr86': 0.79699, 'Sr87/Sr86_unc': 0.000018, 'Rb87/Sr86': 2.33, 'Rb87/Sr86_unc': 0.00049,
        #                 'Sr87/Sr86_i': '', 'Sr87/Sr86_i_unc': '', 'Age': '', 'Age_unc': ''},
        #     'MICAMG': {'Sr87/Sr86': 1.8525, 'Sr87/Sr86_unc': 0.0024, 'Rb87/Sr86': 154.6, 'Rb87/Sr86_unc': 1.93,
        #                'Sr87/Sr86_i': 0.72607, 'Sr87/Sr86_i_unc': 0.0007, 'Age': 519.4, 'Age_unc': 6.5}
        # }
        #
        # file = open('database.db', 'wb')
        # pickle.dump(reference, file)
        # file.close()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == QtCore.Qt.LeftButton:
                if self.ui.listWidget_names.viewport() == obj:
                    selected = self.ui.listWidget_names.selectedItems()
                    self.select_list_names(selected)
                elif self.ui.listWidget_masses.viewport() == obj:
                    selected = self.ui.listWidget_masses.selectedItems()
                    self.select_list_masses(selected)
                return super().eventFilter(obj, event)
        else:
            return super().eventFilter(obj, event)

    def setupSubWindows(self):
        def remove_buttons(obj, bts):
            flags = obj.windowFlags()
            for bt in bts:
                if bt == 'close':
                    flags &= ~Qt.WindowCloseButtonHint
                    obj.setWindowFlags(flags)
                elif bt == 'minimise':
                    flags &= ~Qt.WindowMinimizeButtonHint
                    obj.setWindowFlags(flags)
                elif bt == 'maximise':
                    flags &= ~Qt.WindowMaximizeButtonHint
                    obj.setWindowFlags(flags)

        self.subScheme = self.ui.mdiArea.addSubWindow(self.ui.subwindowScheme)
        remove_buttons(self.subScheme, ['maximise'])
        self.subScheme.setAttribute(Qt.WA_DeleteOnClose, False)
        self.subScheme.resize(320, 425)
        self.subScheme.show()
        self.subScheme.move(0, 0)

        self.subTable = self.ui.mdiArea.addSubWindow(self.ui.subwindowTable)
        remove_buttons(self.subTable, ['close'])
        self.subTable.setAttribute(Qt.WA_DeleteOnClose, False)
        self.subTable.resize(775, 340)
        self.subTable.show()
        self.subTable.move(345, 430)

        self.subPlot = self.ui.mdiArea.addSubWindow(self.ui.subwindowPlot)
        remove_buttons(self.subPlot, ['close'])
        self.subPlot.setAttribute(Qt.WA_DeleteOnClose, False)
        self.subPlot.resize(690, 425)
        self.subPlot.show()
        self.subPlot.move(325, 0)

        self.subLists = self.ui.mdiArea.addSubWindow(self.ui.subwindowLists)
        remove_buttons(self.subLists, ['maximise', 'close'])
        self.subLists.setAttribute(Qt.WA_DeleteOnClose, False)
        self.subLists.resize(340, 340)
        self.subLists.show()
        self.subLists.move(0, 430)

    def showSubwindows(self):
        sender_name = self.sender().objectName()

        if sender_name == 'btn_scheme':
            if self.subScheme.isHidden():
                self.subScheme.showNormal()
                self.subScheme.raise_()

        elif sender_name == 'btn_table':
            if self.subTable.isHidden():
                self.subTable.showNormal()
                self.subTable.raise_()

        elif sender_name == 'btn_plot':
            if self.subPlot.isHidden():
                self.subPlot.showNormal()
                self.subPlot.raise_()

        elif sender_name == 'btn_lists':
            if self.subLists.isHidden():
                self.subLists.showNormal()
                self.subLists.raise_()

    def check_drift_option(self):
        if self.ui.checkBox_matrix.isChecked():
            if not self.ui.checkBox_drift.isChecked():
                self.print_message('Matrix-effect correction can only be applied if drift correction is applied too')
                self.ui.checkBox_drift.setCheckState(Qt.Checked)

    def open_groupDialog(self):
        self.overlay.show()
        self.groupDialog = GroupDialog(self, self.handlefiles.run_names, self.database, self.handlelog.name_links,
                                       self.handlelog.names_log)
        self.groupDialog.setWindowModality(Qt.WindowModal)
        self.groupDialog.group_return.connect(self.return_groupDialog)
        self.groupDialog.show()

    @pyqtSlot(dict)
    def return_groupDialog(self, groups):
        self.overlay.hide()
        self.groups = groups

    def open_materialsDialog(self):
        self.overlay.show()
        self.materialsDialog = MaterialsDialog(self)
        self.materialsDialog.setWindowModality(Qt.WindowModal)
        self.materialsDialog.materials_return.connect(self.return_materialsDialog)
        self.materialsDialog.show()

    @pyqtSlot()
    def return_materialsDialog(self):
        self.overlay.hide()
        self.load_reference_material()

    def open_fractionationDialog(self, method):
        self.overlay.show()
        self.fractionationDialog = FractionationDialog(self, self.groups, self.DRS, method, self.handlelog)
        self.fractionationDialog.setWindowModality(Qt.WindowModal)
        self.fractionationDialog.fractionation_return.connect(self.return_fractionationDialog)
        self.fractionationDialog.exec_()

    @pyqtSlot(bool)
    def return_fractionationDialog(self, opt):
        self.overlay.hide()
        if not opt:
            self.ui.checkBox_fractionation.setCheckState(Qt.Unchecked)
            self.DRS.remove_correction('downhole', self.groups)
            return

    def open_driftDialog(self, method, rm):
        self.overlay.show()
        self.driftDialog = DriftDialog(self, self.DRS, self.database, self.groups, method, rm,
                                       self.handlefiles.run_names, self.handlelog.name_links)
        self.driftDialog.setWindowModality(Qt.WindowModal)
        self.driftDialog.drift_return.connect(self.return_driftDialog)
        self.driftDialog.exec_()

    @pyqtSlot(bool)
    def return_driftDialog(self, opt):
        self.overlay.hide()
        if not opt:
            self.ui.checkBox_drift.setCheckState(Qt.Unchecked)
            self.DRS.remove_correction('drift', self.groups)
            return

    def open_signalDialog(self):
        self.overlay.show()
        self.signalDialog = SignalDialog(self, self.handlefiles.alldatafiles, self.DRS.line_index,
                                         self.handlefiles.all_run_names, self.handlefiles.data_head, self.DRS.limits,
                                         self.handlelog.name_links, self.handlelog.names_log)
        self.signalDialog.signal_return.connect(self.return_signalDialog)
        self.signalDialog.setWindowModality(Qt.WindowModal)
        self.signalDialog.exec_()

    @pyqtSlot(bool, dict)
    def return_signalDialog(self, opt, new_limits):
        self.overlay.hide()
        self.DRS.limits = new_limits
        self.signal = opt
        if opt:
            if self.create_popup('Run Scheme?',
                                 'You have changed baseline/signal intervals.'
                                 '\nDo you want to run the reduction scheme?'):
                self.check_reduction_scheme()

    def open_exportDataDialog(self):
        self.overlay.show()
        self.exportDialog = ExportDataDialog(self, self.groups, self.handlefiles.data_head)
        self.exportDialog.setWindowModality(Qt.WindowModal)
        self.exportDialog.export_return.connect(self.return_exportDialog)
        self.exportDialog.exec_()

    @pyqtSlot(bool, dict)
    def return_exportDialog(self, status, opts):
        if status:
            self.export_data(opts)
        self.overlay.hide()

    def restart_app(self):
        self.close()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def load_reference_material(self):
        file = open('database.db', 'rb')
        self.database = pickle.load(file)
        file.close()

        self.ui.comboBox_rm.clear()
        self.ui.comboBox_rm2.clear()
        self.ui.comboBox_rm.addItems(self.database.keys())
        self.ui.comboBox_rm2.addItems(self.database.keys())

    def load_folder(self):
        directory = tk.filedialog.askdirectory(title='Load Data Folder')
        if directory != '':
            self.handlefiles.open_folders(directory)
            if len(self.handlefiles.datapath) > 0:
                self.globalcounter += 1
                self.handle_files()
            else:
                self.print_message('ERROR! Could not import folder')

    def load_file(self):
        filepath = tk.filedialog.askopenfilenames(title='Load Data File', filetypes=[("CSV", "*.csv")])
        if filepath != '':
            self.handlefiles.open_single_file(filepath)
            if self.handlefiles.datapath:
                self.handle_files()
            else:
                self.print_message('ERROR! Could not import file')

    def handle_files(self):
        self.handlefiles.counter = self.globalcounter
        self.handlefiles.open_data_files()
        self.populate_list_masses()
        self.populate_list_names()
        self.DRS.get_limits(self.handlefiles.alldatafiles, self.gases[self.ui.comboBoxGas.currentText()][3])

    def load_log(self):
        if len(self.handlefiles.alldatafiles.keys()) > 0:
            path = tk.filedialog.askopenfilename(title='Load Log File', filetypes=[("CSV", "*.csv")])
            if path != '':
                if self.handlelog.open_log_file(path):
                    self.handlelog.get_names_from_log()
                    if self.handlelog.names_log:
                        self.handlelog.link_unique_name_with_log(self.handlefiles.run_names)
                        new_names = get_log_name(self.handlelog.name_links, self.handlefiles.all_run_names,
                                                 self.handlelog.names_log)
                        self.ui.listWidget_names.clear()
                        self.ui.listWidget_names.addItems(new_names)
                        if self.runselected:
                            self.runselected = get_log_name(self.handlelog.name_links, self.runselected,
                                                            self.handlelog.names_log)
                            self.previous_runselected = get_log_name(self.handlelog.name_links,
                                                                     self.previous_runselected,
                                                                     self.handlelog.names_log)
                            for i in range(self.ui.listWidget_names.count()):
                                item = self.ui.listWidget_names.item(i)
                                if item.text() in self.runselected:
                                    item.setSelected(True)
                else:
                    self.print_message('ERROR! Could not import log file')
            else:
                self.print_message('ERROR! Could not import log file')

    def export_data(self, opts):
        if opts['Results']:
            if isinstance(self.DRS.results, pd.DataFrame):
                with pd.ExcelWriter('results.xlsx') as writer:
                    self.DRS.results.to_excel(writer, sheet_name='Data', index=True)
            else:
                self.print_message('No results to export.')
        if opts['Time Series']:
            if self.handlefiles.alldatafiles:
                # get selections and channels
                channels = opts['Channels']
                groups = opts['Groups']
                if groups:
                    selections = [selection for group in groups for selection in self.groups[group]]
                else:
                    selections = list(self.handlefiles.alldatafiles.keys())
                selections = get_log_name(self.handlelog.name_links,
                                                    selections,
                                                    self.handlelog.names_log)
                # get the path to save
                path = tk.filedialog.asksaveasfilename(title="Export Time Series Data",
                                                       filetypes=[('Excel file', '*.xlsx')])
                # save data to excel
                if path:
                    if not os.path.splitext(os.path.basename(path))[1] == '.xlsx':
                        path = path + '.xlsx'
                    with pd.ExcelWriter(path) as writer:
                        try:
                            for name, data in self.handlefiles.alldatafiles.items():
                                if not channels:
                                    channels = data.columns.to_list()
                                name = get_log_name(self.handlelog.name_links,
                                                    [name],
                                                    self.handlelog.names_log)[0]
                                if name in selections:
                                    data[channels].to_excel(writer, sheet_name=name, index=False)
                                    # applying style
                                    workbook = writer.book
                                    worksheet = writer.sheets[name]
                                    header_format = workbook.add_format({'bold': False, 'border': 0})
                                    for col in data.columns:
                                        if col in channels:
                                            worksheet.write(0, channels.index(col), col, header_format)
                        except Exception as error:
                            raise error
            else:
                self.print_message('No raw data to export.')
        if opts['Signal']:
            if self.DRS.signal_data_raw:
                # get selections and channels
                channels = opts['Channels']
                groups = opts['Groups']
                if groups:
                    selections = [selection for group in groups for selection in self.groups[group]]
                else:
                    selections = list(self.DRS.signal_data_raw.keys())
                selections = get_log_name(self.handlelog.name_links,
                                          selections,
                                          self.handlelog.names_log)
                # get the path to save
                path = tk.filedialog.asksaveasfilename(title="Export Signal Data", filetypes=[('Excel file', '*.xlsx')])
                # save data to excel
                if path:
                    if not os.path.splitext(os.path.basename(path))[1] == '.xlsx':
                        path = path + '.xlsx'
                    with pd.ExcelWriter(path) as writer:
                        try:
                            for name, data_sig in self.DRS.signal_data_raw.items():
                                mean_bkg = self.DRS.background_data_raw[name].mean(axis=0)
                                if not channels:
                                    channels = data_sig.columns.to_list()
                                name = get_log_name(self.handlelog.name_links,
                                                    [name],
                                                    self.handlelog.names_log)[0]
                                if name in selections:
                                    data_corr = data_sig[['Time [Sec]']].merge(data_sig[channels[1:]] - mean_bkg[channels[1:]], left_index=True, right_index=True, how='outer')
                                    data_corr.to_excel(writer, sheet_name=name, index=False)
                                    # applying style
                                    workbook = writer.book
                                    worksheet = writer.sheets[name]
                                    header_format = workbook.add_format({'bold': False, 'border': 0})
                                    for col in data_corr.columns:
                                        if col in channels:
                                            worksheet.write(0, channels.index(col), col, header_format)
                        except Exception as error:
                            raise error

    def populate_list_names(self):
        current_names = []
        for i in range(self.ui.listWidget_names.count()):
            current_names.append(self.ui.listWidget_names.item(i).text())
        for item in self.handlefiles.all_run_names:
            if item not in current_names:
                self.ui.listWidget_names.addItem(item)

    def populate_list_masses(self):
        masses = (self.handlefiles.data_head[1:] +
                  ['Rb87', 'Rb85/Sr86_raw', 'Sr87/Sr86_raw', 'Rb87/Sr86_raw', 'Sr87/Rb87_raw', 'Sr88/Sr86_raw',
                   'Rb87/Sr87_raw', 'Rb87/Sr86_DF', 'Rb87/Sr86_mb', 'Sr87/Sr86_mb', 'Rb87/Sr86_drift', 'Sr87/Sr86_drift'
                   ])
        self.ui.listWidget_masses.blockSignals(True)
        current_masses = []
        for i in range(self.ui.listWidget_masses.count()):
            current_masses.append(self.ui.listWidget_masses.item(i).text())
        for mass in masses:
            if mass not in current_masses:
                self.ui.listWidget_masses.addItem(mass)
        self.ui.listWidget_masses.blockSignals(False)

    def populate_table(self):
        def _deselect_opts(mode):
            if mode == 'single':
                for obj in self.ui.layoutAll.children():
                    if not isinstance(obj, QtWidgets.QLabel):
                        obj.blockSignals(True)
                        obj.setCheckState(Qt.Unchecked)
                        obj.blockSignals(False)
                if self.ui.checkBox_all.isChecked():
                    for obj in self.ui.layoutSingle.children():
                        if not isinstance(obj, QtWidgets.QLabel) or obj.objectName() != 'checkBox_all':
                            obj.blockSignals(True)
                            obj.setCheckState(Qt.Unchecked)
                            obj.blockSignals(False)
            else:
                if self.ui.checkBox_all.isChecked():
                    for obj in self.ui.singleModeBkg.children():
                        if not isinstance(obj, QtWidgets.QLabel):
                            obj.blockSignals(True)
                            obj.setCheckState(Qt.Unchecked)
                            obj.blockSignals(False)

        def _fill_table_single_mode(cols):
            if self.runselected:
                selected = get_unique_name(self.handlelog.name_links, self.runselected)
                name = selected[-1]
                if self.DRS.intermediate_data.keys():
                    self.ui.tableWidget.clear()
                    data = self.DRS.intermediate_data[name]
                    rows = data.iloc[:, 0].astype(str)
                    if len(cols) == 0:
                        cols = data.columns[1:].to_list()
                    else:
                        for col in cols.copy():
                            if col not in data.columns:
                                cols.remove(col)
                    self.ui.tableWidget.setColumnCount(len(cols))
                    self.ui.tableWidget.setRowCount(len(rows))
                    self.ui.tableWidget.setHorizontalHeaderLabels(cols)
                    self.ui.tableWidget.setVerticalHeaderLabels(rows)

                    for i, row in enumerate(data.index.to_list()):
                        for j, column in enumerate(cols):
                            value = str(round(data.loc[row, column], 4))
                            self.ui.tableWidget.setItem(i, j, QtWidgets.QTableWidgetItem(value))

        cols = []
        if self.ui.checkBox_rawRatios.isChecked():
            _deselect_opts('single')
            cols += ['Rb85/Sr86_raw', 'Sr87/Sr86_raw', 'Rb87/Sr86_raw', 'Sr87/Rb87_raw','Sr88/Sr86_raw',
                     'Rb87/Sr87_raw']
        if self.ui.checkBox_corrRatios.isChecked():
            _deselect_opts('single')
            cols += ['Rb87/Sr86_DFcorr', 'Sr87/Sr86_mb', 'Rb87/Sr86_mb', 'Sr87/Sr86_drift', 'Rb87/Sr86_drift',
                     'Rb87/Sr86_matrix']
        if self.ui.checkBox_all.isChecked():
            _deselect_opts('single')
        _fill_table_single_mode(cols)

        # NEEDS TO FINISH FOR THE RESULTS PART

        # if self.ui.checkBox_dfIndex.isChecked():
        #     try:
        #         if len(self.DRS.DF_data) > 0:
        #             self.ui.tableWidget.clear()
        #             columns = self.DRS.DF_data.columns.to_list()
        #             rows = self.DRS.DF_data.index.to_list()
        #             self.ui.tableWidget.setColumnCount(len(columns))
        #             self.ui.tableWidget.setRowCount(len(rows))
        #             self.ui.tableWidget.setHorizontalHeaderLabels(columns)
        #             self.ui.tableWidget.setVerticalHeaderLabels(rows)
        #             for i, row in enumerate(rows):
        #                 for j, column in enumerate(columns):
        #                     value = str(round(self.DRS.DF_data.loc[row, column], 2))
        #                     self.ui.tableWidget.setItem(i, j, QtWidgets.QTableWidgetItem(value))
        #     except TypeError as error:
        #         pass
        #
        # elif self.ui.checkBox_convertionRate.isChecked():
        #     try:
        #         if len(self.DRS.convertion_rate_data) > 0:
        #             self.ui.tableWidget.clear()
        #             self.ui.tableWidget.setColumnCount(1)
        #             self.ui.tableWidget.setRowCount(len(self.DRS.convertion_rate_data))
        #             columns = self.DRS.convertion_rate_data.columns.to_list()
        #             rows = self.DRS.convertion_rate_data.index.to_list()
        #             self.ui.tableWidget.setHorizontalHeaderLabels(columns)
        #             self.ui.tableWidget.setVerticalHeaderLabels(rows)
        #             for i, row in enumerate(rows):
        #                 value = str(round(self.DRS.convertion_rate_data.loc[row, 'Convertion rate'], 2))
        #                 self.ui.tableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(value))
        #     except TypeError as error:
        #         pass

    def select_list_names(self, selected):
        selected = [item.text() for item in selected]
        self.previous_runselected = self.runselected
        self.runselected = selected

        if len(self.runselected) == 0:
            self.ui.tableWidget.clear()
            self.ui.tableWidget.setRowCount(0)
            self.ui.tableWidget.setColumnCount(0)
            self.ui.graphicsView.clear()
            self.plotted = {}
        else:
            self.populate_table()
            if len(self.mselected) > 0:
                self.plot_data()
            else:
                self.ui.graphicsView.clear()
                self.plotted = {}

    def select_list_masses(self, selected):
        selected = [item.text() for item in selected]
        self.previous_mselected = self.mselected
        self.mselected = selected
        if len(self.mselected) > 0:
            if len(self.runselected) > 0:
                self.plot_data()
        else:
            self.ui.graphicsView.clear()
            self.plotted = {}

    def lists_selection_mode(self):
        sender = self.sender().objectName()
        self.ui.runSelectionMode.blockSignals(True)
        self.ui.massSelectionMode.blockSignals(True)

        if sender == 'runSelectioMode':
            self.ui.runSelectionMode.setEnabled(False)
            self.ui.listWidget_names.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

            self.ui.massSelectionMode.setChecked(False)
            self.ui.massSelectionMode.setEnabled(True)
            self.ui.listWidget_masses.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

            selected = self.ui.listWidget_masses.selectedItems()
            if len(selected) > 0:
                item = selected[-1]

                self.ui.listWidget_masses.clearSelection()
                self.ui.listWidget_masses.setCurrentItem(item)

                self.previous_mselected = self.mselected
                self.mselected = [item.text()]

        else:
            self.ui.massSelectionMode.setEnabled(False)
            self.ui.listWidget_masses.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

            self.ui.runSelectionMode.setChecked(False)
            self.ui.runSelectionMode.setEnabled(True)
            self.ui.listWidget_names.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

            selected = self.ui.listWidget_names.selectedItems()

            if len(selected) > 0:
                item = selected[-1]
                self.ui.listWidget_names.clearSelection()
                self.ui.listWidget_names.setCurrentItem(item)

                self.previous_runselected = self.runselected
                self.runselected = [item.text()]

        self.ui.runSelectionMode.blockSignals(False)
        self.ui.massSelectionMode.blockSignals(False)

        self.plot_data()

    def plot_data(self):
        def _colorgen(run, mass):
            color = "#" + ''.join([random.choice('ABCDE0123456789') for i in range(6)])
            if run in self.penDic.keys():
                mass_colour = self.penDic[run]
                if mass not in mass_colour.keys():
                    mass_colour[mass] = color
                    self.penDic[run] = mass_colour

            else:
                self.penDic[run] = {mass: color}

        def _plt():
            selected = get_unique_name(self.handlelog.name_links, self.runselected)
            previousselected = get_unique_name(self.handlelog.name_links, self.previous_runselected)
            legend = self.ui.graphicsView.addLegend(offset=(-1, 1), labelTextColor='k')
            for i, run in enumerate(selected):
                data = pd.concat([self.DRS.background_data_raw[run], self.DRS.intermediate_data[run]], axis=0)
                for mass in self.mselected:
                    xdata = data.iloc[:, 0].to_list()
                    ydata = data.loc[:, mass].to_list()
                    if run in self.plotted.keys():
                        run_plot = self.plotted[run]
                        if mass in run_plot.keys():
                            plot = run_plot[mass]
                            plot.setData(xdata, ydata)
                        else:
                            _colorgen(run, mass)
                            run_colour = self.penDic[run]
                            pen = pg.mkPen(color=run_colour[mass], width=1)
                            plot = self.ui.graphicsView.plot(xdata, ydata, pen=pen, name=self.runselected[i]+' '+mass)
                            run_plot[mass] = plot
                            self.plotted[run] = run_plot
                    else:
                        _colorgen(run, mass)
                        run_colour = self.penDic[run]
                        pen = pg.mkPen(color=run_colour[mass], width=1)
                        plot = self.ui.graphicsView.plot(xdata, ydata, name=run+' '+mass, pen=pen)
                        self.plotted[run] = {mass: plot}
            for run in previousselected:
                if run not in selected and run in self.plotted.keys():
                    masses = self.plotted[run]
                    for key, mass_plot in masses.items():
                        self.ui.graphicsView.removeItem(mass_plot)
                    self.plotted.pop(run)
            for run in selected:
                masses = self.plotted[run]
                for mass in previousselected:
                    if mass in masses and mass not in self.mselected:
                        self.ui.graphicsView.removeItem(masses[mass])
                        masses.pop(mass)
                        self.plotted[run] = masses

        if self.runselected:
            if self.ui.checkBox_dfIndex.isChecked():
                self.previous_mselected = self.mselected
                self.mselected = ['Rb87/Sr86_DF']
                for i in range(self.ui.listWidget_masses.count()):
                    item = self.ui.listWidget_masses.item(i)
                    if item.text() != 'Rb87/Sr86_DF':
                        item.setSelected(False)
                    else:
                        item.setSelected(True)
            else:
                if not self.mselected:
                    self.previous_mselected = self.mselected
                    self.ui.listWidget_masses.setCurrentRow(0)
                    self.mselected = [self.ui.listWidget_masses.currentItem().text()]

            _plt()

        else:
            self.ui.graphicsView.clear()
            self.plotted = {}
            self.penDic = {}

    def create_popup(self,title, message):
        popup = QtWidgets.QMessageBox(self)
        popup.setWindowTitle(title)
        popup.setText(message)
        popup.setIcon(QtWidgets.QMessageBox.Question)
        popup.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        opt = popup.exec_()
        return opt == QtWidgets.QMessageBox.Yes

    def print_message(self, message):
        QTimer.singleShot(0, lambda: self.ui.labelStatus.setText(message))
        QTimer.singleShot(6000, lambda: self.ui.labelStatus.setText(''))

    def check_signal(self):
        if not self.signal:
            return self.create_popup('Signal warning',
                                     f"You haven't especfied baseline and signal intervals."
                                     "\nDo you want to continue with automatic intervals?")
        else:
            return True

    def check_reduction_scheme(self):
        if self.groups:
            if self.check_signal():
                self.reduction_scheme()
            else:
                self.open_signalDialog()
        else:
            self.print_message('ERROR! You should create group selections')

    def reduction_scheme(self):
        gas = self.ui.comboBoxGas.currentText()
        Rb_85 = self.gases[gas][0]
        Sr_86 = self.gases[gas][1]
        Sr_87 = self.gases[gas][2]
        Sr_88 = self.gases[gas][3]
        fractionation = self.ui.checkBox_fractionation.isChecked()
        massBias = self.ui.checkBox_massBias.isChecked()
        drift = self.ui.checkBox_drift.isChecked()
        matrix = self.ui.checkBox_matrix.isChecked()
        fractionation_method = self.ui.comboBox_fractionation.currentText()
        drift_method = self.ui.comboBox_drift.currentText()
        rm1_name = self.ui.comboBox_rm.currentText()
        rm2_name = self.ui.comboBox_rm2.currentText()

        self.DRS.background(self.handlefiles.alldatafiles)
        self.DRS.background_subtraction()
        self.DRS.Rb_calculation()
        self.DRS.raw_ratios(Sr_86, Sr_87, Sr_88)
        self.DRS.convertion_rate(Sr_88)
        self.DRS.downhole_fractionation_index()
        if fractionation:
            self.open_fractionationDialog(fractionation_method)
            fractionation = self.ui.checkBox_fractionation.isChecked()
            if not fractionation:
                return
        if massBias:
            self.DRS.mass_bias_correction(self.groups)
        if drift:
            if rm1_name in self.groups.keys() and rm1_name in self.database.keys():
                self.open_driftDialog(drift_method, rm1_name)
                drift = self.ui.checkBox_drift.isChecked()
                if not drift:
                    return
            else:
                self.print_message('ERROR! RM for drift correction should be in the database and in groups')
        if matrix:
            if rm2_name in self.groups.keys() and rm2_name in self.database.keys():
                if drift:
                    self.DRS.matrix_correction(self.groups, rm2_name, self.database)
                else:
                    self.print_message('ERROR! no external correction has been performed')
        else:
            self.print_message('ERROR! RM for matrix correction should be in the database and in groups')
        self.DRS.compute_results(self.groups, self.handlelog.name_links)
        self.print_message('All selected data corrected!')
        self.populate_table()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
