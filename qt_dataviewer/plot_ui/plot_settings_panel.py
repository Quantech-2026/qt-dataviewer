import logging
from functools import partial

from PyQt5 import QtCore, QtGui, QtWidgets

from qt_dataviewer.utils.qt_utils import qt_log_exception
from qt_dataviewer.model.plot_model import AxisMode, AxisSettings, PlotModel
from .smart_format import SmartFormatter

logger = logging.getLogger(__name__)


class PlotSettings(QtWidgets.QWidget):
    def __init__(self, plot_model: PlotModel):
        super().__init__()
        self._plot_model = plot_model

        max_column = 8

        layout = QtWidgets.QGridLayout(self)
        layout.setColumnMinimumWidth(0, 120)
        layout.setVerticalSpacing(0)
        layout.setHorizontalSpacing(8)
        layout.setColumnStretch(0, 1)
        for icol in range(1, max_column-1):
            layout.setColumnMinimumWidth(icol, 20)
        layout.setColumnMinimumWidth(max_column-2, 30)

        self._rb_groups = {}
        self._cb_log = {}
        self._cb_fft = {}
        self._sliders = {}
        irow = 0
        btn_col = 1

        label_name = QtWidgets.QLabel(plot_model.var_name)
        label_name.setFont(get_font(11))
        label_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(label_name, irow, 0, 1, max_column)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1

        for i, text in enumerate(['x', 'y', 'avg', 'slice', 'log', 'fft', 'len'], btn_col):
            label_name = QtWidgets.QLabel(text)
            label_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(label_name, irow, i)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1
        for axis in range(plot_model.n_axis):
            settings = plot_model.get_axis_settings(axis)
            ax_name = settings.data.name
            layout.addWidget(QtWidgets.QLabel(ax_name), irow, 0)
            dim_label = QtWidgets.QLabel(f"{len(settings.data)}")
            dim_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            layout.addWidget(dim_label, irow, max_column-1)
            group = QtWidgets.QButtonGroup(layout)
            self._rb_groups[axis] = group
            for icol, mode in enumerate([AxisMode.XAxis, AxisMode.YAxis, AxisMode.Average, AxisMode.Slice], btn_col):
                rb = QtWidgets.QRadioButton()
                rb.setChecked(settings.mode == mode)
                rb.toggled.connect(partial(self._set_mode, index=axis, mode=mode))
                group.addButton(rb, mode)
                layout.addWidget(rb, irow, icol, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

            cb = QtWidgets.QCheckBox()
            cb.setChecked(settings.logarithmic)
            cb.toggled.connect(partial(self._set_log, index=axis))
            self._cb_log[axis] = cb
            layout.addWidget(cb, irow, max_column-3, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

            cb = QtWidgets.QCheckBox()
            cb.setChecked(settings.fft)
            cb.toggled.connect(partial(self._set_fft, index=axis))
            self._cb_fft[axis] = cb
            layout.addWidget(cb, irow, max_column-2, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

            irow += 1

            # Slider ROW
            layout.addWidget(self._height_filler(), irow, 0)

            slider = Slider(axis, settings, partial(self._set_slice, index=axis))
            self._sliders[axis] = slider
            slider.widget.setVisible(settings.mode == AxisMode.Slice)
            layout.addWidget(slider.widget, irow, 0, 1, max_column)
            # layout.setRowMinimumHeight(irow, 10)
            irow += 1


        # Histogram
        axis = 'histogram'
        hist_mode = plot_model.histogram_mode
        layout.addWidget(QtWidgets.QLabel('histogram'), irow, 0)
        group = QtWidgets.QButtonGroup(layout)
        self._rb_groups[axis] = group
        for icol, mode in enumerate([AxisMode.XAxis, AxisMode.YAxis], btn_col):
            rb = QtWidgets.QRadioButton()
            rb.setChecked(hist_mode == mode)
            rb.toggled.connect(partial(self._set_mode, index=axis, mode=mode))
            group.addButton(rb, mode)
            layout.addWidget(rb, irow, icol, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1
        # @@@ add hist bins, range

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line, irow, 0, 1, max_column)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1

        layout.addWidget(QtWidgets.QLabel('multiline plot'), irow, 0)
        cb = QtWidgets.QCheckBox()
        cb.setChecked(plot_model.multiline_plot)
        cb.toggled.connect(self._set_multiline_plot)
        self._cb_multiline = cb
        layout.addWidget(cb, irow, btn_col, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1

        layout.addWidget(QtWidgets.QLabel('measured log.'), irow, 0)
        cb = QtWidgets.QCheckBox()
        cb.setChecked(plot_model.logarithmic)
        cb.toggled.connect(self._set_logarithmic)
        self._cb_measured_log = cb
        layout.addWidget(cb, irow, btn_col, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1

        layout.addWidget(QtWidgets.QLabel('2D sidebar histogram'), irow, 0)
        cb = QtWidgets.QCheckBox()
        cb.setChecked(plot_model.show_sidebar)
        cb.toggled.connect(self._set_show_sidebar)
        self._cb_sidebar = cb
        layout.addWidget(cb, irow, btn_col, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
        irow += 1
        layout.addWidget(self._height_filler(), irow, 0)
        irow += 1

        self.update_gui()

        # @@@ value range

    def _height_filler(self):
        height_filler = QtWidgets.QFrame()
        height_filler.setMinimumHeight(10)
        return height_filler

    @qt_log_exception
    def _set_mode(self, checked, index, mode):
        logger.debug(f"set mode {index} {mode}")
        if checked:
            self._plot_model.set_axis_mode(index, mode)
            self.update_gui()
            try:
                slider = self._sliders[index]
                slider.widget.setVisible(mode == AxisMode.Slice)
            except KeyError:
                pass
        else:
            if index == 'histogram':
                hist_btns = self._rb_groups['histogram']
                if hist_btns.checkedButton() is None:
                    self._plot_model.set_axis_mode(index, None)
                    self.update_gui()

    @qt_log_exception
    def _set_log(self, checked, index):
        logger.debug(f"set log {index}")
        self._plot_model.set_axis_log(index, checked)

    @qt_log_exception
    def _set_fft(self, checked, index):
        logger.debug(f"set fft {index}")
        self._plot_model.set_axis_fft(index, checked)

    @qt_log_exception
    def _set_slice(self, slice_index, index):
        logger.debug(f"set log {index}")
        self._plot_model.set_axis_slice(index, slice_index)

    @qt_log_exception
    def _set_logarithmic(self, checked):
        self._plot_model.set_logarithmic(checked)

    @qt_log_exception
    def _set_multiline_plot(self, checked):
        self._plot_model.set_multiline_plot(checked)

    @qt_log_exception
    def _set_show_sidebar(self, checked):
        self._plot_model.set_show_sidebar(checked)

    def update_gui(self):
        logger.debug('update gui')
        plot_model = self._plot_model
        if not plot_model:
            return
        for axis in range(plot_model.n_axis):
            settings = plot_model.get_axis_settings(axis)
            mode = settings.mode
            self._rb_groups[axis].button(mode).setChecked(True)
            self._cb_log[axis].setEnabled(mode in [AxisMode.XAxis, AxisMode.YAxis])
            self._cb_fft[axis].setEnabled(mode in [AxisMode.XAxis, AxisMode.YAxis])
        # histogram
        hist_btns = self._rb_groups['histogram']
        hist_btns.setExclusive(False)
        hist_mode = plot_model.histogram_mode
        for mode in [AxisMode.XAxis, AxisMode.YAxis]:
            hist_btns.button(mode).setChecked(mode == hist_mode)

        self._cb_sidebar.setEnabled(plot_model.ndim == 2)
        self._cb_measured_log.setEnabled(plot_model.ndim == 1)


class Slider:
    def __init__(self, axis: int, settings: AxisSettings, changed_cb):
        self.axis = axis
        self.settings = settings
        self.changed_cb = changed_cb
        self.formatter = SmartFormatter(settings.data.attrs)

        slider = QtWidgets.QSlider()
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setTickInterval(1)
        slider.setMinimum(0)
        slider.setMaximum(len(settings.data)-1)
        slider.valueChanged.connect(self._slider_changed)
        slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 6px; /* the groove expands to the size of the slider by default. by giving it a height, it has a fixed size */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 0px 0;
                border-radius: 2px;
            }

            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 10px;
                margin: -6px 0; /* handle is placed by default on the contents rect of the groove. Expand outside the groove */
                border-radius: 3px;
            }
            QSlider:focus {
                border: 1px dotted #404040;
            }
            """)

        label = QtWidgets.QLabel()
        label.setMinimumWidth(40)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.qslider = slider
        self.label = label
        self.widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(self.widget)
        layout.setContentsMargins(20, 2, 0, 4)
        layout.addWidget(slider)
        layout.addWidget(label)

        self._set_label_text(settings.slice_index)
        slider.setValue(settings.slice_index)

    def _set_label_text(self, slice_index):
        settings = self.settings
        value = settings.data[slice_index] * self.formatter.scale
        value_str = self.formatter.with_units(value, settings.data)
        self.label.setText(value_str)

    @qt_log_exception
    def _slider_changed(self, slice_index):
        self._set_label_text(slice_index)
        self.changed_cb(slice_index)


def get_font(point_size):
    font = QtGui.QFont()
    font.setPointSize(point_size)
    return font
