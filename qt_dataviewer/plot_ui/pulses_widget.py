import logging
import traceback
from numbers import Number
from typing import Any

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
    def set_pulses(self, pulses: dict[str, Any] | None):
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

            old_format = self._is_old_format(pulses)
            if old_format:
                self._plot_old_format(pulses, pc_keys, gate_keys)
            else:
                self._plot_new_format(pulses, pc_keys, gate_keys)

            self.pulses_layout.addWidget(pulse_plot, 1)
        except Exception:
            logger.error("Couldn't plot pulses", exc_info=True)
            message = traceback.format_exc()
            error_message = QtWidgets.QLabel(message)
            error_message.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            self.pulses_layout.addWidget(error_message, 1)
        finally:
            tab_widget.setCursor(QtCore.Qt.ArrowCursor)

    def _plot_new_format(self, pulses, pc_keys, gate_keys):
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
            except Exception:
                end_time = max([x['stop'] for y in seg.values() for x in y.values()])
            end_times[pc] = end_time

        try:
            lo_freqs = pulses['LOs']
        except KeyError:
            pass

        n_colors = len(color_list)
        # TODO handle acquisition channels
        for (j, name) in enumerate(gate_keys):
            if name.endswith('_baseband'):
                sine_pulses_name = name[:-9]+"_pulses"
                self._plot_baseband(pulses, pc_keys, end_times, name, color=color_list[j % n_colors],
                                    sine_pulses=sine_pulses_name if sine_pulses_name in gate_keys else None)
            elif name.endswith('_pulses') and name[:-7]+"_baseband" not in gate_keys:
                try:
                    lo_frequency = lo_freqs[name[:-7]]
                except Exception:
                    lo_frequency = None
                self._plot_mw_pulses(pulses, pc_keys, end_times, name, color_list[j % n_colors], lo_frequency)

    def _plot_old_format(self, pulses, pc_keys, gate_keys):
        try:
            lo_freqs = pulses['LOs']
        except KeyError:
            pass
        end_times = {}
        for pc in pc_keys:
            seg = pulses[pc]
            try:
                end_time = seg['_total_time']
                while isinstance(end_time, list):
                    end_time = end_time[-1]
            except Exception:
                end_time = max([x['stop'] for y in seg.values() for x in y.values()])
            end_times[pc] = end_time
        n_colors = len(color_list)

        for (j, name) in enumerate(gate_keys):
            if name.endswith('_baseband'):
                self._plot_baseband_old(pulses, pc_keys, end_times, name, color=color_list[j % n_colors])
            elif name.endswith('_pulses'):
                try:
                    lo_frequency = lo_freqs[name[:-7]]
                except Exception:
                    lo_frequency = None
                self._plot_mw_pulses(pulses, pc_keys, end_times, name, color_list[j % n_colors], lo_frequency)

    def _is_old_format(self, segments):
        # search for first pulse in baseband
        for pc in segments.values():
            for name, pulses in pc.items():
                if name.endswith('_baseband'):
                    if 'p0' in pulses:
                        return 'index_start' in pulses['p0']
        return False

    def _plot_baseband_old(self, pulses, pc_keys, end_times, name, color):
        t0 = 0
        x_plot = list()
        y_plot = list()
        for pc in pc_keys:
            end_time = end_times[pc]

            try:
                seg_pulses = pulses[pc][name]
            except Exception:
                t0 += end_time
                continue

            timepoints = set([x[key] for x in seg_pulses.values() for key in ['start', 'stop']])
            timepoints.add(end_time)
            for tp in sorted(timepoints):
                point1 = 0
                point2 = 0
                for seg_name, seg_dict in seg_pulses.items():
                    if seg_dict['start'] < tp and seg_dict['stop'] > tp:  # active segement
                        offset = (tp/(seg_dict['stop'] - seg_dict['start'])
                                  * (seg_dict['v_stop'] - seg_dict['v_start']) + seg_dict['v_start'])
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

    def _plot_baseband(self, pulses, pc_keys, end_times, name, color, sine_pulses: str | None = None):
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

            seg_pulses = seg.get(name, {})

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
                    if v_start != 0.0:
                        # there is a step
                        x_plot.append(start)
                        y_plot.append(0.0)
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

        # Add sine pulses
        line = LineBuilder(x_plot, y_plot)
        t0 = 0
        for pc in pc_keys:
            end_time = end_times[pc]

            if 'branch_0' in pulses[pc]:
                seg = pulses[pc]['branch_0']
            else:
                seg = pulses[pc]

            seg_pulses = seg.get(sine_pulses, {})
            for pulse in seg_pulses.values():
                line.add_sine(t0=t0, **pulse)

            t0 += end_time
        line_x, line_y = line.get_line()

        legend_name = name[:-9]
        self.pulse_plot.plot(line_x, line_y, pen=color, name=legend_name)

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
            except Exception:
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
                x_plot += x
                y_plot += y
            t0 += end_time

        legend_name = name[:-7]
        self.pulse_plot.plot(x_plot, y_plot, pen=color, name=legend_name)


