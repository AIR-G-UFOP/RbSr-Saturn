import os.path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from module.core import *


class HandleFiles:
    def __init__(self):
        super(HandleFiles, self).__init__()

        self.datapath = []
        self.file_start_index = None
        self.file_end_index = None
        self.data_head = None
        self.alldatafiles = {}
        self.counter = 0
        self.run_names = []
        self.all_run_names = []
        self.name_links = {}

    def open_folders(self, dirct):
        self.datapath = []
        folders = next(os.walk(dirct))[1]
        for folder in folders:
            folderpath = os.path.join(dirct, folder)
            files = next(os.walk(folderpath))[2]
            for file in files:
                file_name, file_extension = os.path.splitext(file)
                if file_extension == '.csv':
                    file_path = os.path.join(folderpath, file)
                    self.datapath.append(file_path)

    def open_data_files(self):
        self.run_names = []
        self.sort_path()
        for n, data_path in enumerate(self.datapath):
            run_name = os.path.basename(data_path)
            name_without_extension = os.path.splitext(run_name)[0]

            raw_file = []
            with open(data_path) as data:
                for line in data:
                    line_stripped = line.strip()
                    line_splitted = line_stripped.split(sep=',')
                    raw_file.append(line_splitted)
                if n == 0:
                    for j, line in enumerate(raw_file):
                        for i, item in enumerate(line):
                            if item == 'Time [Sec]':
                                self.file_start_index = j
                                self.data_head = self.head_masses(line)
                            if i == 0:
                                try:
                                    float(item)
                                    self.file_end_index = j - self.file_start_index
                                except:
                                    pass
                filedata = pd.read_csv(data_path, header=self.file_start_index)
                filedata.columns = self.data_head
                filedata = filedata.iloc[:self.file_end_index]
                filedata = filedata.astype(float)
                filedata.replace(0, 1, inplace=True)

                # self.slice_data(filedata)

            unique_name = name_without_extension + " #" + str(self.counter)
            self.alldatafiles[unique_name] = filedata
            self.all_run_names.append(unique_name)
            self.run_names.append(unique_name)

    def open_single_file(self, filepath):
        self.datapath = []
        for path in filepath:
            extention = os.path.splitext(os.path.basename(path))[1]
            if extention == '.csv':
                self.datapath.append(path)

    def head_masses(self, masses):
        head = []
        for i, mass in enumerate(masses):
            if i != 0:
                match = re.match(r'([a-zA-Z]+)(\d+) -> (\d+)', mass)
                new = mass
                if match:
                    element, mass1, mass2 = match.groups()
                    if mass1 == mass2:
                        new = element + mass1
                    else:
                        new = element + mass2
                head.append(new)
            else:
                head.append(mass)

        return head

    def slice_data(self, data):
        time = data.iloc[:, 0]
        smoothing_window = 10
        prominence = 5
        distance = 50

        for col in data.columns[1:]:
            values = data[col].dropna().values
            indices = np.arange(len(values))

            smoothed_values = pd.Series(values).rolling(smoothing_window, center=True).mean()

            peaks, _ = find_peaks(smoothed_values, prominence=prominence, distance=distance)
            troughs, _ = find_peaks(-smoothed_values, prominence=prominence, distance=distance)

            boundaries = sorted(set(np.concatenate((peaks, troughs, [0, len(values)-1]))))

            for i in range(len(boundaries) - 1):
                start, end = boundaries[i], boundaries[i+1]
                segment = data.iloc[start:end + 1]

            plt.plot(time, values, alpha=0.7)
            plt.scatter(time.iloc[peaks], values[peaks], color='red', marker='o', label=f'{col} Peaks')
            plt.scatter(time.iloc[troughs], values[troughs], color='blue', marker='x', label=f'{col} Troughs')
            plt.show()

    def sort_path(self):
        self.datapath = sorted(self.datapath, key=lambda x: int(os.path.basename(x).split('.')[0]))




