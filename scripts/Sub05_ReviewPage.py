# Title: This script include a class to design a review database page.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/25/2024
# ======================================================================================================================

# Importing the required libraries.
import sys
import sqlite3
import numpy as np
from matplotlib import cm
from matplotlib.colors import to_hex, LinearSegmentedColormap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QGroupBox, 
    QHBoxLayout, QVBoxLayout, QPushButton, QWidget, QMessageBox, QLabel, QFormLayout, QComboBox, QPlainTextEdit)
from PyQt5.QtGui import QFont, QBrush, QColor
from PyQt5.QtCore import Qt
from scripts.Sub02_CreateNewSQLTable import Get_DB_SummaryData, Get_Identifier_Combinations

# Define the custom cmap for the table COV colors. 
Reds = cm.get_cmap('Reds', 256)             # Get the "reds" colormap.
New  = Reds(np.linspace(0, 0.75, 256))      # Clip at 0.85 to prevent excessive dark red colors.
Custom_cmap = LinearSegmentedColormap.from_list("custom_reds", New)


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
        self.ColumnNames = ['id', 'ID-number', 'Lab Aging', 'Rep #', 
                            'ICO (Decon)', 'ISO (Decon)',
                            'ICO (base)', 'ICO (tang)', 'ISO (base)', 'ISO (tang)', 
                            'Carbonyl Peak loc (1/cm)', 'Sulfoxide Peak loc (1/cm)', 
                            'Aliphatic Peak loc 1 (1/cm)', 'Aliphatic Peak loc 2 (1/cm)', 
                            'Carbonyl Peak val', 'Sulfoxide Peak val', 
                            'Aliphatic Peak val 1', 'Aliphatic Peak val 2', 
                            'Carbonyl Area (base)', 'Sulfoxide Area (base)', 'Aliphatic Area (base)', 
                            'Carbonyl Area (tang)', 'Sulfoxide Area (tang)', 'Aliphatic Area (tang)', 
                            'Carbonyl Xmin', 'Carbonyl Xmax', 
                            'Sulfoxide Xmin', 'Sulfoxide Xmax', 
                            'Aliphatic Xmin', 'Aliphatic Xmax']
        self.SQL_ColumnNames = [
            'id', 'Bnumber', 'Lab_Aging', 'RepNumber',
            'Deconv_ICO', 'Deconv_ISO',        
            'ICO_Baseline', 'ICO_Tangential', 'ISO_Baseline', 'ISO_Tangential',
            'Carbonyl_Peak_Wavenumber', 'Sulfoxide_Peak_Wavenumber', 
            'Aliphatic_Peak_Wavenumber_1', 'Aliphatic_Peak_Wavenumber_2', 
            'Carbonyl_Peak_Absorption', 'Sulfoxide_Peak_Absorption', 
            'Aliphatic_Peak_Absorption_1', 'Aliphatic_Peak_Absorption_2', 
            'Carbonyl_Area_Baseline',   'Sulfoxide_Area_Baseline',   'Aliphatic_Area_Baseline', 
            'Carbonyl_Area_Tangential', 'Sulfoxide_Area_Tangential', 'Aliphatic_Area_Tangential', 
            'Carbonyl_Min_Wavenumber', 'Carbonyl_Max_Wavenumber', 
            'Sulfoxide_Min_Wavenumber', 'Sulfoxide_Max_Wavenumber', 
            'Aliphatic_Min_Wavenumber', 'Aliphatic_Max_Wavenumber']
        self.ColumnNamesAnalysis = [
            'B_Number', 'Lab_Aging_Condition', 'Num_Data', 
            'ICO_Baseline_mean', 'ICO_Baseline_std', 'ICO_Baseline_COV', 
            'ICO_Deconv_mean', 'ICO_Deconv_std', 'ICO_Deconv_COV', 
            'ICO_Tangential_mean', 'ICO_Tangential_std', 'ICO_Tangential_COV', 
            'ISO_Baseline_mean', 'ISO_Baseline_std', 'ISO_Baseline_COV', 
            'ISO_Deconv_mean', 'ISO_Deconv_std', 'ISO_Deconv_COV', 
            'ISO_Tangential_mean', 'ISO_Tangential_std', 'ISO_Tangential_COV', 
            'Aliphatic_Area_Baseline_mean', 'Aliphatic_Area_Baseline_std', 'Aliphatic_Area_Baseline_COV', 
            'Aliphatic_Area_Tangential_mean', 'Aliphatic_Area_Tangential_std', 'Aliphatic_Area_Tangential_COV', 
            'Carbonyl_Peak_Wavenumber_mean', 'Carbonyl_Peak_Wavenumber_std', 'Carbonyl_Peak_Wavenumber_COV', 
            'Sulfoxide_Peak_Wavenumber_mean', 'Sulfoxide_Peak_Wavenumber_std', 'Sulfoxide_Peak_Wavenumber_COV', 
            'Carbonyl_Peak_Absorption_mean', 'Carbonyl_Peak_Absorption_std', 'Carbonyl_Peak_Absorption_COV', 
            'Sulfoxide_Peak_Absorption_mean', 'Sulfoxide_Peak_Absorption_std', 'Sulfoxide_Peak_Absorption_COV']
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
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
        self.DropDown_Bnumber.currentIndexChanged.connect(self.Function_DropDown_Bnumber)
        # Second dropdown for the Laboratory aging state. 
        Label_DropDown02 = QLabel("Select the laboratory aging level:")
        self.DropDown_LabAging = QComboBox()
        self.DropDown_LabAging.addItems(['All Aging Levels'])
        self.DropDown_LabAging.setEnabled(False)
        self.DropDown_LabAging.currentIndexChanged.connect(self.Function_DropDown_LabAging)
        # Finally, add the apply button. 
        self.Button_Fetch = QPushButton("Fetch data")
        self.Button_Fetch.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_Fetch.clicked.connect(self.Function_Button_Fetch)
        self.Button_Fetch.setFixedWidth(150)
        # Place the items in the window. 
        Section03_Layout.addWidget(Label_DropDown01)
        Section03_Layout.addWidget(self.DropDown_Bnumber)
        Section03_Layout.addWidget(Label_DropDown02)
        Section03_Layout.addWidget(self.DropDown_LabAging)
        Section03_Layout.addWidget(self.Button_Fetch, alignment=Qt.AlignHCenter)
        Section03.setLayout(Section03_Layout)
        RightLayout.addWidget(Section03, 20)
        # --------------------------------------------------------------------------------------------------------------
        # Section 04: 
        Section04 = QGroupBox("Operation")
        Section04.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section04_Layout = QVBoxLayout()
        # First button for the modification of the current selection. 
        self.Button_Modify = QPushButton("Review/Modify Selected Row")
        self.Button_Modify.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_Modify.clicked.connect(self.Function_Button_Modify)
        self.Button_Modify.setFixedSize(150, 45)
        # Second button to change the view to Analysis of DB results.
        self.Button_Analysis = QPushButton("Show Analysis Results")
        self.Button_Analysis.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_Analysis.clicked.connect(self.Function_Button_Analysis)
        self.Button_Analysis.setFixedSize(150, 45)
        # Next button for going back to the previous page.
        self.Button_Go2Main = QPushButton("Main Page")
        self.Button_Go2Main.setStyleSheet(
        """
        QPushButton:hover {background-color: lightgray;}
        QPushButton:pressed {background-color: gray;}
        """)
        self.Button_Go2Main.clicked.connect(self.Function_Button_Go2Main)
        self.Button_Go2Main.setFixedSize(100, 35)
        # Placement of the buttons. 
        Section04_Layout.addWidget(self.Button_Modify, alignment=Qt.AlignHCenter)
        Section04_Layout.addWidget(self.Button_Analysis, alignment=Qt.AlignHCenter)
        Section04_Layout.addWidget(self.Button_Go2Main, alignment=Qt.AlignHCenter)
        Section04.setLayout(Section04_Layout)
        RightLayout.addWidget(Section04, 10)
        # --------------------------------------------------------------------------------------------------------------
        # Section 04: Output section. 
        Section05 = QGroupBox("Output section (Terminal-like)")
        Section05.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section05_Layout = QVBoxLayout()
        self.Terminal = QPlainTextEdit(self)
        self.Terminal.setReadOnly(True)             # Make it read-only. User shouldn't write!
        self.Terminal.setStyleSheet("background-color: black; color: white;")
        self.Terminal.appendPlainText(">>> Review_Database_Results()\n")
        Section05_Layout.addWidget(self.Terminal)
        Section05.setLayout(Section05_Layout)
        RightLayout.addWidget(Section05, 70)
        # --------------------------------------------------------------------------------------------------------------
        # Final placement of the right and left layouts. 
        layout.addLayout(LeftLayout, 70)
        layout.addLayout(RightLayout, 30)
    # ------------------------------------------------------------------------------------------------------------------
    def ShowEvent(self, event):
        # Update the identifier combinations. 
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
        self.Function_Button_Fetch()
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
        self.Label_NumUniqueLabAge.setText(f'{SummaryData["NumUniqueLabAging"]}')
        self.Label_NumUniqueBnumLabAge.setText(f'{SummaryData["NumUniqueBnumLabAge"]}')
        # Return Nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_Bnumber(self):
        # First, empty the table. 
        self.Table.clearSelection()
        self.Label_NumFetchedRows.setText('Number of fetched data (rows): 0')
        self.Table.setRowCount(10)
        for row_idx in range(10):
            for col_idx in range(len(self.ColumnNames)):
                self.Table.setItem(row_idx, col_idx, QTableWidgetItem(''))
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
            self.DropDown_LabAging.addItems(['All Aging Levels'] + list(self.IdentifierCombs['Lab_Aging'].unique()))
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(True)
        else:
            # A specific B-number was selected. 
            Bnumber = self.DropDown_Bnumber.currentText()
            TempDF = self.IdentifierCombs[self.IdentifierCombs['Bnumber'] == Bnumber]
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'] + list(TempDF['Lab_Aging'].unique()))
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(True)
        # Return nothing.
        return
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_LabAging(self):
        # Empty the table.
        self.Table.clearSelection() 
        self.Label_NumFetchedRows.setText('Number of fetched data (rows): 0')
        self.Table.setRowCount(10)
        for row_idx in range(10):
            for col_idx in range(len(self.ColumnNames)):
                self.Table.setItem(row_idx, col_idx, QTableWidgetItem(''))
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Fetch(self):
        # First, read the filters. 
        self.Table.clearSelection()
        Bnumber  = self.DropDown_Bnumber.currentText()
        LabAging = self.DropDown_LabAging.currentText()
        if self.DropDown_Bnumber.currentIndex() == 0:
            return
        elif self.DropDown_Bnumber.currentIndex() == 1:         # For all binders. 
            if self.DropDown_LabAging.currentIndex() == 0:    # For all aging levels. 
                self.cursor.execute(f"SELECT {', '.join(self.SQL_ColumnNames)} FROM FTIR")
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
        # Modify the table with the row value
        self.Label_NumFetchedRows.setText(f'Number of fetched data (rows): {len(Rows)}')
        self.Table.setRowCount(len(Rows))
        for row_idx, row_data in enumerate(Rows):
            for col_idx, cell_data in enumerate(row_data):
                if type(cell_data) == float:
                    item = QTableWidgetItem(f'{cell_data:.4f}')
                else:
                    item = QTableWidgetItem(str(cell_data))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.Table.setItem(row_idx, col_idx, item)
        # Print the selection to the terminal.
        Msg = f'>>> "{len(Rows)}" rows found in the Database, for:\n>>>\tBnumber: {Bnumber}\n>>>\tAging: {LabAging}'
        self.Terminal.appendPlainText(Msg)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Go2Main(self):
        """
        This function simply clear the current page and move to the main page.
        """
        # Clear the table and drop down menus. 
        self.Table.clearSelection()
        self.DropDown_Bnumber.setCurrentIndex(0)
        self.DropDown_LabAging.setCurrentIndex(0)
        self.Table.setRowCount(10)
        for row_idx in range(10):
            for col_idx in range(len(self.ColumnNames)):
                self.Table.setItem(row_idx, col_idx, QTableWidgetItem(''))
        # Move to the main page. 
        self.stack.setCurrentIndex(0)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Modify(self):
        # First check if a row is selected or not. 
        SelectedRow = self.Table.currentRow()
        if SelectedRow == -1:
            QMessageBox.warning(self, "Row Selection Error", 
                                f"Please select a row in the table to review/Modify its FTIR calculations.")
            return
        # Otherwise, fetch the data for this row from the database. 
        ID = int(self.Table.item(SelectedRow, 0).text())
        # Call Stack 3 and send the ID. 
        self.shared_data.data = ID
        self.stack.setCurrentIndex(2)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Analysis(self):
        # First check which view needed to be shown.
        if self.Button_Analysis.text() == "Show Analysis Results":
            # First of all, check if the analysis is available. 
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", ("FTIR_Analysis_DB",))
            Response = self.cursor.fetchone()
            if not Response: 
                # Such table is not existed and user need to first analyze the results. 
                QMessageBox.critical(self, "Analysis NOT available", 
                                     f"The analysis results are NOT available. Please use the 'Main Page' button and " + 
                                     f"go back to the main page. Then, click on 'Analyze DB and Export to Excel' " + 
                                     f"button to perform the analysis and then use this page for visualization.")
                return
            # If results are available, prepare the page. 
            self.DropDown_Bnumber.setEnabled(False)
            self.DropDown_Bnumber.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(False)
            self.DropDown_LabAging.setCurrentIndex(0)
            self.Button_Fetch.setEnabled(False)
            self.Button_Modify.setEnabled(False)
            self.Button_Go2Main.setEnabled(False)
            self.Terminal.appendPlainText(f"\n>>> Moving to the Analysis of Results view:")
            # Get the results from the DB.
            self.cursor.execute(f"SELECT {', '.join(self.ColumnNamesAnalysis)} FROM FTIR_Analysis_DB") 
            Rows = self.cursor.fetchall()
            # Clear the table. 
            self.Table.clearContents()
            self.Table.clearSelection()
            self.Table.setColumnCount(len(self.ColumnNamesAnalysis))
            self.Table.setHorizontalHeaderLabels(self.ColumnNamesAnalysis)
            self.Table.setRowCount(len(Rows))
            # Fill the table with the new analysis results.
            for row_idx, row_data in enumerate(Rows):
                for col_idx, cell_data in enumerate(row_data):
                    if col_idx in [5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38]:
                        try:
                            item = QTableWidgetItem(f'{cell_data*100:.1f}%')
                            ColorNumber = Get_Color_4_COV(cell_data)
                            item.setBackground(QBrush(QColor(ColorNumber)))
                        except:
                            item = QTableWidgetItem('None')
                    elif type(cell_data) == float:
                        item = QTableWidgetItem(f'{cell_data:.4f}')
                    else:
                        item = QTableWidgetItem(str(cell_data))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.Table.setItem(row_idx, col_idx, item)
            # Change the text on the button. 
            self.Button_Analysis.setText('Show Database')
        else:
            # Show the database content. 
            self.DropDown_Bnumber.setEnabled(True)
            self.DropDown_Bnumber.setCurrentIndex(0)
            self.Button_Modify.setEnabled(True)
            self.Button_Go2Main.setEnabled(True)
            self.Button_Fetch.setEnabled(True)
            self.Terminal.appendPlainText(f"\n>>> Moving to the DB view:")
            # Clear the table. 
            self.Table.clearContents()
            self.Table.clearSelection()
            self.Table.setColumnCount(len(self.ColumnNames))
            self.Table.setHorizontalHeaderLabels(self.ColumnNames)
            self.Table.setRowCount(10)
            # change the name. 
            self.Button_Analysis.setText('Show Analysis Results')
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
        return to_hex(Custom_cmap(normalized_value))  # Get color from Reds colormap
    # Use "red" for more than 50%. 
    else:
        return to_hex((1.0, 0.0, 0.0))  # Bright red
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Connect to a SQL database. 
    conn = sqlite3.connect("C:\\Users\\SF.Abdollahi.ctr\\OneDrive - DOT OST\\FTIR_Temp\\PTF5_DB.db")
    cursor = conn.cursor()

    Main = DB_ReviewPage(conn, cursor, 'PTF5_DB')
    Main.show()
    app.exec()


    conn.close()
    app.quit()
    print('finish')
