# Title: This script connects the SBS detection model ("Sub12_SBSDetection.py") to AutoFTIR: the "Modification" tab of the
#   "Results" group box with its "More details" window, the SBS columns of the database, and the model file and state.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/06/2026
# ======================================================================================================================
#
# The model only needs the Gaussians of the deconvolution. So, it runs again whenever they change on the Main or Modify page
#   (a new file, Re-Plot, the mouse editor, or new preprocessing), and "OK & Accept" saves the results of the Gaussians that
#   it saves. "Mark as Outlier" empties the SBS columns of the record.
#
# The model file is "data/FTIR_SBS_Model.npz" by default. Another one can be selected from "Run > SBS Detection Model >
#   Select Model File...", which saves its path as "SBS_Model_File" in "configs/config.json". The same menu turns the model
#   on and off, saved as "SBS_Model_Enabled". While the model is off, or if its file is not found or not valid, the tab says
#   so, nothing is calculated, and the database is not touched.
#
# The Qt parts are here, so "Sub12_SBSDetection.py" only needs NumPy and can be used by the notebooks as well.
# ======================================================================================================================

# Importing the required libraries.
import html
import os
import traceback
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, \
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from scripts.Sub02_CreateNewSQLTable import Add_SBS_Columns, Has_SBS_Columns, SBS_Columns
from scripts.Sub04_FTIR_Analysis_Functions import Binary_to_Array
from scripts.Sub05_ReviewPage import Dialog_Button_Style
from scripts.Sub10_Rheology_Prediction import Get_Path_For_Config, Get_Project_Path, Read_Config, Write_Config
from scripts.Sub12_SBSDetection import Calculate_SBS_Indices, Get_Default_Model_Path, Index_Bands, Load_SBS_Model, \
    Spectrum_Area_Range


Config_Key = 'SBS_Model_Enabled'
Config_File_Key = 'SBS_Model_File'
Cut_Off = 0.5           # A spectrum is "Modified" if its probability is at least this.
Inactive_Reason = 'The SBS detection model is inactive. You can turn it on from "Run > SBS Detection Model".'
Result_Colors = {'Modified': '#6A3D9A', 'Unmodified': '#5D6D7E'}       # The text of the result.
Bar_Colors = {'Modified': '#CBB8E6', 'Unmodified': '#CBD3DB'}          # The bar of the probability (lighter, for its text).
Saved_Indices = ['Rh699', 'Rh1', 'Ra1', 'Ra2']                          # Saved to the database as "SBS_<name>".
# The indices of the "More details" window, by group, as (name, definition).
Index_Groups = [
    ('Height-based indices', [('Rh699', 'H699 / H1377 (polystyrene / CH3)'), ('Rh1', 'H966 / H1377 (polybutadiene / CH3)'),
                              ('Rh2', 'H966 / H813 (polybutadiene / aromatic C-H)'), ('Rh20', 'H966 / (H966 + H813)')]),
    ('Area-based indices', [('Ra699', 'A699 / A1377'), ('Ra1', 'A966 / A1377'), ('Ra2', 'A966 / A813'),
                            ('Ra20', 'A966 / (A966 + A813)')]),
    ('Indices relative to the spectrum', [
        ('I699', f'A699 / area of the spectrum ({Spectrum_Area_Range[0]:g}-{Spectrum_Area_Range[1]:g} 1/cm)'),
        ('I966', f'A966 / area of the spectrum ({Spectrum_Area_Range[0]:g}-{Spectrum_Area_Range[1]:g} 1/cm)')])]


# ======================================================================================================================
# The model file and its state (the same way as the rheology model, in "Sub10_Rheology_Prediction.py").
# ======================================================================================================================
_Model = None
_Reason = None
_Loaded = False


