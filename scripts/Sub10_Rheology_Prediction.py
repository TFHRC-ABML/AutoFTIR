# Title: This script predicts the rheological properties of a binder from its raw FTIR spectrum, using a trained model.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/05/2026
# ======================================================================================================================
#
# The model and the prediction method in this script were developed by Tianhao Yan, National Center for Asphalt Technology
#   (NCAT), Auburn University (tianhao.yan@auburn.edu), and are used here with his permission. The functions below are
#   adapted from his "ftir_rheo_predict" package (version 0.1.0). When reporting the results, please cite:
#
#   T. Yan, M. S. Sakhaeifar, S. F. Abdollahi (2026). FTIR-Based Rheology Prediction of Asphalt Binders via Autoencoder.
#   Road Materials and Pavement Design. https://doi.org/10.1080/14680629.2026.2708068
#
# The trained model is one file, which holds the structure and weights of the networks, the wavenumber grid, the reference
#   peaks, and the expected errors. So, an updated model only needs another file. By default, this is the file
#   "data/FTIR_Rheology_Model.npz". Another one can be selected from "Run > FTIR-Rheology Model > Select Model File...",
#   which saves its path as "Rheology_Model_File" in "configs/config.json".
#
# The model can be turned off from the same menu, which saves "Rheology_Model_Enabled" in "configs/config.json". It is also
#   off if the model file is not found or is not valid. While it is off, nothing is predicted and the database is not
#   touched.
# ======================================================================================================================

# Importing the required libraries.
import json
import os
import sys
import traceback
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGroupBox, QLabel, QMessageBox, QTabWidget, QVBoxLayout, QWidget
from scripts.Sub02_CreateNewSQLTable import Add_Rheology_Columns, Has_Rheology_Columns, Rheology_Columns
from scripts.Sub04_FTIR_Analysis_Functions import Binary_to_Array


Config_Key = 'Rheology_Model_Enabled'
Config_File_Key = 'Rheology_Model_File'
Supported_Format_Version = 1
# The columns of the database for each predicted property, as (value, standard deviation of the networks).
Property_Columns = {'htpg': ('Rheo_HTPG', 'Rheo_HTPG_Std'), 'ltpg': ('Rheo_LTPG', 'Rheo_LTPG_Std'),
                    'ctod': ('Rheo_CTOD', 'Rheo_CTOD_Std'), 'delta_tc': ('Rheo_DeltaTc', 'Rheo_DeltaTc_Std'),
                    'g_star': ('Rheo_GStar', 'Rheo_GStar_Std'), 'phase_angle': ('Rheo_PhaseAngle', 'Rheo_PhaseAngle_Std'),
                    's_value_m30': ('Rheo_S_m30', 'Rheo_S_m30_Std'), 'm_value_m30': ('Rheo_m_m30', 'Rheo_m_m30_Std')}
# The properties shown in the "Rheology" tab, as (key, label, unit).
Shown_Properties = [('htpg', 'HTPG', '°C'), ('ltpg', 'LTPG', '°C'), ('ctod', 'CTOD', 'mm')]
Important_Note = (
    "These predictions are preliminary and for information only, for this specific spectrum.\n\n"
    "HTPG is designed to work for unaged (ORG) and RTFO-aged binders. CTOD and LTPG are designed to work with PAV20 "
    "binders. If you are predicting these for any other aging level, it is outside the scope of the trained model, and "
    "the results won't be reliable.\n\n"
    "The value after ± is the standard deviation between the five networks of the model. It shows how well they agree, "
    "which is usually smaller than the actual error of the prediction.")


