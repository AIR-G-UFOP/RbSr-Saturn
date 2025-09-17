import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from module.core import *


class HandleFiles:
    def __init__(self, datapath, counter):
        super(HandleFiles, self).__init__()

        self.datapath = datapath
        self.file_start_index = None
        self.file_end_index = None
        self.data_head = None
        self.alldatafiles = {}
        self.counter = counter
        self.run_names = []

    def open_datafiles(self):
        for n, data_path in enumerate(self.datapath):
            run_name = os.path.basename(data_path)
            name_without_extention = os.path.splitext(run_name)[0]

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

            unique_name = name_without_extention + "_" + str(self.counter)
            self.alldatafiles[unique_name] = filedata
            self.run_names.append(unique_name)

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

    def handle_log(self, log):
        sequence = [x for x in log[' Sequence Number'].to_list() if not pd.isna(x)]
        names = [x for x in log[' Comment'].to_list() if not pd.isna(x)]

        return dict(zip(names, sequence))

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