def Is_SBS_Enabled_In_Config():
    # A missing setting counts as enabled, so only an explicit "false" turns the model off.
    return str(Read_Config().get(Config_Key, True)).strip().lower() != 'false'
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_SBS_Model_File_Path():
    # The file saved in the config, if there is any (see "Get_Path_For_Config"). Otherwise, the default file of the program.
    Selected = Read_Config().get(Config_File_Key)
    if isinstance(Selected, str) and Selected.strip() != '':
        return os.path.abspath(Get_Project_Path(Selected))      # An absolute path stays as it is here.
    return Get_Default_Model_Path()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_SBS_Model():
    """
    This function returns the model, or None if it is turned off or not available (see "Get_SBS_Unavailable_Reason"). The
    model is loaded once, when it is first needed, and the menu changes it through the functions below. So, changing the
    config by hand needs restarting the program.
    """
    global _Model, _Reason, _Loaded
    if not _Loaded:
        _Loaded = True
        if Is_SBS_Enabled_In_Config():
            _Model, _Reason = Load_SBS_Model(Get_SBS_Model_File_Path())
        else:
            _Model, _Reason = None, Inactive_Reason
    return _Model
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_SBS_Unavailable_Reason():
    Get_SBS_Model()
    return _Reason
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Select_SBS_Model_File(Path):
    """
    This function uses another model file, if it is valid, and saves its path to the config. Otherwise, nothing changes.
    If the model is inactive, it stays inactive, and the selected file is used when it gets active.

    :param Path: Path to the selected file.
    :return: An empty string, or the reason that it can't be used.
    """
    global _Model, _Reason, _Loaded
    Model, Error = Load_SBS_Model(os.path.abspath(Path))
    if Model is None:
        return Error
    # The selected file is always saved to the config, so the next start of the program uses the same model.
    try:
        Write_Config({Config_File_Key: Get_Path_For_Config(Path)})
    except Exception as Err:
        return f'The selection could not be saved to the config file: {Err}'
    _Loaded = True
    if Is_SBS_Enabled_In_Config():
        _Model, _Reason = Model, None
    else:
        _Model, _Reason = None, Inactive_Reason
    return ''
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Set_SBS_Model_Active(Active):
    """
    This function turns the model on or off, and saves it to the config. It only gets active if the model file is valid.

    :param Active: True to turn on the model, False to turn it off.
    :return: An empty string, or the reason that it can't be done, in which case nothing changes.
    """
    global _Model, _Reason, _Loaded
    Model, Error = None, ''
    if Active:
        Model, Error = Load_SBS_Model(Get_SBS_Model_File_Path())
        if Model is None:
            return Error
    try:
        Write_Config({Config_Key: bool(Active)})
    except Exception as Err:
        return f'The change could not be saved to the config file: {Err}'
    _Loaded = True
    _Model, _Reason = (Model, None) if Active else (None, Inactive_Reason)
    return ''
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


