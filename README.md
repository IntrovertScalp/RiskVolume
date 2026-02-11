# RiskVolume - Trading Risk Calculator

A professional PyQt6-based trading calculator for risk management and automated order placement.

## Features

### Core Functionality
- **Risk Calculator**: Calculate position size based on deposit, risk percentage, and stop loss
- **Volume Distribution**: Distribute capital across multiple orders with various strategies
- **Cascade Orders (Profit Forge)**: Automated placement of multiple orders with custom volumes and distances
- **Real-time Calculation**: Dynamic updates with commission fee consideration

### Order Distribution Types
1. **Uniform**: Equal distribution across all orders
2. **Decreasing**: Gradually decreasing volumes (100%, 75%, 50%, 25%, 10%)
3. **Scalper**: Optimized for scalping (40%, 20%, 15%, 15%, 10%)
4. **Pyramid**: Pyramiding strategy (50%, 25%, 15%, 7%, 3%)
5. **Manual**: Custom percentage allocation

### Cascade Types
- **Uniform**: Equal order sizes
- **Matryoshka x1.2**: Progressive increase by 1.2x multiplier
- **Matryoshka x1.5**: Progressive increase by 1.5x multiplier
- **Aggressive x2**: Progressive increase by 2x multiplier

### Advanced Features
- **Commission Management**: Separate Maker/Taker fee configuration with toggle
- **Calibration System**: Point-and-click coordinate capture for terminal automation
- **Hotkey Support**: Configurable keyboard shortcuts (F1: Show/Hide, F2: Calibration, F3: Send)
- **UI Scaling**: Adjustable interface size (80%-200%, baseline 150%)
- **Multi-language**: Russian/English interface
- **Precision Control**: Customizable decimal places for all values
- **Settings Persistence**: All configurations saved automatically
- **Window Management**: Position memory, drag functionality, minimize on execution

## Technical Stack
- **Framework**: PyQt6
- **Automation**: pyautogui, keyboard
- **Clipboard**: pyperclip
- **Configuration**: JSON-based settings storage

## Installation

```bash
# Install dependencies
pip install PyQt6 pyautogui keyboard pyperclip

# Run application
python main.py
```

## Usage

### Calculator Tab
1. Enter deposit amount
2. Set risk percentage
3. Define stop loss percentage
4. Adjust number of orders and minimum order size
5. Select distribution type
6. Click "CALIBRATE" to set terminal coordinates
7. Click "EXECUTE" to place orders

### Cascades Tab (Profit Forge)
1. Select percentage of total volume (25%, 50%, 75%, 100%)
2. Configure quantity, minimum order size, type, and distance step
3. Click "CALIBRATE" to capture terminal interface points
4. Click "EXECUTE" to place cascade orders

### Settings
- **Hotkeys**: Customize keyboard shortcuts
- **Commission**: Configure Maker/Taker fees (toggle on/off)
- **Display Precision**: Set decimal places for each value type
- **Interface Scale**: Adjust UI size
- **Language**: Switch between Russian/English

## Project Structure
```
RiskVolume/
├── main.py                    # Main application entry
├── cascade_tab.py            # Cascade orders functionality
├── ui_components.py          # Settings dialog and UI components
├── logic.py                  # Risk calculation logic
├── translations.py           # Multi-language support
├── config.py                 # Configuration management
├── ScalpSettings_Py.json     # Persistent settings
└── Logo/                     # Application assets
```

## Configuration

All settings are stored in `ScalpSettings_Py.json` including:
- Window position and scale
- Hotkey mappings
- Commission fees (Maker/Taker)
- Precision settings
- Calibration points
- Order distribution preferences

## License

Private project - All rights reserved

## Author

IntrovertScalp
