# Title: This script include classes for the main page of the AutoFTIR.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/25/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import sys
import sqlite3
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSpinBox, QDoubleSpinBox, QLabel, \
    QPushButton, QWidget, QGridLayout, QFormLayout, QLineEdit, QFileDialog, QMessageBox, QGroupBox, QProgressBar, \
    QPlainTextEdit, QStackedWidget, QCheckBox, QDialog, QComboBox
from PyQt5.QtGui import QPixmap, QFont, QRegExpValidator, QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt, QRegExp
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scripts.Sub02_CreateNewSQLTable import Get_DB_SummaryData, Append_to_Database, Get_Info_From_Name
from scripts.Sub04_FTIR_Analysis_Functions import Read_FTIR_Data, Baseline_Adjustment_ALS, Normalization_Method_B, \
    Calc_Aliphatic_Area, Calc_Carbonyl_Area, Calc_Sulfoxide_Area, Array_to_Binary, Binary_to_Array, Find_Peaks, \
    FindRepresentativeRows, Normalization_Method_A, Normalization_Method_C, Normalization_Method_D
from scripts.Sub05_ReviewPage import DB_ReviewPage
from scripts.Sub06_FTIR_RevisePage import Revise_FTIR_AnalysisPage
from scripts.Sub07_Deconvolution_Analysis import Run_Deconvolution, gaussian_bell



