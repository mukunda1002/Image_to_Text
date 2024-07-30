import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "123.json"

import sys
import io
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QTextEdit, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QProgressBar, QMessageBox)
from PyQt5.QtCore import QTimer
from google.cloud import vision
import json
import subprocess
import platform

CONFIG_FILE = 'config.json'

class TextExtractorApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load configuration
        self.load_config()

        # Set up the GUI
        self.init_ui()

        # Set up Google Cloud Vision client
        self.client = vision.ImageAnnotatorClient()

        # List to keep track of files to process
        self.files_to_process = []
        self.current_file_index = 0

        # Set up logging
        self.log_file_path = os.path.join(self.output_dir, "processing_log.txt")
        sys.stdout = self.ConsoleLogger(self.log_file_path)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as config_file:
                config = json.load(config_file)
                self.output_dir = config.get('output_dir', None)
        else:
            self.output_dir = None

    def save_config(self):
        config = {'output_dir': self.output_dir}
        with open(CONFIG_FILE, 'w') as config_file:
            json.dump(config, config_file)

    def select_output_directory(self):
        self.output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not self.output_dir:
            QMessageBox.critical(self, "No Output Directory", "You must select an output directory to save the results.")
            sys.exit()
        self.save_config()

    def init_ui(self):
        # Set up the main window
        self.setWindowTitle('Text Extractor')
        self.setGeometry(100, 100, 900, 750)  # Increased size for better visibility

        # Create widgets
        self.title_label = QLabel("Text Extractor", self)
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; padding: 10px;")

        self.status_label = QLabel("Status: Awaiting file selection...", self)
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")

        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("Extracted text will appear here...")
        self.text_edit.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumHeight(200)  # Ensure the text area is spacious

        self.select_button = QPushButton('Select Files', self)
        self.select_button.setStyleSheet("background-color: #add8e6; color: black; font-weight: bold; padding: 10px;")
        self.select_button.clicked.connect(self.open_file_dialog)

        self.open_folder_button = QPushButton('Open Output Folder', self)
        self.open_folder_button.setStyleSheet("background-color: #f0e68c; color: black; font-weight: bold; padding: 10px;")
        self.open_folder_button.clicked.connect(self.open_output_folder)

        self.change_folder_button = QPushButton('Change Output Folder', self)
        self.change_folder_button.setStyleSheet("background-color: #ffcccb; color: black; font-weight: bold; padding: 10px;")
        self.change_folder_button.clicked.connect(self.select_output_directory)

        self.clear_console_button = QPushButton('Clear Console', self)
        self.clear_console_button.setStyleSheet("background-color: #f08080; color: black; font-weight: bold; padding: 10px;")
        self.clear_console_button.clicked.connect(self.clear_console)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.file_count_label = QLabel("Total Files: 0", self)
        self.file_count_label.setStyleSheet("font-size: 14px; padding: 5px;")

        self.processed_count_label = QLabel("Processed Files: 0", self)
        self.processed_count_label.setStyleSheet("font-size: 14px; padding: 5px;")

        # Layouts
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.open_folder_button)
        button_layout.addWidget(self.change_folder_button)
        button_layout.addWidget(self.clear_console_button)

        info_layout = QHBoxLayout()
        info_layout.addWidget(self.file_count_label)
        info_layout.addWidget(self.processed_count_label)

        console_layout = QVBoxLayout()
        console_layout.addWidget(self.text_edit)
        # console_layout.setAlignment(self.clear_console_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(info_layout)
        main_layout.addLayout(console_layout)
        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        if not self.output_dir:
            self.select_output_directory()

    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_names, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", 
                                                     "Images (*.png *.jpg *.bmp);;PDF Files (*.pdf);;All Files (*)", 
                                                     options=options)
        if file_names:
            self.files_to_process = file_names
            self.current_file_index = 0
            self.progress_bar.setMaximum(len(self.files_to_process))
            self.file_count_label.setText(f"Total Files: {len(self.files_to_process)}")
            self.processed_count_label.setText("Processed Files: 0")
            self.process_next_file()

    def process_next_file(self):
        if self.current_file_index < len(self.files_to_process):
            file_path = self.files_to_process[self.current_file_index]
            self.status_label.setText(f"Processing file: {file_path}")
            self.update_progress(self.current_file_index + 1)
            self.process_file(file_path)
        else:
            self.status_label.setText("All files processed.")
            print("All files have been processed. Log file is saved at:", self.log_file_path)

    def process_file(self, file_path):
        output_file_path = os.path.join(self.output_dir, os.path.basename(file_path) + ".txt")
        
        if file_path.lower().endswith('.pdf'):
            extracted_text = self.extract_text_from_pdf(file_path)
        else:
            extracted_text = self.extract_text_from_image(file_path)

        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(extracted_text)

        self.text_edit.setText(extracted_text)
        self.status_label.setText(f"Finished processing: {file_path}")
        
        # Update processed file count
        self.current_file_index += 1
        self.processed_count_label.setText(f"Processed Files: {self.current_file_index}")
        QTimer.singleShot(1000, self.process_next_file)  # Introduce a small delay

    def extract_text_from_image(self, file_path):
        # Load the image file
        with io.open(file_path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        # Perform text detection
        response = self.client.text_detection(image=image)
        texts = response.text_annotations

        # Return the detected text
        if texts:
            return texts[0].description
        else:
            return "No text detected."

    def extract_text_from_pdf(self, file_path):
        pdf_document = fitz.open(file_path)
        extracted_text = ""

        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            pix = page.get_pixmap()
            img_bytes = io.BytesIO(pix.tobytes())

            image = vision.Image(content=img_bytes.getvalue())
            response = self.client.text_detection(image=image)
            texts = response.text_annotations

            if texts:
                extracted_text += texts[0].description + "\n"
            else:
                extracted_text += f"Page {page_number+1}: No text detected.\n"

            if response.error.message:
                extracted_text += f"Page {page_number+1} Error: {response.error.message}\n"

        return extracted_text

    def update_progress(self, current_value):
        self.progress_bar.setValue(current_value)

    def open_output_folder(self):
        if self.output_dir:
            if platform.system() == "Windows":
                os.startfile(self.output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", self.output_dir])
            else:  # Linux
                subprocess.call(["xdg-open", self.output_dir])
        else:
            QMessageBox.warning(self, "No Output Directory", "Output directory is not set.")

    def clear_console(self):
        self.text_edit.clear()
        print("Console cleared.")

    class ConsoleLogger(io.StringIO):
        def __init__(self, log_file_path):
            super().__init__()
            self.log_file_path = log_file_path

        def write(self, text):
            super().write(text)
            QApplication.instance().processEvents()
            with open(self.log_file_path, 'a', encoding='utf-8') as log_file:
                log_file.write(text)
                log_file.flush()

        def flush(self):
            super().flush()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TextExtractorApp()
    window.show()
    sys.exit(app.exec_())
