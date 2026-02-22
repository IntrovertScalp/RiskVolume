from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QSlider,
    QGridLayout,
    QComboBox,
    QWidget,
    QSpinBox,
    QAbstractSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QFrame,
    QMessageBox,
)
from translations import TRANS  # Импортируем наш новый файл
from PyQt6.QtCore import Qt, QPoint, QRegularExpression, QRect
from PyQt6.QtGui import (
    QRegularExpressionValidator,
    QPainter,
    QPen,
    QColor,
    QFont,
    QIntValidator,
)


class CustomCheckBox(QCheckBox):
    """Чекбокс с кастомной отрисовкой галочки"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(20, 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Рисуем прямоугольник индикатора
        rect = QRect(1, 1, 18, 18)

        if self.isChecked():
            # Зеленый фон когда включено
            painter.fillRect(rect, QColor(0x38, 0xBE, 0x1D))
            painter.setPen(QPen(QColor(0x38, 0xBE, 0x1D), 1))
            painter.drawRoundedRect(rect, 3, 3)

            # Рисуем черную галочку
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            # Координаты галочки
            painter.drawLine(5, 10, 8, 13)
            painter.drawLine(8, 13, 14, 6)
        else:
            # Серый фон когда выключено
            painter.fillRect(rect, QColor(0x2A, 0x2A, 0x2A))
            painter.setPen(QPen(QColor(0x44, 0x44, 0x44), 1))
            painter.drawRoundedRect(rect, 3, 3)


class HotkeyEdit(QLineEdit):
    def __init__(self, *args, placeholder_text=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setPlaceholderText(placeholder_text or "Нажми клавишу...")
        self.setStyleSheet(
            """
            QLineEdit { 
                background: #252525; 
                color: #38BE1D; 
                border: 1px solid #333; 
                padding: 4px; 
                border-radius: 4px; 
                font-weight: bold; 
            }
            QLineEdit:hover { border: 1px solid #38BE1D; background: #2a2a2a; }
            QLineEdit:focus { border: 1px solid #FF9F0A; background: #333; }
        """
        )

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.setText("esc")
            return

        if key in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        ):
            return

        mods = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            mods.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            mods.append("alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            mods.append("shift")

        special_keys = {
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "page up",
            Qt.Key.Key_PageDown: "page down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_F1: "f1",
            Qt.Key.Key_F2: "f2",
            Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5",
            Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7",
            Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10",
            Qt.Key.Key_F11: "f11",
            Qt.Key.Key_F12: "f12",
        }

        key_name = special_keys.get(key)
        if not key_name:
            if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                key_name = chr(ord("a") + (int(key) - int(Qt.Key.Key_A)))
            elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
                key_name = str(int(key) - int(Qt.Key.Key_0))
            else:
                key_name = (event.text() or "").strip().lower()

        if key_name:
            self.setText("+".join(mods + [key_name]) if mods else key_name)


class SettingsDialog(QDialog):
    def show_about_dialog(self):
        from about_dialog import AboutDialog

        dlg = AboutDialog(self)
        dlg.exec()

    def show_donate_dialog(self):
        try:
            from donate_dialog import DonateDialog

            dlg = DonateDialog(self)
            dlg.exec()
        except ModuleNotFoundError as e:
            t = TRANS.get(self.parent_window.settings.get("lang", "ru"), TRANS["ru"])
            QMessageBox.warning(
                self,
                t["support_title"],
                t["support_qr_missing"],
            )
        except Exception as e:
            t = TRANS.get(self.parent_window.settings.get("lang", "ru"), TRANS["ru"])
            QMessageBox.warning(
                self,
                t["support_title"],
                t["support_open_failed"].format(error=e),
            )

    def _create_checkmark_icon(self):
        import os
        import tempfile

        path = os.path.join(tempfile.gettempdir(), "rv_checkmark.png")
        if not os.path.exists(path):
            pix = QPixmap(12, 12)
            pix.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pix)
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(2, 6, 5, 9)
            painter.drawLine(5, 9, 10, 3)
            painter.end()
            pix.save(path, "PNG")

        self._checkmark_path_css = path.replace("\\", "/")
        return path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        lang_code = parent.settings.get("lang", "ru")
        t = TRANS[lang_code]

        # --- ВОССТАНОВЛЕНИЕ ПОЗИЦИИ ОКНА ---
        if "settings_pos" in parent.settings:
            pos = parent.settings["settings_pos"]
            self.move(pos[0], pos[1])

        self.setStyleSheet(
            """
            QDialog { background: #1E1E1E; border: 2px solid #555; border-radius: 8px; }
            QLabel { color: #ccc; font-size: 10pt; font-weight: bold; }
            QLabel#SectionHeader { color: #38BE1D; font-size: 9pt; font-weight: bold; margin-top: 5px; }
            QLineEdit#FeeInput, QLineEdit#PrecInput { 
                background: #252525; color: #38BE1D; border: 1px solid #333; 
                padding: 4px; border-radius: 4px; font-weight: bold; 
            }
            QLineEdit#FeeInput:hover, QLineEdit#PrecInput:hover { border: 1px solid #38BE1D; }
            QPushButton { 
                background: #38BE1D; color: black; border: none; 
                padding: 8px; border-radius: 4px; font-weight: bold; 
            }
            QPushButton:hover { background: #45e024; }
            QPushButton#CloseBtn { background: #444; color: white; }
            QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
            QSlider::handle:horizontal { background: #38BE1D; width: 14px; margin: -5px 0; border-radius: 7px; }
            QCheckBox { color: #ccc; font-size: 10pt; font-weight: bold; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                background: #2a2a2a;
                border: 1px solid #444;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background: #38BE1D;
                border: 1px solid #38BE1D;
            }
            QFrame#Separator {
                background: #333;
                max-height: 1px;
            }
        """
        )

        layout = QVBoxLayout(self)

        # Добавляем пустое место сверху (шапка окна)
        layout.addSpacing(32)

        # --- КНОПКИ ---
        extra_btns = QHBoxLayout()
        self.btn_about = QPushButton(t["about_btn"])
        self.btn_about.clicked.connect(self.show_about_dialog)
        self.btn_about.setAutoDefault(False)
        self.btn_about.setDefault(False)
        self.btn_donate = QPushButton(t["support_btn"])
        self.btn_donate.clicked.connect(self.show_donate_dialog)
        self.btn_donate.setAutoDefault(False)
        self.btn_donate.setDefault(False)
        # Темный стиль для этих двух кнопок
        dark_style = (
            "QPushButton {"
            "background: #2a2a2a;"
            "color: white;"
            "border-radius: 6px;"
            "border: 1px solid #3a3a3a;"
            "font-weight: bold;"
            "font-size: 11px;"
            "padding: 6px 12px;"
            "}"
            "QPushButton:hover {"
            "background: #3a3a3a;"
            "border: 1px solid #555;"
            "}"
        )
        self.btn_about.setStyleSheet(dark_style)
        self.btn_donate.setStyleSheet(dark_style)
        extra_btns.addWidget(self.btn_about)
        extra_btns.addWidget(self.btn_donate)
        layout.addLayout(extra_btns)

        # Масштаб и язык
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel(t["scale"]))
        self.cb_scale = QComboBox()
        # Internal scales: 130-200, displayed as 100-170
        self.scale_display = [
            str(i) for i in range(100, 180, 10)
        ]  # [100, 110, 120, ..., 170]
        self.scale_actual = [
            i for i in range(130, 210, 10)
        ]  # [130, 140, 150, ..., 200]
        self.cb_scale.addItems(self.scale_display)
        current_scale = int(parent.settings.get("scale", 130))
        # Find display index from actual scale
        if current_scale in self.scale_actual:
            idx = self.scale_actual.index(current_scale)
            self.cb_scale.setCurrentIndex(idx)
        scale_row.addWidget(self.cb_scale)

        # Компактное меню языка
        scale_row.addSpacing(20)
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["Русский", "English"])
        self.combo_lang.setCurrentIndex(0 if lang_code == "ru" else 1)
        self.combo_lang.setStyleSheet(
            "background: #252525; color: white; padding: 4px;"
        )
        self.combo_lang.setFixedWidth(100)
        scale_row.addWidget(self.combo_lang)

        scale_row.addStretch()
        layout.addLayout(scale_row)
        # Определяем текущий язык
        lang_code = parent.settings.get("lang", "ru")
        t = TRANS[lang_code]

        grid = QGridLayout()

        # Поля ввода клавиш
        self.hk_show = HotkeyEdit(
            parent.settings.get("hk_show", "f1"), placeholder_text=t["hk_placeholder"]
        )
        self.hk_coords = HotkeyEdit(
            parent.settings.get("hk_coords", "f2"),
            placeholder_text=t["hk_placeholder"],
        )

        # Комиссия
        fee_total = float(parent.settings.get("fee_percent", 0.1))
        fee_taker = float(parent.settings.get("fee_taker", fee_total / 2))
        fee_maker = float(parent.settings.get("fee_maker", fee_total / 2))
        self.inp_fee_taker = QLineEdit(str(fee_taker))
        self.inp_fee_taker.setObjectName("FeeInput")
        self.inp_fee_maker = QLineEdit(str(fee_maker))
        self.inp_fee_maker.setObjectName("FeeInput")
        self.inp_fee_taker.textChanged.connect(self._preview_fee_change)
        self.inp_fee_maker.textChanged.connect(self._preview_fee_change)

        # Чекбокс для учета комиссии
        self.chk_use_fee = CustomCheckBox()
        use_fee = parent.settings.get("use_fee", True)
        self.chk_use_fee.setChecked(use_fee)
        self.chk_use_fee.stateChanged.connect(self.toggle_fee_fields)
        self.chk_use_fee.stateChanged.connect(self._preview_fee_change)

        # Метки для полей комиссии
        self.lbl_fee_maker = QLabel(t["fee_maker"])
        self.lbl_fee_taker = QLabel(t["fee_taker"])

        # Настройки точности
        self.prec_dep = QLineEdit(str(parent.settings.get("prec_dep", 2)))
        self.prec_risk = QLineEdit(str(parent.settings.get("prec_risk", 2)))
        self.prec_fee = QLineEdit(str(parent.settings.get("prec_fee", 3)))
        self.prec_lev = QLineEdit(str(parent.settings.get("prec_lev", 1)))  # ПЛЕЧО

        for inp in [
            self.prec_dep,
            self.prec_risk,
            self.prec_fee,
            self.prec_lev,
        ]:
            inp.setObjectName("PrecInput")
            inp.setFixedWidth(45)

        # --- НАЧАЛО ЗАМЕНЫ БЛОКА GRID ---
        row = 0

        # === ГОРЯЧИЕ КЛАВИШИ ===
        lbl_hotkeys = QLabel(t["section_hotkeys"])
        lbl_hotkeys.setObjectName("SectionHeader")
        grid.addWidget(lbl_hotkeys, row, 0, 1, 2)
        row += 1

        grid.addWidget(QLabel(t["hide"]), row, 0)
        grid.addWidget(self.hk_show, row, 1)
        row += 1
        grid.addWidget(QLabel(t["coords"]), row, 0)
        grid.addWidget(self.hk_coords, row, 1)
        row += 1

        self.chk_minimize_after_apply = QCheckBox(t["minimize_after_apply"])
        self.chk_minimize_after_apply.setObjectName("MinimizeAfterApply")
        self.chk_minimize_after_apply.setChecked(
            bool(parent.settings.get("minimize_after_apply", True))
        )
        self._create_checkmark_icon()
        self.chk_minimize_after_apply.setStyleSheet(
            "QCheckBox#MinimizeAfterApply { color: #aaa; font-size: 9pt; spacing: 5px; }"
            "QCheckBox#MinimizeAfterApply::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #555; background: #1A1A1A; }"
            f"QCheckBox#MinimizeAfterApply::indicator:checked {{ background: #38BE1D; border: 1px solid #38BE1D; image: url({self._checkmark_path_css}); }}"
        )
        grid.addWidget(self.chk_minimize_after_apply, row, 0, 1, 2)
        row += 1

        # Разделитель
        sep1 = QFrame()
        sep1.setObjectName("Separator")
        sep1.setFrameShape(QFrame.Shape.HLine)
        grid.addWidget(sep1, row, 0, 1, 2)
        row += 1
        grid.setRowMinimumHeight(row, 8)  # Отступ
        row += 1

        # === КОМИССИЯ ===
        lbl_fee = QLabel(t["section_fee"])
        lbl_fee.setObjectName("SectionHeader")
        grid.addWidget(lbl_fee, row, 0, 1, 2)
        row += 1

        grid.addWidget(QLabel(t["use_fee"]), row, 0)
        grid.addWidget(self.chk_use_fee, row, 1)
        row += 1
        grid.addWidget(self.lbl_fee_maker, row, 0)
        grid.addWidget(self.inp_fee_maker, row, 1)
        row += 1
        grid.addWidget(self.lbl_fee_taker, row, 0)
        grid.addWidget(self.inp_fee_taker, row, 1)
        row += 1

        # Разделитель
        sep2 = QFrame()
        sep2.setObjectName("Separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        grid.addWidget(sep2, row, 0, 1, 2)
        row += 1
        grid.setRowMinimumHeight(row, 8)  # Отступ
        row += 1

        # === ТОЧНОСТЬ ОТОБРАЖЕНИЯ ===
        lbl_prec = QLabel(t["section_precision"])
        lbl_prec.setObjectName("SectionHeader")
        grid.addWidget(lbl_prec, row, 0, 1, 2)
        row += 1

        grid.addWidget(QLabel(t["prec_dep"]), row, 0)
        grid.addWidget(self.prec_dep, row, 1)
        row += 1
        grid.addWidget(QLabel(t["prec_risk"]), row, 0)
        grid.addWidget(self.prec_risk, row, 1)
        row += 1
        grid.addWidget(QLabel(t["prec_fee"]), row, 0)
        grid.addWidget(self.prec_fee, row, 1)
        row += 1
        grid.addWidget(QLabel(t["prec_lev"]), row, 0)
        grid.addWidget(self.prec_lev, row, 1)
        # --- КОНЕЦ ЗАМЕНЫ БЛОКА GRID ---

        layout.addLayout(grid)

        # --- КНОПКИ ---
        btns = QHBoxLayout()
        save_btn = QPushButton(t["save"])
        save_btn.clicked.connect(self.save_and_close)
        close_btn = QPushButton(t["cancel"])
        close_btn.setObjectName("CloseBtn")
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn)
        btns.addWidget(save_btn)
        layout.addLayout(btns)

        # Применяем начальное состояние полей комиссии
        self.toggle_fee_fields()

        # Верхняя большая кнопка закрытия (правый верхний угол). Не добавляем в layout.
        self.top_close_btn = QPushButton("✕", self)
        self.top_close_btn.setObjectName("TopCloseBtn")
        self.top_close_btn.setFixedSize(40, 30)
        self.top_close_btn.clicked.connect(self.close)
        self.top_close_btn.setStyleSheet(
            "QPushButton#TopCloseBtn { background: transparent; color: white; border: none; font-weight: bold; font-size: 18px; }"
            "QPushButton#TopCloseBtn:hover { color: #ff3333; }"
        )
        self.top_close_btn.raise_()

        self._install_enter_accept_handlers()

    def _install_enter_accept_handlers(self):
        for widget in self.findChildren(QLineEdit):
            if isinstance(widget, HotkeyEdit):
                continue
            widget.installEventFilter(self)
        for widget in self.findChildren(QAbstractSpinBox):
            widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress and event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        ):
            if isinstance(obj, (QLineEdit, QAbstractSpinBox)) and not isinstance(
                obj, HotkeyEdit
            ):
                if isinstance(obj, QAbstractSpinBox):
                    obj.interpretText()
                if isinstance(obj, QLineEdit):
                    obj.deselect()
                obj.clearFocus()
                return True
        return super().eventFilter(obj, event)

    def toggle_fee_fields(self):
        """Показать/скрыть поля комиссии в зависимости от чекбокса"""
        is_checked = self.chk_use_fee.isChecked()
        self.lbl_fee_maker.setVisible(is_checked)
        self.inp_fee_maker.setVisible(is_checked)
        self.lbl_fee_taker.setVisible(is_checked)
        self.inp_fee_taker.setVisible(is_checked)

    def _preview_fee_change(self):
        if not self.parent_window:
            return

        try:
            fee_taker = float(self.inp_fee_taker.text().replace(",", ".") or 0)
        except Exception:
            fee_taker = 0.0
        try:
            fee_maker = float(self.inp_fee_maker.text().replace(",", ".") or 0)
        except Exception:
            fee_maker = 0.0

        self.parent_window.settings["use_fee"] = self.chk_use_fee.isChecked()
        self.parent_window.settings["fee_taker"] = fee_taker
        self.parent_window.settings["fee_maker"] = fee_maker
        self.parent_window.settings["fee_percent"] = fee_taker + fee_maker
        self.parent_window.schedule_update_calc()

    def _clamp_prec_vol_input(self, value):
        if not value:
            return

        try:
            num = int(value)
        except ValueError:
            self.prec_vol.setText("0")
            return

        if num > 6:
            self.prec_vol.setText("6")

    def _safe_int(self, text, default, min_val=None, max_val=None):
        try:
            num = int(text)
        except ValueError:
            num = default

        if min_val is not None:
            num = max(min_val, num)
        if max_val is not None:
            num = min(max_val, num)
        return num

    def save_and_close(self):
        try:
            fee_taker = float(self.inp_fee_taker.text().replace(",", "."))
        except:
            fee_taker = 0.05
        try:
            fee_maker = float(self.inp_fee_maker.text().replace(",", "."))
        except:
            fee_maker = 0.05
        fee_val = fee_taker + fee_maker

        # Сохраняем позицию окна
        current_pos = [self.x(), self.y()]

        prec_dep = self._safe_int(self.prec_dep.text() or "", 2, 0, 6)
        prec_risk = self._safe_int(self.prec_risk.text() or "", 2, 0, 6)
        prec_fee = self._safe_int(self.prec_fee.text() or "", 3, 0, 6)
        prec_lev = self._safe_int(self.prec_lev.text() or "", 1, 0, 6)

        self.prec_dep.setText(str(prec_dep))
        self.prec_risk.setText(str(prec_risk))
        self.prec_fee.setText(str(prec_fee))
        self.prec_lev.setText(str(prec_lev))
        self.parent_window.settings.update(
            {
                "scale": self.scale_actual[self.cb_scale.currentIndex()],
                "hk_show": self.hk_show.text(),
                "hk_coords": self.hk_coords.text(),
                "minimize_after_apply": self.chk_minimize_after_apply.isChecked(),
                "use_fee": self.chk_use_fee.isChecked(),
                "fee_taker": fee_taker,
                "fee_maker": fee_maker,
                "fee_percent": fee_val,
                "prec_dep": prec_dep,
                "prec_risk": prec_risk,
                "prec_fee": prec_fee,
                "prec_lev": prec_lev,
                "prec_min_order": 0,
                "settings_pos": current_pos,
                "lang": "ru" if self.combo_lang.currentIndex() == 0 else "en",
            }
        )
        self.parent_window.save_settings()
        self.parent_window.refresh_labels()
        self.parent_window.apply_styles()
        self.parent_window.rebind_hotkeys()
        self.parent_window.update_calc()
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, "old_pos"):
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Позиционируем кнопку в правом верхнем углу (в шапке окна)
        try:
            if hasattr(self, "top_close_btn"):
                x = self.width() - self.top_close_btn.width() - 8
                y = 6
                self.top_close_btn.move(x, y)
        except Exception:
            pass
