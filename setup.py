from setuptools import setup

APP = ['exam-cheater.py']
DATA_FILES = []  # Removed AppIcon.iconset
OPTIONS = {
    'argv_emulation': False,  # Changed to False
    # 'iconfile': 'AppIcon.icns',  # Ensure you have this file or generate it
    'includes': ['rumps', 'pyperclip', 'keyboard', 'requests', 'pynput', 'subprocess', 'json', 'os', 'sys', 'threading', 'logging', 'time', 'tkinter', 'charset_normalizer'], # Added charset_normalizer
    'strip': False,  # Added to disable stripping
    'emulate_shell_environment': True,  # Added this line
    'packages': ['tkinter', 'pynput', 'charset_normalizer']  # Added pynput and charset_normalizer
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app', 'rumps'],
)
