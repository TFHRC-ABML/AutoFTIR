# Title: This script estimates the probability that a binder is polymer (SBS) modified, from the Gaussians fitted to its
#   FTIR spectrum, using a trained model.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/06/2026
# ======================================================================================================================
#
# Method: SBS has two bands of its own: the polystyrene ring at ~699 1/cm and the trans-1,4-polybutadiene C=C at ~966
#   1/cm. Each band is measured by the Gaussians of the deconvolution whose centers fall in its window: the "height" is
#   the largest amplitude among them, and the "area" is the sum of their areas. A band with no Gaussian is zero. The
#   features are ratios of these values to a reference band of the binder itself (e.g., the CH3 band at ~1377 1/cm), so
#   they don't depend on the normalization of the spectrum. A logistic regression turns the features into a probability:
#       P(modified) = 1 / (1 + exp(-z)),    z = Intercept + sum(Coefficient_i * Feature_i)
#
# The model was developed in "development/SBSDetection01_PeakRatioMethod.ipynb", trained on the Rodeo RA database with
#   binder-level labels (MODIFIED/NEAT) at all aging levels, and validated by leaving one binder out at a time.
#
# The trained model is one file, which holds the band windows, the definition of each feature, the coefficients, and the
#   training information. So, a retrained model (new coefficients, other features, or other windows) only needs another
#   file. By default, this is the file "data/FTIR_SBS_Model.npz", written by "Save_SBS_Model".
# ======================================================================================================================

# Importing the required libraries.
import json
import os
import sys
import traceback
import numpy as np


Supported_Format_Version = 1
Default_Model_File = ('data', 'FTIR_SBS_Model.npz')
Supported_Measures = ('height', 'area')
Supported_Model_Types = ('logistic',)
# The probabilities between these two get a "not confident" warning. It is a choice of the user (not from an analysis),
#   saved in the model file, and this is the default for a file without it.
Default_Uncertain_Range = (0.25, 0.75)
# The bands of the SBS indices (1/cm), as in "development/SBSDetection01_PeakRatioMethod.ipynb". They are fixed here, so
#   the indices stay comparable between records and databases, even if a retrained model uses other windows for its own
#   features (those come from the model file).
Index_Bands = {'699': (685.0, 710.0),       # Monosubstituted benzene ring C-H out-of-plane rocking (polystyrene).
               '813': (795.0, 830.0),       # Aromatic ring C-H out-of-plane rocking.
               '966': (950.0, 980.0),       # Trans-1,4-butadiene C=C out-of-plane bending (polybutadiene).
               '1377': (1350.0, 1400.0)}    # Aliphatic methyl (-CH3) symmetric deformation.
Spectrum_Area_Range = (600.0, 2000.0)       # The range of the spectrum area for "I699" and "I966".


