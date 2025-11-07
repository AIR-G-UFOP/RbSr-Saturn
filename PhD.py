import glob
import os.path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas.core.frame

from ui.GroupDialog import Ui_GroupDialog
from scipy.integrate import simpson
import statistics

from module.core import *


# Utils ///////////////////////////////////////////////////////////////////////////////////////////////////////////////
def open_grouped_data(path):
    excel = pd.ExcelFile(path)
    material = excel.sheet_names

    data = {}
    for name in material:
        data[name] = pd.read_excel(path, sheet_name=name)

    return data

def open_ungrouped_data_ratios(path):
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

def open_ungrouped_raw_data(path):
    excel = pd.ExcelFile(path)
    sheets = excel.sheet_names
    header = 1  # 0 for raw data, 1 for selected data
    cols = ['Rb85_Sr86s_Raw', 'Sr87s_Sr86s_Raw'] # ['Rb85_CPS', 'Sr86_CPS','Sr87_CPS','Sr107_CPS'], ['Rb85', 'Sr105', 'Sr106', 'Sr107']
    time_col = 'Elapsed Time' # 'Time [Sec]' for raw data
    drop_col =  ['Absolute Time', time_col] # [time_col] for selected data
    groups = defaultdict(list)
    for sheet in sheets:
        match = re.match(r'([a-zA-Z0-9]+(?:_[a-zA-Z]+|-[a-zA-Z]+)?)(?:[-_]\d+)?', sheet)
        if match:
            key = match.group(1)
            groups[key].append(sheet)
    materials = dict(groups)

    raw = {}
    for name, sheet_names in materials.items():
        data_dict = {sheet: pd.read_excel(excel, sheet_name=sheet, header=header) for sheet in sheet_names}
        time = max(data_dict.keys(), key=lambda s: len(data_dict[s][time_col].dropna()))

        # Rb85 = data_dict[time][[time_col]].copy()
        # Sr86 = data_dict[time][[time_col]].copy()
        # Sr87 = data_dict[time][[time_col]].copy()
        # Sr107 = data_dict[time][[time_col]].copy()
        rbsr = data_dict[time][[time_col]].copy()
        srsr = data_dict[time][[time_col]].copy()

        cont = 1
        for sheet, data in data_dict.items():
            data_i = data.drop(columns=drop_col, errors='ignore')
            for col in cols:
                data_m = data_i.loc[:, col]
                data_m.rename(col + '-' + str(cont), inplace=True)
                # if col == 'Rb85':
                #     Rb85 = Rb85.merge(data_m, left_index=True, right_index=True, how='outer')
                # elif col == 'Sr105':
                #     Sr86 = Sr86.merge(data_m, left_index=True, right_index=True, how='outer')
                # elif col == 'Sr106':
                #     Sr87 = Sr87.merge(data_m, left_index=True, right_index=True, how='outer')
                # elif col == 'Sr107':
                #     Sr107 = Sr107.merge(data_m, left_index=True, right_index=True, how='outer')
                if col == 'Rb85_Sr86s_Raw':
                    rbsr = rbsr.merge(data_m, left_index=True, right_index=True, how='outer')
                elif col == 'Sr87s_Sr86s_Raw':
                    srsr = srsr.merge(data_m, left_index=True, right_index=True, how='outer')
            cont += 1
        # raw[name] = {'Rb85': Rb85, 'Sr105': Sr86, 'Sr106': Sr87, 'Sr107': Sr107}
        raw[name] = {'Rb/Sr': rbsr, 'Sr/Sr': srsr}
    return raw

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
# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Plot raw signal /////////////////////////////////////////////////////////////////////////////////////////////////////
def plot_raw_data():
    # settings
    colours = ['#000000', '#9E9B99', '#66CCEE', '#FFC20A', '#0C7BDC', '#E66100', '#5D3A9B', '#D41159', '#D35FB7',
               '#1AFF1A']
    RM = ['LaPosta_V', 'LaPosta_H', 'MD4B_V', 'MD4B_H', 'HogsboM_V', 'HogsboM_H', 'BRM1_V', 'BRM1_H', 'BRM2_V', 'BRM2_H']
    # get data file paths
    dir_path = r'raw_signal_crystallographic_comparison'
    file_pathern = os.path.join(dir_path, '*.xlsx')
    data_files = glob.glob(file_pathern)
    # create canvas
    fig, axes = plt.subplots(nrows=5, ncols=2, layout='constrained')
    axes = axes.flatten()
    # open and sort data files
    for i, file in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        print(file_name)
        raw_data = open_ungrouped_raw_data(file)
        # plot data
        mass = 'Sr107'
        for name, data in raw_data.items():
            data_m = data[mass]
            row = RM.index(name)
            mean_data_m = data_m.iloc[:, 1:].mean(axis=1)
            time = data_m.iloc[:, 0]
            # plot all data
            axes[row].plot(time, data_m, label=file_name, color=colours[i])
            axes[row].set_title(name)
            # plot data mean
            # axes[row].plot(time, mean_data_m, label=file_name, color=colours[i])
            # axes[row].set_title(name)
            # axes[row].legend(ncol=2, loc='upper right', fontsize=8, columnspacing=0.5)
            # Plot settings
            axes[row].set_xlabel('Ablation time (s)')
            axes[row].set_ylabel(mass + '(cps)')
    plt.show()
    # plot legend only
    # handles0, labels0 = axes[0].get_legend_handles_labels()
    # handles1, labels1 = axes[7].get_legend_handles_labels()
    # handles = handles0 + handles1
    # labels = labels0 + labels1
    # legend_fig = plt.figure(figsize=(2, 1))
    # legend_fig.legend(handles, labels, loc='center')
    # legend_fig.savefig('legend_mean_average_signals_all_data.pdf', bbox_inches='tight')
    # plt.close(legend_fig)
# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Percentage difference horizontal vs vertical ////////////////////////////////////////////////////////////////////////
def percentage_difference_raw_signal():
    # get data file paths
    dir_path = r'selected_signal_crystallographic_comparison'
    file_pathern = os.path.join(dir_path, '*.xlsx')
    data_files = glob.glob(file_pathern)
    # open and sort data files
    data_perc_diff = {}
    for i, file in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        print(file_name)
        raw_data = open_ungrouped_raw_data(file)
        perc_diff_mass = {}
        for mass in ['Rb85', 'Sr105', 'Sr106', 'Sr107']:
            data_mean = {}
            for name, data in raw_data.items():
                data_m = data[mass]
                mean_data_m = data_m.iloc[:, 1:].mean(axis=1)
                time = data_m.iloc[:, 0]
                data_mean[name] = pd.concat([time, mean_data_m], axis=1)
            perc_diff_mass[mass] = calculate_percentage_difference_raw_signal(data_mean)
        data_perc_diff[file_name] = perc_diff_mass
    data_perc_diff = {outer: pd.DataFrame(inner_dict) for outer, inner_dict in data_perc_diff.items()}
    data_perc_diff = pd.concat({batch: df for batch, df in data_perc_diff.items()}, names=['Session', 'Material']).reset_index()
    data_perc_diff = data_perc_diff.melt(id_vars=['Session', 'Material'], var_name='Masses', value_name='Percent_diff')
    plot_percentage_difference(data_perc_diff)
    with pd.ExcelWriter('perc_diff_selected_data.xlsx') as writer:
        data_perc_diff.to_excel(writer)

