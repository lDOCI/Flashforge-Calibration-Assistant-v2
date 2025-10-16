from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWidgets import QButtonGroup

from flashforge_app.services.localization import LocalizationService
from flashforge_app.services.settings import ApplicationSettings, SettingsService, ThermalPreset
from flashforge_app.state import AppState


class SettingsView(QWidget):
    """Editable settings form grouped by categories."""

    def __init__(
        self,
        settings_service: SettingsService,
        localization: LocalizationService,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.localization = localization
        self.app_state = app_state
        self.settings: ApplicationSettings = self.settings_service.settings

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)

        self.header_label = QLabel(self.localization.translate("neo_ui.settings.header"))
        self.header_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.header_label)

        self.hardware_fields = {}
        self.screw_mode_buttons: dict[str, QRadioButton] = {}
        self.screw_mode_group = QButtonGroup(self)
        self.screw_mode_label: QLabel | None = None
        self.screw_mode_buttons: dict[str, QRadioButton] = {}
        self.threshold_fields = {}
        self.environment_fields = {}
        self.visualization_fields = {}
        self.visualization_checks = {}
        self.workflow_checks = {}
        self.thermal_fields: dict[str, QLineEdit] = {}
        self.thermal_combo: QComboBox | None = None
        self.thermal_add_button: QPushButton | None = None
        self.thermal_remove_button: QPushButton | None = None
        self._current_preset_index: int = 0

        layout.addWidget(self._build_hardware_group())
        layout.addWidget(self._build_threshold_group())
        layout.addWidget(self._build_environment_group())
        layout.addWidget(self._build_thermal_group())
        layout.addWidget(self._build_visualization_group())
        layout.addWidget(self._build_workflow_group())

        buttons_frame = QFrame()
        buttons_layout = QGridLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setHorizontalSpacing(12)
        buttons_frame.setLayout(buttons_layout)

        self.save_button = QPushButton(self.localization.translate("settings_tab.save"))
        self.save_button.clicked.connect(self._handle_save)
        self.reset_button = QPushButton(self.localization.translate("settings_tab.reset"))
        self.reset_button.clicked.connect(self._handle_reset)

        buttons_layout.addWidget(self.save_button, 0, 0, alignment=Qt.AlignLeft)
        buttons_layout.addWidget(self.reset_button, 0, 1, alignment=Qt.AlignRight)
        layout.addWidget(buttons_frame)

        self._refresh_fields()

    def apply_translations(self) -> None:
        self.header_label.setText(self.localization.translate("neo_ui.settings.header"))
        self.save_button.setText(self.localization.translate("settings_tab.save"))
        self.reset_button.setText(self.localization.translate("settings_tab.reset"))
        if self.screw_mode_label:
            self.screw_mode_label.setText(self.localization.translate("settings_tab.screw_mode_label"))
        if self.screw_mode_buttons:
            self.screw_mode_buttons['hold_nut'].setText(self.localization.translate("settings_tab.screw_mode_hold_nut"))
            self.screw_mode_buttons['hold_screw'].setText(self.localization.translate("settings_tab.screw_mode_hold_screw"))

    # ------------------------------------------------------------------ group builders
    def _build_card(self, title: str) -> tuple[QFrame, QFormLayout]:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QFormLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        frame.setLayout(layout)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addRow(title_label)
        return frame, layout

    def _add_line_edit(self, layout: QFormLayout, label: str, value: float | int | str, storage: dict, key: str) -> QLineEdit:
        edit = QLineEdit(str(value))
        layout.addRow(label, edit)
        storage[key] = edit
        return edit

    def _build_hardware_group(self) -> QFrame:
        title = self.localization.translate("settings_tab.hardware")
        frame, form = self._build_card(title)
        hw = self.settings.hardware
        self._add_line_edit(form, self.localization.translate("settings_tab.screw_pitch"), hw.screw_pitch, self.hardware_fields, "screw_pitch")
        self._add_line_edit(form, self.localization.translate("settings_tab.min_adjustment"), hw.min_adjustment, self.hardware_fields, "min_adjustment")
        self._add_line_edit(form, self.localization.translate("settings_tab.max_adjustment"), hw.max_adjustment, self.hardware_fields, "max_adjustment")
        self._add_line_edit(form, self.localization.translate("settings_tab.tape_thickness"), hw.tape_thickness, self.hardware_fields, "tape_thickness")
        self._add_line_edit(form, self.localization.translate("settings_tab.belt_tooth_mm"), hw.belt_tooth_mm, self.hardware_fields, "belt_tooth_mm")

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(12)

        hold_nut_button = QRadioButton(self.localization.translate("settings_tab.screw_mode_hold_nut"))
        hold_screw_button = QRadioButton(self.localization.translate("settings_tab.screw_mode_hold_screw"))
        self.screw_mode_group.addButton(hold_nut_button)
        self.screw_mode_group.addButton(hold_screw_button)
        self.screw_mode_buttons['hold_nut'] = hold_nut_button
        self.screw_mode_buttons['hold_screw'] = hold_screw_button

        mode_layout.addWidget(hold_nut_button)
        mode_layout.addWidget(hold_screw_button)
        mode_layout.addStretch(1)
        self.screw_mode_label = QLabel(self.localization.translate("settings_tab.screw_mode_label"))
        form.addRow(self.screw_mode_label, mode_widget)

        return frame

    def _build_threshold_group(self) -> QFrame:
        title = self.localization.translate("settings_tab.thresholds")
        frame, form = self._build_card(title)
        th = self.settings.thresholds
        self._add_line_edit(form, self.localization.translate("settings_tab.belt_threshold"), th.belt_threshold, self.threshold_fields, "belt_threshold")
        self._add_line_edit(form, self.localization.translate("settings_tab.screw_threshold"), th.screw_threshold, self.threshold_fields, "screw_threshold")
        self._add_line_edit(form, self.localization.translate("settings_tab.tape_threshold"), th.tape_threshold, self.threshold_fields, "tape_threshold")
        return frame

    def _build_environment_group(self) -> QFrame:
        title = self.localization.translate("settings_tab.environment")
        frame, form = self._build_card(title)
        env = self.settings.environment
        self._add_line_edit(form, self.localization.translate("settings_tab.measurement_temp"), env.measurement_temp, self.environment_fields, "measurement_temp")
        self._add_line_edit(form, self.localization.translate("settings_tab.target_temp"), env.target_temp, self.environment_fields, "target_temp")
        self._add_line_edit(form, self.localization.translate("settings_tab.thermal_coeff"), env.thermal_expansion_coeff, self.environment_fields, "thermal_expansion_coeff")
        return frame

    def _build_thermal_group(self) -> QFrame:
        title = self.localization.translate("settings_tab.thermal_group")
        frame, form = self._build_card(title)

        combo = QComboBox()
        self.thermal_combo = combo
        combo.currentIndexChanged.connect(self._handle_preset_change)
        form.addRow(self.localization.translate("settings_tab.thermal_preset"), combo)

        button_row = QWidget()
        row_layout = QHBoxLayout(button_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        add_button = QPushButton(self.localization.translate("settings_tab.thermal_add"))
        remove_button = QPushButton(self.localization.translate("settings_tab.thermal_remove"))
        add_button.clicked.connect(self._handle_add_preset)
        remove_button.clicked.connect(self._handle_remove_preset)
        row_layout.addWidget(add_button)
        row_layout.addWidget(remove_button)
        form.addRow("", button_row)
        self.thermal_add_button = add_button
        self.thermal_remove_button = remove_button

        self.thermal_fields['name'] = self._add_line_edit(form, self.localization.translate("settings_tab.thermal_name"), "", self.thermal_fields, "name")
        self.thermal_fields['measurement_temp'] = self._add_line_edit(form, self.localization.translate("settings_tab.thermal_measurement_temp"), 0.0, self.thermal_fields, "measurement_temp")
        self.thermal_fields['target_temp'] = self._add_line_edit(form, self.localization.translate("settings_tab.thermal_target_temp"), 0.0, self.thermal_fields, "target_temp")
        self.thermal_fields['chamber_factor'] = self._add_line_edit(form, self.localization.translate("settings_tab.chamber_factor"), 0.0, self.thermal_fields, "chamber_factor")
        self.thermal_fields['pei_thickness'] = self._add_line_edit(form, self.localization.translate("settings_tab.pei_thickness"), 0.0, self.thermal_fields, "pei_thickness")
        self.thermal_fields['steel_thickness'] = self._add_line_edit(form, self.localization.translate("settings_tab.steel_thickness"), 0.0, self.thermal_fields, "steel_thickness")
        self.thermal_fields['alpha_pei'] = self._add_line_edit(form, self.localization.translate("settings_tab.alpha_pei"), 0.0, self.thermal_fields, "alpha_pei")
        self.thermal_fields['alpha_steel'] = self._add_line_edit(form, self.localization.translate("settings_tab.alpha_steel"), 0.0, self.thermal_fields, "alpha_steel")
        self.thermal_fields['beta_uniform'] = self._add_line_edit(form, self.localization.translate("settings_tab.beta_uniform"), 0.0, self.thermal_fields, "beta_uniform")
        return frame

    def _build_visualization_group(self) -> QFrame:
        title = self.localization.translate("settings_tab.visualization")
        frame, form = self._build_card(title)
        vis = self.settings.visualization
        interpolation = self._add_line_edit(form, self.localization.translate("settings_tab.interpolation_factor"), vis.interpolation_factor, self.visualization_fields, "interpolation_factor")
        interpolation.setValidator(None)

        self.visualization_checks['show_minutes'] = self._add_checkbox(form, self.localization.translate("settings_tab.show_minutes"), vis.show_minutes)
        self.visualization_checks['show_degrees'] = self._add_checkbox(form, self.localization.translate("settings_tab.show_degrees"), vis.show_degrees)
        return frame

    def _add_checkbox(self, form: QFormLayout, label: str, checked: bool) -> QCheckBox:
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        form.addRow(label, checkbox)
        return checkbox

    def _build_workflow_group(self) -> QFrame:
        title = self.localization.translate("settings_tab.workflow")
        frame, form = self._build_card(title)
        wf = self.settings.workflow
        self.workflow_checks['enable_belt'] = self._add_checkbox(form, self.localization.translate("settings_tab.enable_belt"), wf.enable_belt)
        self.workflow_checks['enable_screws'] = self._add_checkbox(form, self.localization.translate("settings_tab.enable_screws"), wf.enable_screws)
        self.workflow_checks['enable_tape'] = self._add_checkbox(form, self.localization.translate("settings_tab.enable_tape"), wf.enable_tape)
        return frame

    # ------------------------------------------------------------------ save/reset
    def _handle_save(self) -> None:
        tr = self.localization.translate
        try:
            hardware = self.settings.hardware
            for key, edit in self.hardware_fields.items():
                setattr(hardware, key, float(edit.text()))
            hardware.screw_mode = self._selected_screw_mode()

            thresholds = self.settings.thresholds
            for key, edit in self.threshold_fields.items():
                setattr(thresholds, key, float(edit.text()))

            self._update_current_preset_from_fields()
            self._sync_environment_with_active_preset()

            environment = self.settings.environment
            for key, edit in self.environment_fields.items():
                setattr(environment, key, float(edit.text()))

            visualization = self.settings.visualization
            visualization.interpolation_factor = int(self.visualization_fields['interpolation_factor'].text())
            visualization.show_minutes = self.visualization_checks['show_minutes'].isChecked()
            visualization.show_degrees = self.visualization_checks['show_degrees'].isChecked()

            workflow = self.settings.workflow
            for key, checkbox in self.workflow_checks.items():
                setattr(workflow, key, checkbox.isChecked())

            self.app_state.update_settings(self.settings)
            QMessageBox.information(self, "", tr("settings_tab.settings_saved"))
        except ValueError:
            QMessageBox.warning(self, tr("Warning"), tr("settings_tab.numeric_error"))

    def _handle_reset(self) -> None:
        tr = self.localization.translate
        default = ApplicationSettings()
        self.settings = default
        self.settings_service.settings = default
        self._refresh_fields()
        self.app_state.update_settings(default)
        QMessageBox.information(self, "", tr("settings_tab.settings_reset"))

    def _refresh_fields(self) -> None:
        hw = self.settings.hardware
        for key, edit in self.hardware_fields.items():
            edit.setText(str(getattr(hw, key)))

        mode = getattr(hw, "screw_mode", "hold_nut")
        if mode not in self.screw_mode_buttons:
            mode = "hold_nut"
        for key, button in self.screw_mode_buttons.items():
            button.setChecked(key == mode)

        th = self.settings.thresholds
        for key, edit in self.threshold_fields.items():
            edit.setText(str(getattr(th, key)))

        env = self.settings.environment
        for key, edit in self.environment_fields.items():
            edit.setText(str(getattr(env, key)))

        vis = self.settings.visualization
        self.visualization_fields['interpolation_factor'].setText(str(vis.interpolation_factor))
        self.visualization_checks['show_minutes'].setChecked(vis.show_minutes)
        self.visualization_checks['show_degrees'].setChecked(vis.show_degrees)

        wf = self.settings.workflow
        for key, checkbox in self.workflow_checks.items():
            checkbox.setChecked(getattr(wf, key))

        self._refresh_thermal_presets()

    def _selected_screw_mode(self) -> str:
        for mode, button in self.screw_mode_buttons.items():
            if button.isChecked():
                return mode
        return "hold_nut"

    # ------------------------------------------------------------------ thermal presets helpers
    def _refresh_thermal_presets(self) -> None:
        combo = self.thermal_combo
        if combo is None:
            return
        combo.blockSignals(True)
        combo.clear()
        for preset in self.settings.thermal_presets:
            combo.addItem(preset.name)
        active_name = self.settings.active_thermal_preset
        index = 0
        if active_name:
            for i, preset in enumerate(self.settings.thermal_presets):
                if preset.name == active_name:
                    index = i
                    break
        combo.blockSignals(False)
        combo.setCurrentIndex(index)
        self._current_preset_index = index
        self._load_preset_fields(index)

    def _load_preset_fields(self, index: int) -> None:
        if index < 0 or index >= len(self.settings.thermal_presets):
            for edit in self.thermal_fields.values():
                edit.setText("")
            return
        preset = self.settings.thermal_presets[index]
        self.thermal_fields['name'].setText(preset.name)
        self.thermal_fields['measurement_temp'].setText(str(preset.measurement_temp))
        self.thermal_fields['target_temp'].setText(str(preset.target_temp))
        self.thermal_fields['chamber_factor'].setText(str(preset.chamber_factor))
        self.thermal_fields['pei_thickness'].setText(str(preset.pei_thickness))
        self.thermal_fields['steel_thickness'].setText(str(preset.steel_thickness))
        self.thermal_fields['alpha_pei'].setText(str(preset.alpha_pei))
        self.thermal_fields['alpha_steel'].setText(str(preset.alpha_steel))
        self.thermal_fields['beta_uniform'].setText(str(preset.beta_uniform))
        self.settings.active_thermal_preset = preset.name
        self._populate_environment_from_preset(preset)

    def _handle_preset_change(self, index: int) -> None:
        self._update_current_preset_from_fields(self._current_preset_index)
        self._current_preset_index = index
        self._load_preset_fields(index)

    def _handle_add_preset(self) -> None:
        base_name = self.localization.translate("settings_tab.thermal_new")
        existing = {preset.name for preset in self.settings.thermal_presets}
        counter = 1
        name = f"{base_name} {counter}"
        while name in existing:
            counter += 1
            name = f"{base_name} {counter}"
        new_preset = ThermalPreset(name=name)
        self.settings.thermal_presets.append(new_preset)
        if self.thermal_combo:
            self.thermal_combo.addItem(new_preset.name)
            self.thermal_combo.setCurrentIndex(self.thermal_combo.count() - 1)

    def _handle_remove_preset(self) -> None:
        if len(self.settings.thermal_presets) <= 1:
            return
        index = self.thermal_combo.currentIndex() if self.thermal_combo else -1
        if index < 0:
            return
        removed = self.settings.thermal_presets.pop(index)
        if self.settings.active_thermal_preset == removed.name:
            self.settings.active_thermal_preset = self.settings.thermal_presets[0].name
        self._current_preset_index = 0
        self._refresh_thermal_presets()

    def _update_current_preset_from_fields(self, index_override: int | None = None) -> None:
        combo = self.thermal_combo
        if combo is None:
            return
        index = index_override if index_override is not None else combo.currentIndex()
        if index < 0 or index >= len(self.settings.thermal_presets):
            return
        preset = self.settings.thermal_presets[index]
        try:
            preset.name = self.thermal_fields['name'].text().strip() or preset.name
            preset.measurement_temp = float(self.thermal_fields['measurement_temp'].text())
            preset.target_temp = float(self.thermal_fields['target_temp'].text())
            preset.chamber_factor = float(self.thermal_fields['chamber_factor'].text())
            preset.pei_thickness = float(self.thermal_fields['pei_thickness'].text())
            preset.steel_thickness = float(self.thermal_fields['steel_thickness'].text())
            preset.alpha_pei = float(self.thermal_fields['alpha_pei'].text())
            preset.alpha_steel = float(self.thermal_fields['alpha_steel'].text())
            preset.beta_uniform = float(self.thermal_fields['beta_uniform'].text())
        except ValueError:
            return
        combo.setItemText(index, preset.name)
        self.settings.active_thermal_preset = preset.name

    def _populate_environment_from_preset(self, preset: ThermalPreset) -> None:
        # Update environment inputs so core settings stay in sync with preset selection
        if 'measurement_temp' in self.environment_fields:
            self.environment_fields['measurement_temp'].setText(str(preset.measurement_temp))
        if 'target_temp' in self.environment_fields:
            self.environment_fields['target_temp'].setText(str(preset.target_temp))

    def _sync_environment_with_active_preset(self) -> None:
        combo = self.thermal_combo
        if combo is None:
            return
        index = combo.currentIndex()
        if index < 0 or index >= len(self.settings.thermal_presets):
            return
        preset = self.settings.thermal_presets[index]
        env = self.settings.environment
        env.measurement_temp = preset.measurement_temp
        env.target_temp = preset.target_temp
        if 'measurement_temp' in self.environment_fields:
            self.environment_fields['measurement_temp'].setText(str(preset.measurement_temp))
        if 'target_temp' in self.environment_fields:
            self.environment_fields['target_temp'].setText(str(preset.target_temp))
