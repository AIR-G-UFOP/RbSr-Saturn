import glob
import os.path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas.core.frame
from ui.GroupDialog import Ui_GroupDialog

from module.core import *


def df_patterns_calc(data):
    DF_data = {}
    DFI_data = {}
    for name, data_i in data.items():
        time = data_i['Elapsed Time']

        data_i.drop('Elapsed Time', axis=1, inplace=True)
        data_i.mask(data_i < 0, np.nan, inplace=True)
        mid = len(data_i) // 2

        average = data_i.mean()
        DF = data_i / average

        DF1 = data_i.iloc[:mid].mean()
        DF2 = data_i.iloc[mid:].mean()
        DFI = ((DF2 - DF1) / average) * 100

        DF_data[name] = pd.concat([time, DF], axis=1)
        DFI_data[name] = DFI.mean()

    return DF_data, DFI_data


def open_grouped_data(path):
    excel = pd.ExcelFile(path)
    material = excel.sheet_names

    data = {}
    for name in material:
        data[name] = pd.read_excel(path, sheet_name=name)

    return data


def open_ungrouped_data(path):
    excel = pd.ExcelFile(path)
    sheets = excel.sheet_names

    groups = defaultdict(list)
    materials = {}
    for sheet in sheets:
        match = re.match(r'([a-zA-Z0-9]+(?:_[a-zA-Z]+|-[a-zA-Z]+)?)(?:[-_]\d+)?', sheet)
        if match:
            key = match.group(1)
            groups[key].append(sheet)
    materials = dict(groups)

    raw_ratio = {}
    for name, sheet_names in materials.items():
        data_dict = {sheet: pd.read_excel(excel, sheet_name=sheet, header=1) for sheet in sheet_names}
        time = max(data_dict.keys(), key=lambda s: len(data_dict[s]['Elapsed Time'].dropna()))

        main_data = data_dict[time][['Elapsed Time']].copy()

        cont = 1
        for sheet, data in data_dict.items():
            data_i = data.drop(columns=['Absolute Time', 'Elapsed Time', 'Sr87s_Sr86s_Raw'], errors='ignore')
            col = data_i.columns[0]
            data_i.rename(columns={col: col + '-' + str(cont)}, inplace=True)
            main_data = main_data.merge(data_i, left_index=True, right_index=True, how='outer')
            cont += 1

        raw_ratio[name] = main_data

    return raw_ratio


def plot_patterns():
    fig, axes = plt.subplots(nrows=5, ncols=2, layout='constrained')
    axes = axes.flatten()
    row = ['MicaMg', '610', 'MD4B_V', 'MD4B_H', 'LaPosta_V', 'LaPosta_H', 'HogsboM_V', 'HogsboM_H', 'WP1_V', 'WP1_H']

    raw_ratio = open_ungrouped_data('20260626_OU_Batch3_Raw_Ratios.xlsx')
    df_data, df_index = df_patterns_calc(raw_ratio)
    for name, data_i in df_data.items():
        time = data_i.iloc[:, 0]
        values = data_i.iloc[:, 1:].mean(axis=1)
        # values_average = values.mean(axis=1)
        row_i = row.index(name)
        axes[row_i].plot(time, values)
        axes[row_i].plot(time, values, 'k')
        axes[row_i].set_title(name)
        axes[row_i].set_ylim(0.5, 1.5)

    with pd.ExcelWriter('DF_indexfentosecond.xlsx', engine='xlsxwriter') as writer:
        DF = pd.DataFrame.from_dict(df_index, orient='index')
        DF.to_excel(writer, index=True)

    plt.show()