# ======================================================================================================================
# Running the model and saving the results.
# ======================================================================================================================
def Run_SBS_Detection(GaussianList, Wavenumber=None, Absorbance=None, Model=None):
    """
    This function calculates the SBS indices and the probability of modification for one spectrum. It doesn't raise an
    error: if the prediction is not possible (e.g., no Gaussian in the 1377 band), the reason is in "Error".

    :param GaussianList: An array of the Gaussians, one per row, as (center, sigma, amplitude).
    :param Wavenumber: Optional array of the wavenumbers of the pre-processed spectrum (only for "I699" and "I966").
    :param Absorbance: Optional array of the pre-processed absorbance (only for "I699" and "I966").
    :param Model: The model, defaults to the current one.
    :return: None if the model is not available. Otherwise, a dictionary of:
        "Indices", "Bands", "SpectrumArea": See "Calculate_SBS_Indices".
        "Prediction": The dictionary of "SBS_Model.Predict", or None if the prediction failed.
        "Error": The reason that the prediction failed (empty if it didn't).
        "Result": "Modified" or "Unmodified" (None if the prediction failed).
        "Uncertain": True if the probability is in the range where the model is not confident.
        "OutsideTraining": The names of the features outside the range of the training data.
        "Model": The model.
    """
    Model = Get_SBS_Model() if Model is None else Model
    if Model is None:
        return None
    Results = {'Indices': {}, 'Bands': {}, 'SpectrumArea': np.nan, 'Prediction': None, 'Error': '', 'Result': None,
               'Uncertain': False, 'OutsideTraining': [], 'Model': Model}
    try:
        Results.update(Calculate_SBS_Indices(GaussianList, Wavenumber, Absorbance))
        Prediction = Model.Predict(GaussianList)
    except Exception as Err:
        Results['Error'] = str(Err) or type(Err).__name__
        return Results
    Probability = Prediction['Probability']
    Results['Prediction'] = Prediction
    Results['Result'] = 'Modified' if Probability >= Cut_Off else 'Unmodified'
    Results['Uncertain'] = bool(Model.UncertainRange[0] < Probability < Model.UncertainRange[1])
    Results['OutsideTraining'] = [Name for Name, Value in Prediction['Features'].items() if Name in Model.FeatureRange
                                  and not (Model.FeatureRange[Name][0] <= Value <= Model.FeatureRange[Name][1])]
    return Results
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Number_Or_None(Value):
    # The database gets NULL for a missing or undefined (NaN) value.
    try:
        Value = float(Value)
    except (TypeError, ValueError):
        return None
    return Value if np.isfinite(Value) else None
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Results_To_Row(Results):
    # Converts the results into the values of the database columns (all NULL for None).
    Row = dict.fromkeys([Name for Name, _ in SBS_Columns])
    if Results is None:
        return Row
    for Name in Saved_Indices:
        Row[f'SBS_{Name}'] = Number_Or_None(Results['Indices'].get(Name))
    Row['SBS_ModelVersion'] = Results['Model'].Version
    Prediction = Results['Prediction']
    if Prediction is None:
        Row['SBS_Warnings'] = f'Not predicted: {Results["Error"]}'
    else:
        Row['SBS_Result'] = Results['Result']
        Row['SBS_Probability'] = Number_Or_None(Prediction['Probability'])
        Row['SBS_Warnings'] = ' '.join(Prediction['Warnings']) or None
    return Row
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Write_SBS_Row(cursor, RecordID, Results):
    Row = Results_To_Row(Results)
    Names = list(Row)
    cursor.execute(f"UPDATE FTIR SET {', '.join(f'{Name} = ?' for Name in Names)} WHERE id = ?",
                   [Row[Name] for Name in Names] + [RecordID])
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Save_SBS_Results(Parent, conn, cursor, RecordID, Results, IsOutlier=False):
    """
    This function saves the SBS results of a record, after the record itself is saved. If the database doesn't have the
    SBS columns, it adds them and lets the user know. A problem here is shown to the user, but it doesn't stop the program,
    since the record itself is already saved.

    :param Parent: The page, for showing the messages.
    :param RecordID: The "id" of the record.
    :param Results: The results of "Run_SBS_Detection" (None if they are not available).
    :param IsOutlier: If True, the SBS columns of the record are emptied.
    """
    Enabled = Get_SBS_Model() is not None
    try:
        HasColumns = Has_SBS_Columns(cursor)
        # While the model is off, the database isn't updated and the existing results aren't touched. The exception is an
        #   outlier, whose results should not stay in the database.
        if (not Enabled) and not (IsOutlier and HasColumns):
            return
        if not HasColumns:
            Add_SBS_Columns(conn, cursor)
        Write_SBS_Row(cursor, RecordID, None if IsOutlier else Results)
        conn.commit()
    except Exception:
        conn.rollback()
        QMessageBox.warning(Parent, "SBS Detection Results", "The record was saved, but its SBS detection results could " +
                            f"not be saved:\n\n{traceback.format_exc()}")
        return
    if not HasColumns:
        QMessageBox.information(Parent, "Database Updated", "This database didn't have the columns for the SBS detection " +
                                "results, so they were added. The existing records were not changed.\n\nTo add the " +
                                'results of the existing records, please use "Run > Run SBS Detection...".')
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Run_SBS_For_Database(conn, cursor, progress_callback=None):
    """
    This function runs the SBS detection for all the records of the database, from their saved Gaussians, and saves the
    results, after adding the SBS columns if the database doesn't have them. The SBS columns of the outliers are emptied.
    A record that can't be predicted keeps its indices, with the reason in "SBS_Warnings". All the results are written
    together, so a failure leaves the records as they were.

    :param progress_callback: An optional function, called with the number of processed records and the total number.
    :return: A dictionary of the number of records, modified, unmodified, and outlier records, the errors as a list of
    (id, message), and whether the columns were added.
    """
    Model = Get_SBS_Model()
    if Model is None:
        raise RuntimeError(Get_SBS_Unavailable_Reason())
    Summary = {'NumRecords': 0, 'NumModified': 0, 'NumUnmodified': 0, 'NumOutliers': 0, 'Errors': [],
               'ColumnsAdded': not Has_SBS_Columns(cursor)}
    if Summary['ColumnsAdded']:
        Add_SBS_Columns(conn, cursor)
    cursor.execute("SELECT id, IsOutlier, Deconv_GaussianList, Deconv_GaussianList_shape, Deconv_GaussianList_dtype "
                   "FROM FTIR ORDER BY id")
    Records = cursor.fetchall()
    Summary['NumRecords'] = len(Records)
    Updates = []
    for i, (RecordID, IsOutlier, Binary, Shape, DataType) in enumerate(Records):
        Results = None
        if IsOutlier:
            Summary['NumOutliers'] += 1
        else:
            try:
                Results = Run_SBS_Detection(Binary_to_Array(Binary, Shape, DataType), Model=Model)
            except Exception as Err:        # E.g., a Gaussian list that can't be read.
                Results = None
                Summary['Errors'].append((RecordID, str(Err) or type(Err).__name__))
            if Results is not None:
                if Results['Prediction'] is None:
                    Summary['Errors'].append((RecordID, Results['Error']))
                else:
                    Summary['NumModified' if Results['Result'] == 'Modified' else 'NumUnmodified'] += 1
        Updates.append((RecordID, Results))
        if progress_callback is not None:
            progress_callback(i + 1, len(Records))
    try:
        for RecordID, Results in Updates:
            Write_SBS_Row(cursor, RecordID, Results)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return Summary
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


