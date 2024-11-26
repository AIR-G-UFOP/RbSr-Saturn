from module.core import *


class RDS:
    def __init__(self):
        super(RDS, self).__init__()

        self.line_index = None

        self.signal_data = {}  # signal sweeps of all files imported
        self.background_data = {}  # background sweeps of all files imported
        self.signal_mean = {}  # signal mean of all files imported
        self.background_mean = {}  # background mean of all files imported
        self.convertion_rate_data = None  # mean convertion rate of all files imported
        self.background_corr_data = {}  # signal background corrected of all files
        self.ratios_data = {}   # raw ratios of all files
        self.DF_data = None   # downhole fractionation of all files

    def background(self, dict_initial, mass_index):
        self.signal_data = {}
        self.background_data = {}
        self.signal_mean = {}
        self.background_mean = {}

        for name, data in dict_initial.items():
            isotope_standard_mean = data[mass_index].mean()

            index_counter = 0
            for value in data[mass_index]:
                if value > isotope_standard_mean:
                    self.line_index = index_counter
                    break
                else:
                    index_counter += 1

            row_count = len(data.index)
            if self.line_index == 0 or self.line_index == row_count:
                self.line_index = row_count // 2

            percent_subtracted_background = int(round((self.line_index * 0.1), 0))
            background_data = data.iloc[percent_subtracted_background:(self.line_index - percent_subtracted_background),1:]
            self.background_data[name] = background_data
            self.background_mean[name] = background_data.mean()

            percent_subtracted_signal = int(round(((row_count - self.line_index) * 0.1), 0))
            run_data = data.iloc[(self.line_index + percent_subtracted_signal):(row_count - percent_subtracted_signal),1:]
            self.signal_data[name] = run_data
            self.signal_mean[name] = run_data.mean()

        # self.signal = pd.DataFrame.from_dict(self.signal_mean, orient='index')
        # self.background = pd.DataFrame.from_dict(self.background_mean, orient='index')
        # self.convertion_rate = pd.DataFrame.from_dict(self.convertion_rate_data, orient='index', columns=['Convertion rate'])

    def background_subtraction(self):
        self.background_corr_data = {}

        for name, signal in self.signal_data.items():
            background = self.background_mean[name]
            self.background_corr_data[name] = signal.subtract(background, axis=1)

    def Rb_calculation(self):
        for name, data in self.background_corr_data.items():
            data['Rb87'] = data['Rb85'] * 0.38562

            self.background_corr_data[name] = data

    def raw_ratios(self, Sr_86, Sr_87, Sr_88):
        columns = ['Rb85/Sr86_raw', 'Sr87/Sr86_raw', 'Rb87/Sr86_raw', 'Sr87/Rb87_raw', 'Sr88/Sr86_raw', 'Rb87/Sr87_raw']
        self.ratios_data = {}

        for name, data in self.background_corr_data.items():
            ratio = pd.DataFrame(columns=columns, index=data.index)

            ratio['Rb85/Sr86_raw'] = data["Rb85"] / data[Sr_86]
            ratio['Sr87/Sr86_raw'] = data[Sr_87] / data[Sr_86]
            ratio['Rb87/Sr86_raw'] = data["Rb87"] / data[Sr_86]
            ratio['Sr87/Rb87_raw'] = data[Sr_87] / data["Rb87"]
            ratio['Sr88/Sr86_raw'] = data[Sr_88] / data[Sr_86]
            ratio['Rb87/Sr87_raw'] = data["Rb87"] / data[Sr_87]

            self.ratios_data[name] = ratio

    def convertion_rate(self, reacted):
        convertion_rate = {}
        for name, data in self.signal_mean.items():
            convertion_rate_i = data[reacted] / (data[reacted] + data["Sr88"]) * 100

            convertion_rate[name] = convertion_rate_i
        self.convertion_rate_data = pd.DataFrame.from_dict(convertion_rate, orient='index', columns=['Convertion rate'])

    def downhole_fractionation(self):
        self.DF_data = None
        DF = {}
        for name, data in self.ratios_data.items():
            # size = len(data) // 2
            # index = data.index[size]
            # half_1 = data.iloc[:index]
            # half_2 = data.iloc[index:]

            half_1, half_2 = np.array_split(data, 2)

            M = data.mean()
            M1 = half_1.mean()
            M2 = half_2.mean()

            df = (M2 - M1) / M * 100

            DF[name] = df

        self.DF_data = pd.DataFrame.from_dict(DF, orient='index', columns=['DF index'])