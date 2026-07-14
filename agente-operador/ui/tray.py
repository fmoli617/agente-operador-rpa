from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QSize

from service.logger import get_logger

_logger = get_logger(__name__)


def _build_icon() -> QIcon:
    """Gera um icone simples em runtime — sem depender de arquivo externo."""
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Circulo de fundo
    painter.setBrush(QBrush(QColor("#50fa7b")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # Letra "O" centralizada
    painter.setPen(QColor("#1e1e2e"))
    font = painter.font()
    font.setPixelSize(36)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "O")

    painter.end()
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window, parent=None):
        super().__init__(_build_icon(), parent)
        self.window = window
        self.setToolTip("Operação Assistida")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()

        show_action = menu.addAction("Mostrar notificação")
        show_action.triggered.connect(self._show_window)

        menu.addSeparator()

        quit_action = menu.addAction("Encerrar")
        quit_action.triggered.connect(self._quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        _logger.info("janela reaberta via ícone da bandeja")
        self.window._position_window()
        self.window.show()
        self.window.raise_()

    def _quit(self):
        _logger.info("encerramento solicitado via menu da bandeja")
        QApplication.quit()
