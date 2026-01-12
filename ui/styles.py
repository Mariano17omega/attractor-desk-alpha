"""Theme styles for the application."""

# Color Tokens
COLORS = {
    # Primary (Light Theme - Cyan)
    "primary": "#00C2FF",
    "primary_dark": "#009ACD",
    "primary_fade": "rgba(0, 194, 255, 0.20)",
    "primary_hover": "rgba(0, 194, 255, 0.35)",
    
    # Accessibility - Focus indicator (WCAG AA compliant)
    "focus_outline": "#00C2FF",  # High contrast cyan for focus rings
    
    # Dark Mode (Blue primary with terminal-style backgrounds)
    "dark": {
        "primary": "#135bec",
        "primary_fade": "rgba(19, 91, 236, 0.20)",
        "primary_hover": "rgba(19, 91, 236, 0.35)",
        "background": "#101622",
        "terminal_bg": "#111318",
        "surface": "#1e232e",
        "surface_highlight": "#282e39",
        "border": "#282e39",
        "text_primary": "#FFFFFF",
        "text_secondary": "#9da6b9",  # text-subtle from palette
        "text_muted": "#9da6b9",
    },
    
    # Light Mode (Cyan primary)
    "light": {
        "background": "#F3F4F6",
        "surface": "#FFFFFF",
        "surface_highlight": "#F9FAFB",  # Gray-50
        "border": "#E5E7EB",  # Updated from palette
        "text_primary": "#1F2937",    # Gray-800
        "text_secondary": "#374151",  # Adjusted for WCAG AA (4.5:1 on surface)
        "text_muted": "#6B7280",      # Adjusted for WCAG AA (3:1 on surface)
    }
}

# Fonts
FONTS = {
    "display": "'Rajdhani', 'Segoe UI', sans-serif",
    "body": "'Inter', 'Segoe UI', sans-serif",
    "mono": "'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'",
}

