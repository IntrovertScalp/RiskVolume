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
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QFrame,
)
from translations import TRANS  # Импортируем наш новый файл
from PyQt6.QtCore import Qt, QPoint, QRegularExpression, QRect
from PyQt6.QtGui import QRegularExpressionValidator, QPainter, QPen, QColor, QFont


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setPlaceholderText("Нажми клавишу...")
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

        key_name = special_keys.get(key, event.text().lower())
        if key_name:
            self.setText("+".join(mods + [key_name]) if mods else key_name)


class SettingsDialog(QDialog):
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

        # Масштаб и язык
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel(t["scale"]))
        self.cb_scale = QComboBox()
        scales = [str(i) for i in range(80, 210, 10)]
        self.cb_scale.addItems(scales)
        current_scale = int(parent.settings.get("scale", 100))
        idx = self.cb_scale.findText(str(current_scale))
        if idx >= 0:
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
        self.hk_show = HotkeyEdit(parent.settings.get("hk_show", "f1"))
        self.hk_coords = HotkeyEdit(parent.settings.get("hk_coords", "f2"))

        # Комиссия
        fee_total = float(parent.settings.get("fee_percent", 0.1))
        fee_taker = float(parent.settings.get("fee_taker", fee_total / 2))
        fee_maker = float(parent.settings.get("fee_maker", fee_total / 2))
        self.inp_fee_taker = QLineEdit(str(fee_taker))
        self.inp_fee_taker.setObjectName("FeeInput")
        self.inp_fee_maker = QLineEdit(str(fee_maker))
        self.inp_fee_maker.setObjectName("FeeInput")

        # Чекбокс для учета комиссии
        self.chk_use_fee = CustomCheckBox()
        use_fee = parent.settings.get("use_fee", True)
        self.chk_use_fee.setChecked(use_fee)
        self.chk_use_fee.stateChanged.connect(self.toggle_fee_fields)

        # Метки для полей комиссии
        self.lbl_fee_maker = QLabel(t["fee_maker"])
        self.lbl_fee_taker = QLabel(t["fee_taker"])

        # Настройки точности
        self.prec_dep = QLineEdit(str(parent.settings.get("prec_dep", 2)))
        self.prec_risk = QLineEdit(str(parent.settings.get("prec_risk", 2)))
        self.prec_fee = QLineEdit(str(parent.settings.get("prec_fee", 3)))
        self.prec_vol = QLineEdit(str(parent.settings.get("prec_vol", 0)))
        self.prec_lev = QLineEdit(str(parent.settings.get("prec_lev", 1)))  # ПЛЕЧО

        for inp in [
            self.prec_dep,
            self.prec_risk,
            self.prec_fee,
            self.prec_vol,
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
        row += 1
        grid.addWidget(QLabel(t["prec_vol"]), row, 0)
        grid.addWidget(self.prec_vol, row, 1)
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

    def toggle_fee_fields(self):
        """Показать/скрыть поля комиссии в зависимости от чекбокса"""
        is_checked = self.chk_use_fee.isChecked()
        self.lbl_fee_maker.setVisible(is_checked)
        self.inp_fee_maker.setVisible(is_checked)
        self.lbl_fee_taker.setVisible(is_checked)
        self.inp_fee_taker.setVisible(is_checked)

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

        self.parent_window.settings.update(
            {
                "scale": int(self.cb_scale.currentText()),
                "hk_show": self.hk_show.text(),
                "hk_coords": self.hk_coords.text(),
                "use_fee": self.chk_use_fee.isChecked(),
                "fee_taker": fee_taker,
                "fee_maker": fee_maker,
                "fee_percent": fee_val,
                "prec_dep": int(self.prec_dep.text() or 2),
                "prec_risk": int(self.prec_risk.text() or 2),
                "prec_fee": int(self.prec_fee.text() or 3),
                "prec_vol": int(self.prec_vol.text() or 0),
                "prec_lev": int(self.prec_lev.text() or 1),
                "settings_pos": current_pos,
                "lang": "ru" if self.combo_lang.currentIndex() == 0 else "en",
            }
        )
        self.parent_window.save_settings()
        self.parent_window.apply_styles()
        self.parent_window.rebind_hotkeys()
        self.parent_window.update_calc()
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, "old_pos"):
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
