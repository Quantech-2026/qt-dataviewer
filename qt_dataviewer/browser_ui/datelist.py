
import logging
from datetime import date

from qtpy import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class DateListView(QtWidgets.QListWidget):
    dates_selected = QtCore.Signal(list) # List[date]

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QListWidget::item {
            height: 22px;
            }
            """
            )

        self.setSelectionMode(QtWidgets.QListView.ExtendedSelection)
        self.itemSelectionChanged.connect(self.date_selection_changed)

    @QtCore.Slot(list)
    def update_date_list(self, dates: list[date]) -> None:
        dates = [f"{date:%Y-%m-%d}" for date in dates]
        if len(dates) == 0:
            self.clear()
            self.addItem("<no data>")
            return

        if self.count() > 0 and self.item(0).text() == "<no data>":
            self.takeItem(0)

        # Add new dates to the list
        for d in dates:
            if not self.findItems(d, QtCore.Qt.MatchExactly):
                self.insertItem(0, d)

        # Remove dates that are no longer in the list
        i = self.count() - 1
        while i >= 0:
            elem = self.item(i)
            if elem is not None and elem.text() not in dates:
                self.takeItem(i)
                del elem
            i -= 1

        # Sort the list in descending order
        self.sortItems(QtCore.Qt.DescendingOrder)

        if len(self.selectedIndexes()) == 0: # TODO check if this is the desired behavior when filtering.
            self.item(0).setSelected(True)

    @QtCore.Slot()
    def date_selection_changed(self) -> None:
        dates = []
        for item in self.selectedItems():
            try:
                dates.append(date.fromisoformat(item.text()))
            except ValueError:
                pass
        self.dates_selected.emit(dates)