def get_dark_theme_stylesheet() -> str:
    """Get the dark theme QSS stylesheet.
    
    Returns:
        The stylesheet string.
    """
    c = COLORS["dark"]
    p = COLORS
    
    return f"""
    /* Global Styles */
    QWidget {{
        background-color: {c['background']};
        color: {c['text_primary']};
        font-family: {FONTS['body']};
        font-size: 14px;
    }}
    
    /* Main Window */
    QMainWindow {{
        background-color: {c['background']};
    }}
    
    /* Scroll Areas */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    QScrollBar:vertical {{
        background-color: {c['terminal_bg']};
        width: 8px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {c['border']};
        border-radius: 3px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {c['primary']};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: {c['terminal_bg']};
        height: 8px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {c['border']};
        border-radius: 3px;
        min-width: 20px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {c['primary']};
    }}
    
    /* Text Inputs */
    QTextEdit, QPlainTextEdit {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 8px 14px;
        color: {c['text_primary']};
    }}
    
    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c['primary']};
    }}
    
    QLineEdit {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 32px;
        color: {c['text_primary']};
    }}
    
    QLineEdit:focus {{
        border-color: {c['primary']};
    }}

    QLineEdit#keySequenceEdit {{
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-weight: bold;
    }}
    
    QLineEdit#keySequenceEdit:focus {{
        border: none;
    }}

    /* Spin Boxes */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 8px;
        padding-right: 24px;
        min-height: 32px;
        color: {c['text_primary']};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['primary']};
    }}

    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        width: 20px;
        border-left: 1px solid {c['border']};
        background-color: {c['surface_highlight']};
    }}

    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {c['primary_fade']};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {c['primary_fade']};
        color: {c['text_primary']};
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
        font-family: {FONTS['display']};
        letter-spacing: 0.5px;
    }}
    
    QPushButton:hover {{
        background-color: {c['primary_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {c['primary']};
        color: #FFFFFF;
    }}
    
    QPushButton:disabled {{
        background-color: {c['border']};
        color: {c['text_muted']};
    }}
    
    QPushButton:focus {{
        outline: 2px solid {p['focus_outline']};
        outline-offset: 2px;
    }}
    
    /* Icon Buttons (Ghost) */
    QPushButton#iconButton {{
        background-color: transparent;
        color: {c['text_muted']};
        border-radius: 8px;
        padding: 8px;
    }}
    
    QPushButton#iconButton:hover {{
        background-color: {c['surface_highlight']};
        color: {c['primary']};
    }}
    
    QPushButton#deleteButton {{
        background-color: transparent;
        color: #F87171;
        padding: 4px 8px;
        font-size: 12px;
    }}
    
    QPushButton#deleteButton:hover {{
        background-color: rgba(239, 68, 68, 0.2);
    }}
    
    QPushButton#newChatButton {{
        background-color: {c['primary_fade']};
        color: {c['text_primary']};
        border: 1px solid rgba(19, 91, 236, 0.3);
    }}
    
    QPushButton#newChatButton:hover {{
        background-color: {c['primary_hover']};
        color: #FFFFFF;
        border-color: {c['primary']};
    }}
    
    QPushButton#settingsButton {{
        background-color: transparent;
        color: {c['text_muted']};
        border: none;
        padding: 8px;
        border-radius: 50px; 
    }}
    
    QPushButton#settingsButton:hover {{
        color: {c['primary']};
        background-color: {c['surface_highlight']};
    }}
    
    /* ComboBox */
    QComboBox, QFontComboBox {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 32px;
        color: {c['text_primary']};
        min-width: 120px;
    }}
    
    QComboBox:hover, QFontComboBox:hover {{
        border-color: {c['primary']};
    }}
    
    QComboBox:focus, QFontComboBox:focus {{
        border-color: {p['focus_outline']};
        outline: 2px solid {p['focus_outline']};
        outline-offset: 1px;
    }}
    
    QComboBox:drop-down, QFontComboBox:drop-down {{
        border: none;
        width: 0px;
    }}

    
    QComboBox QAbstractItemView {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        selection-background-color: {c['primary_fade']};
        color: {c['text_primary']};
        outline: none;
    }}
    
    QComboBox QAbstractItemView::item {{
        padding-left: 12px;
        padding-right: 12px;
        min-height: 24px;
    }}
    
    /* List Widget */
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}
    
    QListWidget::item {{
        background-color: {c['background']}; /* Often transparent, but can use bg-fade */
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 10px 12px;
        margin: 4px 0;
        color: {c['text_primary']};
    }}
    
    QListWidget::item:selected {{
        background-color: {c['surface_highlight']};
        border-color: {c['primary']};
    }}
    
    QListWidget::item:hover {{
        border-color: rgba(19, 91, 236, 0.5);
    }}
    
    QListWidget::item:focus {{
        border: 2px solid {p['focus_outline']};
    }}
    
    /* Chat List (custom widget items) */
    QListWidget#chatList::item {{
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 0;
    }}
    
    QListWidget#chatList::item:selected {{
        background-color: transparent;
        border: none;
    }}
    
    /* Chat List Item Widget */
    QFrame#chatListItem {{
        background-color: {c['background']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}
    
    QFrame#chatListItem[selected="true"] {{
        background-color: {c['surface_highlight']};
        border-color: {c['primary']};
    }}
    
    QFrame#chatListItem:hover {{
        border-color: rgba(19, 91, 236, 0.5);
    }}
    
    QFrame#chatListItem QLabel#chatListItemTitle {{
        color: {c['text_primary']};
    }}
    
    QPushButton#chatDeleteButton {{
        background-color: transparent;
        color: #F87171;
        border: none;
        padding: 0;
        font-size: 12px;
        min-width: 18px;
        min-height: 18px;
    }}
    
    QPushButton#chatDeleteButton:hover {{
        background-color: rgba(239, 68, 68, 0.2);
    }}

    /* Table Widget */
    QTableWidget {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        gridline-color: {c['border']};
        alternate-background-color: {c['surface_highlight']};
        outline: none;
    }}

    QTableWidget::item {{
        padding: 5px;
        border: none;
        color: {c['text_primary']};
        background-color: {c['surface']};
    }}

    QTableWidget::item:selected {{
        background-color: {c['primary_fade']};
        color: {c['text_primary']};
    }}

    QHeaderView::section {{
        background-color: {c['surface']};
        padding: 5px;
        border: 1px solid {c['border']};
        font-weight: bold;
        color: {c['text_primary']};
    }}

    QTableWidget::item:alternate {{
        background-color: {c['surface_highlight']};
    }}
    
    /* Labels */
    QLabel {{
        background-color: transparent;
    }}
    
    QLabel#headerLabel {{
        font-family: {FONTS['display']};
        font-size: 20px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: {c['text_primary']};
    }}

    QLabel#workspaceHeaderLabel {{
        font-family: {FONTS['display']};
        font-size: 16px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: {c['text_primary']};
    }}
    
    QLabel#sectionLabel {{
        font-family: {FONTS['display']};
        font-size: 11px;
        color: {c['text_muted']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 5px 0;
    }}
    
    /* Splitter */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    
    /* Frame - Sidebar */
    QFrame#sidebar {{
        background-color: {c['surface']};
        border-right: 1px solid {c['border']};
        /* No radius on the container frame itself usually if full height */
    }}
    
    /* Frame - Chat Panel */
    QFrame#chatPanel {{
        background-color: {c['background']};
        /* Optional: bg-grid-pattern handled via overlay usually, simple solid for now */
    }}

    QFrame#chatHeader {{
        background-color: {c['surface']};
        border-bottom: 1px solid {c['border']};
    }}

    QFrame#workspaceMemoryPanel {{
        background-color: {c['surface']};
        border-left: 1px solid {c['border']};
    }}

    QFrame#memoryItem {{
        background-color: {c['surface_highlight']};
        border-radius: 6px;
        border: 1px solid {c['border']};
    }}

    QFrame#messageRow {{
        background-color: transparent;
    }}

    QLabel#assistantAvatar {{
        border: 1px solid {c['primary']};
        border-radius: 20px;
        background-color: {c['surface_highlight']};
        color: {c['primary']};
        font-weight: 700;
    }}

    QLabel#userAvatar {{
        border: 1px solid {c['border']};
        border-radius: 20px;
        background-color: {c['surface']};
        color: {c['text_primary']};
        font-weight: 700;
    }}
    
    /* Chat Message Bubbles */
    QFrame#userMessage {{
        background-color: {c['surface_highlight']};
        border: 1px solid {c['primary']};
        border-radius: 16px;
        border-top-left-radius: 16px;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 16px;
        border-bottom-left-radius: 16px;
        padding: 12px 16px;
    }}
    
    QFrame#userMessage QLabel {{
        color: {c['text_primary']};
    }}
    
    QFrame#assistantMessage {{
        background-color: {c['surface_highlight']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        border-top-left-radius: 4px;
        padding: 12px 16px;
    }}
    
    QFrame#assistantMessage QLabel {{
        color: {c['text_primary']};
    }}
    
    /* Floating Input Area */
    QFrame#inputArea {{
        background-color: {c['surface_highlight']}; 
        border: 1px solid transparent; 
        border-radius: 12px;
    }}
    
    QFrame#inputArea:focus-within {{
        border: 1px solid {c['primary']};
    }}
    
    /* Large Card Buttons (Sidebar) */
    QPushButton#cardButton {{
        background-color: {c['surface_highlight']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 16px;
        text-align: left;
    }}
    
    QPushButton#cardButton:hover {{
        background-color: {c['surface_highlight']}; /* Slightly lighter? handled by overlay? */
        border-color: {c['primary']};
    }}
    
    QPushButton#primaryCardButton {{
        background-color: {c['primary_fade']};
        border: 1px solid rgba(19, 91, 236, 0.3);
        border-radius: 12px;
        padding: 16px;
        text-align: left;
        color: {c['primary']};
    }}
    
    QPushButton#primaryCardButton:hover {{
        background-color: {c['primary_fade']};
        border-color: {c['primary']};
    }}
    
    /* QCheckBox & QRadioButton */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {c['text_primary']};
    }}
    
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {c['border']};
        background: {c['surface']};
    }}
    
    QRadioButton::indicator {{
        border-radius: 10px;
    }}
    
    QCheckBox::indicator:unchecked:hover, QRadioButton::indicator:unchecked:hover {{
        border-color: {c['primary']};
        background: {c['surface_highlight']};
    }}
    
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {c['primary']};
        border-color: {c['primary']};
        image: none; /* We can use a custom icon here if we had one */
    }}
    
    /* Simulate checkmark/dot for now with background */
    QRadioButton::indicator:checked {{
        background: qradialgradient(
            cx: 0.5, cy: 0.5, radius: 0.4,
            fx: 0.5, fy: 0.5,
            stop: 0 {c['text_primary']},
            stop: 0.5 {c['text_primary']},
            stop: 0.6 {c['primary']},
            stop: 1.0 {c['primary']}
        );
    }}

    /* QSlider */
    QSlider::groove:horizontal {{
        border: 1px solid {c['border']};
        height: 6px;
        background: {c['surface_highlight']};
        margin: 2px 0;
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background: {c['primary']};
        border: 1px solid {c['primary']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background: {c['primary_hover']};
    }}

    /* Status Bar */
    QStatusBar {{
        background-color: {c['surface_highlight']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
    }}
    
    QStatusBar::item {{
        border: none;
    }}

    /* RAG Status Label */
    QLabel#ragStatusLabel {{
        padding: 12px;
        border-radius: 8px;
        background-color: {c['surface_highlight']};
        color: {c['text_muted']};
        font-weight: 500;
    }}

    QLabel#ragStatusLabel[state="ready"] {{
        color: #a6e3a1; /* Success green */
        border: 1px solid rgba(166, 227, 161, 0.3);
    }}

    QLabel#ragStatusLabel[state="error"] {{
        color: #f38ba8; /* Error red */
        border: 1px solid rgba(243, 139, 168, 0.3);
    }}

    QLabel#ragStatusLabel[state="default"] {{
        color: {c['text_muted']};
    }}
    
    /* Specific Widget Styles defined by ObjectName */
    /* ... (previous styles) ... */
    """


