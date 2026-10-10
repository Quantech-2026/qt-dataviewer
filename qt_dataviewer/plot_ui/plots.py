from abc import abstractmethod
import logging

from qtpy import QtWidgets
from qt_dataviewer.model.plot_model import PlotModel


logger = logging.getLogger(__name__)


class BasePlot:
    def __init__(self, layout: QtWidgets.QLayout, plot_model: PlotModel):
        self._layout = layout
        self._plot_model = plot_model

        # cached (!) attributes describing plot type
        # If attribute changes, then plot should be recreated.
        self.plot_axes = plot_model.plot_axes
        self.gridded = plot_model.gridded
        self.multiline_plot = plot_model.multiline_plot
        self.one_d_is_vertical = plot_model.one_d_is_vertical

        # TODO add title and action buttons
        try:
            self.create()
        except Exception:
            logger.error("Exception creating plot", exc_info=True)
            raise

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def update(self):
        pass

    def remove(self):
        layout = self._layout
        while layout.count():
            widget = layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)



## RESOURCES
## https://www.pythonguis.com/tutorials/qresource-system/

    # def save(self):
    #     img = QImage(mywidget.size())
    #     painter = QPainter(img)
    #     mywidget.render(painter)
    #     img.save("/some/file.jpg")


# ## https://pyqtgraph.readthedocs.io/en/latest/user_guide/exporting.html

# * With filename, no filename -> dialog, bytes -> QImage

# import pyqtgraph as pg
# import pyqtgraph.exporters

# # generate something to export
# plt = pg.plot([1,5,2,4,3])

# # create an exporter instance, as an argument give it
# # the item you wish to export
# exporter = pg.exporters.ImageExporter(plt.plotItem)

# # set export parameters if needed
# exporter.parameters()['width'] = 100   # (note this also affects height parameter)

# # save to file
# exporter.export('fileName.png')

## https://doc.qt.io/qt-6/qclipboard.html

# QClipboard().setImage(exporter.export(toBytes=True))