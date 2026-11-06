# Title: This script include a class to design a review database page.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/25/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import re
import sys
import math
import sqlite3
import itertools
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image
from matplotlib import cm
from matplotlib.colors import to_hex, LinearSegmentedColormap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QGroupBox,
                             QHBoxLayout, QVBoxLayout, QPushButton, QWidget, QMessageBox, QLabel, QFormLayout,
                             QComboBox, QPlainTextEdit, QInputDialog, QFileDialog, QDialog, QCheckBox, QScrollArea,
                             QGridLayout)
from PyQt5.QtGui import QFont, QBrush, QColor, QFontMetrics
from PyQt5.QtCore import Qt
from scripts.Sub02_CreateNewSQLTable import Get_DB_SummaryData, Get_Identifier_Combinations
from scripts.Sub04_FTIR_Analysis_Functions import Binary_to_Array

# Define the custom cmap for the table COV colors.
Reds = cm.get_cmap('Reds', 256)             # Get the "reds" colormap.
# Clip at 0.85 to prevent excessive dark red colors.
New = Reds(np.linspace(0, 0.75, 256))
Custom_cmap = LinearSegmentedColormap.from_list("custom_reds", New)


def Get_Button_Style(Color, HoverColor):
    """
    This function generates the rounded style of the buttons in the program, for the given colors.

    :param Color: the background color of the button.
    :param HoverColor: the background color when the mouse is over the button.
    :return: the style sheet of the button.
    """
    Shape = "border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;"
    return f"""
        QPushButton:enabled {{background-color: {Color}; color: #000; {Shape}}}
        QPushButton:disabled {{background-color: #dcdcdc; color: #808080; {Shape}}}
        QPushButton:hover {{background-color: {HoverColor}; color: #000; {Shape}}}
        QPushButton:pressed {{background-color: gray; color: #000; {Shape}}}
        """


# The button styles of the popup windows, with the same meaning of the colors as on the pages of the program.
Dialog_Button_Style = {
    "General": Get_Button_Style("#DCECF9", "lightgray"),    # Neutral actions, such as Cancel, Browse, and Move Up.
    "Accept": Get_Button_Style("#93E9BE", "#56C28B"),       # Carrying out the action, such as Apply, Merge, and OK.
    "Modify": Get_Button_Style("#F2E394", "#E0D57D"),       # Changing what exists, such as Remove Selected.
}


