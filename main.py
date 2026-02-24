import sys, json, os, ctypes, time, threading, keyboard, pyautogui, pyperclip
import config
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
    QStyledItemDelegate,
    QStyleOptionViewItem,
)
from PyQt6.QtCore import (
    Qt,
    QRegularExpression,
    QTimer,
    pyqtSignal,
    QObject,
    QSharedMemory,
)
from PyQt6.QtGui import QIcon, QRegularExpressionValidator, QColor, QBrush, QPalette

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


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Глобальный обработчик исключений — не даёт приложению упасть тихо."""
    import traceback

    try:
        traceback.print_exception(exc_type, exc_value, exc_tb)
    except Exception:
        pass


def _thread_exception_handler(args):
    """Обработчик исключений в потоках (keyboard хуки и т.д.)."""
    import traceback

    try:
        traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
    except Exception:
        pass


sys.excepthook = _global_exception_handler
threading.excepthook = _thread_exception_handler


class HotkeySignaler(QObject):
    toggle_sig = pyqtSignal()
    apply_sig = pyqtSignal()  # Новый сигнал для применения


class CellsLabelDarkDelegate(QStyledItemDelegate):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

    def paint(self, painter, option, index):
        if index.column() == 0:
            try:
                selected_rows = set(self.app._get_active_rows_for_table())
            except Exception:
                selected_rows = set()

            if index.row() not in selected_rows:
                bg = QColor("#000000")
                fg = QColor("#161616")
                painter.save()
                painter.fillRect(option.rect, bg)
                painter.setPen(fg)
                text = index.data(Qt.ItemDataRole.DisplayRole)
                if text:
                    painter.drawText(
                        option.rect, Qt.AlignmentFlag.AlignCenter, str(text)
                    )
                painter.restore()
                return

        super().paint(painter, option, index)


class RiskVolumeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_scale = 130
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
        self.table_volume_override = float(
            self.settings.get("pos_table_volume_override", 0.0) or 0.0
        )
        self.selected_transfer_rows = set(
            int(i) for i in self.settings.get("selected_cells", []) if str(i).isdigit()
        )
        self.position_target_row_active = None
        self._cells_count_before_target_mode = None
        self._ghost_input = None
        self.calc_calibration_active = False

        self.init_ui()
        self._calc_update_timer = QTimer(self)
        self._calc_update_timer.setSingleShot(True)
        self._calc_update_timer.timeout.connect(self.update_calc)
        self._min_order_live_timer = QTimer(self)
        self._min_order_live_timer.setSingleShot(True)
        self._min_order_live_timer.timeout.connect(self._apply_min_order_live)
        self.rebind_hotkeys()
        self.update_calc()

        # Периодически перерегистрируем keyboard-хуки (Windows убивает их при простое/сне)
        self._hotkey_keepalive_timer = QTimer(self)
        self._hotkey_keepalive_timer.timeout.connect(self._keepalive_hotkeys)
        self._hotkey_keepalive_timer.start(5 * 60 * 1000)  # каждые 5 минут

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
            "scale": 130,
            "hk_show": "f1",
            "hk_coords": "f2",
            "hk_send": "f3",
            "points": [],
            "prec_dep": 2,
            "prec_risk": 2,
            "prec_fee": 3,
            "prec_vol": 0,
            "prec_lev": 1,
            "prec_min_order": 0,
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
            "cas_use_custom_percent": False,
            "cas_custom_percent": 100.0,
            "cas_max_count_enabled": False,
            "cas_max_count": 0,
            "cas_type_index": 0,
            "cas_dist_step": 0.1,
            "cas_range_mode": False,
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
            "pos_mode_enabled": False,
            "pos_table_volume_override": 0.0,
            "selected_cells": [0],
            "minimize_after_apply": True,
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

        self.settings["prec_min_order"] = 0

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
        if scale < 130 or scale > 200:
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
            # Настройки уже применяются внутри save_and_close() диалога.
            # Здесь только мягко синхронизируем расчеты/таблицу.
            self.schedule_update_calc()
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

        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        self.tab_calculator = QWidget()
        self.init_calculator_tab()
        self.tab_calculator.installEventFilter(self)
        self.tabs.addTab(self.tab_calculator, t.get("tab_calc", "Калькулятор"))

        self.tab_cascade = CascadeTab(self)
        self.tab_cascade.installEventFilter(self)
        self.tabs.addTab(self.tab_cascade, t.get("tab_casc", "Каскады"))
        self.installEventFilter(self)

        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.main_layout.addWidget(self.tabs)

        self.apply_min_order_precision()
        self.refresh_labels()
        self.apply_styles()
        QTimer.singleShot(0, self.finalize_startup_layout)

    def on_tab_changed(self, index):
        if index == 1 and hasattr(self, "tab_cascade"):
            self.tab_cascade.recalc_table()

    def init_calculator_tab(self):
        init_calculator_tab(self)
        if hasattr(self, "cells_table"):
            self.cells_table.setItemDelegateForColumn(
                0, CellsLabelDarkDelegate(self, self.cells_table)
            )

    def refresh_labels(self):
        lang = self.settings.get("lang", "ru")
        t = TRANS.get(lang, TRANS["ru"])
        self.lbl_dep_title.setText(t["dep"])
        self.lbl_risk_title.setText(t["risk"])
        self.lbl_stop_title.setText(t["stop"])
        self.lbl_vol_title.setText(t["vol"])
        self.tabs.setTabText(0, t.get("tab_calc", "Калькулятор"))
        self.tabs.setTabText(1, t.get("tab_casc", "Каскады"))
        self.refresh_calculator_labels()
        if hasattr(self, "tab_cascade"):
            self.tab_cascade.refresh_labels()

    def refresh_calculator_labels(self):
        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        if hasattr(self, "chk_pos_mode"):
            self.chk_pos_mode.setText(t["calc_pos_mode"])
        if hasattr(self, "lbl_pos_vol_title"):
            self.lbl_pos_vol_title.setText(t["calc_in_position"])
        if hasattr(self, "lbl_pos_risk_title"):
            self.lbl_pos_risk_title.setText(t["calc_risk_percent"])
        if hasattr(self, "lbl_pos_stop_title"):
            self.lbl_pos_stop_title.setText(t["calc_stop_percent"])
        if hasattr(self, "lbl_pos_adjust"):
            self.lbl_pos_adjust.setText(t["calc_recommendation"])
        if hasattr(self, "btn_reverse_cells"):
            self.btn_reverse_cells.setToolTip(t["calc_reverse_cells"])
        if hasattr(self, "btn_move_adjust_to_cell"):
            self.btn_move_adjust_to_cell.setToolTip(t["calc_move_adjust"])
        if hasattr(self, "btn_toggle_all_cells"):
            self.btn_toggle_all_cells.setText(t["calc_toggle_all_btn"])
            self.btn_toggle_all_cells.setToolTip(t["calc_toggle_all"])
        if hasattr(self, "lbl_min_order_title"):
            self.lbl_min_order_title.setText(t["calc_min_order"])
        if hasattr(self, "lbl_calc_type_title"):
            self.lbl_calc_type_title.setText(t["calc_type"])
        if hasattr(self, "cb_distribution"):
            current_idx = self.cb_distribution.currentIndex()
            self.cb_distribution.blockSignals(True)
            self.cb_distribution.clear()
            self.cb_distribution.addItems(
                [
                    t["calc_dist_uniform"],
                    t["calc_dist_desc"],
                    t["calc_dist_manual"],
                ]
            )
            self.cb_distribution.setCurrentIndex(max(0, current_idx))
            self.cb_distribution.blockSignals(False)
        if hasattr(self, "cells_table"):
            self.cells_table.setHorizontalHeaderLabels(
                [
                    t["calc_table_cells"],
                    t["calc_table_volumes"],
                    t["calc_table_percent"],
                ]
            )
            self.update_cells_labels()
        if hasattr(self, "btn_submit"):
            self.btn_submit.setText(t["calc_apply"])
        self.update_position_adjustment_info()
        self.update_calibration_status()

    # Метод format_deposit_input удален - депозит не форматируется автоматически

    def apply_min_order_precision(self):
        prec_min_order = 0

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

            self.inp_min_order.setText(str(int(round(current_val))))

        if hasattr(self, "tab_cascade") and hasattr(
            self.tab_cascade, "apply_min_order_precision"
        ):
            self.tab_cascade.apply_min_order_precision(prec_min_order)

    def update_calc(self):
        try:
            p_dep = self.settings.get("prec_dep", 2)
            p_risk = self.settings.get("prec_risk", 2)
            p_fee = self.settings.get("prec_fee", 3)
            p_vol = self.settings.get("prec_dep", 2)
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
            hint_text = self.format_hint_no_decimals(d)
            self.lbl_hint.setText(hint_text)

            vol_str = f"{vol:,.{p_vol}f}".replace(",", " ").replace(".", ",")
            self.lbl_vol.setText(vol_str)

            t = TRANS[self.settings.get("lang", "ru")]
            dimmed = self.settings.get("pos_mode_enabled", False)
            self.lbl_info.setText(
                get_info_html(
                    cash_risk,
                    lev,
                    comm_usd,
                    t,
                    p_risk,
                    p_fee,
                    p_lev,
                    dimmed=dimmed,
                )
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

            if (
                hasattr(self, "tab_cascade")
                and hasattr(self, "tabs")
                and self.tabs.currentIndex() == 1
            ):
                self.tab_cascade.recalc_table()

            self.update_position_adjustment_info()
            self._adapt_window_width_to_content()

            self.settings.update({"deposit": d, "risk": r, "stop": s})
            self.save_settings()
        except Exception as e:
            print(f"Error: {e}")

    def schedule_update_calc(self):
        if hasattr(self, "_calc_update_timer"):
            self._calc_update_timer.start(40)
        else:
            self.update_calc()

    def update_position_adjustment_info(self):
        if not hasattr(self, "lbl_pos_adjust"):
            return

        self.position_target_volume = 0.0

        if not bool(self.settings.get("pos_mode_enabled", False)):
            self.table_volume_override = 0.0
            self.pos_adjust_delta = 0.0
            self.pos_adjust_action = None
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t["pos_mode_off"])
            self.lbl_pos_adjust.setStyleSheet("color: #555; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_na"])
                self.lbl_pos_risk_cash.setStyleSheet("color: #555; font-size: 7pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        self.pos_adjust_delta = 0.0
        self.pos_adjust_action = None

        p_vol = self.settings.get("prec_dep", 2)
        p_risk = self.settings.get("prec_risk", 2)

        try:
            pos_vol = float(self.inp_pos_vol.text().replace(",", ".") or 0)
        except Exception:
            pos_vol = 0.0

        if hasattr(self, "lbl_pos_vol_hint"):
            self.lbl_pos_vol_hint.setText(self.format_hint_no_decimals(pos_vol))

        try:
            pos_risk = float(self.inp_pos_risk.text().replace(",", ".") or 0)
        except Exception:
            pos_risk = 0.0

        try:
            pos_stop = float(self.inp_pos_stop.text().replace(",", ".") or 0)
        except Exception:
            pos_stop = 0.0

        if pos_risk <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t["pos_rec_risk"])
            self.lbl_pos_adjust.setStyleSheet("color: #888; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_need"])
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

        # Риск в $ считаем от ДЕПОЗИТА
        try:
            deposit_for_risk = float(self.inp_dep.text().replace(",", ".") or 0)
        except Exception:
            deposit_for_risk = 0.0

        risk_cash = (
            deposit_for_risk * (pos_risk / 100.0)
            if deposit_for_risk > 0
            else pos_vol * (pos_risk / 100.0)
        )
        risk_cash_text = f"{risk_cash:,.{p_risk}f}".replace(",", " ").replace(".", ",")

        if pos_stop <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t["pos_rec_stop"])
            self.lbl_pos_adjust.setStyleSheet("color: #888; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_pos_risk_cash.setText(
                    t["pos_risk_cash"].format(risk_cash=risk_cash_text)
                )
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

        # Берём депозит из основного поля калькулятора
        try:
            deposit = float(self.inp_dep.text().replace(",", ".") or 0)
        except Exception:
            deposit = 0.0

        if deposit <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t.get("pos_need_deposit", "Укажите депозит"))
            self.lbl_pos_adjust.setStyleSheet("color: #888; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    t["pos_risk_cash"].format(risk_cash=risk_cash_text)
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #888; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        # Целевой объём считаем от ДЕПОЗИТА, а не от текущего объёма позиции
        try:
            _, max_vol_at_stop, _, _ = calculate_risk_data(
                deposit, pos_risk, pos_stop, f_perc
            )
        except Exception:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t["pos_calc_error"])
            self.lbl_pos_adjust.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            if hasattr(self, "lbl_pos_risk_cash"):
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_pos_risk_cash.setText(
                    t["pos_risk_cash"].format(risk_cash=risk_cash_text)
                )
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
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_pos_risk_cash.setText(
                    t["pos_add"].format(risk_cash=risk_cash_text, delta=delta_text)
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(
                t["pos_target_vol"].format(target=target_vol_text)
            )
            self.lbl_pos_adjust.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(True)
        elif delta < 0:
            self.pos_adjust_delta = float(abs(delta))
            self.pos_adjust_action = "reduce"
            delta_text = f"{abs(delta):,.{p_vol}f}".replace(",", " ").replace(".", ",")
            if hasattr(self, "lbl_pos_risk_cash"):
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_pos_risk_cash.setText(
                    t["pos_reduce"].format(risk_cash=risk_cash_text, delta=delta_text)
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #FF6B6B; font-size: 8pt;")
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(
                t["pos_target_vol"].format(target=target_vol_text)
            )
            self.lbl_pos_adjust.setStyleSheet("color: #FF6B6B; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(True)
        else:
            if hasattr(self, "lbl_pos_risk_cash"):
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_pos_risk_cash.setText(
                    t["pos_in_limit"].format(risk_cash=risk_cash_text)
                )
                self.lbl_pos_risk_cash.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(
                t["pos_target_vol"].format(target=target_vol_text)
            )
            self.lbl_pos_adjust.setStyleSheet("color: #38BE1D; font-size: 8pt;")
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)

        self.settings["pos_current_vol"] = self.inp_pos_vol.text()
        self.settings["pos_risk"] = self.inp_pos_risk.text()
        self.settings["pos_stop"] = self.inp_pos_stop.text()
        self.save_settings()

        if hasattr(self, "cells_table"):
            self.update_cell_volumes()

        self._adapt_window_width_to_content()

    def select_position_target_cell(self, cell_num):
        if not hasattr(self, "pos_target_cell_buttons"):
            return
        cell_num = max(1, min(5, int(cell_num)))
        for idx, btn in enumerate(self.pos_target_cell_buttons, start=1):
            btn.setChecked(idx == cell_num)
        self.settings["pos_target_cell"] = cell_num
        self.save_settings()

    def _set_position_target_row_mask(self, target_row=None, lock_controls=True):
        if not hasattr(self, "cells_table") or not hasattr(self, "lbl_cells_count"):
            return

        try:
            cells_count = int(
                self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
            )
        except Exception:
            cells_count = int(self.lbl_cells_count.text())

        if target_row is None:
            self.position_target_row_active = None
            if self._cells_count_before_target_mode is not None and hasattr(
                self, "lbl_cells_count"
            ):
                self.lbl_cells_count.setText(str(self._cells_count_before_target_mode))
            self._cells_count_before_target_mode = None
            if lock_controls:
                if hasattr(self, "btn_cells_minus"):
                    self.btn_cells_minus.setEnabled(True)
                if hasattr(self, "btn_cells_plus"):
                    self.btn_cells_plus.setEnabled(True)
                if hasattr(self, "btn_reverse_cells"):
                    self.btn_reverse_cells.setEnabled(True)
        else:
            self.position_target_row_active = int(target_row)
            if self._cells_count_before_target_mode is None:
                try:
                    self._cells_count_before_target_mode = int(
                        self.lbl_cells_count.text()
                    )
                except Exception:
                    self._cells_count_before_target_mode = cells_count
            if lock_controls:
                if hasattr(self, "lbl_cells_count"):
                    self.lbl_cells_count.setText("1")
                if hasattr(self, "btn_cells_minus"):
                    self.btn_cells_minus.setEnabled(False)
                if hasattr(self, "btn_cells_plus"):
                    self.btn_cells_plus.setEnabled(False)
                if hasattr(self, "btn_reverse_cells"):
                    self.btn_reverse_cells.setEnabled(False)

        mask_rows_count = 5 if target_row is not None else cells_count

        default_flags = QTableWidgetItem().flags()

        for i in range(mask_rows_count):
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

    def _dim_top_controls(self, dim):
        """Затемняет или освещает верхние элементы (риск, стоп, объем) — депозит всегда активен"""
        elements = [
            ("inp_risk", True),
            ("inp_stop", True),
            ("lbl_vol", False),
            ("lbl_risk_title", False),
            ("lbl_stop_title", False),
            ("lbl_hint", False),
            ("lbl_info", False),
            ("lbl_vol_title", False),
        ]

        for name, is_input in elements:
            widget = getattr(self, name, None)
            if widget:
                if isinstance(widget, QLineEdit):
                    if dim:
                        widget.setEnabled(False)
                        widget.setStyleSheet(
                            "QLineEdit:disabled { background: #0F0F0F; color: #333; border: 1px solid #222; }"
                        )
                    else:
                        widget.setEnabled(True)
                        widget.setStyleSheet(
                            "QLineEdit { background: #1A1A1A; color: white; border: 1px solid #252525; padding: 3px; border-radius: 4px; font-size: 9pt; }"
                        )
                elif isinstance(widget, QLabel):
                    if dim:
                        current_style = widget.styleSheet()
                        import re

                        new_style = re.sub(
                            r"color:\s*#[0-9A-Fa-f]{3,6}",
                            "color: #555",
                            current_style,
                        )
                        widget.setStyleSheet(new_style)
                    else:
                        current_style = widget.styleSheet()
                        # Восстанавливаем оригинальные цвета
                        if (
                            name == "lbl_dep_title"
                            or name == "lbl_risk_title"
                            or name == "lbl_stop_title"
                        ):
                            import re

                            new_style = re.sub(
                                r"color:\s*#[0-9A-Fa-f]{3,6}",
                                "color: #888",
                                current_style,
                            )
                            widget.setStyleSheet(new_style)
                        elif name == "lbl_vol_title":
                            import re

                            new_style = re.sub(
                                r"color:\s*#[0-9A-Fa-f]{3,6}",
                                "color: #888",
                                current_style,
                            )
                            widget.setStyleSheet(new_style)
                        elif name == "lbl_hint":
                            import re

                            new_style = re.sub(
                                r"color:\s*#[0-9A-Fa-f]{3,6}",
                                "color: #666",
                                current_style,
                            )
                            widget.setStyleSheet(new_style)
                        elif name == "lbl_info":
                            import re

                            new_style = re.sub(
                                r"color:\s*#[0-9A-Fa-f]{3,6}",
                                "color: #888",
                                current_style,
                            )
                            widget.setStyleSheet(new_style)
                        elif name == "lbl_vol":
                            import re

                            new_style = re.sub(
                                r"color:\s*#[0-9A-Fa-f]{3,6}",
                                "color: #FF9F0A",
                                current_style,
                            )
                            widget.setStyleSheet(new_style)

    def on_position_mode_toggled(self, checked, is_startup=False):
        enabled = bool(checked)
        self.settings["pos_mode_enabled"] = enabled

        # Сохраняем текущий размер окна перед изменениями
        if not is_startup:
            current_size = self.size()

        pos_controls = []
        for name in (
            "inp_pos_vol",
            "inp_pos_risk",
            "inp_pos_stop",
            "lbl_pos_vol_title",
            "lbl_pos_risk_title",
            "lbl_pos_stop_title",
            "btn_move_adjust_to_cell",
            "lbl_pos_vol_hint",
            "lbl_pos_risk_cash",
            "lbl_pos_adjust",
        ):
            widget = getattr(self, name, None)
            if widget:
                pos_controls.append(widget)

        if enabled and not is_startup:
            # User enabled position mode - switch to manual distribution and apply transfer
            if hasattr(self, "cb_distribution"):
                self.cb_distribution.setCurrentIndex(2)  # Manual mode
            # Automatically apply position adjustment
            if hasattr(self, "apply_position_adjustment_to_cell"):
                self.apply_position_adjustment_to_cell()
        elif not enabled and not is_startup:
            # User disabled position mode - reset to default distribution
            self.table_volume_override = 0.0
            self.settings["pos_table_volume_override"] = 0.0
            if hasattr(self, "cb_distribution"):
                self.cb_distribution.setCurrentIndex(0)  # Uniform distribution
            if (
                hasattr(self, "position_target_row_active")
                and self.position_target_row_active is not None
            ):
                self._set_position_target_row_mask(None)

        self.save_settings()

        # Затемняем/включаем верхнюю часть в зависимости от позиции режима
        self._dim_top_controls(enabled)

        # Пересчитываем для обновления lbl_info с правильным значением dimmed
        self.schedule_update_calc()

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

        # Восстанавливаем исходный размер окна, чтобы избежать "прыжков"
        if not is_startup:
            self.setFixedSize(current_size)

    def _get_active_rows_for_table(self):
        selected_rows = sorted(
            i for i in getattr(self, "selected_transfer_rows", set()) if 0 <= int(i) < 5
        )
        return selected_rows

    def _sync_selected_rows_with_cells_count(self):
        selected = {
            int(i)
            for i in getattr(self, "selected_transfer_rows", set())
            if 0 <= int(i) < 5
        }

        self.selected_transfer_rows = selected
        self.settings["selected_cells"] = sorted(selected)

    def _update_selected_rows_visuals(self):
        if not hasattr(self, "cells_table"):
            return

        prev_block_state = self.cells_table.blockSignals(True)
        selected = set(self._get_active_rows_for_table())
        preset_index = (
            int(self.cb_distribution.currentIndex())
            if hasattr(self, "cb_distribution")
            else 2
        )
        default_flags = QTableWidgetItem().flags()
        for i in range(5):
            for col in range(3):
                item = self.cells_table.item(i, col)
                if not item:
                    continue

                if col == 0:
                    t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                    base_text = item.text() or t["calc_cell_label"].format(num=i + 1)
                    if base_text.startswith("● "):
                        base_text = base_text[2:]
                    item.setText(base_text)

                if i in selected:
                    bg = QColor("#3a3a3a")
                    fg = QColor("#ffffff")
                    item.setBackground(bg)
                    item.setForeground(fg)
                    item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(bg))
                    item.setData(Qt.ItemDataRole.ForegroundRole, QBrush(fg))
                    if col == 0:
                        item.setFlags(default_flags & ~Qt.ItemFlag.ItemIsEditable)
                    elif col == 1:
                        item.setFlags(
                            default_flags
                            & ~Qt.ItemFlag.ItemIsEditable
                            & ~Qt.ItemFlag.ItemIsSelectable
                        )
                    else:
                        if preset_index == 2:
                            item.setFlags(default_flags)
                        else:
                            item.setFlags(
                                default_flags
                                & ~Qt.ItemFlag.ItemIsEditable
                                & ~Qt.ItemFlag.ItemIsSelectable
                            )
                else:
                    bg = QColor("#000000")
                    fg = QColor("#000000") if col == 0 else QColor("#161616")
                    item.setBackground(bg)
                    item.setForeground(fg)
                    item.setData(Qt.ItemDataRole.BackgroundRole, QBrush(bg))
                    item.setData(Qt.ItemDataRole.ForegroundRole, QBrush(fg))
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.cells_table.blockSignals(prev_block_state)

    def _adapt_window_width_to_content(self):
        if not self.isVisible():
            return

        scale = self.settings.get("scale", self.base_scale)
        ratio = scale / float(self.base_scale)
        base_w = max(90, int(105 * ratio))
        max_w = max(220, int(360 * ratio))

        for name in (
            "inp_dep",
            "inp_risk",
            "inp_stop",
            "inp_pos_vol",
            "inp_pos_risk",
            "inp_pos_stop",
            "inp_min_order",
        ):
            widget = getattr(self, name, None)
            if not widget:
                continue

            try:
                text = widget.text() if widget.text() else "0"
                desired = widget.fontMetrics().horizontalAdvance(text + " 000") + 18
                widget.setMinimumWidth(max(base_w, min(max_w, desired)))
            except Exception:
                pass

        label_base_w = max(140, int(180 * ratio))
        label_max_w = max(320, int(700 * ratio))
        for name in (
            "lbl_status",
            "lbl_hint",
            "lbl_pos_vol_hint",
            "lbl_pos_risk_cash",
            "lbl_pos_adjust",
        ):
            label = getattr(self, name, None)
            if not label:
                continue
            try:
                text = label.text() if label.text() else ""
                desired = label.fontMetrics().horizontalAdvance(text) + 22
                label.setMinimumWidth(max(label_base_w, min(label_max_w, desired)))
            except Exception:
                pass

        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def apply_position_adjustment_to_cell(self):
        if not bool(self.settings.get("pos_mode_enabled", False)):
            self._update_status_text()
            return

        amount = float(getattr(self, "pos_adjust_delta", 0.0) or 0.0)
        if amount <= 0:
            self._update_status_text()
            return

        active_rows = self._get_active_rows_for_table()
        if not active_rows:
            self._update_status_text()
            return

        self.table_volume_override = float(amount)
        self.settings["pos_table_volume_override"] = float(amount)

        preset_index = (
            int(self.cb_distribution.currentIndex())
            if hasattr(self, "cb_distribution")
            else 2
        )

        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except Exception:
            pass

        if preset_index == 2:
            existing_values = []
            row_values = {}
            for row in active_rows:
                item = self.cells_table.item(row, 2)
                if item:
                    text = (item.text() or "").strip()
                    value = int(text) if text.isdigit() else 0
                    existing_values.append(value)
                    row_values[row] = value

            if sum(existing_values) <= 0:
                for i in range(5):
                    item = self.cells_table.item(i, 2)
                    if item:
                        item.setText("0")
                first_row = active_rows[0]
                first_item = self.cells_table.item(first_row, 2)
                if first_item:
                    first_item.setText("100")
            else:
                for row in active_rows:
                    if row_values.get(row, 0) > 0:
                        continue
                    item = self.cells_table.item(row, 2)
                    if item:
                        item.setText("100")
        else:
            for i in range(5):
                item = self.cells_table.item(i, 2)
                if item:
                    item.setText("0")

            count = len(active_rows)
            values = []
            if preset_index == 0:
                base = int(100 / count)
                remainder = 100 % count
                values = [base + (1 if idx < remainder else 0) for idx in range(count)]
            else:
                dec = [100, 75, 50, 25, 10]
                values = dec[:count]
                if len(values) < count:
                    values.extend([10] * (count - len(values)))

            for idx, row in enumerate(active_rows):
                item = self.cells_table.item(row, 2)
                if item:
                    item.setText(str(values[idx]))

        self.cells_table.itemChanged.connect(self.on_table_item_changed)

        self._update_selected_rows_visuals()
        self.update_cell_volumes()
        self.save_cell_settings()

        self._update_status_text()

    def format_with_abbreviations(self, value, precision):
        """Форматирует число с одним сокращением"""
        try:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            # Основное форматированное значение
            main = f"{value:,.{precision}f}".replace(",", " ").replace(".", ",")

            # Одно сокращение
            if value >= 1_000_000_000:
                abbr = f"{value / 1_000_000_000:.1f}{t['abbr_billion']}"
            elif value >= 1_000_000:
                abbr = f"{value / 1_000_000:.1f}{t['abbr_million']}"
            elif value >= 1_000:
                abbr = f"{value / 1_000:.0f}{t['abbr_thousand']}"
            else:
                return main

            return f"{main} / {abbr}"
        except:
            return str(value)

    def format_hint_no_decimals(self, value):
        """Формат подсказок без дробной части и без зависимости от настроек точности."""
        try:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            value = float(value)
            main = f"{value:,.0f}".replace(",", " ")

            def fmt_abbr(val, div, suffix):
                short = f"{val / div:.1f}".rstrip("0").rstrip(".")
                return f"{short}{suffix}"

            if abs(value) >= 1_000_000_000:
                abbr = fmt_abbr(value, 1_000_000_000, t["abbr_billion"])
            elif abs(value) >= 1_000_000:
                abbr = fmt_abbr(value, 1_000_000, t["abbr_million"])
            elif abs(value) >= 1_000:
                abbr = fmt_abbr(value, 1_000, t["abbr_thousand"])
            else:
                return main

            return f"{main} / {abbr}"
        except Exception:
            return "0"

    def apply_styles(self):

        scale = self.settings.get("scale", self.base_scale)
        scale = max(80, min(200, int(scale)))
        ratio = scale / float(self.base_scale)
        base_font = int(11 * (self.base_scale / 100.0))
        f_main = max(8, int(base_font * ratio))
        input_font = max(8, int(9 * ratio))
        f_small = max(7, int(8.5 * ratio))
        pad_main = max(2, int(3 * ratio))
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
            QPushButton {{ background: #333; color: #9A9A9A; border: 1px solid #444; border-radius: {max(4, int(4*ratio))}px; font-weight: bold; }}
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

        input_height = max(int(28 * ratio), int(12 * ratio + 14))
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
                    color: #A8A8A8;
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
                    color: #161616;
                    background: #000000;
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
        pos_toggle_pad_v = max(1, int(2 * ratio))
        pos_toggle_min_h = max(14, int(16 * ratio))
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
                (
                    f"QCheckBox#PosModeToggle {{ color: #9A9A9A; font-size: {f_small}pt; font-weight: bold; padding: {pos_toggle_pad_v}px {btn_pad}px; min-height: {pos_toggle_min_h}px; border-radius: {radius_main}px; background: #2A2A2A; border: 1px solid #3A3A3A; }}"
                    f"QCheckBox#PosModeToggle:checked {{ background: #38BE1D; color: black; border: 1px solid #38BE1D; }}"
                    f"QCheckBox#PosModeToggle:unchecked {{ background: #2A2A2A; color: #888; border: 1px solid #3A3A3A; }}"
                )
            )

        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        # Обновляем масштаб элементов на вкладке каскадов
        if hasattr(self, "tab_cascade"):
            self.tab_cascade.apply_scale()

    # --- УПРАВЛЕНИЕ ГОРЯЧИМИ КЛАВИШАМИ (ИСПРАВЛЕНО) ---
    def rebind_hotkeys(self):
        def normalize_hotkey(hotkey_value, fallback):
            value = str(hotkey_value or "").strip().lower()
            value = value.replace(" ", "")
            return value or fallback

        keyboard.unhook_all()
        # F1 - Скрыть/Показать
        hk_show = normalize_hotkey(self.settings.get("hk_show", "f1"), "f1")
        try:
            keyboard.add_hotkey(hk_show, self.signaler.toggle_sig.emit)
            self.settings["hk_show"] = hk_show
        except Exception:
            keyboard.add_hotkey("f1", self.signaler.toggle_sig.emit)
            self.settings["hk_show"] = "f1"

        # F2 - Калибровка (в зависимости от активной вкладки)
        hk_coords = normalize_hotkey(self.settings.get("hk_coords", "f2"), "f2")
        try:
            keyboard.add_hotkey(hk_coords, self.handle_hotkey_calibration)
            self.settings["hk_coords"] = hk_coords
        except Exception:
            keyboard.add_hotkey("f2", self.handle_hotkey_calibration)
            self.settings["hk_coords"] = "f2"
        # F3 - ОТПРАВИТЬ - ОТКЛЮЧЕНО, теперь только через кнопку
        # keyboard.add_hotkey(
        #     self.settings.get("hk_send", "f3"), self.signaler.apply_sig.emit
        # )

    def _keepalive_hotkeys(self):
        """Периодическая перерегистрация хуков — Windows убивает их при простое/сне."""
        try:
            self.rebind_hotkeys()
        except Exception:
            pass

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
        if hasattr(self, "tab_cascade") and self.tab_cascade.is_apply_active():
            return False

        if hasattr(self, "tab_cascade") and self.tab_cascade.cancel_calibration():
            return True

        if getattr(self, "calc_calibration_active", False):
            self.settings["points"] = []
            self.save_settings()
            self.calc_calibration_active = False
            hk_coords = self.settings.get("hk_coords", "f2").upper()
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_status.setText(t["calc_calib_reset"].format(hotkey=hk_coords))
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
        active_rows = sorted(self._get_active_rows_for_table())
        is_reversed = self.settings.get("cells_reversed", False)
        if is_reversed:
            active_rows = list(reversed(active_rows))

        if not active_rows:
            return

        transfers = []
        for row in active_rows:
            point_index = row
            if len(points) <= point_index:
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_status.setText(t["calc_not_enough_points"])
                self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
                return

            vol_item = self.cells_table.item(row, 1)
            vol_to_send = (
                vol_item.text().replace(" ", "").replace(",", ".")
                if vol_item and vol_item.text()
                else "0"
            )
            transfers.append((point_index, vol_to_send))

        if not transfers:
            return

        # Order already follows the intended row direction

        try:
            # speed-tweak: set pyautogui minimal sleeps/durations like in cascade_tab
            try:
                pyautogui.MINIMUM_SLEEP = 0.0005
                pyautogui.MINIMUM_DURATION = 0.005
                pyautogui.PAUSE = 0.0
            except Exception:
                pass

            old_clip = pyperclip.paste()
            # capture exact start position to restore later if needed
            try:
                start_pos = pyautogui.position()
                start_x, start_y = int(start_pos[0]), int(start_pos[1])
            except Exception:
                start_x, start_y = None, None

            if bool(self.settings.get("minimize_after_apply", True)):
                self.showMinimized()
                time.sleep(0.08)
            else:
                time.sleep(0.02)

            for point_index, vol_to_send in transfers:
                pyperclip.copy(vol_to_send)
                time.sleep(0.01)
                # balanced sequence: faster than before, but still reliable
                pyautogui.moveTo(
                    points[point_index][0], points[point_index][1], duration=0.015
                )
                pyautogui.click()
                time.sleep(0.012)
                pyautogui.doubleClick(interval=0.03)
                time.sleep(0.012)
                keyboard.press_and_release("ctrl+a")
                time.sleep(0.01)
                keyboard.press_and_release("backspace")
                time.sleep(0.01)
                keyboard.press_and_release("ctrl+v")
                time.sleep(0.012)
                keyboard.press_and_release("enter")
                # short pause before next cell
                time.sleep(0.025)

            # restore original cursor position if captured
            if start_x is not None and start_y is not None:
                try:
                    pyautogui.moveTo(start_x, start_y)
                except Exception:
                    pass
            pyperclip.copy(old_clip)
            # Окно остается свернутым - не разворачиваем автоматически
        except Exception as e:
            print(f"Error: {e}")

    def start_calibration_calc(self):
        """Начинает калибровку - очищает точки и показывает инструкции"""
        cells_count = int(
            self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
        )
        hk_coords = self.settings.get("hk_coords", "f2").upper()

        points = self.settings.get("points", [])
        if len(points) >= cells_count:
            self.calc_calibration_active = False
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_status.setText(t["calc_calib_exists"].format(cells=cells_count))
            self.lbl_status.setStyleSheet("color: #38BE1D; font-size: 7pt;")
            self.update_calibration_status()
            return

        self.calc_calibration_active = True

        # Показываем подробную инструкцию
        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        instruction = t["calc_calib_instruction"].format(
            cells=cells_count, hotkey=hk_coords
        )

        self.lbl_status.setText(instruction)
        self.lbl_status.setStyleSheet(
            "color: #FFD700; font-size: 6pt; line-height: 130%;"
        )
        self.update_calibration_status()

    def capture_coords(self):
        """Захватывает координаты ячеек (ровно столько, сколько нужно)"""
        if not getattr(self, "calc_calibration_active", False):
            try:
                configured = int(
                    self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
                )
            except Exception:
                configured = int(self.lbl_cells_count.text())

            existing_points = self.settings.get("points", [])
            if len(existing_points) >= configured:
                self.settings["points"] = []
                self.save_settings()
                self.calc_calibration_active = True
                hk_coords = self.settings.get("hk_coords", "f2").upper()
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_status.setText(
                    t["calc_calib_reset_short"].format(hotkey=hk_coords)
                )
                self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
                return

            self.start_calibration_calc()
            return

        cells_count = int(
            self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
        )
        points = self.settings.get("points", [])

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
        cells_count = int(
            self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
        )
        points_count = len(self.settings.get("points", []))
        hk_coords = self.settings.get("hk_coords", "f2").upper()

        if points_count == 0:
            if self.calc_calibration_active:
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_status.setText(t["calc_calib_active"].format(hotkey=hk_coords))
                self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
            else:
                self.lbl_status.setText("")
        elif points_count < cells_count:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_status.setText(
                t["calc_calib_progress"].format(points=points_count, cells=cells_count)
            )
            self.lbl_status.setStyleSheet("color: #FF9F0A; font-size: 7pt;")
        else:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_status.setText(t["calc_calib_ready"].format(cells=cells_count))
            self.lbl_status.setStyleSheet("color: #38BE1D; font-size: 7pt;")

    def increase_cells(self):
        """Увеличивает количество ячеек"""
        current = int(self.lbl_cells_count.text())
        if current < 5:
            current += 1
            self.lbl_cells_count.setText(str(current))
            self.settings["scalp_cells_count"] = current
            self.on_cells_changed()
            self._apply_manual_min_order_defaults()

    def decrease_cells(self):
        """Уменьшает количество ячеек"""
        current = int(self.lbl_cells_count.text())
        if current > 1:
            current -= 1
            self.lbl_cells_count.setText(str(current))
            self.settings["scalp_cells_count"] = current
            self.on_cells_changed()
            self._apply_manual_min_order_defaults()

    def _apply_manual_min_order_defaults(self):
        if (
            not hasattr(self, "cb_distribution")
            or int(self.cb_distribution.currentIndex()) != 2
        ):
            return

        active_rows = self._get_active_rows_for_table()
        if not active_rows:
            return

        total_vol = float(self._get_active_table_total_volume() or 0.0)
        if total_vol <= 0:
            return

        try:
            min_order = float(self.inp_min_order.text().replace(",", ".") or 0)
        except Exception:
            min_order = 0.0

        if min_order <= 0:
            return

        min_percent = int(round((min_order / total_vol) * 100))
        min_percent = max(1, min(100, min_percent))

        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except Exception:
            pass

        for i in active_rows:
            # Skip the target row that has transferred volume - preserve it as-is
            if i == self.position_target_row_active:
                continue
            percent_item = self.cells_table.item(i, 2)
            if not percent_item:
                continue
            current_text = (percent_item.text() or "").strip()
            current_val = int(current_text) if current_text.isdigit() else 0
            if current_val <= 0:
                percent_item.setText(str(min_percent))

        self.cells_table.itemChanged.connect(self.on_table_item_changed)
        self.update_cell_volumes()
        self.save_cell_settings()

    def _apply_manual_active_row_flags(self):
        if (
            not hasattr(self, "cb_distribution")
            or int(self.cb_distribution.currentIndex()) != 2
            or not hasattr(self, "cells_table")
        ):
            return

        default_flags = QTableWidgetItem().flags()
        for i in range(5):
            for col in range(3):
                item = self.cells_table.item(i, col)
                if not item:
                    continue
                if col in (0, 1):
                    item.setFlags(default_flags & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(default_flags)

    def toggle_cells_order(self):
        """Переворачивает порядок ячеек в таблице"""
        cells_count = 5

        # Собираем текущие проценты для всех 5 строк
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
        self._update_selected_rows_visuals()

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
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            label_item = QTableWidgetItem(t["calc_cell_label"].format(num=i + 1))
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            label_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cells_table.setItem(i, 0, label_item)

            # Ячейка с объемом (не редактируется, не выделяется, рассчитывается)
            volume_item = QTableWidgetItem("0")
            volume_item.setFlags(
                volume_item.flags()
                & ~Qt.ItemFlag.ItemIsEditable
                & ~Qt.ItemFlag.ItemIsSelectable
            )
            volume_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cells_table.setItem(i, 1, volume_item)

            # Ячейка с процентом (редактируется только для активных)
            percent_item = QTableWidgetItem("")
            percent_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cells_table.setItem(i, 2, percent_item)

        # Обновляем подписи ячеек с учетом порядка
        self.update_cells_labels()

        # Обновляем высоту таблицы, чтобы всегда были видны 5 строк
        self.update_cells_table_height()
        self._sync_selected_rows_with_cells_count()

        # Переприменяем текущий тип распределения
        preset_index = self.cb_distribution.currentIndex()

        if preset_index != 2 and self.position_target_row_active is not None:
            self._set_position_target_row_mask(None)
        self._apply_preset_values(preset_index)

        # Загружаем сохраненные значения процентов только для режима "Вручную"
        if preset_index == 2:
            saved_multipliers = self.settings.get(
                "scalp_multipliers", [100, 50, 25, 10, 0]
            )
            is_reversed = self.settings.get("cells_reversed", False)
            if is_reversed:
                saved_multipliers = list(reversed(saved_multipliers))

            # Use actual active rows (which may include target row beyond cells_count)
            active_rows = self._get_active_rows_for_table()
            for i in active_rows:
                # Skip loading saved value for target row if we have active transfer
                # - keep it at 100% to preserve transferred volume
                if i == self.position_target_row_active:
                    percent_item = self.cells_table.item(i, 2)
                    if percent_item:
                        percent_item.setText("100")
                    continue
                if i < len(saved_multipliers) and saved_multipliers[i] > 0:
                    percent_item = self.cells_table.item(i, 2)
                    if percent_item:
                        percent_item.setText(str(saved_multipliers[i]))
            self._apply_manual_active_row_flags()

        self._update_selected_rows_visuals()

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

        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])

        for i in range(5):
            label_item = self.cells_table.item(i, 0)
            if not label_item:
                continue

            if i < cells_count:
                label_item.setText(t["calc_cell_label"].format(num=active_labels[i]))
            else:
                label_item.setText(t["calc_cell_label"].format(num=i + 1))

        self._update_selected_rows_visuals()

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
        """Обработчик клика по ячейке: toggle-мультивыбор в колонке 0"""
        self._clear_ghost_focus()
        if not item:
            return

        if item.column() == 0:
            row = item.row()

            selected = set(getattr(self, "selected_transfer_rows", set()))
            if row in selected:
                selected.remove(row)
            else:
                selected.add(row)

            self.selected_transfer_rows = selected
            self.settings["selected_cells"] = sorted(selected)

            preset_index = self.cb_distribution.currentIndex()
            if preset_index != 2:
                try:
                    self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
                except Exception:
                    pass
                self._apply_preset_values(preset_index)
                self.cells_table.itemChanged.connect(self.on_table_item_changed)

            self._update_selected_rows_visuals()
            self.update_cell_volumes()
            self.save_cell_settings()

            self.cells_table.clearSelection()
            self.cells_table.setCurrentItem(None)
        elif item.column() == 1:
            self.cells_table.clearSelection()
            self.cells_table.setCurrentItem(None)

    def on_table_item_changed(self, item):
        """Вызывается когда изменяется ячейка таблицы"""
        if item.column() == 2:  # Только для колонки с процентами
            if (
                hasattr(self, "cb_distribution")
                and int(self.cb_distribution.currentIndex()) != 2
            ):
                return

            # Проверяем что введено число
            text = item.text().strip()
            if text and not text.isdigit():
                item.setText("0")

            self.update_cell_volumes()
            self.save_cell_settings()
            self._adapt_window_width_to_content()

    def toggle_all_transfer_rows(self):
        if not hasattr(self, "cells_table"):
            return
        selected = set(getattr(self, "selected_transfer_rows", set()))
        if len(selected) >= 5:
            selected = set()
        else:
            selected = set(range(5))

        self.selected_transfer_rows = selected
        self.settings["selected_cells"] = sorted(selected)

        preset_index = (
            int(self.cb_distribution.currentIndex())
            if hasattr(self, "cb_distribution")
            else 2
        )
        if preset_index != 2:
            try:
                self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
            except Exception:
                pass
            self._apply_preset_values(preset_index)
            self.cells_table.itemChanged.connect(self.on_table_item_changed)

        self._update_selected_rows_visuals()
        self.update_cell_volumes()
        self.save_cell_settings()

    def finalize_startup_layout(self):
        self.update_cells_table_height()
        self._adapt_window_width_to_content()
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    def _apply_preset_values(self, preset_index):
        """Применяет значения выбранного пресета"""
        active_rows = self._get_active_rows_for_table()
        if self.settings.get("cells_reversed", False):
            active_rows = list(reversed(active_rows))
        cells_count = len(active_rows)

        if preset_index == 2:  # Вручную
            return

        if cells_count <= 0:
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

        # Применяем значения
        for idx, row in enumerate(active_rows):
            item = self.cells_table.item(row, 2)
            if item:
                item.setText(str(values[idx]))

    def apply_distribution_preset(self):
        """Применяет выбранную предустановку распределения"""
        preset_index = self.cb_distribution.currentIndex()

        if preset_index != 2:
            self.table_volume_override = 0.0
            self.settings["pos_table_volume_override"] = 0.0

        if preset_index == 2 and hasattr(self, "lbl_cells_count"):
            # In manual mode, preserve the current cell count (don't force to 1)
            current_cells_count = int(self.lbl_cells_count.text())

        if preset_index != 2 and self.position_target_row_active is not None:
            self._set_position_target_row_mask(None)

        # Отключаем сигнал чтобы не вызывать сохранение много раз
        try:
            self.cells_table.itemChanged.disconnect(self.on_table_item_changed)
        except:
            pass

        # Применяем значения пресета
        self._apply_preset_values(preset_index)

        # Включаем сигнал обратно
        self.cells_table.itemChanged.connect(self.on_table_item_changed)

        # Сохраняем выбранный тип и всё остальное
        self.settings["scalp_distribution_type"] = preset_index
        self._update_selected_rows_visuals()
        self.update_cell_volumes()
        self.save_cell_settings()  # This calls save_settings() internally

    def _get_active_table_total_volume(self):
        override = float(getattr(self, "table_volume_override", 0.0) or 0.0)
        if override <= 0:
            override = float(self.settings.get("pos_table_volume_override", 0.0) or 0.0)
            if override > 0:
                self.table_volume_override = override
        if override > 0:
            return override

        if bool(self.settings.get("pos_mode_enabled", False)):
            delta = float(getattr(self, "pos_adjust_delta", 0.0) or 0.0)
            if delta > 0:
                return delta
        return float(getattr(self, "current_vol", 0.0) or 0.0)

    def update_cell_volumes(self):
        """Обновляет объемы в каждой ячейке на основе процентов и минимума"""
        active_rows = set(self._get_active_rows_for_table())
        total_vol = self._get_active_table_total_volume()
        p_vol = self.settings.get("prec_dep", 2)
        preset_index = (
            int(self.cb_distribution.currentIndex())
            if hasattr(self, "cb_distribution")
            else 2
        )

        try:
            min_order = float(self.inp_min_order.text().replace(",", ".") or 6)
        except:
            min_order = 6

        self.cells_table.blockSignals(True)
        for i in range(5):
            volume_item = self.cells_table.item(i, 1)
            percent_item = self.cells_table.item(i, 2)

            if not volume_item:
                continue

            if i in active_rows and percent_item:
                try:
                    percent = float(percent_item.text() or 0)
                    raw_volume = (total_vol * percent) / 100.0
                    if preset_index == 0:  # Равномерно: не раздуваем сумму до min_order
                        volume = raw_volume
                    else:
                        volume = max(min_order, raw_volume)  # Не меньше минимума
                    volume_item.setText(
                        f"{volume:,.{p_vol}f}".replace(",", " ").replace(".", ",")
                    )
                except:
                    volume_item.setText("0")
            else:
                volume_item.setText("")
                if percent_item:
                    percent_item.setText("")

            # Сохраняем минимум в настройки
            self.settings["scalp_min_order"] = min_order
        self.cells_table.blockSignals(False)
        self._update_selected_rows_visuals()

    def on_min_order_changed(self):
        """Вызывается при нажатии Enter в поле минимального ордера"""
        self._apply_min_order_live()
        self.inp_min_order.deselect()
        self.inp_min_order.clearFocus()

    def on_min_order_live_changed(self):
        if hasattr(self, "_min_order_live_timer"):
            self._min_order_live_timer.start(20)
        else:
            self._apply_min_order_live()

    def _apply_min_order_live(self):
        self.update_cell_volumes()
        self._adapt_window_width_to_content()
        self.save_cell_settings()

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
        if self.position_target_row_active is not None:
            cells_count = int(self.settings.get("scalp_cells_count", 4))
        else:
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
        self.settings["pos_table_volume_override"] = float(
            getattr(self, "table_volume_override", 0.0) or 0.0
        )
        try:
            self.save_cell_settings()
        except Exception:
            self.save_settings()
        event.accept()

    def _on_app_about_to_quit(self):
        """Сохраняет настройки при завершении приложения"""
        try:
            self.settings["window_pos"] = [self.x(), self.y()]
            self.settings["pos_table_volume_override"] = float(
                getattr(self, "table_volume_override", 0.0) or 0.0
            )
            self.save_cell_settings()
        except Exception:
            pass


if __name__ == "__main__":
    existing_qt_rules = os.environ.get("QT_LOGGING_RULES", "")
    dpi_noise_rule = "qt.qpa.window.warning=false"
    if dpi_noise_rule not in existing_qt_rules:
        os.environ["QT_LOGGING_RULES"] = (
            f"{existing_qt_rules};{dpi_noise_rule}"
            if existing_qt_rules
            else dpi_noise_rule
        )

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
