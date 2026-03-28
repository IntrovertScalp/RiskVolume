import sys, json, os, ctypes, time, threading, importlib, hmac, hashlib, multiprocessing, keyboard, pyautogui, pyperclip
from urllib.parse import urlencode
import queue
import config
import requests
from PyQt6.QtWidgets import (
    QApplication,
    QStyleFactory,
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
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt,
    QRegularExpression,
    QTimer,
    QEasingCurve,
    QVariantAnimation,
    pyqtSignal,
    QObject,
    QSharedMemory,
)
from PyQt6.QtGui import (
    QIcon,
    QRegularExpressionValidator,
    QColor,
    QBrush,
    QPalette,
    QPixmap,
    QPainter,
    QPen,
)

from config import *
from settings_dialog import SettingsDialog
from logic import calculate_risk_data, calculate_position_adjustment, get_info_html
from translations import TRANS
from cascade_tab import CascadeTab
from calculator_tab import init_calculator_tab
from secure_credentials import protect_secret, unprotect_secret

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

_app_shared_memory_guard = None


def _fetch_balance_with_ccxt_process(payload, result_queue):
    try:
        ccxt = importlib.import_module("ccxt")

        exchange_id = str(payload.get("exchange_id", "") or "").strip().lower()
        api_key = str(payload.get("api_key", "") or "").strip()
        api_secret = str(payload.get("api_secret", "") or "").strip()
        market_type = str(payload.get("market_type", "spot") or "spot").strip().lower()
        asset = str(payload.get("asset", "USDT") or "USDT").strip().upper()
        passphrase = str(payload.get("passphrase", "") or "").strip()

        ex_class = getattr(ccxt, exchange_id, None)
        if ex_class is None:
            result_queue.put({"ok": False, "error": f"Unsupported exchange: {exchange_id}"})
            return

        options = {}
        if market_type == "futures":
            default_map = {
                "bybit": "swap",
                "okx": "swap",
                "gate": "swap",
                "bitget": "swap",
                "mexc": "swap",
                "kucoin": "swap",
            }
            options["defaultType"] = default_map.get(exchange_id, "swap")

        params = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": 4000,
            "options": options,
        }
        if passphrase:
            params["password"] = passphrase

        exchange = ex_class(params)
        try:
            balance = exchange.fetch_balance()
        finally:
            try:
                exchange.close()
            except Exception:
                pass

        total = balance.get("total", {}) if isinstance(balance, dict) else {}
        free = balance.get("free", {}) if isinstance(balance, dict) else {}
        used = balance.get("used", {}) if isinstance(balance, dict) else {}

        free_val = float(free.get(asset, 0.0) or 0.0)
        used_val = float(used.get(asset, 0.0) or 0.0)

        # For futures, show only free (available) balance, not total/wallet balance.
        if market_type == "futures":
            if asset in free and free[asset] is not None:
                result_queue.put({"ok": True, "balance": free_val})
                return
            if asset in total and total[asset] is not None:
                result_queue.put({"ok": True, "balance": float(total[asset])})
                return
            result_queue.put({"ok": True, "balance": free_val})
            return

        if asset in total and total[asset] is not None:
            result_queue.put({"ok": True, "balance": float(total[asset])})
            return

        result_queue.put({"ok": True, "balance": free_val + used_val})
    except Exception as exc:
        result_queue.put({"ok": False, "error": str(exc)})


def _force_consistent_qt_theme(app: QApplication):
    """Фиксирует единый тёмный вид на разных ПК/версиях Windows."""
    try:
        fusion_style = QStyleFactory.create("Fusion")
        if fusion_style is not None:
            app.setStyle(fusion_style)
    except Exception:
        pass

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#121212"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#121212"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#252525"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#38BE1D"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    app.setPalette(palette)


class HotkeySignaler(QObject):
    toggle_sig = pyqtSignal()
    calibrate_sig = pyqtSignal()
    apply_sig = pyqtSignal()  # Новый сигнал для применения


