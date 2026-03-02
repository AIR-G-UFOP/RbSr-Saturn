import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from module.core import *
from module.utils import get_unique_name, remap_dataframe


class DRS:
    def __init__(self):
        super(DRS, self).__init__()

        self.line_index = None
        self.limits = {}
        self.crop_time = {}
        self.signal_data_raw = {}  # signal sweeps of all files imported
        self.signal_data = {}  # signal sweeps of all files imported
        self.background_data_raw = {}  # background sweeps of all files imported
        self.background_data = {}  # background sweeps of all files imported
        self.signal_mean = {}  # signal mean of all files imported
        self.background_mean = {}  # background mean of all files imported
        self.intermediate_data = {}
        self.convertion_rate_data = None  # mean convertion rate of all files imported
        self.DF_data = None  # downhole fractionation of all files
        self.background_uncertainty = {}
        self.ratios_uncertainty = {}
        self.excess_variance_drift = {}
        self.excess_variance_matrix = {}
        self.results = None

    def get_limits(self, dict_initial, mass_index):
        self.background_data_raw = {}
        self.signal_data_raw = {}
        for name, data in dict_initial.items():
            mass_index_mean = data[mass_index].mean()
            index_counter = 0
            for value in data[mass_index]:
                if value > mass_index_mean:
                    self.line_index = index_counter
                    break
                else:
                    index_counter += 1
            row_count = len(data.index)
            if self.line_index == 0 or self.line_index == row_count:
                self.line_index = row_count // 2
            percent_subtracted_background = int(round((self.line_index * 0.1), 0))
            percent_subtracted_signal = int(round(((row_count - self.line_index) * 0.1), 0))
            min_bkg = data.iloc[percent_subtracted_background, 0]
            max_bkg = data.iloc[self.line_index - percent_subtracted_background, 0]
            min_sig = data.iloc[self.line_index + percent_subtracted_signal, 0]
            max_sig = data.iloc[row_count - percent_subtracted_signal, 0]
            background_data = data.iloc[:self.line_index]
            run_data = data.iloc[self.line_index:]
            self.limits[name] = [min_bkg, max_bkg, min_sig, max_sig]
            self.crop_time[name] = [round(min_bkg, 1), round(min_bkg, 1),
                                    round(min_sig - data.iloc[self.line_index, 0], 1),
                                    round(min_sig - data.iloc[self.line_index, 0], 1)]
            self.background_data_raw[name] = background_data
            self.signal_data_raw[name] = run_data

    def background(self, dict_initial):
        self.background_data = {}
        self.signal_data = {}
        self.signal_mean = {}
        self.background_mean = {}
        for name, data in dict_initial.items():
            limits = self.limits[name]
            background_data_for_mean = data[(data.iloc[:, 0] >= limits[0]) & (data.iloc[:, 0] <= limits[1])]
            run_data_for_mean = data[(data.iloc[:, 0] >= limits[2]) & (data.iloc[:, 0] <= limits[3])]
            self.background_data[name] = background_data_for_mean
            self.signal_data[name] = run_data_for_mean
            self.background_mean[name] = background_data_for_mean.mean()
            self.background_uncertainty[name] = background_data_for_mean.std()
            self.signal_mean[name] = run_data_for_mean.mean()

    def background_subtraction(self):
        self.intermediate_data = {}
        for name, signal in self.signal_data.items():
            background = self.background_mean[name]
            background = background.drop('Time [Sec]')
            time = signal[['Time [Sec]']]
            signal = signal.drop(['Time [Sec]'], axis=1)
            self.intermediate_data[name] = pd.concat([time, signal.subtract(background, axis=1)], axis=1)

    def Rb_calculation(self):
        for name, data in self.intermediate_data.items():
            data['Rb87'] = data['Rb85'] * 0.38562
            self.intermediate_data[name] = data

    def raw_ratios(self, Sr_86, Sr_87, Sr_88):
        for name, data in self.intermediate_data.items():
            data['Rb85/Sr86_raw'] = data["Rb85"] / data[Sr_86]
            data['Sr87/Sr86_raw'] = data[Sr_87] / data[Sr_86]
            data['Rb87/Sr86_raw'] = data["Rb87"] / data[Sr_86]
            data['Sr87/Rb87_raw'] = data[Sr_87] / data["Rb87"]
            data['Sr88/Sr86_raw'] = data[Sr_88] / data[Sr_86]
            data['Rb87/Sr87_raw'] = data["Rb87"] / data[Sr_87]
            self.intermediate_data[name] = data

    def convertion_rate(self, reacted):
        convertion_rate = {}
        for name, data in self.signal_mean.items():
            convertion_rate_i = data[reacted] / (data[reacted] + data["Sr88"]) * 100
            convertion_rate[name] = convertion_rate_i
        self.convertion_rate_data = pd.DataFrame.from_dict(convertion_rate, orient='index',
                                                           columns=['Convertion rate']).sort_index()

    def downhole_fractionation_index(self):
        self.DF_data = None
        columns = ['Rb85/Sr86_raw', 'Sr87/Sr86_raw', 'Rb87/Sr86_raw', 'Sr87/Rb87_raw', 'Sr88/Sr86_raw',
                   'Rb87/Sr87_raw']
        DF = {}
        for name, data in self.intermediate_data.items():
            half_1, half_2 = np.array_split(data[columns], 2)
            M = data[columns].mean()
            M1 = half_1.mean()
            M2 = half_2.mean()
            df = (M2 - M1) / M * 100
            DF[name] = df
            data['Rb87/Sr86_DFindex'] = data['Rb87/Sr86_raw'] / M['Rb87/Sr86_raw']
            self.intermediate_data[name] = data
        self.DF_data = pd.DataFrame.from_dict(DF, orient='index').sort_index()

    def mass_bias_correction(self, groups):
        for group, names in groups.items():
            for run in names:
                data = self.intermediate_data[run]
                if 'Rb87/Sr86_DFcorr' in data.columns:
                    col = 'Rb87/Sr86_DFcorr'
                else:
                    col = 'Rb87/Sr86_raw'
                mass_bias = []
                Sr87_Sr86_mb = []
                Rb87_Sr86_mb = []
                for row in data.index.to_list():
                    mass_bias_i = np.log(((1 / 0.1194) / data.loc[row, 'Sr88/Sr86_raw'])) / np.log(87.90561 / 85.90926)
                    mass_bias.append(mass_bias_i)
                    Sr87_Sr86_mb_i = data.loc[row, 'Sr87/Sr86_raw'] * (86.90888 / 85.90926) ** mass_bias_i
                    Rb87_Sr86_mb_i = data.loc[row, col] * (86.91179 / 85.90926) ** mass_bias_i
                    Sr87_Sr86_mb.append(Sr87_Sr86_mb_i)
                    Rb87_Sr86_mb.append(Rb87_Sr86_mb_i)
                data['mb'] = mass_bias
                data['Sr87/Sr86_mb'] = Sr87_Sr86_mb
                data['Rb87/Sr86_mb'] = Rb87_Sr86_mb
                self.intermediate_data[run] = data

    def _compile_fractionation(self, names):
        group_data = [self.intermediate_data[name]['Rb87/Sr86_raw'].to_numpy() for name in names]
        group_time = [self.intermediate_data[name]['Time [Sec]'].to_numpy() for name in names]
        # Define common time grid
        time_min = min([t.min() for t in group_time])
        time_max = max(t.max() for t in group_time)
        avg_tick_time = np.mean([(t.max() - t.min()) / len(t) for t in group_time])
        num_ticks = int(np.round(time_max - time_min) / avg_tick_time) + 1
        common_time = np.linspace(time_min, time_max, num_ticks)
        # interpolate each dataset to common grid
        resampled_data = []
        for t, r in zip(group_time, group_data):
            interp = interp1d(t, r, kind='linear', bounds_error=False, fill_value=np.nan)
            resampled_data.append(interp(common_time))
        resampled_data = np.vstack(resampled_data)
        # Compute average fractionation
        avg_frac = np.nanmean(resampled_data, axis=0)
        nans = np.isnan(avg_frac)
        avg_frac = avg_frac[~nans]
        common_time = common_time[~nans]
        return common_time, avg_frac

    def downhole_fractionation(self, selections, method, s):
        cov = None
        Ft, Fr = self._compile_fractionation(selections)
        if method == 'Exponential':
            p0 = [1, -0.01, 100]
            parameters, cov = curve_fit(lambda t, a, b, c: a + b * np.exp(-c * t), Ft, Fr, p0=p0, ftol=1e-5,
                                        maxfev=5000)
        elif method == 'Linear':
            parameters, cov = curve_fit(lambda t, a, b: a + b * t, Ft, Fr, ftol=1e-5, maxfev=5000)
        elif method == 'Linear+exponential':
            parameters, cov = curve_fit(lambda t, a, b, c, d: a + b * t + c * np.exp(-d * t), Ft, Fr, ftol=1e-5,
                                        maxfev=5000)
        elif method == 'Smoothing spline':
            parameters = make_smoothing_spline(Ft, Fr, lam=s)
        return parameters, cov, Ft, Fr

    def downhole_fractionation_correction(self, selections, method, interp):
        col = 'Rb87/Sr86_raw'
        fcorr = 1
        for name in selections:
            data = self.intermediate_data[name]
            if method == 'Exponential':
                fcorr = (interp[0] + interp[1] * np.exp(-interp[2] * data.iloc[:, 0]))
            elif method == 'Linear':
                fcorr = (interp[0] + interp[1] * data.iloc[:, 0])
            elif method == 'Linear+exponential':
                fcorr = (interp[0] + interp[1] * data.iloc[:, 0] + interp[2] * np.exp(-interp[3] * data.iloc[:, 0]))
            elif method == 'Smoothing spline':
                fcorr = interp(data.iloc[:, 0])
            data['Rb87/Sr86_DFcorr'] = (data[col] / fcorr) * np.nanmean(fcorr)
            self.intermediate_data[name] = data

    def remove_correction(self, correction, groups):
        for group, names in groups.items():
            for name in names:
                try:
                    if correction == 'downhole':
                        self.intermediate_data[name].drop('Rb87/Sr86_DFcorr', axis=1, inplace=True)
                    elif correction == 'drift':
                        self.intermediate_data[name].drop('Rb87/Sr86_drift', axis=1, inplace=True)
                except KeyError:
                    pass

    def average_factor(self, groups, rm_name, database, all_names):
        rm_positions = groups[rm_name]
        rm_database = database[rm_name]
        rm_true_RbSr = rm_database['Rb87/Sr86']
        rm_true_SrSr = rm_database['Sr87/Sr86']
        rm_RbSr_sum = 0
        rm_SrSr_sum = 0
        x = []
        yRb = []
        yRb_std = []
        ySr = []
        ySr_std = []
        for name in rm_positions:
            rm_data = self.intermediate_data[name]
            x.append(all_names.index(name))
            if 'Rb87/Sr86_mb' in rm_data.columns:
                yRb_i = rm_data['Rb87/Sr86_mb'].mean()
                yRb_std_i = rm_data['Rb87/Sr86_mb'].std()
                ySr_i = rm_data['Sr87/Sr86_mb'].mean()
                ySr_std_i = rm_data['Sr87/Sr86_mb'].std()
            elif 'Rb87/Sr86_DFcorr' in rm_data.columns:
                yRb_i = rm_data['Rb87/Sr86_DFcorr'].mean()
                yRb_std_i = rm_data['Rb87/Sr86_DFcorr'].std()
                ySr_i = rm_data['Sr87/Sr86_raw'].mean()
                ySr_std_i = rm_data['Sr87/Sr86_raw'].std()
            else:
                yRb_i = rm_data['Rb87/Sr86_raw'].mean()
                yRb_std_i = rm_data['Rb87/Sr86_raw'].std()
                ySr_i = rm_data['Sr87/Sr86_raw'].mean()
                ySr_std_i = rm_data['Sr87/Sr86_raw'].std()
            rm_RbSr_sum += yRb_i
            rm_SrSr_sum += ySr_i
            yRb.append(yRb_i)
            yRb_std.append(yRb_std_i)
            ySr.append(ySr_i)
            ySr_std.append(ySr_std_i)
        return ({'Rb87/Sr86': rm_true_RbSr / (rm_RbSr_sum.mean() / len(rm_positions)),
                 'Sr87/Sr86': rm_true_SrSr / (rm_SrSr_sum.mean() / len(rm_positions))}, np.array(x),
                {'Rb87/Sr86': np.array(yRb), 'Sr87/Sr86': np.array(ySr)},
                {'Rb87/Sr86': np.array(yRb_std), 'Sr87/Sr86': np.array(ySr_std)})

    def polynomial_factor(self, groups, rm_name, all_positions, degree):
        models = {}
        selections = groups[rm_name]
        if 'Rb87/Sr86_mb' in self.intermediate_data[selections[0]].columns:
            ratios = ['Rb87/Sr86_mb', 'Sr87/Sr86_mb']
        elif 'Rb87/Sr86_DFcorr' in self.intermediate_data[selections[0]].columns:
            ratios = ['Rb87/Sr86_DFcorr', 'Sr87/Sr86_raw']
        else:
            ratios = ['Rb87/Sr86_raw', 'Sr87/Sr86_raw']
        r = ['Rb87/Sr86', 'Sr87/Sr86']
        y = {}
        y_std = {}
        x = []
        for i, ratio in enumerate(ratios):
            x = []
            y_r = []
            y_std_r = []
            for name in selections:
                x.append(all_positions.index(name))
                data = self.intermediate_data[name]
                ratio_i = data[ratio].mean()
                ratio_std_i = data[ratio].std()
                y_r.append(ratio_i)
                y_std_r.append(ratio_std_i)
            model = np.polyfit(x, y_r, degree)
            models[r[i]] = model
            y[r[i]] = np.array(y_r)
            y_std[r[i]] = np.array(y_std_r)
        return models, np.array(x), y, y_std

    def spline_factor(self, groups, rm_name, all_positions, s):
        splines = {}
        selections = groups[rm_name]
        if 'Rb87/Sr86_mb' in self.intermediate_data[selections[0]].columns:
            ratios = ['Rb87/Sr86_mb', 'Sr87/Sr86_mb']
        elif 'Rb87/Sr86_DFcorr' in self.intermediate_data[selections[0]].columns:
            ratios = ['Rb87/Sr86_DFcorr', 'Sr87/Sr86_raw']
        else:
            ratios = ['Rb87/Sr86_raw', 'Sr87/Sr86_raw']
        r = ['Rb87/Sr86', 'Sr87/Sr86']
        x = []
        y = {}
        y_std = {}
        for i, ratio in enumerate(ratios):
            x = []
            y_r = []
            y_std_r = []
            for name in selections:
                x.append(all_positions.index(name))
                data = self.intermediate_data[name]
                ratio_i = data[ratio].mean()
                ratio_std_i = data[ratio].std()
                y_r.append(ratio_i)
                y_std_r.append(ratio_std_i)
            spline = make_smoothing_spline(x, y_r, lam=s)
            splines[r[i]] = spline
            y[r[i]] = np.array(y_r)
            y_std[r[i]] = np.array(y_std_r)
        return splines, np.array(x), y, y_std

    def drift_correction(self, mtd, groups, factors, dg, true_values, all_positions):
        if mtd == 'Average':
            fc_RbSr = factors['Rb87/Sr86']
            fc_SrSr = factors['Sr87/Sr86']
            for group, names in groups.items():
                for name in names:
                    data = self.intermediate_data[name]
                    if 'Rb87/Sr86_mb' in data.columns:
                        data['Rb87/Sr86_drift'] = data['Rb87/Sr86_mb'] * fc_RbSr
                        data['Sr87/Sr86_drift'] = data['Sr87/Sr86_mb'] * fc_SrSr
                    elif 'Rb87/Sr86_DFcorr' in data.columns:
                        data['Rb87/Sr86_drift'] = data['Rb87/Sr86_DFcorr'] * fc_RbSr
                        data['Sr87/Sr86_drift'] = data['Sr87/Sr86_raw'] * fc_SrSr
                    else:
                        data['Rb87/Sr86_drift'] = data['Rb87/Sr86_raw'] * fc_RbSr
                        data['Sr87/Sr86_drift'] = data['Sr87/Sr86_raw'] * fc_SrSr
                    self.intermediate_data[name] = data

        else:
            for group, names in groups.items():
                for name in names:
                    data = self.intermediate_data[name]
                    x = all_positions.index(name)
                    if 'Rb87/Sr86_mb' in data.columns:
                        ratios = ['Rb87/Sr86_mb', 'Sr87/Sr86_mb']
                    elif 'Rb87/Sr86_DFcorr' in data.columns:
                        ratios = ['Rb87/Sr86_DFcorr', 'Sr87/Sr86_raw']
                    else:
                        ratios = ['Rb87/Sr86_raw', 'Sr87/Sr86_raw']
                    for ratio in ratios:
                        old = re.search(r'_(raw|mb|DFcorr)$', ratio).group(0)
                        r_model = 0
                        if mtd == 'Polynomial':
                            for i, f_i in enumerate(factors[ratio.replace(old, '')]):
                                r_model += f_i * x ** (dg - i)
                        else:
                            spline = factors[ratio.replace(old, '')]
                            r_model = spline(x)
                        true = true_values[ratio.replace(old, '')]
                        data[ratio.replace(old, '_drift')] = data[ratio] * true / r_model
                        self.intermediate_data[name] = data

    def _matrix_factor(self, groups, rm, db):
        rm_selections = groups[rm]
        sr_i = db[rm]['Sr87/Sr86_i']
        age = db[rm]['Age']
        lam = 1.3972
        sr_ratios = [self.intermediate_data[name]['Sr87/Sr86_drift'].mean() for name in rm_selections]
        rb_ratios = [self.intermediate_data[name]['Rb87/Sr86_drift'].mean() for name in rm_selections]
        sr_avg = np.mean(sr_ratios)
        rb_avg = np.mean(rb_ratios)
        rb_calc = (sr_avg - sr_i) / (np.exp(lam * age * 1e-5) - 1)
        return rb_avg / rb_calc

    def matrix_correction(self, groups, rm_name, database):
        rb_fc = self._matrix_factor(groups, rm_name, database)
        for group, names in groups.items():
            for name in names:
                data = self.intermediate_data[name]
                ratio = data['Rb87/Sr86_drift']
                data['Rb87/Sr86_matrix'] = ratio / rb_fc
                self.intermediate_data[name] = data

    @staticmethod
    def _mswd_with_excess(e2, n, x, sd):
        """
        iterative function that calculates the MSWD varying the excess variance until it converges or not
        e2: excess variance, float
        n: number of points, int
        x: ratio, list
        sd: standard deviation, list
        """
        total_var = np.array(sd)**2 + e2
        w_total = 1 / total_var
        x_bar_total = np.sum(w_total * np.array(x)) / np.sum(w_total)
        mswd_total = np.sum(w_total * (np.array(x) - x_bar_total)**2) / (n - 1)
        return mswd_total - 1.0

    def compute_excess_scatter(self, groups, rm, mode):
        selections = groups[rm]
        if mode == 'drift':
            ratios = ['Rb87/Sr86_drift', 'Sr87/Sr86_drift']
        else:
            ratios = ['Rb87/Sr86_matrix', 'Sr87/Sr86_matrix']
        n = len(selections)
        for ratio in ratios:
            x = []
            sd = []
            w = []
            for selection in selections:
                data_i = self.intermediate_data[selection]
                x_i = data_i.loc[:, ratio].mean()    # mean ratios
                sd_i = data_i.loc[:, ratio].std()    # standard deviation ratios
                w_i = 1 / sd_i**2   # weight ratios
                x.append(x_i)
                sd.append(sd_i)
                w.append(w_i)
            x_bar = np.sum(np.array(w) * np.array(x)) / np.sum(np.array(w)) # weighted mean ratios
            mswd = np.sum(np.array(w) * (np.array(x) - x_bar)**2) / (n - 1)
            if mswd > 1:
                try:
                    """
                    root_scalar finds the value of e2 (excess^2) that makes _mswd_with_excess = 0
                    """
                    root_result = root_scalar(lambda e2: self._mswd_with_excess(e2, n, x, sd),
                                              bracket=[0, (np.max(x) - np.min(x))**2])
                    excess_sqr = root_result.root if root_result.converged else 0
                except ValueError:
                    excess_sqr = 0   # excess scatter
            else:
                excess_sqr = 0
            if mode == 'drift':
                self.excess_variance_drift[ratio.split('_')[0]] = np.sqrt(excess_sqr)
            else:
                self.excess_variance_matrix[ratio.split('_')[0]] = np.sqrt(excess_sqr)

    def propagate_internal_uncertainties(self, groups, link):
        pass

    def compute_results(self, groups, link):
        mean = {}
        se = {}
        std = {}
        rho = {}
        for group, names in groups.items():
            for name in names:
                data = self.intermediate_data[name]
                if 'Rb87/Sr86_matrix' in data.columns:
                    cols = ['Rb87/Sr86_matrix', 'Sr87/Sr86_drift']
                elif 'Rb87/Sr86_drift' in data.columns:
                    cols = ['Rb87/Sr86_drift', 'Sr87/Sr86_drift']
                elif 'Rb87/Sr86_mb' in data.columns:
                    cols = ['Rb87/Sr86_mb', 'Sr87/Sr86_mb']
                elif 'Rb87/Sr86_DFcorr' in data.columns:
                    cols = ['Rb87/Sr86_DFcorr', 'Sr87/Sr86_raw']
                else:
                    cols = ['Rb87/Sr86_raw', 'Sr87/Sr86_raw']
                result_cols = ['Rb87/Sr86', 'Sr87/Sr86']
                data_cols = data.loc[:, cols]
                data_mean = data_cols.mean().rename({old: new for old, new in zip(cols, result_cols)})
                data_std = 2 * data_cols.std().rename({old: new + ' 2SD' for old, new in zip(cols, result_cols)})
                data_se = 2 * data_cols.sem().rename({old: new + ' 2SE' for old, new in zip(cols, result_cols)})
                RbSr = data_cols[cols[0]]
                SrSr = data_cols[cols[1]]
                RbSr_SrSr_rho = np.corrcoef(RbSr, SrSr)[0, 1]
                mean[name] = data_mean
                se[name] = data_se
                std[name] = data_std
                rho[name] = RbSr_SrSr_rho
        r_mean = pd.DataFrame(mean).T
        r_std = pd.DataFrame(std).T
        r_se = pd.DataFrame(se).T
        r_rho = pd.DataFrame(data=rho, index=['Rho']).T
        results = pd.concat([r_mean, r_se, r_std, r_rho], axis=1)
        self.results = results[['Rb87/Sr86', 'Rb87/Sr86 2SE', 'Rb87/Sr86 2SD', 'Sr87/Sr86', 'Sr87/Sr86 2SE', 'Sr87/Sr86 2SD', 'Rho']]
        self.results = remap_dataframe(self.results, link)

    def calculate_ratio_statistics(self, groups, link):
        mean = {}
        se = {}
        std = {}
        s = {}
        ratios = ["Rb85/Sr86_raw", "Rb87/Sr86_raw", "Sr87/Sr86_raw", "Rb87/Sr86_DFcorr", "Rb87/Sr86_mb",
                  "Sr87/Sr86_mb", "Rb87/Sr86_drift", "Sr87/Sr86_drift", "Rb87/Sr86_matrix"]
        for group, names in groups.items():
            for name in names:
                data = self.intermediate_data[name]
                data = data.loc[:, ratios]
                data_mean = data.mean().rename({ratio: ratio + '_mean' for ratio in ratios})
                data_std = data.std().rename({ratio: ratio + '_std' for ratio in ratios})
                data_se = data.sem().rename({ratio: ratio + '_se' for ratio in ratios})
                data_s = pd.Series(2 * (data_se.values / data_mean.values) * 100,
                                   index=[ratio + '_2s%' for ratio in ratios])
                mean[name] = data_mean
                std[name] = data_std
                se[name] = data_se
                s[name] = data_s
        mean_df = pd.DataFrame(mean).T
        std_df = pd.DataFrame(std).T
        se_df = pd.DataFrame(se).T
        s_df = pd.DataFrame(s).T
        ratios_export = ["Rb85/Sr86_raw_mean", "Rb85/Sr86_raw_std", "Rb85/Sr86_raw_se", "Rb85/Sr86_raw_2s%",
                         "Rb87/Sr86_raw_mean", "Rb87/Sr86_raw_std", "Rb87/Sr86_raw_se", "Rb87/Sr86_raw_2s%",
                         "Sr87/Sr86_raw_mean", "Sr87/Sr86_raw_std", "Sr87/Sr86_raw_se", "Sr87/Sr86_raw_2s%",
                         "Rb87/Sr86_DFcorr_mean", "Rb87/Sr86_DFcorr_std", "Rb87/Sr86_DFcorr_se", "Rb87/Sr86_DFcorr_2s%",
                         "Rb87/Sr86_mb_mean", "Rb87/Sr86_mb_std", "Rb87/Sr86_mb_se", "Rb87/Sr86_mb_2s%",
                         "Sr87/Sr86_mb_mean", "Sr87/Sr86_mb_std", "Sr87/Sr86_mb_se", "Sr87/Sr86_mb_2s%",
                         "Rb87/Sr86_drift_mean", "Rb87/Sr86_drift_std", "Rb87/Sr86_drift_se", "Rb87/Sr86_drift_2s%",
                         "Sr87/Sr86_drift_mean", "Sr87/Sr86_drift_std", "Sr87/Sr86_drift_se", "Sr87/Sr86_drift_2s%",
                         "Rb87/Sr86_matrix_mean", "Rb87/Sr86_matrix_std", "Rb87/Sr86_matrix_se", "Rb87/Sr86_matrix_2s%"]
        ratio_stats = pd.concat([mean_df, se_df, std_df, s_df], axis=1)[ratios_export]
        ratios_uncertainty = remap_dataframe(ratio_stats, link)
        with pd.ExcelWriter('stats_selected_ratios.xlsx') as writer:
            ratios_uncertainty.to_excel(writer)
        print("Ratio statistics saved to 'stats_selected_ratios.xlsx'")