class SharedData:
    """
    This is just a class to transfer the asphalt ID number between different stacks. 
    """
    def __init__(self):
        self.data = -1
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class Main_Window(QMainWindow):
    """
    This class generates the GUI for the main window of the AutoFTIR. This window has two stacks: (i) main 
    stack is for adding data to the database, and (ii) second stack is for reviewing the FTIR analysis results, and 
    making changes if neccessary. 
    """
    def __init__(self, conn, cursor, DB_Name, DB_Folder):
        super().__init__()
        # Creating the main window. 
        self.setWindowTitle(f"AutoFTIR (version 1.0) | Database name: {DB_Name}")
        # self.setFixedSize(1250, 900)
        self.resize(1250, 900)
        self.setMinimumSize(900, 700)
        self.setStyleSheet("background-color: #f0f0f0;")
        # Create shared data object
        self.shared_data = SharedData()
        # Create QStackedWidget.
        self.stack = QStackedWidget()
        # Create pages
        self.main_page = MainPage(conn, cursor, DB_Name, DB_Folder, self.stack)
        self.db_review_page = DB_ReviewPage(conn, cursor, DB_Name, DB_Folder, self.stack, self.shared_data)
        self.FTIR_revise_page = Revise_FTIR_AnalysisPage(conn, cursor, DB_Name, DB_Folder, self.stack, self.shared_data)
        # Add pages to the stack
        self.stack.addWidget(self.main_page)            # This page has stack index 0
        self.stack.addWidget(self.db_review_page)       # This page has stack index 1
        self.stack.addWidget(self.FTIR_revise_page)     # This page has stack index 2. 
        # Set the stack as the central widget
        self.setCentralWidget(self.stack)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class MainPage(QMainWindow):
    """
    This class generates the GUI for the main page of the AutoFTIR, where the user can load a database and 
    actually add more data, modify the current data, etc.
    """
    def __init__(self, conn, cursor, DB_Name, DB_Folder, stack):
        # Initiate the required parameters. 
        super().__init__()
        self.conn = conn            # connection to the SQL database.
        self.cursor = cursor        # cursor for running the SQL commands. 
        self.DB_Name = DB_Name
        self.DB_Folder = DB_Folder
        self.CurrentFileList = []   # A list of the input files that need to be analyzed!
        self.CurrentFileIndex = 0   # Index of the file to be analyzed. 
        self.stack = stack
        self.ShowFileExistedError = True
        self.Deconv = {}
        self.CurBinderInfo = {'Bnumber': -1, 'RepNum': -1, 'LabAging': ''}  # To share binder info between functions.
        self.initUI()
    # ------------------------------------------------------------------------------------------------------------------
    def initUI(self):
        # # Initiate the user interface. 
        # self.setWindowTitle(f"AutoFTIR (version 1.0) | Database name: {self.DB_Name}")
        # self.setFixedSize(1500, 900)
        # Main widget and layout
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)                   # Make a horizontal layout.
        self.setCentralWidget(main_widget)
        # self.setStyleSheet("background-color: #f0f0f0;")
        # Generate the left and right layouts, where left one include summay info and plots, and right one include the 
        #   buttons, adjustments, and controls. 
        LeftLayout  = QVBoxLayout()
        RightLayout = QVBoxLayout()
        # --------------------------------------------------------------------------------------------------------------
        # Section 1: summary information.
        SummaryData = Get_DB_SummaryData(self.cursor)
        Section01 = QGroupBox("Summary Information")
        Section01_Layout = QHBoxLayout()
        FormLayout_Left  = QFormLayout()            # Define a form layout for the left side.
        FormLayout_Right = QFormLayout()            # Define a form layout for the right side. 
        # Create the left side labels in Section 01.
        Label01 = QLabel("Number of data:")
        self.Label_NumData = QLabel(f'{SummaryData["NumRows"]}')
        Label02 = QLabel("Number of valid data:")
        self.Label_NumValidData = QLabel(f'{SummaryData["NumValidRows"]}')
        Label03 = QLabel("Avg Number Replicates:")
        self.Label_AvgNumReplicates = QLabel(f'{SummaryData["AvgNumRep"]:.1f}')
        # Create the right side labels in Section 01.
        Label04 = QLabel("Number of unique B-numbers:")
        self.Label_NumUniqueBnum = QLabel(f'{SummaryData["NumUniqueBnumber"]}')
        Label05 = QLabel("Number of unique Lab agings:")
        self.Label_NumUniqueLabAge = QLabel(f'{SummaryData["NumUniqueLabAging"]}')
        Label06 = QLabel("Number of Unique Bnum/LabAge:")
        self.Label_NumUniqueBnumLabAge = QLabel(f'{SummaryData["NumUniqueBnumLabAge"]}')
        # Syncing button.
        self.Button_Sync = QPushButton("Refresh summay")
        self.Button_Sync.setFont(QFont("Arial", 8))
        self.Button_Sync.clicked.connect(self.Sync_Summary_Info)
        self.Button_Sync.setFixedSize(100, 30)
        self.Button_Sync.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        # Place the labels in the GUI.
        FormLayout_Left.addRow(Label01,  self.Label_NumData)
        FormLayout_Left.addRow(Label02,  self.Label_NumValidData)
        FormLayout_Left.addRow(Label03,  self.Label_AvgNumReplicates)
        FormLayout_Right.addRow(Label04, self.Label_NumUniqueBnum)
        FormLayout_Right.addRow(Label05, self.Label_NumUniqueLabAge)
        FormLayout_Right.addRow(Label06, self.Label_NumUniqueBnumLabAge)
        Section01_Layout.addLayout(FormLayout_Left)
        Section01_Layout.addLayout(FormLayout_Right)
        Section01_Layout.addWidget(self.Button_Sync, alignment=Qt.AlignHCenter | Qt.AlignTop)
        Section01.setLayout(Section01_Layout)
        Left_Top_Layout = QHBoxLayout()
        Left_Top_Layout.addWidget(Section01, 50)
        # --------------------------------------------------------------------------------------------------------------
        # Section 1-2: Preprocessing options. 
        Section12 = QGroupBox("Pre-Processing Options")
        Section12_Layout = QHBoxLayout()
        FormLayout12_Left  = QFormLayout()            # Define a form layout for the left side.
        FormLayout12_Right = QFormLayout()            # Define a form layout for the right side. 
        # Create the left side labels in Section 01.
        Label12_01 = QLabel("ALS Lambda:".ljust(13))
        self.LineEdit_ALSLambda = QLineEdit()
        self.LineEdit_ALSLambda.setPlaceholderText("Enter Lambda parameter ...")
        self.LineEdit_ALSLambda.setReadOnly(False)
        LambdaValidator = QDoubleValidator(10, 10000000000, 3)
        LambdaValidator.setNotation(QDoubleValidator.ScientificNotation)
        self.LineEdit_ALSLambda.setValidator(LambdaValidator)
        self.LineEdit_ALSLambda.setText("1e6")
        Label12_02 = QLabel("ALS Ratio:".ljust(13))
        self.LineEdit_ALSRatio = QLineEdit()
        self.LineEdit_ALSRatio.setPlaceholderText("Enter ratio parameter ...")
        self.LineEdit_ALSRatio.setReadOnly(False)
        RatioValidator = QDoubleValidator(0.0001, 0.5, 6)
        RatioValidator.setNotation(QDoubleValidator.ScientificNotation)
        self.LineEdit_ALSRatio.setValidator(RatioValidator)
        self.LineEdit_ALSRatio.setText("1e-1")
        Label12_03 = QLabel("ALS Num Iterations:".ljust(22))
        self.LineEdit_ALSNumIter = QLineEdit()
        self.LineEdit_ALSNumIter.setPlaceholderText("Enter number of iterations ...")
        self.LineEdit_ALSNumIter.setReadOnly(False)
        NumIterValidator = QIntValidator(100, 1000)
        self.LineEdit_ALSNumIter.setValidator(NumIterValidator)
        Label12_04 = QLabel("Normalization Method:".ljust(22))
        self.DropDown_NormalizationMethod = QComboBox()
        self.DropDown_NormalizationMethod.addItems(["Method A (400 to 4000 cm-1)", 
                                                    "Method B (400 to 1800 cm-1)", 
                                                    "Method C (400 to 4000 cm-1)",
                                                    "Method D (400 to 1800 cm-1)"])
        self.DropDown_NormalizationMethod.setCurrentIndex(1)
        # Replotting button.
        self.Button_UpdatePreprocess = QPushButton("Update\nRe-Plot")
        self.Button_UpdatePreprocess.setFont(QFont("Arial", 8))
        self.Button_UpdatePreprocess.clicked.connect(self.Function_Button_UpdatePreprocessing)
        self.Button_UpdatePreprocess.setFixedSize(70, 50)
        self.Button_UpdatePreprocess.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        # Make everything disable. 
        self.LineEdit_ALSLambda.setEnabled(False)
        self.LineEdit_ALSRatio.setEnabled(False)
        self.LineEdit_ALSNumIter.setEnabled(False)
        self.DropDown_NormalizationMethod.setEnabled(False)
        self.Button_UpdatePreprocess.setEnabled(False)
        # Place the labels in the GUI.
        FormLayout12_Left.addRow(Label12_01, self.LineEdit_ALSLambda)
        FormLayout12_Left.addRow(Label12_02, self.LineEdit_ALSRatio)
        FormLayout12_Right.addRow(Label12_03, self.LineEdit_ALSNumIter)
        FormLayout12_Right.addRow(Label12_04, self.DropDown_NormalizationMethod)
        Section12_Layout.addLayout(FormLayout12_Left)
        Section12_Layout.addLayout(FormLayout12_Right)
        Section12_Layout.addWidget(self.Button_UpdatePreprocess, alignment=Qt.AlignHCenter | Qt.AlignTop)
        Section12.setLayout(Section12_Layout)
        Left_Top_Layout.addWidget(Section12, 60)
        LeftLayout.addLayout(Left_Top_Layout, 10)
        # --------------------------------------------------------------------------------------------------------------
        # Section 2: Matplotlib plots. 
        Section02 = QGroupBox("Plotting Section")
        # Labels and progress bar. 
        Section02_Layout = QVBoxLayout()
        FormLayout_Sec2_top   = QFormLayout()
        FormLayout_Sec2_down  = QFormLayout()
        Label_Sec2_1 = QLabel("File name for current analysis:")
        self.Label_CurrentFileName = QLabel('Waiting for file...')
        FormLayout_Sec2_top.addRow(Label_Sec2_1, self.Label_CurrentFileName)
        self.Label_NumFilesProgress = QLabel(f"Number of selected files: N/A")
        self.NumFilesProgress_bar = QProgressBar(self)
        self.NumFilesProgress_bar.setMinimum(0)
        self.NumFilesProgress_bar.setMaximum(100)
        self.NumFilesProgress_bar.setValue(0)
        FormLayout_Sec2_down.addRow(self.Label_NumFilesProgress, self.NumFilesProgress_bar)
        Section02_Layout.addLayout(FormLayout_Sec2_top)
        Section02_Layout.addLayout(FormLayout_Sec2_down)
        # Prepare the plots. 
        self.fig = Figure(figsize=(10, 7))
        self.fig.set_facecolor("#f0f0f0")
        self.canvas = FigureCanvas(self.fig)
        self.axes = [self.fig.add_subplot(2, 2, i + 1) for i in range(4)]
        # Add the labels to the axes. 
        Titles = ['Wide range data', 'Carbonyl area', 'Sulfoxide area', 'Aliphatic area']
        for i in range(4):
            if i >= 2:
                self.axes[i].set_xlabel('Wavenumber (1/cm)', fontsize=9, fontweight='bold', color='k')
            if i in [0, 2]:
                self.axes[i].set_ylabel('Normalized Absorption', fontsize=9, fontweight='bold', color='k')
            self.axes[i].set_title(Titles[i], fontsize=11, fontweight='bold', color='k')
            self.axes[i].grid(which='both', color='gray', alpha=0.1)
        self.fig.tight_layout()
        self.canvas.draw()
        Section02_Layout.addWidget(self.canvas)
        Section02.setLayout(Section02_Layout)
        LeftLayout.addWidget(Section02, 90)
        # --------------------------------------------------------------------------------------------------------------
        # Section 3: Buttons.
        Section03 = QGroupBox("DB Manager")
        Section03_Layout = QVBoxLayout()
        # Button for adding more data to database. 
        self.Button_AddData = QPushButton("Add more data to DB")
        self.Button_AddData.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_AddData.clicked.connect(self.Add_More_Data_Function)
        self.Button_AddData.setFixedSize(230, 45)
        self.Button_AddData.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        Section03_Layout.addWidget(self.Button_AddData, alignment=Qt.AlignHCenter | Qt.AlignTop)
        # Button for review the database. 
        self.Button_ReviewDB = QPushButton("Review and Edit DB")
        self.Button_ReviewDB.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_ReviewDB.clicked.connect(self.Review_Edit_DB_Function)
        self.Button_ReviewDB.setFixedSize(230, 45)
        self.Button_ReviewDB.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        Section03_Layout.addWidget(self.Button_ReviewDB, alignment=Qt.AlignHCenter | Qt.AlignTop)
        # Button for exporting the database to excel.
        self.Button_ExportDB = QPushButton("Analyze DB and Export to Excel")
        self.Button_ExportDB.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_ExportDB.clicked.connect(self.Export_DB_Function)
        self.Button_ExportDB.setFixedSize(230, 45)
        self.Button_ExportDB.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        Section03_Layout.addWidget(self.Button_ExportDB, alignment=Qt.AlignHCenter | Qt.AlignTop)
        Section03.setLayout(Section03_Layout)
        RightLayout.addWidget(Section03, 20)
        # --------------------------------------------------------------------------------------------------------------
        # Section 4: Adjustment for the graphs. 
        Section04 = QGroupBox("Analysis Adjustment Tool")
        Section04_Layout = QVBoxLayout()
        FormLayout_Spinbox = QFormLayout()
        self.spinboxes = []                 # A list to store the spinboxes.
        LabelTitles = ['Carbonyl range, Min (1/cm):',  'Carbonyl range, Max (1/cm):',
                       'Sulfoxide range, Min (1/cm):', 'Sulfoxide range, Max (1/cm):',
                       'Aliphatic range, Min (1/cm):', 'Aliphatic range, Max (1/cm):']
        SpinBoxRanges = [[1600, 1800],  [1600, 1800], [940,  1100], [940, 1100], [1350, 1600], [1350, 1600]]
        SpinBoxValues = [1670, 1690, 1020, 1040, 1370, 1420]
        Step = 4.0
        for i in range(6):
            label = QLabel(LabelTitles[i])
            spinbox = QDoubleSpinBox()
            spinbox.setRange(SpinBoxRanges[i][0], SpinBoxRanges[i][1])
            spinbox.setSingleStep(Step)
            spinbox.setDecimals(1)
            spinbox.setValue(SpinBoxValues[i])
            spinbox.setEnabled(False)
            if i == 0:
                spinbox.valueChanged.connect(self.update_Carbonyl_min)
            elif i == 1:
                spinbox.valueChanged.connect(self.update_Carbonyl_max)
            elif i == 2:
                spinbox.valueChanged.connect(self.update_Sulfoxide_min)
            elif i == 3:
                spinbox.valueChanged.connect(self.update_Sulfoxide_max)
            elif i == 4:
                spinbox.valueChanged.connect(self.update_Aliphatic_max)
            elif i == 5:
                spinbox.valueChanged.connect(self.update_Aliphatic_max)
            self.spinboxes.append(spinbox)
            FormLayout_Spinbox.addRow(label, spinbox)
        Section04_Layout.addLayout(FormLayout_Spinbox)
        # Add button to save the progress. 
        self.Button_SaveProgress = QPushButton("Save the Current Progress & Exit")
        self.Button_SaveProgress.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_SaveProgress.clicked.connect(self.SaveExit_Button_Function)        # Connect to a custom function
        self.Button_SaveProgress.setEnabled(False)
        Section04_Layout.addWidget(self.Button_SaveProgress)
        # Outlier specification button.
        self.Button_Outlier = QPushButton("Outlier, exclude this data!")
        self.Button_Outlier.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_Outlier.clicked.connect(self.Outlier_Button_Function)  # Connect to a custom function
        self.Button_Outlier.setEnabled(False)
        Section04_Layout.addWidget(self.Button_Outlier)
        # OK button.
        self.Button_OK = QPushButton("OK")
        self.Button_OK.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_OK.clicked.connect(self.OK_Button_Function)
        self.Button_OK.setEnabled(False)
        Section04_Layout.addWidget(self.Button_OK)
        Section04.setLayout(Section04_Layout)
        RightLayout.addWidget(Section04, 30)
        # --------------------------------------------------------------------------------------------------------------
        # Section 06: Results of the deconvolution. 
        Section06 = QGroupBox("Deconvolution analysis results:")
        Section06_Layout = QVBoxLayout()
        self.Decon_Label_CArea = QLabel('Carbonyl Area: ')
        self.Decon_Label_SArea = QLabel('Sulfoxide Area: ')
        self.Decon_Label_AArea = QLabel('Aliphatic Area: ')
        self.Decon_Label_Index = QLabel('ICO: N/A, ISO: N/A')
        Section06_Layout.addWidget(self.Decon_Label_CArea)
        Section06_Layout.addWidget(self.Decon_Label_SArea)
        Section06_Layout.addWidget(self.Decon_Label_AArea)
        Section06_Layout.addWidget(self.Decon_Label_Index)
        Section06.setLayout(Section06_Layout)
        RightLayout.addWidget(Section06, 10)
        # --------------------------------------------------------------------------------------------------------------
        # Section 05: Output section. 
        Section05 = QGroupBox("Output section (Terminal-like)")
        Section05_Layout = QVBoxLayout()
        self.Terminal = QPlainTextEdit(self)
        self.Terminal.setReadOnly(True)             # Make it read-only. User shouldn't write!
        self.Terminal.setStyleSheet("background-color: black; color: white;")
        self.Terminal.appendPlainText(">>> FTIR_Aalysis_Tool()\n")
        Section05_Layout.addWidget(self.Terminal)
        Section05.setLayout(Section05_Layout)
        RightLayout.addWidget(Section05, 40)
        # --------------------------------------------------------------------------------------------------------------
        # At the very end, add the left and right layouts to the main layout.
        layout.addLayout(LeftLayout, 80)
        layout.addLayout(RightLayout, 20)
    # ------------------------------------------------------------------------------------------------------------------
    def Sync_Summary_Info(self):
        # Get the latest summary information. 
        SummaryData = Get_DB_SummaryData(self.cursor)
        # Update the values. 
        self.Label_NumData.setText(f'{SummaryData["NumRows"]}')
        self.Label_NumValidData.setText(f'{SummaryData["NumValidRows"]}')
        self.Label_AvgNumReplicates.setText(f'{SummaryData["AvgNumRep"]:.1f}')
        self.Label_NumUniqueBnum.setText(f'{SummaryData["NumUniqueBnumber"]}')
        self.Label_NumUniqueLabAge.setText(f'{SummaryData["NumUniqueLabAging"]}')
        self.Label_NumUniqueBnumLabAge.setText(f'{SummaryData["NumUniqueBnumLabAge"]}')
        # Return Nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Add_More_Data_Function(self):
        # First ask user to select some FTIR test results.
        FileList, _ = QFileDialog.getOpenFileNames(self, caption='Please select new FTIR test result files:', 
                                                   directory='', filter="DPT Files (*.dpt);;All Files (*)")
        self.CurrentFileList = FileList
        self.CurrentFileIndex= -1
        # Check on files that are selected. 
        if len(FileList) == 0:          # Do nothing in case files are NOT selected. 
            return
        # Otherwise, print the number of selected files and update the label in progress bar. 
        self.Terminal.appendPlainText(f">>> {len(FileList)} New files selected for analysis")
        self.Label_NumFilesProgress.setText(f"Number of selected/Remained files: {len(FileList)}, {len(FileList)}")
        # disable the DB manager buttons. 
        self.Button_AddData.setEnabled(False)
        self.Button_ReviewDB.setEnabled(False)
        self.Button_ExportDB.setEnabled(False)
        # Call the function to renew the plots.
        while True:
            self.CurrentFileIndex += 1
            Check = self.Check_EndofLoop()
            if Check:
                return
            # ----------------------------------------------------------------------------------------------------------
            # Update the plots and everything. 
            try:
                self.Renew_MainPlot_4Next_File()
                break
            except:
                # print(f'Skipping {self.CurrentFileList[self.CurrentFileIndex]}')
                continue
    # ------------------------------------------------------------------------------------------------------------------
    def Review_Edit_DB_Function(self):
        self.stack.setCurrentIndex(1)  # Switch to the second page
    # ------------------------------------------------------------------------------------------------------------------
    def Export_DB_Function(self):
        """
        This function create (or re-create) a new table from the "FTIR" to with the analysis results of the 
        current FTIR database.
        """
        self.Terminal.appendPlainText(f'>>> Start analysis of the results in the DB:')
        # Asking user where to save the result file. 
        OutputDir = QFileDialog.getExistingDirectory(self, "Please select a directory at which you want to save the " + 
                                                           "resulting Excel file:", self.DB_Folder)
        OutputPath = os.path.join(OutputDir, self.DB_Name + '.xlsx')
        # Now, get the latest values of the required parameters from the database. 
        Column2Fetch = [
            'id', 'Bnumber', 'Lab_Aging', 'RepNumber', 
            'ICO_Baseline', 'ICO_Tangential', 'ISO_Baseline', 'ISO_Tangential', 
            'Aliphatic_Area_Baseline', 'Aliphatic_Area_Tangential', 
            'Carbonyl_Peak_Wavenumber', 'Sulfoxide_Peak_Wavenumber', 
            'Carbonyl_Peak_Absorption', 'Sulfoxide_Peak_Absorption',
            'IsOutlier', 'Deconv_ICO', 'Deconv_ISO']
        self.cursor.execute(f"SELECT {', '.join(Column2Fetch)} FROM FTIR")
        data = self.cursor.fetchall()
        data = pd.DataFrame(data, columns=Column2Fetch)
        data = data[data.IsOutlier == 0]            # Exclude the outlier data. 
        # Prepare a table for the results. 
        Res ={
            'B_Number': [],
            'Lab_Aging_Condition': [], 'Num_Data': [], 'ICO_Deconv_mean': [], 'ICO_Deconv_std': [], 
            'ICO_Deconv_COV': [], 'ICO_Deconv_min': [], 'ICO_Deconv_max': [], 'ICO_Deconv_Data': [],
            'ICO_Baseline_mean': [], 'ICO_Baseline_std': [], 
            'ICO_Baseline_COV': [], 'ICO_Baseline_min': [], 'ICO_Baseline_max': [], 'ICO_Baseline_Data': [], 
            'ICO_Tangential_mean': [], 'ICO_Tangential_std': [], 'ICO_Tangential_COV': [], 'ICO_Tangential_min': [], 
            'ICO_Tangential_max': [], 'ICO_Tangential_Data': [], 'ISO_Baseline_mean': [], 'ISO_Baseline_std': [], 
            'ISO_Baseline_COV': [], 'ISO_Baseline_min': [], 'ISO_Baseline_max': [], 'ISO_Baseline_Data': [], 
            'ISO_Tangential_mean': [], 'ISO_Tangential_std': [], 'ISO_Tangential_COV': [], 'ISO_Tangential_min': [], 
            'ISO_Tangential_max': [], 'ISO_Tangential_Data': [], 'ISO_Deconv_mean': [], 'ISO_Deconv_std': [], 
            'ISO_Deconv_COV': [], 'ISO_Deconv_min': [], 'ISO_Deconv_max': [], 'ISO_Deconv_Data': [],
            'Aliphatic_Area_Baseline_mean': [], 'Aliphatic_Area_Baseline_std': [], 'Aliphatic_Area_Baseline_COV': [], 
            'Aliphatic_Area_Baseline_min': [], 'Aliphatic_Area_Baseline_max': [], 'Aliphatic_Area_Baseline_Data': [], 
            'Aliphatic_Area_Tangential_mean': [], 'Aliphatic_Area_Tangential_std': [], 'Aliphatic_Area_Tangential_COV': [], 
            'Aliphatic_Area_Tangential_min': [], 'Aliphatic_Area_Tangential_max': [], 'Aliphatic_Area_Tangential_Data': [], 
            'Carbonyl_Peak_Wavenumber_mean': [], 'Carbonyl_Peak_Wavenumber_std': [], 'Carbonyl_Peak_Wavenumber_COV': [], 
            'Carbonyl_Peak_Wavenumber_min': [], 'Carbonyl_Peak_Wavenumber_max': [], 'Carbonyl_Peak_Wavenumber_Data': [], 
            'Sulfoxide_Peak_Wavenumber_mean': [], 'Sulfoxide_Peak_Wavenumber_std': [], 'Sulfoxide_Peak_Wavenumber_COV': [], 
            'Sulfoxide_Peak_Wavenumber_min': [], 'Sulfoxide_Peak_Wavenumber_max': [], 'Sulfoxide_Peak_Wavenumber_Data': [], 
            'Carbonyl_Peak_Absorption_mean': [], 'Carbonyl_Peak_Absorption_std': [], 'Carbonyl_Peak_Absorption_COV': [], 
            'Carbonyl_Peak_Absorption_min': [], 'Carbonyl_Peak_Absorption_max': [], 'Carbonyl_Peak_Absorption_Data': [], 
            'Sulfoxide_Peak_Absorption_mean': [], 'Sulfoxide_Peak_Absorption_std': [], 'Sulfoxide_Peak_Absorption_COV': [], 
            'Sulfoxide_Peak_Absorption_min': [], 'Sulfoxide_Peak_Absorption_max': [], 'Sulfoxide_Peak_Absorption_Data': []}
        # Define a function to add data to the results. 
        def AddResults(Res, data, ResLabel):
            Res[f'{ResLabel}_mean'].append(data.mean())
            Res[f'{ResLabel}_std'].append(data.std())
            Res[f'{ResLabel}_COV'].append(data.std() / data.mean())
            Res[f'{ResLabel}_min'].append(data.min())
            Res[f'{ResLabel}_max'].append(data.max())
            Res[f'{ResLabel}_Data'].append('|'.join(list(data.astype(str))))
            # Return the updated "Res"
            return Res
        # Start iterating over the unique "B-numbers" and analyze the results. 
        Bnumber = data['Bnumber'].unique()             # Unique B-numbers. 
        for bnum in Bnumber:                            # Iterate over all B-numbers. 
            # Get the unique aging condition. 
            AgeData = data[data['Bnumber'] == bnum]
            Aging = AgeData['Lab_Aging'].unique()
            # Iterate over the aging condition. 
            for aging in Aging:
                # Get the unique sample repetitions. 
                RepData = AgeData[AgeData['Lab_Aging'] == aging]
                if len(RepData) < 3:
                    self.Terminal.appendPlainText(f'>>> Warning! Not enough available repetitions for ' + 
                                                  f'B-number={bnum} at aging level of {aging}: ' + 
                                                  f'Need {3 - len(RepData)} more.')
                elif len(RepData) > 3:
                    RepData = FindRepresentativeRows(RepData)
                # Add the data to the "Res" dictionary. 
                Res['B_Number'].append(bnum)
                Res['Lab_Aging_Condition'].append(aging)
                Res['Num_Data'].append(len(RepData))
                Res = AddResults(Res, RepData['ICO_Baseline'].to_numpy(),   'ICO_Baseline')
                Res = AddResults(Res, RepData['ICO_Tangential'].to_numpy(), 'ICO_Tangential')
                Res = AddResults(Res, RepData['Deconv_ICO'].to_numpy(),     'ICO_Deconv')
                Res = AddResults(Res, RepData['ISO_Baseline'].to_numpy(),   'ISO_Baseline')
                Res = AddResults(Res, RepData['ISO_Tangential'].to_numpy(), 'ISO_Tangential')
                Res = AddResults(Res, RepData['Deconv_ISO'].to_numpy(),     'ISO_Deconv')
                Res = AddResults(Res, RepData['Aliphatic_Area_Baseline'].to_numpy(), 'Aliphatic_Area_Baseline')
                Res = AddResults(Res, RepData['Aliphatic_Area_Tangential'].to_numpy(), 'Aliphatic_Area_Tangential')
                Res = AddResults(Res, RepData['Carbonyl_Peak_Wavenumber'].to_numpy(), 'Carbonyl_Peak_Wavenumber')
                Res = AddResults(Res, RepData['Sulfoxide_Peak_Wavenumber'].to_numpy(), 'Sulfoxide_Peak_Wavenumber')
                Res = AddResults(Res, RepData['Carbonyl_Peak_Absorption'].to_numpy(), 'Carbonyl_Peak_Absorption')
                Res = AddResults(Res, RepData['Sulfoxide_Peak_Absorption'].to_numpy(), 'Sulfoxide_Peak_Absorption')
        # Convert "Res" dictionary to DataFrame. 
        Res = pd.DataFrame(Res)
        Res = Res.sort_values(by=["B_Number"])
        # Save the results as an excel file. 
        Res.to_excel(OutputPath, index=False)
        # Save the results to the Database. 
        Res.to_sql('FTIR_Analysis_DB', self.conn, if_exists="replace", index=False)
    # ------------------------------------------------------------------------------------------------------------------
    def update_Carbonyl_min(self, value):
        # Clear the highlighted area. 
        for coll in self.axes[1].collections[:]:
            coll.remove()
        # Update the minimum value for the max. 
        idx = np.argmin(np.abs(self.XC - value))
        if self.XCmaxIndx > idx + 1:
            self.XCminIndx = idx
        else:
            idx = self.XCminIndx
        self.spinboxes[0].setValue(self.XC[idx])
        self.spinboxes[1].setRange(self.XC[self.XCminIndx + 1], 1800)
        # Add the updated highlight region.
        self.CIndex2 = np.arange(self.XCminIndx, self.XCmaxIndx + 1)
        self.axes[1].fill_between(self.XC[self.CIndex2], self.YC[self.CIndex2], 0, color='r', alpha=0.1, 
                                  label='Carbonyl Area')
        # Redraw the canvas
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def update_Carbonyl_max(self, value):
        # Clear the highlighted area. 
        for coll in self.axes[1].collections[:]:
            coll.remove()
        # Update the minimum value for the max. 
        idx = np.argmin(np.abs(self.XC - value))
        if self.XCminIndx < idx - 1:
            self.XCmaxIndx = idx
        else:
            idx = self.XCmaxIndx
        self.spinboxes[1].setValue(self.XC[idx])
        self.spinboxes[0].setRange(1600, self.XC[self.XCmaxIndx - 1])
        # Add the updated highlight region.
        self.CIndex2 = np.arange(self.XCminIndx, self.XCmaxIndx + 1)
        self.axes[1].fill_between(self.XC[self.CIndex2], self.YC[self.CIndex2], 0, color='r', alpha=0.1, 
                                  label='Carbonyl Area')
        # Redraw the canvas
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def update_Sulfoxide_min(self, value):
        # Clear the highlighted area. 
        for coll in self.axes[2].collections[:]:
            coll.remove()
        # Update the minimum value for the max. 
        idx = np.argmin(np.abs(self.XS - value))
        if self.XSmaxIndx > idx + 1:
            self.XSminIndx = idx
        else:
            idx = self.XSminIndx
        self.spinboxes[2].setValue(self.XS[idx])
        self.spinboxes[3].setRange(self.XS[self.XSminIndx + 1], 1100)
        # Add the updated highlight region.
        self.CIndex2 = np.arange(self.XSminIndx, self.XSmaxIndx + 1)
        self.axes[2].fill_between(self.XS[self.CIndex2], self.YS[self.CIndex2], 0, color='y', alpha=0.1, 
                                  label='Sulfoxide Area')
        # Redraw the canvas
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def update_Sulfoxide_max(self, value):
        # Clear the highlighted area. 
        for coll in self.axes[2].collections[:]:
            coll.remove()
        # Update the minimum value for the max. 
        idx = np.argmin(np.abs(self.XS - value))
        if self.XSminIndx < idx - 1:
            self.XSmaxIndx = idx
        else:
            idx = self.XSmaxIndx
        self.spinboxes[3].setValue(self.XS[idx])
        self.spinboxes[2].setRange(940, self.XS[self.XSmaxIndx - 1])
        # Add the updated highlight region.
        self.CIndex2 = np.arange(self.XSminIndx, self.XSmaxIndx + 1)
        self.axes[2].fill_between(self.XS[self.CIndex2], self.YS[self.CIndex2], 0, color='y', alpha=0.1, 
                                  label='Sulfoxide Area')
        # Redraw the canvas
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def update_Aliphatic_min(self, value):
        # Clear the highlighted area. 
        for coll in self.axes[3].collections[:]:
            coll.remove()
        # Update the minimum value for the max. 
        idx = np.argmin(np.abs(self.XA - value))
        if self.XAmaxIndx > idx + 1:
            self.XAminIndx = idx
        else:
            idx = self.XAminIndx
        self.spinboxes[4].setValue(self.XA[idx])
        self.spinboxes[5].setRange(self.XA[self.XAminIndx + 1], 1600)
        # Add the updated highlight region.
        self.AIndex2 = np.arange(self.XAminIndx, self.XAmaxIndx + 1)
        self.axes[3].fill_between(self.XA[self.AIndex2], self.YA[self.AIndex2], 0, color='g', alpha=0.1, 
                                  label='Aliphatic Area')
        # Redraw the canvas
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def update_Aliphatic_max(self, value):
        # Clear the highlighted area. 
        for coll in self.axes[3].collections[:]:
            coll.remove()
        # Update the minimum value for the max. 
        idx = np.argmin(np.abs(self.XA - value))
        if self.XAminIndx < idx - 1:
            self.XAmaxIndx = idx
        else:
            idx = self.XAmaxIndx
        self.spinboxes[5].setValue(self.XA[idx])
        self.spinboxes[4].setRange(1300, self.XA[self.XAmaxIndx - 1])
        # Add the updated highlight region.
        self.AIndex2 = np.arange(self.XAminIndx, self.XAmaxIndx + 1)
        self.axes[3].fill_between(self.XA[self.AIndex2], self.YA[self.AIndex2], 0, color='g', alpha=0.1, 
                                  label='Aliphatic Area')
        # Redraw the canvas.
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def SaveExit_Button_Function(self):
        # This function only saves the current progress, and exits the already started loop. 
        self.CurrentFileIndex = len(self.CurrentFileList)
        Check = self.Check_EndofLoop()
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Outlier_Button_Function(self):
        # Extract the spin box values. 
        XCmin = self.spinboxes[0].value()
        XCmax = self.spinboxes[1].value()
        XSmin = self.spinboxes[2].value()
        XSmax = self.spinboxes[3].value()
        XAmin = self.spinboxes[4].value()
        XAmax = self.spinboxes[5].value()
        # Find the corresponding values in the real data. 
        XCmin = self.X[np.argmin(np.abs(self.X - XCmin))]
        XCmax = self.X[np.argmin(np.abs(self.X - XCmax))]
        XSmin = self.X[np.argmin(np.abs(self.X - XSmin))]
        XSmax = self.X[np.argmin(np.abs(self.X - XSmax))]
        XAmin = self.X[np.argmin(np.abs(self.X - XAmin))]
        XAmax = self.X[np.argmin(np.abs(self.X - XAmax))]
        # Calculating the carbonyl area.  
        CIndex = np.where((self.X >= XCmin) & (self.X <= XCmax))[0]
        CArea_base = np.trapz(self.Y[CIndex], self.X[CIndex])
        CArea_tang = CArea_base - np.abs(self.X[CIndex[0]] - self.X[CIndex[-1]]) * self.Y[CIndex[[0, -1]]].mean()
        # Calculating the Sulfoxide area. 
        SIndex = np.where((self.X >= XSmin) & (self.X <= XSmax))[0]
        SArea_base = np.trapz(self.Y[SIndex], self.X[SIndex])
        SArea_tang = SArea_base - np.abs(self.X[SIndex[0]] - self.X[SIndex[-1]]) * self.Y[SIndex[[0, -1]]].mean()
        # Calculating the Aliphatic area. 
        AIndex = np.where((self.X >= XAmin) & (self.X <= XAmax))[0]
        AArea_base = np.trapz(self.Y[AIndex], self.X[AIndex])
        AArea_tang = AArea_base - np.abs(self.X[AIndex[0]] - self.X[AIndex[-1]]) * self.Y[AIndex[[0, -1]]].mean()
        # Calculate the Indices. 
        ICO_base  = CArea_base / AArea_base
        ICO_tang  = CArea_tang / AArea_tang
        ISO_base  = SArea_base / AArea_base
        ISO_tang  = SArea_tang / AArea_tang
        # Save the results to the database. 
        FileName = os.path.basename(self.CurrentFileList[self.CurrentFileIndex])
        Folder   = os.path.dirname(self.CurrentFileList[self.CurrentFileIndex])
        Bnumber  = self.CurBinderInfo['Bnumber']
        RepNumber= self.CurBinderInfo['RepNum']
        LabAging = self.CurBinderInfo['LabAging']
        Xbinary, Xshape, Xdtype = Array_to_Binary(self.X)
        Ybinary, Yshape, Ydtype = Array_to_Binary(self.Y)
        Xrawbinary, Xrawshape, Xrawdtype = Array_to_Binary(self.RawData[:, 0])
        Yrawbinary, Yrawshape, Yrawdtype = Array_to_Binary(self.RawData[:, 1])
        Gbinary, Gshape, Gdtype = Array_to_Binary(np.zeros((0, 3)))
        Cbinary, Cshape, Cdtype = Array_to_Binary(np.zeros((0, 3)))
        Sbinary, Sshape, Sdtype = Array_to_Binary(np.zeros((0, 3)))
        Abinary, Ashape, Adtype = Array_to_Binary(np.zeros((0, 3)))
        Append_to_Database(self.conn, self.cursor, {
            "Bnumber": Bnumber, "Lab_Aging": LabAging, "RepNumber": RepNumber, 
            "FileName": FileName, "FileDirectory": Folder,
            "ICO_Baseline": ICO_base, "ICO_Tangential": ICO_tang,
            "ISO_Baseline": ISO_base, "ISO_Tangential": ISO_tang,
            "Carbonyl_Area_Baseline": CArea_base,  "Carbonyl_Area_Tangential": CArea_tang,
            "Sulfoxide_Area_Baseline": SArea_base, "Sulfoxide_Area_Tangential": SArea_tang,
            "Aliphatic_Area_Baseline": AArea_base, "Aliphatic_Area_Tangential": AArea_tang,
            "Carbonyl_Peak_Wavenumber": -1.0,    "Sulfoxide_Peak_Wavenumber": -1.0,
            "Aliphatic_Peak_Wavenumber_1": -1.0, "Aliphatic_Peak_Wavenumber_2": -1.0,
            "Carbonyl_Peak_Absorption": -1.0,    "Sulfoxide_Peak_Absorption": -1.0,
            "Aliphatic_Peak_Absorption_1": -1.0, "Aliphatic_Peak_Absorption_2": -1.0,
            "Wavenumber": Xbinary, "Wavenumber_shape": Xshape, "Wavenumber_dtype": Xdtype,
            "Absorption": Ybinary, "Absorption_shape": Yshape, "Absorption_dtype": Ydtype,
            "RawWavenumber": Xrawbinary, "RawWavenumber_shape": Xrawshape, "RawWavenumber_dtype": Xrawdtype,
            "RawAbsorbance": Yrawbinary, "RawAbsorbance_shape": Yrawshape, "RawAbsorbance_dtype": Yrawdtype,
            "Carbonyl_Min_Wavenumber": XCmin,  "Carbonyl_Max_Wavenumber": XCmax,
            "Sulfoxide_Min_Wavenumber": XSmin, "Sulfoxide_Max_Wavenumber": XSmax,
            "Aliphatic_Min_Wavenumber": XAmin, "Aliphatic_Max_Wavenumber": XAmax,
            "Baseline_Adjustment_Method": "ALS Smoothing", 
            "ALS_Lambda": self.ALSLambda, "ALS_Ratio": self.ALSRatio, "ALS_NumIter": self.ALSNumIter,
            "Normalization_Method": self.NormalizationMethod.split(" (4")[0].replace(' ', '_'), 
            "Normalization_Coeff": self.Normalization_Coeff,
            "IsOutlier": 1, 
            "Deconv_ICO": -1.0, "Deconv_ISO": -1.0, 
            "Deconv_GaussianList" : Gbinary, "Deconv_GaussianList_shape" : Gshape, "Deconv_GaussianList_dtype" : Gdtype,
            "Deconv_CarbonylList" : Cbinary, "Deconv_CarbonylList_shape" : Cshape, "Deconv_CarbonylList_dtype" : Cdtype, 
            "Deconv_SulfoxideList": Sbinary, "Deconv_SulfoxideList_shape": Sshape, "Deconv_SulfoxideList_dtype": Sdtype, 
            "Deconv_AliphaticList": Abinary, "Deconv_AliphaticList_shape": Ashape, "Deconv_AliphaticList_dtype": Adtype })
        # --------------------------------------------------------------------------------------------------------------
        # Update the index and check for end of the process. 
        while True:
            self.CurrentFileIndex += 1
            Check = self.Check_EndofLoop()
            if Check:
                return
            # ----------------------------------------------------------------------------------------------------------
            # Update the plots and everything. 
            try:
                self.Renew_MainPlot_4Next_File()
                break
            except:
                # print(f'Skipping {self.CurrentFileList[self.CurrentFileIndex]}')
                continue
        # Return Nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def OK_Button_Function(self):
        # Extract the spin box values. 
        XCmin = self.spinboxes[0].value()
        XCmax = self.spinboxes[1].value()
        XSmin = self.spinboxes[2].value()
        XSmax = self.spinboxes[3].value()
        XAmin = self.spinboxes[4].value()
        XAmax = self.spinboxes[5].value()
        # Find the corresponding values in the real data. 
        XCmin = self.X[np.argmin(np.abs(self.X - XCmin))]
        XCmax = self.X[np.argmin(np.abs(self.X - XCmax))]
        XSmin = self.X[np.argmin(np.abs(self.X - XSmin))]
        XSmax = self.X[np.argmin(np.abs(self.X - XSmax))]
        XAmin = self.X[np.argmin(np.abs(self.X - XAmin))]
        XAmax = self.X[np.argmin(np.abs(self.X - XAmax))]
        # Calculating the carbonyl area.  
        CIndex = np.where((self.X >= XCmin) & (self.X <= XCmax))[0]
        CArea_base = np.trapz(self.Y[CIndex], self.X[CIndex])
        CArea_tang = CArea_base - np.abs(self.X[CIndex[0]] - self.X[CIndex[-1]]) * self.Y[CIndex[[0, -1]]].mean()
        # Calculating the Sulfoxide area. 
        SIndex = np.where((self.X >= XSmin) & (self.X <= XSmax))[0]
        SArea_base = np.trapz(self.Y[SIndex], self.X[SIndex])
        SArea_tang = SArea_base - np.abs(self.X[SIndex[0]] - self.X[SIndex[-1]]) * self.Y[SIndex[[0, -1]]].mean()
        # Calculating the Aliphatic area. 
        AIndex = np.where((self.X >= XAmin) & (self.X <= XAmax))[0]
        AArea_base = np.trapz(self.Y[AIndex], self.X[AIndex])
        AArea_tang = AArea_base - np.abs(self.X[AIndex[0]] - self.X[AIndex[-1]]) * self.Y[AIndex[[0, -1]]].mean()
        # Calculate the Indices. 
        ICO_base  = CArea_base / AArea_base
        ICO_tang  = CArea_tang / AArea_tang
        ISO_base  = SArea_base / AArea_base
        ISO_tang  = SArea_tang / AArea_tang
        # Save the results to the database. 
        FileName = os.path.basename(self.CurrentFileList[self.CurrentFileIndex])
        Folder   = os.path.dirname(self.CurrentFileList[self.CurrentFileIndex])
        Bnumber  = self.CurBinderInfo['Bnumber']
        RepNumber= self.CurBinderInfo['RepNum']
        LabAging = self.CurBinderInfo['LabAging']
        Xbinary, Xshape, Xdtype = Array_to_Binary(self.X)
        Ybinary, Yshape, Ydtype = Array_to_Binary(self.Y)
        Xrawbinary, Xrawshape, Xrawdtype = Array_to_Binary(self.RawData[:, 0])
        Yrawbinary, Yrawshape, Yrawdtype = Array_to_Binary(self.RawData[:, 1])
        Gbinary, Gshape, Gdtype = Array_to_Binary(self.Deconv['Gaussian_List'])
        Cbinary, Cshape, Cdtype = Array_to_Binary(self.Deconv['Carbonyl_Gaussians'])
        Sbinary, Sshape, Sdtype = Array_to_Binary(self.Deconv['Sulfoxide_Gaussians'])
        Abinary, Ashape, Adtype = Array_to_Binary(self.Deconv['Aliphatic_Gaussians'])
        # Find the Aliphatic peaks.
        XPeak, YPeak, Prominence, XLeft, XRight = Find_Peaks(np.hstack((self.X.reshape(-1, 1), self.Y.reshape(-1, 1))), 
                                                             [XAmin, XAmax], 0.001)
        # Check if two peaks were found. 
        if len(XPeak) < 1:
            raise Exception(f'Peak was NOT found in the range of {XAmin:.1f} to {XAmax:.1f} cm^-1 for this binder! ' +
                            f'Check manually!')
        elif len(XPeak) > 1:
            # More than two peak were found. Using two close ones as main peaks.
            SortedIndex = np.argsort(YPeak)
            MaxIndex    = SortedIndex[-2:]      # Get the highwst peaks. 
            MaxIndex    = MaxIndex[np.argsort(np.array(XPeak)[MaxIndex])]       # Sort based on their location.
            # Fix the Peaks. 
            XPeak = np.array(XPeak)[MaxIndex]
            YPeak = np.array(YPeak)[MaxIndex]
        # Append the data to the database. 
        Append_to_Database(self.conn, self.cursor, {
            "Bnumber": Bnumber, "Lab_Aging": LabAging, "RepNumber": RepNumber, 
            "FileName": FileName, "FileDirectory": Folder,
            "ICO_Baseline": ICO_base, "ICO_Tangential": ICO_tang,
            "ISO_Baseline": ISO_base, "ISO_Tangential": ISO_tang,
            "Carbonyl_Area_Baseline": CArea_base,  "Carbonyl_Area_Tangential": CArea_tang,
            "Sulfoxide_Area_Baseline": SArea_base, "Sulfoxide_Area_Tangential": SArea_tang,
            "Aliphatic_Area_Baseline": AArea_base, "Aliphatic_Area_Tangential": AArea_tang,
            "Carbonyl_Peak_Wavenumber": self.X[CIndex][np.argmax(self.Y[CIndex])],
            "Sulfoxide_Peak_Wavenumber": self.X[SIndex][np.argmax(self.Y[SIndex])],
            "Aliphatic_Peak_Wavenumber_1": XPeak[0],
            "Aliphatic_Peak_Wavenumber_2": XPeak[1],
            "Carbonyl_Peak_Absorption": self.Y[CIndex][np.argmax(self.Y[CIndex])],
            "Sulfoxide_Peak_Absorption": self.Y[SIndex][np.argmax(self.Y[SIndex])],
            "Aliphatic_Peak_Absorption_1": YPeak[0],
            "Aliphatic_Peak_Absorption_2": YPeak[0],
            "Wavenumber": Xbinary, "Wavenumber_shape": Xshape, "Wavenumber_dtype": Xdtype,
            "Absorption": Ybinary, "Absorption_shape": Yshape, "Absorption_dtype": Ydtype,
            "RawWavenumber": Xrawbinary, "RawWavenumber_shape": Xrawshape, "RawWavenumber_dtype": Xrawdtype,
            "RawAbsorbance": Yrawbinary, "RawAbsorbance_shape": Yrawshape, "RawAbsorbance_dtype": Yrawdtype,
            "Carbonyl_Min_Wavenumber": XCmin,  "Carbonyl_Max_Wavenumber": XCmax,
            "Sulfoxide_Min_Wavenumber": XSmin, "Sulfoxide_Max_Wavenumber": XSmax,
            "Aliphatic_Min_Wavenumber": XAmin, "Aliphatic_Max_Wavenumber": XAmax,
            "Baseline_Adjustment_Method": "ALS Smoothing", 
            "ALS_Lambda": self.ALSLambda, "ALS_Ratio": self.ALSRatio, "ALS_NumIter": self.ALSNumIter,
            "Normalization_Method": self.NormalizationMethod.split(" (4")[0].replace(' ', '_'), 
            "Normalization_Coeff": self.Normalization_Coeff,
            "IsOutlier": 0, 
            "Deconv_ICO": self.Deconv["ICO"], "Deconv_ISO": self.Deconv["ISO"], 
            "Deconv_GaussianList" : Gbinary, "Deconv_GaussianList_shape" : Gshape, "Deconv_GaussianList_dtype" : Gdtype,
            "Deconv_CarbonylList" : Cbinary, "Deconv_CarbonylList_shape" : Cshape, "Deconv_CarbonylList_dtype" : Cdtype, 
            "Deconv_SulfoxideList": Sbinary, "Deconv_SulfoxideList_shape": Sshape, "Deconv_SulfoxideList_dtype": Sdtype, 
            "Deconv_AliphaticList": Abinary, "Deconv_AliphaticList_shape": Ashape, "Deconv_AliphaticList_dtype": Adtype            
            })
        # --------------------------------------------------------------------------------------------------------------
        # Reset the binder info. 
        self.CurBinderInfo = {'Bnumber': -1, 'RepNum': -1, 'LabAging': ''}
        # Update the index and check for end of the process. 
        while True:
            self.CurrentFileIndex += 1
            Check = self.Check_EndofLoop()
            if Check:
                return
            # ----------------------------------------------------------------------------------------------------------
            # Update the plots and everything. 
            try:
                self.Renew_MainPlot_4Next_File()
                break
            except:
                # print(f'Skipping {self.CurrentFileList[self.CurrentFileIndex]}')
                continue
        # Return Nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Check_EndofLoop(self):
        """
        This function only checks if all the required files are analyzed, and if the analysis is finished, it reactivate
        the main window. 
        """
        if self.CurrentFileIndex >= len(self.CurrentFileList):
            QMessageBox.information(self, "Success", 
                                    f"Loop over {len(self.CurrentFileList)} files has been finished!")
            # Clear the plots.
            self.Funtion_Clear_Axes()
            # Disable the buttons.
            self.Button_OK.setEnabled(False)
            self.Button_Outlier.setEnabled(False)
            self.Button_SaveProgress.setEnabled(False)
            # Disable the spinboxes.
            for j in range(6):
                self.spinboxes[j].setEnabled(False)
            # Reset the progress bar and its labels. 
            self.NumFilesProgress_bar.setValue(0)
            self.Label_NumFilesProgress.setText(f"Number of selected files: N/A")
            self.Label_CurrentFileName.setText(f"Waiting for file...")
            # Enable the buttons of DB manager.
            self.Button_AddData.setEnabled(True)
            self.Button_ReviewDB.setEnabled(True)
            self.Button_ExportDB.setEnabled(True)
            # enable the preprocessing options. 
            self.LineEdit_ALSLambda.setEnabled(False)
            self.LineEdit_ALSRatio.setEnabled(False)
            self.LineEdit_ALSNumIter.setEnabled(False)
            self.DropDown_NormalizationMethod.setEnabled(False)
            self.Button_UpdatePreprocess.setEnabled(False)
            # Reset the values of the preprocessing options. 
            self.LineEdit_ALSLambda.setText("1e6")
            self.LineEdit_ALSRatio.setText("1e-1")
            self.LineEdit_ALSNumIter.setText("150")
            self.DropDown_NormalizationMethod.setCurrentIndex(1)
            # Return "True".
            return True
        # Otherwise, return False.
        return False
    # ------------------------------------------------------------------------------------------------------------------
    def FileExistedError(self, Title, Body):
        # Create a QMessageBox
        message_box = QMessageBox()
        message_box.setIcon(QMessageBox.Critical)
        message_box.setText(Title)
        message_box.setInformativeText(Body)
        message_box.setWindowTitle("File Existed Error")
        message_box.setStandardButtons(QMessageBox.Ok)
        # Add a checkbox
        checkbox = QCheckBox("Do not show this again")
        # Access the layout of the QMessageBox and add the checkbox
        layout = message_box.layout()
        layout.addWidget(checkbox, layout.rowCount(), 0, 1, layout.columnCount())
        # Show the message box
        message_box.exec_()
        # Check the state of the checkbox after the message box is closed
        if checkbox.isChecked():
            self.ShowFileExistedError = False
        else:
            self.ShowFileExistedError = True
    # ------------------------------------------------------------------------------------------------------------------
    def Renew_MainPlot_4Next_File(self):
        """
        This function renew and draw the main plot and prepare it for the next analysis.  
        """
        Data = None                     # reset the "Data" variable. 
        self.Funtion_Clear_Axes()       # First, clear the plotting axes. 
        # Read the files, until a proper file achieved. 
        for i in range(self.CurrentFileIndex, len(self.CurrentFileList)):
            self.CurrentFileIndex = i
            # Check if the file is already exist in the database. 
            self.cursor.execute("SELECT EXISTS(SELECT 1 FROM FTIR WHERE FileName = ?)", 
                                (os.path.basename(self.CurrentFileList[i]),))
            exists = self.cursor.fetchone()[0]
            if exists:
                if not self.ShowFileExistedError:
                    continue
                self.FileExistedError(f"File Already Existed!", 
                                    f"The file <{os.path.basename(self.CurrentFileList[i])}> was already exists "+
                                    f"in the database. Instead of reloading the file, please try to edit/modify " +
                                    f"the analysis on that specific file. Take note of B-number, Rep number, and " +
                                    f"Lab aging state, and try to use 'Edit/Modify DB button to edit this results!" + 
                                    f"'\nFile directory: {os.path.dirname(self.CurrentFileList[i])}")
                continue
            # Check the file name and binder information. 
            Bnumber, Rep, LabAging = Get_Info_From_Name(os.path.basename(self.CurrentFileList[i]))
            if Bnumber == None:
                # Ask user for input. 
                ManualDetails = Get_Details_Manually(os.path.basename(self.CurrentFileList[i]), self.conn, self.cursor)
                if ManualDetails.exec_():
                    Bnumber, Rep, LabAging = ManualDetails.GetInputs()
                else:
                    progress = int((i + 1) / len(self.CurrentFileList) * 100)
                    if progress > 100: progress = 100
                    self.NumFilesProgress_bar.setValue(progress)
                    self.Terminal.appendPlainText(f">>> ERROR!! File name is NOT compatible!: {self.CurrentFileList[i]}")
                    QMessageBox.critical(self, "Unable to Read File!", 
                                        f"The name of the file <{os.path.basename(self.CurrentFileList[i])}> was not "+
                                        f"comparible with file name format! Please make sure to follow " +
                                        f"'BXXXX_FTIR_RepY_AGING.dpt' format, as this is the only format acceptable by " +
                                        f"the code!\nFile directory: {os.path.dirname(self.CurrentFileList[i])}")
                    self.CurBinderInfo = {'Bnumber': -1, 'RepNum': -1, 'LabAging': ''}      # Reset binder info.
                    continue
            self.CurBinderInfo = {'Bnumber': Bnumber, 'RepNum': Rep, 'LabAging': LabAging}  # Update binder info. 
            # Try reading the input files. 
            try:
                Data = Read_FTIR_Data(self.CurrentFileList[i])
                FileName = os.path.basename(self.CurrentFileList[i])
                break
            except:         # If there is an error in reading the file, continue. 
                progress = int((i + 1) / len(self.CurrentFileList) * 100)
                if progress > 100: progress = 100
                self.NumFilesProgress_bar.setValue(progress)
                self.Terminal.appendPlainText(f">>> ERROR!! Unable to Read!: {self.CurrentFileList[i]}")
                QMessageBox.critical(self, "Unable to Read File!", 
                                     f"The file <{os.path.basename(self.CurrentFileList[i])}> was not readable! " +
                                     f"Please make sure to provide a Comma Delimiter file with two columns, (*.dpt) " +
                                     f"files are preffered.\nFile directory: " +
                                     f"{os.path.dirname(self.CurrentFileList[i])}")
                continue
        if type(Data) == type(None):
            self.CurrentFileIndex += 1  # Increase the current file index to make sure it is at end of the file list.
            Check = self.Check_EndofLoop()      # Perform the "Check" to take care of the GUI properties. 
            # self.Button_ExportDB.setEnabled(True)
            self.CurrentFileIndex = 0
            self.CurrentFileList = []
            self.Terminal.appendPlainText("\n>>> Ready for new file selection!")      # Print message to user.
            self.Label_NumFilesProgress.setText(f"Number of selected files: N/A")   # reset the number of selected files
            self.NumFilesProgress_bar.setValue(0)                                   # Set progress bar to zero.
            return
        # --------------------------------------------------------------------------------------------------------------
        # Reset the values of the preprocessing options. 
        self.LineEdit_ALSLambda.setText("1e6")
        self.LineEdit_ALSRatio.setText("1e-1")
        self.LineEdit_ALSNumIter.setText("150")
        self.DropDown_NormalizationMethod.setCurrentIndex(1)
        # Otherwise, perform the baseline adjustment and normalization.
        data = Baseline_Adjustment_ALS(Data, 1e6, 1e-1, 150)            # Baseline adjustment
        Rawdata = Data.copy()
        data, NormalizationCoeff = Normalization_Method_B(data)         # Normalization method B for now. 
        self.Normalization_Coeff = NormalizationCoeff
        self.ALSLambda = 1e6
        self.ALSRatio  = 1e-1
        self.ALSNumIter= 150
        self.NormalizationMethod = "Method_B"
        X = data[:, 0]
        Y = data[:, 1] 
        self.RawData = Rawdata.copy()
        self.X = X
        self.Y = Y
        # Also run the algorithm to get the indices. 
        # Calculate the areas. 
        FlagC, FlagS, FlagA = False, False, False
        try:
            Carbonyl  = Calc_Carbonyl_Area(data)
            Carbonyl_Range = [Carbonyl['Xvalues'].min(), Carbonyl['Xvalues'].max()]
        except: 
            FlagC = True
            Carbonyl_Range = [1670, 1690]
        try:
            Sulfoxide = Calc_Sulfoxide_Area(data)
            Sulfoxide_Range = [Sulfoxide['Xvalues'].min(), Sulfoxide['Xvalues'].max()]
        except:
            FlagS = True
            Sulfoxide_Range = [1020, 1040]
        try:
            Aliphatic = Calc_Aliphatic_Area(data)
            Aliphatic_Range = [Aliphatic['Xvalues'].min(), Aliphatic['Xvalues'].max()]
        except:
            FlagA = True
            Aliphatic_Range = [1350, 1450]
        # --------------------------------------------------------------------------------------------------------------
        # Run the deconvolution method and get the results. 
        Deconv = Run_Deconvolution(X, Y)
        self.Deconv = Deconv.copy()
        Carbonyl_Gaussians = Deconv['Carbonyl_Gaussians']
        Sulfoxide_Gaussians = Deconv['Sulfoxide_Gaussians']
        Aliphatic_Gaussians = Deconv['Aliphatic_Gaussians']
        # --------------------------------------------------------------------------------------------------------------
        # Calculating the Areas. 
        CArea = (Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Carbonyl_Gaussians[:, 1])).sum()
        SArea = (Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Aliphatic_Gaussians[:, 1])).sum()
        # Update the deconvolution information. 
        self.Decon_Label_CArea.setText(f'Carbonyl Area: {CArea:.2f}')
        self.Decon_Label_SArea.setText(f'Sulfoxide Area: {SArea:.2f}')
        self.Decon_Label_AArea.setText(f'Aliphatic Area: {AArea:.2f}')
        self.Decon_Label_Index.setText(f'ICO: {Deconv["ICO"]:.4f}, ISO: {Deconv["ISO"]:.4f}')
        # --------------------------------------------------------------------------------------------------------------
        # Plot the data. 
        # First, whole wavenumbers. 
        self.axes[0].plot(data[:, 0], data[:, 1], color='k', ls='-', label='Processed data')
        self.axes[0].plot(Rawdata[:, 0], Rawdata[:, 1], color='b', ls='-', lw=0.5, label='raw data')
        self.axes[0].axvspan(xmin=1620, xmax=1800, alpha=0.1, color='r', label='Carbonyl search area')
        self.axes[0].axvspan(xmin=970,  xmax=1070, alpha=0.1, color='y', label='Sulfoxide search area')
        self.axes[0].legend()
        self.axes[0].set_xlim([2000, 600])
        # For cabonyl plot.
        CIndex = np.where((data[:, 0] >= 1600) & (data[:, 0] <= 1800))[0]
        self.XC = data[CIndex, 0]
        self.YC = data[CIndex, 1]
        self.CIndex = CIndex
        self.XCminIndx = np.where(self.XC >= Carbonyl_Range[0])[0][0]
        self.XCmaxIndx = np.where(self.XC <= Carbonyl_Range[1])[0][-1]
        self.XCmin = self.XC[self.XCminIndx]
        self.XCmax = self.XC[self.XCmaxIndx]
        self.CIndex2 = np.arange(self.XCminIndx, self.XCmaxIndx + 1)
        self.axes[1].plot(data[CIndex, 0], data[CIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[1].fill_between(self.XC[self.CIndex2], self.YC[self.CIndex2], 0, color='r', alpha=0.2, 
                                  label='Carbonyl Area')
        Xgaussian = np.linspace(1600, 1800, num=1000)
        for ii in range(Carbonyl_Gaussians.shape[0]):
            if ii == 0:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, Carbonyl_Gaussians[ii, 0], 
                                                        Carbonyl_Gaussians[ii, 1], Carbonyl_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, Carbonyl_Gaussians[ii, 0], 
                                                        Carbonyl_Gaussians[ii, 1], Carbonyl_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[1].legend()
        self.axes[1].invert_xaxis()
        # For Sulfoxide plot
        SIndex = np.where((data[:, 0] >= 940) & (data[:, 0] <= 1100))[0]
        self.XS = data[SIndex, 0]
        self.YS = data[SIndex, 1]
        self.SIndex = SIndex
        self.XSminIndx = np.where(self.XS >= Sulfoxide_Range[0])[0][0]
        self.XSmaxIndx = np.where(self.XS <= Sulfoxide_Range[1])[0][-1]
        self.XSmin = self.XS[self.XSminIndx]
        self.XSmax = self.XS[self.XSmaxIndx]
        self.SIndex2 = np.arange(self.XSminIndx, self.XSmaxIndx + 1)
        self.axes[2].plot(data[SIndex, 0], data[SIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[2].fill_between(self.XS[self.SIndex2], self.YS[self.SIndex2], 0, color='y', alpha=0.2, 
                                  label='Sulfoxide Area')
        Xgaussian = np.linspace(940, 1100, num=1000)
        for ii in range(Sulfoxide_Gaussians.shape[0]):
            if ii == 0:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, Sulfoxide_Gaussians[ii, 0], 
                                                        Sulfoxide_Gaussians[ii, 1], Sulfoxide_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, Sulfoxide_Gaussians[ii, 0], 
                                                        Sulfoxide_Gaussians[ii, 1], Sulfoxide_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[2].legend()
        self.axes[2].invert_xaxis()
        # For Aliphatic plot
        AIndex = np.where((data[:, 0] >= 1300) & (data[:, 0] <= 1600))[0]
        self.XA = data[AIndex, 0]
        self.YA = data[AIndex, 1]
        self.AIndex = AIndex
        self.XAminIndx = np.where(self.XA >= Aliphatic_Range[0])[0][0]
        self.XAmaxIndx = np.where(self.XA <= Aliphatic_Range[1])[0][-1]
        self.XAmin = self.XA[self.XAminIndx]
        self.XAmax = self.XA[self.XAmaxIndx]
        self.AIndex2 = np.arange(self.XAminIndx, self.XAmaxIndx + 1)
        self.axes[3].plot(data[AIndex, 0], data[AIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[3].fill_between(self.XA[self.AIndex2], self.YA[self.AIndex2], 0, color='g', alpha=0.2, 
                                  label='Aliphatic Area')
        Xgaussian = np.linspace(1300, 1600, num=1000)
        for ii in range(Aliphatic_Gaussians.shape[0]):
            if ii == 0:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, Aliphatic_Gaussians[ii, 0], 
                                                        Aliphatic_Gaussians[ii, 1], Aliphatic_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, Aliphatic_Gaussians[ii, 0], 
                                                        Aliphatic_Gaussians[ii, 1], Aliphatic_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[3].legend()
        self.axes[3].invert_xaxis()
        # Redraw the canvas
        self.canvas.draw()
        # Enable the adjustment buttons. 
        self.Button_OK.setEnabled(True)
        self.Button_Outlier.setEnabled(True)
        self.Button_SaveProgress.setEnabled(True)
        # Update the file name and remaining number of files. 
        self.Label_NumFilesProgress.setText(f"Number of selected/Remained files: {len(self.CurrentFileList)}, " + 
                                            f"{len(self.CurrentFileList) - self.CurrentFileIndex}")
        self.Label_CurrentFileName.setText(f"{self.CurrentFileList[self.CurrentFileIndex]}")
        # Update and enable the spinboxes. 
        SpinBoxValues = [self.XCmin, self.XCmax, self.XSmin, self.XSmax, self.XAmin, self.XAmax]
        SpinBoxStep = np.diff(X).mean()
        for i in range(len(self.spinboxes)):
            self.spinboxes[i].setEnabled(True)
            self.spinboxes[i].setSingleStep(SpinBoxStep)
            self.spinboxes[i].setDecimals(1)
            self.spinboxes[i].setValue(SpinBoxValues[i])
        # Update the spinbox ranges.
        self.spinboxes[0].setRange(1600, self.XC[self.XCmaxIndx - 1])
        self.spinboxes[1].setRange(self.XC[self.XCminIndx + 1], 1800)
        self.spinboxes[2].setRange(940,  self.XS[self.XSmaxIndx - 1])
        self.spinboxes[3].setRange(self.XS[self.XSminIndx + 1], 1100)
        self.spinboxes[4].setRange(1300, self.XA[self.XAmaxIndx - 1])
        self.spinboxes[5].setRange(self.XA[self.XAminIndx + 1], 1600)
        # Update the progress bar and text.
        progress = int((self.CurrentFileIndex + 1) / len(self.CurrentFileList) * 100)
        if progress > 100: progress = 100
        self.NumFilesProgress_bar.setValue(progress)
        # enable the preprocessing options. 
        self.LineEdit_ALSLambda.setEnabled(True)
        self.LineEdit_ALSRatio.setEnabled(True)
        self.LineEdit_ALSNumIter.setEnabled(True)
        self.DropDown_NormalizationMethod.setEnabled(True)
        self.Button_UpdatePreprocess.setEnabled(True)
        # Return Nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_UpdatePreprocessing(self):
        """
        This function updates the preprocessing procedure. 
        """
        # Check the number of iteration. 
        NumIter = self.LineEdit_ALSNumIter.text()
        try:
            NumIter = int(float(NumIter))
            if NumIter < 100:
                NumIter = 100
                self.LineEdit_ALSNumIter.setText("100")
            elif NumIter > 1000:
                NumIter = 1000
                self.LineEdit_ALSNumIter.setText("1000")
            else:
                self.LineEdit_ALSNumIter.setText(f"{NumIter}")
        except Exception as err:
            QMessageBox.critical(self, "Error in Number of iterations!", err)
            return
        # --------------------------------------------------------------------------------------------------------------
        # Check the Ratio.
        Ratio = self.LineEdit_ALSRatio.text()
        try:
            Ratio = float(Ratio)
            if Ratio > 0.5:
                Ratio = 0.5
                self.LineEdit_ALSRatio.setText(f'{Ratio:.6e}')
            elif Ratio < 0.0001:
                Ratio = 0.0001
                self.LineEdit_ALSRatio.setText(f'{Ratio:.6e}')
            else:
                self.LineEdit_ALSRatio.setText(f'{Ratio:.6e}')
        except Exception as err:
            QMessageBox.critical(self, "Error in ALS Ratio!", err)
            return
        # --------------------------------------------------------------------------------------------------------------
        # Check the Lambda
        Lambda = self.LineEdit_ALSLambda.text()
        try:
            Lambda = float(Lambda)
            if Lambda > 1e10:
                Lambda = 1e10
                self.LineEdit_ALSLambda.setText(f'{Lambda:.3e}')
            elif Lambda < 10:
                Lambda = 10
                self.LineEdit_ALSLambda.setText(f'{Lambda:.3e}')
            else:
                self.LineEdit_ALSLambda.setText(f'{Lambda:.3e}')
        except Exception as err:
            QMessageBox.critical(self, "Error in ALS Lambda!", err)
            return
        # --------------------------------------------------------------------------------------------------------------
        # Perform the ALS Smoothing baseline correction and normalization. 
        data = Baseline_Adjustment_ALS(self.RawData, Lambda, Ratio, NumIter)        # Baseline adjustment.
        if self.DropDown_NormalizationMethod.currentIndex() == 0:
            data, NormalizationCoeff = Normalization_Method_A(data)
        elif self.DropDown_NormalizationMethod.currentIndex() == 1:
            data, NormalizationCoeff = Normalization_Method_B(data)
        elif self.DropDown_NormalizationMethod.currentIndex() == 2:
            data, NormalizationCoeff = Normalization_Method_C(data)
        elif self.DropDown_NormalizationMethod.currentIndex() == 3:
            data, NormalizationCoeff = Normalization_Method_D(data)
        self.Normalization_Coeff = NormalizationCoeff
        self.ALSLambda = Lambda
        self.ALSRatio  = Ratio
        self.ALSNumIter= NumIter
        self.NormalizationMethod = self.DropDown_NormalizationMethod.currentText()
        X = data[:, 0].copy()
        Y = data[:, 1].copy()
        self.X = X
        self.Y = Y
        # --------------------------------------------------------------------------------------------------------------
        # Re-Run the deconvolution method and get the results. 
        Deconv = Run_Deconvolution(X, Y)
        self.Deconv = Deconv.copy()
        Carbonyl_Gaussians = Deconv['Carbonyl_Gaussians']
        Sulfoxide_Gaussians = Deconv['Sulfoxide_Gaussians']
        Aliphatic_Gaussians = Deconv['Aliphatic_Gaussians']
        # --------------------------------------------------------------------------------------------------------------
        # Plot the data. 
        self.Funtion_Clear_Axes()       # First, clear the plots.
        # First, whole wavenumbers. 
        self.axes[0].plot(data[:, 0], data[:, 1], color='k', ls='-', label='Processed data')
        self.axes[0].plot(self.RawData[:, 0], self.RawData[:, 1], color='b', ls='-', lw=0.5, label='raw data')
        self.axes[0].axvspan(xmin=1620, xmax=1800, alpha=0.1, color='r', label='Carbonyl search area')
        self.axes[0].axvspan(xmin=970,  xmax=1070, alpha=0.1, color='y', label='Sulfoxide search area')
        self.axes[0].legend()
        self.axes[0].set_xlim([2000, 600])
        # For cabonyl plot.
        CIndex = np.where((data[:, 0] >= 1600) & (data[:, 0] <= 1800))[0]
        self.XC = data[CIndex, 0]
        self.YC = data[CIndex, 1]
        self.CIndex = CIndex
        self.XCminIndx = np.where(self.XC >= self.spinboxes[0].value())[0][0]
        self.XCmaxIndx = np.where(self.XC <= self.spinboxes[1].value())[0][-1]
        self.XCmin = self.XC[self.XCminIndx]
        self.XCmax = self.XC[self.XCmaxIndx]
        self.CIndex2 = np.arange(self.XCminIndx, self.XCmaxIndx + 1)
        self.axes[1].plot(data[CIndex, 0], data[CIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[1].fill_between(self.XC[self.CIndex2], self.YC[self.CIndex2], 0, color='r', alpha=0.2, 
                                  label='Carbonyl Area')
        Xgaussian = np.linspace(1600, 1800, num=1000)
        for ii in range(Carbonyl_Gaussians.shape[0]):
            if ii == 0:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, Carbonyl_Gaussians[ii, 0], 
                                                        Carbonyl_Gaussians[ii, 1], Carbonyl_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, Carbonyl_Gaussians[ii, 0], 
                                                        Carbonyl_Gaussians[ii, 1], Carbonyl_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[1].legend()
        self.axes[1].invert_xaxis()
        # For Sulfoxide plot
        SIndex = np.where((data[:, 0] >= 940) & (data[:, 0] <= 1100))[0]
        self.XS = data[SIndex, 0]
        self.YS = data[SIndex, 1]
        self.SIndex = SIndex
        self.XSminIndx = np.where(self.XS >= self.spinboxes[2].value())[0][0]
        self.XSmaxIndx = np.where(self.XS <= self.spinboxes[3].value())[0][-1]
        self.XSmin = self.XS[self.XSminIndx]
        self.XSmax = self.XS[self.XSmaxIndx]
        self.SIndex2 = np.arange(self.XSminIndx, self.XSmaxIndx + 1)
        self.axes[2].plot(data[SIndex, 0], data[SIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[2].fill_between(self.XS[self.SIndex2], self.YS[self.SIndex2], 0, color='y', alpha=0.2, 
                                  label='Sulfoxide Area')
        Xgaussian = np.linspace(940, 1100, num=1000)
        for ii in range(Sulfoxide_Gaussians.shape[0]):
            if ii == 0:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, Sulfoxide_Gaussians[ii, 0], 
                                                        Sulfoxide_Gaussians[ii, 1], Sulfoxide_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, Sulfoxide_Gaussians[ii, 0], 
                                                        Sulfoxide_Gaussians[ii, 1], Sulfoxide_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[2].legend()
        self.axes[2].invert_xaxis()
        # For Aliphatic plot
        AIndex = np.where((data[:, 0] >= 1300) & (data[:, 0] <= 1600))[0]
        self.XA = data[AIndex, 0]
        self.YA = data[AIndex, 1]
        self.AIndex = AIndex
        self.XAminIndx = np.where(self.XA >= self.spinboxes[4].value())[0][0]
        self.XAmaxIndx = np.where(self.XA <= self.spinboxes[5].value())[0][-1]
        self.XAmin = self.XA[self.XAminIndx]
        self.XAmax = self.XA[self.XAmaxIndx]
        self.AIndex2 = np.arange(self.XAminIndx, self.XAmaxIndx + 1)
        self.axes[3].plot(data[AIndex, 0], data[AIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[3].fill_between(self.XA[self.AIndex2], self.YA[self.AIndex2], 0, color='g', alpha=0.2, 
                                  label='Aliphatic Area')
        Xgaussian = np.linspace(1300, 1600, num=1000)
        for ii in range(Aliphatic_Gaussians.shape[0]):
            if ii == 0:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, Aliphatic_Gaussians[ii, 0], 
                                                        Aliphatic_Gaussians[ii, 1], Aliphatic_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, Aliphatic_Gaussians[ii, 0], 
                                                        Aliphatic_Gaussians[ii, 1], Aliphatic_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[3].legend()
        self.axes[3].invert_xaxis()
        # Redraw the canvas
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def Funtion_Clear_Axes(self):
        """
        This function simply clear the axes (four axes in AutoFTIR) and initialize them for plotting the next results.
        """
        # First, clear the plots.
        for j in range(4):
            self.axes[j].cla()
        # Prepare the plots. 
        Titles = ['Wide range data', 'Carbonyl area', 'Sulfoxide area', 'Aliphatic area']
        for i in range(4):
            if i >= 2:
                self.axes[i].set_xlabel('Wavenumber (1/cm)', fontsize=9, fontweight='bold', color='k')
            if i in [0, 2]:
                self.axes[i].set_ylabel('Normalized Absorption', fontsize=9, fontweight='bold', color='k')
            self.axes[i].set_title(Titles[i], fontsize=11, fontweight='bold', color='k')
            self.axes[i].grid(which='both', color='gray', alpha=0.1)
        # Redraw the canvas
        self.canvas.draw()
        # Return nothing. 
        return
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class Get_Details_Manually(QDialog):
    def __init__(self, FileName, conn, cursor):
        super().__init__()
        self.conn = conn
        self.cursor = cursor
        self.FileName = FileName
        self.Result = [None, None, None]
        self.setWindowTitle("Enter Details Manually")
        self.setMinimumSize(300, 170)
        layout = QVBoxLayout()
        # LineEdit fields
        self.LineEdit_Bnumber = QLineEdit(self)
        self.LineEdit_Bnumber.setPlaceholderText("Enter 4 or 5 digit ID-number ...")
        self.LineEdit_Bnumber.setValidator(QIntValidator(1, 99999))
        self.LineEdit_RepNumber = QLineEdit(self)
        self.LineEdit_RepNumber.setPlaceholderText("Enter Repetition number ...")
        self.LineEdit_RepNumber.setValidator(QIntValidator(1, 99))
        self.DropDown_Aging = QComboBox(self)
        self.DropDown_Aging.addItems(["ORG", "RTFO", "1PAV", "2PAV"])
        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.Function_OK)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        # Add widgets to layout
        Form = QFormLayout()
        Form.addRow(QLabel('File name:'), QLabel(self.FileName))
        Form.addRow(QLabel('ID-number:'), self.LineEdit_Bnumber)
        Form.addRow(QLabel('Repetition number:'), self.LineEdit_RepNumber)
        Form.addRow(QLabel('Aging Level:'), self.DropDown_Aging)
        layout.addLayout(Form)
        layout.addLayout(button_layout)
        self.setLayout(layout)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_OK(self):
        """
        This function first validate the results and then tries to close the dialog. 
        """
        # Get the inputs.  
        Bnumber  = self.LineEdit_Bnumber.text()
        RepNum   = self.LineEdit_RepNumber.text()
        LabAging = self.DropDown_Aging.currentText()
        # First, check if the integer values entered for Bnumber and RepNumber. 
        try:
            Bnumber = int(Bnumber)
            RepNum  = int(RepNum)
        except:
            # Do nothing. 
            return 
        # Then, check if the combination of the three is already available in database. 
        self.cursor.execute('SELECT EXISTS(SELECT 1 FROM FTIR WHERE Bnumber = ? AND RepNumber = ? AND Lab_Aging = ?)', 
                            (Bnumber, RepNum, LabAging))
        Exists = self.cursor.fetchone()[0]
        if Exists:
            QMessageBox.critical(self, "Data already available!", 
                                     f"The combination of the B-number ({Bnumber}), Repetition number ({RepNum}), " + 
                                     f"and laboratory aging ({LabAging}) is already available in the database. If " + 
                                     f"this is a new test result, please increase the repetition number.")
            self.Result = [None, None, None]
            return
        # Otherwise, close the dialog. 
        self.Result = [Bnumber, RepNum, LabAging]
        self.accept()
    # ------------------------------------------------------------------------------------------------------------------
    def GetInputs(self):
        return self.Result[0], self.Result[1], self.Result[2]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


if __name__ == '__main__':

    app = QApplication(sys.argv)
    # Connect to a SQL database. 
    conn = sqlite3.connect("C:\\Users\\SF.Abdollahi.ctr\\OneDrive - DOT OST\\FTIR_Temp\\PTF5_DB.db")
    cursor = conn.cursor()

    Main = MainPage(conn, cursor, 'Example')
    Main.show()
    app.exec()



    app.quit()
    print('finish')
