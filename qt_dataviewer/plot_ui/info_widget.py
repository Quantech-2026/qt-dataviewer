from collections.abc import Mapping, Sequence
from numbers import Number
from typing import List, Tuple, Union, Dict, Any

from PyQt5 import QtCore, QtWidgets

from qt_dataviewer.utils.qt_utils import qt_log_exception


class InfoWidget(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        # Horizontal: panel, line, grid with plots, spacer
        h_layout = QtWidgets.QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(2)

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(2, 2, 2, 2)
        left_layout.setSpacing(2)

        h_layout.addLayout(left_layout)

        details_widget = QtWidgets.QFrame()
        details_widget.setMinimumWidth(350)
        details_widget.setMaximumWidth(350)
        details_widget.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        details_layout = QtWidgets.QGridLayout(details_widget)
        self.details_layout = details_layout

        left_layout.addWidget(details_widget)

        left_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum))

        self._condensed_snapshot = True
        cb_condensed_snapshot = QtWidgets.QCheckBox('Condensed snapshot', self)
        cb_condensed_snapshot.setChecked(True)
        cb_condensed_snapshot.clicked.connect(self._set_condensed_snapshot)
        self.cb_condensed_snapshot = cb_condensed_snapshot
        left_layout.addWidget(cb_condensed_snapshot)

        left_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        tree = QtWidgets.QTreeWidget(self)
        tree.setMinimumSize(QtCore.QSize(340, 600))
        tree.setColumnCount(2)
        tree.setColumnWidth(0, 240)
        tree.setHeaderLabels(['Path', 'Value'])
        tree.itemExpanded.connect(self._expand_item)
        self.snapshot_tree = tree

        h_layout.addWidget(tree, 1)

        h_layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

    def set_info(self, details_list: List[Tuple[str, str]]):
        for i in range(self.details_layout.count()):
            widget = self.details_layout.itemAt(i).widget()
            widget.deleteLater()
        for irow, (name, value) in enumerate(details_list):
            self.details_layout.addWidget(QtWidgets.QLabel(name), irow, 0)
            self.details_layout.addWidget(QtWidgets.QLabel(value), irow, 1)

    def set_snapshot(self, snapshot: Union[None, Dict[str, Any]]):
        self.snapshot = snapshot
        tree = self.snapshot_tree
        tree.clear()

        if snapshot:
            if self._condensed_snapshot:
                snapshot = reduce_snaphot(snapshot)
            self._add_items(None, snapshot)

    @qt_log_exception
    def _expand_item(self, item: QtWidgets.QTreeWidgetItem):
        data, children_expanded = item.data(0, QtCore.Qt.UserRole)
        if not children_expanded:
            self._add_items(item, data, expand_children=True)
            item.setData(0, QtCore.Qt.UserRole, (data, True))

    def _add_items(self, parent, settings, depth=1, expand_children=False):
        for index, (key, value) in enumerate(settings.items()):
            if expand_children:
                item = parent.child(index)
            else:
                item = QtWidgets.QTreeWidgetItem()
                item.setText(0, key)
                item.setData(0, QtCore.Qt.UserRole, (value, False))
                if parent:
                    parent.addChild(item)
                else:
                    self.snapshot_tree.addTopLevelItem(item)
            if value is None:
                item.setText(1, 'None')
            elif isinstance(value, Mapping):
                if (self._condensed_snapshot
                        and "value" in value.keys()
                        and "label" in value.keys()
                        and not (set(value.keys()) - set(["value", "label", "unit"]))):
                    unit = value.get("unit")
                    if unit:
                        item.setText(1, f"{value['value']}  ({unit})")
                    else:
                        item.setText(1, str(value["value"]))
                    item.setData(0, QtCore.Qt.UserRole, (value, True))
                elif depth > 0:
                    self._add_items(item, value, depth-1)
            elif not isinstance(value, str) and isinstance(value, Sequence):
                item.setData(0, QtCore.Qt.UserRole, (value, True))
                if expand_children:
                    for e in value:
                        li = QtWidgets.QTreeWidgetItem()
                        li.setText(0, '-')
                        li.setText(1, str(e))
                        item.addChild(li)
            else:
                item.setText(1, str(value))
                # if hasattr(value, 'dtype') and value.dtype <= float:
                #     if value.ndim == 0:
                #         value = value.item()
                #     else:
                #         value = str(value)
                # item.setData(1, QtCore.Qt.EditRole, value)
                # flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                # item.setFlags(flags)

    @qt_log_exception
    def _set_condensed_snapshot(self, checked):
        self._condensed_snapshot = checked
        snapshot = self.snapshot
        if snapshot:
            self.snapshot_tree.clear()
            if self._condensed_snapshot:
                snapshot = reduce_snaphot(snapshot)
            self._add_items(None, snapshot)


def reduce_snaphot(data):
    if isinstance(data, dict):
        res = {}
        try:
            clss = data['__class__']
        except KeyError:
            pass
        else:
            if clss not in [
                    "qcodes.data.data_set.DataSet",
                    "qcodes.data.data_array.DataArray"]:
                for name in ['submodules', 'parameters', 'value', 'unit', 'label',
                              'names', 'units', 'labels', 'setpoints',
                              'setpoint_names', 'setpoint_units', 'setpoint_labels',
                              'metadata']:
                    try:
                        value = data[name]
                    except KeyError:
                        pass
                    else:
                        if isinstance(value, Number):
                            res[name] = value
                        elif value:
                            value = reduce_snaphot(value)
                            if value:
                                res[name] = value
                        elif name == 'value':
                            res[name] = value
                return res
        for key, value in data.items():
            res[key] = reduce_snaphot(value)
        return res
    return data

