п»ї# cascade_tab.py
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
    """в•ЁРЇв•Ёв•›в•¤Р’в•Ёв•›в•Ёв•‘ в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв–“в•¤Р›в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•њв•Ёв•Ўв•Ёв•њв•Ёв••в•¤Рџ в•Ёв•‘в•Ёв•—в•Ёв••в•Ёв•‘в•Ёв•›в•Ёв–“"""

    finished = pyqtSignal()
    cancelled = pyqtSignal()  # в•ЁР±в•Ёв••в•Ёв”‚в•Ёв•њв•Ёв–‘в•Ёв•— в•Ёв•›в•Ёв–’ в•Ёв•›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв•Ў в•Ёв”ђв•Ёв•› ESC

    def __init__(self, settings, orders_data, main_window):
        super().__init__()
        self.settings = settings
        self.orders = orders_data
        self.main_window = main_window
        self._cancelled = False

    def run(self):
        # в•ЁР¤в•Ёв•›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв•‘в•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•¤Р›
        c_gear = self.settings.get("cas_p_gear")  # в•ЁРёв•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв•Ўв•¤Рђв•Ёв•Ўв•Ёв•њв•Ёв•‘в•Ёв–‘
        c_book = self.settings.get("cas_p_book")  # в•ЁРЇв•¤Р“в•Ёв•њв•Ёв•‘в•¤Р’ в•Ёв•ќв•Ёв•Ўв•Ёв•њв•¤Рћ в•ЁРЄв•Ёв•њв•Ёв••в•Ёв”‚в•Ёв–‘ в•Ёв•–в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•›в•Ёв•‘
        c_scrollbar = self.settings.get("cas_p_scrollbar")  # в•ЁРЇв•Ёв•›в•Ёв•—в•Ёв•–в•¤Р“в•Ёв•њв•Ёв•›в•Ёв•‘ в•¤Р‘в•Ёв•‘в•¤Рђв•Ёв•›в•Ёв•—в•Ёв•—в•Ёв–’в•Ёв–‘в•¤Рђв•Ёв–‘
        c_vol1 = self.settings.get("cas_p_vol1")
        c_dist1 = self.settings.get("cas_p_dist1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_plus = self.settings.get("cas_p_plus")
        c_x = self.settings.get("cas_p_x")

        # в•ЁР®в•¤Р’в•Ёв•—в•Ёв–‘в•Ёв”¤в•Ёв•‘в•Ёв–‘ - в•Ёв–“в•¤Р›в•Ёв–“в•Ёв•›в•Ёв”¤в•Ёв••в•Ёв•ќ в•Ёв•‘в•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•¤Р›
        print(f"[CASCADE] в•ЁРЄв•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•¤Р›:")
        print(f"  в•ЁРёв•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв•Ўв•¤Рђв•Ёв•Ўв•Ёв•њв•Ёв•‘в•Ёв–‘ (c_gear): {c_gear}")
        print(f"  в•ЁРЄв•Ёв•њв•Ёв••в•Ёв”‚в•Ёв–‘ в•Ёв•–в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•›в•Ёв•‘ (c_book): {c_book}")
        print(f"  в•ЁР®в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ 1 (c_vol1): {c_vol1}")
        print(f"  в•ЁР¤в•Ёв••в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•¤Р–в•Ёв••в•¤Рџ 1 (c_dist1): {c_dist1}")
        print(f"  в•ЁР®в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ 2 (c_vol2): {c_vol2}")
        print(f"  в•ЁРЇв•Ёв•—в•¤Рћв•¤Р‘в•Ёв••в•Ёв•‘ (c_plus): {c_plus}")
        print(f"  в•ЁРЄв•¤Рђв•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв••в•Ёв•‘ (c_x): {c_x}")
        print(f"  в•ЁР§в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•›в•Ёв•‘ в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв–“в•¤Р›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв••в•¤Рџ: {len(self.orders)}")

        # в•ЁРҐв•¤Р‘в•Ёв•—в•Ёв•• в•Ёв•њв•Ёв•Ў в•Ёв–“в•¤Р‘в•Ёв•Ў в•¤Р’в•Ёв•›в•¤Р—в•Ёв•‘в•Ёв•• в•Ёв•–в•Ёв–‘в•Ёв”¤в•Ёв–‘в•Ёв•њв•¤Р› - в•¤Р‘в•¤Р’в•Ёв•›в•Ёв”ђ
        if not (c_gear and c_book and c_vol1 and c_dist1 and c_vol2 and c_plus and c_x):
            return

        row_height = c_vol2[1] - c_vol1[1]

        # в•ЁР°в•Ёв•Ўв•Ёв”‚в•Ёв••в•¤Р‘в•¤Р’в•¤Рђв•Ёв••в•¤Рђв•¤Р“в•Ёв•Ўв•Ёв•ќ ESC в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв•›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв••
        def on_esc():
            self._cancelled = True
            # в•ЁРЇв•Ёв•›в•Ёв•‘в•Ёв–‘в•Ёв•–в•¤Р›в•Ёв–“в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв•›в•Ёв•‘в•Ёв•њв•Ёв•› в•Ёв•›в•Ёв–’в•¤Рђв•Ёв–‘в•¤Р’в•Ёв•њв•Ёв•›
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.cancelled.emit()

        keyboard.add_hotkey("esc", on_esc)

        try:
            # 1. в•ЁР®в•¤Р’в•Ёв•‘в•¤Рђв•¤Р›в•Ёв–“в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв•њв•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Јв•Ёв•‘в•Ёв•• (в•ЁРёв•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв•Ўв•¤Рђв•Ёв•Ўв•Ёв•њв•Ёв•‘в•Ёв–‘)
            if self._cancelled:
                return
            pyautogui.moveTo(c_gear[0], c_gear[1])
            pyautogui.click()
            time.sleep(0.15)

            # 2. в•ЁРўв•¤Р›в•Ёв–’в•Ёв••в•¤Рђв•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв”ђв•¤Р“в•Ёв•њв•Ёв•‘в•¤Р’ "в•ЁРЄв•Ёв•њв•Ёв••в•Ёв”‚в•Ёв–‘ в•Ёв•–в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•›в•Ёв•‘"
            if self._cancelled:
                return
            pyautogui.moveTo(c_book[0], c_book[1])
            pyautogui.click()
            time.sleep(0.15)

            # 3. в•ЁРЇв•Ёв•Ўв•¤Рђв•Ёв•Ўв•¤Р’в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв••в•Ёв–“в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•–в•¤Р“в•Ёв•њв•Ёв•›в•Ёв•‘ в•Ёв–“в•Ёв•њв•Ёв••в•Ёв•– (в•Ёв•Ўв•¤Р‘в•Ёв•—в•Ёв•• в•Ёв•‘в•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•Ёв–‘ в•¤Р‘в•Ёв•‘в•¤Рђв•Ёв•›в•Ёв•—в•Ёв•—в•Ёв–’в•Ёв–‘в•¤Рђв•Ёв–‘ в•Ёв•–в•Ёв–‘в•Ёв”¤в•Ёв–‘в•Ёв•њв•Ёв–‘)
            if self._cancelled:
                return
            if c_scrollbar:
                scrollbar_x = c_scrollbar[0]
                scrollbar_y_start = c_scrollbar[1]
                scrollbar_y_end = scrollbar_y_start + 700  # в•ЁРІв•¤Рџв•Ёв•њв•Ёв•Ўв•Ёв•ќ в•Ёв–“в•Ёв•њв•Ёв••в•Ёв•– в•Ёв•њв•Ёв–‘ 700px

                # в•ЁРЇв•Ёв•Ўв•¤Рђв•Ёв•Ўв•¤Р’в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв••в•Ёв–“в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•–в•¤Р“в•Ёв•њв•Ёв•›в•Ёв•‘: в•Ёв•њв•Ёв–‘в•Ёв•ўв•Ёв••в•Ёв•ќв•Ёв–‘в•Ёв•Ўв•Ёв•ќ, в•¤Р’в•¤Рџв•Ёв•њв•Ёв•Ўв•Ёв•ќ, в•Ёв•›в•¤Р’в•Ёв”ђв•¤Р“в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв•Ўв•Ёв•ќ
                pyautogui.moveTo(scrollbar_x, scrollbar_y_start)
                time.sleep(0.1)
                pyautogui.mouseDown(button="left")
                time.sleep(0.05)
                pyautogui.moveTo(scrollbar_x, scrollbar_y_end, duration=0.4)
                time.sleep(0.05)
                pyautogui.mouseUp(button="left")
                time.sleep(0.2)

            # в•ЁР¤в•Ёв•›в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•њв•Ёв••в•¤Р’в•Ёв•Ўв•Ёв•—в•¤Рњв•Ёв•њв•Ёв•›: в•Ёв•њв•Ёв•Ўв•¤Р‘в•Ёв•‘в•Ёв•›в•Ёв•—в•¤Рњв•Ёв•‘в•Ёв•› PageDown в•Ёв”¤в•Ёв•—в•¤Рџ в•¤Р’в•Ёв•›в•¤Р—в•Ёв•њв•Ёв•›в•¤Р‘в•¤Р’в•Ёв••
            pyautogui.moveTo(c_book[0], c_book[1] + 200)
            pyautogui.click()
            time.sleep(0.05)
            for _ in range(2):
                if self._cancelled:
                    return
                pyautogui.press("pagedown")
                time.sleep(0.03)

            # 4. в•ЁР®в•¤Р—в•Ёв••в•¤Р‘в•¤Р’в•Ёв•‘в•Ёв–‘ (в•¤Р“в•Ёв”¤в•Ёв–‘в•Ёв•—в•¤Рџв•Ёв•Ўв•Ёв•ќ в•¤Р‘в•¤Р’в•Ёв–‘в•¤Рђв•¤Р›в•Ёв•Ў в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв•• в•Ёв•‘в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤в•Ёв–‘)
            if self._cancelled:
                return
            print(
                f"[CASCADE] в•ЁРёв•Ёв–‘в•Ёв”‚ 4: в•ЁР­в•Ёв–‘в•Ёв•ўв•Ёв••в•Ёв•ќв•Ёв–‘в•¤Рћ в•Ёв•њв•Ёв–‘ в•Ёв•‘в•¤Рђв•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв••в•Ёв•‘ (X) в•Ёв”¤в•Ёв•—в•¤Рџ в•¤Р“в•Ёв”¤в•Ёв–‘в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв••в•¤Рџ в•Ёв•–в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•›в•Ёв•‘. в•ЁРЄв•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•¤Р›: {c_x}"
            )
            pyautogui.moveTo(c_x[0], c_x[1])
            for i in range(12):  # в•ЁР± в•Ёв•–в•Ёв–‘в•Ёв”ђв•Ёв–‘в•¤Р‘в•Ёв•›в•Ёв•ќ
                if self._cancelled:
                    return
                print(f"[CASCADE]   в•ЁР­в•Ёв–‘в•Ёв•ўв•Ёв–‘в•¤Р’в•Ёв••в•Ёв•Ў {i+1}/12 в•Ёв•њв•Ёв–‘ в•Ёв•‘в•¤Рђв•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв••в•Ёв•‘ (X)")
                pyautogui.click()
                time.sleep(0.02)

            # 5. в•ЁР±в•Ёв•›в•Ёв•–в•Ёв”¤в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв•њв•¤Р“в•Ёв•ўв•Ёв•њв•Ёв•›в•Ёв•Ў в•Ёв•‘в•Ёв•›в•Ёв•—в•Ёв••в•¤Р—в•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв–“в•Ёв•› в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘
            if self._cancelled:
                return
            print(
                f"[CASCADE] в•ЁРёв•Ёв–‘в•Ёв”‚ 5: в•ЁР­в•Ёв–‘в•Ёв•ўв•Ёв••в•Ёв•ќв•Ёв–‘в•¤Рћ в•Ёв•њв•Ёв–‘ в•Ёв”ђв•Ёв•—в•¤Рћв•¤Р‘в•Ёв••в•Ёв•‘ (+) в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв”¤в•Ёв•›в•Ёв–’в•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв••в•¤Рџ в•Ёв•–в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•›в•Ёв•‘. в•ЁРЄв•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•¤Р›: {c_plus}. в•ЁРЄв•Ёв•›в•Ёв•—в•Ёв••в•¤Р—в•Ёв•Ўв•¤Р‘в•¤Р’в•Ёв–“в•Ёв•› в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв”¤в•Ёв•›в•Ёв–’в•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв••в•¤Рџ: {len(self.orders) - 1}"
            )
            pyautogui.moveTo(c_plus[0], c_plus[1])
            for i in range(len(self.orders) - 1):
                if self._cancelled:
                    return
                print(f"[CASCADE]   в•ЁР­в•Ёв–‘в•Ёв•ўв•Ёв–‘в•¤Р’в•Ёв••в•Ёв•Ў {i+1}/{len(self.orders)-1} в•Ёв•њв•Ёв–‘ в•Ёв”ђв•Ёв•—в•¤Рћв•¤Р‘в•Ёв••в•Ёв•‘ (+)")
                pyautogui.click()
                time.sleep(0.03)

            # 6. в•ЁР§в•Ёв–‘в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•њв•¤Рџв•Ёв•Ўв•Ёв•ќ в•Ёв•–в•Ёв•њв•Ёв–‘в•¤Р—в•Ёв•Ўв•Ёв•њв•Ёв••в•¤Рџ
            print(
                f"[CASCADE] в•ЁРёв•Ёв–‘в•Ёв”‚ 6: в•ЁР§в•Ёв–‘в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•њв•¤Рџв•¤Рћ в•Ёв•›в•Ёв–’в•¤Рљв•¤РЎв•Ёв•ќв•¤Р› в•Ёв•• в•Ёв”¤в•Ёв••в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•¤Р–в•Ёв••в•Ёв••. в•ЁРўв•¤Р›в•¤Р‘в•Ёв•›в•¤Р’в•Ёв–‘ в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв••: {row_height}"
            )
            for i, order in enumerate(self.orders):
                if self._cancelled:
                    return
                cur_y = c_vol1[1] + (i * row_height)
                print(
                    f"[CASCADE]   в•ЁР§в•Ёв–‘в•¤Рџв•Ёв–“в•Ёв•‘в•Ёв–‘ {i+1}: в•Ёв•›в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ={order['vol']:.2f}, в•Ёв”¤в•Ёв••в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•¤Р–в•Ёв••в•¤Рџ={order['dist']:.2f}%, Y={cur_y}"
                )

                # --- в•ЁР®в•Ёв–’в•¤Рљв•¤РЎв•Ёв•ќ ---
                vol_str = f"{order['vol']:.2f}".replace(",", ".")
                pyperclip.copy(vol_str)
                print(
                    f"[CASCADE]     в•ЁРўв•¤Р›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв–“в•Ёв•—в•¤Рџв•¤Рћ в•Ёв•›в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ {vol_str} в•Ёв–“ в•Ёв•‘в•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’в•¤Р› ({c_vol1[0]}, {cur_y})"
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

                # --- в•ЁР¤в•Ёв••в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•¤Р–в•Ёв••в•¤Рџ ---
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

            # 7. в•ЁР§в•Ёв–‘в•Ёв•‘в•¤Рђв•¤Р›в•Ёв–“в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв•њв•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Јв•Ёв•‘в•Ёв•• (Esc)
            if not self._cancelled:
                time.sleep(0.1)
                pyautogui.press("esc")
                self.finished.emit()
        finally:
            # в•ЁРів•Ёв–’в•Ёв••в•¤Рђв•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•¤Р•в•Ёв•›в•¤Р’в•Ёв•‘в•Ёв•Ўв•Ёв•Ј ESC
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

        # в•ЁР±в•Ёв•›в•¤Р•в•¤Рђв•Ёв–‘в•Ёв•њв•¤Рџв•Ёв•Ўв•Ёв•ќ в•¤Р‘в•¤Р‘в•¤Р›в•Ёв•—в•Ёв•‘в•Ёв•• в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв•ќв•Ёв–‘в•¤Р‘в•¤Рв•¤Р’в•Ёв–‘в•Ёв–’в•Ёв••в•¤Рђв•Ёв•›в•Ёв–“в•Ёв–‘в•Ёв•њв•Ёв••в•¤Рџ
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

        # --- в•ЁР±в•¤Р’в•Ёв••в•Ёв•—в•Ёв•• в•Ёв”¤в•Ёв•—в•¤Рџ в•¤Рќв•¤Р’в•Ёв•›в•Ёв”‚в•Ёв•› в•Ёв•›в•Ёв•‘в•Ёв•њв•Ёв–‘ ---
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
            /* в•ЁР±в•¤Р’в•Ёв••в•Ёв•—в•¤Рњ в•Ёв•‘в•Ёв•њв•Ёв•›в•Ёв”ђв•Ёв•›в•Ёв•‘ в•Ёв”ђв•¤Рђв•Ёв•›в•¤Р–в•Ёв•Ўв•Ёв•њв•¤Р’в•Ёв•›в•Ёв–“ (в•ЁРЁв•¤Р‘в•Ёв”ђв•¤Рђв•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв•›) */
            QPushButton.percBtn {
                background-color: #252525;
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton.percBtn:checked {
                background-color: #38BE1D; /* в•ЁРїв•¤Рђв•Ёв•‘в•Ёв•›-в•Ёв•–в•Ёв•Ўв•Ёв•—в•Ёв•Ўв•Ёв•њв•¤Р›в•Ёв•Ј */
                color: black;             /* в•ЁР·в•Ёв•Ўв•¤Рђв•Ёв•њв•¤Р›в•Ёв•Ј в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р‘в•¤Р’ - в•¤Р—в•Ёв••в•¤Р’в•Ёв–‘в•Ёв•Ўв•¤Р’в•¤Р‘в•¤Рџ в•Ёв•›в•¤Р’в•Ёв•—в•Ёв••в•¤Р—в•Ёв•њв•Ёв•› */
                border: 1px solid #38BE1D;
            }
            QPushButton.percBtn:hover { border: 1px solid #555; }
            
            QComboBox {
                background: #1A1A1A; color: white; border: 1px solid #333; padding: 2px;
                min-width: 60px; /* в•ЁР·в•¤Р’в•Ёв•›в•Ёв–’в•¤Р› в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р‘в•¤Р’ в•Ёв•њв•Ёв•Ў в•¤Рђв•Ёв•Ўв•Ёв•–в•Ёв–‘в•Ёв•—в•¤Р‘в•¤Рџ */
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

        # --- в•ЁРЎв•ЁР«в•ЁР®в•ЁРЄ 1: в•ЁР®в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ ---
        gb_vol = QGroupBox("1. в•ЁР®в•Ёв–’в•¤Р™в•Ёв••в•Ёв•Ј в•Ёв•›в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ в•Ёв•‘в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤в•Ёв–‘")
        l_vol = QVBoxLayout()

        h_perc = QHBoxLayout()
        self.group_btns = []
        for text in ["25%", "50%", "75%", "100%"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "percBtn")  # в•ЁР¤в•Ёв•—в•¤Рџ CSS
            btn.setObjectName("percBtn")  # в•ЁР¤в•Ёв•—в•¤Рџ Qt
            btn.clicked.connect(self.on_perc_click)
            self.group_btns.append(btn)
            h_perc.addWidget(btn)

        self.group_btns[3].setChecked(True)  # 100% в•Ёв”ђв•Ёв•› в•¤Р“в•Ёв•ќв•Ёв•›в•Ёв•—в•¤Р—в•Ёв–‘в•Ёв•њв•Ёв••в•¤Рћ

        self.lbl_total_vol = QLabel("в•ЁРЁв•¤Р’в•Ёв•›в•Ёв”‚в•Ёв•› в•Ёв–“ в•Ёв•‘в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤: 0 $")
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt; margin-top: 5px;"
        )
        self.lbl_total_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)

        l_vol.addLayout(h_perc)
        l_vol.addWidget(self.lbl_total_vol)
        gb_vol.setLayout(l_vol)
        layout.addWidget(gb_vol)

        # --- в•ЁРЎв•ЁР«в•ЁР®в•ЁРЄ 2: в•ЁР­в•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Јв•Ёв•‘в•Ёв•• (в•ЁР±в•Ёв•Ўв•¤Р’в•Ёв•‘в•Ёв–‘ в•Ёв••в•¤Р‘в•Ёв”ђв•¤Рђв•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв–‘) ---
        gb_set = QGroupBox("2. в•ЁР­в•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Јв•Ёв•‘в•Ёв•• в•¤Рђв•Ёв–‘в•¤Р‘в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв••")
        grid = QGridLayout()
        grid.setHorizontalSpacing(15)  # в•ЁР®в•¤Р’в•¤Р‘в•¤Р’в•¤Р“в•Ёв”ђ в•Ёв•ќв•Ёв•Ўв•Ёв•ўв•Ёв”¤в•¤Р“ в•Ёв•‘в•Ёв•›в•Ёв•—в•Ёв•›в•Ёв•њв•Ёв•‘в•Ёв–‘в•Ёв•ќв•Ёв••
        grid.setVerticalSpacing(8)

        # в•ЁРЁв•¤Р‘в•Ёв”ђв•Ёв•›в•Ёв•—в•¤Рњв•Ёв•–в•¤Р“в•Ёв•Ўв•Ёв•ќ QLabel в•¤Р‘ wordWrap, в•¤Р—в•¤Р’в•Ёв•›в•Ёв–’в•¤Р› в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р‘в•¤Р’ в•Ёв”ђв•Ёв•Ўв•¤Рђв•Ёв•Ўв•Ёв•њв•Ёв•›в•¤Р‘в•Ёв••в•Ёв•—в•¤Р‘в•¤Рџ в•Ёв•Ўв•¤Р‘в•Ёв•—в•Ёв•• в•¤Р—в•¤Р’в•Ёв•›
        l1 = QLabel("в•ЁРЄв•Ёв•›в•Ёв•—-в•Ёв–“в•Ёв•›:")
        grid.addWidget(l1, 0, 0)
        self.sb_count = QSpinBox()
        self.sb_count.setRange(2, 20)
        self.sb_count.setValue(5)
        self.sb_count.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_count.setObjectName("spinInner")
        self.sb_count_wrap = self._wrap_spinbox(self.sb_count)
        grid.addWidget(self.sb_count_wrap, 0, 1)

        l2 = QLabel("в•ЁР¬в•Ёв••в•Ёв•њ.в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв•Ўв•¤Рђ ($):")
        grid.addWidget(l2, 0, 2)
        self.sb_min = QDoubleSpinBox()
        self.sb_min.setRange(1, 1000)
        self.sb_min.setValue(6)
        self.sb_min.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_min.setObjectName("spinInner")
        self.sb_min_wrap = self._wrap_spinbox(self.sb_min)
        grid.addWidget(self.sb_min_wrap, 0, 3)

        l3 = QLabel("в•ЁРІв•Ёв••в•Ёв”ђ:")
        grid.addWidget(l3, 1, 0)
        self.cb_type = QComboBox()
        # в•ЁР±в•Ёв•›в•Ёв•‘в•¤Рђв•Ёв–‘в•¤Р’в•Ёв••в•Ёв•ќ в•Ёв•њв•Ёв–‘в•Ёв•–в•Ёв–“в•Ёв–‘в•Ёв•њв•Ёв••в•¤Рџ, в•¤Р—в•¤Р’в•Ёв•›в•Ёв–’в•¤Р› в•Ёв–“в•Ёв•—в•Ёв–‘в•Ёв•–в•Ёв••в•Ёв•—в•Ёв••
        self.cb_type.addItems(
            ["в•ЁР°в•Ёв–‘в•Ёв–“в•Ёв•њв•Ёв•›в•Ёв•ќв•Ёв•Ўв•¤Рђв•Ёв•њв•Ёв•›", "в•ЁР¬в•Ёв–‘в•¤Р’в•¤Рђв•Ёв•Ўв•¤Рв•Ёв•‘в•Ёв–‘ x1.2", "в•ЁР¬в•Ёв–‘в•¤Р’в•¤Рђв•Ёв•Ўв•¤Рв•Ёв•‘в•Ёв–‘ x1.5", "в•ЁР в•Ёв”‚в•¤Рђв•Ёв•Ўв•¤Р‘в•¤Р‘в•Ёв••в•Ёв–“в•Ёв•њв•Ёв•› x2"]
        )
        self.cb_type.setMinimumWidth(70)  # в•ЁРЎв•Ёв•›в•Ёв•—в•Ёв•Ўв•Ёв•Ў в•Ёв•‘в•Ёв•›в•Ёв•ќв•Ёв”ђв•Ёв–‘в•Ёв•‘в•¤Р’в•Ёв•њв•Ёв–‘в•¤Рџ в•¤Рв•Ёв••в•¤Рђв•Ёв••в•Ёв•њв•Ёв–‘
        grid.addWidget(self.cb_type, 1, 1)

        l4 = QLabel("в•ЁРёв•Ёв–‘в•Ёв”‚ (%):")
        grid.addWidget(l4, 1, 2)
        self.sb_dist = QDoubleSpinBox()
        self.sb_dist.setRange(0.01, 10.0)
        self.sb_dist.setValue(0.1)
        self.sb_dist.setSingleStep(0.05)
        self.sb_dist.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_dist.setObjectName("spinInner")
        self.sb_dist_wrap = self._wrap_spinbox(self.sb_dist)
        grid.addWidget(self.sb_dist_wrap, 1, 3)

        # в•ЁР±в•Ёв•›в•Ёв–’в•¤Р›в•¤Р’в•Ёв••в•¤Рџ
        self.sb_count.valueChanged.connect(self.recalc_table)
        self.sb_min.valueChanged.connect(self.recalc_table)
        self.cb_type.currentIndexChanged.connect(self.recalc_table)
        self.sb_dist.valueChanged.connect(self.recalc_table)

        gb_set.setLayout(grid)
        layout.addWidget(gb_set)

        # --- в•ЁРЎв•ЁР«в•ЁР®в•ЁРЄ 3: в•ЁРІв•Ёв–‘в•Ёв–’в•Ёв•—в•Ёв••в•¤Р–в•Ёв–‘ (в•ЁРЁв•¤Р‘в•Ёв”ђв•¤Рђв•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв•› в•Ёв•›в•Ёв–’в•¤Рђв•Ёв•Ўв•Ёв•–в•Ёв–‘в•Ёв•њв•Ёв••в•Ёв•Ў) ---
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["в•ЁР®в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ ($)", "в•ЁР¤в•Ёв••в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•¤Р–в•Ёв••в•¤Рџ (%)"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        # в•ЁРів•Ёв–“в•Ёв•Ўв•Ёв•—в•Ёв••в•¤Р—в•Ёв••в•Ёв–“в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв–“в•¤Р›в•¤Р‘в•Ёв•›в•¤Р’в•¤Р“ в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘, в•¤Р—в•¤Р’в•Ёв•›в•Ёв–’в•¤Р› в•¤Рв•¤Рђв•Ёв••в•¤Р”в•¤Р’ в•Ёв•њв•Ёв•Ў в•¤Рђв•Ёв•Ўв•Ёв•–в•Ёв–‘в•Ёв•—в•¤Р‘в•¤Рџ
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setRowCount(0)
        self.table.setFixedHeight(120)
        # в•ЁРЎв•Ёв–‘в•Ёв•–в•Ёв•›в•Ёв–“в•¤Р›в•Ёв•Ј в•¤Р‘в•¤Р’в•Ёв••в•Ёв•—в•¤Рњ в•¤Р’в•Ёв–‘в•Ёв–’в•Ёв•—в•Ёв••в•¤Р–в•¤Р› (в•¤Р’в•Ёв•›в•¤Р—в•Ёв•њв•¤Р›в•Ёв•Ў в•¤Рђв•Ёв–‘в•Ёв•–в•Ёв•ќв•Ёв•Ўв•¤Рђв•¤Р› в•Ёв–“в•¤Р›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв–“в•¤Рџв•¤Р’в•¤Р‘в•¤Рџ в•Ёв–“ apply_scale)
        self.table.setStyleSheet(
            "QTableWidget::item { font-size: 6pt; padding: 0px 2px; }"
            "QHeaderView::section { font-size: 8pt; padding: 2px; }"
            "selection-background-color: #38BE1D; selection-color: black;"
        )
        layout.addWidget(self.table)

        # --- в•ЁРЎв•ЁР«в•ЁР®в•ЁРЄ 4: в•ЁРЄв•Ёв•њв•Ёв•›в•Ёв”ђв•Ёв•‘в•Ёв•• ---
        h_btn = QHBoxLayout()
        self.btn_calib = QPushButton("в•ЁРЄв•ЁР в•ЁР«в•ЁРЁв•ЁРЎв•ЁР°в•ЁР®в•ЁРўв•ЁРЄв•ЁР ")
        self.btn_calib.setStyleSheet(
            "background: #333; color: white; padding: 8px; border: 1px solid #555;"
        )
        self.btn_calib.clicked.connect(self.start_calibration)

        self.btn_apply = QPushButton("в•ЁРўв•ЁР»в•ЁР±в•ЁРІв•ЁР в•ЁРўв•ЁРЁв•ЁРІв•ЁРј")
        self.btn_apply.setStyleSheet(
            "background: #38BE1D; color: black; font-weight: bold; padding: 8px; font-size: 10pt;"
        )
        self.btn_apply.clicked.connect(self.run_automation)

        h_btn.addWidget(self.btn_calib)
        h_btn.addWidget(self.btn_apply)
        layout.addLayout(h_btn)

        # в•ЁР±в•¤Р’в•Ёв–‘в•¤Р’в•¤Р“в•¤Р‘ (в•¤Р‘ в•Ёв”ђв•Ёв•Ўв•¤Рђв•Ёв•Ўв•Ёв•њв•Ёв•›в•¤Р‘в•Ёв•›в•Ёв•ќ в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р‘в•¤Р’в•Ёв–‘)
        self.lbl_status = QLabel("в•ЁР­в•¤Р“в•Ёв•ўв•Ёв•њв•Ёв–‘ в•Ёв•‘в•Ёв–‘в•Ёв•—в•Ёв••в•Ёв–’в•¤Рђв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв–‘ (7 в•¤Рв•Ёв–‘в•Ёв”‚в•Ёв•›в•Ёв–“)")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)  # <-- в•ЁРўв•ЁР в•ЁР¦в•ЁР­в•ЁР®: в•ЁРІв•Ёв•Ўв•Ёв•‘в•¤Р‘в•¤Р’ в•Ёв–’в•¤Р“в•Ёв”¤в•Ёв•Ўв•¤Р’ в•Ёв”ђв•Ёв•Ўв•¤Рђв•Ёв•Ўв•Ёв•њв•Ёв•›в•¤Р‘в•Ёв••в•¤Р’в•¤Рњв•¤Р‘в•¤Рџ
        self.lbl_status.setStyleSheet(
            "color: #666; font-size: 7pt; margin-bottom: 5px;"
        )
        layout.addWidget(self.lbl_status)

        # в•ЁРЇв•¤Рђв•Ёв••в•Ёв•ќв•Ёв•Ўв•Ёв•њв•¤Рџв•Ёв•Ўв•Ёв•ќ в•Ёв•ќв•Ёв–‘в•¤Р‘в•¤Рв•¤Р’в•Ёв–‘в•Ёв–’в•Ёв••в•¤Рђв•Ёв•›в•Ёв–“в•Ёв–‘в•Ёв•њв•Ёв••в•Ёв•Ў в•Ёв”ђв•Ёв•›в•Ёв”¤ в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р“в•¤Р™в•Ёв••в•Ёв•Ј в•¤Рђв•Ёв–‘в•Ёв•–в•Ёв•ќв•Ёв•Ўв•¤Рђ в•Ёв••в•Ёв•њв•¤Р’в•Ёв•Ўв•¤Рђв•¤Р”в•Ёв•Ўв•Ёв•Јв•¤Р‘в•Ёв–‘
        self.apply_scale()

    def apply_scale(self):
        """
        в•ЁРЇв•Ёв•›в•Ёв”¤в•Ёв”‚в•Ёв•›в•Ёв•њв•¤Рџв•Ёв•Ўв•¤Р’ в•¤Рђв•Ёв–‘в•Ёв•–в•Ёв•ќв•Ёв•Ўв•¤Рђв•¤Р› в•¤Рќв•Ёв•—в•Ёв•Ўв•Ёв•ќв•Ёв•Ўв•Ёв•њв•¤Р’в•Ёв•›в•Ёв–“ в•Ёв”ђв•Ёв•›в•Ёв”¤ в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р“в•¤Р™в•Ёв••в•Ёв•Ј в•Ёв•ќв•Ёв–‘в•¤Р‘в•¤Рв•¤Р’в•Ёв–‘в•Ёв–’ в•Ёв••в•Ёв•њв•¤Р’в•Ёв•Ўв•¤Рђв•¤Р”в•Ёв•Ўв•Ёв•Јв•¤Р‘в•Ёв–‘ (settings['scale']),
        в•¤Р—в•¤Р’в•Ёв•›в•Ёв–’в•¤Р› в•Ёв•њв•Ёв–‘ в•Ёв–“в•Ёв•‘в•Ёв•—в•Ёв–‘в•Ёв”¤в•Ёв•‘в•Ёв•Ў в•Ёв•‘в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤в•Ёв•›в•Ёв–“ в•Ёв•њв•Ёв••в•¤Р—в•Ёв•Ўв•Ёв”‚в•Ёв•› в•Ёв•њв•Ёв•Ў в•Ёв–“в•¤Р›в•Ёв•—в•Ёв•Ўв•Ёв•–в•Ёв–‘в•Ёв•—в•Ёв•› в•Ёв•–в•Ёв–‘ в•¤Рђв•Ёв–‘в•Ёв•ќв•Ёв•‘в•Ёв•• в•Ёв•• в•¤Р’в•Ёв•Ўв•Ёв•‘в•¤Р‘в•¤Р’ в•Ёв•њв•Ёв•Ў в•¤Рђв•Ёв•Ўв•Ёв•–в•Ёв–‘в•Ёв•—в•¤Р‘в•¤Рџ.
        """
        scale = self.main.settings.get("scale", 100)
        base_scale = getattr(self.main, "base_scale", 150)
        ratio = scale / float(base_scale)
        sc = scale / 100.0

        # в•ЁРЄв•Ёв•њв•Ёв•›в•Ёв”ђв•Ёв•‘в•Ёв–‘ в•¤Р’в•Ёв••в•Ёв”ђв•Ёв•›в•Ёв–“: в•Ёв•‘в•Ёв•›в•Ёв•ќв•Ёв”ђв•Ёв–‘в•Ёв•‘в•¤Р’в•Ёв•њв•Ёв–‘в•¤Рџ в•¤Рв•Ёв••в•¤Рђв•Ёв••в•Ёв•њв•Ёв–‘ в•Ёв•• в•¤Р‘в•Ёв••в•Ёв•њв•¤Р•в•¤Рђв•Ёв•›в•Ёв•њв•Ёв•њв•Ёв•› в•¤Р‘ "в•ЁРЄв•Ёв•›в•Ёв•—-в•Ёв–“в•Ёв•›"
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

        # в•ЁРЁв•¤Р’в•Ёв•›в•Ёв”‚в•Ёв•›в•Ёв–“в•¤Р›в•Ёв•Ј в•Ёв•›в•Ёв–’в•¤Рљв•Ёв•Ўв•Ёв•ќ в•Ёв•‘в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤в•Ёв–‘
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt; margin-top: 5px;"
        )

        # в•ЁРІв•Ёв–‘в•Ёв–’в•Ёв•—в•Ёв••в•¤Р–в•Ёв–‘ в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв•Ўв•¤Рђв•Ёв•›в•Ёв–“
        self.table.verticalHeader().setDefaultSectionSize(int(14 * sc))
        self.table.setFixedHeight(int(80 * sc))
        item_font = max(6, int(6 * ratio))
        header_font = max(6, int(8 * ratio))
        self.table.setStyleSheet(
            f"QTableWidget::item {{ font-size: {item_font}pt; padding: 0px 1px; margin: 0px; }}"
            f"QHeaderView::section {{ font-size: {header_font}pt; padding: 1px; }}"
            "selection-background-color: #38BE1D; selection-color: black;"
        )

        # в•ЁР±в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв–‘ в•¤Р‘в•¤Р’в•Ёв–‘в•¤Р’в•¤Р“в•¤Р‘в•Ёв–‘ в•Ёв–“в•Ёв•њв•Ёв••в•Ёв•–в•¤Р“
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

        self.lbl_total_vol.setText(f"в•ЁРЁв•¤Р’в•Ёв•›в•Ёв”‚в•Ёв•› в•Ёв–“ в•Ёв•‘в•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤: {total_vol:.1f} $")

        if total_vol <= 0:
            self.table.setRowCount(0)
            return

        count = self.sb_count.value()
        mult = self.get_multiplier()
        min_size = self.sb_min.value()
        dist_step = self.sb_dist.value()

        # в•ЁР¬в•Ёв–‘в•¤Р’в•Ёв•Ўв•Ёв•ќв•Ёв–‘в•¤Р’в•Ёв••в•Ёв•‘в•Ёв–‘
        weights = [mult**i for i in range(count)]
        total_weight = sum(weights)
        raw_volumes = [(w / total_weight) * total_vol for w in weights]

        # в•ЁРЈв•¤Рђв•¤Р“в•Ёв”ђв•Ёв”ђв•Ёв••в•¤Рђв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв–‘ в•Ёв•ќв•Ёв•Ўв•Ёв•—в•Ёв•›в•¤Р—в•Ёв••
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

        # в•ЁР§в•Ёв–‘в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•њв•Ёв•Ўв•Ёв•њв•Ёв••в•Ёв•Ў в•¤Р’в•Ёв–‘в•Ёв–’в•Ёв•—в•Ёв••в•¤Р–в•¤Р›
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
        # в•ЁРЇв•Ёв•›в•Ёв•—в•¤Р“в•¤Р—в•Ёв–‘в•Ёв•Ўв•Ёв•ќ в•Ёв”‚в•Ёв•›в•¤Рђв•¤Рџв•¤Р—в•¤Р“в•¤Рћ в•Ёв•‘в•Ёв•—в•Ёв–‘в•Ёв–“в•Ёв••в•¤Рв•¤Р“ в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв•–в•Ёв–‘в•¤Р•в•Ёв–“в•Ёв–‘в•¤Р’в•Ёв–‘ в•Ёв•‘в•Ёв•›в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв••в•Ёв•њв•Ёв–‘в•¤Р’ в•Ёв••в•Ёв•– в•Ёв•њв•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Ўв•Ёв•‘
        self.calib_hotkey = self.main.settings.get("hk_coords", "f2").lower()
        hotkey_display = self.calib_hotkey.upper().replace("+", " + ")

        self.lbl_status.setText(
            f"1. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•ЁРёв•ЁРҐв•ЁР±в•ЁРІв•ЁРҐв•ЁР°в•ЁРҐв•ЁР­в•ЁРЄв•ЁРі в•Ёв•њв•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Ўв•Ёв•‘ -> в•Ёв•њв•Ёв–‘в•Ёв•ўв•Ёв•ќв•Ёв•• {hotkey_display}"
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
                f"2. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•Ёв”ђв•¤Р“в•Ёв•њв•Ёв•‘в•¤Р’ в•Ёв•ќв•Ёв•Ўв•Ёв•њв•¤Рћ 'в•ЁРЄв•ЁР­в•ЁРЁв•ЁРЈв•ЁР  в•ЁР§в•ЁР в•ЁРїв•ЁРўв•ЁР®в•ЁРЄ' -> {hotkey_display}"
            )

        elif self.calib_step == 2:
            self.main.settings["cas_p_book"] = [x, y]
            self.lbl_status.setText(
                f"3. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•ЁРЇв•ЁР®в•ЁР«в•ЁР§в•ЁРів•ЁР­в•ЁР®в•ЁРЄ в•ЁР±в•ЁРЄв•ЁР°в•ЁР®в•ЁР«в•ЁР«в•ЁРЎв•ЁР в•ЁР°в•ЁР  (в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•›в•¤Р‘в•Ёв–‘ в•Ёв”ђв•¤Рђв•Ёв•›в•Ёв•‘в•¤Рђв•¤Р“в•¤Р’в•Ёв•‘в•Ёв•• в•Ёв–“в•Ёв•њв•Ёв••в•Ёв•–в•¤Р“) -> {hotkey_display}\n"
                f"(в•ЁРЅв•¤Р’в•Ёв•› в•Ёв•њв•¤Р“в•Ёв•ўв•Ёв•њв•Ёв•› в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв•‘в•Ёв•›в•¤Рђв•¤Рђв•Ёв•Ўв•Ёв•‘в•¤Р’в•Ёв•њв•Ёв•›в•Ёв”‚в•Ёв•› в•¤Р‘в•Ёв•‘в•¤Рђв•Ёв•›в•Ёв•—в•Ёв•—в•Ёв••в•Ёв•њв•Ёв”‚в•Ёв–‘ в•Ёв•‘ в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв–‘в•Ёв•ќ в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв•Ўв•¤Рђв•Ёв•›в•Ёв–“)"
            )

        elif self.calib_step == 3:
            self.main.settings["cas_p_scrollbar"] = [x, y]
            self.lbl_status.setText(
                f"4. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•Ў в•Ёв–“в•Ёв–“в•Ёв•›в•Ёв”¤в•Ёв–‘ в•ЁР®в•ЁРЎв•ЁРєв•ЁРҐв•ЁР¬в•ЁР  в•Ёв”ђв•Ёв•Ўв•¤Рђв•Ёв–“в•Ёв•›в•Ёв•Ј в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв•• -> {hotkey_display}"
            )

        elif self.calib_step == 4:
            self.main.settings["cas_p_vol1"] = [x, y]
            self.lbl_status.setText(
                f"5. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•Ў в•ЁР¤в•ЁРЁв•ЁР±в•ЁРІв•ЁР в•ЁР­в•ЁР¶в•ЁРЁв•ЁРЁ (0%) в•Ёв”ђв•Ёв•Ўв•¤Рђв•Ёв–“в•Ёв•›в•Ёв•Ј в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв•• -> {hotkey_display}"
            )

        elif self.calib_step == 5:
            self.main.settings["cas_p_dist1"] = [x, y]
            self.lbl_status.setText(
                f"6. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•Ёв”ђв•Ёв•›в•Ёв•—в•Ёв•Ў в•ЁР®в•ЁРЎв•ЁРєв•ЁРҐв•ЁР¬в•ЁР  в•ЁРўв•ЁРІв•ЁР®в•ЁР°в•ЁР®в•ЁР© в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв•• -> {hotkey_display}"
            )

        elif self.calib_step == 6:
            self.main.settings["cas_p_vol2"] = [x, y]
            self.lbl_status.setText(f"7. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•Ёв•‘в•Ёв•њв•Ёв•›в•Ёв”ђв•Ёв•‘в•¤Р“ в•ЁРЇв•ЁР«в•ЁРѕв•ЁР± (+) -> {hotkey_display}")

        elif self.calib_step == 7:
            self.main.settings["cas_p_plus"] = [x, y]
            self.lbl_status.setText(
                f"8. в•ЁР­в•Ёв–‘в•Ёв–“в•Ёв•Ўв•Ёв”¤в•Ёв•• в•Ёв•њв•Ёв–‘ в•Ёв•‘в•Ёв•њв•Ёв•›в•Ёв”ђв•Ёв•‘в•¤Р“ в•ЁРів•ЁР¤в•ЁР в•ЁР«в•ЁРЁв•ЁРІв•ЁРј (X) в•Ёв”ђв•Ёв•Ўв•¤Рђв•Ёв–“в•Ёв•›в•Ёв•Ј в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•‘в•Ёв•• -> {hotkey_display}"
            )

        elif self.calib_step == 8:
            self.main.settings["cas_p_x"] = [x, y]
            self.lbl_status.setText("С‚Р¬РЈ в•ЁРЄв•Ёв–‘в•Ёв•—в•Ёв••в•Ёв–’в•¤Рђв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв–‘ в•Ёв•–в•Ёв–‘в•Ёв–“в•Ёв•Ўв•¤Рђв•¤Рв•Ёв•Ўв•Ёв•њв•Ёв–‘! в•ЁР­в•Ёв–‘в•¤Р‘в•¤Р’в•¤Рђв•Ёв•›в•Ёв•Јв•Ёв•‘в•Ёв•• в•¤Р‘в•Ёв•›в•¤Р•в•¤Рђв•Ёв–‘в•Ёв•њв•Ёв•Ўв•Ёв•њв•¤Р›.")
            self.lbl_status.setStyleSheet("color: #38BE1D;")
            self.main.save_settings()
            keyboard.remove_hotkey(self.calib_hotkey)

        self.calib_step += 1

    def run_automation(self):
        if not hasattr(self, "calculated_orders") or not self.calculated_orders:
            self.recalc_table()

        self.lbl_status.setText("в•ЁРўв•¤Р›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв–“в•Ёв•—в•¤Рџв•¤Рћ в•Ёв•›в•¤Рђв•Ёв”¤в•Ёв•Ўв•¤Рђв•Ёв–‘... в•ЁР­в•Ёв–‘в•Ёв•ўв•Ёв•ќв•Ёв•• ESC в•Ёв”¤в•Ёв•—в•¤Рџ в•Ёв•›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•Ёв•›в•Ёв–“в•Ёв•‘в•Ёв••")
        self.lbl_status.setStyleSheet("color: #FF9F0A;")
        self.worker = CascadeWorker(
            self.main.settings, self.calculated_orders, self.main
        )
        self.worker.finished.connect(
            lambda: self.lbl_status.setText("в•ЁРЄв•Ёв–‘в•¤Р‘в•Ёв•‘в•Ёв–‘в•Ёв”¤ в•Ёв–“в•¤Р›в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њ!")
        )
        self.worker.cancelled.connect(
            lambda: self.lbl_status.setText("в•ЁР®в•¤Р‘в•¤Р’в•Ёв–‘в•Ёв•њв•Ёв•›в•Ёв–“в•Ёв•—в•Ёв•Ўв•Ёв•њв•Ёв•› в•Ёв”ђв•Ёв•›в•Ёв•—в•¤Рњв•Ёв•–в•Ёв•›в•Ёв–“в•Ёв–‘в•¤Р’в•Ёв•Ўв•Ёв•—в•Ёв•Ўв•Ёв•ќ (ESC)")
        )
        self.worker.start()
