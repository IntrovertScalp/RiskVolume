from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTableWidget,
    QAbstractItemView,
    QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, QRegularExpression, QTimer
from PyQt6.QtGui import QRegularExpressionValidator


class PercentItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
            editor.setFrame(False)
            editor.setFont(option.font)
            editor.setContentsMargins(0, 0, 0, 0)
            editor.setStyleSheet("padding: 0px; margin: 0px;")
            QTimer.singleShot(0, editor.selectAll)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


def init_calculator_tab(app):
    main_layout = QVBoxLayout(app.tab_calculator)
    main_layout.setContentsMargins(5, 5, 5, 5)
    main_layout.setSpacing(6)
    app.calc_layout = main_layout
    v_reg = QRegularExpressionValidator(QRegularExpression(r"[0-9]*[.,]?[0-9]*"))

    # --- ДЕПОЗИТ (ВВЕРХУ НА ВСЮ ШИРИНУ) ---
    app.lbl_dep_title = QLabel("...")
    app.lbl_dep_title.setStyleSheet("color: #888; font-size: 8pt; font-weight: bold;")
    main_layout.addWidget(app.lbl_dep_title)

    # Депозит без форматирования при загрузке
    dep_val = app.settings.get("deposit", 1000)
    app.inp_dep = QLineEdit(
        str(int(dep_val) if dep_val == int(dep_val) else dep_val).replace(".", ",")
    )
    app.inp_dep.setValidator(v_reg)
    app.inp_dep.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_dep.setFixedHeight(26)
    app.inp_dep.textChanged.connect(app.update_calc)
    app.inp_dep.returnPressed.connect(app._commit_input)
    app.inp_dep.installEventFilter(app)
    main_layout.addWidget(app.inp_dep)

    app.lbl_hint = QLabel("0")
    app.lbl_hint.setStyleSheet("color: #666; font-size: 7pt;")
    app.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignLeft)
    main_layout.addWidget(app.lbl_hint)

    # --- РИСК И СТОП В ОДНОЙ СТРОКЕ ---
    risk_stop_row = QHBoxLayout()
    risk_stop_row.setSpacing(8)

    # Риск
    risk_col = QVBoxLayout()
    risk_col.setSpacing(2)
    app.lbl_risk_title = QLabel("...")
    app.lbl_risk_title.setStyleSheet("color: #888; font-size: 8pt; font-weight: bold;")
    risk_col.addWidget(app.lbl_risk_title)
    app.inp_risk = QLineEdit(str(app.settings.get("risk", 1)))
    app.inp_risk.setValidator(v_reg)
    app.inp_risk.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_risk.setFixedHeight(26)
    app.inp_risk.textChanged.connect(app.update_calc)
    app.inp_risk.returnPressed.connect(app._commit_input)
    app.inp_risk.installEventFilter(app)
    risk_col.addWidget(app.inp_risk)
    risk_stop_row.addLayout(risk_col)

    # Стоп
    stop_col = QVBoxLayout()
    stop_col.setSpacing(2)
    app.lbl_stop_title = QLabel("...")
    app.lbl_stop_title.setStyleSheet("color: #888; font-size: 8pt; font-weight: bold;")
    stop_col.addWidget(app.lbl_stop_title)
    app.inp_stop = QLineEdit(str(app.settings.get("stop", 1)))
    app.inp_stop.setValidator(v_reg)
    app.inp_stop.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_stop.setFixedHeight(26)
    app.inp_stop.textChanged.connect(app.update_calc)
    app.inp_stop.returnPressed.connect(app._commit_input)
    app.inp_stop.installEventFilter(app)
    stop_col.addWidget(app.inp_stop)
    risk_stop_row.addLayout(stop_col)

    main_layout.addLayout(risk_stop_row)

    # --- ИНФОРМАЦИЯ (Риск сделки, Комиссия, Плечо) ---
    app.lbl_info = QLabel("")
    app.lbl_info.setStyleSheet("color: #888; font-size: 8pt; line-height: 1.2;")
    app.lbl_info.setWordWrap(True)
    app.lbl_info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    main_layout.addWidget(app.lbl_info)

    # --- ОБЪЁМ (ПОСЛЕ ИНФОРМАЦИИ) ---
    app.lbl_vol_title = QLabel("...")
    app.lbl_vol_title.setStyleSheet(
        "color: #888; font-size: 11pt; font-weight: bold; margin-top: 2px;"
    )
    main_layout.addWidget(app.lbl_vol_title)

    app.lbl_vol = QLabel("0")
    app.lbl_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.lbl_vol.setStyleSheet(
        "color: #FF9F0A; font-size: 11pt; font-weight: bold; border: 1px solid #333; "
        "border-radius: 4px; padding: 4px; background: #1A1A1A;"
    )
    app.lbl_vol.setFixedHeight(36)
    main_layout.addWidget(app.lbl_vol)

    # --- НАСТРОЙКА ЯЧЕЕК ---
    cells_header = QHBoxLayout()

    # Кнопка переворота таблицы
    app.btn_reverse_cells = QPushButton("⇅")
    app.btn_reverse_cells.setFixedSize(25, 25)
    app.btn_reverse_cells.setToolTip("Перевернуть порядок ячеек")
    app.btn_reverse_cells.clicked.connect(app.toggle_cells_order)
    cells_header.addWidget(app.btn_reverse_cells)

    lbl_cells = QLabel("Кол-во:")
    lbl_cells.setStyleSheet("font-size: 8pt;")
    cells_header.addWidget(lbl_cells)

    # Кнопка уменьшить
    app.btn_cells_minus = QPushButton("-")
    app.btn_cells_minus.setFixedSize(25, 25)
    app.btn_cells_minus.clicked.connect(app.decrease_cells)
    cells_header.addWidget(app.btn_cells_minus)

    # Отображение количества (с возможностью прокрутки колесиком)
    app.lbl_cells_count = QLabel(str(app.settings.get("scalp_cells_count", 4)))
    app.lbl_cells_count.setStyleSheet(
        "color: white; font-weight: bold; font-size: 8pt;"
    )
    app.lbl_cells_count.setFixedWidth(20)
    app.lbl_cells_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
    # Включаем захват колесика мыши
    app.lbl_cells_count.installEventFilter(app)
    cells_header.addWidget(app.lbl_cells_count)

    # Кнопка увеличить
    app.btn_cells_plus = QPushButton("+")
    app.btn_cells_plus.setFixedSize(25, 25)
    app.btn_cells_plus.clicked.connect(app.increase_cells)
    cells_header.addWidget(app.btn_cells_plus)

    # Минимальный ордер
    lbl_min_order = QLabel("Мин.ордер:")
    lbl_min_order.setStyleSheet("font-size: 8pt;")
    cells_header.addWidget(lbl_min_order)
    app.inp_min_order = QLineEdit(str(app.settings.get("scalp_min_order", 6)))
    app.inp_min_order.setValidator(v_reg)
    app.inp_min_order.setFixedWidth(50)
    app.inp_min_order.setFixedHeight(22)
    app.inp_min_order.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_min_order.setStyleSheet("font-size: 8pt; padding: 2px;")
    app.inp_min_order.returnPressed.connect(app.on_min_order_changed)
    app.inp_min_order.installEventFilter(app)
    cells_header.addWidget(app.inp_min_order)

    # Тип распределения (слева, в той же строке)
    lbl_type = QLabel("Тип:")
    lbl_type.setStyleSheet("font-size: 8pt;")
    cells_header.addWidget(lbl_type)
    app.cb_distribution = QComboBox()
    app.cb_distribution.addItems(["Равномерно", "Убывающая", "Вручную"])
    saved_type = app.settings.get("scalp_distribution_type", 0)
    if saved_type >= 3:
        saved_type = 0  # Защита от устаревших значений
    app.cb_distribution.setCurrentIndex(saved_type)
    app.cb_distribution.currentIndexChanged.connect(app.apply_distribution_preset)
    app.cb_distribution.setStyleSheet(
        """
        QComboBox { background: #1A1A1A; color: white; border: 1px solid #333; padding: 3px; border-radius: 4px; font-size: 8pt; }
        """
    )
    app.cb_distribution.installEventFilter(app)
    cells_header.addWidget(app.cb_distribution)
    cells_header.addStretch()
    main_layout.addLayout(cells_header)

    # Таблица на всю ширину (3 колонки, всегда 5 строк)
    app.cells_table = QTableWidget()
    app.cells_table.setColumnCount(3)
    app.cells_table.setHorizontalHeaderLabels(
        ["Ячейки:", "Объемы:", "% от общего объёма"]
    )
    app.cells_table.verticalHeader().setVisible(False)
    app.cells_table.horizontalHeader().setStretchLastSection(True)
    app.cells_table.setEditTriggers(
        QAbstractItemView.EditTrigger.SelectedClicked
        | QAbstractItemView.EditTrigger.DoubleClicked
    )
    app.cells_table.setStyleSheet(
        """
        QTableWidget { 
            background: #1A1A1A; 
            gridline-color: #333; 
            color: white; 
            border: 1px solid #333;
            border-radius: 4px;
            show-decoration-selected: 0;
        }
        QHeaderView::section { 
            background: #252525; 
            color: #888; 
            border: 1px solid #333;
            padding: 4px;
            font-size: 8pt;
        }
        QTableWidget::item {
            padding: 5px;
            border: none;
            color: white;
            background: #1A1A1A;
            outline: none;
            font-size: 6pt;
        }
        QTableWidget::item:focus {
            border: none;
            outline: none;
        }
        QTableWidget::item:selected {
            background: #1A1A1A;
            border: none;
        }
        QTableWidget::item:disabled {
            color: #555;
            background: #0F0F0F;
        }
        QLineEdit {
            background: #1A1A1A !important;
            color: white;
            border: 1px solid #333 !important;
            border-radius: 4px;
            padding: 1px;
            font-size: 6pt;
            margin: 0px;
            selection-background-color: rgba(90, 205, 80, 150);
            selection-color: white;
        }
        """
    )
    app.cells_table.setItemDelegateForColumn(2, PercentItemDelegate(app.cells_table))
    # Устанавливаем пропорции колонок (30%, 35%, 35%)
    app.cells_table.horizontalHeader().setSectionResizeMode(
        0, app.cells_table.horizontalHeader().ResizeMode.Stretch
    )
    app.cells_table.horizontalHeader().setSectionResizeMode(
        1, app.cells_table.horizontalHeader().ResizeMode.Stretch
    )
    app.cells_table.horizontalHeader().setSectionResizeMode(
        2, app.cells_table.horizontalHeader().ResizeMode.Stretch
    )
    # Обработчик для предотвращения выделения колонок 0 и 1
    app.cells_table.itemClicked.connect(app.on_table_item_clicked)
    main_layout.addWidget(app.cells_table)

    # --- КНОПКИ (КАЛИБРОВКА И ВЫСТАВИТЬ) ---
    h_btn = QHBoxLayout()
    app.btn_calib_calc = QPushButton("КАЛИБРОВКА")
    app.btn_calib_calc.setStyleSheet("background: #333; color: white; padding: 8px;")
    app.btn_calib_calc.clicked.connect(app.start_calibration_calc)
    app.btn_submit = QPushButton("ВЫСТАВИТЬ")
    app.btn_submit.setStyleSheet(
        "background: #38BE1D; color: black; font-weight: bold; padding: 8px;"
    )
    app.btn_submit.clicked.connect(app.send_volume_to_terminal)
    h_btn.addWidget(app.btn_calib_calc)
    h_btn.addWidget(app.btn_submit)
    main_layout.addLayout(h_btn)

    # --- СТАТУС (ВНИЗУ) ---
    app.lbl_status = QLabel("")
    app.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.lbl_status.setStyleSheet("color: #666; font-size: 7pt;")
    main_layout.addWidget(app.lbl_status)

    # Добавляем растяжение в конец
    main_layout.addStretch()

    # Создаём поля ячеек (всегда 5 строк)
    app.on_cells_changed()
    app.update_calibration_status()
    # Вызываем один раз при инициализации для показа статуса
    QTimer.singleShot(100, app._update_status_text)
