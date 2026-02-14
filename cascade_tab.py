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
    """Поток для выполнения кликов"""

    finished = pyqtSignal()
    cancelled = pyqtSignal()  # Сигнал об остановке по ESC

    def __init__(self, settings, orders_data, main_window):
        super().__init__()
        self.settings = settings
        self.orders = orders_data
        self.main_window = main_window
        self._cancelled = False

    def run(self):
        # Достаем координаты
        c_gear = self.settings.get("cas_p_gear")  # Шестеренка
        c_book = self.settings.get("cas_p_book")  # Пункт меню Книга заявок
        c_scrollbar = self.settings.get("cas_p_scrollbar")  # Ползунок скроллбара
        c_vol1 = self.settings.get("cas_p_vol1")
        c_dist1 = self.settings.get("cas_p_dist1")
        c_vol2 = self.settings.get("cas_p_vol2")
        c_plus = self.settings.get("cas_p_plus")
        c_x = self.settings.get("cas_p_x")

        # Отладка - выводим координаты
        print(f"[CASCADE] Координаты:")
        print(f"  Шестеренка (c_gear): {c_gear}")
        print(f"  Книга заявок (c_book): {c_book}")
        print(f"  Объем 1 (c_vol1): {c_vol1}")
        print(f"  Дистанция 1 (c_dist1): {c_dist1}")
        print(f"  Объем 2 (c_vol2): {c_vol2}")
        print(f"  Плюсик (c_plus): {c_plus}")
        print(f"  Крестик (c_x): {c_x}")
        print(f"  Заявок для выставления: {len(self.orders)}")

        # Если не все точки заданы - стоп
        if not (c_gear and c_book and c_vol1 and c_dist1 and c_vol2 and c_plus and c_x):
            return

        row_height = c_vol2[1] - c_vol1[1]

        # Регистрируем ESC для остановки
        def on_esc():
            self._cancelled = True
            # Показываем окно обратно
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.cancelled.emit()

        keyboard.add_hotkey("esc", on_esc)

        try:
            # 1. Открываем настройки (Шестеренка)
            if self._cancelled:
                return
            pyautogui.moveTo(c_gear[0], c_gear[1])
            pyautogui.click()
            time.sleep(0.15)

            # 2. Выбираем пункт "Книга заявок"
            if self._cancelled:
                return
            pyautogui.moveTo(c_book[0], c_book[1])
            pyautogui.click()
            time.sleep(0.15)

            # 3. Перетаскиваем ползунок вниз (если координата скроллбара задана)
            if self._cancelled:
                return
            if c_scrollbar:
                scrollbar_x = c_scrollbar[0]
                scrollbar_y_start = c_scrollbar[1]
                scrollbar_y_end = scrollbar_y_start + 700  # Тянем вниз на 700px

                # Перетаскиваем ползунок: нажимаем, тянем, отпускаем
                pyautogui.moveTo(scrollbar_x, scrollbar_y_start)
                time.sleep(0.1)
                pyautogui.mouseDown(button="left")
                time.sleep(0.05)
                pyautogui.moveTo(scrollbar_x, scrollbar_y_end, duration=0.4)
                time.sleep(0.05)
                pyautogui.mouseUp(button="left")
                time.sleep(0.2)

            # Дополнительно: несколько PageDown для точности
            pyautogui.moveTo(c_book[0], c_book[1] + 200)
            pyautogui.click()
            time.sleep(0.05)
            for _ in range(2):
                if self._cancelled:
                    return
                pyautogui.press("pagedown")
                time.sleep(0.03)

            # 4. Очистка (удаляем старые строки каскада)
            if self._cancelled:
                return
            print(
                f"[CASCADE] Шаг 4: Нажимаю на крестик (X) для удаления заявок. Координаты: {c_x}"
            )
            pyautogui.moveTo(c_x[0], c_x[1])
            for i in range(12):  # С запасом
                if self._cancelled:
                    return
                print(f"[CASCADE]   Нажатие {i+1}/12 на крестик (X)")
                pyautogui.click()
                time.sleep(0.02)

            # 5. Создаем нужное количество строк
            if self._cancelled:
                return
            print(
                f"[CASCADE] Шаг 5: Нажимаю на плюсик (+) для добавления заявок. Координаты: {c_plus}. Количество для добавления: {len(self.orders) - 1}"
            )
            pyautogui.moveTo(c_plus[0], c_plus[1])
            for i in range(len(self.orders) - 1):
                if self._cancelled:
                    return
                print(f"[CASCADE]   Нажатие {i+1}/{len(self.orders)-1} на плюсик (+)")
                pyautogui.click()
                time.sleep(0.03)

            # 6. Заполняем значения
            print(
                f"[CASCADE] Шаг 6: Заполняю объёмы и дистанции. Высота строки: {row_height}"
            )
            for i, order in enumerate(self.orders):
                if self._cancelled:
                    return
                cur_y = c_vol1[1] + (i * row_height)
                print(
                    f"[CASCADE]   Заявка {i+1}: объем={order['vol']:.2f}, дистанция={order['dist']:.2f}%, Y={cur_y}"
                )

                # --- Объём ---
                vol_str = f"{order['vol']:.2f}".replace(",", ".")
                pyperclip.copy(vol_str)
                print(
                    f"[CASCADE]     Выставляю объем {vol_str} в координаты ({c_vol1[0]}, {cur_y})"
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

                # --- Дистанция ---
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

            # 7. Закрываем настройки (Esc)
            if not self._cancelled:
                time.sleep(0.1)
                pyautogui.press("esc")
                self.finished.emit()
        finally:
            # Убираем хоткей ESC
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

        # Сохраняем ссылки для масштабирования
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

        # --- Стили для этого окна ---
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
            /* Стиль кнопок процентов (Исправлено) */
            QPushButton.percBtn {
                background-color: #252525;
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton.percBtn:checked {
                background-color: #38BE1D; /* Ярко-зеленый */
                color: black;             /* Черный текст - читается отлично */
                border: 1px solid #38BE1D;
            }
            QPushButton.percBtn:hover { border: 1px solid #555; }
            
            QComboBox {
                background: #1A1A1A; color: white; border: 1px solid #333; padding: 2px;
                min-width: 60px; /* Чтобы текст не резался */
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

        # --- БЛОК 1: Объем ---
        gb_vol = QGroupBox("1. Общий объем каскада")
        l_vol = QVBoxLayout()

        h_perc = QHBoxLayout()
        self.group_btns = []
        for text in ["25%", "50%", "75%", "100%"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("class", "percBtn")  # Для CSS
            btn.setObjectName("percBtn")  # Для Qt
            btn.clicked.connect(self.on_perc_click)
            self.group_btns.append(btn)
            h_perc.addWidget(btn)

        self.group_btns[3].setChecked(True)  # 100% по умолчанию

        self.lbl_total_vol = QLabel("Итого в каскад: 0 $")
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt; margin-top: 5px;"
        )
        self.lbl_total_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)

        l_vol.addLayout(h_perc)
        l_vol.addWidget(self.lbl_total_vol)
        gb_vol.setLayout(l_vol)
        layout.addWidget(gb_vol)

        # --- БЛОК 2: Настройки (Сетка исправлена) ---
        gb_set = QGroupBox("2. Настройки расстановки")
        grid = QGridLayout()
        grid.setHorizontalSpacing(15)  # Отступ между колонками
        grid.setVerticalSpacing(8)

        # Используем QLabel с wordWrap, чтобы текст переносился если что
        l1 = QLabel("Кол-во:")
        grid.addWidget(l1, 0, 0)
        self.sb_count = QSpinBox()
        self.sb_count.setRange(2, 50)
        self.sb_count.setValue(5)
        self._last_max_possible = 50  # Отслеживаем предыдущий максимум
        self._last_type_index = -1  # Отслеживаем смену типа
        self.sb_count.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_count.setObjectName("spinInner")
        self.sb_count_wrap = self._wrap_spinbox(self.sb_count)
        grid.addWidget(self.sb_count_wrap, 0, 1)

        l2 = QLabel("Мин.ордер ($):")
        grid.addWidget(l2, 0, 2)
        self.sb_min = QDoubleSpinBox()
        self.sb_min.setRange(1, 1000)
        min_order_prec = int(self.main.settings.get("prec_min_order", 2))
        if min_order_prec < 0:
            min_order_prec = 0
        if min_order_prec > 6:
            min_order_prec = 6
        self.sb_min.setDecimals(min_order_prec)
        self.sb_min.setSingleStep(1 if min_order_prec == 0 else 10 ** (-min_order_prec))
        self.sb_min.setValue(float(self.main.settings.get("scalp_min_order", 6)))
        self.sb_min.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_min.setObjectName("spinInner")
        self.sb_min_wrap = self._wrap_spinbox(self.sb_min)
        grid.addWidget(self.sb_min_wrap, 0, 3)

        # Подсказка под Кол-во (новая строка 1)
        self.lbl_count_hint = QLabel("Макс: ? ячеек")
        self.lbl_count_hint.setStyleSheet("color: #888; font-size: 8pt;")
        self.lbl_count_hint.setAlignment(Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(self.lbl_count_hint, 1, 0, 1, 2)

        l3 = QLabel("Тип:")
        grid.addWidget(l3, 2, 0)
        self.cb_type = QComboBox()
        # Сократим названия, чтобы влазили
        self.cb_type.addItems(
            ["Равномерно", "Матрешка x1.2", "Матрешка x1.5", "Агрессивно x2"]
        )
        self.cb_type.setMinimumWidth(70)  # Более компактная ширина
        grid.addWidget(self.cb_type, 2, 1)

        l4 = QLabel("Шаг (%):")
        grid.addWidget(l4, 2, 2)
        self.sb_dist = QDoubleSpinBox()
        self.sb_dist.setRange(0.01, 10.0)
        self.sb_dist.setValue(0.1)
        self.sb_dist.setSingleStep(0.05)
        self.sb_dist.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.sb_dist.setObjectName("spinInner")
        self.sb_dist_wrap = self._wrap_spinbox(self.sb_dist)
        grid.addWidget(self.sb_dist_wrap, 2, 3)

        # Используем тот же eventFilter, что и в калькуляторе (из main.py)
        self.sb_count.lineEdit().installEventFilter(self.main)
        self.sb_min.lineEdit().installEventFilter(self.main)
        self.sb_dist.lineEdit().installEventFilter(self.main)

        # События
        self.sb_count.valueChanged.connect(self.recalc_table)
        self.sb_min.valueChanged.connect(self.recalc_table)
        self.cb_type.currentIndexChanged.connect(self.recalc_table)
        self.sb_dist.valueChanged.connect(self.recalc_table)
        
        # Реал-тайм обновление при вводе текста в спинбоксы
        # Подключаемся к встроенному QLineEdit для обновления при каждом символе
        self.sb_min.lineEdit().textChanged.connect(self.on_min_text_changed)
        self.sb_dist.lineEdit().textChanged.connect(self.on_dist_text_changed)
        
        # Обновляем подсказку когда меняется процент
        self.group_btns[0].clicked.connect(self.recalc_table)
        self.group_btns[1].clicked.connect(self.recalc_table)
        self.group_btns[2].clicked.connect(self.recalc_table)
        self.group_btns[3].clicked.connect(self.recalc_table)

        gb_set.setLayout(grid)
        layout.addWidget(gb_set)

        # --- БЛОК 3: Таблица (Исправлено обрезание) ---
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Объем ($)", "Дистанция (%)"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        # Увеличиваем высоту строк, чтобы шрифт не резался
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setRowCount(0)
        self.table.setFixedHeight(120)
        # Базовый стиль таблицы (точные размеры выставятся в apply_scale)
        self.table.setStyleSheet(
            "QTableWidget::item { font-size: 6pt; padding: 0px 2px; }"
            "QHeaderView::section { font-size: 8pt; padding: 2px; }"
            "selection-background-color: #38BE1D; selection-color: black;"
        )
        layout.addWidget(self.table)

        # --- БЛОК 4: Кнопка выставления ---
        self.btn_apply = QPushButton("ВЫСТАВИТЬ")
        self.btn_apply.setStyleSheet(
            "background: #38BE1D; color: black; font-weight: bold; padding: 8px; font-size: 10pt;"
        )
        self.btn_apply.clicked.connect(self.run_automation)
        layout.addWidget(self.btn_apply)

        # Статус (с переносом текста)
        self.lbl_status = QLabel("Нужна калибровка (7 шагов)")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)  # <-- ВАЖНО: Текст будет переноситься
        self.lbl_status.setStyleSheet(
            "color: #666; font-size: 7pt; margin-bottom: 5px;"
        )
        layout.addWidget(self.lbl_status)

        # Применяем масштабирование под текущий размер интерфейса
        self.apply_scale()

    def apply_scale(self):
        """
        Подгоняет размеры элементов под текущий масштаб интерфейса (settings['scale']),
        чтобы на вкладке каскадов ничего не вылезало за рамки и текст не резался.
        """
        scale = self.main.settings.get("scale", 100)
        base_scale = getattr(self.main, "base_scale", 150)
        ratio = scale / float(base_scale)
        sc = scale / 100.0

        # Кнопка типов: компактная ширина и синхронно с "Кол-во"
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

        # Итоговый объем каскада
        self.lbl_total_vol.setStyleSheet(
            "color: #FF9F0A; font-weight: bold; font-size: 11pt; margin-top: 5px;"
        )

        # Таблица ордеров
        self.table.verticalHeader().setDefaultSectionSize(int(14 * sc))
        self.table.setFixedHeight(int(80 * sc))
        item_font = max(6, int(6 * ratio))
        header_font = max(6, int(8 * ratio))
        self.table.setStyleSheet(
            f"QTableWidget::item {{ font-size: {item_font}pt; padding: 0px 1px; margin: 0px; }}"
            f"QHeaderView::section {{ font-size: {header_font}pt; padding: 1px; }}"
            "selection-background-color: #38BE1D; selection-color: black;"
        )

        # Строка статуса внизу
        self.lbl_status.setStyleSheet(
            "color: #666; font-size: 7pt; margin-bottom: 5px;"
        )

    def apply_min_order_precision(self, decimals):
        if decimals < 0:
            decimals = 0
        if decimals > 6:
            decimals = 6

        self.sb_min.blockSignals(True)
        self.sb_min.setDecimals(decimals)
        self.sb_min.setSingleStep(1 if decimals == 0 else 10 ** (-decimals))
        self.sb_min.setValue(round(self.sb_min.value(), decimals))
        self.sb_min.blockSignals(False)
        self.recalc_table()

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

    def on_min_text_changed(self, text):
        """Реал-тайм обновление при изменении текста в 'Мин. ордер'"""
        try:
            float(text)  # Проверяем, что это валидное число
            self.recalc_table()
        except ValueError:
            pass  # Ждем, пока пользователь доведет ввод до валидного числа

    def on_dist_text_changed(self, text):
        """Реал-тайм обновление при изменении текста в 'Шаг'"""
        try:
            float(text)  # Проверяем, что это валидное число
            self.recalc_table()
        except ValueError:
            pass  # Ждем, пока пользователь доведет ввод до валидного числа

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

        self.lbl_total_vol.setText(f"Итого в каскад: {total_vol:.1f} $")

        count = self.sb_count.value()
        min_size = self.sb_min.value()
        dist_step = self.sb_dist.value()
        mult = self.get_multiplier()

        if total_vol <= 0:
            self.table.setRowCount(0)
            self.calculated_orders = []
            return
        
        # Проверяем: изменился ли тип
        current_type_index = self.cb_type.currentIndex()
        type_changed = (current_type_index != self._last_type_index)
        
        # Проверяем: был ли count на максимуме перед изменением типа
        user_was_at_max = (count == self._last_max_possible)

        # Вычисляем максимально возможное количество ячеек
        if mult == 1.0:
            # Равномерное распределение: все ячейки = total_vol / count
            max_possible = int(total_vol / min_size)
        else:
            # Матрешка: геометрическая прогрессия
            # Сумма геометрической прогрессии: S = min_size * (mult^n - 1) / (mult - 1)
            # Ограничение: S <= total_vol
            # Находим максимальный n такой, что S(n) <= total_vol
            max_possible = 1
            while True:
                geo_sum = min_size * (mult**max_possible - 1) / (mult - 1)
                if geo_sum > total_vol:
                    break
                max_possible += 1
            max_possible = max(1, max_possible - 1)

        if max_possible < 1:
            max_possible = 1

        # Устанавливаем максимум для SpinBox
        self.sb_count.blockSignals(True)
        self.sb_count.setMaximum(max_possible)
        
        # Если тип изменился или пользователь был на максимуме, ставим новый максимум
        if type_changed or user_was_at_max:
            self.sb_count.setValue(max_possible)
        elif count > max_possible:
            # Если count > max_possible, принудительно ограничиваем
            self.sb_count.setValue(max_possible)
        
        self.sb_count.blockSignals(False)
        
        # Запоминаем текущий максимум и тип для следующего вызова
        self._last_max_possible = max_possible
        self._last_type_index = current_type_index

        # === РАВНОМЕРНОЕ РАСПРЕДЕЛЕНИЕ ===
        if mult == 1.0:
            # Используем введенное кол-во, делим поровну
            vol_per_cell = total_vol / count
            final_volumes = [vol_per_cell for _ in range(count)]

            # Подсказка для равномерного
            self.lbl_count_hint.setText(f"Макс: {max_possible} ячеек")
            if count > max_possible:
                self.lbl_count_hint.setStyleSheet(
                    "color: #FF6B6B; font-size: 8pt; font-weight: bold;"
                )
            else:
                self.lbl_count_hint.setStyleSheet("color: #888; font-size: 8pt;")

        else:
            # === МАТРЕШКА/АГРЕССИВНО (экспоненциальное распределение) ===
            # Геометрическая прогрессия с масштабированием
            # volume[i] = scale * min_size * mult^i
            # где scale подбирается так, чтобы сумма = total_vol

            # Вычисляем сумму идеальной геометрической прогрессии
            # S = min_size * (mult^count - 1) / (mult - 1)
            geo_sum = min_size * (mult**count - 1) / (mult - 1)

            # Вычисляем коэффициент масштабирования
            scale = total_vol / geo_sum if geo_sum > 0 else 1.0

            # Генерируем масштабированный ряд
            final_volumes = [scale * min_size * (mult**i) for i in range(count)]

            # Подсказка для матрешки с максимумом
            self.lbl_count_hint.setText(f"Макс: {max_possible} ячеек")
            if count > max_possible:
                self.lbl_count_hint.setStyleSheet(
                    "color: #FF6B6B; font-size: 8pt; font-weight: bold;"
                )
            else:
                self.lbl_count_hint.setStyleSheet("color: #888; font-size: 8pt;")

        # Заполнение таблицы
        self.table.setRowCount(len(final_volumes))
        self.calculated_orders = []

        for i, vol in enumerate(final_volumes):
            dist = i * dist_step
            vol_item = QTableWidgetItem(f"{vol:.2f}")
            vol_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Подсвечиваем если < min_size
            if vol < min_size:
                vol_item.setForeground(Qt.GlobalColor.red)

            self.table.setItem(i, 0, vol_item)

            dist_item = QTableWidgetItem(f"{dist:.2f}")
            dist_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, dist_item)
            self.calculated_orders.append(
                {"vol": round(vol, 2), "dist": round(dist, 2)}
            )

    def start_calibration(self):
        # Получаем горячую клавишу для захвата координат из настроек
        self.calib_hotkey = self.main.settings.get("hk_coords", "f2").lower()
        hotkey_display = self.calib_hotkey.upper().replace("+", " + ")

        self.lbl_status.setText(
            f"1. Наведи на ШЕСТЕРЕНКУ настроек -> нажми {hotkey_display}"
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
                f"2. Наведи на пункт меню 'КНИГА ЗАЯВОК' -> {hotkey_display}"
            )

        elif self.calib_step == 2:
            self.main.settings["cas_p_book"] = [x, y]
            self.lbl_status.setText(
                f"3. Наведи на ПОЛЗУНОК СКРОЛЛБАРА (полоса прокрутки внизу) -> {hotkey_display}\n"
                f"(Это нужно для корректного скроллинга к строкам ордеров)"
            )

        elif self.calib_step == 3:
            self.main.settings["cas_p_scrollbar"] = [x, y]
            self.lbl_status.setText(
                f"4. Наведи на поле ввода ОБЪЕМА первой строки -> {hotkey_display}"
            )

        elif self.calib_step == 4:
            self.main.settings["cas_p_vol1"] = [x, y]
            self.lbl_status.setText(
                f"5. Наведи на поле ДИСТАНЦИИ (0%) первой строки -> {hotkey_display}"
            )

        elif self.calib_step == 5:
            self.main.settings["cas_p_dist1"] = [x, y]
            self.lbl_status.setText(
                f"6. Наведи на поле ОБЪЕМА ВТОРОЙ строки -> {hotkey_display}"
            )

        elif self.calib_step == 6:
            self.main.settings["cas_p_vol2"] = [x, y]
            self.lbl_status.setText(f"7. Наведи на кнопку ПЛЮС (+) -> {hotkey_display}")

        elif self.calib_step == 7:
            self.main.settings["cas_p_plus"] = [x, y]
            self.lbl_status.setText(
                f"8. Наведи на кнопку УДАЛИТЬ (X) первой строки -> {hotkey_display}"
            )

        elif self.calib_step == 8:
            self.main.settings["cas_p_x"] = [x, y]
            self.lbl_status.setText("✓ Калибровка завершена! Настройки сохранены.")
            self.lbl_status.setStyleSheet("color: #38BE1D;")
            self.main.save_settings()
            keyboard.remove_hotkey(self.calib_hotkey)

        self.calib_step += 1

    def run_automation(self):
        if not hasattr(self, "calculated_orders") or not self.calculated_orders:
            self.recalc_table()

        self.lbl_status.setText("Выставляю ордера... Нажми ESC для остановки")
        self.lbl_status.setStyleSheet("color: #FF9F0A;")
        self.worker = CascadeWorker(
            self.main.settings, self.calculated_orders, self.main
        )
        self.worker.finished.connect(
            lambda: self.lbl_status.setText("Каскад выставлен!")
        )
        self.worker.cancelled.connect(
            lambda: self.lbl_status.setText("Остановлено пользователем (ESC)")
        )
        self.worker.start()