def calculate_percentage_difference_raw_signal(data):
    materials = {'LaPosta': ['LaPosta_V', 'LaPosta_H'],
                 'MD4B': ['MD4B_V', 'MD4B_H'],
                 'HogsboM': ['HogsboM_V', 'HogsboM_H'],
                 'BRM1': ['BRM1_V', 'BRM1_H'],
                 'BRM2': ['BRM2_V', 'BRM2_H']}
    data_diff = {}
    for mat, orient in materials.items():
        try:
            vert = orient[0]
            horiz = orient[1]
            if horiz in data.keys():
                data_a = data[vert].dropna()  # data vertical orientation
                data_b = data[horiz].dropna()   # data horizontal orientation
                auc_a = simpson(data_a.iloc[:, 1], data_a.iloc[:, 0], ) # area under the curve, vertical
                auc_b = simpson(data_b.iloc[:, 1], data_b.iloc[:, 0], ) # area under the curve, horizontal
                # percentage difference
                data_diff[mat] = round((auc_b - auc_a) / ((auc_a + auc_b) / 2) * 100, 2)
        except Exception as error:
            raise error
    return data_diff

def plot_percentage_difference(data):
    palette = {'20241213_batch1': '#000000', '20241213_batch2': '#9E9B99', '20250218_batch2': '#66CCEE',
               '20250218_batch3': '#FFC20A', '20250224_batch1': '#0C7BDC', '20250224_batch2': '#E66100',
               '20250227_batch1': '#5D3A9B', '20251016_batch2': '#D41159', '20251020_batch1': '#D35FB7',
               '20251020_batch2': '#1AFF1A'}
    RM = ['LaPosta', 'MD4B', 'HogsboM', 'BRM1', 'BRM2']
    materials = sorted(data['Material'].unique())
    elements = sorted(data['Masses'].unique())
    nrows, ncols = len(materials), len(elements)
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4 * ncols, 3.5 * nrows), sharey='row')
    axes = axes.reshape(nrows, ncols)
    sns.set_theme(style='whitegrid')
    sns.set_context('talk', font_scale=0.9)
    for i, material in enumerate(RM):
        for j, mass in enumerate(['Rb85', 'Sr105', 'Sr106', 'Sr107']):
            ax = axes[i, j]
            sub = data[(data['Material'] == material) & (data['Masses'] == mass)]
            sns.barplot(data=sub, x='Session', y='Percent_diff', hue='Session', dodge=False, palette=palette, ax=ax,
                        edgecolor='black')
            ax.axhline(0, color='gray', linestyle='--', linewidth=1)
            ax.set_title(f'{material} – {mass}', fontsize=11, pad=10)
            ax.set_xlabel('')
            ax.set_ylabel('% diff (H – V)' if j == 0 else '', fontsize=10)
            ax.legend().remove()
            ax.set_xticks([])  # Remove x-tick labels
            sns.despine(ax=ax)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Internal precision for raw signal ///////////////////////////////////////////////////////////////////////////////////
def internal_precision_raw_signal():
    # get data file paths
    dir_path = r'selected_signal_crystallographic_comparison'
    file_pathern = os.path.join(dir_path, '*.xlsx')
    data_files = glob.glob(file_pathern)
    # open and sort data files
    int_prec = {}
    for i, file in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        print(file_name)
        raw_data = open_ungrouped_raw_data(file)
        int_prec_mass = {}
        for mass in ['Rb85', 'Sr105', 'Sr106', 'Sr107']:
            int_prec_mat = {}
            for name, data in raw_data.items():
                data_m = data[mass]
                int_prec_mat[name] = calculate_internal_precision_raw_data(data_m)
            int_prec_mass[mass] = int_prec_mat
        int_prec[file_name] = int_prec_mass
    to_export = []
    for session, masses in int_prec.items():
        for mass, materials in masses.items():
            for material, values in materials.items():
                to_export.append({'Session': session,
                                  'Material': material,
                                  'Mass': mass,
                                  '2s%': values[0],
                                  'std': values[1]})
    with pd.ExcelWriter('int_prec_selected_signal.xlsx') as writer:
        pd.DataFrame(to_export).to_excel(writer)

def calculate_internal_precision_raw_data(data):
    result = []
    for spot in data.columns.to_list()[1:]:
        spot_data = data.loc[:, spot]
        x = spot_data.mean()
        sig = spot_data.std()
        n = len(spot_data.index)
        result.append(2 * (sig / np.sqrt(n)) * (1 / x) * 100)
    return [statistics.mean(result), statistics.stdev(result)]
# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

# Down-hole fractionation patterns ////////////////////////////////////////////////////////////////////////////////////
def df_patterns_calc_all_data(data):
    df_data = {}
    df_index_data = {}
    ratios_data = {}
    for name, ratios in data.items():
        time = ratios['Rb85']['Time [Sec]']
        data_rb85 = ratios['Rb85'].iloc[:, 1:]
        data_sr105 = ratios['Sr105'].iloc[:, 1:]
        data_sr106 = ratios['Sr106'].iloc[:, 1:]
        rb_sr = time
        sr_sr = time
        rbsr_r = time
        srsr_r = time
        rbsr_dfi = []
        srsr_dfi = []
        for i, spot in enumerate(data_rb85.columns.to_list()):
            data_rb85_i = data_rb85.loc[:, spot].dropna()
            data_sr105_i = data_sr105.iloc[:, i].dropna()
            data_sr106_i = data_sr106.iloc[:, i].dropna()
            # data_i.mask(data_i < 0, np.nan, inplace=True)
            # ratios
            rbsr_i = data_rb85_i / data_sr105_i
            srsr_i = data_sr106_i / data_sr105_i
            rbsr_r = pd.concat([rbsr_r, rbsr_i.rename('Rb/Sr-' + str(i+1))], axis=1)
            srsr_r = pd.concat([srsr_r, srsr_i.rename('Sr/Sr-' + str(i+1))], axis=1)
            # df pattern
            rbsr_mean = rbsr_i.mean()
            rbsr_df = rbsr_i / rbsr_mean
            srsr_mean = srsr_i.mean()
            srsr_df = srsr_i / srsr_mean
            rb_sr = pd.concat([rb_sr, rbsr_df.rename('Rb/Sr-' + str(i+1))], axis=1)
            sr_sr = pd.concat([sr_sr, srsr_df.rename('Sr/Sr-' + str(i+1))], axis=1)
            # df index
            mid = len(rbsr_i) // 2
            rbsr_h1 = rbsr_i.iloc[:mid].mean()
            rbsr_h2 = rbsr_i.iloc[mid:].mean()
            rbsr_dfi.append(((rbsr_h2 - rbsr_h1) / rbsr_mean) * 100)
            srsr_h1 = srsr_i.iloc[:mid].mean()
            srsr_h2 = srsr_i.iloc[mid:].mean()
            srsr_dfi.append(((srsr_h2 - srsr_h1) / srsr_mean) * 100)
            # saving
        df_data[name] = {'Rb/Sr': rb_sr, 'Sr/Sr': sr_sr}
        df_index_data[name] = {'Rb/Sr': statistics.mean(rbsr_dfi), 'Rb/Sr sd': statistics.stdev(rbsr_dfi),
                               'Sr/Sr': statistics.mean(srsr_dfi), 'Sr/Sr sd': statistics.stdev(srsr_dfi)}
        ratios_data[name] = {'Rb/Sr': rbsr_r, 'Sr/Sr': srsr_r}
    return df_data, df_index_data, ratios_data

