from __future__ import annotations

from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from flashforge_app.services.localization import LocalizationService
from flashforge_app.state import AppState, BedWorkspace
from flashforge_app.ui.widgets import CardWidget


class DashboardView(QWidget):
    """High level overview with quick access tiles and recent activities."""

    navigate_requested = Signal(str)

    def __init__(
        self,
        localization: LocalizationService,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.localization = localization
        self.app_state = app_state
        self.workspace: Optional[BedWorkspace] = None

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)

        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.header_label)

        self.cards_container = QWidget()
        self.cards_layout = QGridLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setHorizontalSpacing(16)
        self.cards_layout.setVerticalSpacing(16)
        self.cards_container.setLayout(self.cards_layout)
        layout.addWidget(self.cards_container)

        self.card_max_delta = CardWidget("-", "0.00")
        self.card_mean_height = CardWidget("-", "0.00")
        self.card_workflow_stage = CardWidget("-", "-")
        self.card_shaper_status = CardWidget("-", "-")

        self.cards_layout.addWidget(self.card_max_delta, 0, 0)
        self.cards_layout.addWidget(self.card_mean_height, 0, 1)
        self.cards_layout.addWidget(self.card_workflow_stage, 0, 2)
        self.cards_layout.addWidget(self.card_shaper_status, 0, 3)
        for col in range(4):
            self.cards_layout.setColumnStretch(col, 1)

        self.quick_actions_frame = QFrame()
        self.quick_actions_frame.setObjectName("Card")
        quick_layout = QVBoxLayout()
        quick_layout.setContentsMargins(24, 24, 24, 24)
        quick_layout.setSpacing(12)
        self.quick_actions_frame.setLayout(quick_layout)
        self.quick_title = QLabel()
        self.quick_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        quick_layout.addWidget(self.quick_title)
        self.quick_description = QLabel()
        self.quick_description.setObjectName("Subtitle")
        self.quick_description.setWordWrap(True)
        quick_layout.addWidget(self.quick_description)

        buttons_row = QFrame()
        buttons_layout = QVBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)
        buttons_row.setLayout(buttons_layout)
        quick_layout.addWidget(buttons_row)

        self.quick_bed_button = QPushButton()
        self.quick_bed_button.setCursor(Qt.PointingHandCursor)
        self.quick_bed_button.clicked.connect(lambda: self.navigate_requested.emit("bed"))
        buttons_layout.addWidget(self.quick_bed_button)

        self.quick_shaper_button = QPushButton()
        self.quick_shaper_button.setCursor(Qt.PointingHandCursor)
        self.quick_shaper_button.clicked.connect(lambda: self.navigate_requested.emit("shaper"))
        buttons_layout.addWidget(self.quick_shaper_button)

        self.quick_settings_button = QPushButton()
        self.quick_settings_button.setCursor(Qt.PointingHandCursor)
        self.quick_settings_button.clicked.connect(lambda: self.navigate_requested.emit("settings"))
        buttons_layout.addWidget(self.quick_settings_button)

        layout.addWidget(self.quick_actions_frame)

        self.activity_frame = QFrame()
        self.activity_frame.setObjectName("Card")
        activity_layout = QVBoxLayout()
        activity_layout.setContentsMargins(24, 24, 24, 24)
        activity_layout.setSpacing(12)
        self.activity_frame.setLayout(activity_layout)
        self.activity_title = QLabel()
        self.activity_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.activity_body = QLabel()
        self.activity_body.setObjectName("Subtitle")
        self.activity_body.setWordWrap(True)
        activity_layout.addWidget(self.activity_title)
        activity_layout.addWidget(self.activity_body)
        layout.addWidget(self.activity_frame)

        self.apply_translations()
        self._refresh_cards()

    # ------------------------------------------------------------------ data handling
    def update_workspace(self, workspace: BedWorkspace) -> None:
        self.workspace = workspace
        self._refresh_cards()

    def clear_workspace(self) -> None:
        self.workspace = None
        self._refresh_cards()

    def _refresh_cards(self) -> None:
        if self.workspace is None or self.workspace.bed.mesh_data is None:
            self.card_max_delta.set_value("0.00 mm")
            self.card_mean_height.set_value("0.00 mm")
            self.card_workflow_stage.set_value("-")
            self.card_workflow_stage.set_subtitle(self.localization.translate("neo_ui.dashboard.workflow_pending"))
            self.card_shaper_status.set_value("-")
            self.card_shaper_status.set_subtitle(self.localization.translate("neo_ui.dashboard.shaper_pending"))
            return

        matrix = self.workspace.mesh_matrix
        max_delta = float(np.max(matrix) - np.min(matrix))
        average = float(np.mean(matrix))

        self.card_max_delta.set_value(f"{max_delta:.3f} mm")
        self.card_mean_height.set_value(f"{average:+.3f} mm")

        workflow = self.workspace.workflow
        if workflow and workflow.best_stage:
            stage_name = self.localization.translate(workflow.best_stage.label)
            self.card_workflow_stage.set_value(stage_name)
            self.card_workflow_stage.set_subtitle(
                self.localization.translate("neo_ui.dashboard.workflow_best"))
        else:
            self.card_workflow_stage.set_value("-")
            self.card_workflow_stage.set_subtitle(self.localization.translate("neo_ui.dashboard.workflow_pending"))

        self.card_shaper_status.set_value(self.localization.translate("neo_ui.dashboard.shaper_placeholder"))
        self.card_shaper_status.set_subtitle(self.localization.translate("neo_ui.dashboard.shaper_pending"))

    # ------------------------------------------------------------------ translations
    def apply_translations(self) -> None:
        tr = self.localization.translate
        self.header_label.setText(tr("neo_ui.dashboard.header"))
        self.card_max_delta.set_title(tr("neo_ui.dashboard.cards.max_delta"))
        self.card_mean_height.set_title(tr("neo_ui.dashboard.cards.mean_height"))
        self.card_workflow_stage.set_title(tr("neo_ui.dashboard.cards.workflow"))
        self.card_shaper_status.set_title(tr("neo_ui.dashboard.cards.shaper"))

        self.activity_title.setText(tr("neo_ui.dashboard.activity.title"))
        self.activity_body.setText(tr("neo_ui.dashboard.activity.placeholder"))
        self._refresh_cards()

        self.quick_title.setText(tr("neo_ui.dashboard.quick.title"))
        self.quick_description.setText(tr("neo_ui.dashboard.quick.description"))
        self.quick_bed_button.setText(tr("neo_ui.dashboard.quick.to_bed"))
        self.quick_shaper_button.setText(tr("neo_ui.dashboard.quick.to_shaper"))
        self.quick_settings_button.setText(tr("neo_ui.dashboard.quick.to_settings"))