def plot_DF_all_data():
    colours = ['#000000', '#9E9B99', '#66CCEE', '#FFC20A', '#0C7BDC', '#E66100', '#5D3A9B', '#D41159', '#D35FB7', '#1AFF1A', '#994f00', '#FF0000']
    RM = ['LaPosta_V', 'LaPosta_H', '610', 'MD4B_V', 'MD4B_H', 'MicaMg', 'Hogsbo_V', 'Hogsbo_H'] #, 'MicaFe', 'WP1_V', 'WP1_H']
    DFI = {}
    all_data = {name: [] for name in RM}
    data_each_run = {name: {} for name in RM}

    dir_path = r'data'
    file_pathern = os.path.join(dir_path, '*.xlsx')
    data_files = glob.glob(file_pathern)

    fig, axes = plt.subplots(nrows=3, ncols=3, layout='constrained')
    axes = axes.flatten()
    for i, file in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        if file_name == '20250203-UoP' or file_name == '20260626_UoP_Batch3':
            raw_data = open_grouped_data(file)
        else:
            raw_data = open_ungrouped_data(file)
        DF_data, DFI_data = df_patterns_calc(raw_data)
        DFI[file_name] = DFI_data
        for name, data in DF_data.items():
            if name != 'WP1_V' and name != 'WP1_H' and name != 'MicaFe':
                row = RM.index(name)
                time = data.iloc[:, 0]
                norm_data = data.iloc[:, 1:].mean(axis=1)

                run_data_and_mean = pd.concat([data, norm_data.mean(axis=1).rename('mean')], axis=1)
                material = data_each_run[name+'-'+file_name]
                material[file_name] = run_data_and_mean

                list = all_data[name+'-'+file_name]
                list.append(pd.DataFrame(data=norm_data.values, index=time.values))

                axes[row].plot(time, norm_data, label=name, color=colours[i])
                # axes[row].plot(time, norm_data.mean(axis=1), color='black')
                axes[row].set_title(name)
                axes[row].set_ylim(0.5, 1.5)
                # axes[row].legend(ncol=2, loc='upper right', fontsize=8, columnspacing=0.5)

                axes[row].set_xlabel('Ablation time (s)')
                axes[row].set_ylabel('Norm Rb/Sr')

    from statsmodels.nonparametric.smoothers_lowess import lowess
    all_data_mean = {}
    for name, list in all_data.items():
        try:
            all_times = [df.index.to_numpy() for df in list]
            all_times = np.unique(np.concatenate(all_times))
            common_times = np.linspace(all_times.min(), all_times.max(), 200)

            interpolated_dfs = []
            for df in list:
                # Ensure sorted index and numeric
                df = df.sort_index()
                df.index = df.index.astype(float)

                # Interpolate to make time a continuous function
                df_interp = df.interpolate(method='index', limit_direction='both')

                # Now use numpy.interp for each column to ensure smooth interpolation
                df_uniform = pd.DataFrame(index=common_times)

                for col in df.columns:
                    # Drop NaNs to avoid crashing interp
                    valid = df_interp[col].dropna()
                    if len(valid) < 2:
                        # Not enough points to interpolate — skip or fill
                        df_uniform[col] = np.nan
                    else:
                        df_uniform[col] = np.interp(common_times, valid.index, valid.values)

                interpolated_dfs.append(df_uniform)

            # Combine and average (ignoring NaNs)
            combined = pd.concat(interpolated_dfs)
            mean_df = combined.groupby(combined.index).mean()
            all_data_mean[name] = mean_df
            std_df = combined.groupby(combined.index).std()
            n = combined.groupby(combined.index).count()
            x = mean_df.index.to_numpy()
            y = mean_df.iloc[:, 0].to_numpy()
            lowess_r = np.array(lowess(endog=y, exog=x, frac=0.15, return_sorted=False))
            stderr = (std_df.iloc[:, 0] / np.sqrt(n.iloc[:, 0])).to_numpy()
            upper = lowess_r + 1.96 * stderr
            lower = lowess_r - 1.96 * stderr

            axes[RM.index(name)].plot(x, lowess_r, 'black', label=name+'_LOWESS')
            axes[RM.index(name)].fill_between(x, lower, upper, color='black', alpha=0.1, label='95% Envelope')
        except ValueError:
            pass

    # with pd.ExcelWriter('DF_index_spot_sizes_test.xlsx', engine='xlsxwriter') as writer:
    #     for sheet_name, d in DFI.items():
    #         DF = pd.DataFrame.from_dict(d, orient='index')
    #         DF.to_excel(writer, sheet_name=sheet_name, index=True)
    #
    # for name, run in data_each_run.items():
    #     with pd.ExcelWriter(name + '_DF_patterns_and_mean.xlsx', engine='xlsxwriter') as writer:
    #         for sheet_name, data in run.items():
    #             data.to_excel(writer, sheet_name=sheet_name, index=False)
    #
    # with pd.ExcelWriter('DF_all_data_mean.xlsx', engine='xlsxwriter') as writer:
    #     for name, data in all_data_mean.items():
    #         data.to_excel(writer, sheet_name=name, index=True)

    plt.show()


