import os
from collections import defaultdict
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread, QTimer

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.inputLayout = QtWidgets.QHBoxLayout()
        self.inputLayout.setObjectName("inputLayout")
        self.directoryLabel = QtWidgets.QLabel(self.centralwidget)
        self.directoryLabel.setObjectName("directoryLabel")
        self.inputLayout.addWidget(self.directoryLabel)
        self.directoryLineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.directoryLineEdit.setObjectName("directoryLineEdit")
        self.inputLayout.addWidget(self.directoryLineEdit)
        self.browseButton = QtWidgets.QPushButton(self.centralwidget)
        self.browseButton.setObjectName("browseButton")
        self.inputLayout.addWidget(self.browseButton)
        self.scanButton = QtWidgets.QPushButton(self.centralwidget)
        self.scanButton.setEnabled(False)
        self.scanButton.setObjectName("scanButton")
        self.inputLayout.addWidget(self.scanButton)
        self.verticalLayout.addLayout(self.inputLayout)
        self.treeWidget = QtWidgets.QTreeWidget(self.centralwidget)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.headerItem().setText(0, "Имя файла")
        self.treeWidget.headerItem().setText(1, "Размер")
        self.treeWidget.headerItem().setText(2, "Папка")
        self.treeWidget.headerItem().setText(3, "Путь")
        self.verticalLayout.addWidget(self.treeWidget)
        self.statusLayout = QtWidgets.QVBoxLayout()
        self.statusLayout.setObjectName("statusLayout")
        self.statusbar1 = QtWidgets.QLabel(self.centralwidget)
        self.statusbar1.setObjectName("statusbar1")
        self.statusLayout.addWidget(self.statusbar1)
        self.statusbar2 = QtWidgets.QLabel(self.centralwidget)
        self.statusbar2.setObjectName("statusbar2")
        self.statusLayout.addWidget(self.statusbar2)
        self.progressBar = QtWidgets.QProgressBar(self.centralwidget)
        self.progressBar.setVisible(False)
        self.statusLayout.addWidget(self.progressBar)
        self.verticalLayout.addLayout(self.statusLayout)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Сканер дубликатов файлов"))
        self.directoryLabel.setText(_translate("MainWindow", "Директория:"))
        self.browseButton.setText(_translate("MainWindow", "Обзор"))
        self.scanButton.setText(_translate("MainWindow", "Сканировать"))

class ScanThread(QThread):
    update_progress = QtCore.pyqtSignal(int)
    scan_complete = QtCore.pyqtSignal(defaultdict)

    def __init__(self, directory, parent=None):
        self.directory = directory
        super(ScanThread, self).__init__(parent)

    def run(self):
        file_sizes = defaultdict(list)
        total_files = sum([len(files) for r, d, files in os.walk(self.directory)])
        current_file = 0
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                file_sizes[file_size].append((file_path, os.path.basename(root), file))
                current_file += 1
                progress = (current_file / total_files) * 100
                self.update_progress.emit(progress)

        self.scan_complete.emit(file_sizes)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)

        self.progress_value = 0
        self.scan_thread = None
        # Создаем таймер
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress_ui)
        self.timer.start(100)  # обновляем прогресс бар каждые 100 мс

        self.browseButton.clicked.connect(self.browse)
        self.scanButton.clicked.connect(self.scan)
        self.directoryLineEdit.textChanged.connect(self.enable_scan_button)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+V"), self.directoryLineEdit, self.paste_from_clipboard)

    def format_file_size(self, size):
        """Returns the file size in human readable format."""
        if size < 1024 * 1024:  # size less than 1MB
            return f"{size / 1024:.2f} KB"
        else:  # size 1MB or more
            return f"{size / 1024 / 1024:.2f} MB"

    def browse(self):
        directory = QFileDialog.getExistingDirectory()
        if directory:
            self.directoryLineEdit.setText(directory)

    def enable_scan_button(self):
        if self.directoryLineEdit.text():
            self.scanButton.setEnabled(True)
        else:
            self.scanButton.setEnabled(False)

    def paste_from_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard().text()
        if os.path.isdir(clipboard):
            self.directoryLineEdit.setText(clipboard)

    def scan(self):
        directory = self.directoryLineEdit.text()
        if directory:
            self.treeWidget.clear()
            self.statusbar1.clear()
            self.statusbar2.clear()
            self.progressBar.setMaximum(100)
            self.progressBar.setValue(0)
            self.progressBar.setVisible(True)
            self.scan_thread = ScanThread(directory)
            self.scan_thread.update_progress.connect(self.store_progress_value)
            self.scan_thread.scan_complete.connect(self.on_scan_complete)
            self.scan_thread.start()

    def on_update_progress(self, progress, file_path, file_name):
        print(f'On update progress: {progress}')
        self.progress_value = int(progress)  # Сохраняем значение прогресса, вместо обновления интерфейса здесь
        self.statusbar1.setText(f"Сканирование: {file_name}")
        self.statusbar2.setText(f"Путь: {file_path}")
        QtCore.QCoreApplication.processEvents()  # Обрабатываем события в главном потоке

    def store_progress_value(self, progress):
        self.progress_value = progress

    def update_progress_ui(self):
        # Обновляем интерфейс здесь
        self.progressBar.setValue(self.progress_value)

    def on_scan_complete(self, file_sizes):
        self.progressBar.setValue(100)
        self.progressBar.setVisible(False)
        self.statusbar1.clear()
        self.statusbar2.clear()

        duplicates = 0
        duplicates_size = 0
        for size, files in file_sizes.items():
            if len(files) > 1:
                duplicates += len(files) - 1
                duplicates_size += (len(files) - 1) * size

        total_files = sum(len(files) for files in file_sizes.values())
        duplicates_percentage = (duplicates / total_files) * 100

        self.statusbar1.setText(f"Всего файлов: {total_files}, Количество дубликатов: {duplicates}")
        self.statusbar2.setText(f"Размер дубликатов: {self.format_file_size(duplicates_size)}, Процент дубликатов: {duplicates_percentage:.2f}%")

        for size, files in file_sizes.items():
            if len(files) > 1:
                original = QTreeWidgetItem(self.treeWidget)
                original.setText(0, files[0][2])
                original.setText(1, self.format_file_size(size))
                original.setText(2, files[0][1])
                original.setText(3, files[0][0])
                for duplicate in files[1:]:
                    dup = QTreeWidgetItem(original)
                    dup.setText(0, duplicate[2])
                    dup.setText(1, self.format_file_size(size))
                    dup.setText(2, duplicate[1])
                    dup.setText(3, duplicate[0])
                self.treeWidget.expandItem(original)

        self.treeWidget.collapseAll()  # Свернем все элементы в дереве

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MainWindow()
    MainWindow.show()
    sys.exit(app.exec_())