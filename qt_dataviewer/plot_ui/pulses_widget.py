import logging
import traceback
from typing import Union, Dict, Any

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets

from qt_dataviewer.utils.qt_utils import qt_log_exception


logger = logging.getLogger(__name__)


# default colors cycle: see matplotlib CN colors.
color_cycle = [
    '#1f77b4',  # muted blue
    '#ff7f0e',  # safety orange
    '#2ca02c',  # cooked asparagus green
    '#d62728',  # brick red
    '#9467bd',  # muted purple
    '#8c564b',  # chestnut brown
    '#e377c2',  # raspberry yogurt pink
    '#7f7f7f',  # middle gray
    '#bcbd22',  # curry yellow-green
    '#17becf'   # blue-teal
]

color_list = [pg.mkColor(cl) for cl in color_cycle]


class PulsesWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        pulses_layout = QtWidgets.QVBoxLayout(self)
        self.pulses_layout = pulses_layout
        self.active = False
        self.pulses = None

    def set_active(self, active):
        self.active = active
        if active and self.needs_plotting:
            self._plot_pulses()

    @qt_log_exception
    def set_pulses(self, pulses: Union[None, Dict[str, Any]]):
        for i in range(self.pulses_layout.count()):
            widget = self.pulses_layout.itemAt(i).widget()
            widget.deleteLater()
        self.pulses = pulses
        if pulses is not None:
            self.needs_plotting = True
            self._plot_pulses()

    def _plot_pulses(self):
        if not self.active:
            return
        self.needs_plotting = False
        pulses = self.pulses
        try:
            tab_widget = self.parent().parent()
            tab_widget.setCursor(QtCore.Qt.WaitCursor)
            pulse_plot = pg.PlotWidget()
            pulse_plot.addLegend()
            pulse_plot.getAxis('bottom').enableAutoSIPrefix(False)
            pc_keys = [k for k, v in pulses.items() if k.startswith('pc') and v is not None]
            gate_keys = set([key for pc in pc_keys for key in pulses[pc] if not key.startswith('_')])
            try:
                baseband_freqs = pulses['LOs']
            except KeyError:
                pass
            for (j, name) in enumerate(gate_keys):
                t0 = 0
                x_plot = list()
                y_plot = list()
                # @@@ handle acquisition channels, condition channels
                # @@@ add check boxes for channels
                for pc in pc_keys:
                    legend_name = name.replace('_baseband','').replace('_pulses','')
                    try:
                        end_time = pulses[pc]['_total_time']
                        while isinstance(end_time, list):
                            end_time = end_time[-1]
                    except:
                        end_time = max([x['stop'] for y in pulses[pc].values() for x in y.values()])
                    try:
                        pulses[pc][name]
                    except:
                        t0 += end_time
                        continue

                    if 'baseband' in name:
                        timepoints = set([x[key] for x in pulses[pc][name].values() for key in ['start','stop']])
                        timepoints.add(end_time)
                        for tp in sorted(timepoints):
                            point1 = 0
                            point2 = 0
                            for seg_name, seg_dict in pulses[pc][name].items():
                                if seg_dict['start'] < tp and seg_dict['stop'] > tp: # active segement
                                    point1 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_start'] ) + seg_dict['v_start']
                                    point2 += tp/(seg_dict['stop'] - seg_dict['start']) * ( seg_dict['v_stop'] - seg_dict['v_start'] ) + seg_dict['v_start']
                                elif seg_dict['start'] == tp:
                                    point2 += seg_dict['v_start']
                                elif seg_dict['stop'] == tp:
                                    point1 += seg_dict['v_stop']
                            x_plot += [tp + t0, tp + t0]
                            y_plot += [point1, point2]

                    elif 'pulses' in name:
                        try:
                            baseband = baseband_freqs[name.replace('_pulses','')]
                        except:
                            logger.warning('No baseband frequency found, assuming 0')
                            baseband = 0

                        x = []
                        y = []
                        for seg_name, seg_dict in pulses[pc][name].items():
                            x_ar = np.arange(seg_dict['start'], seg_dict['stop'])
                            xx_ar = x_ar-seg_dict['start']
                            f_rl = (seg_dict['frequency'] - baseband)/1e9
                            y_ar = np.sin(2*np.pi*f_rl*xx_ar+seg_dict['start_phase'])*seg_dict['amplitude']
                            x = x + [seg_dict['start']] + list(x_ar) + [seg_dict['stop']]
                            y = y + [0] + list(y_ar) + [0]
                            x_plot = x
                            y_plot = y
                    t0 += end_time

                pulse_plot.setLabel('left', 'Voltage', 'mV')
                pulse_plot.setLabel('bottom', 'Time', 'ns')
                pulse_plot.plot(x_plot, y_plot, pen = color_list[j%len(color_list)], name = legend_name)

            self.pulses_layout.addWidget(pulse_plot, 1)
        except Exception:
            logger.error("Couldn't plot pulses", exc_info=True)
            message = traceback.format_exc()
            error_message = QtWidgets.QLabel(message)
            error_message.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.pulses_layout.addWidget(error_message, 1)
        finally:
            tab_widget.setCursor(QtCore.Qt.ArrowCursor)