def df_patterns_calc_selected_data(data):
    df_data = {}
    df_index_data = {}
    for name, ratios in data.items():
        time = ratios['Rb/Sr']['Elapsed Time']
        data_rbsr = ratios['Rb/Sr'].iloc[:, 1:]
        data_srsr = ratios['Sr/Sr'].iloc[:, 1:]
        rb_sr = time
        sr_sr = time
        rbsr_dfi = []
        srsr_dfi = []
        for i, spot in enumerate(data_rbsr.columns.to_list()):
            rbsr_i = data_rbsr.loc[:, spot].dropna()
            srsr_i = data_srsr.iloc[:, i].dropna()
            # data_i.mask(data_i < 0, np.nan, inplace=True)
            # df pattern
            rbsr_mean = rbsr_i.mean()
            rbsr_df = rbsr_i / rbsr_mean
            srsr_mean = srsr_i.mean()
            srsr_df = srsr_i / srsr_mean
            rb_sr = pd.concat([rb_sr, rbsr_df.rename('Rb/Sr-' + str(i + 1))], axis=1)
            sr_sr = pd.concat([sr_sr, srsr_df.rename('Sr/Sr-' + str(i + 1))], axis=1)
            # df index
            mid = len(rbsr_i) // 2
            rbsr_h1 = rbsr_i.iloc[:mid].mean()
            rbsr_h2 = rbsr_i.iloc[mid:].mean()
            rbsr_dfi.append(((rbsr_h2 - rbsr_h1) / rbsr_mean) * 100)
            srsr_h1 = srsr_i.iloc[:mid].mean()
            srsr_h2 = srsr_i.iloc[mid:].mean()
            srsr_dfi.append(((srsr_h2 - srsr_h1) / srsr_mean) * 100)
            # saving
        df_data[name] = {'Rb/Sr': rb_sr, 'Sr/Sr': sr_sr}
        df_index_data[name] = {'Rb/Sr': statistics.mean(rbsr_dfi), 'Rb/Sr sd': statistics.stdev(rbsr_dfi),
                               'Sr/Sr': statistics.mean(srsr_dfi), 'Sr/Sr sd': statistics.stdev(srsr_dfi)}
    return df_data, df_index_data