def get_light_theme_stylesheet() -> str:
    """Get the light theme QSS stylesheet.
    
    Returns:
        The stylesheet string.
    """
    c = COLORS["light"]
    p = COLORS
    
    return f"""
    /* Global Styles */
    QWidget {{
        background-color: {c['background']};
        color: {c['text_primary']};
        font-family: {FONTS['body']};
        font-size: 14px;
    }}
    
    QMainWindow {{
        background-color: {c['background']};
    }}
    
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    /* Scrollbars */
    QScrollBar:vertical {{
        background-color: rgba(0, 0, 0, 0.05);
        width: 8px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: rgba(0, 194, 255, 0.3);
        border-radius: 4px;
        min-height: 20px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {p['primary']};
    }}
    
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: rgba(0, 0, 0, 0.05);
        height: 8px;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: rgba(0, 194, 255, 0.3);
        border-radius: 4px;
        min-width: 20px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {p['primary']};
    }}
    
    /* Inputs */
    QTextEdit, QPlainTextEdit {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 8px 14px;
        color: {c['text_primary']};
    }}
    
    QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {p['primary']};
    }}
    
    QLineEdit {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 32px;
        color: {c['text_primary']};
    }}
    
    QLineEdit:focus {{
        border-color: {p['primary']};
    }}

    QLineEdit#keySequenceEdit {{
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
        font-weight: bold;
    }}
    
    QLineEdit#keySequenceEdit:focus {{
        border: none;
    }}

    /* Spin Boxes */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 8px;
        padding-right: 24px;
        min-height: 32px;
        color: {c['text_primary']};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {p['primary']};
    }}

    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        width: 20px;
        border-left: 1px solid {c['border']};
        background-color: {c['surface_highlight']};
    }}

    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {p['primary_fade']};
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {p['primary_fade']};
        color: {c['text_primary']};
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
        font-family: {FONTS['display']};
    }}
    
    QPushButton:hover {{
        background-color: {p['primary_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {p['primary']};
        color: #FFFFFF;
    }}
    
    QPushButton:disabled {{
        background-color: {c['border']};
        color: {c['text_muted']};
    }}
    
    QPushButton:focus {{
        outline: 2px solid {p['focus_outline']};
        outline-offset: 2px;
    }}
    
    QPushButton#iconButton {{
        background-color: transparent;
        color: {c['text_muted']};
        border-radius: 8px;
        padding: 8px;
    }}
    
    QPushButton#iconButton:hover {{
        background-color: {c['surface_highlight']};
        color: {p['primary']};
    }}
    
    QPushButton#deleteButton {{
        background-color: transparent;
        color: #EF4444;
        padding: 4px 8px;
        font-size: 12px;
    }}
    
    QPushButton#deleteButton:hover {{
        background-color: rgba(239, 68, 68, 0.1);
    }}
    
    QPushButton#newChatButton {{
        background-color: {p['primary_fade']};
        color: {c['text_primary']};
        border: 1px solid rgba(0, 194, 255, 0.2);
    }}
    
    QPushButton#newChatButton:hover {{
        background-color: {p['primary_hover']};
        border-color: {p['primary']};
    }}

    QPushButton#settingsButton {{
        background-color: transparent;
        color: {c['text_muted']};
        border: none;
        padding: 8px;
        border-radius: 50px;
    }}
    
    QPushButton#settingsButton:hover {{
        color: {p['primary']};
        background-color: {c['surface_highlight']};
    }}
    
    /* ComboBox */
    QComboBox, QFontComboBox {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 32px;
        color: {c['text_primary']};
        min-width: 120px;
    }}
    
    QComboBox:hover, QFontComboBox:hover {{
        border-color: {p['primary']};
    }}
    
    QComboBox:focus, QFontComboBox:focus {{
        border-color: {p['focus_outline']};
        outline: 2px solid {p['focus_outline']};
        outline-offset: 1px;
    }}
    
    QComboBox:drop-down, QFontComboBox:drop-down {{
        border: none;
        width: 0px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        selection-background-color: {p['primary_fade']};
        color: {c['text_primary']};
    }}

    QComboBox QAbstractItemView::item {{
        padding-left: 12px;
        padding-right: 12px;
        min-height: 24px;
    }}
    
    /* List Widget */
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}
    
    QListWidget::item {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 10px 12px;
        margin: 4px 0;
        color: {c['text_primary']};
    }}
    
    QListWidget::item:selected {{
        background-color: {p['primary_fade']};
        border-color: {p['primary']};
    }}
    
    QListWidget::item:hover {{
        border-color: rgba(0, 194, 255, 0.4);
    }}
    
    QListWidget::item:focus {{
        border: 2px solid {p['focus_outline']};
    }}
    
    /* Chat List (custom widget items) */
    QListWidget#chatList::item {{
        background-color: transparent;
        border: none;
        padding: 0;
        margin: 0;
    }}
    
    QListWidget#chatList::item:selected {{
        background-color: transparent;
        border: none;
    }}
    
    /* Chat List Item Widget */
    QFrame#chatListItem {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
    }}
    
    QFrame#chatListItem[selected="true"] {{
        background-color: {p['primary_fade']};
        border-color: {p['primary']};
    }}
    
    QFrame#chatListItem:hover {{
        border-color: rgba(0, 194, 255, 0.4);
    }}
    
    QFrame#chatListItem QLabel#chatListItemTitle {{
        color: {c['text_primary']};
    }}
    
    QPushButton#chatDeleteButton {{
        background-color: transparent;
        color: #EF4444;
        border: none;
        padding: 0;
        font-size: 12px;
        min-width: 18px;
        min-height: 18px;
    }}
    
    QPushButton#chatDeleteButton:hover {{
        background-color: rgba(239, 68, 68, 0.12);
    }}
    
    /* Table Widget */
    QTableWidget {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        gridline-color: {c['border']};
        alternate-background-color: {c['surface_highlight']};
        outline: none;
    }}
    
    QTableWidget::item {{
        padding: 5px;
        border: none;
        color: {c['text_primary']};
        background-color: {c['surface']};
    }}
    
    QTableWidget::item:selected {{
        background-color: {p['primary_fade']};
        color: {c['text_primary']};
    }}
    
    QHeaderView::section {{
        background-color: {c['surface']};
        padding: 5px;
        border: 1px solid {c['border']};
        font-weight: bold;
        color: {c['text_primary']};
    }}
    
    QTableWidget::item:alternate {{
        background-color: {c['surface_highlight']};
    }}
    
    /* Labels */
    QLabel {{
        background-color: transparent;
    }}
    
    QLabel#headerLabel {{
        font-family: {FONTS['display']};
        font-size: 20px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: {c['text_primary']};
    }}

    QLabel#workspaceHeaderLabel {{
        font-family: {FONTS['display']};
        font-size: 16px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: {c['text_primary']};
    }}
    
    QLabel#sectionLabel {{
        font-family: {FONTS['display']};
        font-size: 11px;
        color: {c['text_muted']};
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 5px 0;
    }}
    
    /* Splitter */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    
    /* Sidebar */
    QFrame#sidebar {{
        background-color: {c['surface']};
        border-right: 1px solid {c['border']};
    }}
    
    /* Chat Panel */
    QFrame#chatPanel {{
        background-color: {c['background']};
        /* For light mode, design implies a light gray background */
    }}

    QFrame#chatHeader {{
        background-color: {c['surface']};
        border-bottom: 1px solid {c['border']};
    }}

    QFrame#workspaceMemoryPanel {{
        background-color: {c['surface']};
        border-left: 1px solid {c['border']};
    }}

    QFrame#memoryItem {{
        background-color: {c['surface_highlight']};
        border-radius: 6px;
        border: 1px solid {c['border']};
    }}

    QFrame#messageRow {{
        background-color: transparent;
    }}

    QLabel#assistantAvatar {{
        border: 1px solid {p['primary']};
        border-radius: 20px;
        background-color: {c['surface_highlight']};
        color: {p['primary']};
        font-weight: 700;
    }}

    QLabel#userAvatar {{
        border: 1px solid {c['border']};
        border-radius: 20px;
        background-color: {c['surface']};
        color: {c['text_primary']};
        font-weight: 700;
    }}
    
    /* Messages */
    QFrame#userMessage {{
        background-color: {p['primary']};
        border-radius: 16px; 
        border-top-right-radius: 4px;
        padding: 12px 16px;
    }}
    
    QFrame#userMessage QLabel {{
        color: #FFFFFF;
    }}
    
    QFrame#assistantMessage {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        border-top-left-radius: 4px;
        padding: 12px 16px;
    }}
    
    QFrame#assistantMessage QLabel {{
        color: {c['text_primary']};
    }}
    
    /* Input Area */
    QFrame#inputArea {{
        background-color: {c['surface']};
        border: 1px solid {c['border']}; 
        border-radius: 12px;
    }}
    
    QFrame#inputArea:focus-within {{
        border-color: {p['primary']};
    }}
    
    /* Large Card Buttons */
    QPushButton#cardButton {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 16px;
        text-align: left;
    }}
    
    QPushButton#cardButton:hover {{
        background-color: {c['surface_highlight']};
        border-color: {p['primary']};
    }}
    
    QPushButton#primaryCardButton {{
        background-color: {p['primary_fade']};
        border: 1px solid rgba(0, 194, 255, 0.2);
        border-radius: 12px;
        padding: 16px;
        text-align: left;
        color: {c['text_primary']};
    }}
    
    QPushButton#primaryCardButton:hover {{
        background-color: {p['primary_fade']};
        border-color: {p['primary']};
    }}
    
    /* QCheckBox & QRadioButton */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {c['text_primary']};
    }}
    
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {c['border']};
        background: {c['surface']};
    }}
    
    QRadioButton::indicator {{
        border-radius: 10px;
    }}
    
    QCheckBox::indicator:unchecked:hover, QRadioButton::indicator:unchecked:hover {{
        border-color: {p['primary']};
        background: {c['surface_highlight']};
    }}
    
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {p['primary']};
        border-color: {p['primary']};
        image: none;
    }}
    
    QRadioButton::indicator:checked {{
        background: qradialgradient(
            cx: 0.5, cy: 0.5, radius: 0.4,
            fx: 0.5, fy: 0.5,
            stop: 0 {c['text_primary']},
            stop: 0.5 {c['text_primary']},
            stop: 0.6 {p['primary']},
            stop: 1.0 {p['primary']}
        );
    }}

    /* QSlider */
    QSlider::groove:horizontal {{
        border: 1px solid {c['border']};
        height: 6px;
        background: rgba(0, 0, 0, 0.05);
        margin: 2px 0;
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background: {p['primary']};
        border: 1px solid {p['primary']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background: {p['primary_hover']};
    }}

    /* Table Widget */
    QTableWidget {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        gridline-color: {c['border']};
        alternate-background-color: {c['surface_highlight']};
        outline: none;
    }}
    
    QTableWidget::item {{
        padding: 5px;
        border: none;
        color: {c['text_primary']};
        background-color: {c['surface']};
    }}
    
    QTableWidget::item:selected {{
        background-color: {p['primary_fade']};
        color: {c['text_primary']};
    }}
    
    QHeaderView::section {{
        background-color: {c['surface']};
        padding: 5px;
        border: 1px solid {c['border']};
        font-weight: bold;
        color: {c['text_primary']};
    }}
    
    QTableWidget::item:alternate {{
        background-color: {c['surface_highlight']};
    }}

    /* Status Bar */
    QStatusBar {{
        background-color: {c['surface']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
    }}

    /* RAG Status Label */
    QLabel#ragStatusLabel {{
        padding: 12px;
        border-radius: 8px;
        background-color: {c['surface_highlight']};
        color: {c['text_muted']};
        font-weight: 500;
    }}

    QLabel#ragStatusLabel[state="ready"] {{
        color: #a6e3a1; /* Success green */
        border: 1px solid rgba(166, 227, 161, 0.3);
    }}

    QLabel#ragStatusLabel[state="error"] {{
        color: #f38ba8; /* Error red */
        border: 1px solid rgba(243, 139, 168, 0.3);
    }}

    QLabel#ragStatusLabel[state="default"] {{
        color: {c['text_muted']};
    }}
    """
