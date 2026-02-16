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
    QCheckBox,
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
    main_layout.setContentsMargins(4, 4, 4, 4)
    main_layout.setSpacing(4)
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
    app.inp_dep.setFixedHeight(24)
    app.inp_dep.textChanged.connect(app.schedule_update_calc)
    app.inp_dep.returnPressed.connect(app._commit_input)
    app.inp_dep.installEventFilter(app)
    main_layout.addWidget(app.inp_dep)

    app.lbl_hint = QLabel("0")
    app.lbl_hint.setStyleSheet("color: #666; font-size: 8pt;")
    app.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignLeft)
    main_layout.addWidget(app.lbl_hint)

    # --- РИСК И СТОП В ОДНОЙ СТРОКЕ ---
    risk_stop_row = QHBoxLayout()
    risk_stop_row.setSpacing(6)

    # Риск
    risk_col = QVBoxLayout()
    risk_col.setSpacing(1)
    app.lbl_risk_title = QLabel("...")
    app.lbl_risk_title.setStyleSheet("color: #888; font-size: 8pt; font-weight: bold;")
    risk_col.addWidget(app.lbl_risk_title)
    app.inp_risk = QLineEdit(str(app.settings.get("risk", 1)))
    app.inp_risk.setValidator(v_reg)
    app.inp_risk.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_risk.setFixedHeight(24)
    app.inp_risk.textChanged.connect(app.schedule_update_calc)
    app.inp_risk.returnPressed.connect(app._commit_input)
    app.inp_risk.installEventFilter(app)
    risk_col.addWidget(app.inp_risk)
    risk_stop_row.addLayout(risk_col)

    # Стоп
    stop_col = QVBoxLayout()
    stop_col.setSpacing(1)
    app.lbl_stop_title = QLabel("...")
    app.lbl_stop_title.setStyleSheet("color: #888; font-size: 8pt; font-weight: bold;")
    stop_col.addWidget(app.lbl_stop_title)
    app.inp_stop = QLineEdit(str(app.settings.get("stop", 1)))
    app.inp_stop.setValidator(v_reg)
    app.inp_stop.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_stop.setFixedHeight(24)
    app.inp_stop.textChanged.connect(app.schedule_update_calc)
    app.inp_stop.returnPressed.connect(app._commit_input)
    app.inp_stop.installEventFilter(app)
    stop_col.addWidget(app.inp_stop)
    risk_stop_row.addLayout(stop_col)

    main_layout.addLayout(risk_stop_row)

    # --- ИНФОРМАЦИЯ (Риск сделки, Комиссия, Плечо) ---
    app.lbl_info = QLabel("")
    app.lbl_info.setStyleSheet("color: #888; font-size: 9pt; line-height: 1.2;")
    app.lbl_info.setWordWrap(False)
    app.lbl_info.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    app.lbl_info.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    main_layout.addWidget(app.lbl_info)

    # --- ОБЪЁМ (ПОСЛЕ ИНФОРМАЦИИ) ---
    app.lbl_vol_title = QLabel("...")
    app.lbl_vol_title.setStyleSheet(
        "color: #888; font-size: 9pt; font-weight: 600; margin-top: 2px;"
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

    app.chk_pos_mode = QCheckBox("Расчет в позиции (добор/сокращение)")
    app.chk_pos_mode.setObjectName("PosModeToggle")
    app.chk_pos_mode.setChecked(bool(app.settings.get("pos_mode_enabled", True)))
    app.chk_pos_mode.toggled.connect(app.on_position_mode_toggled)
    main_layout.addWidget(app.chk_pos_mode)

    # --- ДОБОР / СОКРАЩЕНИЕ ПО ТЕКУЩЕЙ ПОЗИЦИИ ---
    pos_row = QHBoxLayout()
    pos_row.setSpacing(6)

    pos_vol_col = QVBoxLayout()
    pos_vol_col.setSpacing(1)
    lbl_pos_vol = QLabel("В позиции:")
    lbl_pos_vol.setStyleSheet("font-size: 8pt;")
    pos_vol_col.addWidget(lbl_pos_vol)

    app.inp_pos_vol = QLineEdit(str(app.settings.get("pos_current_vol", "0")))
    app.inp_pos_vol.setValidator(v_reg)
    app.inp_pos_vol.setFixedHeight(22)
    app.inp_pos_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_pos_vol.setStyleSheet("font-size: 8pt; padding: 1px;")
    app.inp_pos_vol.returnPressed.connect(app._commit_input)
    app.inp_pos_vol.installEventFilter(app)
    app.inp_pos_vol.textChanged.connect(app.update_position_adjustment_info)
    pos_vol_col.addWidget(app.inp_pos_vol)

    pos_risk_col = QVBoxLayout()
    pos_risk_col.setSpacing(1)
    lbl_pos_risk = QLabel("Риск сделки %:")
    lbl_pos_risk.setStyleSheet("font-size: 8pt;")
    pos_risk_col.addWidget(lbl_pos_risk)

    app.inp_pos_risk = QLineEdit(str(app.settings.get("pos_risk", "1")))
    app.inp_pos_risk.setValidator(v_reg)
    app.inp_pos_risk.setFixedHeight(22)
    app.inp_pos_risk.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_pos_risk.setStyleSheet("font-size: 8pt; padding: 1px;")
    app.inp_pos_risk.returnPressed.connect(app._commit_input)
    app.inp_pos_risk.installEventFilter(app)
    app.inp_pos_risk.textChanged.connect(app.update_position_adjustment_info)
    pos_risk_col.addWidget(app.inp_pos_risk)

    pos_stop_col = QVBoxLayout()
    pos_stop_col.setSpacing(1)
    lbl_pos_stop = QLabel("Стоп %:")
    lbl_pos_stop.setStyleSheet("font-size: 8pt;")
    pos_stop_col.addWidget(lbl_pos_stop)

    app.inp_pos_stop = QLineEdit(str(app.settings.get("pos_stop", "0")))
    app.inp_pos_stop.setValidator(v_reg)
    app.inp_pos_stop.setFixedHeight(22)
    app.inp_pos_stop.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_pos_stop.setStyleSheet("font-size: 8pt; padding: 1px;")
    app.inp_pos_stop.returnPressed.connect(app._commit_input)
    app.inp_pos_stop.installEventFilter(app)
    app.inp_pos_stop.textChanged.connect(app.update_position_adjustment_info)
    pos_stop_col.addWidget(app.inp_pos_stop)

    pos_row.addLayout(pos_vol_col, 1)
    pos_row.addLayout(pos_risk_col, 1)
    pos_row.addLayout(pos_stop_col, 1)
    main_layout.addLayout(pos_row)

    pos_hints_row = QHBoxLayout()
    pos_hints_row.setSpacing(6)

    app.lbl_pos_vol_hint = QLabel("0")
    app.lbl_pos_vol_hint.setStyleSheet("color: #666; font-size: 8pt;")
    app.lbl_pos_vol_hint.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    pos_hints_row.addWidget(app.lbl_pos_vol_hint, 1)

    app.lbl_pos_risk_cash = QLabel("Риск сделки в $: —")
    app.lbl_pos_risk_cash.setStyleSheet("color: #888; font-size: 8pt;")
    app.lbl_pos_risk_cash.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    pos_hints_row.addWidget(app.lbl_pos_risk_cash, 1)

    app.lbl_pos_adjust = QLabel("Рекомендация: —")
    app.lbl_pos_adjust.setStyleSheet("color: #888; font-size: 8pt;")
    app.lbl_pos_adjust.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    app.lbl_pos_adjust.setWordWrap(False)
    pos_hints_row.addWidget(app.lbl_pos_adjust, 1)

    main_layout.addLayout(pos_hints_row)

    # --- НАСТРОЙКА ЯЧЕЕК ---
    cells_header = QHBoxLayout()

    # Кнопка переворота таблицы
    app.btn_reverse_cells = QPushButton("⇅")
    app.btn_reverse_cells.setStyleSheet("color: #8E8E8E;")
    app.btn_reverse_cells.setFixedSize(34, 25)
    app.btn_reverse_cells.setToolTip("Перевернуть порядок ячеек")
    app.btn_reverse_cells.clicked.connect(app.toggle_cells_order)
    cells_header.addWidget(app.btn_reverse_cells)

    app.btn_move_adjust_to_cell = QPushButton("↪")
    app.btn_move_adjust_to_cell.setFixedSize(34, 25)
    app.btn_move_adjust_to_cell.setToolTip("Перенести сумму в выбранные ячейки")
    app.btn_move_adjust_to_cell.setStyleSheet("color: #8E8E8E;")
    app.btn_move_adjust_to_cell.clicked.connect(app.apply_position_adjustment_to_cell)
    app.btn_move_adjust_to_cell.setEnabled(False)
    cells_header.addWidget(app.btn_move_adjust_to_cell)

    # Количество ячеек фиксируем на 5, управление теперь только выделением строк
    app.lbl_cells_count = QLabel("5")
    app.lbl_cells_count.hide()

    # Минимальный ордер
    lbl_min_order = QLabel("Мин.ордер:")
    lbl_min_order.setStyleSheet("font-size: 8pt;")
    cells_header.addWidget(lbl_min_order)
    min_order_val = int(float(app.settings.get("scalp_min_order", 6) or 6))
    app.inp_min_order = QLineEdit(str(min_order_val))
    app.inp_min_order.setValidator(
        QRegularExpressionValidator(QRegularExpression(r"[0-9]*"))
    )
    app.inp_min_order.setFixedWidth(50)
    app.inp_min_order.setFixedHeight(22)
    app.inp_min_order.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.inp_min_order.setStyleSheet("font-size: 8pt; padding: 2px;")
    app.inp_min_order.textChanged.connect(app.on_min_order_live_changed)
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
    app.cells_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Remove focus border
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
            color: #777;
            background: #000000;
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

    # --- КНОПКА ВЫСТАВИТЬ ---
    app.btn_submit = QPushButton("ВЫСТАВИТЬ")
    app.btn_submit.setStyleSheet(
        "background: #38BE1D; color: black; font-weight: bold; padding: 6px 16px 6px 24px;"
    )
    app.btn_submit.clicked.connect(app.send_volume_to_terminal)
    main_layout.addWidget(app.btn_submit)

    # --- СТАТУС (ВНИЗУ) ---
    app.lbl_status = QLabel("")
    app.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.lbl_status.setStyleSheet("color: #666; font-size: 8pt;")
    main_layout.addWidget(app.lbl_status)

    # Создаём поля ячеек (всегда 5 строк)
    app.on_position_mode_toggled(
        app.chk_pos_mode.isChecked(), is_startup=True
    )  # Restore mode state without overriding distribution
    app.on_cells_changed()
    app.update_calibration_status()
    app.update_position_adjustment_info()
    # Вызываем один раз при инициализации для показа статуса
    QTimer.singleShot(100, app._update_status_text)
