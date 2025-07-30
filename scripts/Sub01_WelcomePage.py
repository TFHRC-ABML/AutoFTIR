# Title: Designing the "Welcome Page" for the AutoFTIR.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/24/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import sys
import json
import pickle
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, \
    QPushButton, QWidget, QLineEdit, QFileDialog, QMessageBox, QComboBox, QPlainTextEdit
from PyQt5.QtGui import QPixmap, QFont, QRegExpValidator
from PyQt5.QtCore import Qt, QRegExp
from time import sleep

class WelcomePage(QMainWindow):
    """
    This class is defined for the main welcome page, where the user can either create a new database or load the 
    already existed one. 

    :param QMainWindow: _description_
    """
    def __init__(self):
        # Initiate the required parameters. 
        super().__init__()
        self.DB_FileName = ''
        self.DB_Folder = ''
        self.initUI()
    # ------------------------------------------------------------------------------------------------------------------
    def initUI(self):
        # Initiate the user interface. 
        self.setWindowTitle("AutoFTIR (version 1.0)")
        self.setFixedSize(710, 600)
        # Main widget and layout
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)
        self.setStyleSheet("background-color: #f0f0f0;")
        # --------------------------------------------------------------------------------------------------------------
        # Define the logo. 
        Label_Logo = QLabel()
        CWD = os.path.dirname(os.path.abspath(__file__))
        pixmap = QPixmap(os.path.join(CWD, "..//assets//Logo.png"))
        Label_Logo.setPixmap(pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        Label_Logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(Label_Logo)
        # --------------------------------------------------------------------------------------------------------------
        # Title
        Label_Title = QLabel(f"Asphalt Binder and Mixture Laboratory (ABML)\n\n\nAutoFTIR")
        Label_Title.setAlignment(Qt.AlignCenter)
        Label_Title.setFont(QFont("Arial", 17, QFont.Bold))
        Label_Title.setStyleSheet("color: #000000;")
        layout.addWidget(Label_Title)
        # Label_Description
        Label_Description = QLabel(f"This tool provde a graphical user intergace (GUI) to:\n" + 
                            f" 1. Analyze the raw data from FTIR test results;\n" + 
                            f" 2. Create a database of FTIR results\n" +
                            f" 3. Export the analysis results as Excel files\n" + 
                            f" 4. Review the raw and processed data for quality control purposes\n")
        Label_Description.setAlignment(Qt.AlignLeft)
        Label_Description.setFont(QFont("Arial", 12))
        Label_Description.setStyleSheet("color: #000000;")
        layout.addWidget(Label_Description)
        # --------------------------------------------------------------------------------------------------------------
        # Add the create database button. 
        Button_Layout = QHBoxLayout()
        Button_CreateDB = QPushButton("Create New Database")
        Button_CreateDB.setFont(QFont("Arial", 13, QFont.Bold))
        Button_CreateDB.setStyleSheet(
        """
        QPushButton {
            background-color: lime; color: black;
            padding: 10px; border-radius: 5px;
            border: 2px solid #000;
        }
        QPushButton:hover {
            background-color: green;
        }
        """)
        Button_CreateDB.clicked.connect(self.CreateDB_Function)
        Button_CreateDB.setFixedSize(300, 90)
        Button_Layout.addWidget(Button_CreateDB)
        # --------------------------------------------------------------------------------------------------------------
        # Add the load database button. 
        Button_LoadDB = QPushButton("Load Database")
        Button_LoadDB.setFont(QFont("Arial", 13, QFont.Bold))
        Button_LoadDB.setStyleSheet(
        """
        QPushButton {
            background-color: deepskyblue; color: black;
            padding: 10px; border-radius: 5px;
            border: 2px solid #000;
        }
        QPushButton:hover {
            background-color: steelblue;
        }
        """)
        Button_LoadDB.clicked.connect(self.LoadDB_Function)
        Button_LoadDB.setFixedSize(300, 90)
        Button_Layout.addWidget(Button_LoadDB)
        layout.addLayout(Button_Layout)
        # --------------------------------------------------------------------------------------------------------------
        # Add the exit button. 
        Button_Exit = QPushButton("Exit")
        Button_Exit.setFont(QFont("Arial", 10))
        Button_Exit.setStyleSheet(
        """
        QPushButton {
            background-color: #d6cece; color: black;
            padding: 5px; border-radius: 5px;
            border: 2px solid #000;
        }
        QPushButton:hover {
            background-color: gray;
        }
        """)
        Button_Exit.setFixedSize(100, 40)
        Button_Exit.clicked.connect(lambda: self.close())
        layout.addWidget(Button_Exit)
    # ------------------------------------------------------------------------------------------------------------------
    # Define the functions.
    def CreateDB_Function(self):
        # This function initiates another window, in which inputs were asked from user to create the new database. 
        self.setEnabled(False)          # Disable the main window while the dialog is open
        self.CreateNewDatabase_Window = NewDatabaseInputs(self)
        self.CreateNewDatabase_Window.show()
    # ------------------------------------------------------------------------------------------------------------------
    def LoadDB_Function(self):
        # This function initiates another window, in which inputs were asked from user to Load the new database. 
        self.setEnabled(False)          # Disable the main window while the dialog is open
        self.LoadDatabase_Window = LoadDatabaseInputs(self)
        self.LoadDatabase_Window.show()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class NewDatabaseInputs(QMainWindow):
    """
    This class represents the dialog for creating a new database.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.regex = QRegExp("^[a-zA-Z0-9_-]*$")        # Define the regular expression limitations for the inputs.
        self.FileName = ''
        self.SaveDirectory = ''
        self.initUI()
    # ------------------------------------------------------------------------------------------------------------------
    def initUI(self):
        self.setWindowTitle("Create New Database")
        self.setFixedSize(800, 350)
        # Main widget and layout
        MainWidget = QWidget()
        self.setCentralWidget(MainWidget)
        layout = QVBoxLayout(MainWidget)
        self.setStyleSheet("background-color: #f0f0f0;")
        # --------------------------------------------------------------------------------------------------------------
        # Database name input
        NameInput_Layout = QVBoxLayout()
        Label_DBName = QLabel("Database Name:")
        Label_DBName.setFont(QFont("Arial", 12))
        self.Input_DBName = QLineEdit()
        self.Input_DBName.setFont(QFont("Arial", 12, QFont.Bold))
        self.Input_DBName.setPlaceholderText("Enter database name...")
        validator = QRegExpValidator(self.regex, self.Input_DBName) 
        self.Input_DBName.setValidator(validator)
        NameInput_Layout.addWidget(Label_DBName)
        NameInput_Layout.addWidget(self.Input_DBName)
        layout.addLayout(NameInput_Layout)
        layout.addSpacing(30)
        # --------------------------------------------------------------------------------------------------------------
        # Save path input
        Path_Layout = QVBoxLayout()
        Label_SavePath = QLabel("Save Path:")
        Label_SavePath.setFont(QFont("Arial", 12, QFont.Bold))
        self.Input_SavePath = QLabel("Use 'Browse' button and select a path to save the database...")
        self.Input_SavePath.setFont(QFont("Arial", 10))
        # Browse button
        Button_Browse = QPushButton("Browse")
        Button_Browse.setFont(QFont("Arial", 10))
        Button_Browse.setStyleSheet(
        """
        QPushButton {
            background-color: lightgray; color: black;
            padding: 5px; border-radius: 5px;
            border: 1px solid #000;
        }
        QPushButton:hover {
            background-color: gray;
        }
        """)
        Button_Browse.setFixedSize(750, 30)
        Button_Browse.clicked.connect(self.Browse_Directory_Function)
        Path_Layout.addWidget(Label_SavePath)
        Path_Layout.addWidget(self.Input_SavePath)
        Path_Layout.addWidget(Button_Browse, alignment=Qt.AlignCenter)
        layout.addLayout(Path_Layout)
        layout.addSpacing(30)
        # --------------------------------------------------------------------------------------------------------------
        # Buttons layout
        Button_Layout = QHBoxLayout()
        Button_Create = QPushButton("Create")
        Button_Create.setFont(QFont("Arial", 13, QFont.Bold))
        Button_Create.setStyleSheet(
        """
        QPushButton {
            background-color: lime; color: black;
            padding: 10px; border-radius: 5px;
            border: 2px solid #000;
        }
        QPushButton:hover {
            background-color: green;
        }
        """)
        Button_Create.clicked.connect(self.Create_Database_Function)
        Button_Create.setFixedSize(200, 50)
        Button_Cancel = QPushButton("Cancel")
        Button_Cancel.setFont(QFont("Arial", 10))
        Button_Cancel.setStyleSheet(
        """
        QPushButton {
            background-color: #d6cece; color: black;
            padding: 5px; border-radius: 5px;
            border: 2px solid #000;
        }
        QPushButton:hover {
            background-color: gray;
        }
        """)
        Button_Cancel.clicked.connect(self.Cancel_Function)
        Button_Cancel.setFixedSize(100, 30)
        # Place the buttons.
        Button_Layout.addWidget(Button_Create)
        Button_Layout.addWidget(Button_Cancel)
        layout.addLayout(Button_Layout)
    # ------------------------------------------------------------------------------------------------------------------
    def Browse_Directory_Function(self):
        # Open a file dialog to select a directory by user.
        save_path = QFileDialog.getExistingDirectory(self, "Please select Directory to create Database")
        # If a directory is selected by the user, update the Input_SavePath.
        if save_path:
            self.Input_SavePath.setText(save_path)
            self.Input_SavePath.setAlignment(Qt.AlignLeft)
    # ------------------------------------------------------------------------------------------------------------------
    def Create_Database_Function(self):
        # First, check if a valid directory has been entered by the user. 
        SaveDirectory = self.Input_SavePath.text()
        if not os.path.isdir(SaveDirectory):
            QMessageBox.warning(self, "Warning", "Please enter a valid directory, using the 'Browse' Button!")
            return
        # Second check if the project name is a valid name. 
        FileName = self.Input_DBName.text()
        if len(FileName) < 3: 
            QMessageBox.warning(self, "Warning", "Database name should contain at least 3 characters!")
            return
        # Printing a success message and save the project locations. 
        QMessageBox.information(self, "Success", f"Database '{FileName + '.db'}' created successfully at " + 
                                                 f"'{SaveDirectory}'.")
        # Save the results. 
        self.SaveDirectory = SaveDirectory
        self.FileName = FileName
        # Add this DB to the recent DBs.
        CWD = os.path.dirname(os.path.abspath(__file__))
        if os.path.isfile(os.path.join(CWD, '..//configs//config.json')):
            config = json.load(open(os.path.join(CWD, '..//configs//config.json'), 'r'))
            if 'Recent_DBs' not in config:
                config['Recent_DBs'] = []
            if os.path.join(SaveDirectory, FileName + '.db') not in config['Recent_DBs']:
                config['Recent_DBs'].append(os.path.join(SaveDirectory, FileName + '.db'))
            json.dump(config, open(os.path.join(CWD, '..//configs//config.json'), 'w'))
        else:
            json.dump({'Recent_DBs': [os.path.join(SaveDirectory, FileName + '.db')]}, 
                      open(os.path.join(CWD, '..//configs//config.json'), 'w'))
        # Close the new window
        self.close()
    # ------------------------------------------------------------------------------------------------------------------
    def Cancel_Function(self):
        # This function is for canceling the operation of creating new database and get back to the main window. 
        self.FileName = ''
        self.SaveDirectory = ''
        self.close()
    # ------------------------------------------------------------------------------------------------------------------
    def closeEvent(self, event):
        # Handle the closure of the dialog and re-enable the main window
        if self.parent:
            # Enable the parent window.
            self.parent.setEnabled(True)
            # Check if the inputs are valid
            if self.FileName and self.SaveDirectory:
                self.parent.DB_FileName = self.FileName
                self.parent.DB_Folder = self.SaveDirectory
                self.parent.close()  # Close the main window if valid inputs are provided
        event.accept()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class LoadDatabaseInputs(QMainWindow):
    """
    This class represents the dialog for loading a new database.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.regex = QRegExp("^[a-zA-Z0-9_-]*$")        # Define the regular expression limitations for the inputs.
        self.FileName = ''
        self.SaveDirectory = ''
        # Check if the config file is available. 
        CWD = os.path.dirname(os.path.abspath(__file__))
        try:
            if os.path.isfile(os.path.join(CWD, '..//configs//config.json')):
                config = json.load(open(os.path.join(CWD, '..//configs//config.json'), 'r'))
                self.RecentDBs = config['Recent_DBs']
            else:
                self.RecentDBs = []
        except:
            self.RecentDBs = []
        self.initUI()
    # ------------------------------------------------------------------------------------------------------------------
    def initUI(self):
        self.setWindowTitle("Loading an Already Existed Database")
        self.setFixedSize(600, 180)
        # Main widget and layout
        MainWidget = QWidget()
        self.setCentralWidget(MainWidget)
        layout = QVBoxLayout(MainWidget)
        self.setStyleSheet("background-color: #f0f0f0;")
        # --------------------------------------------------------------------------------------------------------------
        # First have a dropdown menu of the recent files:
        RecentFiles_Layout = QVBoxLayout()
        if len(self.RecentDBs) > 6:
            RecentDBs = self.RecentDBs[-6:]
        else:
            RecentDBs = self.RecentDBs
        RecentDBs.append('Please select...')
        RecentDBs.reverse()
        Label_RecentFiles = QLabel("You might want to select a recent Database (if available):")
        self.RecentFilesDropDown = QComboBox()
        self.RecentFilesDropDown.addItems(RecentDBs)
        self.RecentFilesDropDown.currentIndexChanged.connect(self.Change_RecentFiles_DropDown_Function)
        self.RecentFilesDropDown.setFixedSize(300, 20)
        RecentFiles_Layout.addWidget(Label_RecentFiles)
        RecentFiles_Layout.addWidget(self.RecentFilesDropDown)
        layout.addLayout(RecentFiles_Layout)
        # --------------------------------------------------------------------------------------------------------------
        # Next, add a button to search for the DB file. 
        Label_Browse = QLabel("or you can click on the 'Browse' button and select your database:")
        self.Button_Find_DB = QPushButton("Browse")
        self.Button_Find_DB.setFont(QFont("Arial", 10))
        self.Button_Find_DB.setStyleSheet(
        """
        QPushButton {
            background-color: lightgray; color: black;
            padding: 5px; border-radius: 5px;
            border: 1px solid #000;
        }
        QPushButton:hover {
            background-color: gray;
        }
        """)
        self.Button_Find_DB.setFixedSize(550, 30)
        self.Button_Find_DB.clicked.connect(self.Browse_File_Function)
        layout.addWidget(Label_Browse)
        layout.addWidget(self.Button_Find_DB, alignment=Qt.AlignHCenter)
        # Next, add a label to show the selected location:
        self.Output = QPlainTextEdit(self)
        self.Output.setReadOnly(True)             # Make it read-only. User shouldn't write!
        self.Output.setStyleSheet("background-color: black; color: white;")
        self.Output.appendPlainText(">>> File name: N/A\n>>> Directory: N/A")
        layout.addWidget(self.Output)
    # ------------------------------------------------------------------------------------------------------------------
    def Change_RecentFiles_DropDown_Function(self):
        CurrentIndx = self.RecentFilesDropDown.currentIndex()
        CurrentText = self.RecentFilesDropDown.currentText()
        if CurrentIndx == 0:
            return              # Has no effect. 
        else:
            Directory = os.path.dirname(CurrentText)
            FileName  = os.path.basename(CurrentText)
            FileNameNoExt  = os.path.splitext(FileName)[0]
            # Check if file is available. 
            if os.path.isfile(os.path.join(Directory, FileName)):
                # File was available and select the file. 
                # Freeze the main window. 
                self.setEnabled(False)
                # Update the output.
                self.Output.setPlainText(f">>> File name: {FileNameNoExt}\n>>> Directory: {Directory}")
                # Printing a success message and save the project locations. 
                QMessageBox.information(self, "Success", f"Database '{FileNameNoExt + '.db'}' Loaded successfully at " + 
                                                        f"'{Directory}'.")
                # Save the results.
                self.FileName = FileNameNoExt
                self.SaveDirectory = Directory
                # Close the new window
                self.close()
            else:
                # File wasn't available. 
                # Print an error to the user. 
                QMessageBox.critical(self, "File not found!", f"Recent database file <'{FileName}' wasn't found at " + 
                                                        f"'{Directory}'. Please user 'Browse' button to select " +
                                                        f"another file")
                # Remove the file from the config file. 
                CWD = os.path.dirname(os.path.abspath(__file__))
                if os.path.isfile(os.path.join(CWD, '..//configs//config.json')):
                    config = json.load(open(os.path.join(CWD, '..//configs//config.json'), 'r'))
                    if 'Recent_DBs' not in config:
                        config['Recent_DBs'] = []
                    if CurrentText in config['Recent_DBs']:
                        config['Recent_DBs'].remove(CurrentText)
                    json.dump(config, open(os.path.join(CWD, '..//configs//config.json'), 'w'))
                else:
                    json.dump({'Recent_DBs': []}, 
                            open(os.path.join(CWD, '..//configs//config.json'), 'w'))
                # Set the current index on "Please select..."
                self.RecentFilesDropDown.setCurrentIndex(0)
    # ------------------------------------------------------------------------------------------------------------------
    def Browse_File_Function(self):
        # First, put the dropdown option on the "Please select..."
        self.RecentFilesDropDown.setCurrentIndex(0)
        # Then, ask user for a file. 
        FilePath, _ = QFileDialog.getOpenFileName(self, 
                                                   "Please select your database", "", 
                                                   "Database files (*.db *.db3);;All Files (*)")
        # If a file is selected by the user, update the Input_SavePath.
        if FilePath:
            # Freeze the main window. 
            self.setEnabled(False)
            # Get the directory and file name. 
            Directory = os.path.dirname(FilePath)
            FileName  = os.path.basename(FilePath)
            FileNameNoExt = os.path.splitext(FileName)[0]
            # Update the output.
            self.Output.setPlainText(f">>> File name: {FileNameNoExt}\n>>> Directory: {Directory}")
            # Printing a success message and save the project locations. 
            QMessageBox.information(self, "Success", f"Database '{FileName}' Loaded successfully at " + 
                                                     f"'{Directory}'.")
            # Add the path to the "config" file. 
            CWD = os.path.dirname(os.path.abspath(__file__))
            if os.path.isfile(os.path.join(CWD, '..//configs//config.json')):
                config = json.load(open(os.path.join(CWD, '..//configs//config.json'), 'r'))
                if 'Recent_DBs' not in config:
                    config['Recent_DBs'] = []
                if FilePath not in config['Recent_DBs']:
                    config['Recent_DBs'].append(FilePath)
                json.dump(config, open(os.path.join(CWD, '..//configs//config.json'), 'w'))
            else:
                json.dump({'Recent_DBs': [FilePath]}, 
                        open(os.path.join(CWD, '..//configs//config.json'), 'w'))
            # Save the results.
            self.FileName = FileNameNoExt
            self.SaveDirectory = Directory
            # Close the new window
            self.close()
    # ------------------------------------------------------------------------------------------------------------------
    def closeEvent(self, event):
        # Handle the closure of the dialog and re-enable the main window
        if self.parent:
            # Enable the parent window.
            self.parent.setEnabled(True)
            # Check if the inputs are valid
            if self.FileName and self.SaveDirectory:
                self.parent.DB_FileName = self.FileName
                self.parent.DB_Folder = self.SaveDirectory
                self.parent.close()  # Close the main window if valid inputs are provided
        event.accept()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


if __name__ == '__main__':
    # NOTE: This part is only used during the development process! These classes will be called from "Main_GUI.py" 
    #   function.
    #
    # Create the app.
    app = QApplication(sys.argv)
    # Create an object from the class. 
    window = WelcomePage()
    # window = NewDatabaseInputs()
    window.show()
    app.exec_()
    # Quit the app. 
    app.quit()
    print('finish')
