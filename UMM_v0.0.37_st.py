import os
from collections import defaultdict
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QTreeWidgetItem
from PyQt5.QtCore import QThread

class Ui_MainWindow(object): # здесь у нас основное окно, надо будет вынести в отдельный файл и собирать в Qt дизайнере
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
        self.treeWidget.headerItem().setText(0, "Name")
        self.treeWidget.headerItem().setText(1, "Size")
        self.treeWidget.headerItem().setText(2, "Folder")
        self.treeWidget.headerItem().setText(3, "Path")
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
        MainWindow.setWindowTitle(_translate("MainWindow", "Universal Media Manger: pre-alfa"))
        self.directoryLabel.setText(_translate("MainWindow", "Directory:"))
        self.browseButton.setText(_translate("MainWindow", "Choose"))
        self.scanButton.setText(_translate("MainWindow", "Scan"))

class ScanThread(QThread): # здесь у нас сканирование, нужно будет вынести в отдельный файл
    update_progress = QtCore.pyqtSignal(int)
    scan_complete = QtCore.pyqtSignal(defaultdict)
    update_current_directory = QtCore.pyqtSignal(str)  # new signal
    update_current_file = QtCore.pyqtSignal(str)  # new signal

    def __init__(self, directory, parent=None):
        self.directory = directory
        super(ScanThread, self).__init__(parent)

    def run(self):
        file_sizes = defaultdict(list)
        total_files = sum([len(files) for r, d, files in os.walk(self.directory)])
        current_file = 0
        for root, dirs, files in os.walk(self.directory):
            current_directory = os.path.basename(root)  # get the base name of the current directory
            self.update_current_directory.emit(current_directory)  # emit current directory
            for file in files:
                self.update_current_file.emit(file)  # emit current file
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                file_sizes[file_size].append((file_path, os.path.basename(root), file))
                current_file += 1
                progress = int((current_file / total_files) * 100)  # calculate progress as an integer
                self.update_progress.emit(progress)  # emit progress

        self.scan_complete.emit(file_sizes)

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)

        self.scan_thread = None

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
            self.scan_thread.update_progress.connect(self.update_progress)
            self.scan_thread.update_current_directory.connect(self.update_current_directory)  # connect the signal
            self.scan_thread.update_current_file.connect(self.update_current_file)  # connect the signal
            self.scan_thread.scan_complete.connect(self.on_scan_complete)
            if self.scan_thread is not None:
                self.scan_thread.start()
    def update_current_directory(self, directory):
        self.statusbar1.setText(f"Folder: {directory}") # Добавлено исправление
    def update_current_file(self, file):
        self.statusbar2.setText(f"File: {file}") # Добавлено исправление
    def update_progress(self, value):
        self.progressBar.setValue(value)
        # Строка удалена чтобы работал код - здесь было: QtCore.QCoreApplication.processEvents()

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

        self.statusbar1.setText(f"Total files: {total_files}, Duplicates: {duplicates}")
        self.statusbar2.setText(f"Duplicates size: {self.format_file_size(duplicates_size)}, Duplicates percent: {duplicates_percentage:.2f}%")

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
