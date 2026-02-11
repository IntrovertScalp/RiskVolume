# cascade_tab.py
import time
import pyautogui
import keyboard
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
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

# Глобальный коэффициент скорости/задержки
SPEED_FACTOR = 0.001


def fast_sleep(delay):
    time.sleep(delay * SPEED_FACTOR)


class CascadeWorker(QThread):
    """Поток для выполнения кликов"""

    finished = pyqtSignal()
    cancelled = pyqtSignal()

    def __init__(self, settings, orders_data, main_window):
        super().__init__()
        self.settings = settings
        self.orders = orders_data
        self.main_window = main_window
        self._cancelled = False

    def get_last_cell_coords(self):
        """Вычислить координаты кнопок на основе высоты ячеек.

        Возвращает координаты для указанной по индексу ячейки (1-based).
        Если index=None — возвращает координаты для 2-й ячейки (поведение по умолчанию).
        """
        c_vol1 = self.settings.get("cas_p_vol1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_btn_add_base = self.settings.get("cas_p_btn_add")
        c_btn_del_base = self.settings.get("cas_p_btn_del")
        c_combo_vol_base = self.settings.get("cas_p_combo_vol")

        if not (
            c_vol1 and c_vol2 and c_btn_add_base and c_btn_del_base and c_combo_vol_base
        ):
            return None, None, None

        # Высота строки = разница между 2-й и 1-й ячейкой
        row_height = c_vol2[1] - c_vol1[1]

        def coords_for_index(index=2):
            # base calibration corresponds to index == 2
            delta_rows = index - 2
            add_y = c_btn_add_base[1] + (delta_rows * row_height)
            del_y = c_btn_del_base[1] + (delta_rows * row_height)
            combo_y = c_combo_vol_base[1] + (delta_rows * row_height)

            return (
                [c_btn_add_base[0], int(add_y)],
                [c_btn_del_base[0], int(del_y)],
                [c_combo_vol_base[0], int(combo_y)],
            )

        # по умолчанию вернуть для 2-й ячейки
        return coords_for_index()

    def add_cascade_row(self):
        """Добавить одну ячейку каскада (старый метод - не используется)"""
        if self._cancelled:
            return

        c_scrollbar = self.settings.get("cas_p_scrollbar")

        # Вычисляем координаты динамически
        c_btn_add, c_btn_del, c_combo_vol = self.get_last_cell_coords()

        if not c_btn_add:
            return

        # Нажимаем кнопку "+"
        pyautogui.click(c_btn_add[0], c_btn_add[1])
        fast_sleep(0.3)

        # Выбираем "свое значение" в комбобоксе (если координаты есть)
        if c_combo_vol:
            self.select_custom_volume_at(c_combo_vol)

        # Скроллим вниз для отображения новой ячейки
        if c_scrollbar:
            pyautogui.moveTo(c_scrollbar[0], c_scrollbar[1])
            pyautogui.mouseDown()
            pyautogui.moveTo(c_scrollbar[0], c_scrollbar[1] + 100, duration=0.01)
            pyautogui.mouseUp()
            fast_sleep(0.01)

    def add_cascade_row_simple(self, last_count=None):
        """Добавить одну ячейку без скроллирования (используется в manage_cascade_count)"""
        if self._cancelled:
            return
        # При добавлении нам нужно кликать на кнопке '+' на уровне текущей последней ячейки
        # last_count в manage_cascade_count передаётся как текущее количество ячеек
        # Здесь используем значение из настроек как запасной вариант
        if last_count is None:
            last_count = self.settings.get("last_cascade_count", 1)
        c_vol1 = self.settings.get("cas_p_vol1")
        c_vol2 = self.settings.get("cas_p_vol2")
        if not (c_vol1 and c_vol2):
            return

        # вычисляем координаты кнопки '+' на уровне текущей последней ячейки
        row_height = c_vol2[1] - c_vol1[1]
        c_btn_add_base = self.settings.get("cas_p_btn_add")
        c_combo_vol_base = self.settings.get("cas_p_combo_vol")
        if not (c_btn_add_base and c_combo_vol_base):
            return

        # позиция '+' для последней ячейки (индекс last_count)
        add_x = c_btn_add_base[0]
        add_y = int(c_btn_add_base[1] + (last_count - 2) * row_height)

        # кликаем '+' на уровне текущей последней ячейки
        pyautogui.click(add_x, add_y)
        fast_sleep(0.35)

        # теперь новая ячейка появилась (index = last_count + 1)
        new_index = last_count + 1
        combo_x = c_combo_vol_base[0]
        combo_y = int(c_combo_vol_base[1] + (new_index - 2) * row_height)

        # Выбираем "свое значение" в комбобоксе новой ячейки
        self.select_custom_volume_at([combo_x, combo_y])

        # обновляем локально last_cascade_count — manage_cascade_count обновит его позже
        fast_sleep(0.25)

    def delete_cascade_row(self, last_count=None):
        """Удалить одну ячейку каскада"""
        if self._cancelled:
            return
        # Вычисляем текущую последнюю ячейку
        if last_count is None:
            last_count = self.settings.get("last_cascade_count", 1)
        c_vol1 = self.settings.get("cas_p_vol1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_btn_del_base = self.settings.get("cas_p_btn_del")
        if not (c_vol1 and c_vol2 and c_btn_del_base):
            return

        row_height = c_vol2[1] - c_vol1[1]
        del_x = c_btn_del_base[0]
        del_y = int(c_btn_del_base[1] + (last_count - 2) * row_height)

        # Нажимаем кнопку "-" на уровне последней ячейки
        pyautogui.click(del_x, del_y)
        fast_sleep(0.35)

    def select_custom_volume(self):
        """Выбрать 'свое значение' в комбобоксе объёма (старый метод - не используется)"""
        if self._cancelled:
            return

        c_combo_vol = self.settings.get("cas_p_combo_vol")

        if not c_combo_vol:
            return

        self.select_custom_volume_at(c_combo_vol)

    def select_custom_volume_at(self, c_combo_vol):
        """Выбрать 'свое значение' в комбобоксе по конкретным координатам"""
        if self._cancelled or not c_combo_vol:
            return

        print(f"[CASCADE]     → Выбираю 'свое значение' в комбобоксе...")

        # Кликаем на комбобокс
        pyautogui.click(c_combo_vol[0], c_combo_vol[1])
        fast_sleep(0.25)

        # Нажимаем Home чтобы перейти в начало списка
        keyboard.press_and_release("home")
        fast_sleep(0.1)

        # Нажимаем стрелку вниз 5 раз для выбора "свое значение" (последний элемент)
        for i in range(5):
            keyboard.press_and_release("down")
            fast_sleep(0.08)

        # Подтверждаем выбор
        keyboard.press_and_release("enter")
        fast_sleep(0.25)

    def manage_cascade_count(self, target_count):
        """Удаляет РОВНО столько раз, сколько было добавлено прошлым запуском.
        Если это первый запуск (last_cascade_count==1), ничего не делает!
        """
        if self._cancelled or not target_count or target_count < 1:
            return

        c_scrollbar = self.settings.get("cas_p_scrollbar")
        c_vol1 = self.settings.get("cas_p_vol1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_btn_del_base = self.settings.get("cas_p_btn_del")
        prev_count = int(self.settings.get("last_cascade_count", 1) or 1)

        print(f"[CASCADE] Управление ячейками: было {prev_count}, нужно {target_count}")

        # Если не нужно удалять (первое выставление или все уже удалено)
        if prev_count <= 1:
            print("[CASCADE] ✓ Нечего удалять, сразу добавляем новые.")
            self.settings["last_cascade_count"] = 1
            self.settings["_cascade_scrolled"] = False
            return

        # Проверка калибровки
        if not (c_vol1 and c_vol2 and c_btn_del_base):
            print("[CASCADE] ⚠ Калибровка неполная")
            self.settings["last_cascade_count"] = 1
            self.settings["_cascade_scrolled"] = False
            return

        # Скроллим в конец, чтобы были видны все крестики
        if c_scrollbar and not self._cancelled:
            print(f"[CASCADE]   Скроллю в конец перед удалением...")
            pyautogui.moveTo(c_scrollbar[0], c_scrollbar[1])
            pyautogui.mouseDown()
            pyautogui.moveTo(c_scrollbar[0], c_scrollbar[1] + 1000, duration=0.01)
            pyautogui.mouseUp()
            fast_sleep(0.01)
            self.settings["_cascade_scrolled"] = True
        else:
            self.settings["_cascade_scrolled"] = False

        del_x = c_btn_del_base[0]
        del_y = int(c_btn_del_base[1])
        print(f"[CASCADE]   Удаляю {prev_count-1} по крестику у второй ячейки.")

        for i in range(prev_count - 1):
            if self._cancelled:
                print("[CASCADE]   Отмена во время удаления")
                break
            pyautogui.click(del_x, del_y)
            fast_sleep(0.35)

        self.settings["last_cascade_count"] = 1
        print("[CASCADE] ✓ Очистка завершена. last_cascade_count = 1")

    def add_cascade_row_simple(self, last_count=None):
        """Добавить одну ячейку без скроллирования (используется в manage_cascade_count).

        Если передан last_count, вычисляем позицию '+' и комбобокса относительно него,
        иначе используем базовые координаты из калибровки.
        """
        if self._cancelled:
            return

        # Если last_count не передан — используем базовую координатку (2-я ячейка)
        if last_count is None:
            c_btn_add, c_btn_del, c_combo_vol = self.get_last_cell_coords()

            if not c_btn_add:
                return

            # Нажимаем кнопку "+"
            pyautogui.click(c_btn_add[0], c_btn_add[1])
            fast_sleep(0.25)

            # Выбираем "свое значение" в комбобоксе
            if c_combo_vol:
                self.select_custom_volume_at(c_combo_vol)

            fast_sleep(0.25)
            return

        # Если last_count задан — считаем положение '+' и комбобокса для новой ячейки
        c_vol1 = self.settings.get("cas_p_vol1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_btn_add_base = self.settings.get("cas_p_btn_add")
        c_combo_vol_base = self.settings.get("cas_p_combo_vol")

        if not (c_vol1 and c_vol2 and c_btn_add_base and c_combo_vol_base):
            return

        row_height = c_vol2[1] - c_vol1[1]

        add_x = c_btn_add_base[0]
        add_y = int(c_btn_add_base[1] + (last_count - 2) * row_height)

        # Нажимаем '+' на уровне текущей последней ячейки
        pyautogui.click(add_x, add_y)
        fast_sleep(0.35)

        # Новая ячейка получила индекс last_count + 1
        new_index = last_count + 1
        combo_x = c_combo_vol_base[0]
        combo_y = int(c_combo_vol_base[1] + (new_index - 2) * row_height)

        # Выбираем "свое значение" в комбобоксе новой ячейки
        self.select_custom_volume_at([combo_x, combo_y])

        fast_sleep(0.25)

    def safe_input(self, x, y, value):
        """Метод для максимально надежной очистки и ввода"""
        if self._cancelled:
            return

        # 1. Наводим и кликаем один раз
        pyautogui.moveTo(x, y, duration=0.05)
        fast_sleep(0.05)
        pyautogui.click()
        fast_sleep(0.15)  # Ждем активации поля

        # 2. Удаляем старое значение нажатием Delete несколько раз
        for _ in range(8):
            keyboard.press_and_release("delete")
            fast_sleep(0.03)

        fast_sleep(0.1)

        # 3. Пишем новое значение
        val_str = f"{value:.2f}".replace(",", ".")
        pyautogui.write(val_str, interval=0.005)
        fast_sleep(0.1)

        # 4. Подтверждаем ввод
        keyboard.press_and_release("enter")
        fast_sleep(0.15)

    def run(self):
        # Координаты
        c_gear = self.settings.get("cas_p_gear")
        c_book = self.settings.get("cas_p_book")
        c_scrollbar = self.settings.get("cas_p_scrollbar")
        c_vol1 = self.settings.get("cas_p_vol1")
        c_dist1 = self.settings.get("cas_p_dist1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_dist2 = self.settings.get("cas_p_dist2")

        if not (c_gear and c_book and c_vol1 and c_dist1 and c_vol2 and c_dist2):
            return

        # Высота строк
        row_height_vol = c_vol2[1] - c_vol1[1]
        row_height_dist = c_dist2[1] - c_dist1[1]

        def on_esc():
            self._cancelled = True

        keyboard.add_hotkey("esc", on_esc)

        try:
            # Открываем настройки
            if self._cancelled:
                return
            pyautogui.click(c_gear[0], c_gear[1])
            fast_sleep(0.01)

            # Выбираем Книгу заявок
            if self._cancelled:
                return
            pyautogui.click(c_book[0], c_book[1])
            fast_sleep(0.01)

            # ===== ЭТАП 1: УПРАВЛЯЕМ КОЛИЧЕСТВОМ ЯЧЕЕК =====
            target_count = len(self.orders)
            print(f"[CASCADE] Целевое количество ячеек: {target_count}")
            self.manage_cascade_count(target_count)

            if self._cancelled:
                return

            fast_sleep(0.3)

            # ===== ЭТАП 2: ЗАПОЛНЯЕМ ДАННЫЕ ПОЭТАПНО С ДОБАВЛЕНИЕМ ЯЧЕЕК =====
            print(f"[CASCADE] Начинаю поэтапное заполнение и добавление ячеек...")

            # Скроллим один раз в конец (если есть ползунок) — но только если manage_cascade_count
            # НЕ прокрутил уже список (маркер "_cascade_scrolled" ставится в manage_cascade_count).
            if (
                c_scrollbar
                and not self._cancelled
                and not self.settings.get("_cascade_scrolled", False)
            ):
                pyautogui.moveTo(c_scrollbar[0], c_scrollbar[1])
                pyautogui.mouseDown()
                pyautogui.moveTo(c_scrollbar[0], c_scrollbar[1] + 1000, duration=0.01)
                pyautogui.mouseUp()
                fast_sleep(0.01)

            # Сбрасываем маркер (иначе будет мешать в следующем запуске)
            self.settings["_cascade_scrolled"] = False

            # Координаты базового (калиброванного) положения — используем позицию 2-й ячейки
            btn_add_base = self.settings.get("cas_p_btn_add")
            combo_base = self.settings.get("cas_p_combo_vol")

            base_vol_x = c_vol2[0]
            base_vol_y = c_vol2[1]
            base_dist_x = c_dist2[0]
            base_dist_y = c_dist2[1]

            # Заполняем первую ячейку, которая после удаления второй находится в позиции калибровки (2-я позиция)
            if len(self.orders) > 0 and not self._cancelled:
                first = self.orders[0]
                print(
                    f"[CASCADE]   Заявка 1/{len(self.orders)}: объем={first['vol']:.2f}, дистанция={first['dist']:.2f}%"
                )
                self.safe_input(base_vol_x, base_vol_y, first["vol"])
                self.safe_input(base_dist_x, base_dist_y, first["dist"])

            # Для каждой следующей заявки: нажать '+', сдвинуть список вниз (1 раз для первой добавленной, далее 2 раза),
            # выбрать "свое значение" в комбобоксе на базовой позиции и заполнить объем/дистанцию на базовой позициях.
            for idx in range(1, len(self.orders)):
                if self._cancelled:
                    break

                order = self.orders[idx]
                print(
                    f"[CASCADE]   Добавляю и заполняю ячейку {idx+1}/{len(self.orders)}: объем={order['vol']:.2f}, дистанция={order['dist']:.2f}%"
                )

                # Нажать '+' на базовой позиции (добавляет новую ячейку ниже)
                if btn_add_base and not self._cancelled:
                    pyautogui.click(btn_add_base[0], btn_add_base[1])
                    fast_sleep(0.25)

                # Нажимаем стрелку вниз 2 раза после каждой вставки (включая первую)
                down_presses = 2
                for _ in range(down_presses):
                    if self._cancelled:
                        break
                    keyboard.press_and_release("down")
                    fast_sleep(0.12)

                fast_sleep(0.18)  # дать интерфейсу перестроиться

                # Выбираем "свое значение" в комбобоксе на базовой позиции
                if combo_base and not self._cancelled:
                    self.select_custom_volume_at(combo_base)

                # Заполняем объем и дистанцию на базовой позициях (новая ячейка теперь там)
                self.safe_input(base_vol_x, base_vol_y, order["vol"])
                self.safe_input(base_dist_x, base_dist_y, order["dist"])

                fast_sleep(0.18)

            # После поэтапного добавления/заполнения — обновляем сохранённое количество
            self.settings["last_cascade_count"] = target_count
            print(f"[CASCADE] ✓ Все заявки выставлены!")
            c_close_x = self.settings.get("cas_p_close_x")
            if c_close_x and not self._cancelled:
                print(f"[CASCADE] Закрываю окно каскадов...")
                pyautogui.click(c_close_x[0], c_close_x[1])
                fast_sleep(0.3)

            if not self._cancelled:
                self.finished.emit()
            else:
                self.cancelled.emit()

        finally:
            try:
                keyboard.remove_hotkey("esc")
            except:
                pass


class CascadeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.setStyleSheet(
            """
            QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 6px; font-weight: bold; color: #ccc; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLabel { color: #aaa; font-size: 9pt; }
            QPushButton.percBtn { background-color: #252525; color: #888; border: 1px solid #333; border-radius: 4px; padding: 4px; font-weight: bold; }
            QPushButton.percBtn:checked { background-color: #38BE1D; color: black; border: 1px solid #38BE1D; }
            QComboBox, QSpinBox, QDoubleSpinBox { background: #1A1A1A; color: white; border: 1px solid #333; padding: 3px; }
        """
        )

        # Блок 1: Объем
        gb_vol = QGroupBox("1. Общий объем каскада")
        l_vol = QVBoxLayout()
        h_perc = QHBoxLayout()
        self.group_btns = []
        for text in ["25%", "50%", "75%", "100%"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "percBtn")
            btn.clicked.connect(self.on_perc_click)
            self.group_btns.append(btn)
            h_perc.addWidget(btn)
        self.group_btns[3].setChecked(True)

        self.lbl_total_vol = QLabel("Итого в каскад: 0 $")
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt;"
        )
        self.lbl_total_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_vol.addLayout(h_perc)
        l_vol.addWidget(self.lbl_total_vol)
        gb_vol.setLayout(l_vol)
        layout.addWidget(gb_vol)

        # Блок 2: Настройки
        gb_set = QGroupBox("2. Настройки расстановки")
        grid = QGridLayout()
        grid.addWidget(QLabel("Кол-во:"), 0, 0)
        self.sb_count = QSpinBox()
        self.sb_count.setRange(2, 22)
        self.sb_count.setValue(self.main.settings.get("cascade_count", 5))
        grid.addWidget(self.sb_count, 0, 1)
        grid.addWidget(QLabel("Мин.ордер ($):"), 0, 2)
        self.sb_min = QDoubleSpinBox()
        self.sb_min.setRange(1, 1000)
        self.sb_min.setValue(self.main.settings.get("cascade_min_order", 6))
        grid.addWidget(self.sb_min, 0, 3)
        grid.addWidget(QLabel("Тип:"), 1, 0)
        self.cb_type = QComboBox()
        self.cb_type.addItems(
            ["Равномерно", "Матрешка x1.2", "Матрешка x1.5", "Агрессивно x2"]
        )
        self.cb_type.setCurrentIndex(self.main.settings.get("cascade_type", 0))
        grid.addWidget(self.cb_type, 1, 1)
        grid.addWidget(QLabel("Шаг (%):"), 1, 2)
        self.sb_dist = QDoubleSpinBox()
        self.sb_dist.setRange(0.01, 10.0)
        self.sb_dist.setValue(self.main.settings.get("cascade_dist_step", 0.1))
        grid.addWidget(self.sb_dist, 1, 3)

        self.sb_count.editingFinished.connect(self.recalc_table)
        self.sb_min.valueChanged.connect(self.recalc_table)
        self.cb_type.currentIndexChanged.connect(self.recalc_table)
        self.sb_dist.valueChanged.connect(self.recalc_table)
        gb_set.setLayout(grid)
        layout.addWidget(gb_set)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Объем ($)", "Дистанция (%)"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setFixedHeight(120)
        self.table.itemChanged.connect(self.on_table_cell_changed)
        layout.addWidget(self.table)

        # Кнопки
        h_btn = QHBoxLayout()
        self.btn_calib = QPushButton("КАЛИБРОВКА")
        self.btn_calib.setStyleSheet("background: #333; color: white; padding: 8px;")
        self.btn_calib.clicked.connect(self.start_calibration)
        self.btn_apply = QPushButton("ВЫСТАВИТЬ")
        self.btn_apply.setStyleSheet(
            "background: #38BE1D; color: black; font-weight: bold; padding: 8px;"
        )
        self.btn_apply.clicked.connect(self.run_automation)
        h_btn.addWidget(self.btn_calib)
        h_btn.addWidget(self.btn_apply)
        layout.addLayout(h_btn)

        self.lbl_status = QLabel("Нужна калибровка")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

    def on_perc_click(self):
        for btn in self.group_btns:
            btn.setChecked(False)
        self.sender().setChecked(True)
        self.recalc_table()

    def recalc_table(self):
        base_vol = getattr(self.main, "current_vol", 0)
        perc = [0.25, 0.5, 0.75, 1.0][
            next(i for i, b in enumerate(self.group_btns) if b.isChecked())
        ]
        total_vol = base_vol * perc
        self.lbl_total_vol.setText(f"Итого в каскад: {total_vol:.1f} $")

        count = self.sb_count.value()
        mult = [1.0, 1.2, 1.5, 2.0][self.cb_type.currentIndex()]
        min_size = self.sb_min.value()
        dist_step = self.sb_dist.value()

        # Корректируем максимальное КОЛИЧЕСТВО: если total_vol < min_size, можно 1; иначе максимум
        max_possible = min(count, int(total_vol // min_size))
        if max_possible < 1:
            max_possible = 1
        if max_possible != count:
            self.sb_count.setValue(max_possible)
            count = max_possible

        # Расчёт веса и объёма
        weights = [mult**i for i in range(count)]
        total_w = sum(weights)
        raw_vols = [(w / total_w) * total_vol for w in weights]

        # Формируем реальные заявки, чтобы любая была >= min_size (и первый ордер — min_size!)
        final_vols = []
        tmp = 0
        for v in raw_vols:
            tmp += v
            if tmp >= min_size:
                final_vols.append(tmp)
                tmp = 0
        if tmp > 0 and final_vols:
            final_vols[-1] += tmp

        self.table.setRowCount(len(final_vols))
        self.calculated_orders = []
        cascade_manual_values = self.main.settings.get("cascade_manual_values", {})
        for i, v in enumerate(final_vols):
            d = i * dist_step

            # Проверяем, есть ли сохраненные пользовательские значения
            if (
                self.cb_type.currentText() == "Вручную"
                and str(i) in cascade_manual_values
            ):
                manual_d = cascade_manual_values[str(i)]
                self.table.setItem(i, 0, QTableWidgetItem(f"{v:.2f}"))
                self.table.setItem(i, 1, QTableWidgetItem(f"{manual_d:.2f}"))
                d = manual_d
            else:
                self.table.setItem(i, 0, QTableWidgetItem(f"{v:.2f}"))
                self.table.setItem(i, 1, QTableWidgetItem(f"{d:.2f}"))

            self.calculated_orders.append({"vol": v, "dist": d})

        # Сохраняем текущие параметры в настройки
        self.main.settings["cascade_count"] = count
        self.main.settings["cascade_min_order"] = min_size
        self.main.settings["cascade_type"] = self.cb_type.currentIndex()
        self.main.settings["cascade_dist_step"] = dist_step
        self.main.save_settings()

    def on_table_cell_changed(self, item):
        """Сохраняет пользовательские значения из таблицы"""
        row = self.table.row(item)
        col = self.table.column(item)

        if col == 1:  # Только колонка с дистанцией
            if item:
                try:
                    value = float(item.text().replace(",", "."))
                    cascade_manual = self.main.settings.get("cascade_manual_values", {})
                    cascade_manual[str(row)] = value
                    self.main.settings["cascade_manual_values"] = cascade_manual
                    self.main.save_settings()
                except:
                    pass

    def start_calibration(self):
        self.calib_hotkey = self.main.settings.get("hk_coords", "f2").lower()
        self.lbl_status.setText(
            f"Шаг 1: Наведи на ШЕСТЕРЕНКУ и нажми {self.calib_hotkey.upper()}"
        )
        self.calib_step = 1
        self.calib_active = True

        # Включаем real-time отслеживание координат
        self.coord_timer = QTimer()
        self.coord_timer.timeout.connect(self.update_coords_display)
        self.coord_timer.start(100)  # Обновляем каждые 100мс

        keyboard.add_hotkey(self.calib_hotkey, self.next_calib_step)

    def update_coords_display(self):
        """Показывает текущие координаты мыши в реальном времени"""
        if self.calib_active:
            x, y = pyautogui.position()
            current_text = self.lbl_status.text()
            # Берём только первую часть (инструкцию), убираем координаты
            if "│" in current_text:
                instruction = current_text.split("│")[0].strip()
            else:
                instruction = current_text
            self.lbl_status.setText(f"{instruction} │ Координаты: X={x}, Y={y}")

    def stop_coord_timer(self):
        """Отключаем отслеживание координат"""
        self.calib_active = False
        if hasattr(self, "coord_timer"):
            self.coord_timer.stop()

    def next_calib_step(self):
        x, y = pyautogui.position()
        hk = self.calib_hotkey.upper()
        steps = {
            1: ("cas_p_gear", f"Шаг 2: Наведи на 'КНИГА ЗАЯВОК' и нажми {hk}"),
            2: ("cas_p_book", f"Шаг 3: Наведи на ПОЛЗУНОК СКРОЛЛА и нажми {hk}"),
            3: ("cas_p_scrollbar", f"Шаг 4: Наведи на 1-е поле ОБЪЕМА и нажми {hk}"),
            4: ("cas_p_vol1", f"Шаг 5: Наведи на 1-е поле ДИСТАНЦИИ и нажми {hk}"),
            5: ("cas_p_dist1", f"Шаг 6: Наведи на 2-е поле ОБЪЕМА и нажми {hk}"),
            6: ("cas_p_vol2", f"Шаг 7: Наведи на 2-е поле ДИСТАНЦИИ и нажми {hk}"),
            7: (
                "cas_p_dist2",
                f"Шаг 8: Наведи на КНОПКУ '+' (НА УРОВНЕ 2-й ЯЧЕЙКИ!) и нажми {hk}",
            ),
            8: (
                "cas_p_btn_add",
                f"Шаг 9: Наведи на КНОПКУ '-' (НА УРОВНЕ 2-й ЯЧЕЙКИ!) и нажми {hk}",
            ),
            9: (
                "cas_p_btn_del",
                f"Шаг 10: Наведи на КОМБОБОКС ОБЪЕМА (НА УРОВНЕ 2-й ЯЧЕЙКИ!) и нажми {hk}",
            ),
            10: (
                "cas_p_combo_vol",
                f"Шаг 11: Наведи на КРЕСТИК ЗАКРЫТИЯ (в конце всех!) и нажми {hk}",
            ),
            11: ("cas_p_close_x", "✓ Калибровка завершена!"),
        }
        key, next_txt = steps[self.calib_step]
        self.main.settings[key] = [x, y]
        self.lbl_status.setText(next_txt)
        if self.calib_step == 11:
            self.stop_coord_timer()
            self.main.save_settings()
            keyboard.remove_hotkey(self.calib_hotkey)
        else:
            self.calib_step += 1

    def apply_scale(self):
        sc = self.main.settings.get("scale", 100) / 100.0
        self.table.setFixedHeight(int(120 * sc))
        self.lbl_total_vol.setStyleSheet(
            f"color: #FF9F0A; font-weight: bold; font-size: {int(11 * sc)}pt;"
        )

    def run_automation(self):
        self.recalc_table()
        if not hasattr(self, "calculated_orders"):
            return
        self.lbl_status.setText("Выставляю... ESC для отмены")
        # Сворачиваем окно перед выставлением
        self.main.showMinimized()
        self.worker = CascadeWorker(
            self.main.settings, self.calculated_orders, self.main
        )
        self.worker.finished.connect(lambda: self.lbl_status.setText("Готово!"))
        self.worker.cancelled.connect(lambda: self.lbl_status.setText("Отменено"))
        self.worker.start()
