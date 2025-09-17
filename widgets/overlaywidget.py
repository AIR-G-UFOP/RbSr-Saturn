from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class OverlayWidget(QWidget):
    def __init__(self, parent=None):
        super(OverlayWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.new_parent()

    def new_parent(self):
        if not self.parent():
            return
        self.parent().installEventFilter(self)
        self.raise_()

    def eventFilter(self, obj, event):
        if obj == self.parent():
            if event.type() == QEvent.Resize:
                self.resize(event.size())
            elif event.type() == QEvent.ChildAdded:
                self.raise_()
        return super().eventFilter(obj, event)

    def event(self, event):
        if event.type() == QEvent.ParentAboutToChange:
            if self.parent():
                self.parent().removeEventFilter(self)
        elif event.type() == QEvent.ParentChange:
            self.new_parent()
        return super().event(event)


class LoadingOverlay(OverlayWidget):

    def __init__(self, parent=None):
        super(LoadingOverlay, self).__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(27, 31, 37, 200))
