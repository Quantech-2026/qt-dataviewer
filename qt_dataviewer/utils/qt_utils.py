import logging
import os
import threading

from PyQt5 import QtCore, QtWidgets

try:
    import IPython.lib.guisupport as gs
    from IPython import get_ipython
except Exception:
    get_ipython = lambda: None


logger = logging.getLogger(__name__)

is_wrapped = threading.local()
is_wrapped.val = False


def qt_log_exception(func):
    ''' Decorator to log exceptions.
    Exceptions are logged and raised again.
    Decorator is designed to be used around functions being called as
    QT event handlers, because QT doesn't report the exceptions.
    Note:
        The decorated method/function cannot be used with
        functools.partial.
    '''

    def wrapped(*args, **kwargs):
        if is_wrapped.val:
            return func(*args, **kwargs)
        else:
            is_wrapped.val = True
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.error('Exception in GUI', exc_info=True)
                raise
            finally:
                is_wrapped.val = False

    return wrapped


_qt_app = None


def qt_init():
    '''Starts the QT application if not yet started.
    Most of the cases the QT backend is already started
    by IPython, but sometimes it is not.
    '''
    # application reference must be held in global scope
    global _qt_app

    if _qt_app is not None:
        return

#    print(QtCore.QCoreApplication.testAttribute(QtCore.Qt.AA_EnableHighDpiScaling))
#    print(QtCore.QCoreApplication.testAttribute(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough))

    # Set attributes for proper scaling when display scaling is not equal to 100%
    # This should be done before QApplication is started.
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    ipython = get_ipython()

    if ipython:
        if not gs.is_event_loop_running_qt4():
            if any('SPYDER' in name for name in os.environ):
                raise Exception('Configure QT5 in Spyder -> Preferences -> IPython Console -> Graphics -> Backend')
            else:
                print('Warning Qt5 not configured for IPython console. Activating it now.')
                ipython.run_line_magic('gui', 'qt5')

        _qt_app = QtCore.QCoreApplication.instance()
        if _qt_app is None:
            logger.debug('Create Qt application')
            _qt_app = QtWidgets.QApplication([])
        else:
            logger.debug('Qt application already created')
