import os

# Автоматически определяем папку проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Пути к файлам
CONFIG_FILE = os.path.join(BASE_DIR, "ScalpSettings_Py.json")
# Используем r"" для корректной работы путей Windows
LOGO_PATH = os.path.join(BASE_DIR, "Logo", "Logo.png")
MY_APP_ID = 'riskvolume.calc.v2'