import sys, json, os, ctypes, time, keyboard, pyautogui, pyperclip
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QAbstractItemView,
)
from PyQt6.QtCore import (
    Qt,
    QRegularExpression,
    QTimer,
    pyqtSignal,
    QObject,
    QSharedMemory,
)
from PyQt6.QtGui import QIcon, QRegularExpressionValidator

from config import *
from settings_dialog import SettingsDialog
from logic import calculate_risk_data, get_info_html
from translations import TRANS
from cascade_tab import CascadeTab
from calculator_tab import init_calculator_tab

try:
    myappid = "introvert.scalp.v1"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass


class HotkeySignaler(QObject):
    toggle_sig = pyqtSignal()
    apply_sig = pyqtSignal()  # Новый сигнал для применения


class RiskVolumeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_scale = 150
        self.load_settings()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if os.path.exists(LOGO_PATH):
            self.setWindowIcon(QIcon(LOGO_PATH))

        self.last_toggle_time = 0
        # Флаг, чтобы отправка не запускалась дважды одновременно (Enter + горячая клавиша)
        self.apply_running = False
        self.signaler = HotkeySignaler()
        self.signaler.toggle_sig.connect(self.toggle_window)
        self.signaler.apply_sig.connect(
            self.handle_hotkey_apply
        )  # Единая точка входа для горячей клавиши

        self.old_pos = None
        self.current_vol = 0.0
        self.position_target_volume = 0.0
        self.table_volume_override = 0.0
        self._ghost_input = None
        self.calc_calibration_active = False

        self.init_ui()
        self.rebind_hotkeys()
        self.update_calc()

        # Сохраняем настройки при закрытии приложения любым способом
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._on_app_about_to_quit)

        # Восстанавливаем позицию окна
        pos = self.settings.get("window_pos", None)
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])

    def load_settings(self):
        default = {
            "deposit": 1000.0,
            "lang": "ru",
            "risk": 1.0,
            "stop": 1.0,
            "scale": 150,
            "hk_show": "f1",
            "hk_coords": "f2",
            "hk_send": "f3",
            "points": [],
            "prec_dep": 2,
            "prec_risk": 2,
            "prec_fee": 3,
            "prec_vol": 0,
            "prec_lev": 1,
            "prec_min_order": 2,
            "fee_percent": 0.1,
            "fee_taker": 0.05,
            "fee_maker": 0.05,
            "use_fee": True,
            "cas_p_gear": None,
            "cas_p_left_scrollbar": None,
            "cas_p_book": None,
            "cas_p_scrollbar": None,
            "cas_p_vol1": None,
            "cas_p_dist1": None,
            "cas_p_vol2": None,
            "cas_p_dist2": None,
            "cas_p_close_x": None,
            "cas_p_btn_add": None,
            "cas_p_btn_del": None,
            "cas_p_combo_vol": None,
            "cas_use_custom_vol": False,
            "cas_custom_total_vol": 100.0,
            "cas_range_width": 0.0,
            "cas_manual_k": 2.0,
            "last_cascade_count": 1,
            "scalp_cells_count": 4,
            "scalp_multipliers": [100, 50, 25, 10],
            "cells_reversed": False,
            "pos_current_vol": "0",
            "pos_risk": "1",
            "pos_stop": "0",
            "pos_target_cell": 1,
            "pos_mode_enabled": True,
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.settings = json.load(f)
            except:
                self.settings = default
        else:
            self.settings = default
        for key, val in default.items():
            if key not in self.settings:
                self.settings[key] = val

        if "fee_taker" not in self.settings or "fee_maker" not in self.settings:
            fee_total = float(self.settings.get("fee_percent", 0.1))
            self.settings["fee_taker"] = float(
                self.settings.get("fee_taker", fee_total / 2)
            )
            self.settings["fee_maker"] = float(
                self.settings.get("fee_maker", fee_total / 2)
            )
            self.settings["fee_percent"] = (
                self.settings["fee_taker"] + self.settings["fee_maker"]
            )
            self.save_settings()

        # Корректируем масштаб если он выходит за разумные пределы
        scale = self.settings.get("scale", self.base_scale)
        if scale < 80 or scale > 200:
            self.settings["scale"] = self.base_scale
            self.save_settings()

    def save_settings(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.settings, f)

    def toggle_window(self):
        if time.time() - self.last_toggle_time < 0.3:
            return
        self.last_toggle_time = time.time()
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.activateWindow()
            self.raise_()
        else:
            self.showMinimized()

    def open_settings(self):
        if SettingsDialog(self).exec():
            self.apply_styles()
            self.rebind_hotkeys()
            self.apply_min_order_precision()
            self.refresh_labels()
            self.update_calc()
            # Принудительно обновляем объемы в таблице с новой точностью
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()

    def init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("Root")
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(5)

        # --- ЗАГОЛОВОК ---
        # Единая полоска с градиентом и скругленными углами
        header_container = QWidget()
        header_container.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(56, 190, 29, 0.15),
                    stop:1 rgba(56, 190, 29, 0.05));
                border: 1px solid rgba(56, 190, 29, 0.3);
                border-radius: 8px;
            }
        """
        )
        self.header_container = header_container

        header = QHBoxLayout(header_container)
        header.setContentsMargins(10, 5, 10, 5)
        header.setSpacing(10)
        self.header_layout = header

        self.lbl_logo_small = QLabel()
        if os.path.exists(LOGO_PATH):
            pix = QIcon(LOGO_PATH).pixmap(24, 24)
            self.lbl_logo_small.setPixmap(pix)
        self.lbl_logo_small.setStyleSheet("background: transparent; border: none;")

        # ВЕРНУЛИ RiskVolume с улучшенным стилем
        title = QLabel("RiskVolume")
        title.setStyleSheet(
            """
            color: #38BE1D; 
            font-weight: bold; 
            font-style: italic; 
            font-size: 11pt;
            border: none; 
            background: transparent;
        """
        )
        self.title_label = title

        self.btn_set = QPushButton("⚙")
        self.btn_min = QPushButton("_")
        self.btn_close = QPushButton("X")
        self.btn_set.clicked.connect(self.open_settings)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_close.clicked.connect(QApplication.quit)

        for b in [self.btn_set, self.btn_min, self.btn_close]:
            b.setObjectName("HeadBtn")
            b.setFixedSize(22, 22)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 4px;
                    color: #38BE1D;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(56, 190, 29, 0.3);
                }
                QPushButton:pressed {
                    background: rgba(56, 190, 29, 0.5);
                }
            """
            )

        # Делаем кнопку свернуть более жирной
        self.btn_min.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                color: #38BE1D;
                font-weight: 900;
                font-size: 14pt;
            }
            QPushButton:hover {
                background: rgba(56, 190, 29, 0.3);
            }
            QPushButton:pressed {
                background: rgba(56, 190, 29, 0.5);
            }
        """
        )

        # Красный крестик при наведении
        self.btn_close.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                color: #38BE1D;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff3333;
            }
            QPushButton:pressed {
                background: rgba(255, 51, 51, 0.3);
            }
        """
        )

        header.addWidget(self.lbl_logo_small)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.btn_set)
        header.addWidget(self.btn_min)
        header.addWidget(self.btn_close)

        self.main_layout.addWidget(header_container)

        # Добавляем промежуток между заголовком и вкладками
        self.main_layout.addSpacing(10)

        # --- ВКЛАДКИ ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #333; color: #888; padding: 5px 10px; border-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #38BE1D; color: black; font-weight: bold; }
        """
        )

        self.tab_calculator = QWidget()
        self.init_calculator_tab()
        self.tab_calculator.installEventFilter(self)
        self.tabs.addTab(self.tab_calculator, "Калькулятор")

        self.tab_cascade = CascadeTab(self)
        self.tab_cascade.installEventFilter(self)
        self.tabs.addTab(self.tab_cascade, "Каскады (Profit Forge)")
        self.installEventFilter(self)

        self.main_layout.addWidget(self.tabs)

        self.apply_min_order_precision()
        self.refresh_labels()
        self.apply_styles()
        QTimer.singleShot(0, self.finalize_startup_layout)

    def init_calculator_tab(self):
        init_calculator_tab(self)

    def refresh_labels(self):
        lang = self.settings.get("lang", "ru")
        t = TRANS.get(lang, TRANS["ru"])
        self.lbl_dep_title.setText(t["dep"])
        self.lbl_risk_title.setText(t["risk"])
        self.lbl_stop_title.setText(t["stop"])
        self.lbl_vol_title.setText(t["vol"])
        self.tabs.setTabText(0, t.get("tab_calc", "Калькулятор"))
        self.tabs.setTabText(1, t.get("tab_casc", "Каскады"))

    # Метод format_deposit_input удален - депозит не форматируется автоматически

    def apply_min_order_precision(self):
        prec_min_order = int(self.settings.get("prec_min_order", 2))
        if prec_min_order < 0:
            prec_min_order = 0
        if prec_min_order > 6:
            prec_min_order = 6

        if hasattr(self, "inp_min_order"):
            if prec_min_order == 0:
                rx = r"[0-9]*"
            else:
                rx = rf"[0-9]*([.,][0-9]{{0,{prec_min_order}}})?"
            self.inp_min_order.setValidator(
                QRegularExpressionValidator(QRegularExpression(rx))
            )

            try:
                current_val = float(self.inp_min_order.text().replace(",", ".") or 0)
            except Exception:
                current_val = float(self.settings.get("scalp_min_order", 6))

            self.inp_min_order.setText(
                f"{current_val:.{prec_min_order}f}".replace(".", ",")
            )

        if hasattr(self, "tab_cascade") and hasattr(
            self.tab_cascade, "apply_min_order_precision"
        ):
            self.tab_cascade.apply_min_order_precision(prec_min_order)

    def update_calc(self):
        try:
            p_dep = self.settings.get("prec_dep", 2)
            p_risk = self.settings.get("prec_risk", 2)
            p_fee = self.settings.get("prec_fee", 3)
            p_vol = self.settings.get("prec_vol", 0)
            p_lev = self.settings.get("prec_lev", 1)

            d = float(self.inp_dep.text().replace(",", ".") or 0)
            r = float(self.inp_risk.text().replace(",", ".") or 0)
            s = float(self.inp_stop.text().replace(",", ".") or 0)

            fee_taker = self.settings.get("fee_taker", 0.05)
            fee_maker = self.settings.get("fee_maker", 0.05)
            use_fee = self.settings.get("use_fee", True)
            f_perc = (fee_taker + fee_maker) if use_fee else 0.0
            cash_risk, vol, lev, comm_usd = calculate_risk_data(d, r, s, f_perc)

            self.current_vol = vol
            # Форматирование депозита с сокращениями
            hint_text = self.format_with_abbreviations(d, p_dep)
            self.lbl_hint.setText(hint_text)

            vol_str = f"{vol:,.{p_vol}f}".replace(",", " ").replace(".", ",")
            self.lbl_vol.setText(vol_str)

            t = TRANS[self.settings.get("lang", "ru")]
            self.lbl_info.setText(
                get_info_html(cash_risk, lev, comm_usd, t, p_risk, p_fee, p_lev)
            )

            # Обновляем объемы в таблице ячеек
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()

            sc = self.settings.get("scale", 100) / 100.0
            color = "#FF3B30" if r >= 10.0 else "#FF9F0A"
            self.lbl_vol.setStyleSheet(
                f"color: {color}; font-size: 11pt; font-weight: bold; border: 1px solid #333; "
                "border-radius: 4px; padding: 4px; background: #1A1A1A;"
            )

            if hasattr(self, "tab_cascade"):
                self.tab_cascade.recalc_table()

            self.update_position_adjustment_info()

            self.settings.update({"deposit": d, "risk": r, "stop": s})
            self.save_settings()
        except Exception as e:
            print(f"Error: {e}")

    def update_position_adjustment_info(self):
        if not hasattr(self, "lbl_pos_adjust"):
            return

        self.position_target_volume = 0.0
        self.table_volume_override = 0.0

        if not bool(self.settings.get("pos_mode_enabled", True)):
            self.pos_adjust_delta = 0.0
            self.pos_adjust_action = None
            self.lbl_pos_adjust.setText(
                "Рекомендация: режим расчета в позиции выключен"
            )
            self.lbl_pos_adjust.setStyleSheet("color: #555; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText("Риск сделки в $: —")
                self.lbl_pos_risk_cash.setStyleSheet("color: #555; font-size: 7pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        self.pos_adjust_delta = 0.0
        self.pos_adjust_action = None

        p_vol = self.settings.get("prec_vol", 0)

        try:
            pos_vol = float(self.inp_pos_vol.text().replace(",", ".") or 0)
        except Exception:
            pos_vol = 0.0

        if hasattr(self, "lbl_pos_vol_hint"):
            p_vol_hint = int(self.settings.get("prec_vol", 0))
            self.lbl_pos_vol_hint.setText(
                f"Объем в позиции: {self.format_with_abbreviations(pos_vol, p_vol_hint)}"
            )

        try:
            pos_risk = float(self.inp_pos_risk.text().replace(",", ".") or 0)
        except Exception:
            pos_risk = 0.0

        try:
            pos_stop = float(self.inp_pos_stop.text().replace(",", ".") or 0)
        except Exception:
            pos_stop = 0.0

        if pos_risk <= 0:
            self.lbl_pos_adjust.setText("Рекомендация: укажи Риск сделки % > 0")
            self.lbl_pos_adjust.setStyleSheet("color: #888; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText("Риск сделки в $: укажи Риск сделки %")
                self.lbl_pos_risk_cash.setStyleSheet("color: #888; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            self.settings["pos_current_vol"] = self.inp_pos_vol.text()
            self.settings["pos_risk"] = self.inp_pos_risk.text()
            self.settings["pos_stop"] = self.inp_pos_stop.text()
            self.save_settings()
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        risk_cash = pos_vol * (pos_risk / 100.0)
        risk_cash_text = f"{risk_cash:,.2f}".replace(",", " ").replace(".", ",")

        if pos_stop <= 0:
            self.lbl_pos_adjust.setText("Рекомендация: укажи Стоп % > 0")
            self.lbl_pos_adjust.setStyleSheet("color: #888; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(f"Риск сделки в $: {risk_cash_text}")
                self.lbl_pos_risk_cash.setStyleSheet("color: #888; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        fee_taker = self.settings.get("fee_taker", 0.05)
        fee_maker = self.settings.get("fee_maker", 0.05)
        use_fee = self.settings.get("use_fee", True)
        f_perc = (fee_taker + fee_maker) if use_fee else 0.0

        try:
            _, max_vol_at_stop, _, _ = calculate_risk_data(
                pos_vol, pos_risk, pos_stop, f_perc
            )
        except Exception:
            self.lbl_pos_adjust.setText("Рекомендация: ошибка расчета")
            self.lbl_pos_adjust.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(f"Риск сделки в $: {risk_cash_text}")
                self.lbl_pos_risk_cash.setStyleSheet("color: #888; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        self.position_target_volume = float(max_vol_at_stop)
        target_vol_text = f"{max_vol_at_stop:,.{p_vol}f}".replace(",", " ").replace(
            ".", ","
        )

        delta = max_vol_at_stop - pos_vol
        if delta > 0:
            self.pos_adjust_delta = float(delta)
            self.pos_adjust_action = "add"
            delta_text = f"{delta:,.{p_vol}f}".replace(",", " ").replace(".", ",")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    f"Риск сделки в $: {risk_cash_text}   |   Добор: {delta_text}"
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            self.lbl_pos_adjust.setText(f"Целевой объем позиции: {target_vol_text}")
            self.lbl_pos_adjust.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(True)
        elif delta < 0:
            self.pos_adjust_delta = float(abs(delta))
            self.pos_adjust_action = "reduce"
            delta_text = f"{abs(delta):,.{p_vol}f}".replace(",", " ").replace(".", ",")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    f"Риск сделки в $: {risk_cash_text}   |   Сокращение: {delta_text}"
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #FF6B6B; font-size: 8pt;")
            self.lbl_pos_adjust.setText(f"Целевой объем позиции: {target_vol_text}")
            self.lbl_pos_adjust.setStyleSheet("color: #FF6B6B; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(True)
        else:
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    f"Риск сделки в $: {risk_cash_text}   |   Позиция уже в лимите риска"
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            self.lbl_pos_adjust.setText(f"Целевой объем позиции: {target_vol_text}")
            self.lbl_pos_adjust.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)

        self.settings["pos_current_vol"] = self.inp_pos_vol.text()
        self.settings["pos_risk"] = self.inp_pos_risk.text()
        self.settings["pos_stop"] = self.inp_pos_stop.text()
        self.save_settings()

        if hasattr(self, "cells_table"):
            self.update_cell_volumes()

    def select_position_target_cell(self, cell_num):
        if not hasattr(self, "pos_target_cell_buttons"):
            return
        cell_num = max(1, min(5, int(cell_num)))
        for idx, btn in enumerate(self.pos_target_cell_buttons, start=1):
            btn.setChecked(idx == cell_num)
        self.settings["pos_target_cell"] = cell_num
        self.save_settings()

    def _set_position_target_row_mask(self, target_row=None):
        if not hasattr(self, "cells_table") or not hasattr(self, "lbl_cells_count"):
            return

        cells_count = int(self.lbl_cells_count.text())
        default_flags = QTableWidgetItem().flags()

        for i in range(cells_count):
            for col in range(3):
                item = self.cells_table.item(i, col)
                if not item:
                    continue

                if target_row is None:
                    if col in (0, 1):
                        item.setFlags(
                            default_flags
                            & ~Qt.ItemFlag.ItemIsEditable
                            & ~Qt.ItemFlag.ItemIsSelectable
                        )
                    else:
                        item.setFlags(default_flags)
                else:
                    if i == target_row:
                        if col in (0, 1):
                            item.setFlags(
                                default_flags
                                & ~Qt.ItemFlag.ItemIsEditable
                                & ~Qt.ItemFlag.ItemIsSelectable
                            )
                        else:
                            item.setFlags(default_flags)
                    else:
                        item.setFlags(Qt.ItemFlag.NoItemFlags)

    def on_position_mode_toggled(self, checked):
        enabled = bool(checked)
        self.settings["pos_mode_enabled"] = enabled
        if not enabled:
            self.table_volume_override = 0.0
        self.save_settings()

        pos_controls = []
        for name in (
            "inp_pos_vol",
            "inp_pos_risk",
            "inp_pos_stop",
            "btn_move_adjust_to_cell",
        ):
            widget = getattr(self, name, None)
            if widget:
                pos_controls.append(widget)

        for widget in pos_controls:
            widget.setEnabled(enabled)

        if hasattr(self, "pos_target_cell_buttons"):
            for btn in self.pos_target_cell_buttons:
                btn.setEnabled(enabled)
                if not enabled:
                    btn.setChecked(False)

            if enabled:
                selected_cell = int(self.settings.get("pos_target_cell", 1) or 1)
                selected_cell = max(1, min(5, selected_cell))
                for idx, btn in enumerate(self.pos_target_cell_buttons, start=1):
                    btn.setChecked(idx == selected_cell)

        if hasattr(self, "lbl_pos_vol_hint"):
            self.lbl_pos_vol_hint.setStyleSheet(
                "color: #666; font-size: 8pt;"
                if enabled
                else "color: #555; font-size: 8pt;"
            )
        if hasattr(self, "lbl_pos_risk_cash"):
            self.lbl_pos_risk_cash.setStyleSheet(
                "color: #888; font-size: 8pt;"
                if enabled
                else "color: #555; font-size: 8pt;"
            )
        if hasattr(self, "lbl_pos_adjust"):
            self.lbl_pos_adjust.setStyleSheet(
                "color: #888; font-size: 8pt;"
                if enabled
                else "color: #555; font-size: 8pt;"
            )

        self._set_position_target_row_mask(None)
        self.update_position_adjustment_info()

    def apply_position_adjustment_to_cell(self):
        if not bool(self.settings.get("pos_mode_enabled", True)):
            self.lbl_status.setText("Режим позиции выключен")
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            return

        amount = float(getattr(self, "pos_adjust_delta", 0.0) or 0.0)
        if amount <= 0:
            self.lbl_status.setText("Нет суммы для переноса")
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            return

        total_vol = float(self._get_active_table_total_volume() or 0.0)
        if total_vol <= 0:
            self.lbl_status.setText("Сначала получи расчет объема")
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            return

        cells_count = (
            int(self.lbl_cells_count.text()) if hasattr(self, "lbl_cells_count") else 0
        )
        if cells_count <= 0:
            self.lbl_status.setText("Нет активных ячеек")
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            return

        target_percent = max(0, min(100, round((amount / total_vol) * 100)))

        # Переключаемся в ручной режим и записываем сумму в выбранную ячейку
        if hasattr(self, "cb_distribution"):
            self.cb_distribution.setCurrentIndex(2)

        self.table_volume_override = float(amount)

        target_cell = int(self.settings.get("pos_target_cell", 1) or 1)
        target_cell = max(1, min(5, target_cell))

        effective_target = min(target_cell, cells_count)
        is_reversed = bool(self.settings.get("cells_reversed", False))
        if is_reversed:
            target_row = cells_count - effective_target
        else:
            target_row = effective_target - 1

        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except Exception:
            pass

        for i in range(cells_count):
            item = self.cells_table.item(i, 2)
            if not item:
                continue
            item.setText(str(target_percent if i == target_row else 0))

        self.cells_table.itemChanged.connect(self.on_table_item_changed)

        self.update_cell_volumes()
        self._set_position_target_row_mask(target_row)
        self.save_cell_settings()

        action = getattr(self, "pos_adjust_action", None)
        action_text = "добавки" if action == "add" else "сокращения"
        self.lbl_status.setText(
            f"Сумма {action_text} перенесена в Ячейку {effective_target} ({target_percent}%)"
        )
        self.lbl_status.setStyleSheet("color: #38BE1D; font-size: 7pt;")

    def format_with_abbreviations(self, value, precision):
        """Форматирует число с одним сокращением"""
        try:
            # Основное форматированное значение
            main = f"{value:,.{precision}f}".replace(",", " ").replace(".", ",")

            # Одно сокращение
            if value >= 1_000_000_000:
                abbr = f"{value / 1_000_000_000:.1f}млрд"
            elif value >= 1_000_000:
                abbr = f"{value / 1_000_000:.1f}млн"
            elif value >= 1_000:
                abbr = f"{value / 1_000:.0f}к"
            else:
                return main

            return f"{main} / {abbr}"
        except:
            return str(value)

    def apply_styles(self):
        scale = self.settings.get("scale", self.base_scale)
        scale = max(80, min(200, int(scale)))
        ratio = scale / float(self.base_scale)
        base_font = int(11 * (self.base_scale / 100.0))
        f_main = max(8, int(base_font * ratio))
        input_font = max(8, int(9 * ratio))
        f_small = max(7, int(8.5 * ratio))
        pad_main = max(4, int(6 * ratio))
        radius_main = max(4, int(6 * ratio))
        self.central_widget.setStyleSheet(
            f"""
            QWidget#Root {{ background: #121212; border: 2px solid #333; border-radius: {int(12*ratio)}px; }}
            QLineEdit {{ background: #1A1A1A; color: white; border: 1px solid #252525; padding: {pad_main}px; border-radius: {radius_main}px; font-size: {input_font}pt; }}
            QLineEdit:disabled {{ background: #0F0F0F; color: #555; border: 1px solid #222; }}
            QLineEdit:focus {{ border: 1px solid #FFFFFF; }}
            QLineEdit[ghostFocus="true"] {{ border: 1px solid #FFFFFF; }}
            QLabel {{ color: #888; border: none; font-size: {max(6, f_main-2)}pt; }}
            QPushButton#HeadBtn {{ color: #555; border: none; background: transparent; font-size: {f_main}pt; font-weight: bold; }}
            QPushButton#HeadBtn:hover {{ color: #38BE1D; }}
            QPushButton {{ background: #333; color: white; border: 1px solid #444; border-radius: {max(4, int(4*ratio))}px; font-weight: bold; }}
            QPushButton:disabled {{ background: #0F0F0F; color: #555; border: 1px solid #222; }}
            QPushButton:hover {{ background: #444; border-color: #38BE1D; }}
            QPushButton:pressed {{ background: #38BE1D; color: black; }}
            QComboBox, QSpinBox, QDoubleSpinBox {{ background: #1A1A1A; color: white; border: 1px solid #333; padding: {max(2, int(3*ratio))}px; border-radius: {max(4, int(4*ratio))}px; }}
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid #FFFFFF; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #888; width: 0; height: 0; margin-right: 5px; }}
            QComboBox QAbstractItemView {{ background: #1A1A1A; color: white; selection-background-color: #38BE1D; selection-color: black; border: 1px solid #333; }}
            QTableWidget {{ background: #1A1A1A; gridline-color: #333; color: white; border: none; }}
            QHeaderView::section {{ background: #252525; color: #888; border: 1px solid #333; }}
        """
        )
        # Масштабируем размеры элементов равномерно относительно базового масштаба
        if hasattr(self, "main_layout"):
            self.main_layout.setContentsMargins(
                int(8 * ratio), int(8 * ratio), int(8 * ratio), int(8 * ratio)
            )
            self.main_layout.setSpacing(int(4 * ratio))
        if hasattr(self, "header_layout"):
            self.header_layout.setContentsMargins(
                int(10 * ratio), int(5 * ratio), int(10 * ratio), int(5 * ratio)
            )
            self.header_layout.setSpacing(int(10 * ratio))
        if hasattr(self, "header_container"):
            self.header_container.setStyleSheet(
                f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(56, 190, 29, 0.15),
                        stop:1 rgba(56, 190, 29, 0.05));
                    border: 1px solid rgba(56, 190, 29, 0.3);
                    border-radius: {int(8 * ratio)}px;
                }}
            """
            )
        if hasattr(self, "lbl_logo_small") and os.path.exists(LOGO_PATH):
            size = max(12, int(24 * ratio))
            pix = QIcon(LOGO_PATH).pixmap(size, size)
            self.lbl_logo_small.setPixmap(pix)
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(
                f"color: #38BE1D; font-weight: bold; font-style: italic; font-size: {max(8, int(11*ratio))}pt; border: none; background: transparent;"
            )

        btn_size = max(18, int(22 * ratio))
        for b in [self.btn_set, self.btn_min, self.btn_close]:
            b.setFixedSize(btn_size, btn_size)

        input_height = max(int(24 * ratio), int(11 * ratio + 12))
        if hasattr(self, "inp_dep"):
            self.inp_dep.setFixedHeight(input_height)
        if hasattr(self, "inp_risk"):
            self.inp_risk.setFixedHeight(input_height)
        if hasattr(self, "inp_stop"):
            self.inp_stop.setFixedHeight(input_height)
        if hasattr(self, "lbl_vol"):
            self.lbl_vol.setFixedHeight(max(24, int(36 * ratio)))

        if hasattr(self, "cb_distribution"):
            self.cb_distribution.setStyleSheet(
                f"""
                QComboBox {{ background: #1A1A1A; color: white; border: 1px solid #333; padding: {max(2, int(3*ratio))}px; border-radius: {max(4, int(4*ratio))}px; font-size: {f_small}pt; }}
                """
            )
        if hasattr(self, "tabs"):
            tab_pad_v = max(3, int(5 * ratio))
            tab_pad_h = max(6, int(10 * ratio))
            self.tabs.setStyleSheet(
                f"""
                QTabWidget::pane {{ border: none; }}
                QTabBar::tab {{ background: #333; color: #888; padding: {tab_pad_v}px {tab_pad_h}px; border-radius: {max(4, int(4*ratio))}px; margin-right: {max(2, int(2*ratio))}px; }}
                QTabBar::tab:selected {{ background: #38BE1D; color: black; font-weight: bold; }}
                """
            )

        if hasattr(self, "cells_table"):
            self.cells_table.setStyleSheet(
                f"""
                QTableWidget {{
                    background: #1A1A1A;
                    gridline-color: #333;
                    color: white;
                    border: 1px solid #333;
                    border-radius: {max(4, int(4*ratio))}px;
                    show-decoration-selected: 0;
                }}
                QHeaderView::section {{
                    background: #252525;
                    color: #888;
                    border: 1px solid #333;
                    padding: {max(2, int(4*ratio))}px;
                    font-size: {f_small}pt;
                }}
                QTableWidget::item {{
                    padding: {max(3, int(5*ratio))}px;
                    border: none;
                    color: white;
                    background: #1A1A1A;
                    outline: none;
                    font-size: {max(6, int(6*ratio))}pt;
                }}
                QTableWidget::item:focus {{
                    border: none;
                    outline: none;
                }}
                QTableWidget::item:selected {{
                    background: #1A1A1A;
                    border: none;
                }}
                QTableWidget::item:disabled {{
                    color: #555;
                    background: #0F0F0F;
                }}
                QLineEdit {{
                    background: #1A1A1A !important;
                    color: white;
                    border: 1px solid #333 !important;
                    border-radius: {max(4, int(4*ratio))}px;
                    padding: {max(2, int(3*ratio))}px;
                    font-size: {max(8, int(9*ratio))}pt;
                    selection-background-color: rgba(90, 205, 80, 150);
                    selection-color: white;
                }}
            """
            )
            self.update_cells_table_height()

        btn_pad = max(4, int(7 * ratio))
        if hasattr(self, "btn_calib_calc"):
            self.btn_calib_calc.setStyleSheet(
                f"background: #333; color: white; padding: {btn_pad}px;"
            )
        if hasattr(self, "btn_submit"):
            self.btn_submit.setStyleSheet(
                f"background: #38BE1D; color: black; font-weight: bold; padding: {btn_pad}px;"
            )
        if hasattr(self, "chk_pos_mode"):
            self.chk_pos_mode.setStyleSheet(
                f"QCheckBox#PosModeToggle {{ background: #38BE1D; color: black; font-weight: bold; padding: {btn_pad}px; border-radius: {radius_main}px; }}"
            )

        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        # Обновляем масштаб элементов на вкладке каскадов
        if hasattr(self, "tab_cascade"):
            self.tab_cascade.apply_scale()

    # --- УПРАВЛЕНИЕ ГОРЯЧИМИ КЛАВИШАМИ (ИСПРАВЛЕНО) ---
    def rebind_hotkeys(self):
        keyboard.unhook_all()
        # F1 - Скрыть/Показать
        keyboard.add_hotkey(
            self.settings.get("hk_show", "f1"), self.signaler.toggle_sig.emit
        )
        # F2 - Калибровка (в зависимости от активной вкладки)
        keyboard.add_hotkey(
            self.settings.get("hk_coords", "f2"), self.handle_hotkey_calibration
        )
        # F3 - ОТПРАВИТЬ - ОТКЛЮЧЕНО, теперь только через кнопку
        # keyboard.add_hotkey(
        #     self.settings.get("hk_send", "f3"), self.signaler.apply_sig.emit
        # )

    def handle_hotkey_apply(self):
        # Защита от повторного входа (если один и тот же клавишный сигнал пришёл дважды)
        if self.apply_running:
            return
        self.apply_running = True

        try:
            # Если окно свернуто, не реагируем
            if self.isMinimized() or not self.isVisible():
                return

            # ПРОВЕРЯЕМ ПОЗИЦИЮ КУРСОРА - данные отправляются только если курсор НАД окном
            if not self.is_cursor_over_window():
                return

            # ПРОВЕРЯЕМ, КАКАЯ ВКЛАДКА ОТКРЫТА
            current_idx = self.tabs.currentIndex()

            if current_idx == 0:
                # Вкладка калькулятора -> обновляем расчёт и вставляем объем
                self.update_calc()
                self.send_volume_to_terminal()
            elif current_idx == 1:
                # Вкладка каскадов -> выставляем ордера
                self.tab_cascade.run_automation()
        finally:
            self.apply_running = False

    def handle_hotkey_calibration(self):
        if not hasattr(self, "tabs"):
            return

        current_idx = self.tabs.currentIndex()
        if current_idx == 1 and hasattr(self, "tab_cascade"):
            self.tab_cascade.handle_calibration_hotkey()
            return

        self.capture_coords()

    def _cancel_active_calibration(self):
        if hasattr(self, "tab_cascade") and self.tab_cascade.cancel_calibration():
            return True

        if getattr(self, "calc_calibration_active", False):
            self.settings["points"] = []
            self.save_settings()
            self.calc_calibration_active = False
            hk_coords = self.settings.get("hk_coords", "f2").upper()
            self.lbl_status.setText(
                f"Калибровка сброшена. Нажми {hk_coords}, чтобы начать заново"
            )
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            return True

        return False

    # Обработка нажатия Enter на клавиатуре (когда фокус в программе)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._cancel_active_calibration():
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Фильтр событий для обработки колесика мыши на lbl_cells_count"""
        if obj == self.lbl_cells_count and event.type() == event.Type.Wheel:
            delta = event.angleDelta().y()
            if delta > 0:
                self.increase_cells()
            elif delta < 0:
                self.decrease_cells()
            return True
        return super().eventFilter(obj, event)

    def send_volume_to_terminal(self):
        """Отправляет объемы ячеек в терминал"""
        points = self.settings.get("points", [])
        cells_count = int(self.lbl_cells_count.text())
        # Читаем объемы из таблицы (как отображаются пользователю)
        volumes = []
        for i in range(cells_count):
            item = self.cells_table.item(i, 1)
            if item and item.text():
                text = item.text().replace(" ", "").replace(",", ".")
                volumes.append(text)
            else:
                volumes.append("0")

        # Если таблица перевернута, переворачиваем и проценты и точки для соответствия
        is_reversed = self.settings.get("cells_reversed", False)
        if is_reversed:
            volumes.reverse()
            points = list(reversed(points[:cells_count])) + points[cells_count:]

        if len(points) < cells_count or self.current_vol <= 0:
            return

        try:
            old_clip = pyperclip.paste()
            start_x, start_y = pyautogui.position()
            self.showMinimized()
            time.sleep(0.12)

            for i in range(cells_count):
                vol_to_send = volumes[i] if i < len(volumes) else "0"
                pyperclip.copy(vol_to_send)
                pyautogui.moveTo(points[i][0], points[i][1], duration=0.04)
                pyautogui.click()
                time.sleep(0.015)
                pyautogui.click(clicks=2)
                time.sleep(0.015)
                keyboard.press_and_release("ctrl+a")
                time.sleep(0.015)
                keyboard.press_and_release("backspace")
                time.sleep(0.015)
                keyboard.press_and_release("ctrl+v")
                time.sleep(0.015)
                keyboard.press_and_release("enter")
                time.sleep(0.015)
            pyautogui.moveTo(start_x, start_y)
            pyperclip.copy(old_clip)
            # Окно остается свернутым - не разворачиваем автоматически
        except Exception as e:
            print(f"Error: {e}")

    def start_calibration_calc(self):
        """Начинает калибровку - очищает точки и показывает инструкции"""
        cells_count = int(self.lbl_cells_count.text())
        hk_coords = self.settings.get("hk_coords", "f2").upper()

        self.calc_calibration_active = True
        self.settings["points"] = []
        self.save_settings()

        # Показываем подробную инструкцию
        instruction = f"""Калибровка активирована!
        
Нужно захватить {cells_count} ячейку(ек) с объемами в терминале:
        
1. Откройте стакан в терминале
2. Локализируйте поле ввода объема в стакане
3. Нажимайте {hk_coords} последовательно на каждое поле объема
   ({cells_count} раз всего - для каждой ячейки)
4. После захвата всех ячеек статус<br/>   изменится на "готово к работе"
        
Объемы находятся внутри стакана терминала
в правой части экрана."""

        self.lbl_status.setText(instruction)
        self.lbl_status.setStyleSheet(
            "color: #FFD700; font-size: 6pt; line-height: 130%;"
        )
        self.update_calibration_status()

    def capture_coords(self):
        """Захватывает координаты ячеек (ровно столько, сколько нужно)"""
        if not getattr(self, "calc_calibration_active", False):
            self.start_calibration_calc()
            return

        cells_count = int(self.lbl_cells_count.text())
        points = self.settings.get("points", [])

        # Если достаточно точек - очищаем
        if len(points) >= cells_count:
            self.settings["points"] = []
            points = []

        # Если уже есть достаточно - не захватываем дальше
        if len(points) >= cells_count:
            return

        x, y = pyautogui.position()
        self.settings["points"].append([x, y])
        self.save_settings()

        if len(self.settings.get("points", [])) >= cells_count:
            self.calc_calibration_active = False

        self.update_calibration_status()

    def update_calibration_status(self):
        """Обновляет подсказку о калибровке при переключении вкладок"""
        # Обновляем только если мы на вкладке калькулятора
        if hasattr(self, "tabs") and self.tabs.currentIndex() == 0:
            self._update_status_text()

    def _update_status_text(self):
        """Внутренний метод для обновления текста статуса"""
        cells_count = int(self.lbl_cells_count.text())
        points_count = len(self.settings.get("points", []))
        hk_coords = self.settings.get("hk_coords", "f2").upper()

        if points_count == 0:
            if self.calc_calibration_active:
                self.lbl_status.setText(
                    f"⚠ Калибровка активна: нажимай {hk_coords} на полях объема"
                )
                self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            else:
                self.lbl_status.setText("")
        elif points_count < cells_count:
            self.lbl_status.setText(
                f"⚡ Захвачено {points_count} из {cells_count} ячеек"
            )
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
        else:
            self.lbl_status.setText(
                f"✓ Захвачено {cells_count} ячеек (готово к работе)"
            )
            self.lbl_status.setStyleSheet("color: #38BE1D; font-size: 7pt;")

    def increase_cells(self):
        """Увеличивает количество ячеек"""
        current = int(self.lbl_cells_count.text())
        if current < 5:
            current += 1
            self.lbl_cells_count.setText(str(current))
            self.settings["scalp_cells_count"] = current
            self.on_cells_changed()

    def decrease_cells(self):
        """Уменьшает количество ячеек"""
        current = int(self.lbl_cells_count.text())
        if current > 1:
            current -= 1
            self.lbl_cells_count.setText(str(current))
            self.settings["scalp_cells_count"] = current
            self.on_cells_changed()

    def toggle_cells_order(self):
        """Переворачивает порядок ячеек в таблице"""
        cells_count = int(self.lbl_cells_count.text())

        # Собираем текущие проценты
        percentages = []
        for i in range(cells_count):
            item = self.cells_table.item(i, 2)
            if item and item.text():
                try:
                    percentages.append(int(item.text()))
                except:
                    percentages.append(0)
            else:
                percentages.append(0)

        # Переворачиваем порядок
        percentages.reverse()

        # Отключаем сигнал
        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except:
            pass

        # Применяем перевернутые значения
        for i in range(cells_count):
            item = self.cells_table.item(i, 2)
            if item:
                item.setText(str(percentages[i]))

        # Включаем сигнал обратно
        self.cells_table.itemChanged.connect(self.on_table_item_changed)

        # Переключаем флаг
        self.settings["cells_reversed"] = not self.settings.get("cells_reversed", False)

        # Обновляем подписи ячеек
        self.update_cells_labels()

        # Обновляем расчеты и сохраняем
        self.update_cell_volumes()
        self.save_cell_settings()

    def on_cells_changed(self):
        """Обновляет поля ячеек при изменении количества (таблица всегда 5 строк)"""
        cells_count = int(self.lbl_cells_count.text())

        # Отключаем сигнал на время обновления
        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except:
            pass

        # Очищаем таблицу
        self.cells_table.setRowCount(0)

        # Всегда создаем 5 строк
        for i in range(5):
            self.cells_table.insertRow(i)

            is_active = i < cells_count

            # Ячейка с названием (не редактируется, не выделяется)
            label_item = QTableWidgetItem(f"Ячейка {i + 1}")
            label_item.setFlags(
                label_item.flags()
                & ~Qt.ItemFlag.ItemIsEditable
                & ~Qt.ItemFlag.ItemIsSelectable
            )
            label_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not is_active:
                label_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.cells_table.setItem(i, 0, label_item)

            # Ячейка с объемом (не редактируется, не выделяется, рассчитывается)
            volume_item = QTableWidgetItem("0")
            volume_item.setFlags(
                volume_item.flags()
                & ~Qt.ItemFlag.ItemIsEditable
                & ~Qt.ItemFlag.ItemIsSelectable
            )
            volume_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not is_active:
                volume_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.cells_table.setItem(i, 1, volume_item)

            # Ячейка с процентом (редактируется только для активных)
            percent_item = QTableWidgetItem("")
            percent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not is_active:
                percent_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.cells_table.setItem(i, 2, percent_item)

        # Обновляем подписи ячеек с учетом порядка
        self.update_cells_labels()

        # Обновляем высоту таблицы, чтобы всегда были видны 5 строк
        self.update_cells_table_height()

        # Переприменяем текущий тип распределения
        preset_index = self.cb_distribution.currentIndex()
        self._apply_preset_values(preset_index)

        # Загружаем сохраненные значения процентов только для режима "Вручную"
        if preset_index == 2:
            saved_multipliers = self.settings.get(
                "scalp_multipliers", [100, 50, 25, 10, 0]
            )
            is_reversed = self.settings.get("cells_reversed", False)
            if is_reversed:
                saved_multipliers = list(reversed(saved_multipliers))
            for i in range(cells_count):
                if i < len(saved_multipliers) and saved_multipliers[i] > 0:
                    percent_item = self.cells_table.item(i, 2)
                    if percent_item:
                        percent_item.setText(str(saved_multipliers[i]))

        # Подключаем сигнал изменения
        self.cells_table.itemChanged.connect(self.on_table_item_changed)

        self.update_cell_volumes()
        self.save_cell_settings()
        self._update_status_text()

    def update_cells_labels(self):
        if not hasattr(self, "cells_table"):
            return

        cells_count = int(self.lbl_cells_count.text())
        is_reversed = self.settings.get("cells_reversed", False)

        active_labels = list(range(1, cells_count + 1))
        if is_reversed:
            active_labels.reverse()

        for i in range(5):
            label_item = self.cells_table.item(i, 0)
            if not label_item:
                continue

            if i < cells_count:
                label_item.setText(f"Ячейка {active_labels[i]}")
            else:
                label_item.setText(f"Ячейка {i + 1}")

    def update_cells_table_height(self):
        if not hasattr(self, "cells_table"):
            return

        # Отключаем скроллбар
        self.cells_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.cells_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Рассчитываем высоту строки по реальному sizeHint
        row_height = 0
        for i in range(self.cells_table.rowCount()):
            row_height = max(row_height, self.cells_table.sizeHintForRow(i))

        # Fallback, если sizeHint еще не готов
        if row_height <= 0:
            scale = self.settings.get("scale", self.base_scale)
            ratio = scale / self.base_scale if self.base_scale else 1.0
            row_height = max(20, int(28 * ratio))

        # Фиксируем высоту строк, чтобы 5 строк всегда были видны
        for i in range(self.cells_table.rowCount()):
            self.cells_table.setRowHeight(i, row_height)

        header = self.cells_table.horizontalHeader()
        header_height = max(header.height(), header.sizeHint().height())
        table_height = (
            header_height + (row_height * 5) + (self.cells_table.frameWidth() * 2)
        )
        self.cells_table.setFixedHeight(table_height)

        if self.isVisible():
            self.adjustSize()
            self.setFixedSize(self.sizeHint())

    def on_table_item_clicked(self, item):
        """Обработчик клика по ячейке - снимает фокус с колонок 0 и 1"""
        self._clear_ghost_focus()
        if item and item.column() in [0, 1]:
            # Если кликнули на колонку 0 или 1, сразу снимаем выделение
            self.cells_table.clearSelection()
            self.cells_table.setCurrentItem(None)

    def on_table_item_changed(self, item):
        """Вызывается когда изменяется ячейка таблицы"""
        if item.column() == 2:  # Только для колонки с процентами
            # Проверяем что введено число
            text = item.text().strip()
            if text and not text.isdigit():
                item.setText("0")

            self.update_cell_volumes()
            self.save_cell_settings()

    def finalize_startup_layout(self):
        self.update_cells_table_height()
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def _apply_preset_values(self, preset_index):
        """Применяет значения выбранного пресета"""
        cells_count = int(self.lbl_cells_count.text())

        if preset_index == 2:  # Вручную
            return

        presets = {
            0: "equal",  # Равномерно
            1: "decreasing",  # Убывающая: 100, 75, 50, 25, 10
        }

        preset = presets.get(preset_index, "equal")
        values = []

        if preset == "equal":
            # Равномерное распределение
            equal_percent = int(100 / cells_count)
            remainder = 100 % cells_count
            for i in range(cells_count):
                value = equal_percent
                if i < remainder:
                    value += 1
                values.append(value)
        elif preset == "decreasing":
            values = [100, 75, 50, 25, 10][:cells_count]

        is_reversed = self.settings.get("cells_reversed", False)
        if is_reversed:
            values.reverse()

        # Применяем значения
        for i in range(cells_count):
            item = self.cells_table.item(i, 2)
            if item:
                item.setText(str(values[i]))

    def apply_distribution_preset(self):
        """Применяет выбранную предустановку распределения"""
        preset_index = self.cb_distribution.currentIndex()

        # Отключаем сигнал чтобы не вызывать сохранение много раз
        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except:
            pass

        # Применяем значения пресета
        self._apply_preset_values(preset_index)

        # Включаем сигнал обратно
        self.cells_table.itemChanged.connect(self.on_table_item_changed)

        # Сохраняем выбранный тип
        self.settings["scalp_distribution_type"] = preset_index
        self.update_cell_volumes()
        self.save_cell_settings()

    def _get_active_table_total_volume(self):
        override = float(getattr(self, "table_volume_override", 0.0) or 0.0)
        if override > 0:
            return override

        if bool(self.settings.get("pos_mode_enabled", True)):
            target = float(getattr(self, "position_target_volume", 0.0) or 0.0)
            if target > 0:
                return target
        return float(getattr(self, "current_vol", 0.0) or 0.0)

    def update_cell_volumes(self):
        """Обновляет объемы в каждой ячейке на основе процентов и минимума"""
        cells_count = int(self.lbl_cells_count.text())
        total_vol = self._get_active_table_total_volume()
        p_vol = self.settings.get(
            "prec_vol", 0
        )  # Используем ту же точность что и для основного объема

        try:
            min_order = float(self.inp_min_order.text().replace(",", ".") or 6)
        except:
            min_order = 6

        for i in range(5):
            volume_item = self.cells_table.item(i, 1)
            percent_item = self.cells_table.item(i, 2)

            if i < cells_count and percent_item:
                try:
                    percent = float(percent_item.text() or 0)
                    volume = max(
                        min_order, (total_vol * percent) / 100.0
                    )  # Не меньше минимума
                    # Форматируем с той же точностью что и основной объем
                    volume_item.setText(
                        f"{volume:,.{p_vol}f}".replace(",", " ").replace(".", ",")
                    )
                except:
                    volume_item.setText("0")
            else:
                volume_item.setText("")

            # Сохраняем минимум в настройки
            self.settings["scalp_min_order"] = min_order

    def on_min_order_changed(self):
        """Вызывается при нажатии Enter в поле минимального ордера"""
        self.update_cell_volumes()
        self.inp_min_order.deselect()
        self.inp_min_order.clearFocus()
        self.save_settings()

    def _commit_input(self):
        sender = self.sender()
        if isinstance(sender, QLineEdit):
            self._clear_ghost_focus()
            sender.deselect()
            sender.clearFocus()

    def _clear_ghost_focus(self, except_obj=None):
        ghost = self._ghost_input
        if ghost and ghost is not except_obj:
            ghost.setProperty("ghostFocus", "false")
            ghost.style().polish(ghost)
            ghost.update()
            ghost.setProperty("click_count", 0)
            ghost.setProperty("last_click_ms", 0)
            ghost.setProperty("await_third_click", False)
            self._ghost_input = None

    def save_cell_settings(self):
        """Сохраняет настройки ячеек"""
        cells_count = int(self.lbl_cells_count.text())
        multipliers = []

        for i in range(5):  # Сохраняем все 5 значений
            item = self.cells_table.item(i, 2)  # Колонка с процентами
            if item:
                val = item.text().strip()
                try:
                    mult = int(val) if val else 0
                except:
                    mult = 0
                multipliers.append(mult)

        # Сохраняем мин.ордер
        try:
            min_order = float(self.inp_min_order.text().replace(",", ".") or 6)
        except:
            min_order = 6

        # Если таблица перевернута, сохраняем multipliers в обратном порядке для корректного отображения
        is_reversed = self.settings.get("cells_reversed", False)
        if is_reversed:
            multipliers.reverse()

        self.settings["scalp_cells_count"] = cells_count
        self.settings["scalp_multipliers"] = multipliers
        self.settings["scalp_min_order"] = min_order
        self.settings["cells_reversed"] = is_reversed
        self.save_settings()

    def is_cursor_over_window(self):
        """Проверяет находится ли курсор мыши над окном приложения"""
        cursor_pos = pyautogui.position()
        win_geom = self.geometry()

        return (
            win_geom.x() <= cursor_pos[0] <= win_geom.x() + win_geom.width()
            and win_geom.y() <= cursor_pos[1] <= win_geom.y() + win_geom.height()
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            pos = e.globalPosition().toPoint()
            self._clear_ghost_focus()

            # На вкладках калькулятора и каскадов - разрешаем везде кроме интерактивных элементов
            if hasattr(self, "tabs") and self.tabs.currentIndex() in (0, 1):
                # Проверяем что клик не попал на интерактивный элемент
                widget = self.childAt(self.mapFromGlobal(pos))

                # Разрешаем перетаскивание если клик не на таких элементах
                non_draggable_types = (
                    QLineEdit,
                    QPushButton,
                    QComboBox,
                    QTableWidget,
                    QSpinBox,
                    QDoubleSpinBox,
                )

                if not widget or not isinstance(widget, non_draggable_types):
                    # Клик в пустое место - очищаем ghost focus
                    self.old_pos = pos
                else:
                    self.old_pos = None
            # На других вкладках - только по верхней полосе
            elif pos.y() < 30:
                self.old_pos = pos
            else:
                self.old_pos = None

    def mouseMoveEvent(self, e):
        if self.old_pos:
            delta = e.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

    def eventFilter(self, obj, event):
        """Перехватывает события мыши на вкладках для перетаскивания"""
        if event.type() == event.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            if self._cancel_active_calibration():
                return True

        if isinstance(obj, QLineEdit):
            if event.type() == event.Type.MouseButtonPress:
                now_ms = int(time.time() * 1000)
                last_ms = obj.property("last_click_ms") or 0
                click_count = obj.property("click_count") or 0
                await_third = obj.property("await_third_click") or False

                if await_third and now_ms - last_ms <= 650:
                    obj.setProperty("await_third_click", False)
                    obj.setProperty("click_count", 0)
                    self._clear_ghost_focus()
                    obj.setFocus()
                    obj.deselect()
                    QTimer.singleShot(
                        0, lambda o=obj: o.setCursorPosition(len(o.text()))
                    )
                    return True

                if now_ms - last_ms <= 450:
                    click_count += 1
                else:
                    click_count = 1
                obj.setProperty("last_click_ms", now_ms)
                obj.setProperty("click_count", click_count)

                if click_count == 1 and not obj.hasFocus():
                    self._clear_ghost_focus()
                    obj.setProperty("ghostFocus", "true")
                    self._ghost_input = obj
                    obj.style().polish(obj)
                    obj.update()
                    QTimer.singleShot(0, obj.clearFocus)
                    return True
                if click_count == 1 and obj.hasFocus():
                    self._clear_ghost_focus()
                    obj.setProperty("ghostFocus", "true")
                    self._ghost_input = obj
                    obj.style().polish(obj)
                    obj.update()
                    QTimer.singleShot(0, lambda: (obj.clearFocus(), obj.deselect()))
                    return True
                if click_count == 2:
                    self._clear_ghost_focus()
                    obj.setProperty("await_third_click", True)
                    obj.setProperty("last_click_ms", now_ms)
                    obj.setFocus()
                    QTimer.singleShot(0, obj.selectAll)
                    return True
            elif event.type() == event.Type.MouseButtonDblClick:
                self._clear_ghost_focus()
                obj.setProperty("await_third_click", True)
                obj.setProperty("last_click_ms", int(time.time() * 1000))
                obj.setProperty("click_count", 2)
                obj.setFocus()
                QTimer.singleShot(0, obj.selectAll)
            elif event.type() == event.Type.KeyPress:
                if event.key() in (
                    Qt.Key.Key_Escape,
                    Qt.Key.Key_Return,
                    Qt.Key.Key_Enter,
                ):
                    self._clear_ghost_focus()
                    obj.deselect()
                    obj.clearFocus()
                    return True
        if event.type() == event.Type.WindowDeactivate:
            self._clear_ghost_focus()
        if isinstance(obj, QComboBox):
            if event.type() == event.Type.KeyPress:
                if event.key() in (
                    Qt.Key.Key_Escape,
                    Qt.Key.Key_Return,
                    Qt.Key.Key_Enter,
                ):
                    obj.hidePopup()
                    obj.clearFocus()
                    return True
        if (
            hasattr(self, "tab_calculator")
            and hasattr(self, "tab_cascade")
            and obj in (self.tab_calculator, self.tab_cascade)
            and event.type() == event.Type.MouseButtonPress
        ):
            self._clear_ghost_focus()
            if event.button() == Qt.MouseButton.LeftButton:
                local_pos = event.position().toPoint()
                widget = obj.childAt(local_pos)
                non_draggable_types = (
                    QLineEdit,
                    QPushButton,
                    QComboBox,
                    QTableWidget,
                    QSpinBox,
                    QDoubleSpinBox,
                )
                if not widget or not isinstance(widget, non_draggable_types):
                    self.old_pos = event.globalPosition().toPoint()
                    return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """Сохраняет позицию окна при закрытии"""
        self.settings["window_pos"] = [self.x(), self.y()]
        self.save_settings()
        event.accept()

    def _on_app_about_to_quit(self):
        """Сохраняет настройки при завершении приложения"""
        try:
            self.settings["window_pos"] = [self.x(), self.y()]
            self.save_settings()
        except Exception:
            pass


if __name__ == "__main__":
    # Защита от множественного запуска
    shared_memory = QSharedMemory("RiskVolume_single_instance_v1")
    if not shared_memory.create(1):
        # Пытаемся очистить "зависший" сегмент и выходим, если уже запущено
        if shared_memory.attach():
            shared_memory.detach()
        if not shared_memory.create(1):
            sys.exit(0)

    app = QApplication(sys.argv)
    win = RiskVolumeApp()
    win.show()
    sys.exit(app.exec())
