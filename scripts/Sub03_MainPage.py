# Title: This script include classes for the main page of the AutoFTIR.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/25/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import sys
import json
import sqlite3
import traceback
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSpinBox, QDoubleSpinBox, QLabel, \
    QPushButton, QWidget, QGridLayout, QFormLayout, QLineEdit, QFileDialog, QMessageBox, QGroupBox, QProgressBar, \
    QPlainTextEdit, QStackedWidget, QCheckBox, QDialog, QComboBox, QTableWidget, QTableWidgetItem, QAction, \
    QProgressDialog, QListWidget
from PyQt5.QtGui import QPixmap, QFont, QRegExpValidator, QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt, QRegExp
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scripts.Sub02_CreateNewSQLTable import Get_DB_SummaryData, Append_to_Database, Get_Info_From_Name, \
    Recalculate_Indices, Get_Unique_Aging_Levels, Is_Valid_Aging_Name, Count_Aging_Collisions, Rename_Aging_Level, \
    Count_Modified_Aging_Records, Restore_Original_Aging_Levels, Get_Available_Rep_Number, Update_Record_Identifiers, \
    Count_Modified_Identifier_Records, Restore_Original_Identifiers, Check_Database_File, Merge_Databases, \
    Find_Common_Records
from scripts.Sub04_FTIR_Analysis_Functions import Read_FTIR_Data, Baseline_Adjustment_ALS, Normalization_Method_B, \
    Calc_Aliphatic_Area, Calc_Carbonyl_Area, Calc_Sulfoxide_Area, Array_to_Binary, Binary_to_Array, Find_Peaks, \
    Normalization_Method_A, Normalization_Method_C, Normalization_Method_D
from scripts.Sub05_ReviewPage import DB_ReviewPage, Dialog_Button_Style
from scripts.Sub06_FTIR_RevisePage import Revise_FTIR_AnalysisPage, FloatDelegate
from scripts.Sub07_Deconvolution_Analysis import Run_Deconvolution, gaussian_bell
from scripts.Sub08_FTIR_PlotPage import FTIR_PlotPage

