from abc import abstractmethod
import logging

from PyQt5 import QtWidgets
from qt_dataviewer.model.plot_model import PlotModel


logger = logging.getLogger(__name__)


class BasePlot:
    def __init__(self, layout: QtWidgets.QLayout, plot_model: PlotModel):
        self._layout = layout
        self._plot_model = plot_model
        self.dims = plot_model.dims
        self.ndim = plot_model.ndim
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
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            layout.removeWidget(widget)
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