class AutoDepositSignaler(QObject):
    fetch_finished = pyqtSignal(object, object)


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
        self._create_posmode_checkmark_icon()
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
        self.signaler.calibrate_sig.connect(self.handle_hotkey_calibration)
        self.signaler.apply_sig.connect(
            self.handle_hotkey_apply
        )  # Единая точка входа для горячей клавиши
        self._auto_dep_signaler = AutoDepositSignaler()
        self._auto_dep_signaler.fetch_finished.connect(self._on_auto_dep_fetch_finished)

        self.old_pos = None
        self._startup_window_size = None
        self._lock_dynamic_resize = False
        self._window_size_anim = None
        self._window_size_anim_target = None
        self._resize_len_baseline = {}
        self._resize_step_chars = 5
        self._last_applied_resize_pressure = 0
        self._force_resize_pending = False
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
        self._hotkey_ids = {}
        self._cells_layout_reflow_pending = False
        self._api_read_only_check_cache = {}
        self._status_neutral_token = 0

        self.init_ui()
        self._calc_update_timer = QTimer(self)
        self._calc_update_timer.setSingleShot(True)
        self._calc_update_timer.timeout.connect(self.update_calc)
        self._min_order_live_timer = QTimer(self)
        self._min_order_live_timer.setSingleShot(True)
        self._min_order_live_timer.timeout.connect(self._apply_min_order_live)
        self._smooth_resize_idle_timer = QTimer(self)
        self._smooth_resize_idle_timer.setSingleShot(True)
        self._smooth_resize_idle_timer.timeout.connect(self._apply_idle_smooth_resize)
        self.rebind_hotkeys()
        self.update_calc()

        # Периодически перерегистрируем keyboard-хуки (Windows убивает их при простое/сне)
        self._hotkey_keepalive_timer = QTimer(self)
        self._hotkey_keepalive_timer.timeout.connect(self._keepalive_hotkeys)
        self._hotkey_keepalive_timer.start(60 * 1000)  # каждые 60 секунд

        # Периодическая синхронизация депозита через API (если включено)
        self._auto_dep_sync_busy = False
        self._auto_dep_timer = QTimer(self)
        self._auto_dep_timer.setSingleShot(False)
        self._auto_dep_timer.timeout.connect(self._sync_deposit_from_exchange)
        self._apply_auto_deposit_sync(force_now=True)

        # Сохраняем настройки при закрытии приложения любым способом
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._on_app_about_to_quit)

        # Восстанавливаем позицию окна
        pos = self.settings.get("window_pos", None)
        if pos and len(pos) == 2:
            self.move(pos[0], pos[1])

    def _create_posmode_checkmark_icon(self):
        import tempfile

        path = os.path.join(tempfile.gettempdir(), "rv_posmode_checkmark_black.png")
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
        self._posmode_checkmark_path_css = path.replace("\\", "/")

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
            "scalp_manual_multipliers": [100, 50, 25, 10, 0],
            "cells_reversed": False,
            "pos_current_vol": "0",
            "pos_risk": "1",
            "pos_stop": "0",
            "pos_stop_now": "0",
            "pos_target_cell": 1,
            "pos_mode_enabled": False,
            "pos_table_volume_override": 0.0,
            "selected_cells": [0],
            "minimize_after_apply": True,
            "auto_dep_enabled": False,
            "auto_dep_exchange": "binance",
            "auto_dep_market": "futures",
            "auto_dep_asset": "USDT",
            "auto_apply_terminal": "profit_forge",
            "calc_points_profit_forge": [],
            "calc_points_metascalp": [],
            "calc_points_tigertrade": [],
            "calc_points_surf": [],
            "calc_points_vataga": [],
            "tiger_open_point": None,
            "tiger_close_point": None,
            "surf_open_point": None,
            "surf_accept_point": None,
            "vataga_open_point": None,
            "auto_dep_api_key": "",
            "auto_dep_api_secret": "",
            "auto_dep_api_passphrase": "",
            "auto_dep_credentials": {},
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

        # Migration: preserve existing calculator calibration points as Profit Forge points.
        if (
            not self.settings.get("calc_points_profit_forge")
            and isinstance(self.settings.get("points", None), list)
            and self.settings.get("points")
        ):
            self.settings["calc_points_profit_forge"] = list(self.settings.get("points", []))

        # One-time fix: clear legacy auto-copied points for non-PF terminals.
        # They could falsely complete calibration after 1-2 hotkey presses.
        non_pf_points_fix_changed = False
        if not bool(self.settings.get("non_pf_points_fix_v1_applied", False)):
            pf_points = self.settings.get("calc_points_profit_forge", [])
            if not isinstance(pf_points, list):
                pf_points = []

            for non_pf_key in [
                "calc_points_metascalp",
                "calc_points_surf",
                "calc_points_vataga",
            ]:
                pts = self.settings.get(non_pf_key, [])
                if isinstance(pts, list) and isinstance(pf_points, list) and pts == pf_points:
                    self.settings[non_pf_key] = []
                    non_pf_points_fix_changed = True

            self.settings["non_pf_points_fix_v1_applied"] = True
            non_pf_points_fix_changed = True

        if non_pf_points_fix_changed:
            self.save_settings()

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

        if self._migrate_auto_dep_credentials_secure_storage():
            self.save_settings()

        # Корректируем масштаб если он выходит за разумные пределы
        scale = self.settings.get("scale", self.base_scale)
        if scale < 130 or scale > 200:
            self.settings["scale"] = self.base_scale
            self.save_settings()

    def save_settings(self):
        self.settings["auto_dep_api_key"] = ""
        self.settings["auto_dep_api_secret"] = ""
        self.settings["auto_dep_api_passphrase"] = ""
        if not isinstance(self.settings.get("auto_dep_credentials", {}), dict):
            self.settings["auto_dep_credentials"] = {}
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.settings, f)

    def _secure_encrypt_field(self, value):
        value = str(value or "").strip()
        if not value:
            return ""
        return f"dpapi:{protect_secret(value)}"

    def _secure_decrypt_field(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if not raw.startswith("dpapi:"):
            return raw
        try:
            return unprotect_secret(raw[6:])
        except Exception:
            return ""

    def _normalize_auto_dep_credentials_shape(self, raw):
        if not isinstance(raw, dict):
            raw = {}
        result = {}
        for exchange_id in ["binance", "bybit", "okx", "gate", "bitget", "mexc", "kucoin"]:
            src = raw.get(exchange_id, {})
            if not isinstance(src, dict):
                src = {}
            result[exchange_id] = {
                "api_key": str(src.get("api_key", "") or ""),
                "api_secret": str(src.get("api_secret", "") or ""),
                "api_passphrase": str(src.get("api_passphrase", "") or ""),
            }
        return result

    def get_auto_dep_credentials_plain(self):
        creds_map = self._normalize_auto_dep_credentials_shape(
            self.settings.get("auto_dep_credentials", {})
        )

        for exchange_id, creds in creds_map.items():
            creds_map[exchange_id] = {
                "api_key": self._secure_decrypt_field(creds.get("api_key", "")),
                "api_secret": self._secure_decrypt_field(creds.get("api_secret", "")),
                "api_passphrase": self._secure_decrypt_field(
                    creds.get("api_passphrase", "")
                ),
            }

        if not any(creds_map.get("binance", {}).values()):
            legacy_key = str(self.settings.get("auto_dep_api_key", "") or "").strip()
            legacy_secret = str(self.settings.get("auto_dep_api_secret", "") or "").strip()
            legacy_passphrase = str(
                self.settings.get("auto_dep_api_passphrase", "") or ""
            ).strip()
            if legacy_key or legacy_secret or legacy_passphrase:
                creds_map["binance"] = {
                    "api_key": legacy_key,
                    "api_secret": legacy_secret,
                    "api_passphrase": legacy_passphrase,
                }

        return creds_map

    def set_auto_dep_credentials_plain(self, plain_map):
        plain_map = self._normalize_auto_dep_credentials_shape(plain_map)
        encrypted_map = {}
        for exchange_id, creds in plain_map.items():
            encrypted_map[exchange_id] = {
                "api_key": self._secure_encrypt_field(creds.get("api_key", "")),
                "api_secret": self._secure_encrypt_field(creds.get("api_secret", "")),
                "api_passphrase": self._secure_encrypt_field(
                    creds.get("api_passphrase", "")
                ),
            }
        self.settings["auto_dep_credentials"] = encrypted_map
        self.settings["auto_dep_api_key"] = ""
        self.settings["auto_dep_api_secret"] = ""
        self.settings["auto_dep_api_passphrase"] = ""

    def _migrate_auto_dep_credentials_secure_storage(self):
        raw = self.settings.get("auto_dep_credentials", {})
        raw = self._normalize_auto_dep_credentials_shape(raw)
        has_unprotected = any(
            (
                str(creds.get("api_key", "") or "").strip()
                and not str(creds.get("api_key", "")).startswith("dpapi:")
            )
            or (
                str(creds.get("api_secret", "") or "").strip()
                and not str(creds.get("api_secret", "")).startswith("dpapi:")
            )
            or (
                str(creds.get("api_passphrase", "") or "").strip()
                and not str(creds.get("api_passphrase", "")).startswith("dpapi:")
            )
            for creds in raw.values()
        )

        has_legacy_plain = bool(
            str(self.settings.get("auto_dep_api_key", "") or "").strip()
            or str(self.settings.get("auto_dep_api_secret", "") or "").strip()
            or str(self.settings.get("auto_dep_api_passphrase", "") or "").strip()
        )

        if not has_unprotected and not has_legacy_plain:
            return False

        try:
            plain_map = self.get_auto_dep_credentials_plain()
            self.set_auto_dep_credentials_plain(plain_map)
            return True
        except Exception:
            return False

    def validate_auto_dep_credentials_read_only(
        self,
        exchange_id,
        api_key,
        api_secret,
        market_type,
        passphrase="",
        use_cache=True,
    ):
        exchange_id = str(exchange_id or "").strip().lower()
        market_type = str(market_type or "futures").strip().lower()
        api_key = str(api_key or "").strip()
        api_secret = str(api_secret or "").strip()
        passphrase = str(passphrase or "").strip()

        if not api_key or not api_secret:
            return False, "Empty API key/secret"

        if exchange_id != "binance":
            # For non-Binance exchanges we cannot reliably infer permissions via one unified API.
            return True, ""

        cache_hash = hashlib.sha256(
            f"{exchange_id}|{market_type}|{api_key}|{api_secret}|{passphrase}".encode("utf-8")
        ).hexdigest()
        cache_key = (exchange_id, market_type, cache_hash)
        if use_cache and cache_key in self._api_read_only_check_cache:
            return self._api_read_only_check_cache[cache_key]

        result = self._validate_binance_read_only_key(
            api_key,
            api_secret,
            market_type,
        )
        self._api_read_only_check_cache[cache_key] = result
        return result

    def _validate_binance_read_only_key(self, api_key, api_secret, market_type):
        try:
            timestamp_ms = int(time.time() * 1000)
            params = {"timestamp": timestamp_ms, "recvWindow": 5000}
            query = urlencode(params)
            signature = hmac.new(
                str(api_secret).encode("utf-8"),
                query.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers = {"X-MBX-APIKEY": str(api_key)}

            if market_type == "spot":
                url = f"https://api.binance.com/api/v3/account?{query}&signature={signature}"
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict) and data.get("code") and data.get("msg"):
                    raise RuntimeError(f"{data.get('code')}: {data.get('msg')}")
                can_trade = bool(data.get("canTrade", False))
            else:
                url = f"https://fapi.binance.com/fapi/v2/account?{query}&signature={signature}"
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict) and data.get("code") and data.get("msg"):
                    raise RuntimeError(f"{data.get('code')}: {data.get('msg')}")
                can_trade = bool(data.get("canTrade", False))

            if can_trade:
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                return False, t.get(
                    "api_key_not_read_only",
                    "API-ключ имеет право торговли. Используйте ключ только для чтения.",
                )

            return True, ""
        except Exception as exc:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            return False, t.get(
                "api_key_check_failed",
                "Не удалось проверить права API-ключа. Проверьте ключи и сеть.",
            ) + f" ({exc})"

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
            self._apply_auto_deposit_sync(force_now=True)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()

    def _apply_auto_deposit_sync(self, force_now=False):
        if not hasattr(self, "_auto_dep_timer"):
            return

        enabled = bool(self.settings.get("auto_dep_enabled", False))
        if hasattr(self, "btn_dep_refresh"):
            self.btn_dep_refresh.setVisible(enabled)
        if enabled:
            # Интервал до 1 минуты: достаточно оперативно и без лишней нагрузки.
            self._auto_dep_timer.start(45 * 1000)
            self._set_auto_dep_status("loading")
            if force_now:
                QTimer.singleShot(100, self._sync_deposit_from_exchange)
        else:
            self._auto_dep_timer.stop()
            self._set_auto_dep_status("off")

    def _set_auto_dep_status(self, state, message=None):
        if not hasattr(self, "lbl_dep_api_status"):
            return

        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        if state == "ok":
            text = t.get("dep_api_status_ok", "API: OK")
            style = "color: #38BE1D; font-size: 8pt;"
        elif state == "loading":
            text = t.get("dep_api_status_loading", "API: обновление...")
            style = "color: #8CB4FF; font-size: 8pt;"
        elif state == "error":
            text = t.get("dep_api_status_error", "API: ошибка")
            style = "color: #FF6B6B; font-size: 8pt;"
        else:
            text = t.get("dep_api_status_off", "API: выкл")
            style = "color: #666; font-size: 8pt;"

        self.lbl_dep_api_status.setText(text)
        self.lbl_dep_api_status.setStyleSheet(style)
        if message:
            self.lbl_dep_api_status.setToolTip(str(message))
        else:
            self.lbl_dep_api_status.setToolTip("")

    def manual_refresh_deposit(self):
        if not bool(self.settings.get("auto_dep_enabled", False)):
            return
        self._sync_deposit_from_exchange(manual=True)

    def _get_auto_dep_credentials(self, exchange_id):
        creds_map = self.get_auto_dep_credentials_plain()
        ex_creds = creds_map.get(str(exchange_id or "").strip().lower(), {})
        api_key = str(ex_creds.get("api_key", "") or "").strip()
        api_secret = str(ex_creds.get("api_secret", "") or "").strip()
        api_passphrase = str(ex_creds.get("api_passphrase", "") or "").strip()

        return api_key, api_secret, api_passphrase

    def _run_auto_dep_fetch(self, exchange_id, api_key, api_secret, market_type, asset, passphrase):
        try:
            balance = self._fetch_exchange_balance(
                exchange_id,
                api_key,
                api_secret,
                market_type,
                asset,
                passphrase,
            )
            self._auto_dep_signaler.fetch_finished.emit(balance, None)
        except Exception as exc:
            self._auto_dep_signaler.fetch_finished.emit(None, str(exc))

    def _on_auto_dep_fetch_finished(self, balance, error_message):
        try:
            if error_message:
                self._set_auto_dep_status("error", error_message)
                return

            if balance is None:
                self._set_auto_dep_status("error", "No balance value")
                return

            if hasattr(self, "inp_dep") and self.inp_dep is not None:
                new_text = self._format_deposit_input_value(balance)
                if (self.inp_dep.text() or "").strip() != new_text:
                    self.inp_dep.setText(new_text)
            self._set_auto_dep_status("ok")
        finally:
            self._auto_dep_sync_busy = False

    def _format_deposit_input_value(self, value):
        try:
            num = float(value)
        except Exception:
            num = 0.0

        # Максимум 2 знака после запятой для автозаполнения.
        text = f"{num:.2f}".rstrip("0").rstrip(".")
        if not text:
            text = "0"
        return text.replace(".", ",")

    def _fetch_exchange_balance(
        self,
        exchange_id,
        api_key,
        api_secret,
        market_type,
        asset,
        passphrase="",
    ):
        if exchange_id == "binance":
            return self._fetch_binance_balance_light(
                api_key,
                api_secret,
                market_type,
                asset,
            )

        return self._fetch_non_binance_balance_light(
            exchange_id,
            api_key,
            api_secret,
            market_type,
            asset,
            passphrase,
        )

    def _fetch_non_binance_balance_light(
        self,
        exchange_id,
        api_key,
        api_secret,
        market_type,
        asset,
        passphrase="",
    ):
        payload = {
            "exchange_id": exchange_id,
            "api_key": api_key,
            "api_secret": api_secret,
            "market_type": market_type,
            "asset": asset,
            "passphrase": passphrase,
        }

        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue(maxsize=1)
        worker = ctx.Process(
            target=_fetch_balance_with_ccxt_process,
            args=(payload, result_queue),
            daemon=True,
        )
        worker.start()
        worker.join(timeout=7.0)

        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=1.0)
            raise RuntimeError("Balance request timed out")

        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            raise RuntimeError("Empty balance response")
        finally:
            try:
                result_queue.close()
                result_queue.join_thread()
            except Exception:
                pass

        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", "Balance fetch failed")))

        return float(result.get("balance", 0.0) or 0.0)

    def _fetch_binance_balance_light(self, api_key, api_secret, market_type, asset):
        timestamp_ms = int(time.time() * 1000)
        params = {
            "timestamp": timestamp_ms,
            "recvWindow": 5000,
        }
        query = urlencode(params)
        signature = hmac.new(
            api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers = {"X-MBX-APIKEY": api_key}

        if market_type == "futures":
            url = f"https://fapi.binance.com/fapi/v2/account?{query}&signature={signature}"
            response = requests.get(url, headers=headers, timeout=4)
            response.raise_for_status()
            data = response.json()
            assets = data.get("assets", []) if isinstance(data, dict) else []
            for row in assets:
                if str(row.get("asset", "")).upper() == asset:
                    available = row.get("availableBalance", None)
                    if available is not None:
                        return float(available or 0.0)
                    return float(row.get("walletBalance", 0.0) or 0.0)
            return 0.0

        url = f"https://api.binance.com/api/v3/account?{query}&signature={signature}"
        response = requests.get(url, headers=headers, timeout=4)
        response.raise_for_status()
        data = response.json()
        balances = data.get("balances", []) if isinstance(data, dict) else []
        for row in balances:
            if str(row.get("asset", "")).upper() == asset:
                free_val = float(row.get("free", 0.0) or 0.0)
                locked_val = float(row.get("locked", 0.0) or 0.0)
                return free_val + locked_val
        return 0.0

    def _sync_deposit_from_exchange(self, manual=False):
        if self._auto_dep_sync_busy:
            return
        if not bool(self.settings.get("auto_dep_enabled", False)) and not manual:
            return
        if not hasattr(self, "inp_dep") or self.inp_dep is None:
            return
        if self.inp_dep.hasFocus() and not manual:
            return

        exchange_id = str(
            self.settings.get("auto_dep_exchange", "binance") or "binance"
        ).strip().lower()
        api_key, api_secret, api_passphrase = self._get_auto_dep_credentials(exchange_id)
        market_type = str(
            self.settings.get("auto_dep_market", "futures") or "futures"
        ).lower()
        asset = str(self.settings.get("auto_dep_asset", "USDT") or "USDT").strip().upper()

        if not api_key or not api_secret:
            self._set_auto_dep_status("error", "Empty API key/secret")
            return

        is_read_only, reason = self.validate_auto_dep_credentials_read_only(
            exchange_id,
            api_key,
            api_secret,
            market_type,
            api_passphrase,
            use_cache=True,
        )
        if not is_read_only:
            self._set_auto_dep_status("error", reason)
            return

        self._auto_dep_sync_busy = True
        self._set_auto_dep_status("loading")
        worker = threading.Thread(
            target=self._run_auto_dep_fetch,
            args=(
                exchange_id,
                api_key,
                api_secret,
                market_type,
                asset,
                api_passphrase,
            ),
            daemon=True,
        )
        worker.start()

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
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

        self._apply_terminal_mode()

        self.apply_min_order_precision()
        self.refresh_labels()
        self.apply_styles()
        QTimer.singleShot(0, self.finalize_startup_layout)

    def on_tab_changed(self, index):
        if index == 1 and not self._is_profit_forge_terminal():
            self.tabs.blockSignals(True)
            self.tabs.setCurrentIndex(0)
            self.tabs.blockSignals(False)
            return
        if index == 1 and hasattr(self, "tab_cascade"):
            self.tab_cascade.recalc_table()

    def _is_profit_forge_terminal(self):
        return (
            str(self.settings.get("auto_apply_terminal", "profit_forge") or "profit_forge")
            .strip()
            .lower()
            == "profit_forge"
        )

    def _is_tigertrade_terminal(self):
        return (
            str(self.settings.get("auto_apply_terminal", "profit_forge") or "profit_forge")
            .strip()
            .lower()
            == "tigertrade"
        )

    def _is_metascalp_terminal(self):
        return (
            str(self.settings.get("auto_apply_terminal", "profit_forge") or "profit_forge")
            .strip()
            .lower()
            == "metascalp"
        )

    def _is_surf_terminal(self):
        return (
            str(self.settings.get("auto_apply_terminal", "profit_forge") or "profit_forge")
            .strip()
            .lower()
            == "surf"
        )

    def _is_vataga_terminal(self):
        return (
            str(self.settings.get("auto_apply_terminal", "profit_forge") or "profit_forge")
            .strip()
            .lower()
            == "vataga"
        )

    def _menu_terminal_kind(self):
        if self._is_tigertrade_terminal():
            return "tiger"
        if self._is_surf_terminal():
            return "surf"
        if self._is_vataga_terminal():
            return "vataga"
        return None

    def _is_menu_terminal(self):
        return self._menu_terminal_kind() is not None

    def _get_menu_terminal_point_keys(self):
        kind = self._menu_terminal_kind()
        if kind == "tiger":
            return ("tiger_open_point", "tiger_close_point")
        if kind == "surf":
            return ("surf_open_point", "surf_accept_point")
        if kind == "vataga":
            return ("vataga_open_point", None)
        return (None, None)

    def _menu_terminal_requires_final_point(self):
        kind = self._menu_terminal_kind()
        return kind in ("tiger", "surf")

    def _get_active_calc_points_key(self):
        if self._is_tigertrade_terminal():
            return "calc_points_tigertrade"
        if self._is_surf_terminal():
            return "calc_points_surf"
        if self._is_vataga_terminal():
            return "calc_points_vataga"
        if self._is_metascalp_terminal():
            return "calc_points_metascalp"
        return "calc_points_profit_forge"

    def _get_active_calc_points(self):
        key = self._get_active_calc_points_key()
        points = self.settings.get(key, [])
        return points if isinstance(points, list) else []

    def _get_standard_volume_precision(self):
        try:
            precision = int(self.settings.get("prec_dep", 2))
        except Exception:
            precision = 2

        return max(0, min(6, precision))

    def _get_calc_volume_precision(self):
        if self._is_tigertrade_terminal():
            return 0

        return self._get_standard_volume_precision()

    def _scaled_pt(self, base_pt):
        try:
            ratio = self.settings.get("scale", self.base_scale) / float(self.base_scale)
        except Exception:
            ratio = 1.0
        return max(7, int(base_pt * ratio))

    def _scale_ratio(self):
        try:
            return self.settings.get("scale", self.base_scale) / float(self.base_scale)
        except Exception:
            return 1.0

    def _top_info_font_pt(self):
        return self._scaled_pt(8)

    def _position_hint_font_pt(self, base_pt=8):
        return self._scaled_pt(base_pt)

    def _position_hint_style(self, color="#888", base_pt=8, with_padding=False):
        style = f"color: {color}; font-size: {self._position_hint_font_pt(base_pt)}pt;"
        if with_padding:
            ratio = self._scale_ratio()
            pad_left = 0
            pad_right = max(6, int(8 * ratio))
            style += f" padding-left: {pad_left}px; padding-right: {pad_right}px;"
        return style

    def _volume_title_text(self):
        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        return str(t.get("vol", "")).upper()

    def _apply_volume_title_style(self, dimmed=False):
        if not hasattr(self, "lbl_vol_title"):
            return
        ratio = self._scale_ratio()
        font_pt = max(6, int(8 * ratio))
        margin_top = max(1, int(2 * ratio))
        color = "#FF9F0A" if not dimmed else "#555"
        self.lbl_vol_title.setText(self._volume_title_text())
        self.lbl_vol_title.setStyleSheet(
            f"color: {color}; font-size: {font_pt}pt; font-weight: 700; margin-top: {margin_top}px;"
        )

    def _animate_window_size(self, target_w, target_h, duration_ms=180):
        target_w = int(target_w)
        target_h = int(target_h)
        cur_w = int(self.width())
        cur_h = int(self.height())
        target_key = (target_w, target_h)

        if self._window_size_anim is not None and self._window_size_anim_target == target_key:
            return

        if cur_w == target_w and cur_h == target_h:
            self.setFixedSize(target_w, target_h)
            self._window_size_anim_target = None
            return

        if self._window_size_anim is not None:
            old_anim = self._window_size_anim
            self._window_size_anim = None
            self._window_size_anim_target = None
            try:
                old_anim.stop()
            except Exception:
                pass

        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(max(60, min(180, int(duration_ms))))
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _apply(progress):
            if self._window_size_anim is not anim:
                return
            k = float(progress)
            nw = int(cur_w + (target_w - cur_w) * k)
            nh = int(cur_h + (target_h - cur_h) * k)
            self.setFixedSize(nw, nh)

        def _finish():
            if self._window_size_anim is not anim:
                return
            self.setFixedSize(target_w, target_h)
            self._window_size_anim = None
            self._window_size_anim_target = None

        anim.valueChanged.connect(_apply)
        anim.finished.connect(_finish)
        self._window_size_anim = anim
        self._window_size_anim_target = target_key
        anim.start()

    def _set_window_size_with_extra_height(self, grow_only=False, smooth=False):
        self.adjustSize()
        size = self.sizeHint()
        try:
            ratio = self.settings.get("scale", self.base_scale) / float(self.base_scale)
        except Exception:
            ratio = 1.0
        extra_h = max(16, int(20 * ratio))
        target_w = int(size.width())
        target_h = int(size.height() + extra_h)

        if grow_only:
            target_w = max(int(self.width()), target_w)
            target_h = max(int(self.height()), target_h)

        try:
            screen = self.screen() or QApplication.primaryScreen()
            if screen is not None:
                available = screen.availableGeometry()
                if self.isVisible():
                    x = int(self.x())
                    y = int(self.y())
                    right_space = int(available.right()) - x + 1 - 6
                    bottom_space = int(available.bottom()) - y + 1 - 6
                    max_w = max(180, right_space)
                    max_h = max(160, bottom_space)
                else:
                    max_w = max(360, int(available.width()) - 12)
                    max_h = max(240, int(available.height()) - 12)
                target_w = min(target_w, max_w)
                target_h = min(target_h, max_h)
        except Exception:
            pass

        if smooth and self.isVisible():
            self._animate_window_size(target_w, target_h)
        else:
            self.setFixedSize(target_w, target_h)

    def _schedule_smooth_content_resize(self, force=False):
        if getattr(self, "_lock_dynamic_resize", False):
            return
        if force:
            self._force_resize_pending = True
        # Resize after a short pause, not on every keystroke.
        if hasattr(self, "_smooth_resize_idle_timer"):
            self._smooth_resize_idle_timer.start(80)
        else:
            self._apply_idle_smooth_resize()

    def _current_resize_pressure_chars(self):
        if not self._resize_len_baseline:
            return 0
        extra_chars = 0
        for name, base_len in self._resize_len_baseline.items():
            widget = getattr(self, name, None)
            if not widget:
                continue
            cur_len = len((widget.text() or "").strip())
            extra_chars = max(extra_chars, max(0, cur_len - int(base_len)))
        return int(extra_chars)

    def _apply_idle_smooth_resize(self):
        pressure = self._current_resize_pressure_chars()
        step = max(1, int(getattr(self, "_resize_step_chars", 5) or 1))

        force = bool(getattr(self, "_force_resize_pending", False))
        if force:
            self._force_resize_pending = False

        # Quantize pressure to step boundaries so window jumps only every N chars
        quantized = (pressure // step) * step
        last_quantized = (self._last_applied_resize_pressure // step) * step

        force_back_to_base = (
            pressure == 0 and self._last_applied_resize_pressure != 0
        )
        if (
            not force_back_to_base
            and quantized == last_quantized
        ):
            return

        self._last_applied_resize_pressure = pressure
        self._adapt_window_width_to_content(grow_only=False, smooth=True)

    def _set_active_calc_points(self, points):
        key = self._get_active_calc_points_key()
        self.settings[key] = list(points)

    def _reset_active_calc_calibration(self):
        self._set_active_calc_points([])
        if self._is_menu_terminal():
            open_key, close_key = self._get_menu_terminal_point_keys()
            if open_key:
                self.settings[open_key] = None
            if close_key:
                self.settings[close_key] = None
        self.save_settings()

    def _apply_terminal_mode(self):
        if not hasattr(self, "tabs"):
            return

        is_pf = self._is_profit_forge_terminal()
        if hasattr(self, "tab_cascade"):
            self.tab_cascade.setEnabled(is_pf)

        self.tabs.setTabEnabled(1, is_pf)

        if not is_pf and self.tabs.currentIndex() == 1:
            self.tabs.setCurrentIndex(0)

        if hasattr(self, "update_calc"):
            self.update_calc()
        if hasattr(self, "update_position_adjustment_info"):
            self.update_position_adjustment_info()
        if hasattr(self, "update_cell_volumes"):
            self.update_cell_volumes()

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
        self._apply_volume_title_style(
            dimmed=bool(self.settings.get("pos_mode_enabled", False))
        )
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
            self.lbl_pos_stop_title.setText(t["calc_stop_percent_entry"])
        if hasattr(self, "lbl_pos_stop_now_title"):
            self.lbl_pos_stop_now_title.setText(t["calc_stop_percent_now"])
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
        if hasattr(self, "btn_dep_refresh"):
            self.btn_dep_refresh.setText(t.get("dep_refresh", "↻"))
            self.btn_dep_refresh.setToolTip(
                t.get("dep_refresh_tip", "Обновить депозит с биржи")
            )
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
            p_vol = self._get_standard_volume_precision()
            p_lev = self.settings.get("prec_lev", 1)

            d = float(self.inp_dep.text().replace(",", ".") or 0)
            r = float(self.inp_risk.text().replace(",", ".") or 0)
            s = float(self.inp_stop.text().replace(",", ".") or 0)

            f_perc, use_fee = self._get_effective_fee_percent()
            cash_risk, vol, lev, comm_usd = calculate_risk_data(d, r, s, f_perc)

            self.current_vol = vol
            # Форматирование депозита с сокращениями
            hint_text = self.format_hint_no_decimals(d)
            self.lbl_hint.setText(hint_text)

            vol_str = f"{vol:,.{p_vol}f}".replace(",", " ").replace(".", ",")
            self.lbl_vol.setText(vol_str)

            t = TRANS[self.settings.get("lang", "ru")]
            dimmed = self.settings.get("pos_mode_enabled", False)
            info_font_pt = self._top_info_font_pt()
            self.lbl_info.setText(
                get_info_html(
                    cash_risk,
                    lev,
                    comm_usd,
                    t,
                    p_risk,
                    p_fee,
                    p_lev,
                    font_size=info_font_pt,
                    dimmed=dimmed,
                    fee_enabled=use_fee,
                )
            )
            self._update_risk_recommendation(r, s, lev, use_fee)

            # Обновляем объемы в таблице ячеек
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()

            sc = self.settings.get("scale", 100) / 100.0
            color = "#FF3B30" if r >= 10.0 else "#FF9F0A"
            if self.settings.get("pos_mode_enabled", False):
                self.lbl_vol.setStyleSheet(
                    "color: #555; font-size: 11pt; font-weight: bold; border: 1px solid #222; "
                    "border-radius: 4px; padding: 4px; background: #0F0F0F;"
                )
            else:
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
            self._schedule_smooth_content_resize()

            self.settings.update({"deposit": d, "risk": r, "stop": s})
            self.save_settings()
        except Exception as e:
            print(f"Error: {e}")

    def _get_effective_fee_percent(self):
        use_fee = bool(self.settings.get("use_fee", True))
        if not use_fee:
            return 0.0, False

        try:
            fee_taker = float(self.settings.get("fee_taker", 0.0) or 0.0)
        except Exception:
            fee_taker = 0.0

        try:
            fee_maker = float(self.settings.get("fee_maker", 0.0) or 0.0)
        except Exception:
            fee_maker = 0.0

        fee_taker = max(0.0, fee_taker)
        fee_maker = max(0.0, fee_maker)
        return fee_taker + fee_maker, True

    def _build_risk_warning_text(self, risk_percent, stop_percent, leverage, use_fee):
        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        warnings = []

        try:
            risk_value = float(risk_percent)
        except Exception:
            risk_value = 0.0

        try:
            stop_value = float(stop_percent)
        except Exception:
            stop_value = 0.0

        try:
            lev_value = float(leverage)
        except Exception:
            lev_value = 0.0

        fee_total = 0.0
        if bool(use_fee):
            try:
                fee_total = float(self.settings.get("fee_taker", 0.0)) + float(
                    self.settings.get("fee_maker", 0.0)
                )
            except Exception:
                fee_total = 0.0
        effective_stop = abs(max(0.0, stop_value + fee_total))

        if risk_value >= 10.0:
            warnings.append(t["risk_warn_high"])
            target_risk = min(5.0, max(1.0, risk_value / 2.0))
            target_text = f"{target_risk:.2f}".rstrip("0").rstrip(".")
            warnings.append(t["risk_warn_reduce"].format(target=target_text))

        liq_move_est = abs(100.0 / lev_value) if lev_value > 0 else 0.0
        liq_warn_threshold = liq_move_est * 0.95
        if liq_move_est > 0 and effective_stop >= liq_warn_threshold:
            liq_text = f"{liq_move_est:.2f}".rstrip("0").rstrip(".")
            warnings.append(t["risk_warn_liq"].format(liq=liq_text))

        if (not bool(use_fee)) and risk_value >= 10.0:
            warnings.append(t["risk_warn_fee_off"])

        if warnings:
            intro = t.get("risk_warn_intro", "⚠")
            return f"{intro}  " + "  ".join(warnings)

        return ""

    def _update_risk_recommendation(self, risk_percent, stop_percent, leverage, use_fee):
        if not hasattr(self, "lbl_risk_warning"):
            return

        warning_text = self._build_risk_warning_text(
            risk_percent, stop_percent, leverage, use_fee
        )
        try:
            risk_value = float(risk_percent)
        except Exception:
            risk_value = 0.0
        warn_pt = self._scaled_pt(8.8 if risk_value >= 10.0 else 7.5)
        self.lbl_risk_warning.setStyleSheet(f"color: #FF6B6B; font-size: {warn_pt}pt;")
        if warning_text:
            self.lbl_risk_warning.setText(warning_text)
            self.lbl_risk_warning.setVisible(True)
        else:
            self.lbl_risk_warning.setText("")
            self.lbl_risk_warning.setVisible(False)

    def _update_position_risk_recommendation(
        self, risk_percent, stop_percent, leverage, use_fee
    ):
        if not hasattr(self, "lbl_pos_warning"):
            return

        warning_text = self._build_risk_warning_text(
            risk_percent, stop_percent, leverage, use_fee
        )
        try:
            risk_value = float(risk_percent)
        except Exception:
            risk_value = 0.0
        warn_pt = self._scaled_pt(8.8 if risk_value >= 10.0 else 7.5)
        self.lbl_pos_warning.setStyleSheet(f"color: #FF6B6B; font-size: {warn_pt}pt;")
        if warning_text:
            self.lbl_pos_warning.setText(warning_text)
            self.lbl_pos_warning.setVisible(True)
        else:
            self.lbl_pos_warning.setText("")
            self.lbl_pos_warning.setVisible(False)

    def _build_position_risk_cash_html(
        self,
        target_risk_cash_text,
        current_risk_cash_text="",
        current_risk_pct_text="",
    ):
        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        font_pt = self._position_hint_font_pt(8)
        label_color = "#FFFFFF"
        risk_value_color = "#FF453A"
        current_risk_value_color = "#FF453A"
        sep_color = "#666"

        risk_label = t.get("pos_risk_cash_label", "Риск сделки в $:")
        current_risk_label = t.get("pos_current_risk_label", "Текущий риск:")

        if current_risk_cash_text:
            current_risk_right = f"${current_risk_cash_text}"
            if current_risk_pct_text:
                current_risk_right += f" ({current_risk_pct_text}%)"
            left_html = (
                f"<span style='color: {label_color}; font-size: {font_pt}pt;'>{risk_label} </span>"
                f"<b style='color: {risk_value_color}; font-size: {font_pt}pt;'>${target_risk_cash_text}</b>"
                f"<span style='color: {sep_color};'>  |  </span>"
                f"<span style='color: {label_color}; font-size: {font_pt}pt;'>{current_risk_label} </span>"
                f"<b style='color: {current_risk_value_color}; font-size: {font_pt}pt;'>{current_risk_right}</b>"
            )
        else:
            left_html = (
                f"<span style='color: {label_color}; font-size: {font_pt}pt;'>{risk_label} </span>"
                f"<b style='color: {risk_value_color}; font-size: {font_pt}pt;'>${target_risk_cash_text}</b>"
            )

        return (
            "<div style='line-height: 120%; white-space: nowrap;'>"
            f"{left_html}"
            "</div>"
        )

    def _set_position_action_chip(self, action=None, delta_text=""):
        if not hasattr(self, "lbl_pos_action_chip"):
            return

        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        ratio = self._scale_ratio()
        font_pt = self._position_hint_font_pt(8)
        border_radius = max(3, int(3 * ratio))
        pad_h = max(3, int(4 * ratio))

        if action == "add":
            label = t.get("pos_add_label", "Добор:")
            color = "#38BE1D"
        elif action == "reduce":
            label = t.get("pos_reduce_label", "Сокращение:")
            color = "#FF453A"
        else:
            self.lbl_pos_action_chip.setText("")
            self.lbl_pos_action_chip.setVisible(False)
            return

        self.lbl_pos_action_chip.setText(f"{label} {delta_text}")
        self.lbl_pos_action_chip.setStyleSheet(
            f"color: {color}; font-size: {font_pt}pt; border: 1px solid {color}; "
            f"border-radius: {border_radius}px; padding: 0px {pad_h}px;"
        )
        self.lbl_pos_action_chip.setVisible(True)

    def _build_position_target_html(self, target_vol_text, target_lev_text):
        t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
        font_pt = self._position_hint_font_pt(8)
        label_color = "#FFFFFF"
        target_value_color = "#FF9F0A"
        leverage_value_color = "#B388FF"
        sep_color = "#666"

        target_label = t.get("pos_target_label", "Целевой объём:")
        leverage_label = t.get("lev", "Плечо:")

        return (
            "<div style='line-height: 120%; white-space: nowrap;'>"
            f"<span style='color: {label_color}; font-size: {font_pt}pt;'>{target_label} </span>"
            f"<b style='color: {target_value_color}; font-size: {font_pt}pt;'>{target_vol_text}</b>"
            f"<span style='color: {sep_color};'>  |  </span>"
            f"<span style='color: {label_color}; font-size: {font_pt}pt;'>{leverage_label} </span>"
            f"<b style='color: {leverage_value_color}; font-size: {font_pt}pt;'>{target_lev_text}x</b>"
            "</div>"
        )

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
            self.lbl_pos_adjust.setStyleSheet(
                self._position_hint_style("#555", base_pt=7)
            )
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_na"])
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style("#555", base_pt=7, with_padding=True)
                )
            self._set_position_action_chip(None)
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "lbl_pos_warning"):
                self.lbl_pos_warning.setText("")
                self.lbl_pos_warning.setVisible(False)
            if hasattr(self, "lbl_pos_stop_delta"):
                self.lbl_pos_stop_delta.setText("")
                self.lbl_pos_stop_delta.setVisible(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            return

        self.pos_adjust_delta = 0.0
        self.pos_adjust_action = None

        p_vol = self._get_standard_volume_precision()
        p_adjust_vol = self._get_calc_volume_precision()
        p_risk = self.settings.get("prec_risk", 2)
        p_lev = self.settings.get("prec_lev", 1)

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

        try:
            pos_stop_now = float(self.inp_pos_stop_now.text().replace(",", ".") or 0)
        except Exception:
            pos_stop_now = 0.0

        try:
            deposit = float(self.inp_dep.text().replace(",", ".") or 0)
        except Exception:
            deposit = 0.0

        pos_vol = max(0.0, float(pos_vol))

        if pos_risk <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t["pos_rec_risk"])
            self.lbl_pos_adjust.setStyleSheet(
                self._position_hint_style("#888", base_pt=7)
            )
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_need"])
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style("#888", base_pt=8, with_padding=True)
                )
            self._set_position_action_chip(None)
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            self.settings["pos_current_vol"] = self.inp_pos_vol.text()
            self.settings["pos_risk"] = self.inp_pos_risk.text()
            self.settings["pos_stop"] = self.inp_pos_stop.text()
            self.settings["pos_stop_now"] = self.inp_pos_stop_now.text()
            self.save_settings()
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            if hasattr(self, "lbl_pos_stop_delta"):
                self.lbl_pos_stop_delta.setText("")
                self.lbl_pos_stop_delta.setVisible(False)
            if hasattr(self, "lbl_pos_warning"):
                self.lbl_pos_warning.setText("")
                self.lbl_pos_warning.setVisible(False)
            return

        if pos_stop <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t.get("pos_rec_stop_entry", t["pos_rec_stop"]))
            self.lbl_pos_adjust.setStyleSheet(
                self._position_hint_style("#888", base_pt=7)
            )
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_need"])
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style("#888", base_pt=8, with_padding=True)
                )
            self._set_position_action_chip(None)
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            if hasattr(self, "lbl_pos_stop_delta"):
                self.lbl_pos_stop_delta.setText("")
                self.lbl_pos_stop_delta.setVisible(False)
            if hasattr(self, "lbl_pos_warning"):
                self.lbl_pos_warning.setText("")
                self.lbl_pos_warning.setVisible(False)
            return

        if pos_stop_now <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t.get("pos_rec_stop_now", t["pos_rec_stop"]))
            self.lbl_pos_adjust.setStyleSheet(
                self._position_hint_style("#888", base_pt=7)
            )
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_need"])
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style("#888", base_pt=8, with_padding=True)
                )
            self._set_position_action_chip(None)
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            if hasattr(self, "lbl_pos_stop_delta"):
                self.lbl_pos_stop_delta.setText("")
                self.lbl_pos_stop_delta.setVisible(False)
            if hasattr(self, "lbl_pos_warning"):
                self.lbl_pos_warning.setText("")
                self.lbl_pos_warning.setVisible(False)
            return

        f_perc, use_fee = self._get_effective_fee_percent()

        if deposit <= 0:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t.get("pos_need_deposit", "Укажите депозит"))
            self.lbl_pos_adjust.setStyleSheet(
                self._position_hint_style("#888", base_pt=7)
            )
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_need"])
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style("#888", base_pt=8, with_padding=True)
                )
            self._set_position_action_chip(None)
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            if hasattr(self, "lbl_pos_warning"):
                self.lbl_pos_warning.setText("")
                self.lbl_pos_warning.setVisible(False)
            return

        tolerance = max(1e-9, 10 ** (-(max(0, int(p_risk)) + 1)))

        # Deterministic in-position model:
        # - current risk is estimated by entry->stop distance
        # - add sizing is estimated by current->stop distance
        # - reduce sizing cuts existing position risk profile
        try:
            pos_calc = calculate_position_adjustment(
                deposit=deposit,
                target_risk_percent=pos_risk,
                current_volume=pos_vol,
                stop_entry_percent=pos_stop,
                stop_now_percent=pos_stop_now,
                fee_percent=f_perc,
                tolerance_cash=tolerance,
            )
        except Exception:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_pos_adjust.setText(t["pos_calc_error"])
            self.lbl_pos_adjust.setStyleSheet(
                self._position_hint_style("#FF9F0A", base_pt=7)
            )
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(t["pos_risk_cash_need"])
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style("#888", base_pt=8, with_padding=True)
                )
            self._set_position_action_chip(None)
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)
            if hasattr(self, "cells_table"):
                self.update_cell_volumes()
            if hasattr(self, "lbl_pos_warning"):
                self.lbl_pos_warning.setText("")
                self.lbl_pos_warning.setVisible(False)
            return

        risk_cash = float(pos_calc.get("target_risk_cash", 0.0) or 0.0)
        current_risk_cash = float(pos_calc.get("current_risk_cash", 0.0) or 0.0)
        current_risk_percent = float(pos_calc.get("current_risk_percent", 0.0) or 0.0)
        max_vol_at_stop = float(pos_calc.get("target_volume", 0.0) or 0.0)
        action = str(pos_calc.get("action", "in_limit") or "in_limit")
        delta_abs = float(pos_calc.get("delta_abs", 0.0) or 0.0)

        risk_cash_text = f"{risk_cash:,.{p_risk}f}".replace(",", " ").replace(".", ",")
        current_risk_cash_text = f"{current_risk_cash:,.{p_risk}f}".replace(",", " ").replace(".", ",")
        current_risk_pct_text = (
            f"{current_risk_percent:,.2f}".replace(",", " ").replace(".", ",")
        )

        self.position_target_volume = float(max_vol_at_stop)
        target_vol_text = f"{max_vol_at_stop:,.{p_vol}f}".replace(",", " ").replace(
            ".", ","
        )
        target_lev = (max_vol_at_stop / deposit) if deposit > 0 else 0.0
        target_lev_text = f"{target_lev:,.{p_lev}f}".replace(",", " ").replace(
            ".", ","
        )
        target_with_lev_text = self._build_position_target_html(
            target_vol_text, target_lev_text
        )
        self._update_position_risk_recommendation(
            pos_risk, pos_stop_now, target_lev, use_fee
        )

        if hasattr(self, "lbl_pos_stop_delta"):
            if pos_stop > 0:
                entry_text = f"{pos_stop:.2f}".rstrip("0").rstrip(".").replace(".", ",")
                now_text = f"{pos_stop_now:.2f}".rstrip("0").rstrip(".").replace(".", ",")
                delta_stop = abs(float(pos_stop_now) - float(pos_stop))
                delta_text = f"{delta_stop:.2f}".rstrip("0").rstrip(".").replace(".", ",")
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_pos_stop_delta.setText(
                    t.get(
                        "pos_stop_delta",
                        "Дистанция до стопа: средняя {entry}% | текущая {now}% | разница {delta}%",
                    ).format(entry=entry_text, now=now_text, delta=delta_text)
                )
                self.lbl_pos_stop_delta.setVisible(True)
            else:
                self.lbl_pos_stop_delta.setText("")
                self.lbl_pos_stop_delta.setVisible(False)

        if action == "add":
            self.pos_adjust_delta = float(delta_abs)
            self.pos_adjust_action = "add"
            delta_text = f"{delta_abs:,.{p_adjust_vol}f}".replace(",", " ").replace(".", ",")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    self._build_position_risk_cash_html(
                        risk_cash_text,
                        current_risk_cash_text,
                        current_risk_pct_text,
                    )
                )
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style(with_padding=True)
                )
            self._set_position_action_chip("add", delta_text)
            self.lbl_pos_adjust.setText(target_with_lev_text)
            self.lbl_pos_adjust.setStyleSheet(self._position_hint_style())
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(True)
        elif action == "reduce":
            self.pos_adjust_delta = float(delta_abs)
            self.pos_adjust_action = "reduce"
            delta_text = f"{delta_abs:,.{p_adjust_vol}f}".replace(",", " ").replace(".", ",")
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    self._build_position_risk_cash_html(
                        risk_cash_text,
                        current_risk_cash_text,
                        current_risk_pct_text,
                    )
                )
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style(with_padding=True)
                )
            self._set_position_action_chip("reduce", delta_text)
            self.lbl_pos_adjust.setText(target_with_lev_text)
            self.lbl_pos_adjust.setStyleSheet(self._position_hint_style())
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(True)
        else:
            self.pos_adjust_delta = 0.0
            self.pos_adjust_action = None
            if hasattr(self, "lbl_pos_risk_cash"):
                self.lbl_pos_risk_cash.setText(
                    self._build_position_risk_cash_html(
                        risk_cash_text,
                        current_risk_cash_text,
                        current_risk_pct_text,
                    )
                )
                self.lbl_pos_risk_cash.setStyleSheet(
                    self._position_hint_style(with_padding=True)
                )
            self._set_position_action_chip(None)
            self.lbl_pos_adjust.setText(target_with_lev_text)
            self.lbl_pos_adjust.setStyleSheet(self._position_hint_style())
            if hasattr(self, "btn_move_adjust_to_cell"):
                self.btn_move_adjust_to_cell.setEnabled(False)

        self.settings["pos_current_vol"] = self.inp_pos_vol.text()
        self.settings["pos_risk"] = self.inp_pos_risk.text()
        self.settings["pos_stop"] = self.inp_pos_stop.text()
        self.settings["pos_stop_now"] = self.inp_pos_stop_now.text()
        self.save_settings()

        if hasattr(self, "cells_table"):
            self.update_cell_volumes()

        self._schedule_smooth_content_resize(force=True)

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
                            "QLineEdit { background: #1A1A1A; color: white; border: 1px solid #252525; padding: 3px; border-radius: 4px; font-size: 9pt; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }"
                            "QLineEdit:focus { border: 1px solid #FFFFFF; }"
                        )
                elif isinstance(widget, QLabel):
                    if dim:
                        if name == "lbl_vol_title":
                            self._apply_volume_title_style(dimmed=True)
                            continue
                        if name == "lbl_vol":
                            widget.setStyleSheet(
                                "color: #555; font-size: 11pt; font-weight: bold; border: 1px solid #222; "
                                "border-radius: 4px; padding: 4px; background: #0F0F0F;"
                            )
                            continue
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
                            self._apply_volume_title_style(dimmed=False)
                            continue
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
                            widget.setStyleSheet(
                                "color: #FF9F0A; font-size: 11pt; font-weight: bold; border: 1px solid #333; "
                                "border-radius: 4px; padding: 4px; background: #1A1A1A;"
                            )

    def on_position_mode_toggled(self, checked, is_startup=False):
        enabled = bool(checked)
        self.settings["pos_mode_enabled"] = enabled

        # Сохраняем текущий размер окна перед изменениями
        if not is_startup:
            current_size = self.size()
            self._lock_dynamic_resize = True

        pos_controls = []
        for name in (
            "inp_pos_vol",
            "inp_pos_risk",
            "inp_pos_stop",
            "inp_pos_stop_now",
            "lbl_pos_vol_title",
            "lbl_pos_risk_title",
            "lbl_pos_stop_title",
            "lbl_pos_stop_now_title",
            "btn_move_adjust_to_cell",
            "lbl_pos_vol_hint",
            "lbl_pos_risk_cash",
            "lbl_pos_action_chip",
            "lbl_pos_adjust",
            "lbl_pos_stop_delta",
            "lbl_pos_warning",
        ):
            widget = getattr(self, name, None)
            if widget:
                pos_controls.append(widget)

        if enabled and not is_startup:
            # Сохраняем выбранный пользователем тип распределения без принудительной смены.
            # Automatically apply position adjustment
            if hasattr(self, "apply_position_adjustment_to_cell"):
                self.apply_position_adjustment_to_cell()
        elif not enabled and not is_startup:
            # User disabled position mode.
            self.table_volume_override = 0.0
            self.settings["pos_table_volume_override"] = 0.0
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

        dim_opacity = 1.0 if enabled else 0.35
        for widget in pos_controls:
            if enabled:
                widget.setGraphicsEffect(None)
            else:
                fx = QGraphicsOpacityEffect(widget)
                fx.setOpacity(dim_opacity)
                widget.setGraphicsEffect(fx)

        if hasattr(self, "pos_target_cell_buttons"):
            for btn in self.pos_target_cell_buttons:
                btn.setEnabled(enabled)
                if not enabled:
                    btn.setChecked(False)
                if enabled:
                    btn.setGraphicsEffect(None)
                else:
                    fx = QGraphicsOpacityEffect(btn)
                    fx.setOpacity(dim_opacity)
                    btn.setGraphicsEffect(fx)

            if enabled:
                selected_cell = int(self.settings.get("pos_target_cell", 1) or 1)
                selected_cell = max(1, min(5, selected_cell))
                for idx, btn in enumerate(self.pos_target_cell_buttons, start=1):
                    btn.setChecked(idx == selected_cell)

        if hasattr(self, "lbl_pos_vol_hint"):
            self.lbl_pos_vol_hint.setStyleSheet(
                self._position_hint_style("#666", base_pt=8)
                if enabled
                else self._position_hint_style("#555", base_pt=8)
            )
        if hasattr(self, "lbl_pos_vol_title"):
            self.lbl_pos_vol_title.setStyleSheet(
                f"color: {'#888' if enabled else '#555'}; font-size: {self._scaled_pt(8)}pt;"
            )
        if hasattr(self, "lbl_pos_risk_cash"):
            self.lbl_pos_risk_cash.setStyleSheet(
                self._position_hint_style("#888", base_pt=8, with_padding=True)
                if enabled
                else self._position_hint_style("#555", base_pt=8, with_padding=True)
            )
        if hasattr(self, "lbl_pos_action_chip"):
            if enabled and self.lbl_pos_action_chip.isVisible():
                # Keep current chip color/border that is set by action state.
                pass
            elif not enabled:
                self.lbl_pos_action_chip.setVisible(False)
        if hasattr(self, "lbl_pos_adjust"):
            self.lbl_pos_adjust.setStyleSheet(
                "color: #888; font-size: 8pt;"
                if enabled
                else "color: #555; font-size: 8pt;"
            )
        if hasattr(self, "lbl_pos_warning"):
            self.lbl_pos_warning.setStyleSheet(
                "color: #FF6B6B; font-size: 7pt;"
                if enabled
                else "color: #555; font-size: 7pt;"
            )

        self._set_position_target_row_mask(None)
        self.update_position_adjustment_info()

        # Восстанавливаем исходный размер окна, чтобы избежать "прыжков"
        if not is_startup:
            if isinstance(self._startup_window_size, tuple) and len(self._startup_window_size) == 2:
                self.setFixedSize(int(self._startup_window_size[0]), int(self._startup_window_size[1]))
            else:
                self.setFixedSize(current_size)
            QTimer.singleShot(120, lambda: setattr(self, "_lock_dynamic_resize", False))

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

    def _adapt_window_width_to_content(self, grow_only=False, smooth=False):
        if getattr(self, "_lock_dynamic_resize", False):
            return
        if not self.isVisible():
            return

        def _metric_text(raw_text):
            import re

            if not raw_text:
                return ""
            text = str(raw_text)
            text = re.sub(r"<[^>]*>", "", text)
            text = text.replace("&nbsp;", " ")
            text = text.replace("&amp;", "&")
            text = text.replace("&lt;", "<")
            text = text.replace("&gt;", ">")
            return text

        scale = self.settings.get("scale", self.base_scale)
        ratio = scale / float(self.base_scale)
        base_w = max(90, int(105 * ratio))
        max_w = max(280, int(560 * ratio))

        for name in (
            "inp_dep",
            "inp_risk",
            "inp_stop",
            "inp_pos_vol",
            "inp_pos_risk",
            "inp_pos_stop",
            "inp_pos_stop_now",
            "inp_min_order",
        ):
            widget = getattr(self, name, None)
            if not widget:
                continue

            try:
                text = widget.text() if widget.text() else "0"
                desired = widget.fontMetrics().horizontalAdvance(text + " 000") + 18
                desired_w = max(base_w, min(max_w, desired))
                if grow_only:
                    desired_w = max(int(widget.minimumWidth()), desired_w)
                widget.setMinimumWidth(desired_w)
            except Exception:
                pass

        label_base_w = max(140, int(180 * ratio))
        label_max_w = max(380, int(980 * ratio))
        for name in (
            "lbl_info",
            "lbl_status",
            "lbl_hint",
            "lbl_pos_risk_cash",
            "lbl_pos_adjust",
        ):
            label = getattr(self, name, None)
            if not label:
                continue
            try:
                text = _metric_text(label.text())
                desired = label.fontMetrics().horizontalAdvance(text) + 22
                desired_w = max(label_base_w, min(label_max_w, desired))
                if grow_only:
                    desired_w = max(int(label.minimumWidth()), desired_w)
                label.setMinimumWidth(desired_w)
            except Exception:
                pass

        pos_vol_hint = getattr(self, "lbl_pos_vol_hint", None)
        if pos_vol_hint:
            try:
                text = _metric_text(pos_vol_hint.text())
                desired = pos_vol_hint.fontMetrics().horizontalAdvance(text) + 10
                desired_w = max(20, min(max(80, int(120 * ratio)), desired))
                if grow_only:
                    desired_w = max(int(pos_vol_hint.minimumWidth()), desired_w)
                pos_vol_hint.setMinimumWidth(desired_w)
            except Exception:
                pass

        # Автоподбор минимальной ширины окна: чтобы подсказки в блоке позиции
        # гарантированно помещались по ширине и не "наезжали" визуально.
        try:
            row1_width = 0
            for name in ("lbl_pos_vol_hint", "lbl_pos_risk_cash"):
                label = getattr(self, name, None)
                if label:
                    row1_width += (
                        label.fontMetrics().horizontalAdvance(
                            _metric_text(label.text())
                        )
                        + 24
                    )

            row2_width = 0
            label_adjust = getattr(self, "lbl_pos_adjust", None)
            if label_adjust:
                row2_width = (
                    label_adjust.fontMetrics().horizontalAdvance(
                        _metric_text(label_adjust.text())
                    )
                    + 24
                )

            hints_required = max(row1_width + int(18 * ratio), row2_width)
            base_min_window = max(620, int(620 * ratio))
            target_min_window = max(base_min_window, hints_required + int(90 * ratio))
            target_min_window = min(target_min_window, max(980, int(1450 * ratio)))

            if smooth:
                char_step_px = max(3, int(5 * ratio))
                extra_chars = self._current_resize_pressure_chars()
                step = max(1, int(getattr(self, "_resize_step_chars", 5) or 1))
                quantized = (extra_chars // step) * step
                target_min_window += quantized * char_step_px

            if grow_only:
                target_min_window = max(int(self.minimumWidth()), int(target_min_window))
            self.setMinimumWidth(int(target_min_window))
        except Exception:
            pass

        self._set_window_size_with_extra_height(grow_only=grow_only, smooth=smooth)

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
        # Compress padding growth for large scales to avoid oversized inner gaps.
        pad_ratio = 1.0 + max(0.0, ratio - 1.0) * 0.55
        pad_main = max(1, int(3 * pad_ratio))
        combo_pad = max(1, int(3 * pad_ratio))
        table_header_pad = max(2, int(4 * pad_ratio))
        table_item_pad = max(2, int(5 * pad_ratio))
        table_edit_pad = max(1, int(3 * pad_ratio))
        radius_main = max(4, int(6 * ratio))
        self.central_widget.setStyleSheet(
            f"""
            QWidget#Root {{ background: #121212; border: 2px solid #333; border-radius: {int(12*ratio)}px; }}
            QLineEdit {{ background: #1A1A1A; color: white; border: 1px solid #252525; padding: {pad_main}px; border-radius: {radius_main}px; font-size: {input_font}pt; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }}
            QLineEdit:disabled {{ background: #0F0F0F; color: #555; border: 1px solid #222; }}
            QLineEdit:focus {{ border: 1px solid #FFFFFF; }}
            QLabel {{ color: #888; border: none; font-size: {max(6, f_main-2)}pt; }}
            QPushButton#HeadBtn {{ color: #555; border: none; background: transparent; font-size: {f_main}pt; font-weight: bold; }}
            QPushButton#HeadBtn:hover {{ color: #38BE1D; }}
            QPushButton {{ background: #333; color: #9A9A9A; border: 1px solid #444; border-radius: {max(4, int(4*ratio))}px; font-weight: bold; }}
            QPushButton:disabled {{ background: #0F0F0F; color: #555; border: 1px solid #222; }}
            QPushButton:hover {{ background: #444; border-color: #38BE1D; }}
            QPushButton:pressed {{ background: #38BE1D; color: black; }}
            QComboBox, QSpinBox, QDoubleSpinBox {{ background: #1A1A1A; color: white; border: 1px solid #333; padding: {combo_pad}px; border-radius: {max(4, int(4*ratio))}px; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }}
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
            self.inp_dep.setStyleSheet(
                f"QLineEdit {{ background: #1A1A1A; color: white; border: 1px solid #252525; padding: {pad_main}px; border-radius: {radius_main}px; font-size: {input_font}pt; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }}"
                "QLineEdit:focus { border: 1px solid #FFFFFF; }"
            )
        if hasattr(self, "inp_risk"):
            self.inp_risk.setFixedHeight(input_height)
            self.inp_risk.setStyleSheet(
                f"QLineEdit {{ background: #1A1A1A; color: white; border: 1px solid #252525; padding: {pad_main}px; border-radius: {radius_main}px; font-size: {input_font}pt; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }}"
                "QLineEdit:focus { border: 1px solid #FFFFFF; }"
            )
        if hasattr(self, "inp_stop"):
            self.inp_stop.setFixedHeight(input_height)
            self.inp_stop.setStyleSheet(
                f"QLineEdit {{ background: #1A1A1A; color: white; border: 1px solid #252525; padding: {pad_main}px; border-radius: {radius_main}px; font-size: {input_font}pt; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }}"
                "QLineEdit:focus { border: 1px solid #FFFFFF; }"
            )
        if hasattr(self, "lbl_vol"):
            self.lbl_vol.setFixedHeight(max(24, int(36 * ratio)))
        self._apply_volume_title_style(
            dimmed=bool(self.settings.get("pos_mode_enabled", False))
        )

        if hasattr(self, "cb_distribution"):
            self.cb_distribution.setStyleSheet(
                f"""
                QComboBox {{ background: #1A1A1A; color: white; border: 1px solid #333; padding: {combo_pad}px; border-radius: {max(4, int(4*ratio))}px; font-size: {f_small}pt; }}
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
                QTabBar::tab:disabled {{ background: #0F0F0F; color: #444; border: 1px solid #222; }}
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
                    padding: {table_header_pad}px;
                    font-size: {f_small}pt;
                }}
                QTableWidget::item {{
                    padding: {table_item_pad}px;
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
                    padding: {table_edit_pad}px;
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
                    f"QCheckBox#PosModeToggle {{ font-size: {f_small}pt; spacing: 5px; margin: 0px; padding: 0px; background: transparent; border: none; }}"
                    "QCheckBox#PosModeToggle:checked { color: #AAA; }"
                    "QCheckBox#PosModeToggle:unchecked { color: #666; }"
                    "QCheckBox#PosModeToggle::indicator { width: 14px; height: 14px; border-radius: 3px; margin-right: 6px; }"
                    f"QCheckBox#PosModeToggle::indicator:checked {{ background: #38BE1D; border: 1px solid #38BE1D; image: url({self._posmode_checkmark_path_css}); }}"
                    "QCheckBox#PosModeToggle::indicator:unchecked { background: #2A2A2A; border: 1px solid #444; image: none; }"
                )
            )

        pos_lbl_pt = max(7, int(8 * ratio))
        pos_input_pt = max(7, int(8 * ratio))
        pos_hint_pt = max(7, int(8 * ratio))
        pos_input_h = max(20, int(22 * ratio))

        for name in (
            "lbl_pos_vol_title",
            "lbl_pos_risk_title",
            "lbl_pos_stop_title",
            "lbl_pos_stop_now_title",
            "lbl_min_order_title",
            "lbl_calc_type_title",
        ):
            widget = getattr(self, name, None)
            if widget:
                if name == "lbl_pos_vol_title":
                    pos_enabled = bool(self.settings.get("pos_mode_enabled", False))
                    color = "#888" if pos_enabled else "#555"
                    widget.setStyleSheet(f"color: {color}; font-size: {pos_lbl_pt}pt;")
                else:
                    widget.setStyleSheet(f"font-size: {pos_lbl_pt}pt;")

        for name in ("inp_pos_vol", "inp_pos_risk", "inp_pos_stop", "inp_pos_stop_now", "inp_min_order"):
            widget = getattr(self, name, None)
            if widget:
                widget.setFixedHeight(pos_input_h)
                widget.setStyleSheet(
                    f"QLineEdit {{ background: #1A1A1A; color: white; border: 1px solid #252525; border-radius: {max(4, int(4 * ratio))}px; font-size: {pos_input_pt}pt; padding: {max(1, int(1 * ratio))}px; selection-background-color: rgba(90, 205, 80, 150); selection-color: white; }}"
                    "QLineEdit:focus { border: 1px solid #FFFFFF; }"
                )

        for name in ("lbl_pos_vol_hint", "lbl_pos_risk_cash", "lbl_pos_adjust", "lbl_pos_stop_delta"):
            widget = getattr(self, name, None)
            if widget:
                color = "#888"
                if name == "lbl_pos_vol_hint":
                    color = "#666"
                elif name == "lbl_pos_stop_delta":
                    color = "#777"
                if name == "lbl_pos_risk_cash":
                    widget.setStyleSheet(
                        self._position_hint_style(color, base_pt=8, with_padding=True)
                    )
                else:
                    widget.setStyleSheet(f"color: {color}; font-size: {pos_hint_pt}pt;")

        for name in ("btn_reverse_cells", "btn_move_adjust_to_cell", "btn_toggle_all_cells"):
            widget = getattr(self, name, None)
            if widget:
                widget.setFixedSize(max(28, int(34 * ratio)), max(22, int(25 * ratio)))

        if hasattr(self, "lbl_status"):
            self.lbl_status.setStyleSheet(f"color: #666; font-size: {self._scaled_pt(7)}pt;")

        self._set_window_size_with_extra_height()

        # Обновляем масштаб элементов на вкладке каскадов
        if hasattr(self, "tab_cascade"):
            self.tab_cascade.apply_scale()

        # Второй проход после применения стилей/DPI-метрик,
        # чтобы таблица калькулятора гарантированно не заходила под кнопку.
        self._schedule_cells_layout_reflow()

    def _schedule_cells_layout_reflow(self):
        if self._cells_layout_reflow_pending:
            return
        self._cells_layout_reflow_pending = True

        def _run():
            self._cells_layout_reflow_pending = False
            if not hasattr(self, "cells_table"):
                return
            try:
                self.update_cells_table_height()
                self._schedule_smooth_content_resize(force=True)
            except Exception:
                pass

        QTimer.singleShot(0, _run)

    # --- УПРАВЛЕНИЕ ГОРЯЧИМИ КЛАВИШАМИ (ИСПРАВЛЕНО) ---
    def _clear_registered_hotkeys(self):
        for _, hotkey_id in list(self._hotkey_ids.items()):
            try:
                keyboard.remove_hotkey(hotkey_id)
            except Exception:
                pass
        self._hotkey_ids = {}

    def _register_hotkey(self, key_name, hotkey_text, callback, fallback):
        try:
            hotkey_id = keyboard.add_hotkey(hotkey_text, callback)
            self._hotkey_ids[key_name] = hotkey_id
            self.settings[key_name] = hotkey_text
            return
        except Exception:
            pass

        hotkey_id = keyboard.add_hotkey(fallback, callback)
        self._hotkey_ids[key_name] = hotkey_id
        self.settings[key_name] = fallback

    def rebind_hotkeys(self):
        def normalize_hotkey(hotkey_value, fallback):
            value = str(hotkey_value or "").strip().lower()
            value = value.replace(" ", "")
            return value or fallback

        self._clear_registered_hotkeys()

        # F1 - Скрыть/Показать
        hk_show = normalize_hotkey(self.settings.get("hk_show", "f1"), "f1")
        self._register_hotkey(
            "hk_show", hk_show, self.signaler.toggle_sig.emit, "f1"
        )

        # F2 - Калибровка (в зависимости от активной вкладки)
        hk_coords = normalize_hotkey(self.settings.get("hk_coords", "f2"), "f2")
        self._register_hotkey(
            "hk_coords", hk_coords, self.signaler.calibrate_sig.emit, "f2"
        )

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
            self._reset_active_calc_calibration()
            self.calc_calibration_active = False
            hk_coords = self.settings.get("hk_coords", "f2").upper()
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            self.lbl_status.setText(t["calc_calib_reset"].format(hotkey=hk_coords))
            self.lbl_status.setStyleSheet(
                f"color: #FF9F0A; font-size: {self._scaled_pt(7)}pt;"
            )
            return True

        return False

    # Обработка нажатия Enter на клавиатуре (когда фокус в программе)
    def keyPressEvent(self, event):
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
        points = self._get_active_calc_points()
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
                self.lbl_status.setStyleSheet(
                    f"color: #FF9F0A; font-size: {self._scaled_pt(7)}pt;"
                )
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

            if self._is_menu_terminal():
                try:
                    pyautogui.MINIMUM_SLEEP = 0.0005
                    pyautogui.MINIMUM_DURATION = 0.005
                    pyautogui.PAUSE = 0.0
                except Exception:
                    pass

                menu_kind = self._menu_terminal_kind() or "tiger"
                open_menu_settle_delay = 0.03
                post_paste_settle_delay = 0.012
                between_cells_delay = 0.025
                close_menu_delay = 0.03

                open_key, close_key = self._get_menu_terminal_point_keys()
                requires_final_point = self._menu_terminal_requires_final_point()
                t_open = self.settings.get(open_key)
                t_close = self.settings.get(close_key)
                if (
                    not isinstance(t_open, (list, tuple))
                    or len(t_open) != 2
                    or (
                        requires_final_point
                        and (
                            not isinstance(t_close, (list, tuple))
                            or len(t_close) != 2
                        )
                    )
                ):
                    t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                    need_key = f"calc_{menu_kind}_need_points"
                    self.lbl_status.setText(t.get(need_key, t["calc_not_enough_points"]))
                    self.lbl_status.setStyleSheet(
                        f"color: #FF9F0A; font-size: {self._scaled_pt(7)}pt;"
                    )
                    return

                pyautogui.moveTo(t_open[0], t_open[1], duration=0.015)
                pyautogui.click()
                time.sleep(0.012)
                pyautogui.doubleClick(interval=0.03)
                time.sleep(open_menu_settle_delay)

                for transfer_index, (point_index, vol_to_send) in enumerate(transfers):
                    pyperclip.copy(vol_to_send)
                    time.sleep(0.01)
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
                    time.sleep(post_paste_settle_delay)
                    if transfer_index < len(transfers) - 1:
                        time.sleep(between_cells_delay)
                    elif menu_kind == "vataga":
                        # Vataga closes the menu by Enter only after the last edited cell.
                        keyboard.press_and_release("enter")
                        time.sleep(close_menu_delay)

                if requires_final_point:
                    pyautogui.moveTo(t_close[0], t_close[1], duration=0.015)
                    pyautogui.click()
                    time.sleep(close_menu_delay)
            else:
                try:
                    pyautogui.MINIMUM_SLEEP = 0.0005
                    pyautogui.MINIMUM_DURATION = 0.005
                    pyautogui.PAUSE = 0.0
                except Exception:
                    pass

                is_metascalp = self._is_metascalp_terminal()
                if is_metascalp:
                    # MetaScalp: first cell needs a short settle delay before editing starts.
                    time.sleep(0.06)

                for transfer_index, (point_index, vol_to_send) in enumerate(transfers):
                    pyperclip.copy(vol_to_send)
                    time.sleep(0.01)
                    pyautogui.moveTo(
                        points[point_index][0], points[point_index][1], duration=0.015
                    )
                    is_metascalp_first_calibrated = is_metascalp and point_index == 0
                    pyautogui.click()
                    if is_metascalp_first_calibrated:
                        # First captured MetaScalp cell: use live double click
                        # (two real clicks with pauses) for stable focus.
                        time.sleep(0.07)
                        pyautogui.click()
                        time.sleep(0.07)
                    elif is_metascalp:
                        time.sleep(0.012)
                    else:
                        time.sleep(0.012)
                    if is_metascalp_first_calibrated:
                        pass
                    else:
                        pyautogui.doubleClick(interval=0.03)

                    if is_metascalp_first_calibrated:
                        time.sleep(0.03)
                    elif is_metascalp:
                        time.sleep(0.012)
                    else:
                        time.sleep(0.012)
                    keyboard.press_and_release("ctrl+a")
                    time.sleep(0.01)
                    keyboard.press_and_release("backspace")
                    time.sleep(0.01)
                    keyboard.press_and_release("ctrl+v")
                    time.sleep(0.012)
                    keyboard.press_and_release("enter")
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
        status_pt = self._scaled_pt(7)

        points = self._get_active_calc_points()
        menu_ready = False
        menu_kind = self._menu_terminal_kind()
        if self._is_menu_terminal():
            open_key, close_key = self._get_menu_terminal_point_keys()
            requires_final_point = self._menu_terminal_requires_final_point()
            menu_ready = (
                isinstance(self.settings.get(open_key), (list, tuple))
                and len(self.settings.get(open_key)) == 2
                and (
                    (not requires_final_point)
                    or (
                        isinstance(self.settings.get(close_key), (list, tuple))
                        and len(self.settings.get(close_key)) == 2
                    )
                )
            )

        if self._is_menu_terminal():
            if menu_ready and len(points) >= cells_count:
                self.calc_calibration_active = False
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                exists_key = f"calc_{menu_kind}_points_exists"
                ready_text = t.get(exists_key, t["calc_calib_exists"]).format(cells=cells_count)
                self._set_ready_status_with_neutral_timeout(ready_text)
                self.update_calibration_status()
                return

            self.calc_calibration_active = True
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            instruction_key = f"calc_{menu_kind}_calib_instruction"
            instruction = t.get(
                instruction_key,
                "Hover the volume selector cells in the order book, choose the first one and press {hotkey}",
            ).format(cells=cells_count, hotkey=hk_coords)
            self.lbl_status.setText(instruction)
            self.lbl_status.setStyleSheet(
                f"color: cyan; font-size: {status_pt}pt;"
            )
            self.update_calibration_status()
            return

        if len(points) >= cells_count:
            self.calc_calibration_active = False
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            ready_text = t["calc_calib_exists"].format(cells=cells_count)
            self._set_ready_status_with_neutral_timeout(ready_text)
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

            existing_points = self._get_active_calc_points()
            menu_ready = False
            if self._is_menu_terminal():
                open_key, close_key = self._get_menu_terminal_point_keys()
                requires_final_point = self._menu_terminal_requires_final_point()
                menu_ready = (
                    isinstance(self.settings.get(open_key), (list, tuple))
                    and len(self.settings.get(open_key)) == 2
                    and (
                        (not requires_final_point)
                        or (
                            isinstance(self.settings.get(close_key), (list, tuple))
                            and len(self.settings.get(close_key)) == 2
                        )
                    )
                )
            should_reset = len(existing_points) >= configured
            if self._is_menu_terminal():
                should_reset = should_reset and menu_ready

            if should_reset:
                self._reset_active_calc_calibration()
                self.calc_calibration_active = False
                hk_coords = self.settings.get("hk_coords", "f2").upper()
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                if self._is_menu_terminal():
                    menu_kind = self._menu_terminal_kind() or "tiger"
                    reset_key = f"calc_{menu_kind}_points_reset"
                    reset_text = t.get(reset_key, t["calc_calib_reset_short"]).format(hotkey=hk_coords)
                else:
                    reset_text = t["calc_calib_reset_short"].format(hotkey=hk_coords)
                self.lbl_status.setText(reset_text)
                self.lbl_status.setStyleSheet(f"color: #FF9F0A; font-size: {self._scaled_pt(7)}pt;")
                return

            self.start_calibration_calc()
            return

        cells_count = int(
            self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
        )

        x, y = pyautogui.position()

        if self._is_menu_terminal():
            open_key, close_key = self._get_menu_terminal_point_keys()
            requires_final_point = self._menu_terminal_requires_final_point()
            menu_open = self.settings.get(open_key)
            menu_close = self.settings.get(close_key)
            points = self._get_active_calc_points()

            if not (isinstance(menu_open, (list, tuple)) and len(menu_open) == 2):
                self.settings[open_key] = [x, y]
                self.save_settings()
                self.update_calibration_status()
                return

            if len(points) < cells_count:
                points.append([x, y])
                self._set_active_calc_points(points)
                self.save_settings()
                if len(points) >= cells_count and not requires_final_point:
                    self.calc_calibration_active = False
                self.update_calibration_status()
                return

            if requires_final_point and not (isinstance(menu_close, (list, tuple)) and len(menu_close) == 2):
                self.settings[close_key] = [x, y]
                self.save_settings()
                self.calc_calibration_active = False
            elif not requires_final_point:
                self.calc_calibration_active = False

            self.update_calibration_status()
            return

        points = self._get_active_calc_points()

        # Если уже есть достаточно - не захватываем дальше
        if len(points) >= cells_count:
            return

        if self._is_metascalp_terminal() and len(points) == 0:
            # Save the first MetaScalp point only when user is on explicit step 1 prompt.
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            hk_coords = self.settings.get("hk_coords", "f2").upper()
            expected_first_prompt = t.get(
                "calc_calib_step_first",
                "Наведи на 1 ячейку объема и нажми {hotkey}",
            ).format(hotkey=hk_coords)
            current_prompt = self.lbl_status.text() if hasattr(self, "lbl_status") else ""
            if str(current_prompt or "").strip() != str(expected_first_prompt).strip():
                if hasattr(self, "lbl_status"):
                    self.lbl_status.setText(expected_first_prompt)
                    self.lbl_status.setStyleSheet(
                        f"color: cyan; font-size: {self._scaled_pt(7)}pt;"
                    )
                return

        points.append([x, y])
        self._set_active_calc_points(points)
        self.save_settings()

        if len(points) >= cells_count:
            self.calc_calibration_active = False

        self.update_calibration_status()

    def update_calibration_status(self):
        """Обновляет подсказку о калибровке при переключении вкладок"""
        # Обновляем только если мы на вкладке калькулятора
        if hasattr(self, "tabs") and self.tabs.currentIndex() == 0:
            self._update_status_text()

    def _set_ready_status_with_neutral_timeout(self, text, ready_color="#38BE1D", delay_ms=5000):
        status_pt = self._scaled_pt(7)
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {ready_color}; font-size: {status_pt}pt;")

        self._status_neutral_token += 1
        token = self._status_neutral_token

        def _neutralize():
            if token != self._status_neutral_token:
                return
            if getattr(self, "calc_calibration_active", False):
                return
            if not hasattr(self, "lbl_status"):
                return
            if self.lbl_status.text() != text:
                return
            self.lbl_status.setStyleSheet(f"color: #666; font-size: {self._scaled_pt(7)}pt;")

        QTimer.singleShot(int(delay_ms), _neutralize)

    def _set_transient_status_then_neutral(self, status_text, neutral_text, status_color="#FF9F0A", delay_ms=5000):
        status_pt = self._scaled_pt(7)
        self.lbl_status.setText(status_text)
        self.lbl_status.setStyleSheet(f"color: {status_color}; font-size: {status_pt}pt;")

        self._status_neutral_token += 1
        token = self._status_neutral_token

        def _neutralize():
            if token != self._status_neutral_token:
                return
            if getattr(self, "calc_calibration_active", False):
                return
            if not hasattr(self, "lbl_status"):
                return
            self.lbl_status.setText(neutral_text)
            self.lbl_status.setStyleSheet(f"color: #666; font-size: {self._scaled_pt(7)}pt;")

        QTimer.singleShot(int(delay_ms), _neutralize)

    def _update_status_text(self):
        """Внутренний метод для обновления текста статуса"""
        cells_count = int(
            self.settings.get("scalp_cells_count", self.lbl_cells_count.text())
        )
        points_count = len(self._get_active_calc_points())
        hk_coords = self.settings.get("hk_coords", "f2").upper()
        status_pt = self._scaled_pt(7)

        if self._is_menu_terminal():
            menu_kind = self._menu_terminal_kind() or "tiger"
            open_key, close_key = self._get_menu_terminal_point_keys()
            requires_final_point = self._menu_terminal_requires_final_point()
            has_open = (
                isinstance(self.settings.get(open_key), (list, tuple))
                and len(self.settings.get(open_key)) == 2
            )
            has_close = (
                (not requires_final_point)
                or (
                    isinstance(self.settings.get(close_key), (list, tuple))
                    and len(self.settings.get(close_key)) == 2
                )
            )

            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            if not self.calc_calibration_active and has_open and has_close and points_count >= cells_count:
                ready_key = f"calc_{menu_kind}_points_ready"
                ready_text = t.get(ready_key, t["calc_calib_ready"]).format(cells=cells_count)
                self._set_ready_status_with_neutral_timeout(ready_text)
                return

            if self.calc_calibration_active:
                if not has_open:
                    step_open_key = f"calc_{menu_kind}_step_open"
                    self.lbl_status.setText(
                        t.get(step_open_key, "Наведи на ячейки выбора объема в стакане, выбери 1 ячейку и нажми {hotkey}").format(
                            hotkey=hk_coords
                        )
                    )
                elif points_count < cells_count:
                    step_key = (
                        f"calc_{menu_kind}_step_cell_first"
                        if points_count == 0
                        else f"calc_{menu_kind}_step_cell_next"
                    )
                    self.lbl_status.setText(
                        t.get(step_key, "Теперь наведи на {num} ячейку и нажми {hotkey}").format(
                            num=points_count + 1,
                            hotkey=hk_coords,
                        )
                    )
                elif not has_close:
                    step_close_key = f"calc_{menu_kind}_step_close"
                    self.lbl_status.setText(
                        t.get(step_close_key, "Теперь наведи на крестик закрытия меню и нажми {hotkey}").format(
                            hotkey=hk_coords
                        )
                    )
                else:
                    ready_key = f"calc_{menu_kind}_points_ready"
                    self.lbl_status.setText(
                        t.get(ready_key, t["calc_calib_ready"]).format(cells=cells_count)
                    )
                self.lbl_status.setStyleSheet(f"color: cyan; font-size: {status_pt}pt;")
            else:
                need_key = f"calc_{menu_kind}_need_points"
                self.lbl_status.setText(
                    t.get(need_key, "⚠ Точки для выставления терминала не захвачены. Нажми горячую клавишу захвата")
                )
                self.lbl_status.setStyleSheet(f"color: #666; font-size: {status_pt}pt;")
            return

        if points_count == 0:
            if self.calc_calibration_active:
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_status.setText(
                    t.get(
                        "calc_calib_step_first",
                        "Наведи на 1 ячейку объема и нажми {hotkey}",
                    ).format(hotkey=hk_coords)
                )
                self.lbl_status.setStyleSheet(f"color: cyan; font-size: {status_pt}pt;")
            else:
                t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
                self.lbl_status.setText(
                    t.get(
                        "calc_need_start",
                        "Нужно выполнить калибровку, для начала нажми {hotkey}",
                    ).format(hotkey=hk_coords)
                )
                self.lbl_status.setStyleSheet(f"color: #666; font-size: {status_pt}pt;")
        elif points_count < cells_count:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            if self.calc_calibration_active:
                self.lbl_status.setText(
                    t.get(
                        "calc_calib_step_next",
                        "Наведи на {num} ячейку объема и нажми {hotkey} ({points} из {cells})",
                    ).format(
                        num=points_count + 1,
                        hotkey=hk_coords,
                        points=points_count,
                        cells=cells_count,
                    )
                )
                self.lbl_status.setStyleSheet(f"color: cyan; font-size: {status_pt}pt;")
            else:
                self.lbl_status.setText(
                    t["calc_calib_progress"].format(points=points_count, cells=cells_count)
                )
                self.lbl_status.setStyleSheet(f"color: #FF9F0A; font-size: {status_pt}pt;")
        else:
            t = TRANS.get(self.settings.get("lang", "ru"), TRANS["ru"])
            ready_text = t["calc_calib_ready"].format(cells=cells_count)
            self._set_ready_status_with_neutral_timeout(ready_text)

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
                "scalp_manual_multipliers",
                self.settings.get("scalp_multipliers", [100, 50, 25, 10, 0]),
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

        # Всегда отключаем скроллбары для таблицы калькулятора:
        # горизонтальный скролл может появляться на некоторых масштабах и "съедать"
        # высоту последней строки, из-за чего визуально таблица заходит под кнопку.
        self.cells_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.cells_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
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

        # Берем фактическую длину вертикального хедера после установки высот строк.
        # Это надежнее, чем row_height * N на разных DPI/масштабах/шрифтах.
        rows_height = self.cells_table.verticalHeader().length()

        # Добавляем небольшой буфер, чтобы нижняя строка никогда не обрезалась.
        table_height = (
            header_height
            + rows_height
            + (self.cells_table.frameWidth() * 2)
            + 4
        )
        self.cells_table.setFixedHeight(table_height)

        if self.isVisible():
            self._set_window_size_with_extra_height()

    def on_table_item_clicked(self, item):
        """Обработчик клика по ячейке: toggle-мультивыбор в колонке 0, редактирование в колонке 2"""
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
        elif item.column() == 2:
            # Percent column: 1-click to edit, 2-click to select all
            now_ms = int(time.time() * 1000)
            last_ms = (item.data(Qt.ItemDataRole.UserRole + 1) or 0)
            click_count = (item.data(Qt.ItemDataRole.UserRole + 2) or 0)

            # Reset click_count if more than 350ms have passed since last click
            if now_ms - last_ms > 350 or last_ms == 0:
                click_count = 0

            # Reset click_count for all other items to avoid interference
            for row in range(self.cells_table.rowCount()):
                for col in range(self.cells_table.columnCount()):
                    other_item = self.cells_table.item(row, col)
                    if other_item is not item:
                        other_item.setData(Qt.ItemDataRole.UserRole + 2, 0)
                        other_item.setData(Qt.ItemDataRole.UserRole + 1, 0)

            click_count += 1
            item.setData(Qt.ItemDataRole.UserRole + 1, now_ms)
            item.setData(Qt.ItemDataRole.UserRole + 2, click_count)

            if click_count == 1:
                # First click: open editor with cursor at end, no selection
                self.cells_table.editItem(item)
                # Ensure no text is selected after editor opens
                def deselect_and_position():
                    from PyQt6.QtWidgets import QApplication
                    editor = QApplication.instance().focusWidget()
                    if isinstance(editor, QLineEdit):
                        editor.deselect()
                        editor.setCursorPosition(len(editor.text()))
                QTimer.singleShot(0, deselect_and_position)
            elif click_count == 2:
                # Second click: select all text
                from PyQt6.QtWidgets import QApplication
                editor = QApplication.instance().focusWidget()
                if not editor or not isinstance(editor, QLineEdit):
                    # If no editor yet, open and select with delay
                    self.cells_table.editItem(item)
                    def select_all_delayed():
                        ed = QApplication.instance().focusWidget()
                        if isinstance(ed, QLineEdit):
                            # Use setSelection() to explicitly select all text
                            ed.setSelection(0, len(ed.text()))
                    QTimer.singleShot(15, select_all_delayed)
                else:
                    # Already editing, select all text
                    editor.setSelection(0, len(editor.text()))


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

            self._capture_current_manual_distribution()
            self.update_cell_volumes()
            self.save_cell_settings()
            self._schedule_smooth_content_resize(force=True)

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
        self._set_window_size_with_extra_height()
        if self._startup_window_size is None:
            self._startup_window_size = (int(self.width()), int(self.height()))
        if not self._resize_len_baseline:
            for name in (
                "inp_dep",
                "inp_risk",
                "inp_stop",
                "inp_pos_vol",
                "inp_pos_risk",
                "inp_pos_stop",
                "inp_pos_stop_now",
                "inp_min_order",
            ):
                widget = getattr(self, name, None)
                if widget:
                    self._resize_len_baseline[name] = len((widget.text() or "").strip())
            self._last_applied_resize_pressure = self._current_resize_pressure_chars()

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

    def _capture_current_manual_distribution(self):
        if not hasattr(self, "cells_table"):
            return

        manual_values = []
        for i in range(5):
            item = self.cells_table.item(i, 2)
            text = (item.text() if item else "") or ""
            text = str(text).strip()
            manual_values.append(int(text) if text.isdigit() else 0)

        self.settings["scalp_manual_multipliers"] = manual_values

    def _restore_manual_distribution(self):
        if not hasattr(self, "cells_table"):
            return

        saved = self.settings.get(
            "scalp_manual_multipliers",
            self.settings.get("scalp_multipliers", [100, 50, 25, 10, 0]),
        )
        if not isinstance(saved, list):
            saved = [100, 50, 25, 10, 0]
        saved = list(saved)[:5] + [0] * max(0, 5 - len(saved))

        if self.settings.get("cells_reversed", False):
            saved = list(reversed(saved))

        active_rows = set(self._get_active_rows_for_table())
        for i in range(5):
            item = self.cells_table.item(i, 2)
            if not item:
                continue
            if i in active_rows:
                val = saved[i]
                item.setText(str(int(val) if str(val).isdigit() else 0))
            else:
                item.setText("")

        self._apply_manual_active_row_flags()

    def apply_distribution_preset(self):
        """Применяет выбранную предустановку распределения"""
        preset_index = self.cb_distribution.currentIndex()
        prev_preset_index = int(self.settings.get("scalp_distribution_type", 0) or 0)

        if prev_preset_index == 2 and preset_index != 2:
            self._capture_current_manual_distribution()

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
        if preset_index == 2:
            self._restore_manual_distribution()
        else:
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
        p_vol = self._get_calc_volume_precision()
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
        self._schedule_smooth_content_resize()
        self.save_cell_settings()

    def _commit_input(self):
        sender = self.sender()
        if isinstance(sender, QLineEdit):
            self._clear_ghost_focus()
            sender.deselect()
            sender.clearFocus()

    def _clear_ghost_focus(self, except_obj=None):
        """Очищает свойства фокуса (ghost focus больше не используется, оставлено для совместимости)"""
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
        if isinstance(obj, QLineEdit):
            if event.type() == event.Type.MouseButtonPress:
                now_ms = int(time.time() * 1000)
                last_ms = obj.property("last_click_ms") or 0
                click_count = obj.property("click_count") or 0

                # Count clicks: if within 350ms, increment; otherwise reset to 1
                if now_ms - last_ms <= 350:
                    click_count += 1
                else:
                    click_count = 1

                obj.setProperty("last_click_ms", now_ms)
                obj.setProperty("click_count", click_count)

                if click_count == 1:
                    # First click: focus + cursor at end, NO select
                    obj.setFocus()
                    obj.deselect()
                    QTimer.singleShot(
                        0, lambda o=obj: o.setCursorPosition(len(o.text()))
                    )
                    return True
                elif click_count == 2:
                    # Second click: select all
                    obj.setFocus()
                    QTimer.singleShot(0, obj.selectAll)
                    return True
            elif event.type() == event.Type.MouseButtonDblClick:
                # Double-click: select all
                obj.setFocus()
                QTimer.singleShot(0, obj.selectAll)
                return True
            elif event.type() == event.Type.KeyPress:
                if event.key() in (
                    Qt.Key.Key_Escape,
                    Qt.Key.Key_Return,
                    Qt.Key.Key_Enter,
                ):
                    obj.deselect()
                    obj.clearFocus()
                    obj.setProperty("click_count", 0)
                    obj.setProperty("last_click_ms", 0)
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
            try:
                self._clear_registered_hotkeys()
            except Exception:
                pass
            self.settings["window_pos"] = [self.x(), self.y()]
            self.settings["pos_table_volume_override"] = float(
                getattr(self, "table_volume_override", 0.0) or 0.0
            )
            self.save_cell_settings()
        except Exception:
            pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
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
    _app_shared_memory_guard = shared_memory

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    _force_consistent_qt_theme(app)
    win = RiskVolumeApp()
    win.show()
    sys.exit(app.exec())
