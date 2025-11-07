import random

import numpy as np

from module.core import *
from ui.signalDialog import Ui_Signal
from module.utils import get_unique_name, get_log_name


class SignalDialog(QDialog):
    signal_return = pyqtSignal(bool, dict, dict)

    def __init__(self, parent, raw, index, crop, all_points, channels, limits, link, log):
        super(SignalDialog, self).__init__(parent)

        self.ui = Ui_Signal()
        self.ui.setupUi(self)

        self.parent = parent
        self.setParent(parent)
        self.setup_position()

        self.ui.graphicsView.setBackground('w')
        self.ui.graphicsView.showGrid(x=True, y=True)
        self.raw_data = raw
        self.index = index
        self.crop = crop
        self.initial_crop = crop
        self.all_points = all_points
        self.channels = channels
        self.limits = limits
        self.initial_limits = limits
        self.name_links = link
        self.names_log = log
        self.viewboxes = {}
        self.curves = {}
        self.axes = {}
        self.channel_selected = []
        self.pen = {}
        self.spot_name = None
        self.region_sig = None
        self.region_bkg = None

        self.ui.comboBox_spot.currentTextChanged.connect(self.plot_data)
        self.ui.listWidget_channels.viewport().installEventFilter(self)
        self.ui.btn_cancel.clicked.connect(self.btn_clicked)
        self.ui.btn_ok.clicked.connect(self.btn_clicked)
        self.ui.bkgStartCrop.valueChanged.connect(self.get_limits_from_crops)
        self.ui.bkgEndCrop.valueChanged.connect(self.get_limits_from_crops)
        self.ui.sigStartCrop.valueChanged.connect(self.get_limits_from_crops)
        self.ui.sigEndCrop.valueChanged.connect(self.get_limits_from_crops)

        self.plot = self.ui.graphicsView.getPlotItem()
        self.plot.setLabel('bottom', 'Time (sec)')
        self.plot.vb.sigResized.connect(self.updateViews)

        self.create_regions_of_interest()
        self.fill_combo()
        self.fill_list()
        self.setup_spinBoxes()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == QtCore.Qt.LeftButton:
                if self.ui.listWidget_channels.viewport() == obj:
                    selected = self.ui.listWidget_channels.selectedItems()
                    self.select_channels(selected)
                return super().eventFilter(obj, event)
        else:
            return super().eventFilter(obj, event)

    def updateViews(self):
        if self.plot.scene() is None:
            return
        rect = self.plot.vb.sceneBoundingRect()
        for vb in self.viewboxes.values():
            if vb != self.plot.vb:
                vb.setGeometry(rect)
                vb.linkedViewChanged(self.plot.vb, vb.XAxis)
                vb.enableAutoRange(axis=pg.ViewBox.XYAxes, enable=True)

    def setup_position(self):
        x = self.parent.pos().x() + self.parent.width() // 2 - self.width() // 2
        y = self.parent.pos().y() + self.parent.height() // 2 - self.height() // 2
        self.move(x, y)

    def closeEvent(self, event):
        if self.sender().objectName() != 'btn_cancel' and self.sender().objectName() != 'btn_ok':
            self.signal_return.emit(False, self.initial_limits, self.initial_crop)
            self.close()

    def btn_clicked(self):
        btn = self.sender().objectName()
        self.close()
        if btn == 'btn_cancel':
            self.signal_return.emit(False, self.initial_limits, self.initial_crop)
        else:
            self.signal_return.emit(True, self.limits, self.crop)

    def fill_combo(self):
        if self.all_points:
            names = get_log_name(self.name_links, self.all_points, self.names_log)
            self.ui.comboBox_spot.addItems(names)

    def fill_list(self):
        if self.channels:
            self.ui.listWidget_channels.addItems(self.channels[1:])
            self.ui.listWidget_channels.setCurrentRow(0)
            self.select_channels(self.ui.listWidget_channels.selectedItems())

    def setup_spinBoxes(self):
        self._set_spinBoxes_signal(True)
        name = get_unique_name(self.name_links, [self.spot_name])[0]
        self.ui.bkgStartCrop.setValue(self.crop[name][0])
        self.ui.bkgEndCrop.setValue(self.crop[name][1])
        self.ui.sigStartCrop.setValue(self.crop[name][2])
        self.ui.sigEndCrop.setValue(self.crop[name][3])
        self._set_spinBoxes_signal(False)

    def select_channels(self, items):
        self.channel_selected = [item.text() for item in items]
        if len(self.channel_selected) > 0:
            self.plot_data()
        else:
            self._clear_all_curves()

    def plot_data(self):
        if self.raw_data:
            if self.viewboxes:
                vb = self.viewboxes.copy()
                for channel in vb.keys():
                    if channel not in self.channel_selected:
                        self._remove_curve(channel)
            for channel in self.channel_selected:
                if channel in self.viewboxes.keys():
                    self._update_curve(channel)
                else:
                    self._add_curve(channel)
                self.updateViews()
            spot_name = self.ui.comboBox_spot.currentText()
            if self.sender() == self.ui.comboBox_spot and spot_name != self.spot_name:
                self.spot_name = spot_name
                self._update_regions_of_interest()
                self.setup_spinBoxes()

    def _get_data(self, channel, label):
        data = self.raw_data[label]
        x = data.loc[:, data.columns[0]].to_numpy()
        y = data.loc[:, channel].to_numpy()
        return x, y

    def _colourgen(self, channel):
        if channel not in self.pen.keys():
            colour = '#' + ''.join([random.choice('ABCDE0123456789') for i in range(6)])
            self.pen[channel] = colour

    def _add_curve(self, channel):
        name_log = self.ui.comboBox_spot.currentText()
        unique_name = get_unique_name(self.name_links, [name_log])[0]
        x, y = self._get_data(channel, unique_name)
        self._colourgen(channel)

        if not self.viewboxes:
            vb = self.plot.vb
            axis = self.plot.getAxis('left')
            self.region_sig.show()
            self.region_bkg.show()
        else:
            vb = pg.ViewBox()
            axis = pg.AxisItem('right')
            self.plot.layout.addItem(axis, 2, len(self.viewboxes.keys())+1)
            self.plot.scene().addItem(vb)
            axis.linkToView(vb)
            vb.setXLink(self.plot)
            axis.setZValue(-1e4)
        axis.setLabel(channel, color=self.pen[channel])
        curve = pg.PlotCurveItem(x, y, pen=pg.mkPen(color=self.pen[channel], width=1.5))
        vb.addItem(curve)
        self.viewboxes[channel] = vb
        self.axes[channel] = axis
        self.curves[channel] = curve

    def _update_curve(self, channel):
        name_log = self.ui.comboBox_spot.currentText()
        unique_name = get_unique_name(self.name_links, [name_log])[0]
        x, y = self._get_data(channel, unique_name)
        curve = self.curves[channel]
        curve.setData(x, y)

    def _remove_curve(self, channel):
        curve = self.curves.pop(channel)
        axis = self.axes.pop(channel)
        vb = self.viewboxes.pop(channel)
        self.pen.pop(channel)

        if vb != self.plot.vb:
            self.plot.scene().removeItem(vb)
            self.plot.layout.removeItem(axis)
            vb.removeItem(curve)
            del vb, axis
        else:
            try:
                new_channel = next(iter(self.viewboxes))
                new_curve = self.curves[new_channel]
                new_vb = self.curves[new_channel]
                new_axis = self.axes[new_channel]

                self.plot.scene().removeItem(new_vb)
                self.plot.layout.removeItem(new_axis)
                vb.removeItem(curve)
                vb.addItem(new_curve)
                axis.setLabel(new_channel, color=self.pen[new_channel])

                self.axes[new_channel] = axis
                self.curves[new_channel] = new_curve
                self.viewboxes[new_channel] = self.plot.vb
            except StopIteration:
                axis.setLabel('')
                vb.removeItem(curve)
        del curve

        self.updateViews()

    def _clear_all_curves(self):
        curves = self.curves.copy()
        for channel in curves.keys():
            self._remove_curve(channel)
        self.region_sig.hide()
        self.region_bkg.hide()

    def create_regions_of_interest(self):
        self.region_sig = pg.LinearRegionItem(brush=(145, 141, 138, 30), pen=(122, 118, 115), swapMode="block",
                                              hoverPen=(145, 141, 138, 5))
        self.region_bkg = pg.LinearRegionItem(brush=(145, 141, 138, 30), pen=(89, 87, 86), swapMode="block",
                                              hoverPen=(145, 141, 138, 93))
        self.region_sig.setZValue(10)
        self.region_bkg.setZValue(10)
        self.region_sig.hide()
        self.region_bkg.hide()
        self.region_sig.sigRegionChangeFinished.connect(self._get_regions_of_interest_limits)
        self.region_bkg.sigRegionChangeFinished.connect(self._get_regions_of_interest_limits)
        self.plot.vb.addItem(self.region_sig, ignoreBounds=True)
        self.plot.vb.addItem(self.region_bkg, ignoreBounds=True)

    def _update_regions_of_interest(self):
        self._set_regions_of_interest_signal(True)
        name = get_unique_name(self.name_links, [self.spot_name])[0]
        data = self.raw_data[name]
        rows = len(data.index)
        try:
            limits = self.limits[name]
            min_bkg = limits[0]
            max_bkg = limits[1]
            min_sig = limits[2]
            max_sig = limits[3]
        except KeyError:
            p_sig = int(round(((rows - self.index) * 0.1), 0))
            p_bkg = int(round((self.index * 0.1), 0))
            min_bkg = data.iloc[p_bkg, 0]
            max_bkg = data.iloc[(self.index - p_bkg), 0]
            min_sig = data.iloc[(self.index + p_sig), 0]
            max_sig = data.iloc[(rows - p_sig), 0]
        self.region_sig.setRegion([min_sig, max_sig])
        self.region_bkg.setRegion([min_bkg, max_bkg])
        for name in self.all_points:
            if name not in self.limits.keys():
                self.limits[name] = [min_bkg, max_bkg, min_sig, max_sig]
        self.region_sig.show()
        self.region_bkg.show()
        self._set_regions_of_interest_signal(False)

    def _set_regions_of_interest_signal(self, block):
        self.region_sig.blockSignals(block)
        self.region_bkg.blockSignals(block)

    def _set_spinBoxes_signal(self, block):
        self.ui.bkgStartCrop.blockSignals(block)
        self.ui.bkgEndCrop.blockSignals(block)
        self.ui.sigStartCrop.blockSignals(block)
        self.ui.sigEndCrop.blockSignals(block)

    def _get_regions_of_interest_limits(self):
        min_sig, max_sig = self.region_sig.getRegion()
        min_bkg, max_bkg = self.region_bkg.getRegion()
        name = get_unique_name(self.name_links, [self.spot_name])[0]
        previous_limits = self.limits[name]
        if min_bkg >= min_sig:
            min_bkg = previous_limits[0]
            max_bkg = previous_limits[1]
            min_sig = previous_limits[2]
            max_sig = previous_limits[3]
        elif max_bkg >= min_sig:
            min_sig = max_bkg + 1
        self._set_regions_of_interest_signal(True)
        self.region_bkg.setRegion([min_bkg, max_bkg])
        self.region_sig.setRegion([min_sig, max_sig])
        self._set_regions_of_interest_signal(False)
        if self.ui.checkBox_applyToAll.isChecked():
            for name in self.all_points:
                self.limits[name] = [min_bkg, max_bkg, min_sig, max_sig]
        else:
            self.limits[name] = [min_bkg, max_bkg, min_sig, max_sig]
        self._get_limits_from_data()

    def get_limits_from_crops(self):
        bkg_start_crop = self.ui.bkgStartCrop.value()
        bkg_end_crop = self.ui.bkgEndCrop.value()
        sig_start_crop = self.ui.sigStartCrop.value()
        sig_end_crop = self.ui.sigEndCrop.value()

        if self.ui.checkBox_applyToAll.isChecked():
            names = self.all_points
        else:
            names = get_unique_name(self.name_links, [self.spot_name])

        for name in names:
            t_values = self.raw_data[name].iloc[:, 0].values
            previous_limits = self.limits[name]
            previous_crop = self.crop[name]
            if bkg_start_crop != previous_crop[0]:
                start_bkg = t_values[0] + bkg_start_crop
                min_bkg = t_values[np.abs(t_values - start_bkg).argmin()]
            else:
                min_bkg = previous_limits[0]
                bkg_start_crop = self.crop[name][0]
            if bkg_end_crop != previous_crop[1]:
                end_bkg = t_values[self.index] - bkg_end_crop
                max_bkg = t_values[np.abs(t_values - end_bkg).argmin()]
            else:
                max_bkg = previous_limits[1]
                bkg_end_crop = self.crop[name][1]
            if sig_start_crop != previous_crop[2]:
                start_sig = t_values[self.index] + sig_start_crop
                min_sig = t_values[np.abs(t_values - start_sig).argmin()]
            else:
                min_sig = previous_limits[2]
                sig_start_crop = self.crop[name][2]
            if sig_end_crop != previous_crop[3]:
                end_sig = t_values[-1] - sig_end_crop
                max_sig = t_values[np.abs(t_values - end_sig).argmin()]
            else:
                max_sig = previous_limits[3]
                sig_end_crop = self.crop[name][3]

            self.limits[name] = [min_bkg, max_bkg, min_sig, max_sig]
            self.crop[name] = [bkg_start_crop, bkg_end_crop, sig_start_crop, sig_end_crop]

        current_spot = get_unique_name(self.name_links, [self.spot_name])[0]
        self._set_regions_of_interest_signal(True)
        self.region_bkg.setRegion([self.limits[current_spot][0], self.limits[current_spot][1]])
        self.region_sig.setRegion([self.limits[current_spot][2], self.limits[current_spot][3]])
        self._set_regions_of_interest_signal(False)

    def _get_limits_from_data(self):
        if self.ui.checkBox_applyToAll.isChecked():
            names = self.all_points
        else:
            names = get_unique_name(self.name_links, [self.spot_name])
        for name in names:
            limits = np.array(self.limits[name])
            t_values = self.raw_data[name].iloc[:, 0].values
            min_bkg = t_values[np.abs(t_values - limits[0]).argmin()]
            max_bkg = t_values[np.abs(t_values - limits[1]).argmin()]
            min_sig = t_values[np.abs(t_values - limits[2]).argmin()]
            max_sig = t_values[np.abs(t_values - limits[3]).argmin()]
            self.limits[name] = [min_bkg, max_bkg, min_sig, max_sig]