def Get_Project_Path(*Parts):
    # Works for both the source code and a PyInstaller build.
    Root = getattr(sys, '_MEIPASS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    return os.path.join(Root, *Parts)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Band_Values(GaussianList, Low, High):
    """
    This function measures one band from the Gaussians of the deconvolution.

    :param GaussianList: An array of the Gaussians, one per row, as (center (1/cm), sigma (1/cm), amplitude), as stored in
    the "Deconv_GaussianList" column of the database.
    :param Low: The lower end of the window for the centers (1/cm), included.
    :param High: The upper end of the window for the centers (1/cm), included.
    :return: A dictionary with the "height" (largest amplitude), the "area" (sum of the areas), and the number of
    Gaussians in the window ("count"). Both values are zero if there is no Gaussian in the window.
    """
    Inside = GaussianList[(GaussianList[:, 0] >= Low) & (GaussianList[:, 0] <= High)]
    if Inside.shape[0] == 0:
        return {'height': 0.0, 'area': 0.0, 'count': 0}
    return {'height': float(np.max(np.abs(Inside[:, 2]))),
            'area': float(np.sum(np.abs(np.sqrt(2 * np.pi) * Inside[:, 1] * Inside[:, 2]))),
            'count': int(Inside.shape[0])}
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Calculate_SBS_Indices(GaussianList, Wavenumber=None, Absorbance=None):
    """
    This function calculates the SBS indices of one spectrum, from the Gaussians of its deconvolution, with the bands of
    "Index_Bands". They don't need a model. A ratio whose reference band has no Gaussian is NaN, since it is not defined,
    while a missing SBS band (699 or 966) only makes its value zero, as in the notebook.

    :param GaussianList: An array of the Gaussians, one per row, as (center (1/cm), sigma (1/cm), amplitude).
    :param Wavenumber: Optional array of the wavenumbers of the pre-processed spectrum, for "I699" and "I966".
    :param Absorbance: Optional array of the pre-processed absorbance, for "I699" and "I966".
    :return: A dictionary of the "Indices", the measured "Bands" (height, area, and number of Gaussians of each band, see
    "Band_Values"), and the "SpectrumArea" (NaN without a spectrum).
    """
    GaussianList = np.asarray(GaussianList, dtype=float)
    if GaussianList.ndim != 2 or GaussianList.shape[1] < 3:
        GaussianList = np.zeros((0, 3))
    Bands = {Name: Band_Values(GaussianList, Low, High) for Name, (Low, High) in Index_Bands.items()}
    H = {Name: Band['height'] for Name, Band in Bands.items()}
    A = {Name: Band['area'] for Name, Band in Bands.items()}
    def Ratio(Numerator, Denominator):
        return Numerator / Denominator if Denominator > 0 else np.nan
    # The area of the spectrum (some stored spectra have NaN at their first point, so only finite values are used).
    SpectrumArea = np.nan
    if Wavenumber is not None and Absorbance is not None:
        X = np.asarray(Wavenumber, dtype=float).ravel()
        Y = np.asarray(Absorbance, dtype=float).ravel()
        if X.shape == Y.shape:
            Keep = np.isfinite(X) & np.isfinite(Y) & (X >= Spectrum_Area_Range[0]) & (X <= Spectrum_Area_Range[1])
            Order = np.argsort(X[Keep])
            if Order.size >= 2:
                Trapezoid = getattr(np, 'trapezoid', None) or np.trapz        # "trapz" in NumPy 1, "trapezoid" in 2.
                SpectrumArea = float(Trapezoid(Y[Keep][Order], X[Keep][Order]))
    Indices = {
        'Rh699': Ratio(H['699'], H['1377']), 'Rh1': Ratio(H['966'], H['1377']), 'Rh2': Ratio(H['966'], H['813']),
        'Rh20': Ratio(H['966'], H['966'] + H['813']) if H['813'] > 0 else np.nan,
        'Ra699': Ratio(A['699'], A['1377']), 'Ra1': Ratio(A['966'], A['1377']), 'Ra2': Ratio(A['966'], A['813']),
        'Ra20': Ratio(A['966'], A['966'] + A['813']) if A['813'] > 0 else np.nan,
        'I699': Ratio(A['699'], SpectrumArea) if np.isfinite(SpectrumArea) else np.nan,
        'I966': Ratio(A['966'], SpectrumArea) if np.isfinite(SpectrumArea) else np.nan}
    return {'Indices': Indices, 'Bands': Bands, 'SpectrumArea': SpectrumArea}
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class SBS_Model:
    """
    This class holds a trained model, loaded from its file. A prediction only needs NumPy.
    """
    def __init__(self, Path):
        with np.load(Path, allow_pickle=False) as File:
            self.Path = Path
            Meta = json.loads(str(File['meta_json']))
            Version = Meta.get('format_version')
            if Version != Supported_Format_Version:
                raise ValueError(f'The model file has format version {Version}, but this version of AutoFTIR reads '
                                 f'version {Supported_Format_Version}.')
            if Meta.get('model_type') not in Supported_Model_Types:
                raise ValueError(f'The model type "{Meta.get("model_type")}" is not supported.')
            self.Meta = Meta
            self.Version = Meta['model_version']
            self.Bands = {Name: (float(Window[0]), float(Window[1])) for Name, Window in Meta['bands'].items()}
            self.Features = Meta['features']
            self.Intercept = float(File['intercept'])
            self.Coefficients = np.asarray(File['coefficients'], dtype=float).ravel()
        # The definition of the features must match the bands and the coefficients.
        if len(self.Features) == 0 or len(self.Features) != self.Coefficients.size:
            raise ValueError(f'The model file has {len(self.Features)} features but {self.Coefficients.size} coefficients.')
        for Feature in self.Features:
            if Feature.get('measure') not in Supported_Measures:
                raise ValueError(f'The feature "{Feature.get("name")}" has an unknown measure: {Feature.get("measure")}')
            for Key in ('numerator', 'denominator'):
                if Feature.get(Key) is not None and Feature[Key] not in self.Bands:
                    raise ValueError(f'The feature "{Feature["name"]}" uses the band "{Feature[Key]}", which is not '
                                     f'defined in the model file.')
        self.FeatureRange = Meta.get('feature_range', {})
        self.UncertainRange = tuple(Meta.get('uncertain_range', Default_Uncertain_Range))
    # ------------------------------------------------------------------------------------------------------------------
    def Calculate_Features(self, GaussianList):
        """
        This function calculates the features of the model from the Gaussians of one spectrum.

        :param GaussianList: An array of the Gaussians, one per row, as (center, sigma, amplitude).
        :return: The values of the features (dictionary), the measured bands (dictionary), and a list of the problems
        that stop the prediction (empty if none). A reference band without any Gaussian is such a problem, since its
        ratio is not defined; a missing SBS band only makes its feature zero.
        """
        Measured = {Name: Band_Values(GaussianList, Low, High) for Name, (Low, High) in self.Bands.items()}
        Values, Missing = {}, {}
        for Feature in self.Features:
            Numerator = Measured[Feature['numerator']][Feature['measure']]
            Denominator = Feature.get('denominator')
            if Denominator is None:
                Values[Feature['name']] = Numerator
                continue
            Reference = Measured[Denominator][Feature['measure']]
            if Reference > 0:
                Values[Feature['name']] = Numerator / Reference
            else:
                Values[Feature['name']] = np.nan
                Missing.setdefault(Denominator, []).append(Feature['name'])
        Problems = []
        for Band, Names in Missing.items():
            Low, High = self.Bands[Band]
            Problems.append(f'No Gaussian was found for the reference band "{Band}" ({Low:g}-{High:g} 1/cm), so '
                            f'{", ".join(Names)} can\'t be calculated.')
        return Values, Measured, Problems
    # ------------------------------------------------------------------------------------------------------------------
    def Predict(self, GaussianList):
        """
        This function estimates the probability of modification for one spectrum.

        :param GaussianList: An array of the Gaussians, one per row, as (center (1/cm), sigma (1/cm), amplitude), from
        the deconvolution of the pre-processed spectrum.
        :return: A dictionary of the results:
            "Probability": The probability that the binder is modified (0 to 1).
            "Features": The value of each feature.
            "Bands": The height, area, and number of Gaussians of each band.
            "Warnings": A list of notes on the reliability of this prediction (empty if none).
            "ModelVersion": The version of the model.
        An error is raised if the prediction is not possible, e.g., when a reference band has no Gaussian.
        """
        GaussianList = np.asarray(GaussianList, dtype=float)
        if GaussianList.ndim != 2 or GaussianList.shape[1] < 3 or GaussianList.shape[0] == 0:
            raise ValueError('The Gaussian list needs one row per Gaussian, as (center, sigma, amplitude).')
        if not np.isfinite(GaussianList[:, :3]).all():
            raise ValueError('The Gaussian list has values that are not finite numbers.')
        Values, Measured, Problems = self.Calculate_Features(GaussianList)
        if Problems:
            raise ValueError(' '.join(Problems))
        X = np.array([Values[Feature['name']] for Feature in self.Features])
        Z = self.Intercept + float(np.dot(self.Coefficients, X))
        Probability = float(1.0 / (1.0 + np.exp(-np.clip(Z, -500, 500))))
        # Notes on the reliability of the result.
        Warnings = []
        Numerators = {Feature['numerator'] for Feature in self.Features if Feature.get('denominator') is not None}
        for Name in sorted(Numerators):
            if Measured[Name]['count'] == 0:
                Low, High = self.Bands[Name]
                Warnings.append(f'No Gaussian was found for the band "{Name}" ({Low:g}-{High:g} 1/cm); it counts as zero.')
        for Name, Value in Values.items():
            if Name in self.FeatureRange:
                Low, High = self.FeatureRange[Name]
                if not (Low <= Value <= High):
                    Warnings.append(f'"{Name}" = {Value:.4g} is outside the range of the training data '
                                    f'({Low:.4g} to {High:.4g}).')
        if self.UncertainRange[0] < Probability < self.UncertainRange[1]:
            Warnings.append(f'The probability is between {self.UncertainRange[0]:g} and {self.UncertainRange[1]:g}, so the '
                            f'model is not confident about this spectrum. Few training spectra fell in this range.')
        return {'Probability': Probability, 'Features': Values, 'Bands': Measured, 'Warnings': Warnings,
                'ModelVersion': self.Version}
    # ------------------------------------------------------------------------------------------------------------------
    def Check(self):
        """
        This function makes sure that the model works, by predicting a test Gaussian list with one Gaussian in the middle
        of each band. An error is raised otherwise.
        """
        GaussianList = np.array([[(Low + High) / 2, 5.0, 0.02] for Low, High in self.Bands.values()])
        Result = self.Predict(GaussianList)
        if not np.isfinite(Result['Probability']):
            raise ValueError('The test prediction is not a finite number.')
    # ------------------------------------------------------------------------------------------------------------------
    def Summary(self):
        # A short description of the model, e.g., for the "About" of a menu.
        Terms = ' '.join(f'{c:+.4g} * {f["name"]}' for c, f in zip(self.Coefficients, self.Features))
        return (f'SBS model version {self.Version}\n'
                f'P(modified) = 1 / (1 + exp(-z)),  z = {self.Intercept:+.4g} {Terms}\n'
                f'File: {self.Path}')
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Save_SBS_Model(Path, Intercept, Coefficients, Features, Bands, ModelVersion, FeatureRange=None,
                   UncertainRange=Default_Uncertain_Range, Training=None, Description=''):
    """
    This function writes a trained logistic-regression model to a file that "SBS_Model" can read. The model is loaded
    and checked after writing, so an invalid file raises an error here instead of in AutoFTIR.

    :param Path: Path of the file (.npz).
    :param Intercept: The intercept of the logistic regression, in the original units of the features.
    :param Coefficients: The coefficient of each feature, in the original units (same order as "Features").
    :param Features: A list of the features, each one a dictionary of "name", "measure" ("height" or "area"),
    "numerator" (band name), and "denominator" (band name, or None for the value of the band itself).
    :param Bands: A dictionary of the window (low, high) in 1/cm for each band name.
    :param ModelVersion: A text that identifies this model, e.g., "2026.11.06-RodeoRA".
    :param FeatureRange: Optional dictionary of the (min, max) of each feature in the training data, for the warnings.
    :param UncertainRange: The probabilities between these two values get a warning.
    :param Training: Optional dictionary of information about the training (database, numbers, metrics, etc.).
    :param Description: Optional text about the model.
    :return: The loaded model.
    """
    Meta = {'format_version': Supported_Format_Version, 'model_type': 'logistic', 'model_version': str(ModelVersion),
            'description': Description, 'bands': {Name: [float(Low), float(High)] for Name, (Low, High) in Bands.items()},
            'features': [{'name': F['name'], 'measure': F['measure'], 'numerator': F['numerator'],
                          'denominator': F.get('denominator')} for F in Features],
            'feature_range': {Name: [float(Low), float(High)] for Name, (Low, High) in (FeatureRange or {}).items()},
            'uncertain_range': [float(UncertainRange[0]), float(UncertainRange[1])], 'training': Training or {}}
    np.savez(Path, meta_json=np.array(json.dumps(Meta, default=float)), intercept=np.array(float(Intercept)),
             coefficients=np.asarray(Coefficients, dtype=float).ravel())
    Model = SBS_Model(Path)
    Model.Check()
    return Model
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Default_Model_Path():
    return os.path.abspath(Get_Project_Path(*Default_Model_File))
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Load_SBS_Model(Path=None):
    """
    This function loads a model file and checks it by a test prediction.

    :param Path: Path to the model file, defaults to "data/FTIR_SBS_Model.npz".
    :return: The model and an empty string, or None and the reason that the file can't be used.
    """
    Path = Get_Default_Model_Path() if Path is None else Path
    if not os.path.isfile(Path):
        return None, f'The SBS model file ({Path}) was not found.'
    try:
        Model = SBS_Model(Path)
        Model.Check()
    except Exception as Err:
        traceback.print_exc()
        return None, f'The SBS model file ({Path}) could not be read: {Err}'
    return Model, ''
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


_Default_Model = None


def Predict_SBS_Probability(GaussianList, Model=None):
    """
    This is the main function. It estimates the probability that a binder is modified from the Gaussians of one of its
    spectra (one replicate at one aging level). For a binder with several replicates, average the probabilities of the
    replicates (see "Combine_Replicates").

    :param GaussianList: An array of the Gaussians, one per row, as (center (1/cm), sigma (1/cm), amplitude), from the
    deconvolution of the pre-processed spectrum (e.g., "Deconv['Gaussian_List']", or the "Deconv_GaussianList" column of
    the database).
    :param Model: A loaded "SBS_Model", defaults to the default model file (loaded once).
    :return: The dictionary of "SBS_Model.Predict", where "Probability" is the result.
    """
    global _Default_Model
    if Model is None:
        if _Default_Model is None:
            _Default_Model, Reason = Load_SBS_Model()
            if _Default_Model is None:
                raise FileNotFoundError(Reason)
        Model = _Default_Model
    return Model.Predict(GaussianList)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Predict_SBS_From_Spectrum(Wavenumber, Absorbance, Model=None):
    """
    This function is a shortcut for a spectrum that has not been deconvoluted yet: it runs the deconvolution of AutoFTIR
    and then "Predict_SBS_Probability". Inside AutoFTIR, use the Gaussians that are already there instead, so that the
    edits of the user to the Gaussians are included.

    :param Wavenumber: An array of the wavenumbers (1/cm), ascending.
    :param Absorbance: An array of the pre-processed absorbance (baseline-corrected and normalized, as in AutoFTIR).
    :param Model: A loaded "SBS_Model", defaults to the default model file.
    :return: The dictionary of "SBS_Model.Predict".
    """
    from scripts.Sub07_Deconvolution_Analysis import Run_Deconvolution      # Only needed here.
    X = np.asarray(Wavenumber, dtype=float)
    Y = np.asarray(Absorbance, dtype=float)
    Keep = np.isfinite(X) & np.isfinite(Y)
    Order = np.argsort(X[Keep])
    Deconv = Run_Deconvolution(X[Keep][Order], Y[Keep][Order])
    return Predict_SBS_Probability(Deconv['Gaussian_List'], Model)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Combine_Replicates(Probabilities):
    """
    This function combines the probabilities of the replicates of one binder (at one or several aging levels), as their
    mean, which is how the model was validated.

    :param Probabilities: A list of probabilities.
    :return: The mean probability, or NaN for an empty list.
    """
    Values = np.asarray([P for P in Probabilities if P is not None and np.isfinite(P)], dtype=float)
    return float(np.mean(Values)) if Values.size > 0 else float('nan')
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


if __name__ == '__main__':
    # A quick check of the default model file: "python -m scripts.Sub12_SBSDetection" from the project folder.
    Model, Reason = Load_SBS_Model()
    print(Model.Summary() if Model is not None else Reason)