# The aging levels always offered when entering record details, in addition to any other level in the database.
Default_Aging_Levels = ["ORG", "RTFO", "1PAV", "2PAV", "1PNV", "2PNV", "Extraction"]



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
        self.conn = conn                # connection to the SQL database.
        self.cursor = cursor            # cursor for running the SQL commands.
        self.SwitchDatabase = False     # If the user closed this window to work on another database.
        # Create shared data object
        self.shared_data = SharedData()
        # Create QStackedWidget.
        self.stack = QStackedWidget()
        # Create pages
        self.main_page = MainPage(conn, cursor, DB_Name, DB_Folder, self.stack)
        self.db_review_page = DB_ReviewPage(conn, cursor, DB_Name, DB_Folder, self.stack, self.shared_data)
        self.FTIR_revise_page = Revise_FTIR_AnalysisPage(conn, cursor, DB_Name, DB_Folder, self.stack, self.shared_data)
        self.FTIR_plot_page = FTIR_PlotPage(conn, cursor, DB_Name, DB_Folder, self.stack, self.shared_data)
        # Add pages to the stack
        self.stack.addWidget(self.main_page)            # This page has stack index 0
        self.stack.addWidget(self.db_review_page)       # This page has stack index 1
        self.stack.addWidget(self.FTIR_revise_page)     # This page has stack index 2.
        self.stack.addWidget(self.FTIR_plot_page)       # This page has stack index 3.
        # Set the stack as the central widget
        self.setCentralWidget(self.stack)
        # Create the menu bar.
        self.Create_MenuBar()
    # ------------------------------------------------------------------------------------------------------------------
    def Create_MenuBar(self):
        """
        This function creates the top-level menu bar for the program. "File" includes the "Add Data to DB" and "Add Data
        to DB (Batch Mode)" actions (the latter inactive for now), a separator, the "Switch DBs..." and "Merge DBs"
        actions, a separator, and the "Exit" action, "Edit" includes the "Edit Aging Levels..." and "Edit Selected
        Record..." actions, a separator, and the
        "Restore Original ID-numbers and Aging Levels..." action, "View" includes four page-navigation actions
        (Main/Review/Analysis/Plot), a separator, and the "Select Columns for Review Panel..."/"Select Columns for
        Analysis Panel..." actions, and "Run" includes the "Re-calculate DB..." action. The other menus are placeholders
        for now.
        """
        MenuBar = self.menuBar()
        MenuBar.setStyleSheet("""
        QMenuBar { background-color: #f0f0f0; color: #000; }
        QMenuBar::item { background-color: transparent; color: #000; }
        QMenuBar::item:selected { background-color: #DCECF9; color: #000; }
        QMenuBar::item:pressed { background-color: #B7D9F2; color: #000; }
        QMenu { background-color: #ffffff; color: #000; border: 1px solid #B0B0B0; }
        QMenu::item { background-color: transparent; color: #000; }
        QMenu::item:selected { background-color: #DCECF9; color: #000; }
        QMenu::item:pressed { background-color: #B7D9F2; color: #000; }
        QMenu::item:disabled { background-color: transparent; color: #A0A0A0; }
        """)
        Menu_File = MenuBar.addMenu("&File")
        Menu_Edit = MenuBar.addMenu("&Edit")
        Menu_View = MenuBar.addMenu("&View")
        Menu_Run = MenuBar.addMenu("&Run")
        MenuBar.addMenu("&Help")
        # "Add Data to DB" action, which is only active when its button on the Main page is.
        self.Action_AddData = QAction("Add Data to DB", self)
        self.Action_AddData.triggered.connect(self.Add_Data_Function)
        Menu_File.addAction(self.Action_AddData)
        Menu_File.aboutToShow.connect(self.Sync_File_Menu)
        # "Add Data to DB (Batch Mode)" action, which is inactive for now.
        Action_AddDataBatch = QAction("Add Data to DB (Batch Mode)", self)
        Action_AddDataBatch.setEnabled(False)
        Menu_File.addAction(Action_AddDataBatch)
        Menu_File.addSeparator()
        # "Switch DBs..." action.
        Action_SwitchDB = QAction("Switch DBs...", self)
        Action_SwitchDB.triggered.connect(self.Switch_Database_Function)
        Menu_File.addAction(Action_SwitchDB)
        # "Merge DBs" action.
        Action_MergeDBs = QAction("Merge DBs", self)
        Action_MergeDBs.triggered.connect(self.Merge_Databases_Function)
        Menu_File.addAction(Action_MergeDBs)
        Menu_File.addSeparator()
        # "Exit" action.
        Action_Exit = QAction("Exit", self)
        Action_Exit.triggered.connect(self.close)
        Menu_File.addAction(Action_Exit)
        # "Edit Aging Levels..." action.
        Action_EditAging = QAction("Edit Aging Levels...", self)
        Action_EditAging.triggered.connect(self.Edit_Aging_Levels_Function)
        Menu_Edit.addAction(Action_EditAging)
        # "Edit Selected Record..." action.
        Action_EditRecord = QAction("Edit Selected Record...", self)
        Action_EditRecord.triggered.connect(self.Edit_Selected_Record_Function)
        Menu_Edit.addAction(Action_EditRecord)
        Menu_Edit.addSeparator()
        # "Restore Original ID-numbers and Aging Levels..." action.
        Action_RestoreOriginal = QAction("Restore Original ID-numbers and Aging Levels...", self)
        Action_RestoreOriginal.triggered.connect(self.Restore_Original_Identifiers_Function)
        Menu_Edit.addAction(Action_RestoreOriginal)
        # Page-navigation actions.
        Action_ViewMain = QAction("Main Page", self)
        Action_ViewMain.triggered.connect(self.Function_View_MainPage)
        Menu_View.addAction(Action_ViewMain)
        Action_ViewReview = QAction("Review Page", self)
        Action_ViewReview.triggered.connect(self.Function_View_ReviewPage)
        Menu_View.addAction(Action_ViewReview)
        Action_ViewAnalysis = QAction("Analysis Page", self)
        Action_ViewAnalysis.triggered.connect(self.Function_View_AnalysisPage)
        Menu_View.addAction(Action_ViewAnalysis)
        Action_ViewPlot = QAction("Plot Page", self)
        Action_ViewPlot.triggered.connect(self.Function_View_PlotPage)
        Menu_View.addAction(Action_ViewPlot)
        Menu_View.addSeparator()
        # "Select Columns for Review Panel..." action.
        Action_SelectColumns = QAction("Select Columns for Review Panel...", self)
        Action_SelectColumns.triggered.connect(self.db_review_page.Open_Column_Selector_Dialog)
        Menu_View.addAction(Action_SelectColumns)
        # "Select Columns for Analysis Panel..." action.
        Action_SelectColumnsAnalysis = QAction("Select Columns for Analysis Panel...", self)
        Action_SelectColumnsAnalysis.triggered.connect(self.db_review_page.Open_Column_Selector_Dialog_Analysis)
        Menu_View.addAction(Action_SelectColumnsAnalysis)
        # "Re-calculate DB..." action.
        Action_Recalculate = QAction("Re-calculate DB...", self)
        Action_Recalculate.triggered.connect(self.Recalculate_DB_Function)
        Menu_Run.addAction(Action_Recalculate)
    # ------------------------------------------------------------------------------------------------------------------
    def Sync_File_Menu(self):
        # The "Add Data to DB" button is disabled while files are being analyzed, so its menu item should be as well.
        self.Action_AddData.setEnabled(self.main_page.Button_AddData.isEnabled())
    # ------------------------------------------------------------------------------------------------------------------
    def Add_Data_Function(self):
        # This function clicks the "Add Data to DB" button of the Main page, after moving to that page to show the work.
        self.stack.setCurrentIndex(0)
        self.main_page.Button_AddData.click()
    # ------------------------------------------------------------------------------------------------------------------
    def Switch_Database_Function(self):
        """
        This function saves the current database and closes this window, so "Main_GUI.py" shows the welcome page again
        to load or create another database. Accepted and modified records are already saved at the time they are
        accepted, but a file or record the user is still working on is not, so a confirmation is asked first in that
        case, rather than saving results the user did not review.
        """
        NotSaved = []
        if self.main_page.Button_SaveProgress.isEnabled():
            NumFiles = len(self.main_page.CurrentFileList) - self.main_page.CurrentFileIndex
            NotSaved.append(f"The analysis on the Main page is not finished, so the current file and the other files "
                            f"not accepted yet ({NumFiles} in total) will not be saved.")
        if self.stack.currentIndex() == 2:
            NotSaved.append("The changes to the record open on the Modify page will not be saved.")
        if len(NotSaved) > 0:
            Question = QMessageBox(self)
            Question.setIcon(QMessageBox.Question)
            Question.setWindowTitle("Switch Database Confirmation")
            Question.setText('\n\n'.join(NotSaved) + "\n\nAll accepted records are already saved. Do you want to "
                                                     "continue?")
            Question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            Question.setDefaultButton(QMessageBox.No)
            if Question.exec_() != QMessageBox.Yes:
                return
        try:
            self.conn.commit()
        except sqlite3.Error as Err:
            QMessageBox.critical(self, "Database Error!", f"The current database could not be saved, so it stays "
                                                          f"open.\n\n{Err}")
            return
        self.SwitchDatabase = True
        self.close()
    # ------------------------------------------------------------------------------------------------------------------
    def Merge_Databases_Function(self):
        """
        This function opens the modal "Merge DBs" dialog. If the merge was successful, it shows the result, and then
        continues as if the user clicked on "Switch DBs...".
        """
        Dialog = MergeDatabasesDialog(self.conn, self)
        if Dialog.exec_() != QDialog.Accepted:
            return
        QMessageBox.information(self, "Merge DBs", Dialog.ResultMessage)
        self.Switch_Database_Function()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_View_MainPage(self):
        self.stack.setCurrentIndex(0)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_View_ReviewPage(self):
        self.Navigate_To_Review_Page(ShowAnalysis=False)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_View_AnalysisPage(self):
        self.Navigate_To_Review_Page(ShowAnalysis=True)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_View_PlotPage(self):
        self.stack.setCurrentIndex(3)
    # ------------------------------------------------------------------------------------------------------------------
    def Navigate_To_Review_Page(self, ShowAnalysis):
        """
        Switches to the Review page, showing its Database or Analysis Results view as requested. If
        "db_review_page" isn't already showing that view, this toggles it via its own "Function_Button_Analysis" --
        the same method its "Analysis Results Page"/"Database Page" button uses -- so navigating here to the
        Analysis view still prompts to re-run the analysis exactly as clicking that button would.
        """
        if self.db_review_page.InAnalysisView != ShowAnalysis:
            self.db_review_page.Function_Button_Analysis()
        self.stack.setCurrentIndex(1)
    # ------------------------------------------------------------------------------------------------------------------
    def Edit_Aging_Levels_Function(self):
        """
        This function opens the modal "Edit Aging Levels" dialog, which freezes the main window until it is closed, and
        updates all pages if the database was changed.
        """
        LabelsBefore = self.FTIR_plot_page.Get_Auto_Labels()
        Dialog = EditAgingLevelsDialog(self.conn, self.cursor, self)
        if Dialog.exec_() != QDialog.Accepted:
            return
        self.Refresh_Pages_After_Identifier_Change(LabelsBefore)
        QMessageBox.information(self, "Edit Aging Levels", Dialog.ResultMessage)
    # ------------------------------------------------------------------------------------------------------------------
    def Edit_Selected_Record_Function(self):
        """
        This function opens the modal "Edit Selected Record" dialog for the record selected on the Review page, and
        updates all pages if the database was changed. The Analysis Results view has no records to select, so it counts
        as not being on the Review page.
        """
        if self.stack.currentIndex() != 1 or self.db_review_page.InAnalysisView:
            self.Navigate_To_Review_Page(ShowAnalysis=False)
            QMessageBox.critical(self, "Review Page Required!",
                                 "You should first go to the Review page and select the record you want to change. "
                                 "You are now on the Review page.")
            return
        idx, ID = self.db_review_page.Check_Row_Selection(ActionLabel='change')
        if (ID == -1) or (idx == -1):
            return
        LabelsBefore = self.FTIR_plot_page.Get_Auto_Labels()
        Dialog = EditRecordDialog(self.conn, self.cursor, ID, self)
        if Dialog.exec_() != QDialog.Accepted:
            return
        self.Refresh_Pages_After_Identifier_Change(LabelsBefore)
        QMessageBox.information(self, "Edit Selected Record", Dialog.ResultMessage)
    # ------------------------------------------------------------------------------------------------------------------
    def Restore_Original_Identifiers_Function(self):
        """
        This function brings back the original B-number, aging level, and repetition number of all modified records from
        their backup columns, after asking for a confirmation, and updates all pages.
        """
        NumModified = Count_Modified_Identifier_Records(self.cursor)
        if NumModified == 0:
            QMessageBox.information(self, "Restore Original Values", "There are no modified records to restore.")
            return
        Question = QMessageBox(self)
        Question.setIcon(QMessageBox.Question)
        Question.setWindowTitle("Restore Original Values Confirmation")
        Question.setText(f"This will restore the original ID-number, aging level, and repetition number of "
                         f"{NumModified} record(s), and all modifications made to them will be lost.\n\n"
                         f"Do you want to continue?")
        Question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        Question.setDefaultButton(QMessageBox.No)
        if Question.exec_() != QMessageBox.Yes:
            return
        LabelsBefore = self.FTIR_plot_page.Get_Auto_Labels()
        try:
            NumRestored, NumRenumbered = Restore_Original_Identifiers(self.conn, self.cursor)
        except sqlite3.Error as Err:
            QMessageBox.critical(self, "Database Error!", f"The database was not changed.\n\n{Err}")
            return
        self.Refresh_Pages_After_Identifier_Change(LabelsBefore)
        Msg = f'The original values of {NumRestored} record(s) were restored.'
        if NumRenumbered > 0:
            Msg += (f'\n\n{NumRenumbered} of them got a new repetition number, since their original number is now used '
                    f'by another record.')
        QMessageBox.information(self, "Restore Original Values", Msg)
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh_Pages_After_Identifier_Change(self, LabelsBefore):
        """
        This function updates all pages after B-numbers or aging levels were changed. This is done explicitly, since the
        current page stays visible behind a modal dialog and therefore never receives a "showEvent" to refresh itself.
        "LabelsBefore" is the plot page's "Get_Auto_Labels" output from before the change.
        """
        self.main_page.Sync_Summary_Info()
        self.db_review_page.Refresh_After_Identifier_Change()
        self.FTIR_plot_page.Refresh_After_Identifier_Change(LabelsBefore)
    # ------------------------------------------------------------------------------------------------------------------
    def Recalculate_DB_Function(self):
        """
        This function re-calculates the Baseline, Tangential, and Deconvolution areas/indices for every non-outlier
        record in the database, from data already stored for each record (it does not re-run baseline correction, peak
        detection, or Gaussian fitting). This repairs records whose stored indices went out of sync with their stored
        Gaussian lists/boundaries. The program is frozen (via a modal, non-cancellable progress dialog) while this runs,
        to prevent the user from interacting with the rest of the program mid-update.
        """
        # First, confirm this potentially long, irreversible operation with the user.
        Question = QMessageBox()
        Question.setIcon(QMessageBox.Question)
        Question.setWindowTitle("Re-calculate Database Confirmation")
        Question.setText(
            "This will recompute the Baseline, Tangential, and Deconvolution areas/indices for every non-outlier "
            "record in the database, from the spectrum, boundaries, and Gaussian fits already stored for each record, "
            "and overwrite the currently stored values. Outlier records are left untouched. This cannot be undone.\n\n"
            "Do you want to continue?")
        Question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        Question.setDefaultButton(QMessageBox.No)
        if Question.exec_() != QMessageBox.Yes:
            return
        # --------------------------------------------------------------------------------------------------------------
        # Prepare and show a modal, non-cancellable progress dialog to freeze the program while recalculating.
        self.cursor.execute("SELECT COUNT(*) FROM FTIR")
        NumRows = self.cursor.fetchone()[0]
        Progress = QProgressDialog("Re-calculating database indices...", None, 0, max(NumRows, 1), self)
        Progress.setWindowTitle("Re-calculate DB")
        Progress.setWindowModality(Qt.ApplicationModal)
        Progress.setMinimumDuration(0)
        Progress.setValue(0)
        Progress.show()
        def Update_Progress(NumProcessed, Total):
            Progress.setMaximum(max(Total, 1))
            Progress.setValue(NumProcessed)
            QApplication.processEvents()
        # Run the recalculation.
        Summary = Recalculate_Indices(self.conn, self.cursor, progress_callback=Update_Progress)
        Progress.close()
        # --------------------------------------------------------------------------------------------------------------
        # Refresh the summary information shown on the pages, since areas/indices may have changed.
        self.main_page.Sync_Summary_Info()
        self.db_review_page.Sync_Summary_Info()
        # Report the results to the user.
        Msg = (f"Re-calculation finished.\n\n"
               f"Rows processed: {Summary['NumRows']}\n"
               f"Rows updated: {Summary['NumUpdated']}\n"
               f"Rows skipped (outliers or errors): {Summary['NumSkipped']}")
        if Summary['Errors']:
            Msg += "\n\nThe following rows raised an error and were left unchanged:\n" + \
                   "\n".join(f"  id={ErrID}: {ErrMsg}" for ErrID, ErrMsg in Summary['Errors'][:10])
            if len(Summary['Errors']) > 10:
                Msg += f"\n  ... and {len(Summary['Errors']) - 10} more."
        QMessageBox.information(self, "Re-calculate DB", Msg)
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
        self.WaveNumberRanges = {}
        self.CurBinderInfo = {'Bnumber': -1, 'RepNum': -1, 'LabAging': ''}  # To share binder info between functions.
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
            "Plot": """
        QPushButton:enabled {
            background-color: #C9B6E4; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: #A88FC9; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
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
        Label01 = QLabel("Number of Data:")
        self.Label_NumData = QLabel(f'{SummaryData["NumRows"]}')
        Label02 = QLabel("Number of Valid Data:")
        self.Label_NumValidData = QLabel(f'{SummaryData["NumValidRows"]}')
        Label03 = QLabel("Avg Number Replicates:")
        self.Label_AvgNumReplicates = QLabel(f'{SummaryData["AvgNumRep"]:.1f}')
        # Create the right side labels in Section 01.
        Label04 = QLabel("Number of Unique B-Numbers:")
        self.Label_NumUniqueBnum = QLabel(f'{SummaryData["NumUniqueBnumber"]}')
        Label05 = QLabel("Number of Unique Lab Agings:")
        self.Label_NumUniqueLabAge = QLabel(f'{SummaryData["NumUniqueLabAging"]}')
        Label06 = QLabel("Number of Unique B-Number/Lab Aging:")
        self.Label_NumUniqueBnumLabAge = QLabel(f'{SummaryData["NumUniqueBnumLabAge"]}')
        # Syncing button.
        self.Button_Sync = QPushButton("Refresh Summay")
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
        Label_Sec2_1 = QLabel("File Name for Current Analysis:")
        self.Label_CurrentFileName = QLabel('Waiting for File...')
        FormLayout_Sec2_top.addRow(Label_Sec2_1, self.Label_CurrentFileName)
        self.Label_NumFilesProgress = QLabel(f"Number of Selected Files: N/A")
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
        Titles = ['Wide Range Data', 'Carbonyl Area', 'Sulfoxide Area', 'Aliphatic Area']
        for i in range(4):
            if i >= 2:
                self.axes[i].set_xlabel('Wavenumber (1/cm)', fontsize=9, fontweight='bold', color='k')
            if i in [0, 2]:
                self.axes[i].set_ylabel('Normalized Absorption', fontsize=9, fontweight='bold', color='k')
            self.axes[i].set_title(Titles[i], fontsize=11, fontweight='bold', color='k')
            self.axes[i].grid(which='both', color='gray', alpha=0.1)
            Xticks = self.axes[i].get_xticks()
            self.axes[i].set_xticks(Xticks)
            self.axes[i].set_xticklabels(f'{num:,.0f}' for num in Xticks)
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
        self.Button_AddData.clicked.connect(self.Add_More_Data_Function)
        self.Button_AddData.setStyleSheet(self.PushButtonStyle['AddData'])
        self.Button_AddData.setSizePolicy(self.Button_AddData.sizePolicy().Expanding, 
                                          self.Button_AddData.sizePolicy().Preferred)
        Section03_Layout.addWidget(self.Button_AddData)
        # Button for review the database. 
        self.Button_ReviewDB = QPushButton("Review && Edit DB")
        self.Button_ReviewDB.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_ReviewDB.clicked.connect(self.Review_Edit_DB_Function)
        self.Button_ReviewDB.setStyleSheet(self.PushButtonStyle['Review'])
        self.Button_ReviewDB.setSizePolicy(self.Button_ReviewDB.sizePolicy().Expanding,
                                           self.Button_ReviewDB.sizePolicy().Preferred)
        Section03_Layout.addWidget(self.Button_ReviewDB)
        # Button for going to the FTIR spectra plotting page.
        self.Button_PlotData = QPushButton("Plot Data")
        self.Button_PlotData.setFont(QFont("Arial", 10, QFont.Bold))
        self.Button_PlotData.clicked.connect(self.Plot_Data_Function)
        self.Button_PlotData.setStyleSheet(self.PushButtonStyle['Plot'])
        self.Button_PlotData.setSizePolicy(self.Button_PlotData.sizePolicy().Expanding,
                                           self.Button_PlotData.sizePolicy().Preferred)
        Section03_Layout.addWidget(self.Button_PlotData)
        Section03.setLayout(Section03_Layout)
        RightLayout.addWidget(Section03, 16)
        # --------------------------------------------------------------------------------------------------------------
        # Section 4: Adjustment for the graphs. 
        Section04 = QGroupBox("Analysis Adjustment Tool")
        Section04_Layout = QVBoxLayout()
        FormLayout_Spinbox = QFormLayout()
        self.spinboxes = []                 # A list to store the spinboxes.
        LabelTitles = ['Carbonyl Range, Min (1/cm):',  'Carbonyl Range, Max (1/cm):',
                       'Sulfoxide Range, Min (1/cm):', 'Sulfoxide Range, Max (1/cm):',
                       'Aliphatic Range, Min (1/cm):', 'Aliphatic Range, Max (1/cm):']
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
        self.Button_SaveProgress = QPushButton("Cencel")
        self.Button_SaveProgress.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_SaveProgress.setSizePolicy(self.Button_SaveProgress.sizePolicy().Expanding, 
                                               self.Button_SaveProgress.sizePolicy().Preferred)
        self.Button_SaveProgress.clicked.connect(self.SaveExit_Button_Function)        # Connect to a custom function
        self.Button_SaveProgress.setEnabled(False)
        Section04_Layout.addWidget(self.Button_SaveProgress)
        # Outlier specification button.
        self.Button_Outlier = QPushButton("Mark as Outlier")
        self.Button_Outlier.setStyleSheet(self.PushButtonStyle['Reject'])
        self.Button_Outlier.setSizePolicy(self.Button_Outlier.sizePolicy().Expanding, 
                                          self.Button_Outlier.sizePolicy().Preferred)
        self.Button_Outlier.clicked.connect(self.Outlier_Button_Function)  # Connect to a custom function
        self.Button_Outlier.setEnabled(False)
        Section04_Layout.addWidget(self.Button_Outlier)
        # OK button.
        self.Button_OK = QPushButton("OK && Accept")
        self.Button_OK.setStyleSheet(self.PushButtonStyle['AddData'])
        self.Button_OK.setSizePolicy(self.Button_OK.sizePolicy().Expanding, self.Button_OK.sizePolicy().Preferred)
        self.Button_OK.clicked.connect(self.OK_Button_Function)
        self.Button_OK.setEnabled(False)
        Section04_Layout.addWidget(self.Button_OK)
        Section04.setLayout(Section04_Layout)
        RightLayout.addWidget(Section04, 30)
        # --------------------------------------------------------------------------------------------------------------
        # Section 06: Results of the deconvolution. 
        Section06 = QGroupBox("Deconvolution Analysis Results:")
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
        Section05 = QGroupBox("Fitted Gaussians:")
        Section05_Layout = QVBoxLayout()
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
        Section05_Layout.addWidget(self.RePlot_Button)
        Section05_Layout.addWidget(self.AddNewRow_Button)
        Section05_Layout.addWidget(self.GL_Table)
        Section05.setLayout(Section05_Layout)
        RightLayout.addWidget(Section05, 44)
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
        FileList, _ = QFileDialog.getOpenFileNames(self, caption='Please Select New FTIR Test Result Files:', 
                                                   directory='', 
                                                   filter="DPT Files (*.dpt);;CSV Files (*.csv);;All Files (*)")
        self.CurrentFileList = FileList
        self.CurrentFileIndex= -1
        # Check on files that are selected. 
        if len(FileList) == 0:          # Do nothing in case files are NOT selected. 
            return
        # Otherwise, print the number of selected files and update the label in progress bar. 
        self.Label_NumFilesProgress.setText(f"Number of Selected/Remained Files: {len(FileList)}, {len(FileList)}")
        # disable the DB manager buttons. 
        self.Button_AddData.setEnabled(False)
        self.Button_ReviewDB.setEnabled(False)
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
                # print(f'\n\n\n\nSkipping {self.CurrentFileList[self.CurrentFileIndex]}\n\n\n\n')
                continue
    # ------------------------------------------------------------------------------------------------------------------
    def Review_Edit_DB_Function(self):
        self.stack.setCurrentIndex(1)  # Switch to the second page
    # ------------------------------------------------------------------------------------------------------------------
    def Plot_Data_Function(self):
        self.stack.setCurrentIndex(3)  # Switch to the FTIR plotting page
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
        self.axes[1].set_xticklabels(f'{num:,.0f}' for num in self.axes[1].get_xticks())
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
        self.axes[1].set_xticklabels(f'{num:,.0f}' for num in self.axes[1].get_xticks())
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
        self.axes[2].set_xticklabels(f'{num:,.0f}' for num in self.axes[2].get_xticks())
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
        self.axes[2].set_xticklabels(f'{num:,.0f}' for num in self.axes[2].get_xticks())
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
        self.axes[3].set_xticklabels(f'{num:,.0f}' for num in self.axes[3].get_xticks())
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
        self.axes[3].set_xticklabels(f'{num:,.0f}' for num in self.axes[3].get_xticks())
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
            # Clear the table. 
            self.GL_Table.clearSelection()
            self.GL_Table.setRowCount(10)
            for row_idx in range(10):
                for col_idx in range(3):
                    item = QTableWidgetItem(f'{0:.4e}')
                    self.GL_Table.setItem(row_idx, col_idx, item)
            self.RePlot_Button.setEnabled(False)
            self.AddNewRow_Button.setEnabled(False)
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
                QMessageBox.critical(self, "Unable to Read File!", 
                                     f"The file <{os.path.basename(self.CurrentFileList[i])}> was not readable! " +
                                     f"Please make sure to provide a Comma Delimiter file with two columns, (*.dpt) " +
                                     f"files are preffered.\nFile directory: " +
                                     f"{os.path.dirname(self.CurrentFileList[i])}")
                continue
        if type(Data) == type(None):
            self.CurrentFileIndex += 1  # Increase the current file index to make sure it is at end of the file list.
            Check = self.Check_EndofLoop()      # Perform the "Check" to take care of the GUI properties. 
            self.CurrentFileIndex = 0
            self.CurrentFileList = []
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
        RawData = Data.copy()
        data, NormalizationCoeff = Normalization_Method_B(data)         # Normalization method B for now. 
        self.Normalization_Coeff = NormalizationCoeff
        self.ALSLambda = 1e6
        self.ALSRatio  = 1e-1
        self.ALSNumIter= 150
        self.NormalizationMethod = "Method_B"
        X = data[:, 0]
        Y = data[:, 1] 
        self.RawData = RawData.copy()
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
        # Store the ranges in "self". 
        self.WaveNumberRanges['Carbonyl'] = Carbonyl_Range.copy()
        self.WaveNumberRanges['Sulfoxide'] = Sulfoxide_Range.copy()
        self.WaveNumberRanges['Aliphatic'] = Aliphatic_Range.copy()
        # --------------------------------------------------------------------------------------------------------------
        # Run the deconvolution method and get the results. 
        Deconv = Run_Deconvolution(X, Y)
        self.Deconv = Deconv.copy()
        Carbonyl_Gaussians = Deconv['Carbonyl_Gaussians']
        Sulfoxide_Gaussians = Deconv['Sulfoxide_Gaussians']
        Aliphatic_Gaussians = Deconv['Aliphatic_Gaussians']
        # Update the Gaussian table. 
        self.GL_Table.clearSelection()
        self.GL_Table.setRowCount(self.Deconv['Gaussian_List'].shape[0])
        for row_idx in range(self.Deconv['Gaussian_List'].shape[0]):
            for col_idx in range(3):
                item = QTableWidgetItem(f'{self.Deconv["Gaussian_List"][row_idx, col_idx]:.4e}')
                self.GL_Table.setItem(row_idx, col_idx, item)
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
        # # Plot the data. 
        self.Plotter()
        # --------------------------------------------------------------------------------------------------------------
        # Enable the adjustment buttons. 
        self.RePlot_Button.setEnabled(True)
        self.AddNewRow_Button.setEnabled(True)
        self.Button_OK.setEnabled(True)
        self.Button_Outlier.setEnabled(True)
        self.Button_SaveProgress.setEnabled(True)
        # Update the file name and remaining number of files. 
        self.Label_NumFilesProgress.setText(f"Number of Selected/Remained Files: {len(self.CurrentFileList)}, " + 
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
    def Plotter(self):
        """
        This function renew and draw the main plot and prepare it for the next analysis.  
        """
        # Extract the deconvolution results. 
        Carbonyl_Gaussians = self.Deconv['Carbonyl_Gaussians']
        Sulfoxide_Gaussians = self.Deconv['Sulfoxide_Gaussians']
        Aliphatic_Gaussians = self.Deconv['Aliphatic_Gaussians']
        # Extract the ranges for "axvspan". 
        Carbonyl_Range = self.WaveNumberRanges['Carbonyl']
        Sulfoxide_Range = self.WaveNumberRanges['Sulfoxide']
        Aliphatic_Range = self.WaveNumberRanges['Aliphatic']
        # Plot the data. 
        self.Funtion_Clear_Axes()       # First, clear the plotting axes. 
        # Plotting whole wavenumbers. 
        self.axes[0].plot(self.X, self.Y, color='k', ls='-', label='Processed Data')
        self.axes[0].plot(self.RawData[:, 0], self.RawData[:, 1], color='b', ls='-', lw=0.5, label='Raw Data')
        self.axes[0].axvspan(xmin=1620, xmax=1800, alpha=0.1, color='r', label='Carbonyl Search Area')
        self.axes[0].axvspan(xmin=970,  xmax=1070, alpha=0.1, color='y', label='Sulfoxide Search Area')
        self.axes[0].legend()
        self.axes[0].set_xlim([2000, 600])
        # For cabonyl plot.
        CIndex = np.where((self.X >= 1600) & (self.X <= 1800))[0]
        self.XC = self.X[CIndex]
        self.YC = self.Y[CIndex]
        self.CIndex = CIndex
        self.XCminIndx = np.where(self.XC >= Carbonyl_Range[0])[0][0]
        self.XCmaxIndx = np.where(self.XC <= Carbonyl_Range[1])[0][-1]
        self.XCmin = self.XC[self.XCminIndx]
        self.XCmax = self.XC[self.XCmaxIndx]
        self.CIndex2 = np.arange(self.XCminIndx, self.XCmaxIndx + 1)
        self.axes[1].plot(self.X[CIndex], self.Y[CIndex], marker='o', ms=3, color='k', ls='-', label='FTIR Data')
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
        SIndex = np.where((self.X >= 940) & (self.X <= 1100))[0]
        try:
            self.XS = self.X[SIndex]
            self.YS = self.Y[SIndex]
            self.SIndex = SIndex
            try:
                self.XSminIndx = np.where(self.XS >= Sulfoxide_Range[0])[0][0]
                self.XSmaxIndx = np.where(self.XS <= Sulfoxide_Range[1])[0][-1]
            except:
                self.XSminIndx = np.where(self.XS >= 980)[0][0]
                self.XSmaxIndx = np.where(self.XS <= 1070)[0][-1]
            self.XSmin = self.XS[self.XSminIndx]
            self.XSmax = self.XS[self.XSmaxIndx]
            self.SIndex2 = np.arange(self.XSminIndx, self.XSmaxIndx + 1)
        except Exception as err:
            print(self.X)
            print(err)
        self.axes[2].plot(self.X[SIndex], self.Y[SIndex], marker='o', ms=3, color='k', ls='-', label='FTIR Data')
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
        AIndex = np.where((self.X >= 1300) & (self.X <= 1600))[0]
        self.XA = self.X[AIndex]
        self.YA = self.Y[AIndex]
        self.AIndex = AIndex
        self.XAminIndx = np.where(self.XA >= Aliphatic_Range[0])[0][0]
        self.XAmaxIndx = np.where(self.XA <= Aliphatic_Range[1])[0][-1]
        self.XAmin = self.XA[self.XAminIndx]
        self.XAmax = self.XA[self.XAmaxIndx]
        self.AIndex2 = np.arange(self.XAminIndx, self.XAmaxIndx + 1)
        self.axes[3].plot(self.X[AIndex], self.Y[AIndex], marker='o', ms=3, color='k', ls='-', label='FTIR Data')
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
        Xlims = [[2000, 600], [1780, 1620], [1100, 940], [1600, 1300]]
        Steps = [150, 20, 20, 40]
        for i in range(4):
            self.axes[i].set_xlim(Xlims[i])
            Xticks = [Xlims[i][1] + Steps[i] * j for j in range(30)]
            self.axes[i].set_xticks(Xticks)
            self.axes[i].set_xticklabels(f'{num:,.0f}' for num in Xticks)
            self.axes[i].set_xlim(Xlims[i])
        # Redraw the canvas
        self.canvas.draw()
        # Return
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
        self.axes[0].plot(data[:, 0], data[:, 1], color='k', ls='-', label='Processed Data')
        self.axes[0].plot(self.RawData[:, 0], self.RawData[:, 1], color='b', ls='-', lw=0.5, label='Raw Data')
        self.axes[0].axvspan(xmin=1620, xmax=1800, alpha=0.1, color='r', label='Carbonyl Search Area')
        self.axes[0].axvspan(xmin=970,  xmax=1070, alpha=0.1, color='y', label='Sulfoxide Search Area')
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
        self.axes[1].plot(data[CIndex, 0], data[CIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR Data')
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
        self.axes[2].plot(data[SIndex, 0], data[SIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR Data')
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
        self.axes[3].plot(data[AIndex, 0], data[AIndex, 1], marker='o', ms=3, color='k', ls='-', label='FTIR Data')
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
        for i in range(4):
            Xticks = self.axes[i].get_xticks()
            self.axes[i].set_xticks(Xticks)
            self.axes[i].set_xticklabels(f'{num:,.0f}' for num in Xticks)
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
        Titles = ['Wide Range Data', 'Carbonyl Area', 'Sulfoxide Area', 'Aliphatic Area']
        for i in range(4):
            if i >= 2:
                self.axes[i].set_xlabel('Wavenumber (1/cm)', fontsize=9, fontweight='bold', color='k')
            if i in [0, 2]:
                self.axes[i].set_ylabel('Normalized Absorption', fontsize=9, fontweight='bold', color='k')
            self.axes[i].set_title(Titles[i], fontsize=11, fontweight='bold', color='k')
            self.axes[i].grid(which='both', color='gray', alpha=0.1)
            Xticks = self.axes[i].get_xticks()
            self.axes[i].set_xticks(Xticks)
            self.axes[i].set_xticklabels(f'{num:,.0f}' for num in Xticks)
        # Redraw the canvas
        self.canvas.draw()
        # Return nothing. 
        return
    # ------------------------------------------------------------------------------------------------------------------
    def AddNewRow_Button_Function(self):
        current_row_count = self.GL_Table.rowCount()
        self.GL_Table.insertRow(current_row_count)  # Add a new row at the end
        # Populate the new row with default values
        for column in range(self.GL_Table.columnCount()):
            self.GL_Table.setItem(current_row_count, column, QTableWidgetItem("0.0"))
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
        GL = GL[np.argsort(GL[:, 0]), :]
        # Then, find the index of the Carbonyl, Sulfoxide, and Aliphatic peaks. 
        Aliphatic_Gaussians = GL[(GL[:, 0] < 1525) & (GL[:, 0] > 1350), :]
        Aliphatic_Gaussians = Aliphatic_Gaussians[Aliphatic_Gaussians[:, 2].argsort(), :]       # Sort based on Amplitude.
        Aliphatic_Gaussians = Aliphatic_Gaussians[-2:, :]       # Took only the biggest peaks. 
        Carbonyl_Gaussians = GL[(GL[:, 0] < 1720) & (GL[:, 0] > 1660), :]
        Sulfoxide_Gaussians = GL[(GL[:, 0] < 1070) & (GL[:, 0] > 970), :]
        Index = np.argmin(np.abs(Sulfoxide_Gaussians[:, 0] - 1030))
        Index2= np.argmax(Sulfoxide_Gaussians[:, 2])
        Sulfoxide_Gaussians = Sulfoxide_Gaussians[[Index2], :]
        # Update the areas and indices. 
        CArea = (Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Carbonyl_Gaussians[:, 1])).sum()
        SArea = (Sulfoxide_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Sulfoxide_Gaussians[:, 1])).sum()
        AArea = (Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Aliphatic_Gaussians[:, 1])).sum()
        # Update the deconvolution information. 
        self.Decon_Label_CArea.setText(f'Carbonyl Area: {CArea:.2f}')
        self.Decon_Label_SArea.setText(f'Sulfoxide Area: {SArea:.2f}')
        self.Decon_Label_AArea.setText(f'Aliphatic Area: {AArea:.2f}')
        self.Decon_Label_Index.setText(f'ICO: {CArea / AArea:.4f}, ISO: {SArea / AArea:.4f}')
        # Replace the table. 
        self.GL_Table.clearSelection()
        self.GL_Table.setRowCount(GL.shape[0])
        for row_idx in range(GL.shape[0]):
            for col_idx in range(3):
                item = QTableWidgetItem(f'{GL[row_idx, col_idx]:.4e}')
                self.GL_Table.setItem(row_idx, col_idx, item)
        # Update the "self.Deconv" variable.
        self.Deconv['Gaussian_List'] = GL.copy()
        self.Deconv['Carbonyl_Gaussians'] = Carbonyl_Gaussians.copy()
        self.Deconv['Sulfoxide_Gaussians'] = Sulfoxide_Gaussians.copy()
        self.Deconv['Aliphatic_Gaussians'] = Aliphatic_Gaussians.copy()
        self.Deconv['Carbonyl_Area'] = CArea
        self.Deconv['Sulfoxide_Area'] = SArea
        self.Deconv['Aliphatic_Area'] = AArea
        self.Deconv['ICO'] = CArea / AArea
        self.Deconv['ISO'] = SArea / AArea
        # Now, call the function to replot. 
        self.Plotter()
        # Return Nothing. 
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
        self.DropDown_Aging.addItems(Default_Aging_Levels)
        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet(Dialog_Button_Style["Accept"])
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(Dialog_Button_Style["General"])
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


class EditAgingLevelsDialog(QDialog):
    """
    This class generates a modal dialog for renaming an aging level on all of its records in the database, or restoring
    the original aging levels saved in the "AgingLevel_Original" column. The dialog is accepted only if the database
    was changed, with the summary of that change available in "ResultMessage".
    """
    def __init__(self, conn, cursor, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.cursor = cursor
        self.ResultMessage = ''
        self.setWindowTitle("Edit Aging Levels")
        self.setMinimumWidth(420)
        layout = QVBoxLayout()
        # Input fields.
        self.DropDown_Aging = QComboBox(self)
        self.DropDown_Aging.addItems(Get_Unique_Aging_Levels(self.cursor))
        self.LineEdit_NewName = QLineEdit(self)
        self.LineEdit_NewName.setPlaceholderText("Enter the new aging level name ...")
        Form = QFormLayout()
        Form.addRow(QLabel('Current aging level:'), self.DropDown_Aging)
        Form.addRow(QLabel('New aging level:'), self.LineEdit_NewName)
        layout.addLayout(Form)
        layout.addWidget(QLabel('Letters and numbers only, starting with a letter, with no spaces.'))
        # Buttons. Pressing "Enter" should only ever trigger "Apply".
        self.Button_Original = QPushButton("Apply Original Labels")
        self.Button_Original.setStyleSheet(Dialog_Button_Style["Modify"])
        self.Button_Original.setAutoDefault(False)
        self.Button_Original.setEnabled(Count_Modified_Aging_Records(self.cursor) > 0)
        self.Button_Original.clicked.connect(self.Function_Apply_Original)
        self.Button_Cancel = QPushButton("Cancel")
        self.Button_Cancel.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_Cancel.setAutoDefault(False)
        self.Button_Cancel.clicked.connect(self.reject)
        self.Button_Apply = QPushButton("Apply")
        self.Button_Apply.setStyleSheet(Dialog_Button_Style["Accept"])
        self.Button_Apply.setDefault(True)
        self.Button_Apply.clicked.connect(self.Function_Apply)
        ButtonLayout = QHBoxLayout()
        ButtonLayout.addWidget(self.Button_Original)
        ButtonLayout.addStretch()
        ButtonLayout.addWidget(self.Button_Cancel)
        ButtonLayout.addWidget(self.Button_Apply)
        layout.addLayout(ButtonLayout)
        self.setLayout(layout)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Apply(self):
        """
        This function validates the new name and renames the selected aging level. On invalid input, it shows an error
        and keeps the dialog open for another try.
        """
        OldLevel = self.DropDown_Aging.currentText()
        NewLevel = self.LineEdit_NewName.text()
        if not OldLevel:
            QMessageBox.critical(self, "No Aging Level!", "There is no aging level available in the database.")
            return
        if not NewLevel:
            self.Show_Name_Error("Please enter the new aging level name.")
            return
        if not Is_Valid_Aging_Name(NewLevel):
            self.Show_Name_Error(f'"{NewLevel}" is not a valid name. Please use letters and numbers only, starting '
                                 f'with a letter, with no spaces.')
            return
        if NewLevel == OldLevel:
            self.Show_Name_Error("The new name is the same as the current aging level.")
            return
        # Renaming to an available level merges the two levels, so ask for a confirmation.
        if self.DropDown_Aging.findText(NewLevel) >= 0:
            Msg = f'The aging level "{NewLevel}" already exists, so the records of "{OldLevel}" will be merged with it.'
            NumCollisions = Count_Aging_Collisions(self.cursor, OldLevel, NewLevel)
            if NumCollisions > 0:
                Msg += (f'\n\nWarning: {NumCollisions} record(s) will then have the same ID-number, repetition number, '
                        f'and aging level as another record, and they will be treated as replicates of it.')
            if not self.Confirm("Merge Aging Levels Confirmation", Msg + '\n\nDo you want to continue?'):
                return
        try:
            NumRenamed = Rename_Aging_Level(self.conn, self.cursor, OldLevel, NewLevel)
        except sqlite3.Error as Err:
            QMessageBox.critical(self, "Database Error!", f"The database was not changed.\n\n{Err}")
            return
        self.ResultMessage = f'{NumRenamed} record(s) were changed from "{OldLevel}" to "{NewLevel}".'
        self.accept()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Apply_Original(self):
        """
        This function restores the original aging levels, after asking for a confirmation.
        """
        NumModified = Count_Modified_Aging_Records(self.cursor)
        Msg = (f'This will restore the original aging level of {NumModified} record(s), and all modifications made to '
               f'the aging levels will be lost.\n\nDo you want to continue?')
        if not self.Confirm("Apply Original Labels Confirmation", Msg):
            return
        try:
            NumRestored, NumRenumbered = Restore_Original_Aging_Levels(self.conn, self.cursor)
        except sqlite3.Error as Err:
            QMessageBox.critical(self, "Database Error!", f"The database was not changed.\n\n{Err}")
            return
        self.ResultMessage = f'The original aging level of {NumRestored} record(s) was restored.'
        if NumRenumbered > 0:
            self.ResultMessage += (f'\n\n{NumRenumbered} of them got a new repetition number, since their number was '
                                   f'already taken at their original aging level.')
        self.accept()
    # ------------------------------------------------------------------------------------------------------------------
    def Show_Name_Error(self, Msg):
        QMessageBox.critical(self, "Invalid Aging Level Name!", Msg)
        self.LineEdit_NewName.setFocus()
    # ------------------------------------------------------------------------------------------------------------------
    def Confirm(self, Title, Msg):
        Question = QMessageBox(self)
        Question.setIcon(QMessageBox.Question)
        Question.setWindowTitle(Title)
        Question.setText(Msg)
        Question.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        Question.setDefaultButton(QMessageBox.No)
        return Question.exec_() == QMessageBox.Yes
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class EditRecordDialog(QDialog):
    """
    This class generates a modal dialog for changing the B-number and aging level of a single record. The repetition
    number is not editable, and only shows what the record will get (see "Get_Available_Rep_Number"). The dialog is
    accepted only if the database was changed, with the summary of that change available in "ResultMessage".
    """
    def __init__(self, conn, cursor, RecordID, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.cursor = cursor
        self.RecordID = RecordID
        self.ResultMessage = ''
        self.cursor.execute("SELECT Bnumber, Lab_Aging, RepNumber FROM FTIR WHERE id = ?", (RecordID,))
        self.OldBnumber, self.OldLabAging, self.OldRep = self.cursor.fetchone()
        self.setWindowTitle("Edit Selected Record")
        self.setMinimumWidth(420)
        layout = QVBoxLayout()
        # Input fields.
        self.LineEdit_Bnumber = QLineEdit(str(self.OldBnumber), self)
        self.LineEdit_Bnumber.setValidator(QRegExpValidator(QRegExp("[0-9]{1,5}"), self))
        self.DropDown_Aging = QComboBox(self)
        self.DropDown_Aging.addItems(Default_Aging_Levels)
        for Level in Get_Unique_Aging_Levels(self.cursor):
            if self.DropDown_Aging.findText(Level) < 0:
                self.DropDown_Aging.addItem(Level)
        self.DropDown_Aging.setCurrentIndex(self.DropDown_Aging.findText(self.OldLabAging))
        self.Label_RepNumber = QLabel(self)
        Form = QFormLayout()
        Form.addRow(QLabel('ID-number:'), self.LineEdit_Bnumber)
        Form.addRow(QLabel('Aging level:'), self.DropDown_Aging)
        Form.addRow(QLabel('Repetition number:'), self.Label_RepNumber)
        layout.addLayout(Form)
        Hint = QLabel('The repetition number stays the same, unless it is already taken at the selected ID-number and '
                      'aging level. In that case, the record gets the next number after the largest one in use.')
        Hint.setWordWrap(True)
        layout.addWidget(Hint)
        # Buttons. Pressing "Enter" should only ever trigger "Apply".
        self.Button_Cancel = QPushButton("Cancel")
        self.Button_Cancel.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_Cancel.setAutoDefault(False)
        self.Button_Cancel.clicked.connect(self.reject)
        self.Button_Apply = QPushButton("Apply")
        self.Button_Apply.setStyleSheet(Dialog_Button_Style["Accept"])
        self.Button_Apply.setDefault(True)
        self.Button_Apply.clicked.connect(self.Function_Apply)
        ButtonLayout = QHBoxLayout()
        ButtonLayout.addStretch()
        ButtonLayout.addWidget(self.Button_Cancel)
        ButtonLayout.addWidget(self.Button_Apply)
        layout.addLayout(ButtonLayout)
        self.setLayout(layout)
        # Keep the shown repetition number up to date.
        self.LineEdit_Bnumber.textChanged.connect(self.Update_RepNumber_Label)
        self.DropDown_Aging.currentIndexChanged.connect(self.Update_RepNumber_Label)
        self.Update_RepNumber_Label()
    # ------------------------------------------------------------------------------------------------------------------
    def Update_RepNumber_Label(self):
        """
        This function shows the repetition number the record will get with the current inputs.
        """
        Text = self.LineEdit_Bnumber.text()
        NewRep = self.OldRep
        if Text:
            NewRep = Get_Available_Rep_Number(self.cursor, int(Text), self.DropDown_Aging.currentText(), self.OldRep,
                                              self.RecordID)
        if NewRep == self.OldRep:
            self.Label_RepNumber.setText(f'{NewRep}')
        else:
            self.Label_RepNumber.setText(f'{NewRep} (Rep {self.OldRep} is already taken)')
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Apply(self):
        """
        This function validates the inputs and changes the record. On invalid input, it shows an error and keeps the
        dialog open for another try.
        """
        Text = self.LineEdit_Bnumber.text()
        if not Text or int(Text) == 0:
            QMessageBox.critical(self, "Invalid ID-number!", "Please enter an ID-number greater than zero.")
            self.LineEdit_Bnumber.setFocus()
            return
        Bnumber = int(Text)
        LabAging = self.DropDown_Aging.currentText()
        if Bnumber == self.OldBnumber and LabAging == self.OldLabAging:
            QMessageBox.critical(self, "Nothing to Change!", "The ID-number and aging level are the same as the "
                                                             "current values of the record.")
            return
        try:
            NewRep = Update_Record_Identifiers(self.conn, self.cursor, self.RecordID, Bnumber, LabAging)
        except sqlite3.Error as Err:
            QMessageBox.critical(self, "Database Error!", f"The database was not changed.\n\n{Err}")
            return
        self.ResultMessage = (f'The record was changed from ID-number {self.OldBnumber}, "{self.OldLabAging}", Rep '
                              f'{self.OldRep} to ID-number {Bnumber}, "{LabAging}", Rep {NewRep}.')
        if NewRep != self.OldRep:
            self.ResultMessage += (f'\n\nThe repetition number was changed, since Rep {self.OldRep} was already taken '
                                   f'at that ID-number and aging level.')
        self.accept()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class MergeDatabasesDialog(QDialog):
    """
    This class generates a modal dialog for merging several databases into a new one. The dialog is accepted only if the
    merge was successful, with the summary of the merge available in "ResultMessage".
    """
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.ResultMessage = ''
        self.ConfigPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..//configs//config.json')
        self.setWindowTitle("Merge DBs")
        self.setMinimumWidth(640)
        layout = QVBoxLayout()
        # Selecting the databases to be merged.
        self.DropDown_Recent = QComboBox(self)
        self.DropDown_Recent.addItems(['Please select...'] + self.Get_Recent_DBs())
        self.DropDown_Recent.currentIndexChanged.connect(self.Function_DropDown_Recent)
        self.Button_Browse = QPushButton("Browse")
        self.Button_Browse.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_Browse.setAutoDefault(False)
        self.Button_Browse.clicked.connect(self.Function_Browse)
        Form = QFormLayout()
        Form.addRow(QLabel('Recent databases:'), self.DropDown_Recent)
        Form.addRow(QLabel('or select the files:'), self.Button_Browse)
        layout.addLayout(Form)
        Label_Priority = QLabel('Databases to merge, from the highest priority to the lowest. The order is important: '
                                'if you use priority for the records available in several databases, the record of the '
                                'database higher in this list is kept. Use "Move Up" and "Move Down" to change it.')
        Label_Priority.setWordWrap(True)
        layout.addWidget(Label_Priority)
        self.List_Databases = QListWidget(self)
        layout.addWidget(self.List_Databases)
        ListButtons = QHBoxLayout()
        self.Button_MoveUp = QPushButton("Move Up")
        self.Button_MoveUp.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_MoveUp.setAutoDefault(False)
        self.Button_MoveUp.clicked.connect(lambda: self.Function_Move(-1))
        ListButtons.addWidget(self.Button_MoveUp)
        self.Button_MoveDown = QPushButton("Move Down")
        self.Button_MoveDown.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_MoveDown.setAutoDefault(False)
        self.Button_MoveDown.clicked.connect(lambda: self.Function_Move(1))
        ListButtons.addWidget(self.Button_MoveDown)
        self.Button_Remove = QPushButton("Remove Selected")
        self.Button_Remove.setStyleSheet(Dialog_Button_Style["Modify"])
        self.Button_Remove.setAutoDefault(False)
        self.Button_Remove.clicked.connect(self.Function_Remove)
        ListButtons.addWidget(self.Button_Remove)
        layout.addLayout(ListButtons)
        # The merged database.
        self.Label_Directory = QLabel("Use the 'Browse' button to select the output directory...")
        self.Label_Directory.setWordWrap(True)
        self.Button_Directory = QPushButton("Browse")
        self.Button_Directory.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_Directory.setAutoDefault(False)
        self.Button_Directory.clicked.connect(self.Function_Directory)
        self.LineEdit_Name = QLineEdit(self)
        self.LineEdit_Name.setPlaceholderText("Enter the merged database name...")
        self.LineEdit_Name.setValidator(QRegExpValidator(QRegExp("^[a-zA-Z0-9_-]*$"), self.LineEdit_Name))
        Form = QFormLayout()
        Form.addRow(QLabel('Output directory:'), self.Label_Directory)
        Form.addRow(QLabel(''), self.Button_Directory)
        Form.addRow(QLabel('Merged database name:'), self.LineEdit_Name)
        layout.addLayout(Form)
        # Buttons. Pressing "Enter" should only ever trigger "Merge".
        self.Button_Cancel = QPushButton("Cancel")
        self.Button_Cancel.setStyleSheet(Dialog_Button_Style["General"])
        self.Button_Cancel.setAutoDefault(False)
        self.Button_Cancel.clicked.connect(self.reject)
        self.Button_Merge = QPushButton("Merge")
        self.Button_Merge.setStyleSheet(Dialog_Button_Style["Accept"])
        self.Button_Merge.setDefault(True)
        self.Button_Merge.clicked.connect(self.Function_Merge)
        ButtonLayout = QHBoxLayout()
        ButtonLayout.addStretch()
        ButtonLayout.addWidget(self.Button_Cancel)
        ButtonLayout.addWidget(self.Button_Merge)
        layout.addLayout(ButtonLayout)
        self.setLayout(layout)
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Recent_DBs(self):
        """
        This function returns the recent databases of the config file, with the latest one first and no repeats.
        """
        try:
            with open(self.ConfigPath, 'r') as File:
                RecentDBs = json.load(File)['Recent_DBs']
        except Exception:
            return []
        Paths = {}
        for Path in reversed(RecentDBs):
            if Path:
                Paths.setdefault(os.path.normcase(os.path.normpath(Path)), os.path.normpath(Path))
        return list(Paths.values())
    # ------------------------------------------------------------------------------------------------------------------
    def Add_To_Recent_DBs(self, Path):
        """
        This function adds the merged database to the recent databases, so it can be selected right after the merge. The
        list is only a convenience, so a problem with it should not turn a successful merge into a failed one.
        """
        try:
            Config = {}
            if os.path.isfile(self.ConfigPath):
                with open(self.ConfigPath, 'r') as File:
                    Config = json.load(File)
            Config.setdefault('Recent_DBs', []).append(Path)
            with open(self.ConfigPath, 'w') as File:
                json.dump(Config, File)
        except Exception:
            pass
    # ------------------------------------------------------------------------------------------------------------------
    def Add_Database(self, Path):
        """
        This function checks a database, and adds it to the list. Otherwise, it shows an error and does not add it.
        """
        Path = os.path.normpath(Path)
        if not os.path.isfile(Path):
            QMessageBox.critical(self, "Unable to Add Database!", f'"{Path}" was not found.')
            return
        for Index in range(self.List_Databases.count()):
            if os.path.normcase(self.List_Databases.item(Index).text()) == os.path.normcase(Path):
                QMessageBox.critical(self, "Unable to Add Database!", f'"{Path}" is already in the list.')
                return
        Error, _ = Check_Database_File(Path, RequireAllColumns=True)
        if Error:
            QMessageBox.critical(self, "Unable to Add Database!", Error)
            return
        self.List_Databases.addItem(Path)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_Recent(self):
        if self.DropDown_Recent.currentIndex() == 0:
            return              # Has no effect.
        self.Add_Database(self.DropDown_Recent.currentText())
        self.DropDown_Recent.setCurrentIndex(0)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Browse(self):
        FilePaths, _ = QFileDialog.getOpenFileNames(self, "Please select the databases to merge", "",
                                                    "Database files (*.db);;All Files (*)")
        for Path in FilePaths:
            self.Add_Database(Path)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Remove(self):
        self.List_Databases.takeItem(self.List_Databases.currentRow())
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Move(self, Step):
        # This function moves the selected database up (-1) or down (+1) in the list, keeping it selected.
        Row = self.List_Databases.currentRow()
        if Row < 0 or not 0 <= Row + Step < self.List_Databases.count():
            return
        self.List_Databases.insertItem(Row + Step, self.List_Databases.takeItem(Row))
        self.List_Databases.setCurrentRow(Row + Step)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Directory(self):
        Directory = QFileDialog.getExistingDirectory(self, "Please select the output directory for the merged database")
        if Directory:
            self.Label_Directory.setText(Directory)
    # ------------------------------------------------------------------------------------------------------------------
    def Choose_Common_Records(self, SourcePaths, Common, NumRecords):
        """
        This function asks the user what to do with the records available in several databases.

        :param SourcePaths: list of the full paths to the databases, in the order of priority.
        :param Common: the common combinations (see "Find_Common_Records").
        :param NumRecords: the total number of records with these combinations.
        :return: A dictionary of each combination with the index of the database to keep it from, or None if the user
        canceled the merge.
        """
        Question = QMessageBox(self)
        Question.setIcon(QMessageBox.Question)
        Question.setWindowTitle("Common Records")
        Question.setText(f'There are {NumRecords} records with similar ID-number/Aging level/Repetition number in the '
                         f'selected databases ({len(Common)} different combination(s)). What do you want to do?\n\n'
                         f'Use Priority: keep the record of the database higher in the list.\n'
                         f'Decide One-by-One: select the database to keep for each combination.')
        Button_Cancel = Question.addButton("Cancel the Merge", QMessageBox.RejectRole)
        Button_Cancel.setStyleSheet(Dialog_Button_Style["General"])
        Button_Priority = Question.addButton("Use Priority", QMessageBox.AcceptRole)
        Button_Priority.setStyleSheet(Dialog_Button_Style["Accept"])
        Button_OneByOne = Question.addButton("Decide One-by-One", QMessageBox.AcceptRole)
        Button_OneByOne.setStyleSheet(Dialog_Button_Style["Accept"])
        Question.setDefaultButton(Button_Cancel)
        Question.setEscapeButton(Button_Cancel)
        Question.exec_()
        if Question.clickedButton() == Button_Priority:
            return {Record: Entries[0][0] for Record, Entries in Common.items()}
        if Question.clickedButton() != Button_OneByOne:
            return None
        KeepFrom = {}
        Labels = self.Get_Database_Labels(SourcePaths)
        for Position, (Record, Entries) in enumerate(Common.items()):
            Databases = [(Index, f'{Labels[Index]}   |   ICO (Decon): {"N/A" if ICO is None else f"{ICO:.4f}"}   |   '
                                 f'ISO (Decon): {"N/A" if ISO is None else f"{ISO:.4f}"}')
                         for Index, ICO, ISO in Entries]
            Dialog = CommonRecordDialog(Record, Databases, Position + 1, len(Common), self)
            if Dialog.exec_() != QDialog.Accepted:
                return None
            KeepFrom[Record] = Dialog.SelectedIndex
        return KeepFrom
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Database_Labels(self, SourcePaths):
        # This function returns the file name of each database, or its full path if another database has the same name.
        Names = [os.path.basename(Path) for Path in SourcePaths]
        return [Path if Names.count(Name) > 1 else Name for Path, Name in zip(SourcePaths, Names)]
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Merge(self):
        """
        This function validates the inputs, asks what to do with the common records (if any), and merges the databases.
        On invalid input or a failed merge, it shows an error and keeps the dialog open for another try. If the user
        cancels at the common records, the dialog is closed to go back to the main window.
        """
        Directory = self.Label_Directory.text()
        FileName = self.LineEdit_Name.text()
        SourcePaths = [self.List_Databases.item(Index).text() for Index in range(self.List_Databases.count())]
        if len(SourcePaths) < 2:
            QMessageBox.critical(self, "Unable to Merge!", "Please add at least two databases to merge.")
            return
        if not os.path.isdir(Directory):
            QMessageBox.critical(self, "Unable to Merge!", "Please select a valid output directory, using the 'Browse' "
                                                           "button.")
            return
        if len(FileName) < 3:
            QMessageBox.critical(self, "Unable to Merge!", "Database name should contain at least 3 characters.")
            self.LineEdit_Name.setFocus()
            return
        OutputPath = os.path.normpath(os.path.join(Directory, FileName + '.db'))
        if os.path.exists(OutputPath):
            QMessageBox.critical(self, "Unable to Merge!", f'"{OutputPath}" already exists. Please use another name, '
                                                           f'since the merge does not overwrite a file.')
            self.LineEdit_Name.setFocus()
            return
        # Check for the common records.
        try:
            self.conn.commit()      # The open database may be one of the sources.
            Common, NumRecords = Find_Common_Records(SourcePaths)
        except Exception:
            QMessageBox.critical(self, "Merge Not Successful!", f"The merge was not successful, and no database was "
                                                                f"created.\n\n{traceback.format_exc()}")
            return
        KeepFrom = {}
        if len(Common) > 0:
            KeepFrom = self.Choose_Common_Records(SourcePaths, Common, NumRecords)
            if KeepFrom is None:
                self.reject()
                return
        # Merge, with a modal, non-cancellable progress dialog to freeze the program meanwhile.
        Progress = QProgressDialog("Merging the databases...", None, 0, 1, self)
        Progress.setWindowTitle("Merge DBs")
        Progress.setWindowModality(Qt.ApplicationModal)
        Progress.setMinimumDuration(0)
        Progress.setValue(0)
        Progress.show()
        def Update_Progress(NumProcessed, Total):
            Progress.setMaximum(max(Total, 1))
            Progress.setValue(NumProcessed)
            QApplication.processEvents()
        try:
            Summary = Merge_Databases(SourcePaths, OutputPath, progress_callback=Update_Progress, KeepFrom=KeepFrom)
        except Exception:
            Progress.close()
            QMessageBox.critical(self, "Merge Not Successful!", f"The merge was not successful, and no database was "
                                                                f"created.\n\n{traceback.format_exc()}")
            return
        Progress.close()
        self.Add_To_Recent_DBs(OutputPath)
        self.ResultMessage = (f'{len(SourcePaths)} databases were merged successfully, with {Summary["NumRecords"]} '
                              f'record(s), into:\n{OutputPath}')
        if Summary['NumCommon'] > 0:
            self.ResultMessage += (f'\n\n{Summary["NumCommon"]} common record(s) were left out, as only one record was '
                                   f'kept for each ID-number/Aging level/Repetition number.')
        if Summary['NumSkipped'] > 0:
            self.ResultMessage += (f'\n\n{Summary["NumSkipped"]} record(s) were skipped, since the same test (same file '
                                   f'name and raw spectrum) was already merged from an earlier database in the list.')
        if Summary['NumRenumbered'] > 0:
            self.ResultMessage += (f'\n\n{Summary["NumRenumbered"]} record(s) got a new repetition number, since their '
                                   f'number was already taken at that ID-number and aging level.')
        self.accept()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class CommonRecordDialog(QDialog):
    """
    This class generates a modal dialog asking which database to keep a common record from, with one button for each
    database. The dialog is accepted when a database is selected, available in "SelectedIndex". Closing it by the "X"
    button rejects it, which disrupts the whole merge.
    """
    def __init__(self, Record, Databases, Position, NumCombinations, parent=None):
        super().__init__(parent)
        self.SelectedIndex = None
        Bnumber, LabAging, RepNumber = Record
        self.setWindowTitle(f"Common Record ({Position} of {NumCombinations})")
        self.setMinimumWidth(420)
        layout = QVBoxLayout()
        Message = QLabel(f'The record of ID-number {Bnumber}, aging level "{LabAging}", and repetition number '
                         f'{RepNumber} was repeated. Which one do you want to keep?')
        Message.setWordWrap(True)
        layout.addWidget(Message)
        # No button is the default one, so pressing "Enter" cannot select a database by accident.
        for Index, Label in Databases:
            Button = QPushButton(Label)
            Button.setStyleSheet(Dialog_Button_Style["Accept"])
            Button.setAutoDefault(False)
            Button.clicked.connect(lambda _, Selected=Index: self.Function_Select(Selected))
            layout.addWidget(Button)
        self.setLayout(layout)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Select(self, Index):
        self.SelectedIndex = Index
        self.accept()
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
