import base64
import json
import winsound

from cryptography.fernet import Fernet

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QStackedWidget, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QPixmap

from ui.widgets.task_row import TaskRow
from application.task_service import TaskService
from service.logger import get_logger

_logger = get_logger(__name__)

WINDOW_WIDTH = 360
WINDOW_HEIGHT = 480

_SESSION_KEY = Fernet.generate_key()
_CIPHER = Fernet(_SESSION_KEY)


class NotificationWindow(QWidget):
    def __init__(self, username: str, hostname: str, task_service: TaskService):
        super().__init__()
        self.username = username
        self.hostname = hostname
        self._task_service = task_service
        self._store = task_service.store  # leitura de estado — escrita sempre via task_service
        self._rows: dict[str, TaskRow] = {}
        self._current_task_id = ""
        self._encrypted_creds: bytes | None = None
        self._setup_window()
        self._setup_ui()
        self._position_window()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

    def _position_window(self):
        screen = QApplication.primaryScreen().availableGeometry()  # pyright: ignore[reportOptionalMemberAccess]
        margin = 14
        x = screen.right() - WINDOW_WIDTH - margin
        y = screen.bottom() - WINDOW_HEIGHT - margin
        self.move(x, y)

    # ------------------------------------------------------------------ #
    #  Setup UI principal                                                  #
    # ------------------------------------------------------------------ #
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._card = QWidget()
        self._card.setObjectName("card")
        self._card.setStyleSheet("""
            QWidget#card {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        self._stack.addWidget(self._build_list_page())
        self._stack.addWidget(self._build_detail_page())

        card_layout.addWidget(self._stack)

        sep_footer = QFrame()
        sep_footer.setFrameShape(QFrame.Shape.HLine)
        sep_footer.setStyleSheet("background: #e5e7eb; border: none; max-height: 1px;")
        card_layout.addWidget(sep_footer)

        footer = QWidget()
        footer.setStyleSheet("background: transparent;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(16, 8, 16, 10)

        self._session_label = QLabel("0 sessões ativas")
        self._session_label.setStyleSheet("color: #9ca3af; font-size: 10px; background: transparent;")
        f_layout.addWidget(self._session_label)
        f_layout.addStretch()

        shutdown_btn = QPushButton("Encerrar tudo")
        shutdown_btn.setFixedHeight(26)
        shutdown_btn.setStyleSheet("""
            QPushButton {
                color: #ef4444;
                background: transparent;
                border: 1px solid #fca5a5;
                border-radius: 4px;
                font-size: 11px;
                padding: 0 10px;
            }
            QPushButton:hover { background: #fef2f2; }
        """)
        shutdown_btn.clicked.connect(self._shutdown_all)
        f_layout.addWidget(shutdown_btn)

        card_layout.addWidget(footer)
        root.addWidget(self._card)

    # ------------------------------------------------------------------ #
    #  Página 1 — Lista                                                    #
    # ------------------------------------------------------------------ #
    def _build_list_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(16, 12, 16, 10)
        h_layout.setSpacing(2)

        top_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #22c55e; font-size: 10px; background: transparent;")
        top_row.addWidget(dot)
        title = QLabel("Operação Assistida")
        title.setStyleSheet("color: #1a1a1a; font-weight: bold; font-size: 13px; background: transparent; padding-left: 4px;")
        top_row.addWidget(title)
        top_row.addStretch()

        minimize_btn = QPushButton("—")
        minimize_btn.setFixedSize(24, 24)
        minimize_btn.setStyleSheet("""
            QPushButton {
                color: #9ca3af; background: transparent;
                border: none; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { color: #374151; background: #f3f4f6; border-radius: 4px; }
        """)
        minimize_btn.clicked.connect(self.hide)
        top_row.addWidget(minimize_btn)

        h_layout.addLayout(top_row)

        info = QLabel(f"{self.hostname}  ·  {self.username}")
        info.setStyleSheet("color: #9ca3af; font-size: 10px; background: transparent;")
        h_layout.addWidget(info)
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #e5e7eb; border: none; max-height: 1px;")
        layout.addWidget(sep)

        tasks_title = QLabel("Tarefas")
        tasks_title.setStyleSheet(
            "color: #111827; font-size: 13px; font-weight: bold;"
            " background: transparent; padding: 12px 16px 4px 16px;"
        )
        layout.addWidget(tasks_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._tasks_container = QWidget()
        self._tasks_container.setStyleSheet("background: transparent;")
        self._tasks_layout = QVBoxLayout(self._tasks_container)
        self._tasks_layout.setContentsMargins(8, 6, 8, 6)
        self._tasks_layout.setSpacing(2)

        self._empty_label = QLabel("Nenhuma tarefa recebida.")
        self._empty_label.setStyleSheet("color: #d1d5db; font-size: 11px; background: transparent;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tasks_layout.addWidget(self._empty_label)
        self._tasks_layout.addStretch()

        scroll.setWidget(self._tasks_container)
        layout.addWidget(scroll)
        return page

    # ------------------------------------------------------------------ #
    #  Página 2 — Detalhe                                                  #
    # ------------------------------------------------------------------ #
    def _build_detail_page(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        back_bar = QWidget()
        back_bar.setStyleSheet("background: transparent;")
        b_layout = QHBoxLayout(back_bar)
        b_layout.setContentsMargins(12, 10, 16, 8)

        back_btn = QPushButton("‹  Voltar")
        back_btn.setFixedHeight(28)
        back_btn.setStyleSheet("""
            QPushButton {
                color: #2563eb; background: #eff6ff;
                border: 1px solid #bfdbfe; border-radius: 5px;
                font-size: 12px; font-weight: bold; padding: 0 12px;
            }
            QPushButton:hover { background: #dbeafe; color: #1d4ed8; }
        """)
        back_btn.clicked.connect(self._go_back)
        b_layout.addWidget(back_btn)
        b_layout.addStretch()
        layout.addWidget(back_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #e5e7eb; border: none; max-height: 1px;")
        layout.addWidget(sep)

        self._detail_title = QLabel("")
        self._detail_title.setStyleSheet(
            "color: #1a1a1a; font-size: 13px; font-weight: bold;"
            " background: transparent; padding: 10px 16px 6px 16px;"
        )
        self._detail_title.setWordWrap(True)
        layout.addWidget(self._detail_title)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background: #e5e7eb; border: none; max-height: 1px;")
        layout.addWidget(sep2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        b_layout2 = QVBoxLayout(body)
        b_layout2.setContentsMargins(16, 12, 16, 12)
        b_layout2.setSpacing(8)

        # Badge de sessão offline (encerrada)
        self._offline_badge = QWidget()
        self._offline_badge.setStyleSheet(
            "background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 6px;"
        )
        self._offline_badge.hide()
        offline_layout = QHBoxLayout(self._offline_badge)
        offline_layout.setContentsMargins(10, 6, 10, 6)
        offline_icon = QLabel("●")
        offline_icon.setStyleSheet("color: #9ca3af; font-size: 8px; background: transparent;")
        offline_layout.addWidget(offline_icon)
        offline_text = QLabel("Sessão encerrada")
        offline_text.setStyleSheet("color: #6b7280; font-size: 11px; background: transparent; padding-left: 4px;")
        offline_layout.addWidget(offline_text)
        offline_layout.addStretch()
        b_layout2.addWidget(self._offline_badge)

        # Badge de credenciais registradas
        self._creds_badge = QWidget()
        self._creds_badge.setStyleSheet(
            "background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;"
        )
        self._creds_badge.hide()
        badge_layout = QHBoxLayout(self._creds_badge)
        badge_layout.setContentsMargins(10, 6, 10, 6)
        badge_layout.setSpacing(6)
        badge_icon = QLabel("✓")
        badge_icon.setStyleSheet("color: #16a34a; font-size: 11px; font-weight: bold; background: transparent;")
        badge_layout.addWidget(badge_icon)
        self._badge_user_label = QLabel("")
        self._badge_user_label.setStyleSheet("color: #15803d; font-size: 11px; background: transparent;")
        badge_layout.addWidget(self._badge_user_label)
        badge_layout.addStretch()
        b_layout2.addWidget(self._creds_badge)

        # Caixa de status/conteúdo (dinâmica)
        self._processing_box = QWidget()
        self._processing_box.setStyleSheet(
            "background: #374151; border-radius: 8px;"
        )
        self._processing_box.hide()
        proc_layout = QVBoxLayout(self._processing_box)
        proc_layout.setContentsMargins(14, 12, 14, 12)
        self._proc_label = QLabel("Aguardando QR Code...")
        self._proc_label.setStyleSheet("color: #ffffff; font-size: 12px; background: transparent;")
        self._proc_label.setWordWrap(True)
        proc_layout.addWidget(self._proc_label)
        b_layout2.addWidget(self._processing_box)

        # Formulário de credenciais
        field_style = """
            QLineEdit {
                border: 1px solid #d1d5db; border-radius: 4px;
                padding: 0 8px; font-size: 12px; color: #1a1a1a; background: #f9fafb;
            }
            QLineEdit:focus { border-color: #2563eb; background: #fff; }
            QLineEdit:disabled { background: #f3f4f6; color: #9ca3af; }
        """
        ok_style = """
            QPushButton {
                background: #2563eb; color: white; border: none;
                border-radius: 4px; font-size: 12px; font-weight: bold; padding: 0;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:disabled { background: #93c5fd; }
        """

        self._creds_widget = QWidget()
        self._creds_widget.setStyleSheet("background: transparent;")
        creds_layout = QVBoxLayout(self._creds_widget)
        creds_layout.setContentsMargins(0, 0, 0, 0)
        creds_layout.setSpacing(6)

        user_label = QLabel("Usuário")
        user_label.setStyleSheet("font-size: 10px; color: #6b7280; background: transparent;")
        creds_layout.addWidget(user_label)
        self._input_user = QLineEdit()
        self._input_user.setPlaceholderText("usuário")
        self._input_user.setFixedHeight(30)
        self._input_user.setStyleSheet(field_style)
        creds_layout.addWidget(self._input_user)

        pass_label = QLabel("Senha")
        pass_label.setStyleSheet("font-size: 10px; color: #6b7280; background: transparent;")
        creds_layout.addWidget(pass_label)

        pass_row = QHBoxLayout()
        self._input_pass = QLineEdit()
        self._input_pass.setPlaceholderText("senha")
        self._input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._input_pass.setFixedHeight(30)
        self._input_pass.setStyleSheet(field_style)
        pass_row.addWidget(self._input_pass)

        self._ok_cred_btn = QPushButton("OK")
        self._ok_cred_btn.setFixedSize(48, 30)
        self._ok_cred_btn.setStyleSheet(ok_style)
        self._ok_cred_btn.clicked.connect(self._submit_credentials)
        pass_row.addWidget(self._ok_cred_btn)
        creds_layout.addLayout(pass_row)

        b_layout2.addWidget(self._creds_widget)

        # Separador antes do QR
        self._sep_qr = QFrame()
        self._sep_qr.setFrameShape(QFrame.Shape.HLine)
        self._sep_qr.setStyleSheet("background: #e5e7eb; border: none; max-height: 1px;")
        self._sep_qr.hide()
        b_layout2.addWidget(self._sep_qr)

        # Seção QR + código
        self._qr_widget = QWidget()
        self._qr_widget.setStyleSheet("background: transparent;")
        self._qr_widget.hide()
        qr_layout = QVBoxLayout(self._qr_widget)
        qr_layout.setContentsMargins(0, 0, 0, 0)
        qr_layout.setSpacing(8)

        qr_label = QLabel("QR Code")
        qr_label.setStyleSheet("font-size: 10px; color: #6b7280; background: transparent;")
        qr_layout.addWidget(qr_label)

        self._qr_box = QLabel()
        self._qr_box.setFixedSize(130, 130)
        self._qr_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_box.setStyleSheet("""
            QLabel {
                border: 1px dashed #d1d5db; border-radius: 6px;
                background: #f9fafb; color: #d1d5db; font-size: 10px;
            }
        """)
        self._qr_box.setText("aguardando\nQR Code")
        qr_layout.addWidget(self._qr_box, alignment=Qt.AlignmentFlag.AlignHCenter)

        code_label = QLabel("Código")
        code_label.setStyleSheet("font-size: 10px; color: #6b7280; background: transparent;")
        qr_layout.addWidget(code_label)

        code_row = QHBoxLayout()
        self._input_code = QLineEdit()
        self._input_code.setPlaceholderText("0000")
        self._input_code.setMaxLength(4)
        self._input_code.setFixedHeight(30)
        self._input_code.setStyleSheet(field_style)
        code_row.addWidget(self._input_code)

        self._ok_code_btn = QPushButton("OK")
        self._ok_code_btn.setFixedSize(48, 30)
        self._ok_code_btn.setStyleSheet(ok_style)
        self._ok_code_btn.clicked.connect(self._submit_code)
        code_row.addWidget(self._ok_code_btn)
        qr_layout.addLayout(code_row)

        b_layout2.addWidget(self._qr_widget)
        b_layout2.addStretch()

        scroll.setWidget(body)
        layout.addWidget(scroll)

        return page

    # ------------------------------------------------------------------ #
    #  Lógica de estados                                                   #
    # ------------------------------------------------------------------ #
    def _show_and_raise(self):
        self._position_window()
        self.show()
        self.raise_()

    def _go_back(self):
        task = self._store.get(self._current_task_id)
        if not (task and task.finished):
            self._encrypted_creds = None
        self._stack.setCurrentIndex(0)

    def _go_to_list(self):
        self._stack.setCurrentIndex(0)

    def _refresh_row_status(self, task_id: str, status: str):
        """Atualiza o badge de status no widget da linha — o estado em si já foi mutado pelo TaskService."""
        row = self._rows.get(task_id)
        if row:
            row.set_status(status)

    def _set_proc_text(self, text: str):
        """Atualiza o texto da caixa de status (UI) — persistência fica a cargo do TaskService."""
        self._proc_label.setText(text)

    def _open_detail(self, task_id: int):
        task = self._store.get_by_index(task_id)
        if not task:
            return
        _logger.info("operador abriu detalhe da tarefa: task_id=%s", task.task_id)
        self._current_task_id = task.task_id
        self._detail_title.setText(task.title)

        # Reset widgets
        self._input_code.clear()
        self._qr_box.setText("aguardando\nQR Code")
        self._qr_box.setPixmap(QPixmap())
        self._sep_qr.hide()
        self._qr_widget.hide()

        if task.finished:
            # Detalhe offline
            self._offline_badge.show()
            if task.session_user:
                self._badge_user_label.setText(f"Sessão: {task.session_user}")
                self._creds_badge.show()
            else:
                self._creds_badge.hide()

            summary = "\n".join(task.log) if task.log else "Sem eventos registrados."
            self._proc_label.setText(summary)
            self._processing_box.show()
            self._creds_widget.hide()
        else:
            self._offline_badge.hide()
            if task.session_user:
                self._badge_user_label.setText(f"Sessão: {task.session_user}")
                self._creds_badge.show()
                self._proc_label.setText(task.proc_text)
                self._processing_box.show()
                self._creds_widget.hide()

                # Restaura QR se já chegou enquanto o detalhe estava fechado
                if task.qr_image_b64:
                    self._render_qr(task.qr_image_b64)
            else:
                self._creds_badge.hide()
                self._processing_box.hide()
                self._creds_widget.show()
                self._input_user.setEnabled(True)
                self._input_pass.setEnabled(True)
                self._ok_cred_btn.setEnabled(True)
                self._input_user.clear()
                self._input_pass.clear()
                self._encrypted_creds = None

                # Pré-preenche com credencial salva para o sistema, se houver — o operador
                # ainda precisa clicar OK para confirmar/enviar (popup nunca é pulado).
                saved = self._task_service.saved_credentials(task.system)
                if saved:
                    self._input_user.setText(saved.get("user", ""))
                    self._input_pass.setText(saved.get("password", ""))

        self._stack.setCurrentIndex(1)

    def _submit_credentials(self):
        user = self._input_user.text().strip()
        password = self._input_pass.text()
        if not user or not password:
            return
        _logger.info("operador submeteu credenciais: task_id=%s user=%s", self._current_task_id, user)

        raw = json.dumps({"user": user, "password": password}).encode()
        self._encrypted_creds = _CIPHER.encrypt(raw)

        self._badge_user_label.setText(f"Sessão: {user}")
        self._creds_badge.show()
        self._creds_widget.hide()
        self._set_proc_text("Aguardando QR Code...")
        self._processing_box.show()

        self._task_service.submit_credentials(self._current_task_id, user, password)
        self._refresh_row_status(self._current_task_id, "Aguardando QR Code")

    def _submit_code(self):
        code = self._input_code.text().strip()
        if not code:
            return
        _logger.info("operador submeteu código de verificação: task_id=%s", self._current_task_id)

        self._ok_code_btn.setEnabled(False)
        self._set_proc_text("Em processamento...")

        if self._current_task_id:
            self._task_service.submit_code(self._current_task_id, code)
            self._refresh_row_status(self._current_task_id, "Em processamento")

        self._go_to_list()

    # ------------------------------------------------------------------ #
    #  Slots públicos                                                      #
    # ------------------------------------------------------------------ #
    def _add_task(self, title: str, message: str, task_id: str, system: str | None = None):
        self._empty_label.hide()
        task = self._task_service.register_task(title, message, task_id, system)
        row = TaskRow(task.id, title, message, self._open_detail)
        self._rows[task.task_id] = row
        self._tasks_layout.insertWidget(self._tasks_layout.count() - 1, row)

    def _dismiss_task(self, task_id: str):
        """Remove definitivamente um card encerrado da lista."""
        _logger.info("operador descartou card da tarefa: task_id=%s", task_id)
        row = self._rows.pop(task_id, None)
        if row:
            self._tasks_layout.removeWidget(row)
            row.hide()
            row.deleteLater()
        self._task_service.dismiss_task(task_id)
        if self._current_task_id == task_id:
            self._current_task_id = ""
            self._stack.setCurrentIndex(0)
        if self._store.is_empty():
            self._empty_label.show()

    def _shutdown_all(self):
        _logger.info("operador solicitou encerramento de tudo via popup")
        QApplication.quit()

    @pyqtSlot(int)
    def update_session_count(self, count: int):
        label = "1 sessão ativa" if count == 1 else f"{count} sessões ativas"
        self._session_label.setText(label)

    @pyqtSlot(str)
    def remove_task(self, task_id: str):
        """Conexão encerrada — mantém o card como 'encerrado' na lista."""
        task = self._task_service.mark_session_ended(task_id)
        if not task:
            return

        self._refresh_row_status(task_id, "Encerrado")
        row = self._rows.get(task_id)
        if row:
            row.set_finished(lambda tid=task_id: self._dismiss_task(tid))

        # Se o detalhe desta task estava aberto, volta à lista
        if self._current_task_id == task_id:
            self._encrypted_creds = None
            self._stack.setCurrentIndex(0)

    @pyqtSlot(str, str, str, str)
    def show_notification(self, title: str, message: str, task_id: str = "", system: str = ""):
        _logger.info("popup exibido para nova tarefa: task_id=%s title=%r", task_id, title)
        self._add_task(title, message, task_id, system or None)
        self._position_window()
        self.show()
        self.raise_()
        winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)

    @pyqtSlot(str)
    def on_execution_started(self, task_id: str):
        self._task_service.mark_execution_started(task_id)
        self._refresh_row_status(task_id, "Em execução")
        self._encrypted_creds = None
        if task_id == self._current_task_id:
            self._set_proc_text("Em execução")

    @pyqtSlot(str, str)
    def on_execution_error(self, task_id: str, message: str):
        self._task_service.mark_execution_error(task_id, message)
        self._refresh_row_status(task_id, "Erro inesperado")
        if task_id == self._current_task_id:
            self._set_proc_text(f"Erro inesperado:\n{message}")

    @pyqtSlot(str, str)
    def on_credentials_error(self, task_id: str, message: str):
        self._task_service.mark_credentials_error(task_id, message)
        self._refresh_row_status(task_id, "Aguardando login")
        if task_id != self._current_task_id:
            return
        self._encrypted_creds = None
        self._creds_badge.hide()
        self._processing_box.hide()
        self._input_user.clear()
        self._input_pass.clear()
        self._input_user.setEnabled(True)
        self._input_pass.setEnabled(True)
        self._ok_cred_btn.setEnabled(True)
        self._creds_widget.show()
        self._input_code.clear()
        self._sep_qr.hide()
        self._qr_widget.hide()
        self._qr_box.setText("aguardando\nQR Code")
        self._qr_box.setPixmap(QPixmap())

    @pyqtSlot(str, str)
    def on_login_error(self, task_id: str, message: str):
        self._task_service.mark_login_error(task_id)
        self._refresh_row_status(task_id, "Aguardando QR Code")
        if task_id != self._current_task_id:
            return
        self._input_code.clear()
        self._ok_code_btn.setEnabled(True)
        self._set_proc_text(
            "Erro de sessão — aguardando novo QR Code.\n"
            "A sessão ativa falhou por questões técnicas e foi reiniciada."
        )

    def _render_qr(self, image_b64: str):
        """Aplica o QR Code no widget — chama apenas quando o detalhe está visível."""
        try:
            img_bytes = base64.b64decode(image_b64)
            pixmap = QPixmap()
            pixmap.loadFromData(img_bytes)
            self._qr_box.setPixmap(
                pixmap.scaled(130, 130, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        except Exception:
            self._qr_box.setText("QR Code\ninválido")
        self._sep_qr.show()
        self._qr_widget.show()
        self._input_code.clear()
        self._ok_code_btn.setEnabled(True)

    @pyqtSlot(str, str)
    def show_qr_code(self, task_id: str, image_b64: str):
        self._task_service.receive_qr_code(task_id, image_b64)
        self._refresh_row_status(task_id, "Aguardando código")

        if task_id != self._current_task_id:
            return

        self._render_qr(image_b64)
        self._set_proc_text("Aguardando código...")