# ======================================================================================================================
# The "Modification" tab and its "More details" window.
# ======================================================================================================================
def Format_Percent(Probability):
    Percent = 100 * Probability
    if Percent < 1:
        return '<1%'
    if Percent > 99:
        return '>99%'
    return f'{Percent:.0f}%'
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Format_Value(Value):
    Value = Number_Or_None(Value)
    return 'N/A' if Value is None else f'{Value:.4g}'
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class SBS_Tab(QWidget):
    """
    This class is the "Modification" tab of the "Results" group box. It shows the SBS detection for the Gaussians on the
    page, and keeps the results in "Results" (None if there is nothing to show), for saving to the database.
    """
    def __init__(self):
        super().__init__()
        self.Results = None
        self.Data = None            # The Gaussians and the spectrum on the page, for running again if the model changes.
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(6, 6, 6, 4)
        Layout.setSpacing(3)
        TopRow = QHBoxLayout()
        self.Label_Result = QLabel()
        self.Bar = QProgressBar()
        self.Bar.setRange(0, 100)
        self.Bar.setFixedHeight(18)
        self.Bar.setToolTip("The probability that the binder is SBS modified. 50% or more counts as modified.")
        TopRow.addWidget(self.Label_Result)
        TopRow.addWidget(self.Bar, 1)
        Layout.addLayout(TopRow)
        self.Label_Text = QLabel()
        self.Label_Text.setWordWrap(True)
        self.Label_Indices = QLabel()
        self.Label_Indices.setToolTip("Rh699 = H699 / H1377 (polystyrene), Rh1 = H966 / H1377 (polybutadiene), from the "
                                      "heights of the fitted Gaussians.")
        self.Label_Links = QLabel()
        self.Label_Links.setTextFormat(Qt.RichText)
        self.Label_Links.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self.Label_Links.linkActivated.connect(self.Show_Details)
        for Label in [self.Label_Text, self.Label_Indices, self.Label_Links]:
            Layout.addWidget(Label)
        Layout.addStretch(1)
        self.Show_Results()
    # ------------------------------------------------------------------------------------------------------------------
    def Set_Bar(self, Value, Text, Color):
        self.Bar.setValue(Value)
        self.Bar.setFormat(Text)
        self.Bar.setStyleSheet("QProgressBar {border: 1px solid #B0B0B0; border-radius: 4px; background-color: #F4F4F4; " +
                               "color: #000; text-align: center;} " +
                               f"QProgressBar::chunk {{background-color: {Color}; border-radius: 3px;}}")
    # ------------------------------------------------------------------------------------------------------------------
    def Show_Results(self):
        try:
            self.Show_Results_Unsafe()
        except Exception:
            # Showing the results should never stop the page.
            traceback.print_exc()
            self.Label_Text.setText('The SBS detection results could not be shown.')
        self.Fit_Text_Height()
    # ------------------------------------------------------------------------------------------------------------------
    def Fit_Text_Height(self):
        # A label with word wrap inside a tab only gets the height of one line from the layout, so the rest of its text
        #   would be cut. It gets the height of its text at its current width instead.
        Width = self.Label_Text.width() if self.Label_Text.isVisibleTo(self) else 0
        if Width > 0:
            self.Label_Text.setMinimumHeight(self.Label_Text.heightForWidth(Width))
    # ------------------------------------------------------------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.Fit_Text_Height()
    # ------------------------------------------------------------------------------------------------------------------
    def Show_Results_Unsafe(self):
        Available = Get_SBS_Model() is not None
        for Widget in [self.Label_Result, self.Bar, self.Label_Indices, self.Label_Links]:
            Widget.setVisible(Available)
        self.Label_Text.setToolTip('')
        if not Available:
            self.Label_Text.setText(Get_SBS_Unavailable_Reason())
            return
        Results = self.Results
        Indices = {} if Results is None else Results['Indices']
        Shown = {Name: Number_Or_None(Indices.get(Name)) for Name in ['Rh699', 'Rh1']}
        self.Label_Indices.setText(', '.join(f'{Name}: ' + ('N/A' if Value is None else f'{Value:.3f}')
                                             for Name, Value in Shown.items()))
        if Results is None or Results['Prediction'] is None:
            self.Label_Result.setText('<b>SBS:</b>')
            self.Set_Bar(0, 'N/A', Bar_Colors['Unmodified'])
            if Results is None:
                self.Label_Text.setText('Probability of SBS modification: N/A')
                self.Label_Links.setText('')
            else:
                self.Label_Text.setText('The SBS detection is not available for this spectrum.')
                self.Label_Text.setToolTip(Results['Error'])
                self.Label_Links.setText('<a href="details">More details</a>')
            return
        Probability = Results['Prediction']['Probability']
        Percent = Format_Percent(Probability)
        Result = Results['Result']
        self.Label_Result.setText(f'<span style="color:{Result_Colors[Result]}; font-weight:bold;">{Result}</span>')
        self.Set_Bar(int(round(100 * Probability)), Percent, Bar_Colors[Result])
        self.Label_Text.setText(f'The binder has a <b>{html.escape(Percent)}</b> probability of being SBS modified.')
        Notes = []
        if Results['Uncertain']:
            Notes.append('Not confident')
        if Results['OutsideTraining']:
            Notes.append('Outside the training data')
        Links = '<a href="details">More details</a>'
        if Notes:
            Links = f'<span style="color:#B00000;">&#9888; {", ".join(Notes)}</span> &nbsp; ' + Links
        self.Label_Links.setText(Links)
    # ------------------------------------------------------------------------------------------------------------------
    def Set_Data(self, GaussianList, Wavenumber=None, Absorbance=None):
        """
        This function runs the SBS detection for the Gaussians on the page and shows the results. Any problem only makes
        the results not available, and the rest of the page keeps working.

        :param GaussianList: The Gaussians, or None if the page has no spectrum.
        :param Wavenumber: The wavenumbers of the pre-processed spectrum (optional).
        :param Absorbance: The pre-processed absorbance (optional).
        """
        try:
            if GaussianList is None:
                self.Clear()
                return
            # Copies, since the mouse editor changes its Gaussians in place.
            self.Data = tuple(None if Array is None else np.array(Array, dtype=float)
                              for Array in (GaussianList, Wavenumber, Absorbance))
            self.Results = Run_SBS_Detection(*self.Data)
        except Exception:
            traceback.print_exc()
            Model = Get_SBS_Model()
            self.Results = None if Model is None else {
                'Indices': {}, 'Bands': {}, 'SpectrumArea': np.nan, 'Prediction': None, 'Uncertain': False,
                'Error': traceback.format_exc().strip().splitlines()[-1], 'Result': None, 'OutsideTraining': [],
                'Model': Model}
        self.Show_Results()
    # ------------------------------------------------------------------------------------------------------------------
    def Clear(self):
        self.Results = None
        self.Data = None
        self.Show_Results()
    # ------------------------------------------------------------------------------------------------------------------
    def Sync_With_Model(self):
        # After the model changes, the Gaussians on the page are run again, so what gets saved is from the current model.
        if self.Data is not None:
            self.Set_Data(*self.Data)
        else:
            self.Clear()
    # ------------------------------------------------------------------------------------------------------------------
    def Show_Details(self, Link=None):
        if self.Results is None:
            return
        try:
            SBS_Details_Dialog(self.Results, self).exec_()
        except Exception:
            QMessageBox.warning(self, "SBS Detection Details", f"The details could not be shown:\n\n{traceback.format_exc()}")
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class SBS_Details_Dialog(QDialog):
    """
    This class is the "More details" window of the "Modification" tab: the result, the inputs of the model, all the SBS
    indices, and the bands they come from, with the notes of the model.
    """
    def __init__(self, Results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SBS Detection Details")
        Layout = QVBoxLayout(self)
        Model, Prediction = Results['Model'], Results['Prediction']
        # The summary.
        if Prediction is None:
            Summary = ('<b>The SBS detection is not available for this spectrum.</b><br>'
                       f'Reason: {html.escape(Results["Error"])}')
        else:
            Result = Results['Result']
            Summary = (f'<span style="color:{Result_Colors[Result]}; font-weight:bold;">{Result}</span>: the binder has a '
                       f'<b>{html.escape(Format_Percent(Prediction["Probability"]))}</b> probability of being SBS modified '
                       f'(modified at {Cut_Off:.0%} or more).')
        Summary += f'<br>Model version: {html.escape(str(Model.Version))}'
        Label_Summary = QLabel(Summary)
        Label_Summary.setWordWrap(True)
        Layout.addWidget(Label_Summary)
        # The table.
        self.Rows = self.Get_Rows(Results)
        self.Table = QTableWidget(len(self.Rows), 3)
        self.Table.setHorizontalHeaderLabels(['Name', 'Value', 'Definition'])
        self.Table.verticalHeader().setVisible(False)
        self.Table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.Table.setSelectionMode(QAbstractItemView.NoSelection)
        self.Table.setWordWrap(False)
        Bold = QFont()
        Bold.setBold(True)
        for Row, Values in enumerate(self.Rows):
            if len(Values) == 1:                # The title of a group.
                Item = QTableWidgetItem(Values[0])
                Item.setFont(Bold)
                Item.setBackground(QColor('#E8E8E8'))
                self.Table.setItem(Row, 0, Item)
                self.Table.setSpan(Row, 0, 1, 3)
                continue
            for Col, Text in enumerate(Values):
                Item = QTableWidgetItem(Text)
                if Col == 1:
                    Item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.Table.setItem(Row, Col, Item)
        Header = self.Table.horizontalHeader()
        Header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        Header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        Header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.Table.resizeRowsToContents()
        Layout.addWidget(self.Table, 1)
        # The notes of the model.
        Notes = Prediction['Warnings'] if Prediction is not None else []
        NotesText = '<b>Notes from the model:</b> '
        NotesText += ('<ul style="margin-top:2px;">' + ''.join(f'<li>{html.escape(Note)}</li>' for Note in Notes) + '</ul>'
                      if Notes else 'None.')
        Label_Notes = QLabel(NotesText)
        Label_Notes.setWordWrap(True)
        Layout.addWidget(Label_Notes)
        # The buttons.
        Buttons = QHBoxLayout()
        self.Button_Copy = QPushButton("Copy Table")
        self.Button_Copy.setStyleSheet(Dialog_Button_Style['General'])
        self.Button_Copy.setAutoDefault(False)
        self.Button_Copy.setToolTip("Copy the table, to paste it in Excel.")
        self.Button_Copy.clicked.connect(self.Function_Copy)
        Button_Close = QPushButton("Close")
        Button_Close.setStyleSheet(Dialog_Button_Style['General'])
        Button_Close.setDefault(True)
        Button_Close.clicked.connect(self.accept)
        Buttons.addWidget(self.Button_Copy)
        Buttons.addStretch(1)
        Buttons.addWidget(Button_Close)
        Layout.addLayout(Buttons)
        self.resize(760, 720)
    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def Get_Rows(Results):
        # The rows of the table, as (name, value, definition), or (title,) for the title of a group.
        Model, Prediction = Results['Model'], Results['Prediction']
        Rows = [('Model',)]
        if Prediction is None:
            Rows.append(('Probability', 'N/A', f'Not predicted: {Results["Error"]}'))
        else:
            Features = Prediction['Features']
            Z = Model.Intercept + sum(Coefficient * Features[Feature['name']]
                                      for Coefficient, Feature in zip(Model.Coefficients, Model.Features))
            Terms = ' '.join(f'{Coefficient:+.4g} * {Feature["name"]}'
                             for Coefficient, Feature in zip(Model.Coefficients, Model.Features))
            Rows.append(('Probability', f'{Prediction["Probability"]:.4f}', 'P(modified) = 1 / (1 + exp(-z))'))
            Rows.append(('z', f'{Z:.4g}', f'{Model.Intercept:+.4g} {Terms}'))
            for Coefficient, Feature in zip(Model.Coefficients, Model.Features):
                Name = Feature['name']
                Definition = f'Model input: {Feature["measure"]} of the {Feature["numerator"]} band'
                if Feature.get('denominator') is not None:
                    Definition += f' / {Feature["measure"]} of the {Feature["denominator"]} band'
                if Name in Model.FeatureRange:
                    Low, High = Model.FeatureRange[Name]
                    Definition += f'; training data: {Low:.3g} to {High:.3g}'
                Rows.append((Name, Format_Value(Features.get(Name)), Definition))
        Indices = Results['Indices']
        for Title, Group in Index_Groups:
            Rows.append((Title,))
            Rows += [(Name, Format_Value(Indices.get(Name)), Definition) for Name, Definition in Group]
        Rows.append(('Spectrum area', Format_Value(Results['SpectrumArea']),
                     f'Area of the pre-processed spectrum, {Spectrum_Area_Range[0]:g}-{Spectrum_Area_Range[1]:g} 1/cm'))
        Rows.append(('Bands (from the fitted Gaussians)',))
        for Name, (Low, High) in Index_Bands.items():
            Band = Results['Bands'].get(Name, {})
            Count = Band.get('count')
            Window = f'{Low:g}-{High:g} 1/cm'
            Found = 'no Gaussian' if Count == 0 else (f'{Count} Gaussian(s)' if Count is not None else 'N/A')
            Rows.append((f'H{Name}', Format_Value(Band.get('height')),
                         f'Largest amplitude of the Gaussians centered at {Window} ({Found})'))
            Rows.append((f'A{Name}', Format_Value(Band.get('area')), f'Sum of the areas of those Gaussians'))
        return Rows
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Copy(self):
        Lines = ['Name\tValue\tDefinition'] + ['\t'.join(Row) for Row in self.Rows]
        QApplication.clipboard().setText('\n'.join(Lines))
        self.Button_Copy.setText("Copied")
