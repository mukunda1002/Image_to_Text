import PyInstaller.__main__

PyInstaller.__main__.run([
    'ocr_pyqt.py',  # Replace with your script name
    '--onefile',  # Create a single executable file
    '--windowed',  # No console window for GUI application
    '--name=TextExtractorApp',  # Name of the executable
    '--add-data=123.json;.',  # Include the Google credentials file
    '--add-data=./123.json;.',  # Include the config file
])

# Note:
# - Replace 'ocr_pyqt.py' with the name of your main script.
# - Adjust the '--add-data' paths according to your project structure.
# - If you need to include additional directories, follow the same pattern with the semicolon separator.