class LineBuilder:
    """
    Combines line defined by ramps with sine pulses.
    Sine pulses are sampled at 2 GSa/s, which is higher than the common AWG sample rate.
    All time values are aligned to the 0.5 ns rounding towards the lower value.

    The resulting plot gives a good visual presentation of the "input pulses".
    It can deviate significantly from the actual AWG output, due to the AWG filtering.
    """

    def __init__(self, x, y):
        self._pts_x = x
        self._pts_y = y
        self._i_pts = 0
        self._line_x = []
        self._line_y = []
        self._wave = None
        self._wave_start = None
        self._wave_stop = None
        self._resolution = 0.5  # ns

    def _round(self, value):
        if isinstance(value, Number):
            return int(2*value + 0.5)/2
        else:
            return np.floor(2*value + 0.5)/2

    def _time_points(self, t0, t1):
        return t0 + np.arange(int((t1-t0)*2))*self._resolution

    def add_sine(self, t0, start, stop, amplitude, frequency, start_phase, AM_envelope=None, PM_envelope=None):
        start = self._round(start + t0)
        stop = self._round(stop + t0)

        if self._wave is not None and start > self._wave_stop:
            self._render_ramps()

        t = self._time_points(0, stop-start)*1e-9
        wave = np.sin(2*np.pi*frequency*t+start_phase)*amplitude

        self._add_wave(start, wave)

    def _add_wave(self, start, wave):
        if self._wave is None:
            self._wave = wave
            self._wave_start = start
            self._wave_stop = start + len(wave)*self._resolution
        else:
            stop = start + len(wave)*self._resolution
            if stop > self._wave_stop:
                new_wave = np.zeros(int((stop - self._wave_start)*2))
                new_wave[:len(self._wave)] = self._wave
                self._wave = new_wave
                self._wave_stop = stop
            istart = int(2*(start-self._wave_start))
            istop = int(2*(stop-self._wave_start))
            self._wave[istart: istop] += wave

    def _render_ramps(self):
        if self._wave is None:
            return
        ipts = self._i_pts
        imax = len(self._pts_x)-1
        # "less than" because step down at start of wave should not be added.
        x = self._round(self._pts_x[ipts])
        while x < self._wave_start:
            self._line_x.append(self._round(self._pts_x[ipts]))
            self._line_y.append(self._pts_y[ipts])
            ipts += 1
            x = self._round(self._pts_x[ipts])

        if x == self._wave_start:
            # Add end point of line
            self._line_x.append(x)
            self._line_y.append(self._pts_y[ipts])
            # do not add start point of next line (this is covered by wave)
            if self._round(self._pts_x[ipts+1]) == self._wave_start:
                ipts += 1
                x = self._round(self._pts_x[ipts])

        if x == self._wave_start:
            t = self._wave_start
            y = self._pts_y[ipts]
        else:
            # x, y interpolate to _wave_start
            x1 = self._round(self._pts_x[ipts-1])
            x2 = self._round(self._pts_x[ipts])
            y1 = self._pts_y[ipts-1]
            y2 = self._pts_y[ipts]

            t = self._wave_start
            y = y1+(t-x1)*(y2-y1)/(x2-x1)
            self._line_x.append(t)
            self._line_y.append(y)

        while x < self._wave_stop:
            stop = x
            i = int(2*(t - self._wave_start))
            j = int(2*(stop - self._wave_start))
            self._wave[i:j] += np.linspace(y, self._pts_y[ipts], j-i, endpoint=False)
            t = stop
            y = self._pts_y[ipts]
            ipts += 1
            x = self._round(self._pts_x[ipts])

        # x, y interpolate to _wave_stop
        if x == self._wave_stop:
            stop = self._wave_stop
            y_stop = self._pts_y[ipts]
            # do not add end point of this line (this is covered by wave
            if ipts+1 <= imax and self._round(self._pts_x[ipts+1]) == self._wave_stop:
                ipts += 1
                x = self._round(self._pts_x[ipts])
        else:
            # x, y interpolate to _wave_stop
            x1 = self._round(self._pts_x[ipts-1])
            x2 = self._round(self._pts_x[ipts])
            y1 = self._pts_y[ipts-1]
            y2 = self._pts_y[ipts]

            stop = self._wave_stop
            y_stop = y1+(stop-x1)*(y2-y1)/(x2-x1)
            # replace previous point
            self._pts_x[ipts-1] = stop
            self._pts_y[ipts-1] = y_stop
            ipts -= 1

        i = int(2*(t - self._wave_start))
        j = int(2*(stop - self._wave_start))
        self._wave[i:j] += np.linspace(y, y_stop, j-i, endpoint=False)

        self._line_x += self._time_points(self._wave_start, self._wave_stop).tolist()
        self._line_y += self._wave.tolist()
        self._wave = None

        self._i_pts = ipts

    def get_line(self):
        self._render_ramps()
        ipts = self._i_pts
        self._line_x += self._pts_x[ipts:]
        self._line_y += self._pts_y[ipts:]
        return self._line_x, self._line_y
