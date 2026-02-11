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
):
    """HTML-блок для калькулятора, принимает txt_labels (словарь текстов)"""
    return f"""
    <div style="line-height: 140%;">
        <span style="color: #888; font-size: {font_size}pt;">{txt_labels['risk_deal']} </span>
        <b style="color: #FF453A; font-size: {font_size+1}pt;">${smart_format(cash_risk, prec_risk)}</b><br>
        
        <span style="color: #888; font-size: {font_size}pt;">{txt_labels['comm']} </span>
        <b style="color: #FF9F0A; font-size: {font_size}pt;">${smart_format(comm_usd, prec_fee)}</b><br>
        
        <span style="color: #888; font-size: {font_size}pt;">{txt_labels['lev']} </span>
        <b style="color: #FFFFFF; font-size: {font_size}pt;">{smart_format(leverage, prec_lev)}x</b>
    </div>
    """