def plot_df_all_data():
    # settings
    colours = ['#000000', '#9E9B99', '#66CCEE', '#FFC20A', '#0C7BDC', '#E66100', '#5D3A9B', '#D41159', '#D35FB7',
               '#1AFF1A']
    RM = ['LaPosta_V', 'LaPosta_H', 'MD4B_V', 'MD4B_H', 'HogsboM_V', 'HogsboM_H', 'BRM1_V', 'BRM1_H', 'BRM2_V',
          'BRM2_H']
    limit = {'LaPosta_V': [.0, 2.5], 'LaPosta_H': [.0, 2.5],
             'MD4B_V': [.0, 2.5], 'MD4B_H': [.0, 2.5],
             'HogsboM_V': [0, 4], 'HogsboM_H': [0, 4],
             'BRM1_V': [.0, 2.5], 'BRM1_H': [.0, 2.5],
             'BRM2_V': [.0, 2.5], 'BRM2_H': [.0, 2.5]}
    # get data file paths
    dir_path = r'selected_signal_crystallographic_comparison'
    file_pathern = os.path.join(dir_path, '*.xlsx')
    data_files = glob.glob(file_pathern)
    # all_data = {name: [] for name in RM}
    # data_each_run = {name: {} for name in RM}
    # open and plot data
    fig, axes = plt.subplots(nrows=5, ncols=2, layout='constrained')
    axes = axes.flatten()
    ratio = 'Rb/Sr'
    df_index = {}
    ratios = {}
    for i, file in enumerate(data_files):
        file_name = os.path.splitext(os.path.basename(file))[0]
        print(file_name)
        raw_data = open_ungrouped_raw_data(file)
        # df_data, df_index_data = df_patterns_calc_selected_data(raw_data)
        # df_data, df_index_data, ratios_data = df_patterns_calc(raw_data)
        # for name, ratios in df_data.items():
        #     row = RM.index(name)
        #     data = ratios[ratio]
        #     time = data.iloc[:, 0]
        #     # plot all data
        #     axes[row].plot(time, data.iloc[:, 1:], color=colours[i])
        #     # plot data mean
        #     # data_mean = data.iloc[:, 1:].mean(axis=1)
        #     # axes[row].plot(time, data_mean, label=name, color=colours[i])
        #     axes[row].set_title(name)
        #     axes[row].set_ylim(limit[name][0], limit[name][1])
        #     if row == 8 or row == 9:
        #         axes[row].set_xlabel('Ablation time (s)')
        #     if row % 2 == 0:
        #         axes[row].set_ylabel('Norm ' + ratio)
            # get data for interpolation
            # run_data_and_mean = pd.concat([data, data_mean.mean(axis=1).rename('mean')], axis=1)
            # material = data_each_run[name + '-' + file_name]
            # material[file_name] = run_data_and_mean
            # list = all_data[name + '-' + file_name]
            # list.append(pd.DataFrame(data=data_mean.values, index=time.values))
        # df_index[file_name] = df_index_data
        # ratios[file_name] = ratios_data
        ratios[file_name] = raw_data
    # from statsmodels.nonparametric.smoothers_lowess import lowess
    # all_data_mean = {}
    # for name, list in all_data.items():
    #     try:
    #         all_times = [df.index.to_numpy() for df in list]
    #         all_times = np.unique(np.concatenate(all_times))
    #         common_times = np.linspace(all_times.min(), all_times.max(), 200)
    #
    #         interpolated_dfs = []
    #         for df in list:
    #             # Ensure sorted index and numeric
    #             df = df.sort_index()
    #             df.index = df.index.astype(float)
    #
    #             # Interpolate to make time a continuous function
    #             df_interp = df.interpolate(method='index', limit_direction='both')
    #
    #             # Now use numpy.interp for each column to ensure smooth interpolation
    #             df_uniform = pd.DataFrame(index=common_times)
    #
    #             for col in df.columns:
    #                 # Drop NaNs to avoid crashing interp
    #                 valid = df_interp[col].dropna()
    #                 if len(valid) < 2:
    #                     # Not enough points to interpolate — skip or fill
    #                     df_uniform[col] = np.nan
    #                 else:
    #                     df_uniform[col] = np.interp(common_times, valid.index, valid.values)
    #
    #             interpolated_dfs.append(df_uniform)
    #
    #         # Combine and average (ignoring NaNs)
    #         combined = pd.concat(interpolated_dfs)
    #         mean_df = combined.groupby(combined.index).mean()
    #         all_data_mean[name] = mean_df
    #         std_df = combined.groupby(combined.index).std()
    #         n = combined.groupby(combined.index).count()
    #         x = mean_df.index.to_numpy()
    #         y = mean_df.iloc[:, 0].to_numpy()
    #         lowess_r = np.array(lowess(endog=y, exog=x, frac=0.15, return_sorted=False))
    #         stderr = (std_df.iloc[:, 0] / np.sqrt(n.iloc[:, 0])).to_numpy()
    #         upper = lowess_r + 1.96 * stderr
    #         lower = lowess_r - 1.96 * stderr
    #
    #         axes[RM.index(name)].plot(x, lowess_r, 'black', label=name+'_LOWESS')
    #         axes[RM.index(name)].fill_between(x, lower, upper, color='black', alpha=0.1, label='95% Envelope')
    #     except ValueError:
    #         pass
    # plt.show()
    # row = []
    # for session, materials in df_index.items():
    #     for material, ratios in materials.items():
    #         row.append({'Session': session, 'Material': material, 'Rb/Sr': ratios['Rb/Sr'],
    #                     'Rb/Sr sd': ratios['Rb/Sr sd'], 'Sr/Sr': ratios['Sr/Sr'], 'Sr/Sr sd': ratios['Sr/Sr sd']})
    # with pd.ExcelWriter('df_index_all_data.xlsx') as writer:
    #     pd.DataFrame(row).to_excel(writer)
    # plot_ratios_all_data(ratios)
    plot_ratios_all_data(ratios)

