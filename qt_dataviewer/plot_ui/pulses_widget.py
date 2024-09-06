import logging
import traceback

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
    def set_pulses(self, pulses: dict[str, any] | None):
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
            pulse_plot.setLabel('left', 'Voltage', 'mV')
            pulse_plot.setLabel('bottom', 'Time', 'ns')
            self.pulse_plot = pulse_plot

            pc_keys = [k for k, v in pulses.items() if k.startswith('pc') and v is not None]
            gate_keys = sorted(set([key for pc in pc_keys for key in pulses[pc] if not key.startswith('_')]))

            end_times = {}
            for pc in pc_keys:
                if 'branch_0' in pulses[pc]:
                    seg = pulses[pc]['branch_0']
                else:
                    seg = pulses[pc]
                try:
                    end_time = seg['_total_time']
                    while isinstance(end_time, list):
                        end_time = end_time[-1]
                except:
                    end_time = max([x['stop'] for y in seg.values() for x in y.values()])
                end_times[pc] = end_time

            try:
                lo_freqs = pulses['LOs']
            except KeyError:
                pass

            # TODO handle acquisition channels
            # TODO add check boxes for channels
            for (j, name) in enumerate(gate_keys):
                if name.endswith('_baseband'):
                    old_format = False
                    for pc in pc_keys:
                        if name in pc:
                            old_format = 'index_start' in pulses[pc][name]['p0']
                            break
                    if old_format:
                        self._plot_baseband_old(pulses, pc_keys, end_times, name, color=color_list[j%len(color_list)])
                    else:
                        self._plot_baseband(pulses, pc_keys, end_times, name, color=color_list[j%len(color_list)])
                elif name.endswith('_pulses'):
                    try:
                        lo_frequency = lo_freqs[name[:-7]]
                    except:
                        lo_frequency = None
                    self._plot_mw_pulses(pulses, pc_keys, end_times, name, color_list[j%len(color_list)], lo_frequency)

            self.pulses_layout.addWidget(pulse_plot, 1)
        except Exception:
            logger.error("Couldn't plot pulses", exc_info=True)
            message = traceback.format_exc()
            error_message = QtWidgets.QLabel(message)
            error_message.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.pulses_layout.addWidget(error_message, 1)
        finally:
            tab_widget.setCursor(QtCore.Qt.ArrowCursor)


    def _plot_baseband_old(self, pulses, pc_keys, end_times, name, color):
        t0 = 0
        x_plot = list()
        y_plot = list()
        for pc in pc_keys:
            end_time = end_times[pc]

            try:
                seg_pulses = pulses[pc][name]
            except:
                t0 += end_time
                continue

            timepoints = set([x[key] for x in seg_pulses.values() for key in ['start','stop']])
            timepoints.add(end_time)
            for tp in sorted(timepoints):
                point1 = 0
                point2 = 0
                for seg_name, seg_dict in seg_pulses.items():
                    if seg_dict['start'] < tp and seg_dict['stop'] > tp: # active segement
                        offset = tp/(seg_dict['stop'] - seg_dict['start']) * (seg_dict['v_stop'] - seg_dict['v_start']) + seg_dict['v_start']
                        point1 += offset
                        point2 += offset
                    elif seg_dict['start'] == tp:
                        point2 += seg_dict['v_start']
                    elif seg_dict['stop'] == tp:
                        point1 += seg_dict['v_stop']
                x_plot += [tp + t0, tp + t0]
                y_plot += [point1, point2]
            t0 += end_time

        legend_name = name[:-9]
        self.pulse_plot.plot(x_plot, y_plot, pen=color, name=legend_name)

    def _plot_baseband(self, pulses, pc_keys, end_times, name, color):
        t0 = 0
        x_plot = [0.0]
        y_plot = [0.0]
        t = 0.0
        v = 0.0
        for pc in pc_keys:
            end_time = end_times[pc]

            if 'branch_0' in pulses[pc]:
                seg = pulses[pc]['branch_0']
            else:
                seg = pulses[pc]

            try:
                seg_pulses = seg[name]
            except:
                t0 += end_time
                continue

            for pulse in seg_pulses.values():
                start = pulse['start'] + t0
                stop = pulse['stop'] + t0
                v_start = pulse['v_start']
                v_stop = pulse['v_stop']
                if start != t:
                    # there is a gap. Add point at end of last pulse
                    x_plot.append(t)
                    y_plot.append(0.0)
                    v = 0.0
                    if v_start != v:
                        # there is a step
                        x_plot.append(start)
                        y_plot.append(v)
                    x_plot.append(start)
                    y_plot.append(v_start)
                elif v_start != v:
                    # there is a step
                    x_plot.append(start)
                    y_plot.append(v_start)
                x_plot.append(stop)
                y_plot.append(v_stop)
                t = stop
                v = v_stop
            t0 += end_time

        if t != t0:
            # there is a gap. Add line till end.
            x_plot.append(t)
            y_plot.append(0.0)
            x_plot.append(t0)
            y_plot.append(0.0)

        legend_name = name[:-9]
        self.pulse_plot.plot(x_plot, y_plot, pen=color, name=legend_name)

    def _plot_mw_pulses(self, pulses, pc_keys, end_times, name, color, lo_frequency):
        t0 = 0
        x_plot = list()
        y_plot = list()
        for pc in pc_keys:
            end_time = end_times[pc]

            if 'branch_0' in pulses[pc]:
                seg = pulses[pc]['branch_0']
            else:
                seg = pulses[pc]

            try:
                seg_pulses = seg[name]
            except:
                t0 += end_time
                continue

            x = []
            y = []
            for seg_name, seg_dict in seg_pulses.items():
                x_ar = np.arange(seg_dict['start'], seg_dict['stop']) + t0
                if lo_frequency is not None:
                    f_rl = (seg_dict['frequency'] - lo_frequency)/1e9
                    y_ar = np.sin(2*np.pi*f_rl*x_ar+seg_dict['start_phase'])*seg_dict['amplitude']
                else:
                    f_rl = seg_dict['frequency']/1e9
                    xx_ar = x_ar-seg_dict['start']-t0
                    y_ar = np.sin(2*np.pi*f_rl*xx_ar+seg_dict['start_phase'])*seg_dict['amplitude']

                x = x + [seg_dict['start']+t0] + list(x_ar) + [seg_dict['stop']+t0]
                y = y + [0] + list(y_ar) + [0]
                x_plot = x
                y_plot = y
            t0 += end_time

        legend_name = name[:-7]
        self.pulse_plot.plot(x_plot, y_plot, pen=color, name=legend_name)
