from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import paramiko
from scp import SCPClient

from flashforge_app.services.localization import LocalizationService
from flashforge_app.state import AppState


class SSHTab(QWidget):
    """Dedicated SSH tab for testing connection and downloading files."""

    config_downloaded = Signal(Path)
    shaper_files_downloaded = Signal(list)

    def __init__(
        self,
        localization: LocalizationService,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.localization = localization
        self.app_state = app_state
        self._current_settings = self.app_state.current_settings.ssh

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)

        self.header_label = QLabel(self.localization.translate("settings_tab.ssh"))
        self.header_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.header_label)

        credentials_frame = QFrame()
        credentials_frame.setObjectName("Card")
        form_layout = QFormLayout()
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(12)
        credentials_frame.setLayout(form_layout)

        self.host_input = QLineEdit(self._current_settings.host)
        self.user_input = QLineEdit(self._current_settings.username)
        self.password_input = QLineEdit(self._current_settings.password)
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow(self.localization.translate("settings_tab.host"), self.host_input)
        form_layout.addRow(self.localization.translate("settings_tab.username"), self.user_input)
        form_layout.addRow(self.localization.translate("settings_tab.password"), self.password_input)

        layout.addWidget(credentials_frame)

        buttons_frame = QFrame()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        buttons_frame.setLayout(btn_layout)

        self.test_button = QPushButton(self.localization.translate("settings_tab.test_connection"))
        self.test_button.clicked.connect(self._on_test_connection)
        btn_layout.addWidget(self.test_button)

        self.fetch_config_button = QPushButton(self.localization.translate("settings_tab.get_printer_cfg"))
        self.fetch_config_button.clicked.connect(self._on_fetch_config)
        btn_layout.addWidget(self.fetch_config_button)

        self.fetch_shapers_button = QPushButton(self.localization.translate("settings_tab.get_shapers"))
        self.fetch_shapers_button.clicked.connect(self._on_fetch_shapers)
        btn_layout.addWidget(self.fetch_shapers_button)

        btn_layout.addStretch(1)
        layout.addWidget(buttons_frame)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("Subtitle")
        self.log_output.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;")
        layout.addWidget(self.log_output)

    def apply_translations(self) -> None:
        tr = self.localization.translate
        self.header_label.setText(tr("settings_tab.ssh"))
        self.test_button.setText(tr("settings_tab.test_connection"))
        self.fetch_config_button.setText(tr("settings_tab.get_printer_cfg"))
        self.fetch_shapers_button.setText(tr("settings_tab.get_shapers"))

    # ------------------------------------------------------------------ helpers
    def _append_log(self, message: str) -> None:
        if message:
            self.log_output.append(message)
        self.log_output.moveCursor(QTextCursor.End)

    def _create_client(self) -> paramiko.SSHClient:
        host = self.host_input.text().strip()
        username = self.user_input.text().strip()
        password = self.password_input.text()

        if not host or not username or not password:
            raise ValueError(self.localization.translate("settings_tab.fill_ssh"))

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=15)
        self.save_credentials()
        return client

    # ------------------------------------------------------------------ slots
    def _on_test_connection(self) -> None:
        tr = self.localization.translate
        try:
            client = self._create_client()
            stdin, stdout, stderr = client.exec_command('echo "test"')
            exit_status = stdout.channel.recv_exit_status()
            client.close()
            if exit_status == 0:
                self._append_log(tr("settings_tab.connection_success"))
            else:
                self._append_log(tr("settings_tab.connection_error").format(stderr.read().decode().strip()))
        except Exception as exc:  # noqa: BLE001
            self._append_log(tr("settings_tab.connection_error").format(str(exc)))

    def _on_fetch_config(self) -> None:
        tr = self.localization.translate
        try:
            client = self._create_client()
            with SCPClient(client.get_transport()) as scp:
                remote_paths = ["/opt/config/printer.cfg", "/root/printer_data/config/printer.cfg"]
                local_path = Path("config/printer.cfg")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                last_error = None
                for remote_path in remote_paths:
                    try:
                        scp.get(remote_path, str(local_path))
                        self._append_log(tr("settings_tab.fill_printer_cfg").format(local_path))
                        self.app_state.load_printer_config(local_path)
                        self.config_downloaded.emit(local_path)
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                else:
                    raise last_error or FileNotFoundError("printer.cfg not found on remote host")
            client.close()
        except Exception as exc:  # noqa: BLE001
            self._append_log(tr("settings_tab.connection_error").format(str(exc)))

    def _on_fetch_shapers(self) -> None:
        tr = self.localization.translate
        try:
            client = self._create_client()
            stdin, stdout, stderr = client.exec_command("ls /tmp/calibration_data_*.csv")
            files = [line.strip() for line in stdout.read().decode().splitlines() if line.strip()]
            err = stderr.read().decode().strip()
            if err:
                self._append_log(err)
            if not files:
                self._append_log(tr("settings_tab.no_shapers_found"))
                client.close()
                return

            local_dir = Path("config/shapers")
            local_dir.mkdir(parents=True, exist_ok=True)
            downloaded: List[Path] = []
            with SCPClient(client.get_transport()) as scp:
                for remote_file in files:
                    local_file = local_dir / Path(remote_file).name
                    scp.get(remote_file, str(local_file))
                    downloaded.append(local_file)
            client.close()

            for entry in downloaded:
                self._append_log(tr("settings_tab.fill_shapers").format(entry))
            self.shaper_files_downloaded.emit(downloaded)
        except Exception as exc:  # noqa: BLE001
            self._append_log(tr("settings_tab.connection_error").format(str(exc)))

    # ------------------------------------------------------------------ persistence
    def save_credentials(self) -> None:
        ssh_settings = self.app_state.current_settings.ssh
        ssh_settings.host = self.host_input.text().strip()
        ssh_settings.username = self.user_input.text().strip()
        ssh_settings.password = self.password_input.text()
        self.app_state.save_settings()