def group_excel_files():
    dir_path = r'C:\Users\if2375\OneDrive - The Open University\LA-ICP-MS lab data\Statistics'
    file_pathern = os.path.join(dir_path, '*.xlsx')
    data_files = glob.glob(file_pathern)
    filter_precis = {}
    filter_reprod = {}

    for i, file_path in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        file_data = pd.ExcelFile(file_path)

        precis_data = pd.read_excel(file_data, sheet_name='IntPrecis', index_col=0)
        index_HogV = []
        index_HogH = []
        # flag = None
        for i, name in enumerate(precis_data.index.to_list()):
            if 'Hogsbo_M' in name or 'HogsboM_H' in name or 'HogsboM-H' in name or 'Hogsbo_H' in name:
                index_HogH.append(i)
            if 'HogsboM_V' in name or 'HogsboM-V' in name or 'Hogsbo_V' in name:
                index_HogV.append(i)

                # flag = 'RM'
            # if name == 'Mica-Mg' or name == 'Mica_Mg':
            #     flag = 'SP'
            # if 'Mica_Mg-' in name or 'MicaMg-' in name:
            #     if flag == 'RM':
            #         index_Mg.append(i)

        HogH = precis_data.iloc[index_HogH]
        HogV = precis_data.iloc[index_HogV]
        HogH = HogH.mean().to_frame().rename(columns={0: 'HogsboM_H'})
        HogV = HogV.mean().to_frame().rename(columns={0: 'HogsboM_V'})

        filter_precis[file_name] = pd.concat([HogH, HogV], axis=1)

        reprod_data = pd.read_excel(file_data, sheet_name='IntReprod', index_col=0)
        index_reprod = []
        for i, name in enumerate(reprod_data.index.to_list()):
            # if name == 'G_NIST610' or name == 'NP_MICAMG':
            #     index_reprod.append(i)
            if 'Hogsbo_M' in name or 'HogsboM_' in name or 'Hogsbo_' in name:
                index_reprod.append(i)

        filter_reprod[file_name] = reprod_data.iloc[index_reprod]

    IntPrecis = pd.concat(filter_precis, axis=1)
    IntReprod = pd.concat(filter_reprod, axis=1)

    with pd.ExcelWriter(r'C:\Users\if2375\OneDrive - The Open University\LA-ICP-MS lab data\Statistics_MicaMg_HogsboM.xlsx', engine='xlsxwriter') as writer:
        IntPrecis.to_excel(writer, sheet_name='InterPrecis')
        IntReprod.to_excel(writer, sheet_name='InterReprod')


def open_pdf():
    import pdfplumber

    dir_path = r'Lenses log'
    file_pathern = os.path.join(dir_path, '*.pdf')
    data_files = glob.glob(file_pathern)

    logs = {}
    for i, file in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"

        # Extract key-value pairs with regex
        pattern = re.compile(r"([A-Za-z0-9 /()#]+)\s+([-+]?[0-9]*\.?[0-9]+(?: [°%VvmlrpscM]+|))")
        matches = pattern.findall(text)
        # Create dictionary
        data = {key.strip(): value.strip() for key, value in matches}
        # Convert to DataFrame
        df = pd.DataFrame(index=data.keys(), columns=["Value"], data=data.values())
        logs[file_name] = df

    final_log = pd.concat(logs, axis=1)

    with pd.ExcelWriter('Lenses_log.xlsx', engine='xlsxwriter') as writer:
        final_log.to_excel(writer, index=True)


