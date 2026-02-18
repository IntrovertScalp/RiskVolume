def calculate_risk_data(deposit, risk_percent, stop_percent, fee_percent=0.1):
    if stop_percent <= 0:
        return 0, 0, 0, 0

    # 1. Считаем риск в $
    cash_risk = deposit * (risk_percent / 100)

    # 2. Считаем объем (Стоп + Комиссия)
    total_loss_factor = (stop_percent + fee_percent) / 100
    volume = cash_risk / total_loss_factor

    # 3. Плечо
    leverage = volume / deposit if deposit > 0 else 0

    # 4. Комиссия в $
    comm_usd = volume * (fee_percent / 100)

    return cash_risk, volume, leverage, comm_usd


def smart_format(value, precision=2):
    """Для отображения в окне: пробелы-тысячные и запятая"""
    try:
        format_str = f"{{:,.{precision}f}}"
        return format_str.format(value).replace(",", " ").replace(".", ",")
    except:
        return str(value)


def get_info_html(
    cash_risk,
    leverage,
    comm_usd,
    txt_labels,
    prec_risk=2,
    prec_fee=3,
    prec_lev=1,
    font_size=8,
    dimmed=False,
):
    """HTML-блок для калькулятора, принимает txt_labels (словарь текстов)"""
    if dimmed:
        # Затемнённые цвета
        text_color = "#555"
        risk_color = "#555"
        sep_color = "#555"
        comm_color = "#555"
        lev_color = "#555"
    else:
        # Обычные цвета
        text_color = "#888"
        risk_color = "#FF453A"
        sep_color = "#666"
        comm_color = "#FF9F0A"
        lev_color = "#A8A8A8"

    return f"""
    <div style="line-height: 120%; white-space: nowrap;">
        <span style="color: {text_color}; font-size: {font_size}pt;">{txt_labels['risk_deal']} </span>
        <b style="color: {risk_color}; font-size: {font_size+1}pt;">${smart_format(cash_risk, prec_risk)}</b>
        <span style="color: {sep_color};">  |  </span>
        <span style="color: {text_color}; font-size: {font_size}pt;">{txt_labels['comm']} </span>
        <b style="color: {comm_color}; font-size: {font_size}pt;">${smart_format(comm_usd, prec_fee)}</b>
        <span style="color: {sep_color};">  |  </span>
        <span style="color: {text_color}; font-size: {font_size}pt;">{txt_labels['lev']} </span>
        <b style="color: {lev_color}; font-size: {font_size}pt;">{smart_format(leverage, prec_lev)}x</b>
    </div>
    """
