# cascade_tab.py
import time
import pyautogui
import keyboard
import pyperclip
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QGridLayout,
    QFrame,
    QAbstractSpinBox,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal


class CascadeWorker(QThread):
    """╨Я╨╛╤В╨╛╨║ ╨┤╨╗╤П ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╕╤П ╨║╨╗╨╕╨║╨╛╨▓"""

    finished = pyqtSignal()
    cancelled = pyqtSignal()  # ╨б╨╕╨│╨╜╨░╨╗ ╨╛╨▒ ╨╛╤Б╤В╨░╨╜╨╛╨▓╨║╨╡ ╨┐╨╛ ESC

    def __init__(self, settings, orders_data, main_window):
        super().__init__()
        self.settings = settings
        self.orders = orders_data
        self.main_window = main_window
        self._cancelled = False

    def run(self):
        # ╨Ф╨╛╤Б╤В╨░╨╡╨╝ ╨║╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╤Л
        c_gear = self.settings.get("cas_p_gear")  # ╨и╨╡╤Б╤В╨╡╤А╨╡╨╜╨║╨░
        c_book = self.settings.get("cas_p_book")  # ╨Я╤Г╨╜╨║╤В ╨╝╨╡╨╜╤О ╨Ъ╨╜╨╕╨│╨░ ╨╖╨░╤П╨▓╨╛╨║
        c_scrollbar = self.settings.get("cas_p_scrollbar")  # ╨Я╨╛╨╗╨╖╤Г╨╜╨╛╨║ ╤Б╨║╤А╨╛╨╗╨╗╨▒╨░╤А╨░
        c_vol1 = self.settings.get("cas_p_vol1")
        c_dist1 = self.settings.get("cas_p_dist1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_plus = self.settings.get("cas_p_plus")
        c_x = self.settings.get("cas_p_x")

        # ╨Ю╤В╨╗╨░╨┤╨║╨░ - ╨▓╤Л╨▓╨╛╨┤╨╕╨╝ ╨║╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╤Л
        print(f"[CASCADE] ╨Ъ╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╤Л:")
        print(f"  ╨и╨╡╤Б╤В╨╡╤А╨╡╨╜╨║╨░ (c_gear): {c_gear}")
        print(f"  ╨Ъ╨╜╨╕╨│╨░ ╨╖╨░╤П╨▓╨╛╨║ (c_book): {c_book}")
        print(f"  ╨Ю╨▒╤К╨╡╨╝ 1 (c_vol1): {c_vol1}")
        print(f"  ╨Ф╨╕╤Б╤В╨░╨╜╤Ж╨╕╤П 1 (c_dist1): {c_dist1}")
        print(f"  ╨Ю╨▒╤К╨╡╨╝ 2 (c_vol2): {c_vol2}")
        print(f"  ╨Я╨╗╤О╤Б╨╕╨║ (c_plus): {c_plus}")
        print(f"  ╨Ъ╤А╨╡╤Б╤В╨╕╨║ (c_x): {c_x}")
        print(f"  ╨Ч╨░╤П╨▓╨╛╨║ ╨┤╨╗╤П ╨▓╤Л╤Б╤В╨░╨▓╨╗╨╡╨╜╨╕╤П: {len(self.orders)}")

        # ╨Х╤Б╨╗╨╕ ╨╜╨╡ ╨▓╤Б╨╡ ╤В╨╛╤З╨║╨╕ ╨╖╨░╨┤╨░╨╜╤Л - ╤Б╤В╨╛╨┐
        if not (c_gear and c_book and c_vol1 and c_dist1 and c_vol2 and c_plus and c_x):
            return

        row_height = c_vol2[1] - c_vol1[1]

        # ╨а╨╡╨│╨╕╤Б╤В╤А╨╕╤А╤Г╨╡╨╝ ESC ╨┤╨╗╤П ╨╛╤Б╤В╨░╨╜╨╛╨▓╨║╨╕
        def on_esc():
            self._cancelled = True
            # ╨Я╨╛╨║╨░╨╖╤Л╨▓╨░╨╡╨╝ ╨╛╨║╨╜╨╛ ╨╛╨▒╤А╨░╤В╨╜╨╛
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.cancelled.emit()

        keyboard.add_hotkey("esc", on_esc)

        try:
            # 1. ╨Ю╤В╨║╤А╤Л╨▓╨░╨╡╨╝ ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ (╨и╨╡╤Б╤В╨╡╤А╨╡╨╜╨║╨░)
            if self._cancelled:
                return
            pyautogui.moveTo(c_gear[0], c_gear[1])
            pyautogui.click()
            time.sleep(0.15)

            # 2. ╨Т╤Л╨▒╨╕╤А╨░╨╡╨╝ ╨┐╤Г╨╜╨║╤В "╨Ъ╨╜╨╕╨│╨░ ╨╖╨░╤П╨▓╨╛╨║"
            if self._cancelled:
                return
            pyautogui.moveTo(c_book[0], c_book[1])
            pyautogui.click()
            time.sleep(0.15)

            # 3. ╨Я╨╡╤А╨╡╤В╨░╤Б╨║╨╕╨▓╨░╨╡╨╝ ╨┐╨╛╨╗╨╖╤Г╨╜╨╛╨║ ╨▓╨╜╨╕╨╖ (╨╡╤Б╨╗╨╕ ╨║╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╨░ ╤Б╨║╤А╨╛╨╗╨╗╨▒╨░╤А╨░ ╨╖╨░╨┤╨░╨╜╨░)
            if self._cancelled:
                return
            if c_scrollbar:
                scrollbar_x = c_scrollbar[0]
                scrollbar_y_start = c_scrollbar[1]
                scrollbar_y_end = scrollbar_y_start + 700  # ╨в╤П╨╜╨╡╨╝ ╨▓╨╜╨╕╨╖ ╨╜╨░ 700px

                # ╨Я╨╡╤А╨╡╤В╨░╤Б╨║╨╕╨▓╨░╨╡╨╝ ╨┐╨╛╨╗╨╖╤Г╨╜╨╛╨║: ╨╜╨░╨╢╨╕╨╝╨░╨╡╨╝, ╤В╤П╨╜╨╡╨╝, ╨╛╤В╨┐╤Г╤Б╨║╨░╨╡╨╝
                pyautogui.moveTo(scrollbar_x, scrollbar_y_start)
                time.sleep(0.1)
                pyautogui.mouseDown(button="left")
                time.sleep(0.05)
                pyautogui.moveTo(scrollbar_x, scrollbar_y_end, duration=0.4)
                time.sleep(0.05)
                pyautogui.mouseUp(button="left")
                time.sleep(0.2)

            # ╨Ф╨╛╨┐╨╛╨╗╨╜╨╕╤В╨╡╨╗╤М╨╜╨╛: ╨╜╨╡╤Б╨║╨╛╨╗╤М╨║╨╛ PageDown ╨┤╨╗╤П ╤В╨╛╤З╨╜╨╛╤Б╤В╨╕
            pyautogui.moveTo(c_book[0], c_book[1] + 200)
            pyautogui.click()
            time.sleep(0.05)
            for _ in range(2):
                if self._cancelled:
                    return
                pyautogui.press("pagedown")
                time.sleep(0.03)

            # 4. ╨Ю╤З╨╕╤Б╤В╨║╨░ (╤Г╨┤╨░╨╗╤П╨╡╨╝ ╤Б╤В╨░╤А╤Л╨╡ ╤Б╤В╤А╨╛╨║╨╕ ╨║╨░╤Б╨║╨░╨┤╨░)
            if self._cancelled:
                return
            print(
                f"[CASCADE] ╨и╨░╨│ 4: ╨Э╨░╨╢╨╕╨╝╨░╤О ╨╜╨░ ╨║╤А╨╡╤Б╤В╨╕╨║ (X) ╨┤╨╗╤П ╤Г╨┤╨░╨╗╨╡╨╜╨╕╤П ╨╖╨░╤П╨▓╨╛╨║. ╨Ъ╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╤Л: {c_x}"
            )
            pyautogui.moveTo(c_x[0], c_x[1])
            for i in range(12):  # ╨б ╨╖╨░╨┐╨░╤Б╨╛╨╝
                if self._cancelled:
                    return
                print(f"[CASCADE]   ╨Э╨░╨╢╨░╤В╨╕╨╡ {i+1}/12 ╨╜╨░ ╨║╤А╨╡╤Б╤В╨╕╨║ (X)")
                pyautogui.click()
                time.sleep(0.02)

            # 5. ╨б╨╛╨╖╨┤╨░╨╡╨╝ ╨╜╤Г╨╢╨╜╨╛╨╡ ╨║╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╤Б╤В╤А╨╛╨║
            if self._cancelled:
                return
            print(
                f"[CASCADE] ╨и╨░╨│ 5: ╨Э╨░╨╢╨╕╨╝╨░╤О ╨╜╨░ ╨┐╨╗╤О╤Б╨╕╨║ (+) ╨┤╨╗╤П ╨┤╨╛╨▒╨░╨▓╨╗╨╡╨╜╨╕╤П ╨╖╨░╤П╨▓╨╛╨║. ╨Ъ╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╤Л: {c_plus}. ╨Ъ╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╨┤╨╗╤П ╨┤╨╛╨▒╨░╨▓╨╗╨╡╨╜╨╕╤П: {len(self.orders) - 1}"
            )
            pyautogui.moveTo(c_plus[0], c_plus[1])
            for i in range(len(self.orders) - 1):
                if self._cancelled:
                    return
                print(f"[CASCADE]   ╨Э╨░╨╢╨░╤В╨╕╨╡ {i+1}/{len(self.orders)-1} ╨╜╨░ ╨┐╨╗╤О╤Б╨╕╨║ (+)")
                pyautogui.click()
                time.sleep(0.03)

            # 6. ╨Ч╨░╨┐╨╛╨╗╨╜╤П╨╡╨╝ ╨╖╨╜╨░╤З╨╡╨╜╨╕╤П
            print(
                f"[CASCADE] ╨и╨░╨│ 6: ╨Ч╨░╨┐╨╛╨╗╨╜╤П╤О ╨╛╨▒╤К╤С╨╝╤Л ╨╕ ╨┤╨╕╤Б╤В╨░╨╜╤Ж╨╕╨╕. ╨Т╤Л╤Б╨╛╤В╨░ ╤Б╤В╤А╨╛╨║╨╕: {row_height}"
            )
            for i, order in enumerate(self.orders):
                if self._cancelled:
                    return
                cur_y = c_vol1[1] + (i * row_height)
                print(
                    f"[CASCADE]   ╨Ч╨░╤П╨▓╨║╨░ {i+1}: ╨╛╨▒╤К╨╡╨╝={order['vol']:.2f}, ╨┤╨╕╤Б╤В╨░╨╜╤Ж╨╕╤П={order['dist']:.2f}%, Y={cur_y}"
                )

                # --- ╨Ю╨▒╤К╤С╨╝ ---
                vol_str = f"{order['vol']:.2f}".replace(",", ".")
                pyperclip.copy(vol_str)
                print(
                    f"[CASCADE]     ╨Т╤Л╤Б╤В╨░╨▓╨╗╤П╤О ╨╛╨▒╤К╨╡╨╝ {vol_str} ╨▓ ╨║╨╛╨╛╤А╨┤╨╕╨╜╨░╤В╤Л ({c_vol1[0]}, {cur_y})"
                )
                pyautogui.moveTo(c_vol1[0], cur_y)
                pyautogui.click()
                time.sleep(0.03)
                pyautogui.click(clicks=2)
                time.sleep(0.03)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.02)
                pyautogui.press("backspace")
                time.sleep(0.02)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.02)
                pyautogui.press("enter")

                # --- ╨Ф╨╕╤Б╤В╨░╨╜╤Ж╨╕╤П ---
                dist_str = f"{order['dist']:.2f}".replace(",", ".")
                pyperclip.copy(dist_str)
                pyautogui.moveTo(c_dist1[0], cur_y)
                pyautogui.click()
                time.sleep(0.03)
                pyautogui.click(clicks=2)
                time.sleep(0.03)
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.02)
                pyautogui.press("backspace")
                time.sleep(0.02)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.02)
                pyautogui.press("enter")

                time.sleep(0.02)

            # 7. ╨Ч╨░╨║╤А╤Л╨▓╨░╨╡╨╝ ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨╕ (Esc)
            if not self._cancelled:
                time.sleep(0.1)
                pyautogui.press("esc")
                self.finished.emit()
        finally:
            # ╨г╨▒╨╕╤А╨░╨╡╨╝ ╤Е╨╛╤В╨║╨╡╨╣ ESC
            try:
                keyboard.remove_hotkey("esc")
            except:
                pass


class CascadeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.init_ui()

    def _wrap_spinbox(self, spinbox):
        wrap = QFrame()
        wrap.setObjectName("SpinWrap")
        wrap_layout = QHBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)

        left_btn = QPushButton("-")
        right_btn = QPushButton("+")
        left_btn.setObjectName("SpinStepBtn")
        right_btn.setObjectName("SpinStepBtn")

        left_btn.clicked.connect(spinbox.stepDown)
        right_btn.clicked.connect(spinbox.stepUp)

        wrap_layout.addWidget(left_btn)
        wrap_layout.addWidget(spinbox)
        wrap_layout.addWidget(right_btn)

        # ╨б╨╛╤Е╤А╨░╨╜╤П╨╡╨╝ ╤Б╤Б╤Л╨╗╨║╨╕ ╨┤╨╗╤П ╨╝╨░╤Б╤И╤В╨░╨▒╨╕╤А╨╛╨▓╨░╨╜╨╕╤П
        if spinbox is getattr(self, "sb_count", None):
            self.sb_count_left, self.sb_count_right = left_btn, right_btn
        elif spinbox is getattr(self, "sb_min", None):
            self.sb_min_left, self.sb_min_right = left_btn, right_btn
        elif spinbox is getattr(self, "sb_dist", None):
            self.sb_dist_left, self.sb_dist_right = left_btn, right_btn

        return wrap

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- ╨б╤В╨╕╨╗╨╕ ╨┤╨╗╤П ╤Н╤В╨╛╨│╨╛ ╨╛╨║╨╜╨░ ---
        self.setStyleSheet(
            """
            QGroupBox { 
                border: 1px solid #333; 
                border-radius: 6px; 
                margin-top: 6px; 
                font-weight: bold; 
                color: #ccc;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: #aaa; font-size: 9pt; }
            /* ╨б╤В╨╕╨╗╤М ╨║╨╜╨╛╨┐╨╛╨║ ╨┐╤А╨╛╤Ж╨╡╨╜╤В╨╛╨▓ (╨Ш╤Б╨┐╤А╨░╨▓╨╗╨╡╨╜╨╛) */
            QPushButton.percBtn {
                background-color: #252525;
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton.percBtn:checked {
                background-color: #38BE1D; /* ╨п╤А╨║╨╛-╨╖╨╡╨╗╨╡╨╜╤Л╨╣ */
                color: black;             /* ╨з╨╡╤А╨╜╤Л╨╣ ╤В╨╡╨║╤Б╤В - ╤З╨╕╤В╨░╨╡╤В╤Б╤П ╨╛╤В╨╗╨╕╤З╨╜╨╛ */
                border: 1px solid #38BE1D;
            }
            QPushButton.percBtn:hover { border: 1px solid #555; }
            
            QComboBox {
                background: #1A1A1A; color: white; border: 1px solid #333; padding: 2px;
                min-width: 60px; /* ╨з╤В╨╛╨▒╤Л ╤В╨╡╨║╤Б╤В ╨╜╨╡ ╤А╨╡╨╖╨░╨╗╤Б╤П */
            }
            QFrame#SpinWrap {
                background: #1A1A1A;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QSpinBox#spinInner, QDoubleSpinBox#spinInner {
                background: transparent; color: white; border: none; padding: 2px;
            }
            QPushButton#SpinStepBtn {
                background: #2a2a2a;
                color: #cfcfcf;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 0px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton#SpinStepBtn:hover {
                background: #3a3a3a;
            }
        """
        )

        # --- ╨С╨Ы╨Ю╨Ъ 1: ╨Ю╨▒╤К╨╡╨╝ ---
        gb_vol = QGroupBox("1. ╨Ю╨▒╤Й╨╕╨╣ ╨╛╨▒╤К╨╡╨╝ ╨║╨░╤Б╨║╨░╨┤╨░")
        l_vol = QVBoxLayout()

        h_perc = QHBoxLayout()
        self.group_btns = []
        for text in ["25%", "50%", "75%", "100%"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "percBtn")  # ╨Ф╨╗╤П CSS
            btn.setObjectName("percBtn")  # ╨Ф╨╗╤П Qt
            btn.clicked.connect(self.on_perc_click)
            self.group_btns.append(btn)
            h_perc.addWidget(btn)

        self.group_btns[3].setChecked(True)  # 100% ╨┐╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О

        self.lbl_total_vol = QLabel("╨Ш╤В╨╛╨│╨╛ ╨▓ ╨║╨░╤Б╨║╨░╨┤: 0 $")
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt; margin-top: 5px;"
        )
        self.lbl_total_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)

        l_vol.addLayout(h_perc)
        l_vol.addWidget(self.lbl_total_vol)
        gb_vol.setLayout(l_vol)
        layout.addWidget(gb_vol)

        # --- ╨С╨Ы╨Ю╨Ъ 2: ╨Э╨░╤Б╤В╤А╨╛╨╣╨║╨╕ (╨б╨╡╤В╨║╨░ ╨╕╤Б╨┐╤А╨░╨▓╨╗╨╡╨╜╨░) ---
        gb_set = QGroupBox("2. ╨Э╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╤А╨░╤Б╤Б╤В╨░╨╜╨╛╨▓╨║╨╕")
        grid = QGridLayout()
        grid.setHorizontalSpacing(15)  # ╨Ю╤В╤Б╤В╤Г╨┐ ╨╝╨╡╨╢╨┤╤Г ╨║╨╛╨╗╨╛╨╜╨║╨░╨╝╨╕
        grid.setVerticalSpacing(8)

        # ╨Ш╤Б╨┐╨╛╨╗╤М╨╖╤Г╨╡╨╝ QLabel ╤Б wordWrap, ╤З╤В╨╛╨▒╤Л ╤В╨╡╨║╤Б╤В ╨┐╨╡╤А╨╡╨╜╨╛╤Б╨╕╨╗╤Б╤П ╨╡╤Б╨╗╨╕ ╤З╤В╨╛
        l1 = QLabel("╨Ъ╨╛╨╗-╨▓╨╛:")
        grid.addWidget(l1, 0, 0)
        self.sb_count = QSpinBox()
        self.sb_count.setRange(2, 20)
        self.sb_count.setValue(5)
        self.sb_count.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_count.setObjectName("spinInner")
        self.sb_count_wrap = self._wrap_spinbox(self.sb_count)
        grid.addWidget(self.sb_count_wrap, 0, 1)

        l2 = QLabel("╨Ь╨╕╨╜.╨╛╤А╨┤╨╡╤А ($):")
        grid.addWidget(l2, 0, 2)
        self.sb_min = QDoubleSpinBox()
        self.sb_min.setRange(1, 1000)
        self.sb_min.setValue(6)
        self.sb_min.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_min.setObjectName("spinInner")
        self.sb_min_wrap = self._wrap_spinbox(self.sb_min)
        grid.addWidget(self.sb_min_wrap, 0, 3)

        l3 = QLabel("╨в╨╕╨┐:")
        grid.addWidget(l3, 1, 0)
        self.cb_type = QComboBox()
        # ╨б╨╛╨║╤А╨░╤В╨╕╨╝ ╨╜╨░╨╖╨▓╨░╨╜╨╕╤П, ╤З╤В╨╛╨▒╤Л ╨▓╨╗╨░╨╖╨╕╨╗╨╕
        self.cb_type.addItems(
            ["╨а╨░╨▓╨╜╨╛╨╝╨╡╤А╨╜╨╛", "╨Ь╨░╤В╤А╨╡╤И╨║╨░ x1.2", "╨Ь╨░╤В╤А╨╡╤И╨║╨░ x1.5", "╨Р╨│╤А╨╡╤Б╤Б╨╕╨▓╨╜╨╛ x2"]
        )
        self.cb_type.setMinimumWidth(70)  # ╨С╨╛╨╗╨╡╨╡ ╨║╨╛╨╝╨┐╨░╨║╤В╨╜╨░╤П ╤И╨╕╤А╨╕╨╜╨░
        grid.addWidget(self.cb_type, 1, 1)

        l4 = QLabel("╨и╨░╨│ (%):")
        grid.addWidget(l4, 1, 2)
        self.sb_dist = QDoubleSpinBox()
        self.sb_dist.setRange(0.01, 10.0)
        self.sb_dist.setValue(0.1)
        self.sb_dist.setSingleStep(0.05)
        self.sb_dist.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_dist.setObjectName("spinInner")
        self.sb_dist_wrap = self._wrap_spinbox(self.sb_dist)
        grid.addWidget(self.sb_dist_wrap, 1, 3)

        # ╨б╨╛╨▒╤Л╤В╨╕╤П
        self.sb_count.valueChanged.connect(self.recalc_table)
        self.sb_min.valueChanged.connect(self.recalc_table)
        self.cb_type.currentIndexChanged.connect(self.recalc_table)
        self.sb_dist.valueChanged.connect(self.recalc_table)

        gb_set.setLayout(grid)
        layout.addWidget(gb_set)

        # --- ╨С╨Ы╨Ю╨Ъ 3: ╨в╨░╨▒╨╗╨╕╤Ж╨░ (╨Ш╤Б╨┐╤А╨░╨▓╨╗╨╡╨╜╨╛ ╨╛╨▒╤А╨╡╨╖╨░╨╜╨╕╨╡) ---
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["╨Ю╨▒╤К╨╡╨╝ ($)", "╨Ф╨╕╤Б╤В╨░╨╜╤Ж╨╕╤П (%)"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        # ╨г╨▓╨╡╨╗╨╕╤З╨╕╨▓╨░╨╡╨╝ ╨▓╤Л╤Б╨╛╤В╤Г ╤Б╤В╤А╨╛╨║, ╤З╤В╨╛╨▒╤Л ╤И╤А╨╕╤Д╤В ╨╜╨╡ ╤А╨╡╨╖╨░╨╗╤Б╤П
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setRowCount(0)
        self.table.setFixedHeight(120)
        # ╨С╨░╨╖╨╛╨▓╤Л╨╣ ╤Б╤В╨╕╨╗╤М ╤В╨░╨▒╨╗╨╕╤Ж╤Л (╤В╨╛╤З╨╜╤Л╨╡ ╤А╨░╨╖╨╝╨╡╤А╤Л ╨▓╤Л╤Б╤В╨░╨▓╤П╤В╤Б╤П ╨▓ apply_scale)
        self.table.setStyleSheet(
            "QTableWidget::item { font-size: 6pt; padding: 0px 2px; }"
            "QHeaderView::section { font-size: 8pt; padding: 2px; }"
            "selection-background-color: #38BE1D; selection-color: black;"
        )
        layout.addWidget(self.table)

        # --- ╨С╨Ы╨Ю╨Ъ 4: ╨Ъ╨╜╨╛╨┐╨║╨╕ ---
        h_btn = QHBoxLayout()
        self.btn_calib = QPushButton("╨Ъ╨Р╨Ы╨Ш╨С╨а╨Ю╨Т╨Ъ╨Р")
        self.btn_calib.setStyleSheet(
            "background: #333; color: white; padding: 8px; border: 1px solid #555;"
        )
        self.btn_calib.clicked.connect(self.start_calibration)

        self.btn_apply = QPushButton("╨Т╨л╨б╨в╨Р╨Т╨Ш╨в╨м")
        self.btn_apply.setStyleSheet(
            "background: #38BE1D; color: black; font-weight: bold; padding: 8px; font-size: 10pt;"
        )
        self.btn_apply.clicked.connect(self.run_automation)

        h_btn.addWidget(self.btn_calib)
        h_btn.addWidget(self.btn_apply)
        layout.addLayout(h_btn)

        # ╨б╤В╨░╤В╤Г╤Б (╤Б ╨┐╨╡╤А╨╡╨╜╨╛╤Б╨╛╨╝ ╤В╨╡╨║╤Б╤В╨░)
        self.lbl_status = QLabel("╨Э╤Г╨╢╨╜╨░ ╨║╨░╨╗╨╕╨▒╤А╨╛╨▓╨║╨░ (7 ╤И╨░╨│╨╛╨▓)")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)  # <-- ╨Т╨Р╨Ц╨Э╨Ю: ╨в╨╡╨║╤Б╤В ╨▒╤Г╨┤╨╡╤В ╨┐╨╡╤А╨╡╨╜╨╛╤Б╨╕╤В╤М╤Б╤П
        self.lbl_status.setStyleSheet(
            "color: #666; font-size: 7pt; margin-bottom: 5px;"
        )
        layout.addWidget(self.lbl_status)

        # ╨Я╤А╨╕╨╝╨╡╨╜╤П╨╡╨╝ ╨╝╨░╤Б╤И╤В╨░╨▒╨╕╤А╨╛╨▓╨░╨╜╨╕╨╡ ╨┐╨╛╨┤ ╤В╨╡╨║╤Г╤Й╨╕╨╣ ╤А╨░╨╖╨╝╨╡╤А ╨╕╨╜╤В╨╡╤А╤Д╨╡╨╣╤Б╨░
        self.apply_scale()

    def apply_scale(self):
        """
        ╨Я╨╛╨┤╨│╨╛╨╜╤П╨╡╤В ╤А╨░╨╖╨╝╨╡╤А╤Л ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨╛╨▓ ╨┐╨╛╨┤ ╤В╨╡╨║╤Г╤Й╨╕╨╣ ╨╝╨░╤Б╤И╤В╨░╨▒ ╨╕╨╜╤В╨╡╤А╤Д╨╡╨╣╤Б╨░ (settings['scale']),
        ╤З╤В╨╛╨▒╤Л ╨╜╨░ ╨▓╨║╨╗╨░╨┤╨║╨╡ ╨║╨░╤Б╨║╨░╨┤╨╛╨▓ ╨╜╨╕╤З╨╡╨│╨╛ ╨╜╨╡ ╨▓╤Л╨╗╨╡╨╖╨░╨╗╨╛ ╨╖╨░ ╤А╨░╨╝╨║╨╕ ╨╕ ╤В╨╡╨║╤Б╤В ╨╜╨╡ ╤А╨╡╨╖╨░╨╗╤Б╤П.
        """
        scale = self.main.settings.get("scale", 100)
        base_scale = getattr(self.main, "base_scale", 150)
        ratio = scale / float(base_scale)
        sc = scale / 100.0

        # ╨Ъ╨╜╨╛╨┐╨║╨░ ╤В╨╕╨┐╨╛╨▓: ╨║╨╛╨╝╨┐╨░╨║╤В╨╜╨░╤П ╤И╨╕╤А╨╕╨╜╨░ ╨╕ ╤Б╨╕╨╜╤Е╤А╨╛╨╜╨╜╨╛ ╤Б "╨Ъ╨╛╨╗-╨▓╨╛"
        compact_w = max(60, int(70 * sc))
        self.cb_type.setMinimumWidth(compact_w)
        self.cb_type.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.sb_count_wrap.setFixedWidth(compact_w)
        self.sb_min_wrap.setFixedWidth(compact_w)
        self.sb_dist_wrap.setFixedWidth(compact_w)

        btn_w = max(10, int(11 * sc))
        btn_h = max(9, int(9 * sc))
        input_w = max(26, compact_w - (btn_w * 2) - 6)
        field_h = max(14, int(14 * sc))
        for spin, left_btn, right_btn in (
            (self.sb_count, self.sb_count_left, self.sb_count_right),
            (self.sb_min, self.sb_min_left, self.sb_min_right),
            (self.sb_dist, self.sb_dist_left, self.sb_dist_right),
        ):
            spin.setFixedWidth(input_w)
            spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin.setFixedHeight(field_h)
            left_btn.setFixedSize(btn_w, btn_h)
            right_btn.setFixedSize(btn_w, btn_h)
        self.sb_count_wrap.setFixedHeight(field_h)
        self.sb_min_wrap.setFixedHeight(field_h)
        self.sb_dist_wrap.setFixedHeight(field_h)

        # ╨Ш╤В╨╛╨│╨╛╨▓╤Л╨╣ ╨╛╨▒╤К╨╡╨╝ ╨║╨░╤Б╨║╨░╨┤╨░
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt; margin-top: 5px;"
        )

        # ╨в╨░╨▒╨╗╨╕╤Ж╨░ ╨╛╤А╨┤╨╡╤А╨╛╨▓
        self.table.verticalHeader().setDefaultSectionSize(int(14 * sc))
        self.table.setFixedHeight(int(80 * sc))
        item_font = max(6, int(6 * ratio))
        header_font = max(6, int(8 * ratio))
        self.table.setStyleSheet(
            f"QTableWidget::item {{ font-size: {item_font}pt; padding: 0px 1px; margin: 0px; }}"
            f"QHeaderView::section {{ font-size: {header_font}pt; padding: 1px; }}"
            "selection-background-color: #38BE1D; selection-color: black;"
        )

        # ╨б╤В╤А╨╛╨║╨░ ╤Б╤В╨░╤В╤Г╤Б╨░ ╨▓╨╜╨╕╨╖╤Г
        self.lbl_status.setStyleSheet(
            "color: #666; font-size: 7pt; margin-bottom: 5px;"
        )

    def on_perc_click(self):
        sender = self.sender()
        for btn in self.group_btns:
            btn.setChecked(False)
        sender.setChecked(True)
        self.recalc_table()

    def get_percent(self):
        for btn in self.group_btns:
            if btn.isChecked():
                return float(btn.text().replace("%", "")) / 100.0
        return 1.0

    def get_multiplier(self):
        idx = self.cb_type.currentIndex()
        if idx == 0:
            return 1.0
        if idx == 1:
            return 1.2
        if idx == 2:
            return 1.5
        if idx == 3:
            return 2.0
        return 1.0

    def recalc_table(self):
        base_vol = getattr(self.main, "current_vol", 0)
        total_vol = base_vol * self.get_percent()

        self.lbl_total_vol.setText(f"╨Ш╤В╨╛╨│╨╛ ╨▓ ╨║╨░╤Б╨║╨░╨┤: {total_vol:.1f} $")

        if total_vol <= 0:
            self.table.setRowCount(0)
            return

        count = self.sb_count.value()
        mult = self.get_multiplier()
        min_size = self.sb_min.value()
        dist_step = self.sb_dist.value()

        # ╨Ь╨░╤В╨╡╨╝╨░╤В╨╕╨║╨░
        weights = [mult**i for i in range(count)]
        total_weight = sum(weights)
        raw_volumes = [(w / total_weight) * total_vol for w in weights]

        # ╨У╤А╤Г╨┐╨┐╨╕╤А╨╛╨▓╨║╨░ ╨╝╨╡╨╗╨╛╤З╨╕
        final_volumes = []
        temp_vol = 0
        for v in raw_volumes:
            temp_vol += v
            if temp_vol >= min_size:
                final_volumes.append(temp_vol)
                temp_vol = 0
        if temp_vol > 0:
            if final_volumes:
                final_volumes[-1] += temp_vol
            else:
                final_volumes.append(temp_vol)

        # ╨Ч╨░╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡ ╤В╨░╨▒╨╗╨╕╤Ж╤Л
        self.table.setRowCount(len(final_volumes))
        self.calculated_orders = []

        for i, vol in enumerate(final_volumes):
            dist = i * dist_step
            vol_item = QTableWidgetItem(f"{vol:.2f}")
            vol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, vol_item)

            dist_item = QTableWidgetItem(f"{dist:.2f}")
            dist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, dist_item)
            self.calculated_orders.append(
                {"vol": round(vol, 2), "dist": round(dist, 2)}
            )

    def start_calibration(self):
        # ╨Я╨╛╨╗╤Г╤З╨░╨╡╨╝ ╨│╨╛╤А╤П╤З╤Г╤О ╨║╨╗╨░╨▓╨╕╤И╤Г ╨┤╨╗╤П ╨╖╨░╤Е╨▓╨░╤В╨░ ╨║╨╛╨╛╤А╨┤╨╕╨╜╨░╤В ╨╕╨╖ ╨╜╨░╤Б╤В╤А╨╛╨╡╨║
        self.calib_hotkey = self.main.settings.get("hk_coords", "f2").lower()
        hotkey_display = self.calib_hotkey.upper().replace("+", " + ")

        self.lbl_status.setText(
            f"1. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨и╨Х╨б╨в╨Х╨а╨Х╨Э╨Ъ╨г ╨╜╨░╤Б╤В╤А╨╛╨╡╨║ -> ╨╜╨░╨╢╨╝╨╕ {hotkey_display}"
        )
        self.lbl_status.setStyleSheet("color: cyan;")
        self.calib_step = 1
        keyboard.add_hotkey(self.calib_hotkey, self.next_calib_step)

    def next_calib_step(self):
        x, y = pyautogui.position()
        hotkey_display = self.calib_hotkey.upper().replace("+", " + ")

        if self.calib_step == 1:
            self.main.settings["cas_p_gear"] = [x, y]
            self.lbl_status.setText(
                f"2. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨┐╤Г╨╜╨║╤В ╨╝╨╡╨╜╤О '╨Ъ╨Э╨Ш╨У╨Р ╨Ч╨Р╨п╨Т╨Ю╨Ъ' -> {hotkey_display}"
            )

        elif self.calib_step == 2:
            self.main.settings["cas_p_book"] = [x, y]
            self.lbl_status.setText(
                f"3. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨Я╨Ю╨Ы╨Ч╨г╨Э╨Ю╨Ъ ╨б╨Ъ╨а╨Ю╨Ы╨Ы╨С╨Р╨а╨Р (╨┐╨╛╨╗╨╛╤Б╨░ ╨┐╤А╨╛╨║╤А╤Г╤В╨║╨╕ ╨▓╨╜╨╕╨╖╤Г) -> {hotkey_display}\n"
                f"(╨н╤В╨╛ ╨╜╤Г╨╢╨╜╨╛ ╨┤╨╗╤П ╨║╨╛╤А╤А╨╡╨║╤В╨╜╨╛╨│╨╛ ╤Б╨║╤А╨╛╨╗╨╗╨╕╨╜╨│╨░ ╨║ ╤Б╤В╤А╨╛╨║╨░╨╝ ╨╛╤А╨┤╨╡╤А╨╛╨▓)"
            )

        elif self.calib_step == 3:
            self.main.settings["cas_p_scrollbar"] = [x, y]
            self.lbl_status.setText(
                f"4. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨┐╨╛╨╗╨╡ ╨▓╨▓╨╛╨┤╨░ ╨Ю╨С╨к╨Х╨Ь╨Р ╨┐╨╡╤А╨▓╨╛╨╣ ╤Б╤В╤А╨╛╨║╨╕ -> {hotkey_display}"
            )

        elif self.calib_step == 4:
            self.main.settings["cas_p_vol1"] = [x, y]
            self.lbl_status.setText(
                f"5. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨┐╨╛╨╗╨╡ ╨Ф╨Ш╨б╨в╨Р╨Э╨ж╨Ш╨Ш (0%) ╨┐╨╡╤А╨▓╨╛╨╣ ╤Б╤В╤А╨╛╨║╨╕ -> {hotkey_display}"
            )

        elif self.calib_step == 5:
            self.main.settings["cas_p_dist1"] = [x, y]
            self.lbl_status.setText(
                f"6. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨┐╨╛╨╗╨╡ ╨Ю╨С╨к╨Х╨Ь╨Р ╨Т╨в╨Ю╨а╨Ю╨Щ ╤Б╤В╤А╨╛╨║╨╕ -> {hotkey_display}"
            )

        elif self.calib_step == 6:
            self.main.settings["cas_p_vol2"] = [x, y]
            self.lbl_status.setText(f"7. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨║╨╜╨╛╨┐╨║╤Г ╨Я╨Ы╨о╨б (+) -> {hotkey_display}")

        elif self.calib_step == 7:
            self.main.settings["cas_p_plus"] = [x, y]
            self.lbl_status.setText(
                f"8. ╨Э╨░╨▓╨╡╨┤╨╕ ╨╜╨░ ╨║╨╜╨╛╨┐╨║╤Г ╨г╨Ф╨Р╨Ы╨Ш╨в╨м (X) ╨┐╨╡╤А╨▓╨╛╨╣ ╤Б╤В╤А╨╛╨║╨╕ -> {hotkey_display}"
            )

        elif self.calib_step == 8:
            self.main.settings["cas_p_x"] = [x, y]
            self.lbl_status.setText("тЬУ ╨Ъ╨░╨╗╨╕╨▒╤А╨╛╨▓╨║╨░ ╨╖╨░╨▓╨╡╤А╤И╨╡╨╜╨░! ╨Э╨░╤Б╤В╤А╨╛╨╣╨║╨╕ ╤Б╨╛╤Е╤А╨░╨╜╨╡╨╜╤Л.")
            self.lbl_status.setStyleSheet("color: #38BE1D;")
            self.main.save_settings()
            keyboard.remove_hotkey(self.calib_hotkey)

        self.calib_step += 1

    def run_automation(self):
        if not hasattr(self, "calculated_orders") or not self.calculated_orders:
            self.recalc_table()

        self.lbl_status.setText("╨Т╤Л╤Б╤В╨░╨▓╨╗╤П╤О ╨╛╤А╨┤╨╡╤А╨░... ╨Э╨░╨╢╨╝╨╕ ESC ╨┤╨╗╤П ╨╛╤Б╤В╨░╨╜╨╛╨▓╨║╨╕")
        self.lbl_status.setStyleSheet("color: #FF9F0A;")
        self.worker = CascadeWorker(
            self.main.settings, self.calculated_orders, self.main
        )
        self.worker.finished.connect(
            lambda: self.lbl_status.setText("╨Ъ╨░╤Б╨║╨░╨┤ ╨▓╤Л╤Б╤В╨░╨▓╨╗╨╡╨╜!")
        )
        self.worker.cancelled.connect(
            lambda: self.lbl_status.setText("╨Ю╤Б╤В╨░╨╜╨╛╨▓╨╗╨╡╨╜╨╛ ╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╤В╨╡╨╗╨╡╨╝ (ESC)")
        )
        self.worker.start()
