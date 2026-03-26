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
    QScrollArea,
    QAbstractItemView,
    QListView,
)
from translations import TRANS  # Импортируем наш новый файл
from PyQt6.QtCore import Qt, QPoint, QRegularExpression, QRect, QItemSelectionModel
from PyQt6.QtGui import (
    QRegularExpressionValidator,
    QPainter,
    QPen,
    QColor,
    QFont,
    QIntValidator,
    QPixmap,
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


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class HoverHighlightListView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def mouseMoveEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            sel = self.selectionModel()
            if sel is not None:
                sel.setCurrentIndex(
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect,
                )
        super().mouseMoveEvent(event)


class SettingsDialog(QDialog):
    def _enable_combo_popup_hover_highlight(self, combo):
        view = HoverHighlightListView(combo)
        combo.setView(view)

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
            QComboBox#ScaleCombo, QComboBox#LangCombo {
                background: #252525;
                color: #EAEAEA;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px 22px 4px 8px;
                min-height: 20px;
            }
            QComboBox#ScaleCombo:hover, QComboBox#LangCombo:hover {
                border: 1px solid #38BE1D;
            }
            QComboBox#AutoDepCombo:hover {
                border: 1px solid #38BE1D;
            }
            QComboBox#ScaleCombo:focus, QComboBox#LangCombo:focus {
                border: 1px solid #333;
            }
            QComboBox#AutoDepCombo:focus {
                border: 1px solid #333;
            }
            QComboBox#ScaleCombo::drop-down, QComboBox#LangCombo::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox#AutoDepCombo::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox#ScaleCombo::down-arrow, QComboBox#LangCombo::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #B8B8B8;
                width: 0;
                height: 0;
                margin-right: 6px;
            }
            QComboBox#AutoDepCombo::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #B8B8B8;
                width: 0;
                height: 0;
                margin-right: 6px;
            }
            QComboBox#ScaleCombo QAbstractItemView, QComboBox#LangCombo QAbstractItemView {
                background: #252525;
                color: #EAEAEA;
                border: 1px solid #333;
                selection-background-color: #38BE1D;
                selection-color: black;
            }
            QComboBox#LangCombo QAbstractItemView::item:hover {
                background: #38BE1D;
                color: black;
            }
            QComboBox#LangCombo QAbstractItemView::item:selected {
                background: #38BE1D;
                color: black;
            }
            QComboBox#AutoDepCombo QAbstractItemView {
                background: #252525;
                color: #EAEAEA;
                border: 1px solid #333;
                selection-background-color: #38BE1D;
                selection-color: black;
            }
        """
        )

        self.setMinimumWidth(390)
        self.resize(400, 560)

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
        self.cb_scale.setObjectName("ScaleCombo")
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
        self.cb_scale.setFixedWidth(96)
        self.cb_scale.activated.connect(self.cb_scale.clearFocus)
        scale_row.addWidget(self.cb_scale)

        # Компактное меню языка
        scale_row.addSpacing(20)
        self.combo_lang = QComboBox()
        self.combo_lang.setObjectName("LangCombo")
        self.combo_lang.addItems(["Русский", "English"])
        self.combo_lang.setCurrentIndex(0 if lang_code == "ru" else 1)
        self.combo_lang.setFixedWidth(118)
        self.combo_lang.activated.connect(self.combo_lang.clearFocus)
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

        # Авто-депозит через API
        self.chk_auto_deposit = CustomCheckBox()
        self.chk_auto_deposit.setChecked(
            bool(parent.settings.get("auto_dep_enabled", False))
        )
        self.chk_auto_deposit.stateChanged.connect(self._toggle_auto_deposit_fields)

        self.cb_auto_dep_exchange = NoWheelComboBox()
        self.cb_auto_dep_exchange.setObjectName("LangCombo")
        self._auto_dep_exchange_values = [
            "binance",
            "bybit",
            "okx",
            "gate",
            "bitget",
            "mexc",
            "kucoin",
        ]
        self.cb_auto_dep_exchange.addItems(
            ["Binance", "Bybit", "OKX", "Gate", "Bitget", "MEXC", "Kucoin"]
        )
        self._enable_combo_popup_hover_highlight(self.cb_auto_dep_exchange)
        self._auto_dep_credentials = self._normalize_auto_dep_credentials(
            parent.settings
        )
        saved_exchange = str(parent.settings.get("auto_dep_exchange", "binance"))
        try:
            self.cb_auto_dep_exchange.setCurrentIndex(
                self._auto_dep_exchange_values.index(saved_exchange)
            )
        except Exception:
            self.cb_auto_dep_exchange.setCurrentIndex(0)
        self._active_auto_dep_exchange = self._auto_dep_exchange_values[
            self.cb_auto_dep_exchange.currentIndex()
        ]
        self.cb_auto_dep_exchange.currentIndexChanged.connect(
            self._on_auto_dep_exchange_changed
        )

        self.cb_auto_dep_market = NoWheelComboBox()
        self.cb_auto_dep_market.setObjectName("LangCombo")
        self.cb_auto_dep_market.addItems(
            [t["auto_dep_market_futures"], t["auto_dep_market_spot"]]
        )
        self._enable_combo_popup_hover_highlight(self.cb_auto_dep_market)
        saved_market = str(parent.settings.get("auto_dep_market", "futures")).lower()
        self.cb_auto_dep_market.setCurrentIndex(1 if saved_market == "spot" else 0)

        self.inp_auto_dep_asset = QLineEdit(
            str(parent.settings.get("auto_dep_asset", "USDT"))
        )
        self.inp_auto_dep_asset.setObjectName("FeeInput")

        self.inp_auto_dep_api_key = QLineEdit(
            str(parent.settings.get("auto_dep_api_key", ""))
        )
        self.inp_auto_dep_api_key.setObjectName("FeeInput")

        self.inp_auto_dep_api_secret = QLineEdit(
            str(parent.settings.get("auto_dep_api_secret", ""))
        )
        self.inp_auto_dep_api_secret.setObjectName("FeeInput")
        self.inp_auto_dep_api_secret.setEchoMode(QLineEdit.EchoMode.Password)

        self.inp_auto_dep_api_passphrase = QLineEdit(
            str(parent.settings.get("auto_dep_api_passphrase", ""))
        )
        self.inp_auto_dep_api_passphrase.setObjectName("FeeInput")
        self.inp_auto_dep_api_passphrase.setEchoMode(QLineEdit.EchoMode.Password)
        self._load_auto_dep_credentials_for_exchange(self._active_auto_dep_exchange)

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
        sep_auto = QFrame()
        sep_auto.setObjectName("Separator")
        sep_auto.setFrameShape(QFrame.Shape.HLine)
        grid.addWidget(sep_auto, row, 0, 1, 2)
        row += 1
        grid.setRowMinimumHeight(row, 8)
        row += 1

        # === АВТО-ДЕПОЗИТ ===
        lbl_auto_dep = QLabel(t["section_auto_deposit"])
        lbl_auto_dep.setObjectName("SectionHeader")
        grid.addWidget(lbl_auto_dep, row, 0, 1, 2)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_enabled"]), row, 0)
        grid.addWidget(self.chk_auto_deposit, row, 1)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_exchange"]), row, 0)
        grid.addWidget(self.cb_auto_dep_exchange, row, 1)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_market"]), row, 0)
        grid.addWidget(self.cb_auto_dep_market, row, 1)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_asset"]), row, 0)
        grid.addWidget(self.inp_auto_dep_asset, row, 1)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_api_key"]), row, 0)
        grid.addWidget(self.inp_auto_dep_api_key, row, 1)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_api_secret"]), row, 0)
        grid.addWidget(self.inp_auto_dep_api_secret, row, 1)
        row += 1

        grid.addWidget(QLabel(t["auto_dep_api_passphrase"]), row, 0)
        grid.addWidget(self.inp_auto_dep_api_passphrase, row, 1)
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

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        grid_container.setLayout(grid)

        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setFrameShape(QFrame.Shape.NoFrame)
        grid_scroll.setWidget(grid_container)
        grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        grid_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
            "QScrollBar:vertical { background: #1A1A1A; width: 8px; border: none; }"
            "QScrollBar::handle:vertical { background: #3A3A3A; min-height: 24px; border-radius: 4px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #1A1A1A; }"
        )
        layout.addWidget(grid_scroll, 1)

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
        self._toggle_auto_deposit_fields()

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
        self._center_on_parent_window()

    def _center_on_parent_window(self):
        parent = self.parent_window
        if parent is None:
            return

        parent_geom = parent.frameGeometry()
        x = parent_geom.x() + (parent_geom.width() - self.width()) // 2
        y = parent_geom.y() + (parent_geom.height() - self.height()) // 2
        self.move(max(0, x), max(0, y))

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
            Qt.Key.Key_Escape,
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

    def _toggle_auto_deposit_fields(self, *_):
        is_checked = self.chk_auto_deposit.isChecked()
        for widget in (
            self.cb_auto_dep_exchange,
            self.cb_auto_dep_market,
            self.inp_auto_dep_asset,
            self.inp_auto_dep_api_key,
            self.inp_auto_dep_api_secret,
            self.inp_auto_dep_api_passphrase,
        ):
            widget.setEnabled(is_checked)

    def _normalize_auto_dep_credentials(self, settings):
        raw = settings.get("auto_dep_credentials", {})
        if not isinstance(raw, dict):
            raw = {}

        result = {}
        for exchange_id in self._auto_dep_exchange_values:
            source = raw.get(exchange_id, {})
            if not isinstance(source, dict):
                source = {}
            result[exchange_id] = {
                "api_key": str(source.get("api_key", "") or ""),
                "api_secret": str(source.get("api_secret", "") or ""),
                "api_passphrase": str(source.get("api_passphrase", "") or ""),
            }

        # Миграция старых общих ключей в Binance.
        if not any(result["binance"].values()):
            result["binance"] = {
                "api_key": str(settings.get("auto_dep_api_key", "") or ""),
                "api_secret": str(settings.get("auto_dep_api_secret", "") or ""),
                "api_passphrase": str(
                    settings.get("auto_dep_api_passphrase", "") or ""
                ),
            }

        return result

    def _store_current_auto_dep_credentials(self):
        exchange_id = self._active_auto_dep_exchange
        self._auto_dep_credentials[exchange_id] = {
            "api_key": self.inp_auto_dep_api_key.text().strip(),
            "api_secret": self.inp_auto_dep_api_secret.text().strip(),
            "api_passphrase": self.inp_auto_dep_api_passphrase.text().strip(),
        }

    def _load_auto_dep_credentials_for_exchange(self, exchange_id):
        creds = self._auto_dep_credentials.get(exchange_id, {})
        self.inp_auto_dep_api_key.setText(str(creds.get("api_key", "") or ""))
        self.inp_auto_dep_api_secret.setText(str(creds.get("api_secret", "") or ""))
        self.inp_auto_dep_api_passphrase.setText(
            str(creds.get("api_passphrase", "") or "")
        )

    def _on_auto_dep_exchange_changed(self, *_):
        self._store_current_auto_dep_credentials()
        new_exchange = self._auto_dep_exchange_values[
            self.cb_auto_dep_exchange.currentIndex()
        ]
        self._active_auto_dep_exchange = new_exchange
        self._load_auto_dep_credentials_for_exchange(new_exchange)

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
        self._store_current_auto_dep_credentials()
        try:
            fee_taker = float(self.inp_fee_taker.text().replace(",", "."))
        except:
            fee_taker = 0.05
        try:
            fee_maker = float(self.inp_fee_maker.text().replace(",", "."))
        except:
            fee_maker = 0.05
        fee_val = fee_taker + fee_maker

        prec_dep = self._safe_int(self.prec_dep.text() or "", 2, 0, 6)
        prec_risk = self._safe_int(self.prec_risk.text() or "", 2, 0, 6)
        prec_fee = self._safe_int(self.prec_fee.text() or "", 3, 0, 6)
        prec_lev = self._safe_int(self.prec_lev.text() or "", 1, 0, 6)

        self.prec_dep.setText(str(prec_dep))
        self.prec_risk.setText(str(prec_risk))
        self.prec_fee.setText(str(prec_fee))
        self.prec_lev.setText(str(prec_lev))
        selected_exchange = self._auto_dep_exchange_values[
            self.cb_auto_dep_exchange.currentIndex()
        ]
        selected_creds = self._auto_dep_credentials.get(selected_exchange, {})
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
                "auto_dep_enabled": self.chk_auto_deposit.isChecked(),
                "auto_dep_exchange": selected_exchange,
                "auto_dep_market": (
                    "spot" if self.cb_auto_dep_market.currentIndex() == 1 else "futures"
                ),
                "auto_dep_asset": (self.inp_auto_dep_asset.text() or "USDT").strip().upper(),
                "auto_dep_api_key": str(selected_creds.get("api_key", "") or ""),
                "auto_dep_api_secret": str(selected_creds.get("api_secret", "") or ""),
                "auto_dep_api_passphrase": str(
                    selected_creds.get("api_passphrase", "") or ""
                ),
                "auto_dep_credentials": self._auto_dep_credentials,
                "prec_dep": prec_dep,
                "prec_risk": prec_risk,
                "prec_fee": prec_fee,
                "prec_lev": prec_lev,
                "prec_min_order": 0,
                "lang": "ru" if self.combo_lang.currentIndex() == 0 else "en",
            }
        )
        self.parent_window.save_settings()
        self.parent_window.refresh_labels()
        self.parent_window.apply_styles()
        self.parent_window.rebind_hotkeys()
        if hasattr(self.parent_window, "_apply_auto_deposit_sync"):
            self.parent_window._apply_auto_deposit_sync(force_now=True)
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