class DB_ReviewPage(QMainWindow):
    """
    This class design a review database page in which the database is shown as table where user can select any specific 
    sample and revise its analysis procedure. 
    """

    def __init__(self, conn, cursor, DB_Name, DB_Folder, stack, shared_data):
        # Initiate the required parameters.
        super().__init__()
        self.conn = conn            # connection to the SQL database.
        self.cursor = cursor        # cursor for running the SQL commands.
        self.DB_Name = DB_Name      # Name of the database.
        self.DB_Folder = DB_Folder  # Directory at which the database is saved.
        self.stack = stack
        self.shared_data = shared_data
        # "AllColumns" is the master list of every selectable (non-BLOB) DB column, as (SQL name, display label)
        #   tuples, in the fixed order used both for display and for the "Select Columns" dialog. "id", "Bnumber",
        #   "Lab_Aging", and "RepNumber" MUST stay the first four entries: several other functions (e.g.
        #   Function_Button_Delete_Record, Check_Row_Selection) assume the selected row's id/Bnumber/Lab_Aging/
        #   RepNumber sit at fixed table columns 0-3.
        self.AllColumns = [
            ('id', 'id'), ('Bnumber', 'ID-number'), ('Lab_Aging', 'Lab Aging'), ('RepNumber', 'Rep #'),
            ('Deconv_ICO', 'ICO (Decon)'), ('Deconv_ISO', 'ISO (Decon)'),
            ('ICO_Baseline', 'ICO (base)'), ('ICO_Tangential', 'ICO (tang)'),
            ('ISO_Baseline', 'ISO (base)'), ('ISO_Tangential', 'ISO (tang)'),
            ('Carbonyl_Peak_Wavenumber', 'Carbonyl Peak loc (1/cm)'),
            ('Sulfoxide_Peak_Wavenumber', 'Sulfoxide Peak loc (1/cm)'),
            ('Aliphatic_Peak_Wavenumber_1', 'Aliphatic Peak loc 1 (1/cm)'),
            ('Aliphatic_Peak_Wavenumber_2', 'Aliphatic Peak loc 2 (1/cm)'),
            ('Carbonyl_Peak_Absorption', 'Carbonyl Peak val'), ('Sulfoxide_Peak_Absorption', 'Sulfoxide Peak val'),
            ('Aliphatic_Peak_Absorption_1', 'Aliphatic Peak val 1'),
            ('Aliphatic_Peak_Absorption_2', 'Aliphatic Peak val 2'),
            ('Carbonyl_Area_Baseline', 'Carbonyl Area (base)'), ('Sulfoxide_Area_Baseline', 'Sulfoxide Area (base)'),
            ('Aliphatic_Area_Baseline', 'Aliphatic Area (base)'),
            ('Carbonyl_Area_Tangential', 'Carbonyl Area (tang)'),
            ('Sulfoxide_Area_Tangential', 'Sulfoxide Area (tang)'),
            ('Aliphatic_Area_Tangential', 'Aliphatic Area (tang)'),
            ('Carbonyl_Min_Wavenumber', 'Carbonyl Xmin'), ('Carbonyl_Max_Wavenumber', 'Carbonyl Xmax'),
            ('Sulfoxide_Min_Wavenumber', 'Sulfoxide Xmin'), ('Sulfoxide_Max_Wavenumber', 'Sulfoxide Xmax'),
            ('Aliphatic_Min_Wavenumber', 'Aliphatic Xmin'), ('Aliphatic_Max_Wavenumber', 'Aliphatic Xmax'),
            ('FileName', 'File Name'), ('FileDirectory', 'File Directory'), ('IsOutlier', 'Is Outlier?'),
            ('Baseline_Adjustment_Method', 'Baseline Method'),
            ('ALS_Lambda', 'ALS λ'), ('ALS_Ratio', 'ALS ρ'), ('ALS_NumIter', 'ALS N Iter'),
            ('Normalization_Method', 'Normalization Method'), ('Normalization_Coeff', 'Normalization Coeff'),
            ('Rheo_HTPG', 'HTPG (Rheo)'), ('Rheo_HTPG_Std', 'HTPG Std (Rheo)'),
            ('Rheo_LTPG', 'LTPG (Rheo)'), ('Rheo_LTPG_Std', 'LTPG Std (Rheo)'),
            ('Rheo_CTOD', 'CTOD (Rheo)'), ('Rheo_CTOD_Std', 'CTOD Std (Rheo)'),
            ('Rheo_DeltaTc', 'ΔTc (Rheo)'), ('Rheo_DeltaTc_Std', 'ΔTc Std (Rheo)'),
            ('Rheo_GStar', '|G*| (Rheo)'), ('Rheo_GStar_Std', '|G*| Std (Rheo)'),
            ('Rheo_PhaseAngle', 'Phase Angle (Rheo)'), ('Rheo_PhaseAngle_Std', 'Phase Angle Std (Rheo)'),
            ('Rheo_S_m30', 'S at -30 (Rheo)'), ('Rheo_S_m30_Std', 'S at -30 Std (Rheo)'),
            ('Rheo_m_m30', 'm at -30 (Rheo)'), ('Rheo_m_m30_Std', 'm at -30 Std (Rheo)'),
            ('Rheo_InDomain', 'In Domain (Rheo)'), ('Rheo_AxisScale', 'Axis Scale (Rheo)'),
            ('Rheo_AxisCorrected', 'Axis Corrected (Rheo)'), ('Rheo_ModelVersion', 'Model Version (Rheo)'),
            ('SBS_Result', 'SBS Result'), ('SBS_Probability', 'SBS Probability'),
            ('SBS_Rh699', 'Rh699 (SBS)'), ('SBS_Rh1', 'Rh1 (SBS)'), ('SBS_Ra1', 'Ra1 (SBS)'), ('SBS_Ra2', 'Ra2 (SBS)'),
            ('SBS_Warnings', 'Warnings (SBS)'), ('SBS_ModelVersion', 'Model Version (SBS)')]
        # Columns the user is not allowed to hide from the "Select Columns" dialog.
        self.AlwaysShownSQL = ['id', 'Bnumber', 'Lab_Aging', 'RepNumber']
        # Default columns shown when the page is first created.
        DefaultSQL = ['id', 'Bnumber', 'Lab_Aging', 'RepNumber', 'Deconv_ICO', 'Deconv_ISO',
                      'ICO_Baseline', 'ISO_Baseline',
                      'Carbonyl_Peak_Wavenumber', 'Sulfoxide_Peak_Wavenumber',
                      'Aliphatic_Peak_Wavenumber_1', 'Aliphatic_Peak_Wavenumber_2']
        self.SQL_ColumnNames = [SQLName for SQLName, _ in self.AllColumns if SQLName in DefaultSQL]
        self.ColumnNames = [Label for SQLName, Label in self.AllColumns if SQLName in DefaultSQL]
        # These two parallel lists define which raw FTIR columns get aggregated into "FTIR_Analysis_DB", and their
        #   display labels. They are the single source of truth for both "Rerun_Database_Analysis" (which builds the
        #   table) and "AllColumnsAnalysis" below (which the Analysis-panel "Select Columns" dialog is built from),
        #   so the two can never drift out of sync.
        self.AnalysisSourceColumns = [
            'id', 'Bnumber', 'Lab_Aging', 'RepNumber', 'IsOutlier',
            'Deconv_ICO', 'Deconv_ISO',
            'ICO_Baseline', 'ISO_Baseline',
            'Carbonyl_Area_Baseline', 'Sulfoxide_Area_Baseline', 'Aliphatic_Area_Baseline',
            'ICO_Tangential', 'ISO_Tangential',
            'Carbonyl_Area_Tangential', 'Sulfoxide_Area_Tangential', 'Aliphatic_Area_Tangential',
            'Carbonyl_Peak_Wavenumber', 'Sulfoxide_Peak_Wavenumber',
            'Aliphatic_Peak_Wavenumber_1', 'Aliphatic_Peak_Wavenumber_2',
            'Carbonyl_Peak_Absorption', 'Sulfoxide_Peak_Absorption',
            'Aliphatic_Peak_Absorption_1', 'Aliphatic_Peak_Absorption_2',
            'Carbonyl_Min_Wavenumber', 'Carbonyl_Max_Wavenumber',
            'Sulfoxide_Min_Wavenumber', 'Sulfoxide_Max_Wavenumber',
            'Aliphatic_Min_Wavenumber', 'Aliphatic_Max_Wavenumber']
        self.AnalysisSourceLabels = [
            'DB id', 'ID-number', 'Laboratory Aging', 'Repetition Number', 'Is Outlier?',
            'ICO (deconvolution)', 'ISO (deconvolution)',
            'ICO (baseline integration)', 'ISO (baseline integration)',
            'Carbonyl Area (baseline integration)', 'Sulfoxide Area (baseline integration)',
            'Aliphatic Area (baseline integration)',
            'ICO (tangential integration)', 'ISO (tangential integration)',
            'Carbonyl Area (tangential integration)', 'Sulfoxide Area (tangential integration)',
            'Aliphatic Area (tangential integration)',
            'Carbonyl Peak Wavenumber (cm⁻¹)', 'Sulfoxide Peak Wavenumber (cm⁻¹)',
            'Aliphatic Peak Wavenumber 1 (cm⁻¹)', 'Aliphatic Peak Wavenumber 2 (cm⁻¹)',
            'Carbonyl Peak Absorption', 'Sulfoxide Peak Absorption',
            'Aliphatic Peak Absorption 1', 'Aliphatic Peak Absorption 2',
            'Carbonyl Min Wavenumber', 'Carbonyl Max Wavenumber',
            'Sulfoxide Min Wavenumber', 'Sulfoxide Max Wavenumber',
            'Aliphatic Min Wavenumber', 'Aliphatic Max Wavenumber']
        # Every column that actually exists in "FTIR_Analysis_DB": 'ID-number', 'Laboratory Aging', 'Number of Data',
        #   plus Mean/Std/COV/Min/Max/Data for each of the 26 aggregated metrics above (159 columns total; none are
        #   BLOB, since this table only ever stores aggregated numbers and pipe-delimited strings of the raw values).
        #   For this table the SQL column name and the display label are identical, unlike "AllColumns" above.
        AnalysisColumnNames = ['ID-number', 'Laboratory Aging', 'Number of Data']
        for lbl in self.AnalysisSourceLabels[5:]:
            for metric in ['Mean of ', 'Std of ', 'COV of ', 'Min of ', 'Max of ']:
                AnalysisColumnNames.append(metric + lbl)
            AnalysisColumnNames.append(lbl + ' Data')
        self.AllColumnsAnalysis = [(name, name) for name in AnalysisColumnNames]
        self.AlwaysShownAnalysisSQL = ['ID-number', 'Laboratory Aging', 'Number of Data']
        # Default columns shown on the Analysis Results table.
        self.ColumnNamesAnalysis = [
            'ID-number', 'Laboratory Aging', 'Number of Data',
            'Mean of ICO (deconvolution)', 'Std of ICO (deconvolution)', 'COV of ICO (deconvolution)',
            'Mean of ICO (baseline integration)', 'Std of ICO (baseline integration)',
            'COV of ICO (baseline integration)',
            'Mean of ICO (tangential integration)', 'Std of ICO (tangential integration)',
            'COV of ICO (tangential integration)',
            'Mean of ISO (deconvolution)', 'Std of ISO (deconvolution)', 'COV of ISO (deconvolution)',
            'Mean of ISO (baseline integration)', 'Std of ISO (baseline integration)',
            'COV of ISO (baseline integration)',
            'Mean of ISO (tangential integration)', 'Std of ISO (tangential integration)',
            'COV of ISO (tangential integration)',
            'Mean of Aliphatic Area (baseline integration)', 'Std of Aliphatic Area (baseline integration)',
            'COV of Aliphatic Area (baseline integration)',
            'Mean of Aliphatic Area (tangential integration)', 'Std of Aliphatic Area (tangential integration)',
            'COV of Aliphatic Area (tangential integration)',
            'Mean of Carbonyl Peak Wavenumber (cm⁻¹)', 'Std of Carbonyl Peak Wavenumber (cm⁻¹)',
            'COV of Carbonyl Peak Wavenumber (cm⁻¹)',
            'Mean of Sulfoxide Peak Wavenumber (cm⁻¹)', 'Std of Sulfoxide Peak Wavenumber (cm⁻¹)',
            'COV of Sulfoxide Peak Wavenumber (cm⁻¹)',
            'Mean of Carbonyl Peak Absorption', 'Std of Carbonyl Peak Absorption',
            'COV of Carbonyl Peak Absorption',
            'Mean of Sulfoxide Peak Absorption', 'Std of Sulfoxide Peak Absorption',
            'COV of Sulfoxide Peak Absorption',]
        # Tracks which of the two views (Database vs. Analysis Results) the table is currently showing, since both
        #   views share the same table/filter widgets but use different columns and query targets.
        self.InAnalysisView = False
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
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
            "Export" : """
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
            "Delete":  """
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
        """, 
            "Modify": """
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
        """, }
        self.initUI()
    # ------------------------------------------------------------------------------------------------------------------
    def initUI(self):
        # # Initiate the user interface.
        # self.setWindowTitle(f"AutoFTIR (version 1.0) | Database name: {self.DB_Name}")
        # self.setFixedSize(1500, 900)
        # Main widget and layout
        main_widget = QWidget()
        # Make a horizontal layout.
        layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)
        # self.setStyleSheet("background-color: #f0f0f0;")
        # Generate the left and right layouts, where left one include summay info and plots, and right one include the
        #   buttons, adjustments, and controls.
        LeftLayout = QVBoxLayout()
        RightLayout = QVBoxLayout()
        # --------------------------------------------------------------------------------------------------------------
        # Section 1: summary information.
        SummaryData = Get_DB_SummaryData(self.cursor)
        Section01 = QGroupBox("Summary Information")
        Section01.setStyleSheet("QGroupBox { font-weight: bold; }")
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
        LeftLayout.addWidget(Section01, 10)
        # --------------------------------------------------------------------------------------------------------------
        # Section 02: Table to show the records.
        Section02 = QGroupBox("Show Database")
        Section02.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section02_Layout = QVBoxLayout()
        # Adding one label to show the number of fetched data.
        self.Label_NumFetchedRows = QLabel('Number of fetched data (rows): 0')
        # Create the table
        self.Table = QTableWidget()
        self.Table.setRowCount(10)
        self.Table.setColumnCount(len(self.ColumnNames))
        self.Table.setHorizontalHeaderLabels(self.ColumnNames)
        self.Table.setSelectionBehavior(self.Table.SelectRows)
        self.Table.setSelectionMode(self.Table.SingleSelection)
        # Clicking a column header sorts the rows by that column, and clicking it again reverses the order.
        self.Reset_Table_Sort()
        self.Table.setSortingEnabled(True)
        self.Fit_Columns_To_Content()
        # Placing the table in the window.
        Section02_Layout.addWidget(self.Label_NumFetchedRows)
        Section02_Layout.addWidget(self.Table)
        Section02.setLayout(Section02_Layout)
        LeftLayout.addWidget(Section02, 90)
        # --------------------------------------------------------------------------------------------------------------
        # Section 3: filtering the database results.
        Section03 = QGroupBox("Filtering Options")
        Section03.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section03_Layout = QVBoxLayout()
        # First, dropdown for the B-numbers.
        Label_DropDown01 = QLabel("Select the asphalt binder B-number:")
        self.DropDown_Bnumber = QComboBox()
        self.DropDown_Bnumber.addItems(['Please Select...', 'All binders'] +
                                       list(self.IdentifierCombs['Bnumber'].unique()))
        self.DropDown_Bnumber.currentIndexChanged.connect(
            self.Function_DropDown_Bnumber)
        # Second dropdown for the Laboratory aging state.
        Label_DropDown02 = QLabel("Select the laboratory aging level:")
        self.DropDown_LabAging = QComboBox()
        self.DropDown_LabAging.addItems(['All Aging Levels'])
        self.DropDown_LabAging.setEnabled(False)
        self.DropDown_LabAging.currentIndexChanged.connect(
            self.Function_DropDown_LabAging)
        # Finally, add the apply button.
        self.Button_Fetch = QPushButton("Fetch data")
        self.Button_Fetch.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Fetch.setSizePolicy(self.Button_Fetch.sizePolicy().Expanding, 
                                        self.Button_Fetch.sizePolicy().Preferred)
        self.Button_Fetch.clicked.connect(self.Function_Button_Fetch)
        # Place the items in the window.
        Section03_Layout.addWidget(Label_DropDown01)
        Section03_Layout.addWidget(self.DropDown_Bnumber)
        Section03_Layout.addWidget(Label_DropDown02)
        Section03_Layout.addWidget(self.DropDown_LabAging)
        Section03_Layout.addWidget(self.Button_Fetch)
        Section03.setLayout(Section03_Layout)
        RightLayout.addWidget(Section03, 20)
        # --------------------------------------------------------------------------------------------------------------
        # Section 04:
        Section04 = QGroupBox("Operation")
        Section04.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section04_Layout = QVBoxLayout()
        # First button for the modification of the current selection.
        self.Button_Modify = QPushButton("Modify Selected Record")
        self.Button_Modify.setStyleSheet(self.PushButtonStyle['Modify'])
        self.Button_Modify.clicked.connect(self.Function_Button_Modify)
        self.Button_Modify.setSizePolicy(self.Button_Modify.sizePolicy().Expanding, 
                                         self.Button_Modify.sizePolicy().Preferred)
        # Second button to change the view to Analysis of DB results.
        self.Button_Analysis = QPushButton("Analysis Results Page")
        self.Button_Analysis.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Analysis.clicked.connect(self.Function_Button_Analysis)
        self.Button_Analysis.setSizePolicy(self.Button_Analysis.sizePolicy().Expanding, 
                                           self.Button_Analysis.sizePolicy().Preferred)
        # Next button for going back to the previous page.
        self.Button_Go2Main = QPushButton("Main Page")
        self.Button_Go2Main.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Go2Main.clicked.connect(self.Function_Button_Go2Main)
        self.Button_Go2Main.setSizePolicy(self.Button_Go2Main.sizePolicy().Expanding, 
                                          self.Button_Go2Main.sizePolicy().Preferred)
        # Next button for Exporting an individual record.
        self.Button_Export_Record = QPushButton("Export Individual Record")
        self.Button_Export_Record.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_Export_Record.clicked.connect(self.Function_Button_Export_Individual)
        self.Button_Export_Record.setSizePolicy(self.Button_Export_Record.sizePolicy().Expanding, 
                                                self.Button_Export_Record.sizePolicy().Preferred)
        # Next button for Exporting the whole database (summary).
        self.Button_Export_Database = QPushButton("Export Database (Summary)")
        self.Button_Export_Database.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_Export_Database.clicked.connect(self.Function_Button_Export_Database)
        self.Button_Export_Database.setSizePolicy(self.Button_Export_Database.sizePolicy().Expanding, 
                                                  self.Button_Export_Database.sizePolicy().Preferred)
        # Next button for Exporting the database.
        self.Button_Export_Analysis = QPushButton("Export Database (Combined)")
        self.Button_Export_Analysis.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_Export_Analysis.clicked.connect(self.Function_Button_Export_Database_Combined)
        self.Button_Export_Analysis.setSizePolicy(self.Button_Export_Analysis.sizePolicy().Expanding, 
                                                  self.Button_Export_Analysis.sizePolicy().Preferred)
        # Next button for Deleting a record.
        self.Button_Delete_Record = QPushButton("Delete Selected Record")
        self.Button_Delete_Record.setStyleSheet(self.PushButtonStyle['Delete'])
        self.Button_Delete_Record.clicked.connect(self.Function_Button_Delete_Record)
        self.Button_Delete_Record.setSizePolicy(self.Button_Delete_Record.sizePolicy().Expanding, 
                                                self.Button_Delete_Record.sizePolicy().Preferred)
        # Placement of the buttons.
        Section04_Layout.addWidget(self.Button_Modify)
        Section04_Layout.addWidget(self.Button_Delete_Record)
        Section04_Layout.addWidget(self.Button_Export_Record)
        Section04_Layout.addWidget(self.Button_Export_Database)
        Section04_Layout.addWidget(self.Button_Export_Analysis)
        Section04_Layout.addWidget(self.Button_Analysis)
        Section04_Layout.addWidget(self.Button_Go2Main)
        Section04.setLayout(Section04_Layout)
        RightLayout.addWidget(Section04, 35)
        # --------------------------------------------------------------------------------------------------------------
        # Section 04: Output section.
        Section05 = QGroupBox("Output section (Terminal-like)")
        Section05.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section05_Layout = QVBoxLayout()
        self.Terminal = QPlainTextEdit(self)
        # Make it read-only. User shouldn't write!
        self.Terminal.setReadOnly(True)
        self.Terminal.setStyleSheet("background-color: black; color: white;")
        self.Terminal.appendPlainText(">>> Review_Database_Results()\n")
        Section05_Layout.addWidget(self.Terminal)
        Section05.setLayout(Section05_Layout)
        RightLayout.addWidget(Section05, 45)
        # --------------------------------------------------------------------------------------------------------------
        # Final placement of the right and left layouts.
        layout.addLayout(LeftLayout, 70)
        layout.addLayout(RightLayout, 30)
    # ------------------------------------------------------------------------------------------------------------------
    def showEvent(self, event):
        # Refresh the identifier combinations and the B-number/Lab-Aging filter dropdowns' available options
        #   whenever this page becomes visible, since records may have been added elsewhere since it was last
        #   shown. (This was previously named "ShowEvent", capital S, which Qt never actually calls -- it was dead
        #   code, and even if it had fired it would not have repopulated the dropdown widgets' own item lists, only
        #   the backing "self.IdentifierCombs" DataFrame, so newly added B-numbers/aging levels never showed up in
        #   the dropdowns without restarting the program.)
        super().showEvent(event)
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
        self.Refresh_Filter_Dropdowns()
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh_Filter_Dropdowns(self):
        """
        Repopulates the B-number/Lab-Aging filter dropdowns from the latest "self.IdentifierCombs" (just refreshed
        in "showEvent"), so B-numbers/aging levels added to the database after this page was first built actually
        show up. Preserves the current selection (by text) where it is still valid, and leaves any already-fetched
        table content untouched (signals are blocked throughout, so this never triggers
        "Function_DropDown_Bnumber"/"Function_DropDown_LabAging"'s own table-resetting logic). Shared by both the
        Database and Analysis Results views, since both filter on the same underlying B-numbers/aging levels.
        """
        CurrentBnumber = self.DropDown_Bnumber.currentText()
        CurrentLabAging = self.DropDown_LabAging.currentText()
        self.DropDown_Bnumber.blockSignals(True)
        self.DropDown_Bnumber.clear()
        self.DropDown_Bnumber.addItems(['Please Select...', 'All binders'] +
                                       list(self.IdentifierCombs['Bnumber'].unique()))
        BIdx = self.DropDown_Bnumber.findText(CurrentBnumber)
        self.DropDown_Bnumber.setCurrentIndex(BIdx if BIdx >= 0 else 0)
        self.DropDown_Bnumber.blockSignals(False)
        self.DropDown_LabAging.blockSignals(True)
        if self.DropDown_Bnumber.currentIndex() <= 0:
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'])
            self.DropDown_LabAging.setEnabled(False)
        elif self.DropDown_Bnumber.currentIndex() == 1:
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'] + list(self.IdentifierCombs['Lab_Aging'].unique()))
            self.DropDown_LabAging.setEnabled(True)
        else:
            Bnumber = self.DropDown_Bnumber.currentText()
            TempDF = self.IdentifierCombs[self.IdentifierCombs['Bnumber'] == Bnumber]
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'] + list(TempDF['Lab_Aging'].unique()))
            self.DropDown_LabAging.setEnabled(True)
        LIdx = self.DropDown_LabAging.findText(CurrentLabAging)
        self.DropDown_LabAging.setCurrentIndex(LIdx if LIdx >= 0 else 0)
        self.DropDown_LabAging.blockSignals(False)
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh_After_Identifier_Change(self):
        """
        Updates this page after B-numbers or aging levels were changed in the database. The aggregated
        "FTIR_Analysis_DB" table, if available, is rebuilt without asking, since it stores these values and would
        otherwise stop matching the filter dropdowns. Then, the dropdowns, summary, and currently shown table are
        refreshed. The table is emptied if the filtered B-number no longer exists.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='FTIR_Analysis_DB'")
        if self.cursor.fetchone() is not None:
            try:
                self.Rerun_Database_Analysis(AskUser=False)
            except Exception as Err:
                QMessageBox.warning(self, "Analysis Not Updated!",
                                    f"The records were changed, but updating the aggregated analysis failed, so it "
                                    f"still shows the previous values.\n\n{Err}")
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
        self.Refresh_Filter_Dropdowns()
        self.Sync_Summary_Info()
        if self.DropDown_Bnumber.currentIndex() > 0:
            self.Function_Button_Fetch()
        elif self.InAnalysisView:
            self.cursor.execute(
                f"SELECT {', '.join([f'[{col}]' for col in self.ColumnNamesAnalysis])} FROM FTIR_Analysis_DB")
            self.Populate_Analysis_Table(self.cursor.fetchall())
        else:
            self.Reset_Table_Empty()
    # ------------------------------------------------------------------------------------------------------------------
    # Define the functions.
    def Sync_Summary_Info(self):
        # Get the latest summary information.
        SummaryData = Get_DB_SummaryData(self.cursor)
        # Update the values.
        self.Label_NumData.setText(f'{SummaryData["NumRows"]}')
        self.Label_NumValidData.setText(f'{SummaryData["NumValidRows"]}')
        self.Label_AvgNumReplicates.setText(f'{SummaryData["AvgNumRep"]:.1f}')
        self.Label_NumUniqueBnum.setText(f'{SummaryData["NumUniqueBnumber"]}')
        self.Label_NumUniqueLabAge.setText(
            f'{SummaryData["NumUniqueLabAging"]}')
        self.Label_NumUniqueBnumLabAge.setText(
            f'{SummaryData["NumUniqueBnumLabAge"]}')
        # Return Nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_Bnumber(self):
        # First, empty the table.
        self.Reset_Table_Empty()
        # Determine the state of the LabAging dropdown menu.
        if self.DropDown_Bnumber.currentIndex() == 0:
            # "Please select..." is selected.
            self.DropDown_LabAging.setEnabled(False)
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'])
        elif self.DropDown_Bnumber.currentIndex() == 1:
            # "All binders" is selected.
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(
                ['All Aging Levels'] + list(self.IdentifierCombs['Lab_Aging'].unique()))
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(True)
        else:
            # A specific B-number was selected.
            Bnumber = self.DropDown_Bnumber.currentText()
            TempDF = self.IdentifierCombs[self.IdentifierCombs['Bnumber'] == Bnumber]
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(
                ['All Aging Levels'] + list(TempDF['Lab_Aging'].unique()))
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(True)
        # Return nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_LabAging(self):
        # Empty the table.
        self.Reset_Table_Empty()
    # ------------------------------------------------------------------------------------------------------------------
    def Reset_Table_Empty(self):
        """
        Reset the table to its empty (10 blank rows) state, using whichever set of column headers is currently
        appropriate: the Database review columns, or the Analysis Results columns.
        """
        Columns = self.ColumnNamesAnalysis if self.InAnalysisView else self.ColumnNames
        self.Table.setSortingEnabled(False)
        self.Table.clearSelection()
        self.Label_NumFetchedRows.setText('Number of fetched data (rows): 0')
        self.Table.setColumnCount(len(Columns))
        self.Table.setHorizontalHeaderLabels(Columns)
        self.Table.setRowCount(10)
        for row_idx in range(10):
            for col_idx in range(len(Columns)):
                self.Table.setItem(row_idx, col_idx, SortableTableItem('', None))
        self.Table.setSortingEnabled(True)
        self.Fit_Columns_To_Content()
    # ------------------------------------------------------------------------------------------------------------------
    def Reset_Table_Sort(self):
        """
        Clears the sorted column, so the rows show in the order they were fetched. This is needed whenever the table's
        columns change, since the sorted column is remembered by its position only.
        """
        self.Table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
    # ------------------------------------------------------------------------------------------------------------------
    def Fit_Columns_To_Content(self, MaxColumnWidth=400):
        """
        Auto-fit every column's width to its header/content, so a header is never clipped and a column is never
        needlessly wide, capped at "MaxColumnWidth" so a single very long cell (e.g. a raw "... Data" column of
        pipe-delimited values on the Analysis panel) can't blow out the whole table's width.
        """
        self.Table.resizeColumnsToContents()
        Header = self.Table.horizontalHeader()
        for col in range(self.Table.columnCount()):
            if Header.sectionSize(col) > MaxColumnWidth:
                Header.resizeSection(col, MaxColumnWidth)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Fetch(self):
        # Dispatch to the Analysis-specific fetch when the Analysis Results view is currently showing.
        if self.InAnalysisView:
            self.Function_Button_Fetch_Analysis()
            return
        # First, read the filters.
        self.Table.clearSelection()
        Bnumber = self.DropDown_Bnumber.currentText()
        LabAging = self.DropDown_LabAging.currentText()
        if self.DropDown_Bnumber.currentIndex() == 0:
            return
        elif self.DropDown_Bnumber.currentIndex() == 1:         # For all binders.
            if self.DropDown_LabAging.currentIndex() == 0:    # For all aging levels.
                self.cursor.execute(
                    f"SELECT {', '.join(self.SQL_ColumnNames)} FROM FTIR")
            else:
                self.cursor.execute(f"SELECT {', '.join(self.SQL_ColumnNames)} FROM FTIR WHERE Lab_Aging = ?",
                                    (LabAging,))
        else:       # For a specific binder.
            if self.DropDown_LabAging.currentIndex() == 0:    # for all aging levels.
                self.cursor.execute(f"SELECT {', '.join(self.SQL_ColumnNames)} FROM FTIR WHERE Bnumber = ?",
                                    (Bnumber,))
            else:
                self.cursor.execute(f"SELECT {', '.join(self.SQL_ColumnNames)} FROM FTIR " +
                                    f"WHERE Bnumber = ? AND Lab_Aging = ?", (Bnumber, LabAging))
        # Get the rows.
        Rows = self.cursor.fetchall()
        # Modify the table with the row value. Sorting is off while filling, since it would move the rows meanwhile.
        #   Turning it back on re-applies the current sorted column, if any.
        self.Label_NumFetchedRows.setText(
            f'Number of fetched data (rows): {len(Rows)}')
        self.Table.setSortingEnabled(False)
        self.Table.setRowCount(len(Rows))
        for row_idx, row_data in enumerate(Rows):
            for col_idx, cell_data in enumerate(row_data):
                if type(cell_data) == float:
                    item = SortableTableItem(f'{cell_data:.4f}', cell_data)
                else:
                    item = SortableTableItem(str(cell_data), cell_data)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.Table.setItem(row_idx, col_idx, item)
        self.Table.setSortingEnabled(True)
        self.Fit_Columns_To_Content()
        # Print the selection to the terminal.
        Msg = f'>>> "{len(Rows)}" rows found in the Database, for:\n>>>\tBnumber: {Bnumber}\n>>>\tAging: {LabAging}'
        self.Terminal.appendPlainText(Msg)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Fetch_Analysis(self):
        """
        This function filters the aggregated "FTIR_Analysis_DB" table by the selected B-number and/or laboratory aging
        level, mirroring "Function_Button_Fetch" (which does the same for the raw Database view).
        """
        self.Table.clearSelection()
        Bnumber = self.DropDown_Bnumber.currentText()
        LabAging = self.DropDown_LabAging.currentText()
        ColSelect = ', '.join([f'[{col}]' for col in self.ColumnNamesAnalysis])
        if self.DropDown_Bnumber.currentIndex() == 0:
            return
        elif self.DropDown_Bnumber.currentIndex() == 1:         # For all binders.
            if self.DropDown_LabAging.currentIndex() == 0:    # For all aging levels.
                self.cursor.execute(f"SELECT {ColSelect} FROM FTIR_Analysis_DB")
            else:
                self.cursor.execute(f"SELECT {ColSelect} FROM FTIR_Analysis_DB WHERE [Laboratory Aging] = ?",
                                    (LabAging,))
        else:       # For a specific binder.
            if self.DropDown_LabAging.currentIndex() == 0:    # for all aging levels.
                self.cursor.execute(f"SELECT {ColSelect} FROM FTIR_Analysis_DB WHERE [ID-number] = ?",
                                    (Bnumber,))
            else:
                self.cursor.execute(f"SELECT {ColSelect} FROM FTIR_Analysis_DB " +
                                    f"WHERE [ID-number] = ? AND [Laboratory Aging] = ?", (Bnumber, LabAging))
        # Get the rows and fill the table.
        Rows = self.cursor.fetchall()
        self.Populate_Analysis_Table(Rows)
        # Print the selection to the terminal.
        Msg = (f'>>> "{len(Rows)}" rows found in the Analysis DB, for:\n>>>\tBnumber: {Bnumber}\n' +
               f'>>>\tAging: {LabAging}')
        self.Terminal.appendPlainText(Msg)
    # ------------------------------------------------------------------------------------------------------------------
    def Populate_Analysis_Table(self, Rows):
        """
        Fill self.Table with the given rows from FTIR_Analysis_DB, using self.ColumnNamesAnalysis as the headers, with
        the COV columns colorized based on their value.
        """
        self.Table.setSortingEnabled(False)
        self.Table.clearContents()
        self.Table.clearSelection()
        self.Table.setColumnCount(len(self.ColumnNamesAnalysis))
        self.Table.setHorizontalHeaderLabels(self.ColumnNamesAnalysis)
        self.Table.setRowCount(len(Rows))
        for row_idx, row_data in enumerate(Rows):
            for col_idx, cell_data in enumerate(row_data):
                # Identify COV columns by name (not a fixed index), since the user can now select an arbitrary
                #   subset/order of columns via the "Select Columns" dialog.
                if self.ColumnNamesAnalysis[col_idx].startswith('COV of '):
                    try:
                        item = SortableTableItem(f'{cell_data*100:.1f}%', cell_data)
                        ColorNumber = Get_Color_4_COV(cell_data)
                        item.setBackground(QBrush(QColor(ColorNumber)))
                    except:
                        item = SortableTableItem('None', None)
                elif type(cell_data) == float:
                    item = SortableTableItem(f'{cell_data:.4f}', cell_data)
                else:
                    item = SortableTableItem(str(cell_data), cell_data)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.Table.setItem(row_idx, col_idx, item)
        self.Table.setSortingEnabled(True)
        self.Fit_Columns_To_Content()
        self.Label_NumFetchedRows.setText(f'Number of fetched data (rows): {len(Rows)}')
    # ------------------------------------------------------------------------------------------------------------------
    def Open_Column_Selector_Dialog(self):
        """
        This function opens the "Select Columns" dialog for the Database table (triggered from the "Edit" menu), and
        applies the user's selection: it updates the table's headers/columns, then either re-fetches the currently
        filtered rows, or resets to the empty state, so the table always reflects the previous selection/filter.
        """
        # Do not allow this while the "Analysis Results" view is showing, since it uses a different, unrelated set of
        #   columns on the same table.
        if self.InAnalysisView:
            QMessageBox.information(self, "Switch to Database View",
                                    'Please switch back to the Database view (click "Database Page") before ' +
                                    'selecting columns for the review table.')
            return
        # Open the dialog, seeded with the currently selected columns.
        # The rheology and SBS columns are only offered if this database has them.
        self.cursor.execute("PRAGMA table_info(FTIR)")
        Available = [Row[1].lower() for Row in self.cursor.fetchall()]
        Offered = [Column for Column in self.AllColumns
                   if (not Column[0].startswith(('Rheo_', 'SBS_'))) or Column[0].lower() in Available]
        Dialog = SelectColumnsDialog(Offered, self.AlwaysShownSQL, self.SQL_ColumnNames, self)
        if Dialog.exec_() != QDialog.Accepted:
            return
        # Apply the new selection (re-derive both lists from the master order, regardless of what order the dialog
        #   happened to return the selection in).
        Selected = set(Dialog.Get_Selected_Columns())
        self.SQL_ColumnNames = [SQLName for SQLName, _ in self.AllColumns if SQLName in Selected]
        self.ColumnNames = [Label for SQLName, Label in self.AllColumns if SQLName in Selected]
        # Update the table headers/column count.
        self.Reset_Table_Sort()
        self.Table.clearContents()
        self.Table.clearSelection()
        self.Table.setColumnCount(len(self.ColumnNames))
        self.Table.setHorizontalHeaderLabels(self.ColumnNames)
        # Refresh the rows: re-fetch if a filter is currently active, otherwise reset to the empty state.
        if self.DropDown_Bnumber.currentIndex() > 0:
            self.Function_Button_Fetch()
        else:
            self.Reset_Table_Empty()
    # ------------------------------------------------------------------------------------------------------------------
    def Open_Column_Selector_Dialog_Analysis(self):
        """
        This function opens the "Select Columns" dialog for the Analysis Results table (triggered from the "Edit"
        menu), and applies the user's selection: it updates the table's headers/columns, then either re-fetches the
        currently filtered rows, or re-fetches everything unfiltered, so the table always reflects the previous
        selection/filter (the Analysis view shows all rows by default, unlike the empty-by-default Database view).
        """
        # This only makes sense while the "Analysis Results" view is showing.
        if not self.InAnalysisView:
            QMessageBox.information(self, "Switch to Analysis View",
                                    'Please switch to the Analysis Results view (click "Analysis Results Page") ' +
                                    'before selecting columns for that table.')
            return
        # Open the dialog, seeded with the currently selected columns.
        Dialog = SelectColumnsDialog(self.AllColumnsAnalysis, self.AlwaysShownAnalysisSQL, self.ColumnNamesAnalysis,
                                     self)
        if Dialog.exec_() != QDialog.Accepted:
            return
        # Apply the new selection (re-derived in master order, same as the Database column picker).
        Selected = set(Dialog.Get_Selected_Columns())
        self.ColumnNamesAnalysis = [Name for Name, _ in self.AllColumnsAnalysis if Name in Selected]
        self.Reset_Table_Sort()
        # Refresh the rows with the new columns: re-fetch if a filter is currently active, otherwise show everything
        #   unfiltered again (Populate_Analysis_Table takes care of the headers/column count either way).
        if self.DropDown_Bnumber.currentIndex() > 0:
            self.Function_Button_Fetch_Analysis()
        else:
            self.cursor.execute(
                f"SELECT {', '.join([f'[{col}]' for col in self.ColumnNamesAnalysis])} FROM FTIR_Analysis_DB")
            self.Populate_Analysis_Table(self.cursor.fetchall())
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Go2Main(self):
        """
        This function simply clear the current page and move to the main page.
        """
        # Clear the table and drop down menus.
        self.Table.clearSelection()
        self.DropDown_Bnumber.setCurrentIndex(0)
        self.DropDown_LabAging.setCurrentIndex(0)
        self.Reset_Table_Empty()
        # Move to the main page.
        self.stack.setCurrentIndex(0)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Modify(self):
        # Find the selected index. 
        idx, ID = self.Check_Row_Selection(ActionLabel='modify')
        if (ID == -1) or (idx == -1):
            return
        # Call Stack 3 and send the ID.
        self.shared_data.data = ID
        self.stack.setCurrentIndex(2)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Analysis(self):
        # First check which view needed to be shown.
        if not self.InAnalysisView:
            # First of all, check if the analysis is available or user may want to rerun the analysis.
            self.Rerun_Database_Analysis()
            # Switch the internal view state first, so the dropdown/table helpers triggered below (e.g. resetting the
            #   LabAging dropdown) use the Analysis column set instead of the Database one.
            self.InAnalysisView = True
            self.Reset_Table_Sort()
            # Prepare the page. The B-number/Aging filters and "Fetch data" stay enabled, so the user can filter the
            #   Analysis results the same way they filter the raw Database records.
            self.DropDown_Bnumber.setCurrentIndex(0)
            self.DropDown_LabAging.setCurrentIndex(0)
            self.Button_Modify.setEnabled(False)
            self.Button_Delete_Record.setEnabled(False)
            self.Button_Export_Record.setEnabled(False)
            self.Button_Export_Database.setEnabled(False)
            self.Button_Export_Analysis.setEnabled(False)
            self.Button_Go2Main.setEnabled(False)
            self.Terminal.appendPlainText(
                f"\n>>> Moving to the Analysis of Results view.")
            # Get the results from the DB (unfiltered, showing everything by default).
            self.cursor.execute(
                f"SELECT {', '.join([f'[{col}]' for col in self.ColumnNamesAnalysis])} FROM FTIR_Analysis_DB")
            Rows = self.cursor.fetchall()
            # Fill the table with the new analysis results.
            self.Populate_Analysis_Table(Rows)
            # Change the text on the button.
            self.Button_Analysis.setText('Database Page')
        else:
            # Switch the internal view state first.
            self.InAnalysisView = False
            self.Reset_Table_Sort()
            # Show the database content.
            self.DropDown_Bnumber.setCurrentIndex(0)
            self.Button_Modify.setEnabled(True)
            self.Button_Delete_Record.setEnabled(True)
            self.Button_Export_Record.setEnabled(True)
            self.Button_Export_Database.setEnabled(True)
            self.Button_Export_Analysis.setEnabled(True)
            self.Button_Go2Main.setEnabled(True)
            self.Terminal.appendPlainText(f"\n>>> Moving to the DB view.")
            # Clear the table.
            self.Reset_Table_Empty()
            # change the name.
            self.Button_Analysis.setText('Analysis Results Page')
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Delete_Record(self): 
        """
        This function deletes the current selection from the database. 
        """
        # Find the selected index. 
        idx, ID = self.Check_Row_Selection(ActionLabel='delete')
        if (ID == -1) or (idx == -1):
            return
        # SelectedIndices = self.Table.selectionModel().selectedIndexes()
        # if len(SelectedIndices) == 0:           
        #     # Nothing is selected. 
        #     QMessageBox.critical(self, "Data Selection Error!", 
        #                          f"Row was not selected. Please first select the row you want to delete " + 
        #                          f"from the database.")
        #     return
        # idx = SelectedIndices[0].row()
        # # Check the id value. 
        # ID = self.Table.item(idx, 0)
        # if ID == None or ID.text() == '':
        #     # Table is empty. 
        #     QMessageBox.critical(self, "Data Selection Error!",
        #                          f"Selected row ({idx + 1}) is empty. Please first fetch the data using the " +
        #                          f'"Search and Filter" section, then select the intended row, and then click ' +
        #                          f'"Delete Record" button.')
        #     return
        # else:
        #     ID = int(ID.text())
        Bnumber = self.Table.item(idx, 1).text()
        LabAging= self.Table.item(idx, 2).text()
        RepNum  = self.Table.item(idx, 3).text()
        Msg  = f'Do you want to Permanently Delete the following record?:\n' + \
                f'ID-number={Bnumber} at age level of "{LabAging}", Rep {RepNum}'
        Question = QMessageBox()
        Question.setIcon(QMessageBox.Question)
        Question.setWindowTitle("Delete Record Confirmation")
        Question.setText(Msg)
        Question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        Question.setDefaultButton(QMessageBox.No)
        Reply = Question.exec_()
        # Check the response. 
        if Reply == QMessageBox.Yes:
            # User Choose Yes.
            # deleting the record from the Database.
            self.cursor.execute("DELETE FROM FTIR WHERE id = ?", (ID,))
            self.conn.commit()
            # Updating the table. 
            self.Function_Button_Fetch()
            # Print out the results in Terminal. 
            Msg = f'>>> 1 record was successfully deleted from Database:\n>>>\tID-number={Bnumber}\n' + \
                    f'>>>\tLab aging level: "{LabAging}"\n>>>\tRepetition number: {RepNum}\n>>>'
            self.Terminal.appendPlainText(Msg)
        else:
            # User clicked No, and ignore the deletion. 
            print("Ignore")
            return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Export_Database(self):
        """
        This function exports the whole database in an Excel file. It is noted that this button exports the database of 
        all individual records, and didn't combine the repititions of a sample. 
        """
        # Ask for a directory to save the file and file name. 
        Directory = QFileDialog.getExistingDirectory(self, "Please select Saving Directory", "")
        # If a file is selected by the user, update the Input_SavePath.
        if not Directory:
            QMessageBox.critical(self, "Directory Selection Failed!", f"Directory was NOT selected. Please try again.")
            return
        print(f'Saving Directory: {Directory}')
        # Ask for the file name. 
        FileName, IsOkButtonPressed = QInputDialog.getText(
            self, "Output File Name", "Please enter the output file name (without .xlsx):", 
            text=f'{self.DB_Name}_Export')
        if IsOkButtonPressed:
            FileName = FileName + '.xlsx'
            print(f"Saving File Name: {FileName}")
        else:
            QMessageBox.critical(self, "Output File Name Failed!", 
                                 f"Output file name was NOT confirmed. Please try again.")
            return
        # --------------------------------------------------------------------------------------------------------------
        # Define the exporting columns and their corresponding labels.
        ColNames = [
            'id', 'Bnumber', 'Lab_Aging', 'RepNumber', 'FileName', 'FileDirectory', 'IsOutlier',
            'Baseline_Adjustment_Method', 'ALS_Lambda', 'ALS_Ratio', 'ALS_NumIter',
            'Normalization_Method', 'Normalization_Coeff',
            'Deconv_ICO', 'Deconv_ISO',
            'ICO_Baseline', 'ISO_Baseline',
            'Carbonyl_Area_Baseline', 'Sulfoxide_Area_Baseline', 'Aliphatic_Area_Baseline',
            'ICO_Tangential', 'ISO_Tangential', 
            'Carbonyl_Area_Tangential', 'Sulfoxide_Area_Tangential', 'Aliphatic_Area_Tangential',
            'Carbonyl_Peak_Wavenumber', 'Sulfoxide_Peak_Wavenumber',
            'Aliphatic_Peak_Wavenumber_1', 'Aliphatic_Peak_Wavenumber_2',
            'Carbonyl_Peak_Absorption', 'Sulfoxide_Peak_Absorption',
            'Aliphatic_Peak_Absorption_1', 'Aliphatic_Peak_Absorption_2',
            'Carbonyl_Min_Wavenumber', 'Carbonyl_Max_Wavenumber',
            'Sulfoxide_Min_Wavenumber', 'Sulfoxide_Max_Wavenumber',
            'Aliphatic_Min_Wavenumber', 'Aliphatic_Max_Wavenumber']
        Labels = [
            'DB id', 'ID-number', 'Laboratory Aging', 'Repetition Number', 'File Name', 'File Directory', 'Is Outlier?',
            'Baseline Adjustment Method', 'ALS λ Coeff', 'ALS ρ Coeff', 'ALS Niter Coeff',
            'Normalization Method', 'Normalization Coeff',
            'ICO (deconvolution)', 'ISO (deconvolution)', 
            'ICO (baseline integration)', 'ISO (baseline integration)',
            'Carbonyl Area (baseline integration)', 'Sulfoxide Area (baseline integration)',
            'Aliphatic Area (baseline integration)',
            'ICO (tangential integration)', 'ISO (tangential integration)',
            'Carbonyl Area (tangential integration)', 'Sulfoxide Area (tangential integration)',
            'Aliphatic Area (tangential integration)',
            'Carbonyl Peak Wavenumber (cm⁻¹)', 'Sulfoxide Peak Wavenumber (cm⁻¹)',
            'Aliphatic Peak Wavenumber 1 (cm⁻¹)', 'Aliphatic Peak Wavenumber 2 (cm⁻¹)',
            'Carbonyl Peak Absorption', 'Sulfoxide Peak Absorption',
            'Aliphatic Peak Absorption 1', 'Aliphatic Peak Absorption 2',
            'Carbonyl Min Wavenumber', 'Carbonyl Max Wavenumber',
            'Sulfoxide Min Wavenumber', 'Sulfoxide Max Wavenumber', 
            'Aliphatic Min Wavenumber', 'Aliphatic Max Wavenumber']
        # The rheology and SBS detection results, if this database has their columns.
        self.cursor.execute("PRAGMA table_info(FTIR)")
        Available = [Row[1].lower() for Row in self.cursor.fetchall()]
        for SQLName, Label in self.AllColumns:
            if SQLName.startswith(('Rheo_', 'SBS_')) and SQLName.lower() in Available:
                ColNames.append(SQLName)
                Labels.append(Label)
        # --------------------------------------------------------------------------------------------------------------
        # Fetch data from Database.
        self.cursor.execute(f"SELECT {','.join(ColNames)} FROM FTIR")
        Content = self.cursor.fetchall()
        # --------------------------------------------------------------------------------------------------------------
        # Prepare the output file. 
        # Create a new workbook and select the active sheet
        wb = Workbook()
        ws = wb.active
        # Set the title of the sheet
        ws.title = "Sheet1"
        # Define some styles. 
        Title_fill      = PatternFill(start_color="FFE989", end_color="FFCC00", fill_type="solid")
        Valid_fill      = PatternFill(start_color="D4FEC2", end_color="D4FEC2", fill_type="solid")
        Invalid_fill    = PatternFill(start_color="FDBBBB", end_color="FDBBBB", fill_type="solid")
        Data_fill       = PatternFill(start_color="DFDED9", end_color="DFDED9", fill_type="solid")
        thin            = Side(border_style="thin", color="000000")
        cell_border     = Border(top=thin, left=thin, right=thin, bottom=thin)
        header_font     = Font(name="Arial", bold=True, size=11, color="000000")
        cell_font       = Font(name="Arial", size=11, color="000000")
        center_alignment= Alignment(horizontal="center", vertical="center")
        # Write the titles. 
        for j, col in enumerate(Labels, start=1):
            cell = ws.cell(row=1, column=j, value=col)
            cell.fill = Title_fill
            cell.border = cell_border
            cell.font = header_font
            cell.alignment = center_alignment
        # Write the data. 
        for i in range(len(Content)):
            Fill = Invalid_fill if Content[i][6] else Valid_fill
            for j, Value in enumerate(Content[i], start=1):
                cell = ws.cell(row=2 + i, column=j, value=Value)
                cell.fill = Fill
                cell.border = cell_border
                cell.font = cell_font
                cell.alignment = center_alignment
        # Adjust the size of each column in the final excel file. 
        for j, col in enumerate(Labels, start=1):
            col_letter = get_column_letter(j)
            # Estimate width: character count + padding (2 to 5 is typical)
            max_label_length = len(str(col)) + 2
            ws.column_dimensions[col_letter].width = max_label_length
        # Save the results. 
        wb.save(os.path.join(Directory, FileName))
        # Return nothing. 
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Export_Database_Combined(self):
        """
        This function is for exporting the database after combining the results to evaluate different replicates of the
        same samples. 
        """
        # First, running the combined analysis, if user prefferred to do so. 
        self.Rerun_Database_Analysis()
        # Ask for a directory to save the file and file name. 
        Directory = QFileDialog.getExistingDirectory(self, "Please select Saving Directory", "")
        # If a file is selected by the user, update the Input_SavePath.
        if not Directory:
            QMessageBox.critical(self, "Directory Selection Failed!", f"Directory was NOT selected. Please try again.")
            return
        print(f'Saving Directory: {Directory}')
        # Ask for the file name. 
        FileName, IsOkButtonPressed = QInputDialog.getText(
            self, "Output File Name", "Please enter the output file name (without .xlsx):", 
            text=f'{self.DB_Name}_Export_Combined')
        if IsOkButtonPressed:
            FileName = FileName + '.xlsx'
            print(f"Saving File Name: {FileName}")
        else:
            QMessageBox.critical(self, "Output File Name Failed!", 
                                 f"Output file name was NOT confirmed. Please try again.")
            return
        # Retrieve the analysis from the database. 
        self.cursor.execute("SELECT * FROM FTIR_Analysis_DB")
        Content = self.cursor.fetchall()
        self.cursor.execute("PRAGMA Table_Info(FTIR_Analysis_DB)")
        ColNames = [column[1] for column in self.cursor.fetchall()]
        # Save the results into the Excel file. 
        # Do the same as other export options using openpyxl library. But for the sake of time, I'll do it more simply. 
        Res = pd.read_sql("SELECT * FROM FTIR_Analysis_DB", self.conn)
        Res.to_excel(os.path.join(Directory, FileName), index=False)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Export_Individual(self):
        """
        This function exports the raw and analyzed results of the selected individual record as an Excel file. 
        """
        # Find the selected index. 
        idx, ID = self.Check_Row_Selection(ActionLabel='export')
        if (ID == -1) or (idx == -1):
            return
        # SelectedIndices = self.Table.selectionModel().selectedIndexes()
        # if len(SelectedIndices) == 0:           
        #     # Nothing is selected. 
        #     QMessageBox.critical(self, "Data Selection Error!", 
        #                                 f"Row was not selected. Please first select the row you want to export " + 
        #                                 f"from the database.")
        #     self.Export_ProgressBar.hide()
        #     return
        # idx = SelectedIndices[0].row()
        # # Check the id value. 
        # ID = self.Table.item(idx, 0)
        # if ID == None or ID.text() == '':
        #     # Table is empty. 
        #     QMessageBox.critical(self, "Data Selection Error!", 
        #                                 f"Selected row ({idx + 1}) is empty. Please first fetch the data using the " +
        #                                 f'"Search and Filter" section, then select the intended row, and then click ' +
        #                                 f'"Export (Individual Record)" button.')
        #     self.Export_ProgressBar.hide()
        #     return
        # # Otherwise, everything is ready for exporting. 
        # ID = int(ID.text())             # The ID to retrieve the data from the DB. 
        # --------------------------------------------------------------------------------------------------------------
        # Ask for a directory to save the file and file name. 
        Directory = QFileDialog.getExistingDirectory(self, "Please select Saving Directory", "")
        # If a file is selected by the user, update the Input_SavePath.
        if not Directory:
            QMessageBox.critical(self, "Directory Selection Failed!", f"Directory was NOT selected. Please try again.")
            return
        print(f'Saving Directory: {Directory}')
        # Ask for the file name. 
        self.cursor.execute("SELECT FileName FROM FTIR WHERE id = ?", (ID,))
        FileName, IsOkButtonPressed = QInputDialog.getText(
            self, "Output File Name", "Please enter the output file name (without .xlsx):", 
            text=os.path.splitext(self.cursor.fetchone()[0])[0])
        if IsOkButtonPressed:
            FileName = FileName + '.xlsx'
            print(f"Saving File Name: {FileName}")
        else:
            QMessageBox.critical(self, "Output File Name Failed!", 
                                 f"Output file name was NOT confirmed. Please try again.")
            return
        # --------------------------------------------------------------------------------------------------------------
        # Prepare the output file. 
        # Create a new workbook and select the active sheet
        wb = Workbook()
        ws = wb.active
        # Set the title of the sheet
        ws.title = "Sheet1"
        # Define some styles. 
        Info_fill       = PatternFill(start_color="FFE989", end_color="FFCC00", fill_type="solid")
        Pre_fill        = PatternFill(start_color="A7E2FF", end_color="A7E2FF", fill_type="solid")
        Res_fill        = PatternFill(start_color="D4FEC2", end_color="D4FEC2", fill_type="solid")
        GL_fill         = PatternFill(start_color="FDBBBB", end_color="FDBBBB", fill_type="solid")
        Data_fill       = PatternFill(start_color="DFDED9", end_color="DFDED9", fill_type="solid")
        thin            = Side(border_style="thin", color="000000")
        cell_border     = Border(top=thin, left=thin, right=thin, bottom=thin)
        header_font     = Font(name="Arial", bold=True, size=11, color="000000")
        cell_font       = Font(name="Arial", size=11, color="000000")
        center_alignment= Alignment(horizontal="center", vertical="center")
        left_alignment  = Alignment(horizontal="left", vertical="center")
        # ----------------------------------------------------------------------------
        # Extract the General information parameters. 
        ColNames_Info = ['Bnumber', 'Lab_Aging', 'RepNumber', 'FileName',  'FileDirectory', 
                        'IsOutlier']
        Labels_Info   = ['B-number', 'Lab aging level', 'Repetition number', 'Raw data file name', 'Raw data file directory', 
                        'Is this test considered Outlier']
        self.cursor.execute(f'SELECT {", ".join(ColNames_Info)} FROM FTIR WHERE id = ?', (ID,))
        Values_Info = list(self.cursor.fetchone())
        # Make isOutlier yes/no.
        Values_Info[5] = 'Yes' if Values_Info[5] else "No"
        # ------------------------------------------------------
        # Write the General information. 
        ws.merge_cells('A1:B1')
        cell = ws.cell(row=1, column=1, value='General Information')
        cell.fill = Info_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        for i, (header, value) in enumerate(zip(Labels_Info, Values_Info), start=2):
            # Write the title.
            cell1 = ws.cell(row=i, column=1, value=header + ':')
            cell1.fill = Info_fill
            cell1.border = cell_border
            cell1.font = header_font
            cell1.alignment = left_alignment
            # Write the value. 
            cell1 = ws.cell(row=i, column=2, value=value)
            cell1.fill = Info_fill
            cell1.border = cell_border
            cell1.font = cell_font
            cell1.alignment = left_alignment
        NextRowIndex = i + 2
        # ----------------------------------------------------------------------------------------------------------------------
        # Next, write the Pre-processing properties. 
        # Extract the results. 
        ColNames_Pre = ['Baseline_Adjustment_Method', 'ALS_Lambda', 'ALS_Ratio', 'ALS_NumIter', 
                        'Normalization_Method', 'Normalization_Coeff']
        Labels_Pre = ['Baseline adjustment method', 'ALSS λ coefficient', 'ALSS ρ coefficient', 'ALSS n coefficient', 
                    'Normalization method', 'Normalization β coefficient']
        self.cursor.execute(f'SELECT {", ".join(ColNames_Pre)} FROM FTIR WHERE id = ?', (ID,))
        Values_Pre = list(self.cursor.fetchone())
        # ------------------------------------------------------
        # Write the General information. 
        ws.merge_cells(f'A{NextRowIndex}:B{NextRowIndex}')
        cell = ws.cell(row=NextRowIndex, column=1, value='Pre-processing Properties')
        cell.fill = Pre_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        for i in range(1, 9):
            for j in range(2):
                cell1 = ws.cell(row=NextRowIndex+i, column=j+1, value='')
                cell1.fill = Pre_fill
        # Put the image. 
        Image_Obj = Read_Resize_Image(ResourcePath(os.path.join(".", "assets", "ALSS Baseline Correction.png")), 153)
        ws.add_image(Image_Obj, f"A{NextRowIndex+1}")
        NextRowIndex += 9
        # Write the 2PP model parameters. 
        for i, (header, value) in enumerate(zip(Labels_Pre, Values_Pre), start=NextRowIndex):
            # Write the title.
            cell1 = ws.cell(row=i, column=1, value=header + ':')
            cell1.fill = Pre_fill
            cell1.border = cell_border
            cell1.font = header_font
            cell1.alignment = left_alignment
            # Write the value. 
            cell1 = ws.cell(row=i, column=2, value=value)
            cell1.fill = Pre_fill
            cell1.border = cell_border
            cell1.font = cell_font
            cell1.alignment = left_alignment
        NextRowIndex = i + 2
        # ----------------------------------------------------------------------------------------------------------------------
        # Next, provide the results. 
        # Extract the results. 
        ColNames_Res = [
            'Deconv_ICO', 'Deconv_ISO', 
            'ICO_Baseline', 'ISO_Baseline', 'ICO_Tangential', 'ISO_Tangential',
            'Carbonyl_Area_Baseline', 'Sulfoxide_Area_Baseline', 'Aliphatic_Area_Baseline', 
            'Carbonyl_Area_Tangential', 'Sulfoxide_Area_Tangential', 'Aliphatic_Area_Tangential',
            'Carbonyl_Peak_Wavenumber', 'Sulfoxide_Peak_Wavenumber', 
            'Aliphatic_Peak_Wavenumber_1', 'Aliphatic_Peak_Wavenumber_2',
            'Carbonyl_Peak_Absorption', 'Sulfoxide_Peak_Absorption', 
            'Aliphatic_Peak_Absorption_1', 'Aliphatic_Peak_Absorption_2',
            'Carbonyl_Min_Wavenumber', 'Carbonyl_Max_Wavenumber', 
            'Sulfoxide_Min_Wavenumber', 'Sulfoxide_Max_Wavenumber', 
            'Aliphatic_Min_Wavenumber', 'Aliphatic_Max_Wavenumber',]
        Labels_Res = [
            'ICO (deconvolution)', 'ISO (deconvolution)', 
            'ICO (baseline integration)', 'ISO (baseline integration)', 
            'ICO (tangential integration)', 'ISO (tangential integration)', 
            'Carbonyl area (baseline integration)', 
            'Sulfoxide area (baseline integration)', 
            'Aliphatic area (baseline integration)', 
            'Carbonyl area (tangential integration)', 
            'Sulfoxide area (tangential integration)', 
            'Aliphatic area (tangential integration)', 
            'Carbonyl peak location (cm⁻¹)', 'Sulfoxide peak location (cm⁻¹)', 
            'First Aliphatic peak location (cm⁻¹)', 'Second aliphatic peak location (cm⁻¹)',
            'Carbonyl peak absorbance', 'Sulfoxide peak absorbance', 
            'First Aliphatic peak absorbance', 'Second aliphatic peak absorbance', 
            'Carbonyl peak min boundary (cm⁻¹)', 'Carbonyl peak max boundary (cm⁻¹)', 
            'Sulfoxide peak min boundary (cm⁻¹)', 'Sulfoxide peak max boundary (cm⁻¹)', 
            'Aliphatic peak min boundary (cm⁻¹)', 'Aliphatic peak max boundary (cm⁻¹)',]
        self.cursor.execute(f'SELECT {", ".join(ColNames_Res)} FROM FTIR WHERE id = ?', (ID,))
        Values_Res = list(self.cursor.fetchone())
        # ------------------------------------------------------
        # Write the General information. 
        ws.merge_cells(f'A{NextRowIndex}:B{NextRowIndex}')
        cell = ws.cell(row=NextRowIndex, column=1, value='Results')
        cell.fill = Res_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        NextRowIndex += 1
        # Write the Results. 
        for i, (header, value) in enumerate(zip(Labels_Res, Values_Res), start=NextRowIndex):
            # Write the title.
            cell1 = ws.cell(row=i, column=1, value=header + ':')
            cell1.fill = Res_fill
            cell1.border = cell_border
            cell1.font = header_font
            cell1.alignment = left_alignment
            # Write the value. 
            cell1 = ws.cell(row=i, column=2, value=value)
            cell1.fill = Res_fill
            cell1.border = cell_border
            cell1.font = cell_font
            cell1.alignment = left_alignment
        NextRowIndex = i + 2
        # ----------------------------------------------------------------------------------------------------------------------
        # Next, provide the deconvolution gaussians. 
        # Get the Gaussian lists. 
        ColNames = [ 
            'Deconv_GaussianList', 'Deconv_GaussianList_shape', 'Deconv_GaussianList_dtype', 
            'Deconv_CarbonylList', 'Deconv_CarbonylList_shape', 'Deconv_CarbonylList_dtype', 
            'Deconv_SulfoxideList', 'Deconv_SulfoxideList_shape', 'Deconv_SulfoxideList_dtype', 
            'Deconv_AliphaticList', 'Deconv_AliphaticList_shape', 'Deconv_AliphaticList_dtype']
        self.cursor.execute(f'SELECT {", ".join(ColNames)} FROM FTIR WHERE id = ?', (ID,))
        Content = list(self.cursor.fetchone())
        Gaussians = Binary_to_Array(Content[0], Content[1],  Content[2])
        GL_C      = Binary_to_Array(Content[3], Content[4],  Content[5])
        GL_S      = Binary_to_Array(Content[6], Content[7],  Content[8])
        GL_A      = Binary_to_Array(Content[9], Content[10], Content[11])
        # ------------------------------------------------------
        # Write the title. 
        ws.merge_cells(f'D1:H1')
        cell = ws.cell(row=1, column=4, value='Deconvolution Results')
        cell.fill = GL_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        for i in range(2, 9):
            for j in range(5):
                cell1 = ws.cell(row=i, column=j+4, value='')
                cell1.fill = GL_fill
        # Put the image. 
        Image_Obj = Read_Resize_Image(ResourcePath(os.path.join(".", "assets", "Deconcolution Gaussian.png")), 125)
        ws.add_image(Image_Obj, "E2")
        NextRowIndex = 8
        Titles = ['Number', 'μ (cm⁻¹)', 'σ (cm⁻¹)', 'α', 'Area']
        for j in range(5):
            # Write the title.
            cell1 = ws.cell(row=NextRowIndex + 1, column=j + 4, value=Titles[j])
            cell1.fill = GL_fill
            cell1.border = cell_border
            cell1.font = header_font
            cell1.alignment = center_alignment
        for i in range(Gaussians.shape[0]):
            Values = [i + 1, Gaussians[i, 0], abs(Gaussians[i, 1]), Gaussians[i, 2], 
                    np.abs(np.sqrt(2 * np.pi) * Gaussians[i, 2] * Gaussians[i, 1])]
            NumberFormat = ["0", "0.00", "0.0000", "0.000000", "0.0000"]
            for j in range(5):
                # Write the title.
                cell1 = ws.cell(row=i + NextRowIndex + 2, column=j + 4, value=Values[j])
                cell1.fill = GL_fill
                cell1.border = cell_border
                cell1.font = cell_font
                cell1.alignment = center_alignment
                cell1.number_format = NumberFormat[j]
        NextRowIndex = i + 2
        # ----------------------------------------------------------------------------------------------------------------------
        # Finally, Provide the raw data. 
        # Extract the raw data. 
        ColNames = [ 
            'Wavenumber', 'Wavenumber_shape', 'Wavenumber_dtype', 
            'Absorption', 'Absorption_shape', 'Absorption_dtype', 
            'RawWavenumber', 'RawWavenumber_shape', 'RawWavenumber_dtype', 
            'RawAbsorbance', 'RawAbsorbance_shape', 'RawAbsorbance_dtype',]
        self.cursor.execute(f'SELECT {", ".join(ColNames)} FROM FTIR WHERE id = ?', (ID,))
        Content = list(self.cursor.fetchone())
        X_BC = Binary_to_Array(Content[0], Content[1],  Content[2])     # Preprocessed: wavenumbers (cm⁻¹). 
        Y_BC = Binary_to_Array(Content[3], Content[4],  Content[5])     # Preprocessed: absorbance. 
        Xraw = Binary_to_Array(Content[6], Content[7],  Content[8])     # Raw data: wavenumbers (cm⁻¹). 
        Yraw = Binary_to_Array(Content[9], Content[10], Content[11])    # Raw data: absorbance.
        # ------------------------------------------------------
        # Write the title. 
        ws.merge_cells(f'J1:M1')
        cell = ws.cell(row=1, column=10, value='FTIR Test Data')
        cell.fill = Data_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        ws.merge_cells(f'J2:K2')
        cell = ws.cell(row=2, column=10, value='Raw Data')
        cell.fill = Data_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        ws.merge_cells(f'L2:M2')
        cell = ws.cell(row=2, column=12, value='Pre-Processed')
        cell.fill = Data_fill
        cell.border = cell_border
        cell.font = Font(name="Arial", size=13, bold=True, color="000000")
        cell.alignment = center_alignment
        Titles = ['Wavenumber (cm⁻¹)', 'Absorbance', 'Wavenumber (cm⁻¹)', 'Absorbance',]
        for j in range(4):
            # Write the title.
            cell1 = ws.cell(row=3, column=j + 10, value=Titles[j])
            cell1.fill = Data_fill
            cell1.border = cell_border
            cell1.font = header_font
            cell1.alignment = center_alignment
        for i in range(len(Xraw)):
            Values = [Xraw[i], Yraw[i], X_BC[i], Y_BC[i]]
            NumberFormat = ["0.00", "0.0000", "0.00", "0.0000"]
            for j in range(4):
                # Write the title.
                cell1 = ws.cell(row=i + 4, column=j + 10, value=Values[j])
                cell1.fill = Data_fill
                cell1.border = cell_border
                cell1.font = cell_font
                cell1.alignment = center_alignment
                cell1.number_format = NumberFormat[j]
        # --------------------------------------------------------------------------------------------------------------
        # Adjust the column dimensions. 
        ws.column_dimensions["A"].width = 40
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 8
        ws.column_dimensions["D"].width = 12
        ws.column_dimensions["E"].width = 12
        ws.column_dimensions["F"].width = 13
        ws.column_dimensions["G"].width = 13
        ws.column_dimensions["H"].width = 13
        ws.column_dimensions["I"].width = 8
        ws.column_dimensions["J"].width = 21
        ws.column_dimensions["K"].width = 15
        ws.column_dimensions["L"].width = 21
        ws.column_dimensions["M"].width = 15
        # Save the Excel file. 
        wb.save(os.path.join(Directory, FileName))
        # Return nothing. 
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Check_Row_Selection(self, ActionLabel):
        """
        This function checks if a row from the table is selected and have valid data in it. Then, it will return the 
        row index and "id" of the selected row. 
        """
        # Find the selected index. 
        SelectedIndices = self.Table.selectionModel().selectedIndexes()
        if len(SelectedIndices) == 0:           
            # Nothing is selected. 
            QMessageBox.critical(self, "Data Selection Error!", 
                                 f"Row was not selected. Please first select the row you want to {ActionLabel} " + 
                                 f"from the database.")
            return -1, -1
        idx = SelectedIndices[0].row()
        # Check the id value. 
        ID = self.Table.item(idx, 0)
        if ID == None or ID.text() == '':
            # Table is empty. 
            QMessageBox.critical(self, "Data Selection Error!",
                                 f"Selected row ({idx + 1}) is empty. Please first fetch the data using the " +
                                 f'"Search and Filter" section, then select the intended row to {ActionLabel}, and ' + 
                                 f'then click the corresponding button.')
            return -1, -1
        else:
            # Return the row index and database "id" value correspond to the selected row. 
            return idx, int(ID.text())
    # ------------------------------------------------------------------------------------------------------------------
    def Rerun_Database_Analysis(self, AskUser=True):
        """
        This function first asks user if the analysis for combining the results should be re-run (unless "AskUser" is
        False) and do the analysis if neccessary. Then, it will overwrite the results in the database.
        """
        # First, check if the combined result table is available in the SQL database.
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        TableNames = [name[0] for name in self.cursor.fetchall()]
        if AskUser and 'FTIR_Analysis_DB' in TableNames:
            # Analysis is available. Ask the user to re-run or not. 
            Msg  = f'Do you want to update the analysis for aggregation of the available FTIR results?'
            Question = QMessageBox()
            Question.setIcon(QMessageBox.Question)
            Question.setWindowTitle("Re-Run Analysis Confirmation")
            Question.setText(Msg)
            Question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            Question.setDefaultButton(QMessageBox.Yes)
            Reply = Question.exec_()
            if Reply == QMessageBox.Yes:
                pass
            else:
                return
        # If user decided to re-run the analysis.
        # Now, get the latest values of the required parameters from the database. "Column2Fetch"/"Labels" are the
        #   shared "self.AnalysisSourceColumns"/"self.AnalysisSourceLabels" (see __init__) so that the columns this
        #   function actually generates in "FTIR_Analysis_DB" can never drift out of sync with "self.AllColumnsAnalysis"
        #   (the master list the "Select Columns" dialog for the Analysis panel is built from).
        Column2Fetch = self.AnalysisSourceColumns
        Labels = self.AnalysisSourceLabels
        self.cursor.execute(f"SELECT {', '.join(Column2Fetch)} FROM FTIR")
        data = self.cursor.fetchall()
        data = pd.DataFrame(data, columns=Column2Fetch)         # Convert the retrieved data to DataFrame. 
        data = data[data.IsOutlier == 0]                        # Exclude the outlier data. 
        # Prepare a table for the results. 
        Res = {'B_Number': [], 'Lab_Aging_Condition': [], 'Num_Data': []}
        for col in Column2Fetch[5:]:
            for metric in ['mean', 'std', 'COV', 'min', 'max', 'data']:
                Res[f'{col}_{metric}'] = []
        # Define a function to add data to the results. 
        def AddResults(Res, arr, ResLabel):
            # An empty value (e.g., an Aliphatic peak not found in a spectrum) is left out of the statistics, so one
            #   replicate doesn't remove the results of the others. It still shows in the list of the data.
            Valid = pd.to_numeric(pd.Series(arr), errors='coerce').dropna().to_numpy()
            if len(Valid) == 0:
                Valid = np.array([np.nan])
            Res[f'{ResLabel}_mean'].append(Valid.mean())
            Res[f'{ResLabel}_std'].append(Valid.std())
            Res[f'{ResLabel}_COV'].append(Valid.std() / Valid.mean())
            Res[f'{ResLabel}_min'].append(Valid.min())
            Res[f'{ResLabel}_max'].append(Valid.max())
            Res[f'{ResLabel}_data'].append('|'.join(list(arr.astype(str))))
            return Res
        # Start iterating over the unique "B-numbers" and analyze the results. 
        Bnumber = data['Bnumber'].unique()              # Unique B-numbers. 
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
                    RepData = RemoveOutliers(RepData)
                # Add the data to the "Res" dictionary. 
                Res['B_Number'].append(bnum)
                Res['Lab_Aging_Condition'].append(aging)
                Res['Num_Data'].append(len(RepData))
                for col in Column2Fetch[5:]:
                    Res = AddResults(Res, RepData[col].to_numpy(), col)
        # Convert "Res" dictionary to DataFrame. 
        Labels4DF = ['ID-number', 'Laboratory Aging', 'Number of Data']
        for lbl in Labels[5:]:
            for metric in ['Mean of ', 'Std of ', 'COV of ', 'Min of ', 'Max of ']:
                Labels4DF.append(metric + lbl)
            Labels4DF.append(lbl + ' Data')
        OrgLabels = list(Res.keys())
        Res = pd.DataFrame(Res)
        Res = Res.sort_values(by=["B_Number"])
        Res.rename(columns={OrgLabels[i]: Labels4DF[i] for i in range(len(Labels4DF))}, inplace=True)
        # Save the results to the Database. 
        Res.to_sql('FTIR_Analysis_DB', self.conn, if_exists="replace", index=False)
        # Print the message to the output terminal. 
        Msg = f'>>> The analysis for aggregation of the available FTIR results is successfully performed!\n'
        self.Terminal.appendPlainText(Msg)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class SelectColumnsDialog(QDialog):
    """
    A reusable dialog that lets the user pick which columns should be shown in a table, from a fixed master list of
    (SQL name, display label) columns. Some columns can be marked as "always shown" (checked and disabled), so the
    user cannot deselect them. Intended for the Database review table (Edit > "Select Columns for Review Panel..."),
    and reusable later for other tables (e.g. the Analysis Results table) that need the same kind of column picker.
    """
    def __init__(self, AllColumns, AlwaysShownSQL, CurrentlySelectedSQL, parent=None):
        """
        :param AllColumns: List of (SQLName, Label) tuples, in the fixed master order used for display.
        :param AlwaysShownSQL: List of SQL names that must always stay selected (checked and disabled).
        :param CurrentlySelectedSQL: List of SQL names that should start checked (in addition to AlwaysShownSQL).
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self.AllColumns = AllColumns
        self.Checkboxes = {}          # SQLName -> QCheckBox
        self.setWindowTitle("Select Columns")
        Layout = QVBoxLayout(self)
        Label = QLabel("Select the columns to display in the table. Columns marked with * are always shown.")
        Layout.addWidget(Label)
        # A scrollable grid of checkboxes, so a long column list stays manageable.
        ScrollArea = QScrollArea()
        ScrollArea.setWidgetResizable(True)
        ScrollContent = QWidget()
        Grid = QGridLayout(ScrollContent)
        NumCols = 3
        FontMetrics = QFontMetrics(self.font())
        MaxLabelWidth = 0
        for i, (SQLName, ColLabel) in enumerate(AllColumns):
            IsAlwaysShown = SQLName in AlwaysShownSQL
            Text = ColLabel + (' *' if IsAlwaysShown else '')
            CheckBox = QCheckBox(Text)
            CheckBox.setChecked(IsAlwaysShown or (SQLName in CurrentlySelectedSQL))
            if IsAlwaysShown:
                CheckBox.setEnabled(False)
            self.Checkboxes[SQLName] = CheckBox
            Grid.addWidget(CheckBox, i // NumCols, i % NumCols)
            MaxLabelWidth = max(MaxLabelWidth, FontMetrics.width(Text))
        ScrollArea.setWidget(ScrollContent)
        Layout.addWidget(ScrollArea)
        # Size the dialog so the longest label isn't clipped, regardless of how many/how long the columns are
        #   (e.g. the Analysis panel's labels are much longer than the Database panel's).
        ColumnWidth = MaxLabelWidth + 60           # checkbox + margins/padding.
        DialogWidth = min(NumCols * ColumnWidth + 60, 1400)      # capped so it stays on-screen for huge lists.
        self.resize(max(DialogWidth, 500), 550)
        # OK/Cancel buttons.
        ButtonLayout = QHBoxLayout()
        Button_OK = QPushButton("OK")
        Button_OK.setStyleSheet(Dialog_Button_Style["Accept"])
        Button_OK.clicked.connect(self.accept)
        Button_Cancel = QPushButton("Cancel")
        Button_Cancel.setStyleSheet(Dialog_Button_Style["General"])
        Button_Cancel.clicked.connect(self.reject)
        ButtonLayout.addWidget(Button_OK)
        ButtonLayout.addWidget(Button_Cancel)
        Layout.addLayout(ButtonLayout)
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Selected_Columns(self):
        """
        :return: The SQL names of the checked columns, in the master "AllColumns" order.
        """
        return [SQLName for SQLName, _ in self.AllColumns if self.Checkboxes[SQLName].isChecked()]
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class SortableTableItem(QTableWidgetItem):
    """
    This class generates a table item that shows the given text, but sorts by the actual value behind it. A regular
    item sorts by its text, which places "10" before "9" and compares rounded numbers and percentages incorrectly.
    """
    def __init__(self, Text, Value):
        super().__init__(Text)
        self.SortKey = Get_Sort_Key(Value)
    # ------------------------------------------------------------------------------------------------------------------
    def __lt__(self, other):
        return self.SortKey < other.SortKey
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Sort_Key(Value):
    """
    This function converts a table value to a key for sorting: numbers (including the 0/1 of the boolean columns) come
    first by their value, then texts, and then empty values. Texts ignore upper/lower case and compare any digits in
    them as whole numbers, like Windows File Explorer, so "Rep2" comes before "Rep10".

    :param Value: the value from the database.
    :return: a tuple, that can be compared with the key of any other value.
    """
    if isinstance(Value, (int, float)):
        return (2,) if math.isnan(Value) else (0, Value)
    if Value is None or Value == '':
        return (2,)
    Parts = re.split(r'(\d+)', str(Value).lower())
    return (1, [int(Part) if i % 2 == 1 else Part for i, Part in enumerate(Parts)])
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Color_4_COV(value):
    """
    This function gets the COV value and return a corresponding background color to specify high COV values. 

    :return: color number. 
    """
    # Ignore less than 15%.
    if value < 0.15:
        return "#f0f0f0"  # background color
    # Use "reds" colormap for between 15% to 50%.
    elif 0.15 <= value <= 0.5:
        # Normalize value to the range [0, 1] for the colormap
        normalized_value = (value - 0.15) / (0.5 - 0.15)
        # Get color from Reds colormap
        return to_hex(Custom_cmap(normalized_value))
    # Use "red" for more than 50%.
    else:
        return to_hex((1.0, 0.0, 0.0))  # Bright red
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def ResourcePath(relative_path):
    """
    Get the absolute path to the resource, works for dev and PyInstaller build.

    :param RelativePath: The relative path, which is going to be converted to the Resource Path. 
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller stores resources in a temporary folder (_MEIPASS)
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Use the relative path during development
        return os.path.join(os.path.abspath(relative_path))
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Read_Resize_Image(path, targetPixel):
    """
    This function reads the image (*.png, *.jpg) and resize it to properly fit in the Excel file. 

    :param path: The complete/relative path to the image. 
    :param targetPixel: The height of the image after resize in pixels, given the fixed aspect ratio. 
    :param return: the resized image object. 
    """
    Image_Obj = Image(path)
    Ratio = targetPixel / Image_Obj.height
    Image_Obj.height = targetPixel
    Image_Obj.width  = Image_Obj.width * Ratio
    return Image_Obj
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def RemoveOutliers(df):
    """
    In case we have more than 3 repetition for a given FTIR sample, this function tries to find the outliers and return 
    the processed Dataframe. 

    VERY IMPORTANT NOTE: this function uses the "ICO" calculated using the "Baseline" method as an index to pick the 
    best combination of three, if the manual results are available. Otherwise, it will use "ICO" calculated using the 
    "deconvolution" method. 
    """
    # Check if "ICO_Baseline" is available for all rows. 
    ColName = 'ICO_Baseline'
    if -1 in df[ColName] or np.any(pd.isnull(df[ColName])):
        ColName = 'Deconv_ICO'
    while len(df) > 3:
        Index = list(df.index)
        Combinations = list(itertools.combinations(Index, len(Index) - 1))
        COVs = []
        for comb in Combinations:
            Arr = df.loc[list(comb), ColName]
            COVs.append(Arr.std() / Arr.mean() * 100)
        if max(COVs) - min(COVs) > 10:
            # This means that if by removing a specific measurement, the COV reduces by at least 10%, we can assume that 
            # specific measurement as outlier. Note that the total number of measurements are more than 3. 
            df = df.loc[list(Combinations[np.argmin(COVs)])]
        else:
            break
    # Return the updated DataFrame. 
    return df
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Connect to a SQL database.
    conn = sqlite3.connect(
        "C:\\Users\\SF.Abdollahi.ctr\\OneDrive - DOT OST\\FTIR_Temp\\PTF5_DB.db")
    cursor = conn.cursor()

    Main = DB_ReviewPage(conn, cursor, 'PTF5_DB')
    Main.show()
    app.exec()

    conn.close()
    app.quit()
    print('finish')