def plot_ratios_all_data(data):
    cb_palette = [
        '#000000', '#9E9B99', '#66CCEE', '#FFC20A', '#0C7BDC',
        '#E66100', '#5D3A9B', '#D41159', '#D35FB7', '#1AFF1A'
    ]
    # Define base materials (without _V / _H)
    base_materials = ['LaPosta', 'MD4B', 'HogsboM', 'BRM1', 'BRM2']
    versions = ['_V', '_H']
    ratio_types = ['Rb/Sr', 'Sr/Sr']
    marker_map = {'_V': 'o', '_H': 's'}

    def _mean_sem(df):
        vals = df.dropna().values
        mean = vals.mean()
        sd = vals.std(ddof=1) # / np.sqrt(len(vals)) if len(vals) > 1 else 0
        return mean, sd

    sessions = list(data.keys())  # preserve user's ordering
    n_sessions = len(sessions)
    n_rows = len(base_materials)
    n_cols = len(ratio_types)

    fig, axes = plt.subplots(nrows=n_rows, ncols=n_cols, sharex=False)

    # Ensure axes is 2D array even if n_rows or n_cols == 1
    axes = np.atleast_2d(axes)

    # x positions for sessions (base)
    x_base = np.arange(n_sessions) * 1.0

    col_jitter_step = .1
    version_offset = .18

    for i_base, base in enumerate(base_materials):
        for j_ratio, ratio in enumerate(ratio_types):
            ax = axes[i_base, j_ratio]
            # For legend handles later, we'll collect nothing here; create legends after plotting
            for s_idx, session in enumerate(sessions):
                color = cb_palette[s_idx % len(cb_palette)]

                for ver in versions:
                    mat_name = base + ver
                    # defensive: skip if missing
                    if session not in data or mat_name not in data[session] or ratio not in data[session][mat_name]:
                        continue
                    df = data[session][mat_name][ratio]

                    # require pandas; assume df has at least 2 columns (time + >=1 ratio col)
                    # select ratio columns (exclude first/time column)
                    try:
                        ratio_cols = df.iloc[:, 1:]
                    except Exception:
                        continue

                    if ratio_cols.shape[1] == 0:
                        continue

                    n_ratio_cols = ratio_cols.shape[1]
                    # center jitter for columns so that multiple points per session are visible
                    # e.g., if 3 cols -> offsets [-j,0,+j], if 4 cols -> [-1.5j, -0.5j, +0.5j, +1.5j], etc.
                    max_spread = 0.25  # total horizontal spread allowed for all columns
                    if n_ratio_cols == 1:
                        col_jitters = np.array([0.0])
                    else:
                        # even spacing from -max_spread to +max_spread
                        col_jitters = np.linspace(-max_spread, max_spread, n_ratio_cols)

                    # version offset: _V left (-version_offset), _H right (+version_offset)
                    v_off = -version_offset if ver == '_V' else version_offset

                    for k, col_name in enumerate(ratio_cols.columns):
                        series = ratio_cols.iloc[:, k]
                        mean, sem = _mean_sem(series)

                        if np.isnan(mean):
                            continue

                        x = x_base[s_idx] + v_off + col_jitters[k]

                        ax.errorbar(
                            x, mean, yerr=sem,
                            fmt=marker_map[ver],
                            color=color,
                            markersize=5,
                            capsize=2,
                            linestyle='None',
                            markeredgewidth=0.5,
                            alpha=0.95
                        )
            # aesthetics
            ax.set_ylabel(base, rotation=90, va='center')
            if i_base == 0:
                ax.set_title(ratio)
            # keep ticks at session positions but hide labels
            ax.set_xticks(x_base)
            ax.set_xticklabels([''] * len(x_base))
            # tighten y-limits a bit if there is data present
            # grab y-data from plotted lines to compute limits safely
            y_data = []
            for line in ax.lines:
                # line.get_xydata() will include errorbar cap lines etc; safer to skip
                try:
                    xy = line.get_xydata()
                    if len(xy) > 0:
                        y_data.extend(xy[:, 1].tolist())
                except Exception:
                    pass
            if len(y_data) > 0:
                ymin, ymax = np.nanmin(y_data), np.nanmax(y_data)
                yrange = ymax - ymin if ymax != ymin else max(abs(ymax), 1.0)
                ax.set_ylim(ymin - 0.12 * yrange, ymax + 0.12 * yrange)
    plt.show()


# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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
        """
        This function calculates the internal precision (2s%) and the internal reproducibility (RSD%) of the Rb/Rb and
        Sr/Sr ratios
        The loaded data file should be the Excel file exported from Iolite
        """

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

# Call the method you want here:
plot_df_all_data()