class Window(QDialog):
    def __init__(self):
        super(Window, self).__init__()
        self.ui = Ui_GroupDialog()
        self.ui.setupUi(self)

        title = "Group selection"
        self.setWindowTitle(title)
        
        self.new_buttons()
        self.resize(301, 300)
        self.ui.listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.ui.btn_group.setDefault(False)
        self.ui.btn_ok.setDefault(True)
        self.ui.btn_group.setDefault(False)

        self.load.clicked.connect(self.open_raw_data)
        self.export.clicked.connect(self.export_data)
        self.ui.btn_group.clicked.connect(self.create_group)
        self.ui.btn_ok.clicked.connect(self.calc)
        self.ui.btn_cancel.clicked.connect(self.clear)
        self.ui.lineEdit_search.textChanged.connect(self.search)

        self.defined_groups = {}
        self.raw_data = None
        self.internal_precision = None
        self.internal_reprod = None

    def keyPressEvent(self, event):
        if event.type() == QEvent.KeyPress:
            if event.modifiers() & Qt.ControlModifier:
                if event.key() == Qt.Key_A:
                    self.select_all_ctrl()

    def new_buttons(self):
        hframe = QtWidgets.QFrame(self.ui.bgApp)
        hframe.setMinimumSize(QtCore.QSize(0, 0))
        hframe.setFrameShape(QtWidgets.QFrame.StyledPanel)
        hframe.setFrameShadow(QtWidgets.QFrame.Raised)
        hframe.setObjectName("hframe")
        hlayout = QtWidgets.QHBoxLayout(hframe)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setSpacing(5)
        hlayout.setObjectName("hlayout")
        self.load = QtWidgets.QPushButton(hframe)
        self.load.setMinimumSize(QtCore.QSize(16777215, 40))
        self.load.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.load.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.load.setObjectName("load")
        self.load.setText('LOAD')
        hlayout.addWidget(self.load)
        self.export = QtWidgets.QPushButton(hframe)
        self.export.setMinimumSize(QtCore.QSize(16777215, 40))
        self.export.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.export.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.export.setObjectName("export")
        self.export.setText('EXPORT')
        hlayout.addWidget(self.export)
        self.ui.verticalLayout_2.addWidget(hframe)

    def open_raw_data(self):
        file = filedialog.askopenfilename(title='Load Data File', filetypes=[("XLSX", "*.xlsx")])
        raw_data = None
        if file != '':
            try:
                raw_data = pd.read_excel(file, sheet_name='Data')
                index = raw_data.iloc[:, 0]
                for i, item in enumerate(index):
                    if type(item) == float:
                        raw_data.drop(i, axis=0, inplace=True)
                raw_data = raw_data.set_index(raw_data.iloc[:, 0])
                cols = raw_data.columns.to_list()
                raw_data.drop(cols[0], axis=1, inplace=True)

                self.raw_data = raw_data
                self.populate_list_combobox()
            except PermissionError:
                print('This file is being used elsewhere')

    def export_data(self):
        if type(self.internal_precision) == pandas.core.frame.DataFrame and type(self.internal_reprod) == pandas.core.frame.DataFrame:
            path = filedialog.asksaveasfile(title='Save Data File', defaultextension='.xlsx', filetypes=[('xlsx', '*.xlsx')])
            if path:
                name = path.name
                with pd.ExcelWriter(path=name, engine='openpyxl') as writer:
                    self.internal_precision.to_excel(writer, sheet_name='IntPrecis')
                    self.internal_reprod.to_excel(writer, sheet_name='IntReprod')
                print('Data exported')
        else:
            print('No data to export')

    def calc(self):
        '''
        This function calculates the internal precision (2s%) and the internal reproducibility (RSD%) of the Rb/Rb and
        Sr/Sr ratios
        The loaded data file should be the Excel file exported from Iolite
        '''

        if len(self.defined_groups.keys()) > 0:
            cols = self.raw_data.columns.to_list()
            rows = self.raw_data.index.to_list()

            double = ['Sr87s_Sr86s_Raw_mean', 'Sr87s_Sr86s_Raw_2SE(int)', 'Sr87s_Sr86s_Raw_2SD',
                      'Sr87s_Sr86s_Raw_NoOfPoints', 'Rb87_Sr86s_Raw_mean', 'Rb87_Sr86s_Raw_2SE(int)',
                      'Rb87_Sr86s_Raw_2SD', 'Rb87_Sr86s_Raw_NoOfPoints']
            single = ['StdCorr_Rb87_Sr86s_mean', 'StdCorr_Rb87_Sr86s_2SE(int)', 'StdCorr_Rb87_Sr86s_2SD',
                      'StdCorr_Rb87_Sr86s_NoOfPoints', 'StdCorr_Sr87s_Sr86s_mean', 'StdCorr_Sr87s_Sr86s_2SE(int)',
                      'StdCorr_Sr87s_Sr86s_2SD', 'StdCorr_Sr87s_Sr86s_NoOfPoints']
            if set(double).issubset(cols):
                indexes = double
            elif set(single).issubset(cols):
                indexes = single
            else:
                print('No data found')
                return

            self.internal_precision = pd.DataFrame(index=rows, columns=['Rb 2s%', 'Sr 2s%'])
            for i, row in enumerate(rows):
                self.internal_precision.loc[row, 'Rb/Sr 2s%'] = round(self.raw_data.loc[row, indexes[5]] / self.raw_data.loc[row, indexes[4]] * 100, 2)
                self.internal_precision.loc[row, 'Sr/Sr 2s%'] = round(self.raw_data.loc[row, indexes[1]] / self.raw_data.loc[row, indexes[0]] * 100, 2)

            # self.internal_reprod = pd.DataFrame(index=list(self.defined_groups.keys()), columns=['Rb RSD', 'Sr RSD'])
            # for key, data in self.defined_groups.items():
            #     SD_Rb = self.raw_data.loc[data, indexes[0]].std()
            #     SD_Sr = self.raw_data.loc[data, indexes[4]].std()
            #     mean_Rb = self.raw_data.loc[data, indexes[0]].mean()
            #     mean_Sr = self.raw_data.loc[data, indexes[4]].mean()
            #
            #     self.internal_reprod.loc[key, 'Rb RSD'] = round(SD_Rb / mean_Rb * 100, 2)
            #     self.internal_reprod.loc[key, 'Sr RSD'] = round(SD_Sr / mean_Sr * 100, 2)

            self.ui.label_status.setStyleSheet("color: #ff5555;")
            QTimer.singleShot(0, lambda: self.ui.label_status.setText('Calc done'))
            QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))
        else:
            self.ui.label_status.setStyleSheet("color: #ff5555;")
            QTimer.singleShot(0, lambda: self.ui.label_status.setText('No group selected'))
            QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))

    def clear(self):
        self.defined_groups = {}
        self.ui.label_status.setStyleSheet("color: #ff5555;")
        QTimer.singleShot(0, lambda: self.ui.label_status.setText('Groups cleared'))
        QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))

    def populate_list_combobox(self):
        names = self.raw_data.index.to_list()
        if len(names) > 0:
            self.defined_groups = {}
            self.internal_reprod = None
            self.internal_precision = None
            self.ui.listWidget.clear()
            self.ui.comboBox_name.clear()
            self.ui.listWidget.addItems(names)
            self.ui.comboBox_name.addItems(names)

    def create_group(self):
        items = [item.text() for item in self.ui.listWidget.selectedItems()]
        name = self.ui.comboBox_name.currentText()

        if len(items) > 0:
            self.defined_groups[name] = items

        else:
            self.ui.label_status.setStyleSheet("color: #ff5555;")
            QTimer.singleShot(0, lambda: self.ui.label_status.setText('No sample selected'))
            QTimer.singleShot(6000, lambda: self.ui.label_status.setText(''))

    def search(self):
        text = self.ui.lineEdit_search.text()
        self.ui.listWidget.clearSelection()

        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def select_all_ctrl(self):
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            if not item.isHidden():
                item.setSelected(True)


# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = Window()
#     window.show()
#     sys.exit(app.exec_())

plot_DF_all_data()