def Get_Project_Path(*Parts):
    # Works for both the source code and a PyInstaller build.
    Root = getattr(sys, '_MEIPASS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    return os.path.join(Root, *Parts)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class Rheology_Model:
    """
    This class holds a trained model, loaded from its file. A prediction only needs NumPy. Each property has an ensemble
    of networks, and each network is a chain of affine maps and ReLU activations, stored in the file. So the number and
    size of the layers can change in an updated model, without changing this code.
    """
    def __init__(self, Path):
        with np.load(Path, allow_pickle=False) as File:
            self.Path = Path
            Meta = json.loads(str(File['meta_json']))
            Version = Meta.get('format_version')
            if Version != Supported_Format_Version:
                raise ValueError(f'The model file has format version {Version}, but this version of AutoFTIR reads '
                                 f'version {Supported_Format_Version}.')
            self.Version = Meta['model_version']
            self.Properties = Meta['properties']
            Grid = Meta['grid']
            self.Grid = (Grid['start'] + Grid['step'] * np.arange(Grid['num_points']))[::-1]
            self.ReferencePeaks = Meta['axis']['reference_peaks']
            self.ScaleTolerance = Meta['axis']['scale_tolerance']
            self.ScaleMax = Meta['axis']['scale_max']
            self.Ensembles = {Key: self.Load_Ensemble(File, Key) for Key in self.Properties}
            self.Domain = {Name: File[f'domain/{Name}'] for Name in ['mean', 'scale', 'pca_mean', 'components', 'variance']}
            self.Q_Threshold = Meta['domain']['q_threshold']
            self.T2_Threshold = Meta['domain']['t2_threshold']
    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def Load_Ensemble(File, Key):
        Members = []
        for i in range(int(File[f'{Key}/n_members'])):
            Prefix = f'{Key}/m{i}.'
            Operations = []
            for j, Kind in enumerate(File[Prefix + 'ops'].tolist()):
                if Kind == 'affine':
                    Operations.append((File[f'{Prefix}op{j}.W'], File[f'{Prefix}op{j}.b']))
                elif Kind == 'relu':
                    Operations.append(None)
                else:
                    raise ValueError(f'The model file has an unknown operation: {Kind}')
            TargetMean, TargetScale = File[Prefix + 'target']
            Members.append((File[Prefix + 'input_mean'], File[Prefix + 'input_scale'], Operations,
                            float(TargetMean), float(TargetScale)))
        return Members
    # ------------------------------------------------------------------------------------------------------------------
    def Find_Peak_Center(self, X, Y, Low, High):
        # The peak location by a parabola around the highest point in the range (X is ascending).
        Inside = np.flatnonzero((X >= Low) & (X <= High))
        i = Inside[np.argmax(Y[Inside])]
        if i == 0 or i == len(X) - 1:
            return float(X[i])
        Y0, Y1, Y2 = Y[i - 1], Y[i], Y[i + 1]
        Curvature = Y0 - 2 * Y1 + Y2
        Offset = 0.5 * (Y0 - Y2) / Curvature if Curvature != 0 else 0.0
        return float(X[i] + Offset * (X[i + 1] - X[i]))
    # ------------------------------------------------------------------------------------------------------------------
    def Estimate_Axis_Scale(self, X, Y):
        # The factor that aligns the sharp CH bands of the spectrum with those of the training spectra.
        Order = np.argsort(X)
        X, Y = X[Order], Y[Order]
        Reference = np.array([Peak[0] for Peak in self.ReferencePeaks])
        Observed = np.array([self.Find_Peak_Center(X, Y, Peak[1], Peak[2]) for Peak in self.ReferencePeaks])
        return float(np.sum(Reference * Observed) / np.sum(Observed ** 2))
    # ------------------------------------------------------------------------------------------------------------------
    def To_Reference_Grid(self, X, Y, MaxEdgeGap):
        # The training spectra have one wavenumber grid, so the spectrum is interpolated to that grid if it is not on it.
        #   The order of the input doesn't matter: AutoFTIR keeps the spectra ascending, and the grid is descending.
        Order = np.argsort(X)
        X, Y = X[Order], Y[Order]
        if X.shape == self.Grid.shape and np.allclose(X, self.Grid[::-1], atol=1e-3):
            return Y[::-1].copy()
        Gap = max(X[0] - self.Grid.min(), self.Grid.max() - X[-1])
        if Gap > MaxEdgeGap:
            raise ValueError(f'The spectrum covers {X[0]:.1f}-{X[-1]:.1f} cm-1, but the model needs '
                             f'{self.Grid.min():.1f}-{self.Grid.max():.1f} cm-1.')
        return np.interp(self.Grid, X, Y)
    # ------------------------------------------------------------------------------------------------------------------
    def Run_Ensemble(self, Key, Spectrum):
        Values = []
        for InputMean, InputScale, Operations, TargetMean, TargetScale in self.Ensembles[Key]:
            Z = (Spectrum - InputMean) / InputScale
            for Operation in Operations:
                if Operation is None:
                    Z = np.maximum(Z, 0.0)
                else:
                    Z = Z @ Operation[0].T + Operation[1]
            Values.append(float(Z[0, 0] * TargetScale + TargetMean))
        return Values
    # ------------------------------------------------------------------------------------------------------------------
    def Is_In_Domain(self, Spectrum):
        # Checks if the spectrum resembles the training spectra, using a PCA model of them.
        Domain = self.Domain
        Z = (Spectrum - Domain['mean']) / float(Domain['scale']) - Domain['pca_mean']
        Scores = Z @ Domain['components'].T
        Q = np.mean((Z - Scores @ Domain['components']) ** 2, axis=1)
        T2 = np.sum(Scores ** 2 / Domain['variance'], axis=1)
        return bool(Q[0] <= self.Q_Threshold and T2[0] <= self.T2_Threshold)
    # ------------------------------------------------------------------------------------------------------------------
    def Check(self):
        """
        This function makes sure that the model works, by predicting a test spectrum with the bands that the model looks
        for. An error is raised otherwise, e.g., when the size of the weights doesn't match the wavenumber grid.
        """
        if not any(Key in Property_Columns for Key in self.Ensembles):
            raise ValueError('It has none of the properties that AutoFTIR uses.')
        Absorbance = np.full(self.Grid.shape, 0.01)
        for Peak in self.ReferencePeaks:
            Absorbance += 0.1 * np.exp(-0.5 * ((self.Grid - Peak[0]) / 5.0) ** 2)
        self.Predict(self.Grid, Absorbance)
    # ------------------------------------------------------------------------------------------------------------------
    def Predict(self, Wavenumber, Absorbance):
        """
        This function predicts all the properties for one spectrum.

        :param Wavenumber: An array of the raw wavenumbers (1/cm), covering 4000 to 400 1/cm.
        :param Absorbance: An array of the raw absorbance, without any baseline correction or normalization.
        :return: A dictionary of the results, where "Values" has the mean and standard deviation of the networks for each
        property. An error is raised if the spectrum cannot be used.
        """
        X = np.asarray(Wavenumber, dtype=float)
        Y = np.asarray(Absorbance, dtype=float)
        if X.ndim != 1 or X.shape != Y.shape or X.size < 10 or not (np.isfinite(X).all() and np.isfinite(Y).all()):
            raise ValueError('The spectrum needs two arrays of finite numbers with the same length.')
        # Correct the wavenumber axis, if it differs from the training instrument.
        Scale = self.Estimate_Axis_Scale(X, Y)
        Corrected = self.ScaleTolerance < abs(Scale - 1) <= self.ScaleMax
        EdgeGap = 2.5
        if Corrected:
            X = X * Scale
            EdgeGap += self.Grid.max() * abs(Scale - 1)
        Spectrum = self.To_Reference_Grid(X, Y, EdgeGap)[np.newaxis, :]
        Values = {}
        for Key in self.Ensembles:
            Predictions = self.Run_Ensemble(Key, Spectrum)
            Values[Key] = (float(np.mean(Predictions)), float(np.std(Predictions)))
        if not np.isfinite(list(Values.values())).all():
            raise ValueError('The prediction is not a finite number.')
        return {'Values': Values, 'InDomain': self.Is_In_Domain(Spectrum), 'AxisScale': Scale,
                'AxisCorrected': bool(Corrected), 'ModelVersion': self.Version}
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


_Model = None
_Reason = None
_Loaded = False
Inactive_Reason = 'The rheology model is inactive. You can change it from "Run > FTIR-Rheology Model".'


def Read_Config():
    # A missing or unreadable config counts as empty, so the defaults are used.
    try:
        with open(Get_Project_Path('configs', 'config.json'), 'r') as File:
            Config = json.load(File)
    except (OSError, ValueError):
        return {}
    return Config if isinstance(Config, dict) else {}
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Write_Config(Updates):
    """
    This function changes some settings in the config and keeps the others, like the recent databases. An unreadable
    config raises an error, instead of being replaced. The new config is written to a temporary file first, so a failure
    can't damage the existing one.
    """
    Path = Get_Project_Path('configs', 'config.json')
    Config = {}
    if os.path.isfile(Path):
        with open(Path, 'r') as File:
            Config = json.load(File)
        if not isinstance(Config, dict):
            raise ValueError(f'"{Path}" is not a valid config file.')
    Config.update(Updates)
    Temporary = Path + '.tmp'
    with open(Temporary, 'w') as File:
        json.dump(Config, File)
    os.replace(Temporary, Path)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Is_Enabled_In_Config():
    # A missing setting counts as enabled, so only an explicit "false" turns the model off.
    return str(Read_Config().get(Config_Key, True)).strip().lower() != 'false'
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Default_Model_Path():
    return os.path.abspath(Get_Project_Path('data', 'FTIR_Rheology_Model.npz'))
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Model_File_Path():
    # The file saved in the config, if there is any (see "Get_Path_For_Config"). Otherwise, the default file of the program.
    Selected = Read_Config().get(Config_File_Key)
    if isinstance(Selected, str) and Selected.strip() != '':
        return os.path.abspath(Get_Project_Path(Selected))      # An absolute path stays as it is here.
    return Get_Default_Model_Path()
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Path_For_Config(Path):
    # A file inside the program's folder is saved relative to it, so it can still be found if that folder moves. Any other
    #   file is saved with its full path.
    Path = os.path.abspath(Path)
    try:
        Relative = os.path.relpath(Path, os.path.abspath(Get_Project_Path()))
    except ValueError:      # On another drive.
        return Path
    if Relative == os.pardir or Relative.startswith(os.pardir + os.sep):
        return Path
    return Relative.replace(os.sep, '/')
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Load_Model_File(Path):
    """
    This function checks if a file is a valid rheology model, by loading it and running a test prediction.

    :param Path: Path to the model file.
    :return: The model and an empty string, or None and the reason that the file can't be used.
    """
    if not os.path.isfile(Path):
        return None, f'The rheology model file ({Path}) was not found.'
    try:
        Model = Rheology_Model(Path)
        Model.Check()
    except Exception as Err:
        traceback.print_exc()
        return None, f'The rheology model file ({Path}) could not be read: {Err}'
    return Model, ''
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Rheology_Model():
    """
    This function returns the trained model, or None if it is turned off or not available (see "Get_Unavailable_Reason").
    The model is loaded once, when it is first needed, and the menu changes it through the functions below. So, changing
    the config by hand needs restarting the program.
    """
    global _Model, _Reason, _Loaded
    if not _Loaded:
        _Loaded = True
        if Is_Enabled_In_Config():
            _Model, _Reason = Load_Model_File(Get_Model_File_Path())
        else:
            _Model, _Reason = None, Inactive_Reason
    return _Model
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Unavailable_Reason():
    Get_Rheology_Model()
    return _Reason
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Select_Rheology_Model_File(Path):
    """
    This function uses another model file, if it is valid, and saves its path to the config. Otherwise, nothing changes.
    If the model is inactive, it stays inactive, and the selected file is used when it gets active.

    :param Path: Path to the selected file.
    :return: An empty string, or the reason that it can't be used.
    """
    global _Model, _Reason, _Loaded
    Model, Error = Load_Model_File(os.path.abspath(Path))
    if Model is None:
        return Error
    # The selected file is always saved to the config, so the next start of the program uses the same model.
    try:
        Write_Config({Config_File_Key: Get_Path_For_Config(Path)})
    except Exception as Err:
        return f'The selection could not be saved to the config file: {Err}'
    _Loaded = True
    if Is_Enabled_In_Config():
        _Model, _Reason = Model, None
    else:
        _Model, _Reason = None, Inactive_Reason
    return ''
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Set_Rheology_Model_Active(Active):
    """
    This function turns the model on or off, and saves it to the config. It only gets active if the model file is valid.

    :param Active: True to turn on the model, False to turn it off.
    :return: An empty string, or the reason that it can't be done, in which case nothing changes.
    """
    global _Model, _Reason, _Loaded
    Model, Error = None, ''
    if Active:
        Model, Error = Load_Model_File(Get_Model_File_Path())
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


def Results_To_Row(Results):
    # Converts the results into the values of the database columns (in the order of "Rheology_Columns").
    Row = dict.fromkeys([Name for Name, _ in Rheology_Columns])
    if Results is None:
        return Row
    for Key, (Value, Std) in Results['Values'].items():
        if Key in Property_Columns:
            Row[Property_Columns[Key][0]], Row[Property_Columns[Key][1]] = Value, Std
    Row['Rheo_InDomain'] = int(Results['InDomain'])
    Row['Rheo_AxisScale'] = Results['AxisScale']
    Row['Rheo_AxisCorrected'] = int(Results['AxisCorrected'])
    Row['Rheo_ModelVersion'] = Results['ModelVersion']
    return Row
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Write_Rheology_Row(cursor, RecordID, Results):
    Row = Results_To_Row(Results)
    Names = list(Row)
    cursor.execute(f"UPDATE FTIR SET {', '.join(f'{Name} = ?' for Name in Names)} WHERE id = ?",
                   [Row[Name] for Name in Names] + [RecordID])
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Save_Rheology_Results(Parent, conn, cursor, RecordID, Results, IsOutlier=False):
    """
    This function saves the rheology results of a record, after the record itself is saved. If the database doesn't have
    the rheology columns, it adds them and lets the user know. A problem here is shown to the user, but it doesn't stop
    the program, since the record itself is already saved.

    :param Parent: The page, for showing the messages.
    :param RecordID: The "id" of the record.
    :param Results: The results of "Predict" (None if they are not available).
    :param IsOutlier: If True, the rheology columns of the record are emptied.
    """
    Enabled = Get_Rheology_Model() is not None
    try:
        HasColumns = Has_Rheology_Columns(cursor)
        # While the model is off, the database isn't updated and the existing predictions aren't touched. The exception is
        #   an outlier, whose predictions should not stay in the database.
        if (not Enabled) and not (IsOutlier and HasColumns):
            return
        if not HasColumns:
            Add_Rheology_Columns(conn, cursor)
        Write_Rheology_Row(cursor, RecordID, None if IsOutlier else Results)
        conn.commit()
    except Exception:
        conn.rollback()
        QMessageBox.warning(Parent, "Rheology Results", "The record was saved, but its rheology results could not be " +
                            f"saved:\n\n{traceback.format_exc()}")
        return
    if not HasColumns:
        QMessageBox.information(Parent, "Database Updated", "This database didn't have the columns for the rheology " +
                                "results, so they were added. The existing records were not changed.\n\nTo add the " +
                                'predictions of the existing records, please use "Run > Run Rheology Predictions...".')
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Has_Raw_Spectrum_Columns(cursor):
    cursor.execute("PRAGMA table_info(FTIR)")
    Columns = [Row[1].lower() for Row in cursor.fetchall()]
    return 'rawwavenumber' in Columns and 'rawabsorbance' in Columns
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Predict_Rheology_For_Database(conn, cursor, progress_callback=None):
    """
    This function runs the rheology prediction for all the records of the database and saves the results, after adding
    the rheology columns if the database doesn't have them. The rheology columns of the outliers, and of the records that
    can't be predicted, are emptied. All the results are written together, so a failure leaves the records as they were.

    :param progress_callback: An optional function, called with the number of processed records and the total number.
    :return: A dictionary of the number of records, predicted records, and outliers, the errors as a list of (id, message),
    and whether the columns were added.
    """
    Model = Get_Rheology_Model()
    if Model is None:
        raise RuntimeError(Get_Unavailable_Reason())
    Summary = {'NumRecords': 0, 'NumPredicted': 0, 'NumOutliers': 0, 'Errors': [],
               'ColumnsAdded': not Has_Rheology_Columns(cursor)}
    if Summary['ColumnsAdded']:
        Add_Rheology_Columns(conn, cursor)
    cursor.execute("SELECT id, IsOutlier FROM FTIR ORDER BY id")
    Records = cursor.fetchall()
    Summary['NumRecords'] = len(Records)
    Updates = []
    for i, (RecordID, IsOutlier) in enumerate(Records):
        Results = None
        if IsOutlier:
            Summary['NumOutliers'] += 1
        else:
            try:
                cursor.execute("SELECT RawWavenumber, RawWavenumber_shape, RawWavenumber_dtype, RawAbsorbance, "
                               "RawAbsorbance_shape, RawAbsorbance_dtype FROM FTIR WHERE id = ?", (RecordID,))
                Raw = cursor.fetchone()
                Results = Model.Predict(Binary_to_Array(Raw[0], Raw[1], Raw[2]), Binary_to_Array(Raw[3], Raw[4], Raw[5]))
                Summary['NumPredicted'] += 1
            except Exception as Err:
                Summary['Errors'].append((RecordID, str(Err)))
        Updates.append((RecordID, Results))
        if progress_callback is not None:
            progress_callback(i + 1, len(Records))
    try:
        for RecordID, Results in Updates:
            Write_Rheology_Row(cursor, RecordID, Results)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return Summary
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class Rheology_Tab(QWidget):
    """
    This class is the "Rheology" tab of the "Results" group box. It shows the predictions for one spectrum, and keeps them
    in "Results" (None if they are not available), for saving to the database.
    """
    def __init__(self):
        super().__init__()
        self.Results = None
        self.Spectrum = None        # The raw spectrum on the page, for predicting it again if the model changes.
        self.Tabs = None            # The tab widget that has this tab.
        Layout = QVBoxLayout(self)
        self.Label_Note = QLabel('<a href="note" style="color:#B00000;"><b>IMPORTANT NOTE</b></a>')
        self.Label_Note.setTextFormat(Qt.RichText)
        self.Label_Note.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self.Label_Note.setToolTip("Click to read about the scope of these predictions.")
        self.Label_Note.linkActivated.connect(self.Show_Note)
        Layout.addWidget(self.Label_Note)
        self.Labels = {}
        for Key, _, _ in Shown_Properties:
            self.Labels[Key] = QLabel()
            Layout.addWidget(self.Labels[Key])
        self.Clear()
    # ------------------------------------------------------------------------------------------------------------------
    def Show_Note(self, Link=None):
        QMessageBox.information(self, "Important Note", Important_Note)
    # ------------------------------------------------------------------------------------------------------------------
    def Show_Results(self, Message='N/A'):
        for Key, Label, Unit in Shown_Properties:
            Value = None if self.Results is None else self.Results['Values'].get(Key)
            if Value is None:
                self.Labels[Key].setText(f'{Label}: {Message}')
            else:
                self.Labels[Key].setText(f'{Label}: {Value[0]:.1f} ± {Value[1]:.1f} {Unit}')
    # ------------------------------------------------------------------------------------------------------------------
    def Clear(self):
        self.Results = None
        self.Spectrum = None
        self.Show_Results()
    # ------------------------------------------------------------------------------------------------------------------
    def Set_Spectrum(self, Wavenumber, Absorbance):
        """
        This function runs the prediction for a raw spectrum and shows the results. Any problem only makes the results
        not available, and the rest of the page keeps working.
        """
        self.Spectrum = (Wavenumber, Absorbance)
        Model = Get_Rheology_Model()
        if Model is None:
            self.Results = None
            self.Show_Results()
            return
        try:
            self.Results = Model.Predict(Wavenumber, Absorbance)
            self.Show_Results()
        except Exception:
            traceback.print_exc()
            self.Results = None
            self.Show_Results('Results are not available')
    # ------------------------------------------------------------------------------------------------------------------
    def Sync_With_Model(self):
        """
        This function updates the tab after the model changes: it turns the tab on or off, and predicts the spectrum on the
        page again, so the results that get saved are always from the current model.
        """
        Index = self.Tabs.indexOf(self)
        Available = Get_Rheology_Model() is not None
        if (not Available) and self.Tabs.currentIndex() == Index:
            self.Tabs.setCurrentIndex(0)
        self.Tabs.setTabEnabled(Index, Available)
        self.Tabs.setTabToolTip(Index, '' if Available else Get_Unavailable_Reason())
        if self.Spectrum is not None:
            self.Set_Spectrum(*self.Spectrum)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Create_Results_GroupBox(DeconvolutionLabels, ModificationTab=None):
    """
    This function creates the "Results" group box, with the tabs for the results of each analysis.

    :param DeconvolutionLabels: A list of the labels of the "Deconvolution" tab.
    :param ModificationTab: The "Modification" tab (see "Sub13_SBS_Detection_App.py"). Without it, the tab is disabled.
    :return: The group box and the "Rheology" tab.
    """
    Deconvolution = QWidget()
    DeconvolutionLayout = QVBoxLayout(Deconvolution)
    for Label in DeconvolutionLabels:
        DeconvolutionLayout.addWidget(Label)
    Rheology = Rheology_Tab()
    Tabs = QTabWidget()
    # All the tab names stay readable: in a narrow window, the panel gets a little wider instead of hiding them.
    Tabs.setUsesScrollButtons(False)
    Tabs.setElideMode(Qt.ElideNone)
    Tabs.addTab(Deconvolution, "Deconvolution")
    Tabs.addTab(Rheology, "Rheology")
    if ModificationTab is None:
        Tabs.setTabEnabled(Tabs.addTab(QWidget(), "Modification"), False)
    else:
        # Always on: while the SBS model is off, the tab says so.
        Tabs.addTab(ModificationTab, "Modification")
    Rheology.Tabs = Tabs
    Rheology.Sync_With_Model()
    GroupBox = QGroupBox("Results")
    Layout = QVBoxLayout(GroupBox)
    Layout.addWidget(Tabs)
    return GroupBox, Rheology
