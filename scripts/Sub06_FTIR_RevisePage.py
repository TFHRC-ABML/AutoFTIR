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
    QPlainTextEdit, QStackedWidget, QTableWidget, QTableWidgetItem, QStyledItemDelegate, QComboBox
from PyQt5.QtGui import QPixmap, QFont, QRegExpValidator, QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt, QRegExp
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scripts.Sub02_CreateNewSQLTable import Get_DB_SummaryData, Append_to_Database, Get_Info_From_Name, Update_Row_in_Database
from scripts.Sub04_FTIR_Analysis_Functions import Read_FTIR_Data, Baseline_Adjustment_ALS, Normalization_Method_B, \
    Calc_Aliphatic_Area, Calc_Carbonyl_Area, Calc_Sulfoxide_Area, Array_to_Binary, Binary_to_Array, Find_Peaks, \
    FindRepresentativeRows, Normalization_Method_A, Normalization_Method_B, Normalization_Method_C, Normalization_Method_D 
from scripts.Sub05_ReviewPage import DB_ReviewPage
from scripts.Sub07_Deconvolution_Analysis import gaussian_bell, Run_Deconvolution


class Revise_FTIR_AnalysisPage(QMainWindow):
    """
    This class generates the GUI for the main page of the AutoFTIR, where the user can load a database and 
    actually add more data, modify the current data, etc.
    """
    def __init__(self, conn, cursor, DB_Name, DB_Folder, stack, shared_data):
        # Initiate the required parameters. 
        super().__init__()
        self.conn = conn            # connection to the SQL database.
        self.cursor = cursor        # cursor for running the SQL commands. 
        self.DB_Name = DB_Name
        self.DB_Folder = DB_Folder
        self.CurrentFileList = []   # A list of the input files that need to be analyzed!
        self.CurrentFileIndex = 0   # Index of the file to be analyzed. 
        self.stack = stack
        self.shared_data = shared_data
        self.IDnumber = shared_data.data          # ID number of the binder of interest. 
        self.Columns2Fetch = [
            'Wavenumber', 'Wavenumber_shape', 'Wavenumber_dtype', 'Absorption', 'Absorption_shape', 'Absorption_dtype',
            'Carbonyl_Min_Wavenumber', 'Carbonyl_Max_Wavenumber', 
            'Sulfoxide_Min_Wavenumber', 'Sulfoxide_Max_Wavenumber', 
            'Aliphatic_Min_Wavenumber', 'Aliphatic_Max_Wavenumber', 'Normalization_Coeff',
            'Bnumber', 'Lab_Aging', 'RepNumber', 
            'Deconv_CarbonylList', 'Deconv_CarbonylList_shape', 'Deconv_CarbonylList_dtype', 
            'Deconv_SulfoxideList', 'Deconv_SulfoxideList_shape', 'Deconv_SulfoxideList_dtype', 
            'Deconv_AliphaticList', 'Deconv_AliphaticList_shape', 'Deconv_AliphaticList_dtype', 
            'Deconv_ICO', 'Deconv_ISO', 
            'Deconv_GaussianList', 'Deconv_GaussianList_shape', 'Deconv_GaussianList_dtype', 
            'ALS_Lambda', 'ALS_Ratio', 'ALS_NumIter', 'Normalization_Method', 'Normalization_Coeff',
            'RawWavenumber', 'RawWavenumber_shape', 'RawWavenumber_dtype',
            'RawAbsorbance', 'RawAbsorbance_shape', 'RawAbsorbance_dtype']
        self.PushButtonStyle = {
            "General": """
        QPushButton:enabled {
            background-color: #DCECF9; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: lightgray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:pressed {
            background-color: gray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        """, 
            "AddData" : """
        QPushButton:enabled {
            background-color: #93E9BE; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: #56C28B; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:pressed {
            background-color: gray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:checked {
            background-color: lime; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        """, 
            "Review":  """
        QPushButton:enabled {
            background-color: #F2E394; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: #E0D57D; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:pressed {
            background-color: gray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:checked {
            background-color: lime; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        """, 
            "Reject":  """
        QPushButton:enabled {
            background-color: #FA8072; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: #CC5F55; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:pressed {
            background-color: gray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:checked {
            background-color: lime; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        """, }
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
        self.Button_Sync.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Sync.setSizePolicy(self.Button_Sync.sizePolicy().Expanding, self.Button_Sync.sizePolicy().Preferred)
        # Place the labels in the GUI.
        FormLayout_Left.addRow(Label01,  self.Label_NumData)
        FormLayout_Left.addRow(Label02,  self.Label_NumValidData)
        FormLayout_Left.addRow(Label03,  self.Label_AvgNumReplicates)
        FormLayout_Right.addRow(Label04, self.Label_NumUniqueBnum)
        FormLayout_Right.addRow(Label05, self.Label_NumUniqueLabAge)
        FormLayout_Right.addRow(Label06, self.Label_NumUniqueBnumLabAge)
        Section01_Layout.addLayout(FormLayout_Left)
        Section01_Layout.addLayout(FormLayout_Right)
        Section01_Layout.addWidget(self.Button_Sync)
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
        self.Button_UpdatePreprocess.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_UpdatePreprocess.setSizePolicy(self.Button_UpdatePreprocess.sizePolicy().Expanding, 
                                                   self.Button_UpdatePreprocess.sizePolicy().Preferred)
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
        Section12_Layout.addWidget(self.Button_UpdatePreprocess)
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
        self.NumFilesProgress_bar.setValue(100)
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
        self.Button_AddData = QPushButton("Add Data to DB")
        self.Button_AddData.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_AddData.setEnabled(False)
        self.Button_AddData.setStyleSheet(self.PushButtonStyle['AddData'])
        self.Button_AddData.setSizePolicy(self.Button_AddData.sizePolicy().Expanding, 
                                          self.Button_AddData.sizePolicy().Preferred)
        Section03_Layout.addWidget(self.Button_AddData)
        # Button for review the database. 
        self.Button_ReviewDB = QPushButton("Review && Edit DB")
        self.Button_ReviewDB.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_ReviewDB.setEnabled(False)
        self.Button_ReviewDB.setStyleSheet(self.PushButtonStyle['Review'])
        self.Button_ReviewDB.setSizePolicy(self.Button_ReviewDB.sizePolicy().Expanding, 
                                           self.Button_ReviewDB.sizePolicy().Preferred)
        Section03_Layout.addWidget(self.Button_ReviewDB)
        # # Button for exporting the database to excel.
        # self.Button_ExportDB = QPushButton("Analyze DB and Export to Excel")
        # self.Button_ExportDB.setFont(QFont("Arial", 10, QFont.Bold))
        # self.Button_ExportDB.setEnabled(False)
        # self.Button_ExportDB.setStyleSheet(
        # """
        # QPushButton:hover {background-color: lightgray;}
        # QPushButton:pressed {background-color: gray;}
        # """)
        # Section03_Layout.addWidget(self.Button_ExportDB, alignment=Qt.AlignHCenter | Qt.AlignTop)
        Section03.setLayout(Section03_Layout)
        RightLayout.addWidget(Section03, 16)
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
            spinbox.setEnabled(True)
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
        self.Button_SaveProgress = QPushButton("Cencel")
        self.Button_SaveProgress.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_SaveProgress.setSizePolicy(self.Button_SaveProgress.sizePolicy().Expanding, 
                                               self.Button_SaveProgress.sizePolicy().Preferred)
        self.Button_SaveProgress.clicked.connect(self.SaveExit_Button_Function)        # Connect to a custom function
        self.Button_SaveProgress.setEnabled(True)
        Section04_Layout.addWidget(self.Button_SaveProgress)
        # Outlier specification button.
        self.Button_Outlier = QPushButton("Mark as Outlier")
        self.Button_Outlier.setStyleSheet(self.PushButtonStyle['Reject'])
        self.Button_Outlier.setSizePolicy(self.Button_Outlier.sizePolicy().Expanding, 
                                          self.Button_Outlier.sizePolicy().Preferred)
        self.Button_Outlier.clicked.connect(self.Outlier_Button_Function)  # Connect to a custom function
        self.Button_Outlier.setEnabled(True)
        Section04_Layout.addWidget(self.Button_Outlier)
        # OK button.
        self.Button_OK = QPushButton("OK && Accept")
        self.Button_OK.setStyleSheet(self.PushButtonStyle['AddData'])
        self.Button_OK.setSizePolicy(self.Button_OK.sizePolicy().Expanding, self.Button_OK.sizePolicy().Preferred)
        self.Button_OK.clicked.connect(self.OK_Button_Function)
        self.Button_OK.setEnabled(True)
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
        # # --------------------------------------------------------------------------------------------------------------
        # # Section 05: Output section. 
        # Section05 = QGroupBox("Output section (Terminal-like)")
        # Section05_Layout = QVBoxLayout()
        # self.Terminal = QPlainTextEdit(self)
        # self.Terminal.setReadOnly(True)             # Make it read-only. User shouldn't write!
        # self.Terminal.setStyleSheet("background-color: black; color: white;")
        # self.Terminal.appendPlainText(f">>> Modify the FTIR analysis for: ID={self.IDnumber}\n")
        # Section05_Layout.addWidget(self.Terminal)
        # Section05.setLayout(Section05_Layout)
        # RightLayout.addWidget(Section05, 40)
        # --------------------------------------------------------------------------------------------------------------
        # Section 07: Gaussian List. 
        Section07 = QGroupBox("Fitted Gaussians:")
        Section07_Layout = QVBoxLayout()
        self.RePlot_Button = QPushButton("Re-Plot")
        self.RePlot_Button.setStyleSheet(self.PushButtonStyle['General'])
        self.RePlot_Button.setSizePolicy(self.RePlot_Button.sizePolicy().Expanding, 
                                         self.RePlot_Button.sizePolicy().Preferred)
        self.RePlot_Button.clicked.connect(self.RePlot_Button_Function)
        self.RePlot_Button.setEnabled(True)
        self.AddNewRow_Button = QPushButton("Add row")
        self.AddNewRow_Button.setStyleSheet(self.PushButtonStyle['General'])
        self.AddNewRow_Button.setSizePolicy(self.AddNewRow_Button.sizePolicy().Expanding, 
                                            self.AddNewRow_Button.sizePolicy().Preferred)
        self.AddNewRow_Button.clicked.connect(self.AddNewRow_Button_Function)
        self.AddNewRow_Button.setEnabled(True)
        # Adding a table. 
        delegate = FloatDelegate()
        self.GL_Table = QTableWidget()
        self.GL_Table.setItemDelegate(delegate)
        self.GL_Table.setRowCount(10)
        self.GL_Table.setColumnCount(3)
        self.GL_Table.setHorizontalHeaderLabels(['Mean (cm⁻¹)', 'Std (cm⁻¹)', 'Amplitude'])
        self.GL_Table.setSelectionBehavior(self.GL_Table.SelectRows)
        self.GL_Table.setSelectionMode(self.GL_Table.SingleSelection)
        Section07_Layout.addWidget(self.RePlot_Button)
        Section07_Layout.addWidget(self.AddNewRow_Button)
        Section07_Layout.addWidget(self.GL_Table)
        Section07.setLayout(Section07_Layout)
        RightLayout.addWidget(Section07, 44)
        # --------------------------------------------------------------------------------------------------------------
        # At the very end, add the left and right layouts to the main layout.
        layout.addLayout(LeftLayout, 80)
        layout.addLayout(RightLayout, 20)
    # ------------------------------------------------------------------------------------------------------------------
    def showEvent(self, event):
        # Update label with the shared data when this stack becomes visible
        # self.data_label.setText(f"Received data: {self.shared_data.data}")
        super().showEvent(event)
        
        # Retrieve the data from the database. 
        self.cursor.execute(f"SELECT {', '.join(self.Columns2Fetch)} FROM FTIR WHERE id = ?", 
                            (self.shared_data.data,))
        row = self.cursor.fetchall()[0]
        # Extract the data. 
        self.X = Binary_to_Array(row[0], row[1], row[2])
        self.Y = Binary_to_Array(row[3], row[4], row[5])
        self.XCmin = row[6]
        self.XCmax = row[7]
        self.XSmin = row[8]
        self.XSmax = row[9]
        self.XAmin = row[10]
        self.XAmax = row[11]
        self.NormCoeff = row[12]
        self.Bnumber = row[13]
        self.LabAging = row[14]
        self.RepNumber = row[15]
        self.Carbonyl_Gaussians  = Binary_to_Array(row[16], row[17], row[18])
        self.Sulfoxide_Gaussians = Binary_to_Array(row[19], row[20], row[21])
        self.Aliphatic_Gaussians = Binary_to_Array(row[22], row[23], row[24])
        self.GaussianList        = Binary_to_Array(row[27], row[28], row[29])
        self.ALS_Lambda     = row[30]
        self.ALS_Ratio      = row[31]
        self.ALS_NumIter    = row[32]
        self.Normalization_Method = row[33]
        self.Normalization_Coeff = row[34]
        RawX = Binary_to_Array(row[35], row[36], row[37])
        RawY = Binary_to_Array(row[38], row[39], row[40])
        self.RawData = np.column_stack((RawX, RawY))
        ICO   = row[25]
        ISO   = row[26]
        # --------------------------------------------------------------------------------------------------------------
        # Adding the Fitted Gaussians to the table. 
        self.GL_Table.clearSelection()
        self.GL_Table.setRowCount(self.GaussianList.shape[0])
        for row_idx in range(self.GaussianList.shape[0]):
            for col_idx in range(3):
                item = QTableWidgetItem(f'{self.GaussianList[row_idx, col_idx]:.4e}')
                self.GL_Table.setItem(row_idx, col_idx, item)
        # --------------------------------------------------------------------------------------------------------------
        # Calculating the Areas. 
        CArea = (self.Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Carbonyl_Gaussians[:, 1])).sum()
        SArea = (self.Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (self.Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Aliphatic_Gaussians[:, 1])).sum()
        # Update the deconvolution information. 
        self.Decon_Label_CArea.setText(f'Carbonyl Area: {CArea:.2f}')
        self.Decon_Label_SArea.setText(f'Sulfoxide Area: {SArea:.2f}')
        self.Decon_Label_AArea.setText(f'Aliphatic Area: {AArea:.2f}')
        try:
            self.Decon_Label_Index.setText(f'ICO: {ICO:.4f}, ISO: {ISO:.4f}')
        except:
            self.Decon_Label_Index.setText(f'ICO: None, ISO: None')
        # --------------------------------------------------------------------------------------------------------------
        # Plotting section. 
        self.RePlotting()
        # Enable the adjustment buttons. 
        self.Button_OK.setEnabled(True)
        self.Button_Outlier.setEnabled(True)
        self.Button_SaveProgress.setEnabled(True)
        # Update the file name and remaining number of files. 
        self.Label_NumFilesProgress.setText(f"Number of selected/Remained files: 1, 0")
        self.Label_CurrentFileName.setText(f"B{self.Bnumber}_FTIR_Rep{self.RepNumber}_{self.LabAging}.dpt")
        # Update and enable the spinboxes. 
        SpinBoxValues = [self.XCmin, self.XCmax, self.XSmin, self.XSmax, self.XAmin, self.XAmax]
        SpinBoxStep = np.diff(self.X).mean()
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
        # Update the preprocessing properties. 
        self.LineEdit_ALSLambda.setText(f"{self.ALS_Lambda:.3e}")
        self.LineEdit_ALSRatio.setText(f"{self.ALS_Ratio:.6e}")
        self.LineEdit_ALSNumIter.setText(f"{self.ALS_NumIter}")
        if 'A' in self.Normalization_Method:
            self.DropDown_NormalizationMethod.setCurrentIndex(0)
        elif 'B' in self.Normalization_Method:
            self.DropDown_NormalizationMethod.setCurrentIndex(1)
        elif 'C' in self.Normalization_Method:
            self.DropDown_NormalizationMethod.setCurrentIndex(2)
        elif 'D' in self.Normalization_Method:
            self.DropDown_NormalizationMethod.setCurrentIndex(3)
        self.LineEdit_ALSLambda.setEnabled(True)
        self.LineEdit_ALSRatio.setEnabled(True)
        self.LineEdit_ALSNumIter.setEnabled(True)
        self.DropDown_NormalizationMethod.setEnabled(True)
        self.Button_UpdatePreprocess.setEnabled(True)
    # ------------------------------------------------------------------------------------------------------------------
    def RePlotting(self):
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
        # First, whole wavenumbers. 
        self.axes[0].plot(self.X, self.Y, color='k', ls='-', label='Processed data')
        self.axes[0].plot(self.RawData[:, 0], self.RawData[:, 1], color='b', ls='-', lw=0.5, label='raw data')
        self.axes[0].axvspan(xmin=1620, xmax=1800, alpha=0.1, color='r', label='Carbonyl search area')
        self.axes[0].axvspan(xmin=970,  xmax=1070, alpha=0.1, color='y', label='Sulfoxide search area')
        self.axes[0].legend()
        self.axes[0].set_xlim([2000, 600])
        # For cabonyl plot.
        CIndex = np.where((self.X >= 1600) & (self.X <= 1800))[0]
        self.XC = self.X[CIndex]
        self.YC = self.Y[CIndex]
        self.CIndex = CIndex
        self.XCminIndx = np.where(self.XC >= self.XCmin)[0][0]
        self.XCmaxIndx = np.where(self.XC <= self.XCmax)[0][-1]
        self.CIndex2 = np.arange(self.XCminIndx, self.XCmaxIndx + 1)
        self.axes[1].plot(self.X[CIndex], self.Y[CIndex], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[1].fill_between(self.XC[self.CIndex2], self.YC[self.CIndex2], 0, color='r', alpha=0.2, 
                                  label='Carbonyl Area')
        Xgaussian = np.linspace(1600, 1800, num=1000)
        for ii in range(self.Carbonyl_Gaussians.shape[0]):
            if ii == 0:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, self.Carbonyl_Gaussians[ii, 0], 
                                                           self.Carbonyl_Gaussians[ii, 1], 
                                                           self.Carbonyl_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, self.Carbonyl_Gaussians[ii, 0], 
                                                           self.Carbonyl_Gaussians[ii, 1], 
                                                           self.Carbonyl_Gaussians[ii, 2]), 
                                ls='--', lw=0.5, color='r')
        self.axes[1].legend()
        self.axes[1].invert_xaxis()
        # For Sulfoxide plot
        SIndex = np.where((self.X >= 940) & (self.X <= 1100))[0]
        self.XS = self.X[SIndex]
        self.YS = self.Y[SIndex]
        self.SIndex = SIndex
        self.XSminIndx = np.where(self.XS >= self.XSmin)[0][0]
        self.XSmaxIndx = np.where(self.XS <= self.XSmax)[0][-1]
        self.SIndex2 = np.arange(self.XSminIndx, self.XSmaxIndx + 1)
        self.axes[2].plot(self.X[SIndex], self.Y[SIndex], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[2].fill_between(self.XS[self.SIndex2], self.YS[self.SIndex2], 0, color='y', alpha=0.2, 
                                  label='Sulfoxide Area')
        Xgaussian = np.linspace(940, 1100, num=1000)
        for ii in range(self.Sulfoxide_Gaussians.shape[0]):
            if ii == 0:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, self.Sulfoxide_Gaussians[ii, 0], 
                                                           self.Sulfoxide_Gaussians[ii, 1], 
                                                           self.Sulfoxide_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, self.Sulfoxide_Gaussians[ii, 0], 
                                                           self.Sulfoxide_Gaussians[ii, 1], 
                                                           self.Sulfoxide_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r')
        self.axes[2].legend()
        self.axes[2].invert_xaxis()
        # For Aliphatic plot
        AIndex = np.where((self.X >= 1300) & (self.X <= 1600))[0]
        self.XA = self.X[AIndex]
        self.YA = self.Y[AIndex]
        self.AIndex = AIndex
        self.XAminIndx = np.where(self.XA >= self.XAmin)[0][0]
        self.XAmaxIndx = np.where(self.XA <= self.XAmax)[0][-1]
        self.AIndex2 = np.arange(self.XAminIndx, self.XAmaxIndx + 1)
        self.axes[3].plot(self.X[AIndex], self.Y[AIndex], marker='o', ms=3, color='k', ls='-', label='FTIR data')
        self.axes[3].fill_between(self.XA[self.AIndex2], self.YA[self.AIndex2], 0, color='g', alpha=0.2, 
                                  label='Aliphatic Area')
        Xgaussian = np.linspace(1300, 1600, num=1000)
        for ii in range(self.Aliphatic_Gaussians.shape[0]):
            if ii == 0:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, self.Aliphatic_Gaussians[ii, 0], 
                                                           self.Aliphatic_Gaussians[ii, 1], 
                                                           self.Aliphatic_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, self.Aliphatic_Gaussians[ii, 0], 
                                                           self.Aliphatic_Gaussians[ii, 1], 
                                                           self.Aliphatic_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r')
        self.axes[3].legend()
        self.axes[3].invert_xaxis()
        # Redraw the canvas
        self.canvas.draw()
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
        self.stack.setCurrentIndex(1)
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
        Xbinary, Xshape, Xdtype = Array_to_Binary(self.X)
        Ybinary, Yshape, Ydtype = Array_to_Binary(self.Y)
        # Convert Arrays to binary.
        Carr, Cshape, Ctype = Array_to_Binary(self.Carbonyl_Gaussians)
        Sarr, Sshape, Stype = Array_to_Binary(self.Sulfoxide_Gaussians)
        Aarr, Ashape, Atype = Array_to_Binary(self.Aliphatic_Gaussians)
        Garr, Gshape, Gtype = Array_to_Binary(self.GaussianList)
        # Recalculate the ICO and ISO indices. 
        CArea = (self.Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Carbonyl_Gaussians[:, 1])).sum()
        SArea = (self.Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (self.Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Aliphatic_Gaussians[:, 1])).sum()
        Decon_ICO = CArea / AArea
        Decon_ISO = SArea / AArea
        Update_Row_in_Database(self.conn, self.cursor, self.shared_data.data, {
            "ICO_Baseline": -1.0, "ICO_Tangential": -1.0,
            "ISO_Baseline": -1.0, "ISO_Tangential": -1.0,
            "Carbonyl_Area_Baseline": CArea_base,  "Carbonyl_Area_Tangential": CArea_tang,
            "Sulfoxide_Area_Baseline": SArea_base, "Sulfoxide_Area_Tangential": SArea_tang,
            "Aliphatic_Area_Baseline": AArea_base, "Aliphatic_Area_Tangential": AArea_tang,
            "Carbonyl_Peak_Wavenumber": -1.0,    "Sulfoxide_Peak_Wavenumber": -1.0,
            "Aliphatic_Peak_Wavenumber_1": -1.0, "Aliphatic_Peak_Wavenumber_2": -1.0,
            "Carbonyl_Peak_Absorption": -1.0,    "Sulfoxide_Peak_Absorption": -1.0,
            "Aliphatic_Peak_Absorption_1": -1.0, "Aliphatic_Peak_Absorption_2": -1.0,
            "Wavenumber": Xbinary, "Wavenumber_shape": Xshape, "Wavenumber_dtype": Xdtype,
            "Absorption": Ybinary, "Absorption_shape": Yshape, "Absorption_dtype": Ydtype,
            "Carbonyl_Min_Wavenumber": XCmin,  "Carbonyl_Max_Wavenumber": XCmax,
            "Sulfoxide_Min_Wavenumber": XSmin, "Sulfoxide_Max_Wavenumber": XSmax,
            "Aliphatic_Min_Wavenumber": XAmin, "Aliphatic_Max_Wavenumber": XAmax,
            "Decon_Carbonyl": Carr,  "Decon_Carbonyl_shape": Cshape,  "Decon_Carbonyl_dtype": Ctype,
            "Decon_Sulfoxide": Sarr, "Decon_Sulfoxide_shape": Sshape, "Decon_Sulfoxide_dtype": Stype,
            "Decon_Aliphatic": Aarr, "Decon_Aliphatic_shape": Ashape, "Decon_Aliphatic_dtype": Atype, 
            "Decon_GaussianList": Garr, "Decon_GaussianList_shape": Gshape, "Decon_GaussianList_dtype": Gtype, 
            "Decon_ICO": -1.0, "Decon_ISO": -1.0,
            "IsOutlier": 1, 
            "ALS_Lambda": self.ALS_Lambda, "ALS_Ratio": self.ALS_Ratio, "ALS_NumIter": self.ALS_NumIter,
            "Normalization_Method": self.Normalization_Method.split(" (4")[0].replace(' ', '_'), 
            "Normalization_Coeff": self.Normalization_Coeff})
        # --------------------------------------------------------------------------------------------------------------
        # Return to the stack widget 2. 
        self.stack.setCurrentIndex(1)
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
        Xbinary, Xshape, Xdtype = Array_to_Binary(self.X)
        Ybinary, Yshape, Ydtype = Array_to_Binary(self.Y)
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
        # Convert Arrays to binary.
        Carr, Cshape, Ctype = Array_to_Binary(self.Carbonyl_Gaussians)
        Sarr, Sshape, Stype = Array_to_Binary(self.Sulfoxide_Gaussians)
        Aarr, Ashape, Atype = Array_to_Binary(self.Aliphatic_Gaussians)
        Garr, Gshape, Gtype = Array_to_Binary(self.GaussianList)
        # Recalculate the ICO and ISO indices. 
        CArea = (self.Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Carbonyl_Gaussians[:, 1])).sum()
        SArea = (self.Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (self.Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Aliphatic_Gaussians[:, 1])).sum()
        Decon_ICO = CArea / AArea
        Decon_ISO = SArea / AArea
        # Append the data to the database. 
        Update_Row_in_Database(self.conn, self.cursor, self.shared_data.data, {
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
            "Carbonyl_Min_Wavenumber": XCmin,  "Carbonyl_Max_Wavenumber": XCmax,
            "Sulfoxide_Min_Wavenumber": XSmin, "Sulfoxide_Max_Wavenumber": XSmax,
            "Aliphatic_Min_Wavenumber": XAmin, "Aliphatic_Max_Wavenumber": XAmax,
            "Decon_Carbonyl": Carr,  "Decon_Carbonyl_shape": Cshape,  "Decon_Carbonyl_dtype": Ctype,
            "Decon_Sulfoxide": Sarr, "Decon_Sulfoxide_shape": Sshape, "Decon_Sulfoxide_dtype": Stype,
            "Decon_Aliphatic": Aarr, "Decon_Aliphatic_shape": Ashape, "Decon_Aliphatic_dtype": Atype, 
            "Decon_GaussianList": Garr, "Decon_GaussianList_shape": Gshape, "Decon_GaussianList_dtype": Gtype, 
            "Decon_ICO": Decon_ICO, "Decon_ISO": Decon_ISO,
            "IsOutlier": 0,
            "ALS_Lambda": self.ALS_Lambda, "ALS_Ratio": self.ALS_Ratio, "ALS_NumIter": self.ALS_NumIter,
            "Normalization_Method": self.Normalization_Method.split(" (4")[0].replace(' ', '_'), 
            "Normalization_Coeff": self.Normalization_Coeff})
        # --------------------------------------------------------------------------------------------------------------
        # Return to the stack widget 2. 
        self.stack.setCurrentIndex(1)
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
            for j in range(4):
                self.axes[j].cla()
            Titles = ['Wide range data', 'Carbonyl area', 'Sulfoxide area', 'Aliphatic area']
            for i in range(4):
                if i >= 2:
                    self.axes[i].set_xlabel('Wavenumber (1/cm)', fontsize=9, fontweight='bold', color='k')
                if i in [0, 2]:
                    self.axes[i].set_ylabel('Normalized Absorption', fontsize=9, fontweight='bold', color='k')
                self.axes[i].set_title(Titles[i], fontsize=11, fontweight='bold', color='k')
                self.axes[i].grid(which='both', color='gray', alpha=0.1)
            # Refresh the axes. 
            self.canvas.draw()
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
            # Return "True".
            return True
        # Otherwise, return False.
        return False
    # ------------------------------------------------------------------------------------------------------------------
    def RePlot_Button_Function(self):
        # First, update the Gaussian list from the table. 
        Nrows = self.GL_Table.rowCount()
        Ncols = self.GL_Table.columnCount()
        GL    = np.zeros((Nrows, Ncols), dtype=float)
        for row in range(Nrows):
            for col in range(Ncols):
                item = self.GL_Table.item(row, col)
                if item is not None:
                    try:
                        GL[row, col] = float(item.text())
                    except ValueError:
                        GL[row, col] = np.nan
        GL = GL[GL[:, -1] != 0.0]       # Remove the peaks without amplitude. 
        self.GaussianList = GL[np.argsort(GL[:, 0]), :]
        # Then, find the index of the Carbonyl, Sulfoxide, and Aliphatic peaks. 
        Aliphatic_Gaussians = self.GaussianList[(self.GaussianList[:, 0] < 1525) & (self.GaussianList[:, 0] > 1350), :]
        Aliphatic_Gaussians = Aliphatic_Gaussians[Aliphatic_Gaussians[:, 2].argsort(), :]       # Sort based on Amplitude.
        self.Aliphatic_Gaussians = Aliphatic_Gaussians[-2:, :]       # Took only the biggest peaks. 
        self.Carbonyl_Gaussians = self.GaussianList[(self.GaussianList[:, 0] < 1720) & \
                                                    (self.GaussianList[:, 0] > 1660), :]
        Sulfoxide_Gaussians = self.GaussianList[(self.GaussianList[:, 0] < 1070) & (self.GaussianList[:, 0] > 970), :]
        Index = np.argmin(np.abs(Sulfoxide_Gaussians[:, 0] - 1030))
        Index2= np.argmax(Sulfoxide_Gaussians[:, 2])
        self.Sulfoxide_Gaussians = Sulfoxide_Gaussians[[Index2], :]
        # Update the areas and indices. 
        CArea = (self.Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Carbonyl_Gaussians[:, 1])).sum()
        SArea = (self.Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (self.Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Aliphatic_Gaussians[:, 1])).sum()
        # Update the deconvolution information. 
        self.Decon_Label_CArea.setText(f'Carbonyl Area: {CArea:.2f}')
        self.Decon_Label_SArea.setText(f'Sulfoxide Area: {SArea:.2f}')
        self.Decon_Label_AArea.setText(f'Aliphatic Area: {AArea:.2f}')
        self.Decon_Label_Index.setText(f'ICO: {CArea / AArea:.4f}, ISO: {SArea / AArea:.4f}')
        # Replace the table. 
        self.GL_Table.clearSelection()
        self.GL_Table.setRowCount(self.GaussianList.shape[0])
        for row_idx in range(self.GaussianList.shape[0]):
            for col_idx in range(3):
                item = QTableWidgetItem(f'{self.GaussianList[row_idx, col_idx]:.4e}')
                self.GL_Table.setItem(row_idx, col_idx, item)
        # Now, call the function to replot. 
        self.RePlotting()
    # ------------------------------------------------------------------------------------------------------------------
    def AddNewRow_Button_Function(self):
        current_row_count = self.GL_Table.rowCount()
        self.GL_Table.insertRow(current_row_count)  # Add a new row at the end
        # Populate the new row with default values
        for column in range(self.GL_Table.columnCount()):
            self.GL_Table.setItem(current_row_count, column, QTableWidgetItem("0.0"))
    # ------------------------------------------------------------------------------------------------------------------
    def Renew_MainPlot_4Next_File(self):
        """
        This function renew and draw the main plot and prepare it for the next analysis.  
        """
        # Read the files, until a proper file achieved. 
        Data = None
        for i in range(self.CurrentFileIndex, len(self.CurrentFileList)):
            self.CurrentFileIndex = i
            # Check if the file is already exist in the database. 
            self.cursor.execute("SELECT EXISTS(SELECT 1 FROM FTIR WHERE FileName = ?)", 
                                (os.path.basename(self.CurrentFileList[i]),))
            exists = self.cursor.fetchone()[0]
            if exists:
                QMessageBox.critical(self, "File Already Existed!", 
                                     f"The file <{os.path.basename(self.CurrentFileList[i])}> was already exists "+
                                     f"in the database. Instead of reloading the file, please try to edit/modify " +
                                     f"the analysis on that specific file. Take note of B-number, Rep number, and " +
                                     f"Lab aging state, and try to use 'Edit/Modify DB button to edit this results!" + 
                                     f"'\nFile directory: {os.path.dirname(self.CurrentFileList[i])}")
                continue
            # Check the file name. 
            Bnumber, Rep, LabAging = Get_Info_From_Name(os.path.basename(self.CurrentFileList[i]))
            if Bnumber == None:
                progress = int((i + 1) / len(self.CurrentFileList) * 100)
                if progress > 100: progress = 100
                self.NumFilesProgress_bar.setValue(progress)
                self.Terminal.appendPlainText(f">>> ERROR!! File name is NOT compatible!: {self.CurrentFileList[i]}")
                QMessageBox.critical(self, "Unable to Read File!", 
                                     f"The name of the file <{os.path.basename(self.CurrentFileList[i])}> was not "+
                                     f"comparible with file name format! Please make sure to follow " +
                                     f"'BXXXX_FTIR_RepY_AGING.dpt' format, as this is the only format acceptable by " +
                                     f"the code!\nFile directory: {os.path.dirname(self.CurrentFileList[i])}")
                continue
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
            # Selected files are not matching the content, reactivate the buttons and free up the variables. 
            self.Button_AddData.setEnabled(True)
            self.Button_ReviewDB.setEnabled(True)
            # self.Button_ExportDB.setEnabled(True)
            self.CurrentFileIndex = 0
            self.CurrentFileList = []
            self.Terminal.appendPlainText("\n\n>>> Ready for new file selection!")      # Print message to user.
            self.Label_NumFilesProgress.setText(f"Number of selected files: N/A")   # reset the number of selected files
            self.NumFilesProgress_bar.setValue(0)                                   # Set progress bar to zero.
            return
        # --------------------------------------------------------------------------------------------------------------
        # Otherwise, perform the baseline adjustment and normalization.
        data = Baseline_Adjustment_ALS(Data, 1e6, 1e-2, 150)            # Baseline adjustment
        Rawdata = Data.copy()
        data, NormalizationCoeff = Normalization_Method_B(data)         # Normalization method B for now. 
        self.Normalization_Coeff = NormalizationCoeff
        X = data[:, 0]
        Y = data[:, 1] 
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
        # Plot the data. 
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
        self.ALS_Lambda = Lambda
        self.ALS_Ratio  = Ratio
        self.ALS_NumIter= NumIter
        self.Normalization_Method = self.DropDown_NormalizationMethod.currentText()
        X = data[:, 0].copy()
        Y = data[:, 1].copy()
        self.X = X
        self.Y = Y
        # --------------------------------------------------------------------------------------------------------------
        # Re-Run the deconvolution method and get the results. 
        Deconv = Run_Deconvolution(X, Y)
        self.Deconv = Deconv.copy()
        self.Carbonyl_Gaussians  = Deconv['Carbonyl_Gaussians']
        self.Sulfoxide_Gaussians = Deconv['Sulfoxide_Gaussians']
        self.Aliphatic_Gaussians = Deconv['Aliphatic_Gaussians']
        # --------------------------------------------------------------------------------------------------------------
        # Calculating the areas and ISO, ICO values. 
        CArea = (self.Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Carbonyl_Gaussians[:, 1])).sum()
        SArea = (self.Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (self.Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(self.Aliphatic_Gaussians[:, 1])).sum()
        ICO = CArea / AArea
        ISO = SArea / AArea
        # Update the deconvolution information. 
        self.Decon_Label_CArea.setText(f'Carbonyl Area: {CArea:.2f}')
        self.Decon_Label_SArea.setText(f'Sulfoxide Area: {SArea:.2f}')
        self.Decon_Label_AArea.setText(f'Aliphatic Area: {AArea:.2f}')
        try:
            self.Decon_Label_Index.setText(f'ICO: {ICO:.4f}, ISO: {ISO:.4f}')
        except:
            self.Decon_Label_Index.setText(f'ICO: None, ISO: None')
        # --------------------------------------------------------------------------------------------------------------
        # Plot the data. 
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
        for ii in range(self.Carbonyl_Gaussians.shape[0]):
            if ii == 0:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, self.Carbonyl_Gaussians[ii, 0], 
                                                           self.Carbonyl_Gaussians[ii, 1], 
                                                           self.Carbonyl_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[1].plot(Xgaussian, gaussian_bell(Xgaussian, self.Carbonyl_Gaussians[ii, 0], 
                                                           self.Carbonyl_Gaussians[ii, 1], 
                                                           self.Carbonyl_Gaussians[ii, 2]), 
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
        for ii in range(self.Sulfoxide_Gaussians.shape[0]):
            if ii == 0:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, self.Sulfoxide_Gaussians[ii, 0], 
                                                           self.Sulfoxide_Gaussians[ii, 1], 
                                                           self.Sulfoxide_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[2].plot(Xgaussian, gaussian_bell(Xgaussian, self.Sulfoxide_Gaussians[ii, 0], 
                                                           self.Sulfoxide_Gaussians[ii, 1], 
                                                           self.Sulfoxide_Gaussians[ii, 2]), 
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
        for ii in range(self.Aliphatic_Gaussians.shape[0]):
            if ii == 0:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, self.Aliphatic_Gaussians[ii, 0], 
                                                        self.Aliphatic_Gaussians[ii, 1], self.Aliphatic_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r', label='Fitted Gaussians')
            else:
                self.axes[3].plot(Xgaussian, gaussian_bell(Xgaussian, self.Aliphatic_Gaussians[ii, 0], 
                                                           self.Aliphatic_Gaussians[ii, 1], 
                                                           self.Aliphatic_Gaussians[ii, 2]), 
                                  ls='--', lw=0.5, color='r')
        self.axes[3].legend()
        self.axes[3].invert_xaxis()
        # Redraw the canvas
        self.canvas.draw()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class FloatDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        """Create an editor with a QDoubleValidator."""
        editor = super().createEditor(parent, option, index)
        if editor:
            validator = QDoubleValidator()
            validator.setNotation(QDoubleValidator.StandardNotation)
            validator.setBottom(-float('inf'))  # Minimum float value
            validator.setTop(float('inf'))      # Maximum float value
            editor.setValidator(validator)
        return editor

    def setModelData(self, editor, model, index):
        """Set the data in the model in engineering format with 6 significant digits."""
        text = editor.text()
        try:
            value = float(text)
            formatted_value = f"{value:.6e}"
            model.setData(index, formatted_value, Qt.EditRole)
        except ValueError:
            # If conversion fails, keep the current value
            pass

    def displayText(self, value, locale):
        """Display the float in engineering format with 6 significant digits."""
        try:
            float_value = float(value)
            return f"{float_value:.6e}"
        except ValueError:
            return value  # Return as is if it's not a valid float
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


if __name__ == '__main__':
    pass