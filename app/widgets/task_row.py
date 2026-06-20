"""Widget de uma linha da lista de tarefas — não conhece TaskStore nem o resto do app."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TaskRow(QWidget):
    def __init__(self, task_id: int, title: str, message: str, on_click):
        super().__init__()
        self.task_id = task_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #22c55e; font-size: 8px; background: transparent;")
        self._dot.setFixedWidth(10)
        self._layout.addWidget(self._dot)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #1a1a1a; background: transparent;")
        self._layout.addWidget(title_label)
        self._layout.addStretch()

        self._status_label = QLabel("Aguardando login")
        self._status_label.setStyleSheet(
            "font-size: 10px; font-weight: bold; color: #d97706;"
            " background: #fef3c7; border-radius: 4px; padding: 1px 6px;"
        )
        self._layout.addWidget(self._status_label)

        self._arrow = QLabel("›")
        self._arrow.setStyleSheet("font-size: 16px; color: #d1d5db; background: transparent; padding-left: 4px;")
        self._layout.addWidget(self._arrow)

        self.setStyleSheet("""
            TaskRow { background: transparent; border-radius: 6px; }
            TaskRow:hover { background: #f9fafb; }
        """)
        self._on_click = on_click

    def set_status(self, text: str):
        self._status_label.setText(text)
        tl = text.lower()
        if "erro" in tl or "inesperado" in tl:
            style = "font-size: 10px; font-weight: bold; color: #dc2626; background: #fee2e2; border-radius: 4px; padding: 1px 6px;"
        elif "execução" in tl or "execucao" in tl:
            style = "font-size: 10px; font-weight: bold; color: #16a34a; background: #dcfce7; border-radius: 4px; padding: 1px 6px;"
        elif "processamento" in tl:
            style = "font-size: 10px; font-weight: bold; color: #2563eb; background: #dbeafe; border-radius: 4px; padding: 1px 6px;"
        elif "encerrado" in tl or "concluído" in tl:
            style = "font-size: 10px; font-weight: bold; color: #6b7280; background: #f3f4f6; border-radius: 4px; padding: 1px 6px;"
        else:
            style = "font-size: 10px; font-weight: bold; color: #d97706; background: #fef3c7; border-radius: 4px; padding: 1px 6px;"
        self._status_label.setStyleSheet(style)

    def set_finished(self, dismiss_cb):
        """Marca a tarefa como encerrada — ponto cinza, X no lugar da seta."""
        self._finished = True
        self._dot.setStyleSheet("color: #9ca3af; font-size: 8px; background: transparent;")
        self._arrow.hide()

        x_btn = QPushButton("×")
        x_btn.setFixedSize(20, 20)
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.setStyleSheet("""
            QPushButton {
                color: #9ca3af; background: transparent;
                border: none; font-size: 15px; font-weight: bold;
            }
            QPushButton:hover { color: #ef4444; background: #fee2e2; border-radius: 4px; }
        """)
        x_btn.clicked.connect(dismiss_cb)
        self._layout.addWidget(x_btn)

    def mousePressEvent(self, event):
        if not getattr(self, '_finished', False):
            self._on_click(self.task_id)
