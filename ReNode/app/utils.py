from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

def loadStylesheet(filename: str):
    """
    Loads an qss stylesheet to the current QApplication instance

    :param filename: Filename of qss stylesheet
    :type filename: str
    """
    print('LOADING STYLE:', filename)
    file = QFile(filename)
    file.open(QFile.ReadOnly | QFile.Text)
    stylesheet = file.readAll()
    QApplication.instance().setStyleSheet(str(stylesheet, encoding='utf-8'))
    return str(stylesheet, encoding='utf-8')

def intTryParse(value):
    try:
        return int(value)
    except ValueError:
        return 0
    
def floatTryParse(value):
    try:
        return float(value)
    except ValueError:
        return 0.0
    
def boolTryParse(value):
    try:
        return bool(value)
    except ValueError:
        return False
    
def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n
    
def updateIconColor(icon : QIcon, color) -> QIcon:
    size = icon.availableSizes()[0]
    pixmap = icon.pixmap(icon.actualSize(size))  # Указываете желаемый размер

    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return QIcon(pixmap)

def updatePixmapColor(pixmap: QPixmap, color: QColor | str) -> QPixmap:
    if isinstance(color, str):
        color = QColor(color)
    image = pixmap.toImage()
    for x in range(image.width()):
        for y in range(image.height()):
            pixel_color = QColor.fromRgba(image.pixelColor(x, y).rgba())
            if not pixel_color.alpha():
                continue
            pixel_color.setRgb(color.red(), color.green(), color.blue(),pixel_color.alpha())
            image.setPixelColor(x, y, pixel_color)
    return QPixmap.fromImage(image)

def mergePixmaps(pixmapSource: QPixmap, pixmapAdd: QPixmap):
    pixmap = pixmapSource
    #pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.drawPixmap(0, 0, pixmapAdd)
    painter.end()
    return pixmap
