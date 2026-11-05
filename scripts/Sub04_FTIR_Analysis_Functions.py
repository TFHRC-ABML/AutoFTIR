# Title:
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date:
# ======================================================================================================================

# Importing the required libraries.
import os
import sys
import ast
import csv
import pickle
import fnmatch
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import sparse
from scipy.signal import find_peaks
from scipy.optimize import curve_fit, root_scalar
from scipy.interpolate import interp1d


def Read_FTIR_Data(Inppath):
    """
    This function reads the raw FTIR data file and retrun the wavenumber and absorbance in two column array.

    :param Inppath: Path to the input raw file. 
    :return Data: A 2D array with two columns, wavenumber (1/cm) and absorbance. 
    """
    # The "*.dpt" file is tab or comma delimited file, where first column is wavenumber in 1/cm, and second column is 
    #   the absorbance. First, try the simple tab or comma delimited files. 
    Data = None
    for delimiter in ['\t', ',']:
        try:
            Data = np.loadtxt(Inppath, delimiter=delimiter)
            break
        except (ValueError, OSError):
            continue
    if type(Data) == type(None):
        # If the file wasn't a simple "*.dpt" file with tab or comma delimited style, search for other options, like the
        #   sample file I got from Butimar. 
        if not fnmatch.fnmatch(os.path.basename(Inppath), '*.csv'):     # For non-CSV formats, skip the reading.
            raise Exception(f'Input file is not readable for AutoFTIR. Please contact the authors to include your file')
        # Read a sample of input to guess the delimiter. 
        with open(Inppath, 'r', encoding='utf-8') as f:
            sample = f.read(2048)       # Read enough to guess
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
            except csv.Error:
                raise ValueError("Could not detect delimiter.")
        # Read the file again to detect how many rows to skip. 
        skip_rows = 0
        with open(Inppath, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    # Try converting to float to detect data line
                    [float(x) for x in line.strip().split(delimiter)]
                    break
                except ValueError:
                    skip_rows += 1
        # Finally, read the file and convert to array. 
        df = pd.read_csv(Inppath, delimiter=delimiter, skiprows=skip_rows, header=None)
        Data = df.to_numpy()
    # Sort based on the wavelengths (to avoid problem with interpolations)
    Data = Data[np.argsort(Data[:, 0]), :]
    # Check if the data provided in terms of "percent transmittance".
    if Data[:, 1].mean() > 20:
        Data[:, 1] = -np.log10(Data[:, 1] / 100)
    # Return the results.
    return Data
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Baseline_Adjustment_ALS(Data, Lambda, Ratio, NumIter):
    """
    This function performs the baseline adjustment using the Asymmetric Least Square (ALS) Smoothing method. 

    :param Data: A 2D array of the raw data.
    :param Lambda: smoothing parameter that controls the trade-off between the data fidelity term and the smoothness of 
    the baseline. A larger value enforces a smoother baseline, making it less sensitive to small fluctuations and noise 
    in the data. A smaller value allows the baseline to follow more rapid changes in the data, which might be helpful 
    if the baseline has more abrupt variations. Typically, values can range from hundreds to millions, depending on the 
    scale of the data and the desired level of smoothness.
    :param Ratio: ratio controls the asymmetry of the weighting in the least squares fitting, making it more or less 
    sensitive to points that lie above or below the fitted baseline. Since ALS is asymmetric, ratio defines the 
    relative penalty on positive versus negative residuals. This is useful because, in many cases, we want the baseline 
    to stay below the main data peaks (like in spectroscopy). A higher ratio value places more weight on residuals that 
    are above the baseline, which helps pull the baseline downwards. A lower ratio value reduces the weight on points 
    above the baseline, allowing the baseline to fit closer to the data points. Commonly, ratio values are set between 
    0.001 and 0.1, with smaller values pushing the baseline to lie below the peaks.
    :param NumIter: Number of iteration, default is 150.
    :return: Updated "Data" array with the adjusted absorbance. 
    """
    # First calculate the baseline.
    Baseline = Calc_Baseline_ALS(
        Data[:, 1], lam=Lambda, p=Ratio, niter=NumIter)
    # Calculate the corrected intensities.
    Data2 = Data.copy()
    Data2[:, 1] = Data2[:, 1] - Baseline
    # Find the index of data points with negative intensity.
    Index = np.where(Data2[:, 1] < 0)[0]
    if len(Index) < 3:
        raise Exception('The baseline of this spectrum could not be adjusted, since it has almost no points below the ' +
                        'fitted baseline. Please check if the absorbance values are all the same (e.g., all zeros).')
    Batches, TempList = [], []
    i = 0
    while True:
        TempList.append(Index[i])
        if Index[i] + 1 != Index[i+1]:
            if len(TempList) > 3:       # Otherwise, we have noise.
                Batches.append(TempList)
            TempList = []
        i += 1                          # Update the indexing.
        if i == len(Index)-2:
            break
    # Find the negative X-coordinates to perform the linear baseline correction.
    X = Data2[:, 0]
    Y = Data2[:, 1]
    XPoints = [X[0]]
    for i in range(len(Batches)):
        XPoints.append(X[Batches[i][np.argmin(Y[Batches[i]])]])
    XPoints.append(X[-1])
    # Perform the linear baseline correction on the ALS Smoothing corrected data.
    Data3 = Baseline_Adjustment(Data2, XPoints)
    # Return the results.
    return Data3
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Calc_Baseline_ALS(y, lam=1e6, p=0.01, niter=100):
    """
    This is the main function for applying the baseline adjustment using the ALS Smoothing method. 

    :param y: An array of the Y-values. 
    :param lam: smoothing parameter, refer to the "Baseline_Adjustment_ALS" function, defaults to 1e6
    :param p: ratio parameters, refer to the "Baseline_Adjustment_ALS" function, defaults to 0.01
    :param niter: Number of iterations, defaults to 100
    :return: An array of the baseline for the input Y-values. 
    """
    L = len(y)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L - 2))
    w = np.ones(L)
    for i in range(niter):
        W = sparse.diags(w, 0)
        Z = W + lam * D.dot(D.T)
        baseline = sparse.linalg.spsolve(Z, w * y)
        w = p * (y > baseline) + (1 - p) * (y < baseline)
    return baseline
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Baseline_Adjustment(Data, Base_XPoints):
    """
    This function performs the baseline adjustment for the FTIR results. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance intesity.
    :param Base_XPoints: Array of the wavelengths used for baseline adjustment (usually 8 reference wavelengths).
    :param return: the adjusted results as a 2D array of the same shape. 
    """
    # First, Find the corresponding absorbance for the Baseline lines.
    Base_YPoints = np.interp(Base_XPoints, Data[:, 0], Data[:, 1])
    # Create the interpolation functions.
    Func = interp1d(Base_XPoints, Base_YPoints,
                    kind='linear', fill_value='extrapolate')
    # Make a copy from the data.
    Data_Adj = Data.copy()
    # Perform the baseline adjustment.
    Data_Adj[:, 1] = Data[:, 1] - Func(Data[:, 0])
    # Return the results
    return Data_Adj
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Baseline_Adjustment_Hofko(Data, Range=[2000, 2500]):
    """
    Adjusting the baseline of the spectrum using the Hofko et al. 2018 procedure, which vertically shift the whole 
    curve to have the integral of spectrum on a specific range equal to zero. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance intesity.
    :param Range: A range of the data used for integration, defaults to [2000, 25000]
    :return: the adjusted data. 
    """
    # Define an objective function which calculates the integral based on the parameter c1.
    Index = np.where((Data[:, 0] >= Range[0]) & (Data[:, 0] <= Range[1]))[0]
    def ObjFunc(c1): return np.trapz(x=Data[Index, 0], y=Data[Index, 1] - c1)
    # Use a simple optimization algorithm to find the correct c1.
    result = root_scalar(ObjFunc, bracket=[-1.0, 1.0], method='brentq')
    # Return the baseline adjusted spectrum.
    Data2 = Data.copy()
    Data2[:, 1] -= result.root
    return Data2
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Normalization_Method_A(Data):
    """
    This function performs the Normalization of the FTIR data using the method A, which normalizes the peak in the 
    range of 600 to 4000 cm^-1 to 0.25.

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity.
    :param return: the normalized results as a 2D array of the same shape. 
    """
    # Find the portion of data falls between 600 to 4000 cm^-1.
    Index = np.where((Data[:, 0] <= 4000) & (Data[:, 0] >= 600))[0]
    # Find the peak.
    PeakValue = Data[Index, 1].max()
    # Find the ratio.
    Beta = 0.25 / PeakValue
    # Calculated the normalized results.
    Res = Data.copy()
    Res[:, 1] = Res[:, 1] * Beta
    # Return the results.
    return Res, Beta
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Normalization_Method_B(Data):
    """
    This function performs the Normalization of the FTIR data using the method B, which normalizes the peak in the 
    range of 600 to 1800 cm^-1 to 0.15.

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity.
    :param return: the normalized results as a 2D array of the same shape. 
    """
    # Find the portion of data falls between 600 to 4000 cm^-1.
    Index = np.where((Data[:, 0] <= 1600) & (Data[:, 0] >= 1300))[0]
    # Find the peak.
    PeakValue = Data[Index, 1].max()
    # Find the ratio.
    Beta = 0.15 / PeakValue
    # Calculated the normalized results.
    Res = Data.copy()
    Res[:, 1] *= Beta
    # Return the results.
    return Res, Beta
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Normalization_Method_C(Data):
    """
    This function performs the Normalization of the FTIR data using the method C, which normalizes the area in the 
    range of 600 to 4000 cm^-1 to 50.

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity.
    :param return: the normalized results as a 2D array of the same shape. 
    """
    # Find the portion of data falls between 600 to 4000 cm^-1.
    Index = np.where((Data[:, 0] <= 4000) & (Data[:, 0] >= 600))[0]
    # Calculating the area.
    Area = np.trapz(Data[Index, 1], Data[Index, 0])
    # Calculating the ratio.
    Beta = 50 / Area
    # Calculated the normalized results.
    Res = Data.copy()
    Res[:, 1] *= Beta
    # Return the results.
    return Res, Beta
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Normalization_Method_D(Data):
    """
    This function performs the Normalization of the FTIR data using the method D, which normalizes the area in the 
    range of 600 to 1800 cm^-1 to 25.

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity.
    :param return: the normalized results as a 2D array of the same shape. 
    """
    # Find the portion of data falls between 600 to 4000 cm^-1.
    Index = np.where((Data[:, 0] <= 1800) & (Data[:, 0] >= 600))[0]
    # Calculating the area.
    Area = np.trapz(Data[Index, 1], Data[Index, 0])
    # Calculating the ratio.
    Beta = 25 / Area
    # Calculated the normalized results.
    Res = Data.copy()
    Res[:, 1] *= Beta
    # Return the results.
    return Res, Beta
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Calc_ICO_ISO_Indices(Data):
    """
    This function calls different functions to calculate the area for the Carbonyl, Sulfoxide, and Aliphatic functional 
    groups and calculate the Carbonyl and Sulfoxide index. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity (Baseline adjusted and normalized).
    :return: A dictionary of the results, including ICO, ISO using baseline and tangential methods, as well as 
    calculated areas, and datapoints used for calculation. 
    """

    # First calculate the Carbonyl, Sulfoxide, and Aliphatic areas.
    Carbonyl = Calc_Carbonyl_Area(Data)
    Sulfoxide = Calc_Sulfoxide_Area(Data)
    Aliphatic = Calc_Aliphatic_Area(Data)
    # Calculate the Indices.
    ICO_base = Carbonyl['Area_Baseline'] / Aliphatic['Area_Baseline']
    ICO_tang = Carbonyl['Area_Tangential'] / Aliphatic['Area_Tangential']
    ISO_base = Sulfoxide['Area_Baseline'] / Aliphatic['Area_Baseline']
    ISO_tang = Sulfoxide['Area_Tangential'] / Aliphatic['Area_Tangential']
    # Prepare the results for returning.
    Results = {
        'ICO_Baseline': ICO_base,
        'ICO_Tangential': ICO_tang,
        'ISO_Baseline': ISO_base,
        'ISO_Tangential': ISO_tang,
        'Carbonyl_Area_Baseline': Carbonyl['Area_Baseline'],
        'Carbonyl_Area_Tangential': Carbonyl['Area_Tangential'],
        'Sulfoxide_Area_Baseline': Sulfoxide['Area_Baseline'],
        'Sulfoxide_Area_Tangential': Sulfoxide['Area_Tangential'],
        'Aliphatic_Area_Baseline': Aliphatic['Area_Baseline'],
        'Aliphatic_Area_Tangential': Aliphatic['Area_Tangential'],
        'Carbonyl_Peak_Wavenumber': Carbonyl['XPeak'],
        'Sulfoxide_Peak_Wavenumber': Sulfoxide['XPeak'],
        'Aliphatic_Peak1_Wavenumber': Aliphatic['XPeak'][0],
        'Aliphatic_Peak2_Wavenumber': Aliphatic['XPeak'][1],
        'Carbonyl_XY': np.vstack((Carbonyl['Xvalues'], Carbonyl['Yvalues'])),
        'Sulfoxide_XY': np.vstack((Sulfoxide['Xvalues'], Sulfoxide['Yvalues'])),
        'Aliphatic_XY': np.vstack((Aliphatic['Xvalues'], Aliphatic['Yvalues']))}
    # Return the results.
    return Results
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Calc_Aliphatic_Area(Data):
    """
    This function calculates the area of the Aliphatic functional group using both baseline and tangential methods. It 
    is noted that the Aliphatic functional group expected to result in two peaks, one around 1376 cm^-1 and another one
    around 1460 cm^-1. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity (Baseline adjusted and normalized).
    :raises Warning: In case of not recognizing the peak in the intended wavelength interval.
    :return: A dictionary of the results, including the calculated area for the Aliphatic functional group using both 
    baseline and tangential methods, as well as the data points used for this calculations. 
    """
    # Define X & Y, because it's easier :)
    X = Data[:, 0]
    Y = Data[:, 1]
    # First, find the peak of data around 1680 (1/cm). For this purpose, searching area of 1350 to 1525 cm^-1.
    XPeak, YPeak, Prominence, XLeft, XRight = Find_Peaks(
        Data, [1350, 1525], 0.001)
    # Check if two peaks were found.
    if len(XPeak) < 1:
        raise Warning(
            'Peak was NOT found in the range of 1350 to 1525 cm^-1 for this binder! Check manually!')
        return 0.0
    elif len(XPeak) > 1:
        # More than two peak were found. Using two close ones as main peaks.
        SortedIndex = np.argsort(YPeak)
        MaxIndex = SortedIndex[-2:]      # Get the highwst peaks.
        # Sort based on their location.
        MaxIndex = MaxIndex[np.argsort(np.array(XPeak)[MaxIndex])]
        # Specify the XLeft and XRight.
        XLeft = min(XLeft)
        XRight = max(XRight)
        # Fix the Peaks.
        XPeak = np.array(XPeak)[MaxIndex]
        YPeak = np.array(YPeak)[MaxIndex]
    # --------------------------------------------------------------------------------------------
    # Find the boundaries of the peak for calculating the area.
    # Step 1: using moving average of span 3.
    XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # Step 2: Fit the Gaussian normal distribution and try to remove data after and before 5% of peak.
    XLeft, XRight = GaussianFit_Bound_Modify_DoublePeak(
        X, Y, XLeft, XRight, XPeak, YPeak)
    XLeft, XRight = MinimumCheck_Bound_Modify_DoublePeak(
        X, Y, XLeft, XRight, XPeak, YPeak)
    XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # --------------------------------------------------------------------------------------------
    # Calculating the area.
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    Area_Base = np.trapz(Y[Index], X[Index])
    # For Tangential, be careful, we got the area connected to the mid value.
    P2PIndex = np.where((X >= XPeak[0]) & (X <= XPeak[1]))[0]
    Xmid = X[P2PIndex[np.argmin(Y[P2PIndex])]]
    Ymid = Y[P2PIndex[np.argmin(Y[P2PIndex])]]
    Area1 = np.abs(X[Index[0]] - Xmid) * 0.5 * (Y[Index[0]] + Ymid)
    Area2 = np.abs(X[Index[1]] - Xmid) * 0.5 * (Y[Index[1]] + Ymid)
    Area_Tang = Area_Base - Area1 - Area2
    # --------------------------------------------------------------------------------------------
    # # Plot the data for verification purposes.
    # plt.figure()
    # idx = np.where((X >= XLeft - 10) & (X <= XRight + 30))[0]
    # plt.plot(X[idx], Y[idx], 'k-', label='FTIR data')
    # idx = np.where((X >= XLeft) & (X <= XRight))[0]
    # plt.plot(X[idx], Y[idx], 'x', label='Data points used')
    # plt.legend()
    # --------------------------------------------------------------------------------------------
    # Returning the results.
    Results = {
        'Area_Baseline': Area_Base,
        'Area_Tangential': Area_Tang,
        'Xvalues': X[Index],
        'Yvalues': Y[Index],
        'XPeak': XPeak}
    # Return the results.
    return Results
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Calc_Sulfoxide_Area(Data):
    """
    This function calculates the area of the Sulfoxide functional group using both baseline and tangential methods. It 
    is noted that the Sulfoxide functional group expected to result in a peak around 1030 cm^-1. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity (Baseline adjusted and normalized).
    :raises Warning: In case of not recognizing the peak in the intended wavelength interval.
    :return: A dictionary of the results, including the calculated area for the Sulfoxide functional group using both 
    baseline and tangential methods, as well as the data points used for this calculations.
    """
    # Define X & Y, because it's easier :)
    X = Data[:, 0]
    Y = Data[:, 1]
    # First, find the peak of data around 1680 (1/cm). For this purpose, searching area of 1620 to 1800 cm^-1.
    XPeak, YPeak, Prominence, XLeft, XRight = Find_Peaks(
        Data, [970, 1070], 0.001)
    # Check if the peak was found.
    if len(XPeak) < 1:
        raise Warning(
            'Peak was NOT found in the range of 1620 to 1800 cm^-1 for this binder! Check manually!')
        return np.nan
    elif len(XPeak) > 1:
        # More than one peak was found. Using only one peak which is closer to 1680 cm^-1.
        Distance = np.abs(np.array(XPeak) - 1030)
        Index = np.argmin(Distance)
    else:
        # We found the only peak, which is for carbonyl.
        Index = 0
    # Get the property of the peak.
    XPeak = XPeak[Index]
    YPeak = YPeak[Index]
    XLeft = XLeft[Index]
    XRight = XRight[Index]
    Prominence = Prominence[Index]
    XPeak2Report = XPeak
    # --------------------------------------------------------------------------------------------
    # Find the boundaries of the peak for calculating the area.
    # Step 1: using moving average of span 3.
    XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # Step 2: Fit the Gaussian normal distribution and try to remove data after and before 5% of peak.
    XLeft, XRight = GaussianFit_Bound_Modify(X, Y, XLeft, XRight, XPeak, YPeak)
    XLeft, XRight = MinimumCheck_Bound_Modify(
        X, Y, XLeft, XRight, XPeak, YPeak)
    XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # --------------------------------------------------------------------------------------------
    # Solve the problem with double-peak.
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    XX = X[Index]
    YY = Y[Index]
    PeakIndices, PeakProperties = find_peaks(
        YY, height=0, prominence=(YY.max() - YY.min()) / 10, wlen=200)
    if len(PeakIndices) > 1:
        # We have double-peak. Find the closest peak.
        XPeak = XX[PeakIndices]
        Distance = np.abs(np.array(XPeak) - 1680)
        PeakIndex = np.argmin(Distance)
        # Clean the left side.
        if PeakIndex > 0:
            XPeak1 = XPeak[PeakIndex]
            XPeak2 = XPeak[PeakIndex-1]
            BetweenIndex = np.where((XX >= XPeak2) & (XX <= XPeak1))[0]
            XLeft = XX[BetweenIndex[np.argmin(YY[BetweenIndex])]]
        # Clean the right side.
        if PeakIndex < len(PeakIndices) - 1:
            XPeak1 = XPeak[PeakIndex]
            XPeak2 = XPeak[PeakIndex+1]
            BetweenIndex = np.where((XX <= XPeak2) & (XX >= XPeak1))[0]
            XRight = XX[BetweenIndex[np.argmin(YY[BetweenIndex])]]
        XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # --------------------------------------------------------------------------------------------
    # Calculating the area.
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    Area_Base = np.trapz(Y[Index], X[Index])
    Area_Tang = Area_Base - \
        np.abs(X[Index[0]] - X[Index[-1]]) * Y[Index[[0, -1]]].mean()
    # --------------------------------------------------------------------------------------------
    # # Plot the data for verification purposes.
    # plt.figure()
    # idx = np.where((X >= XLeft - 10) & (X <= XRight + 30))[0]
    # plt.plot(X[idx], Y[idx], 'k-', label='FTIR data')
    # idx = np.where((X >= XLeft) & (X <= XRight))[0]
    # plt.plot(X[idx], Y[idx], 'x', label='Data points used')
    # plt.legend()
    # --------------------------------------------------------------------------------------------
    # Returning the results.
    Results = {
        'Area_Baseline': Area_Base,
        'Area_Tangential': Area_Tang,
        'Xvalues': X[Index],
        'Yvalues': Y[Index],
        'XPeak': XPeak2Report}
    return Results
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Calc_Carbonyl_Area(Data):
    """
    This function calculates the area of the Carbonyl functional group using both baseline and tangential methods. It 
    is noted that the Carbonyl functional group expected to result in a peak around 1680 cm^-1. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity (Baseline adjusted and normalized).
    :raises Warning: In case of not recognizing the peak in the intended wavelength interval.
    :return: A dictionary of the results, including the calculated area for the Carbonyl functional group using both 
    baseline and tangential methods, as well as the data points used for this calculations.    
    """
    # Define X & Y, because it's easier :)
    X = Data[:, 0]
    Y = Data[:, 1]
    # First, find the peak of data around 1680 (1/cm). For this purpose, searching area of 1620 to 1800 cm^-1.
    XPeak, YPeak, Prominence, XLeft, XRight = Find_Peaks(
        Data, [1620, 1800], 0.001)
    # Check if the peak was found.
    if len(XPeak) < 1:
        raise Warning(
            'Peak was NOT found in the range of 1620 to 1800 cm^-1 for this binder! Check manually!')
        return np.nan
    elif len(XPeak) > 1:
        # More than one peak was found. Using only one peak which is closer to 1680 cm^-1.
        Distance = np.abs(np.array(XPeak) - 1680)
        Index = np.argmin(Distance)
    else:
        # We found the only peak, which is for carbonyl.
        Index = 0
    # Get the property of the peak.
    XPeak = XPeak[Index]
    YPeak = YPeak[Index]
    XLeft = XLeft[Index]
    XRight = XRight[Index]
    Prominence = Prominence[Index]
    XPeak2Report = XPeak
    # --------------------------------------------------------------------------------------------
    # Find the boundaries of the peak for calculating the area.
    # Step 1: using moving average of span 3.
    XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # Step 2: Fit the Gaussian normal distribution and try to remove data after and before 5% of peak.
    XLeft, XRight = GaussianFit_Bound_Modify(X, Y, XLeft, XRight, XPeak, YPeak)
    XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # --------------------------------------------------------------------------------------------
    # Solve the problem with double-peak.
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    XX = X[Index]
    YY = Y[Index]
    PeakIndices, PeakProperties = find_peaks(
        YY, height=0, prominence=(YY.max() - YY.min()) / 5, wlen=200)
    if len(PeakIndices) > 1:
        # We have double-peak. Find the closest peak.
        XPeak = XX[PeakIndices]
        Distance = np.abs(np.array(XPeak) - 1680)
        PeakIndex = np.argmin(Distance)
        # Clean the left side.
        if PeakIndex > 0:
            XPeak1 = XPeak[PeakIndex]
            XPeak2 = XPeak[PeakIndex-1]
            BetweenIndex = np.where((XX >= XPeak2) & (XX <= XPeak1))[0]
            XLeft = XX[BetweenIndex[np.argmin(YY[BetweenIndex])]]
        # Clean the right side.
        if PeakIndex < len(PeakIndices) - 1:
            XPeak1 = XPeak[PeakIndex]
            XPeak2 = XPeak[PeakIndex+1]
            BetweenIndex = np.where((XX <= XPeak2) & (XX >= XPeak1))[0]
            XRight = XX[BetweenIndex[np.argmin(YY[BetweenIndex])]]
        XLeft, XRight = MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak)
    # --------------------------------------------------------------------------------------------
    # Calculating the area.
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    Area_Base = np.trapz(Y[Index], X[Index])
    Area_Tang = Area_Base - \
        np.abs(X[Index[0]] - X[Index[-1]]) * Y[Index[[0, -1]]].mean()
    # --------------------------------------------------------------------------------------------
    # # Plot the data for verification purposes.
    # plt.figure()
    # idx = np.where((X >= XLeft - 10) & (X <= XRight + 30))[0]
    # plt.plot(X[idx], Y[idx], 'k-', label='FTIR data')
    # idx = np.where((X >= XLeft) & (X <= XRight))[0]
    # plt.plot(X[idx], Y[idx], 'x', label='Data points used')
    # plt.legend()
    # --------------------------------------------------------------------------------------------
    # Returning the results.
    Results = {
        'Area_Baseline': Area_Base,
        'Area_Tangential': Area_Tang,
        'Xvalues': X[Index],
        'Yvalues': Y[Index],
        'XPeak': XPeak2Report}
    return Results
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def GaussianFit_Bound_Modify(X, Y, XLeft, XRight, XPeak, YPeak):
    """
    This function fits a Gaussian normal distribution function to the data points around a peak point and try to 
    confine the boundaries based on the fitted function, where the left and right boundaries are limited to the 
    corresponding boundary of the normal distribution function from 5% to 95% interval.  

    :param X: An array of the wavenumbers (1/cm).
    :param Y: An array of the absorbances. 
    :param XLeft: Current lower wavenumber boundary (1/cm).
    :param XRight: Current upper wavenumber boundary (1/cm).
    :param XPeak: Wavenumber of the peak point (1/cm).
    :param YPeak: Absorbance of the peak point.
    :return: The updated lower and upper wavewnumber boundaries (1/cm).
    """
    # Find the data points to fit the Gaussian.
    Index = np.where((Y <= YPeak) & (Y >= 0.6 * YPeak)
                     & (X >= XLeft) & (X <= XRight))[0]
    # Exclude points far from the cluster of points.
    XX = X[Index]
    PeakIndx = np.argmin(np.abs(XPeak - XX))
    XDiff = np.diff(XX)
    SplitIndex = np.insert(np.where(XDiff > 1.2 * np.median(XDiff))[0], 0, 0)
    SplitIndex = np.insert(SplitIndex, len(SplitIndex), len(Index))
    for i in range(1, len(SplitIndex)):
        if PeakIndx < SplitIndex[i]:
            Index = Index[SplitIndex[i-1]:SplitIndex[i]]
            break

    # fit the gaussian.
    InitialGuess = [YPeak, XPeak, 0.5 * (XRight - XLeft)]
    FitCoeff, Covariance = curve_fit(
        Gaussian_Function, X[Index], Y[Index], p0=InitialGuess)
    a, Mu, Sigma = FitCoeff

    # Specify the boundaries of Gaussian at 5% of its peak, which corresponds to x_bound = Mu +- SQRT(-2*Sigma*Ln(0.05))
    XLeft_Gaussian = Mu - np.sqrt(-2 * (Sigma ** 2) * np.log(0.05))
    XRight_Gaussian = Mu + np.sqrt(-2 * (Sigma ** 2) * np.log(0.05))
    # Check the boundaries.
    if XLeft < XLeft_Gaussian:
        XLeft = XLeft_Gaussian
    if XRight > XRight_Gaussian:
        XRight = XRight_Gaussian
    # Return the results.
    return XLeft, XRight
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def GaussianFit_Bound_Modify_DoublePeak(X, Y, XLeft, XRight, XPeak, YPeak):
    """
    This function fits a Gaussian normal distribution function to the data points around each of the two main peaks of 
    the Aliphatic functional group and try to confine the boundaries based on the fitted function, where the left and 
    right boundaries are limited to the corresponding boundary of the normal distribution function from 5% to 95% 
    interval.  

    :param X: An array of the wavenumbers (1/cm).
    :param Y: An array of the absorbances. 
    :param XLeft: Current lower wavenumber boundary (1/cm).
    :param XRight: Current upper wavenumber boundary (1/cm).
    :param XPeak: A list of the peak points wavenumber (1/cm).
    :param YPeak: A list of the peak points absorbance.
    :return: The updated lower and upper wavewnumber boundaries (1/cm).
    """
    # First, find the Gaussian for the first peak.
    # Find the mid point.
    Index = np.where((X >= XPeak[0]) & (X <= XPeak[1]))[0]
    Xmid = X[Index[np.argmin(Y[Index])]]
    Ymid = Y[Index[np.argmin(Y[Index])]]
    # Find the index of the points used for gaussian to first peak.
    Index = np.where((Y <= YPeak[0]) & (
        Y >= 0.6 * YPeak[0]) & (X >= XLeft) & (X <= Xmid))[0]
    # Exclude points far from the cluster of points.
    XX = X[Index]
    PeakIndx = np.argmin(np.abs(XPeak[0] - XX))
    XDiff = np.diff(XX)
    SplitIndex = np.insert(np.where(XDiff > 1.2 * np.median(XDiff))[0], 0, 0)
    SplitIndex = np.insert(SplitIndex, len(SplitIndex), len(Index))
    for i in range(1, len(SplitIndex)):
        if PeakIndx < SplitIndex[i]:
            Index = Index[SplitIndex[i-1]:SplitIndex[i]]
            break
    # fit the gaussian.
    InitialGuess = [YPeak[0], XPeak[0], 0.5 * (Xmid - XLeft)]
    FitCoeff1, _ = curve_fit(
        Gaussian_Function, X[Index], Y[Index], p0=InitialGuess)
    a1, Mu1, Sigma1 = FitCoeff1
    # Specify the boundaries of Gaussian at 5% of its peak, which corresponds to x_bound = Mu +- SQRT(-2*Sigma*Ln(0.05))
    XLeft_Gaussian = Mu1 - np.sqrt(-2 * (Sigma1 ** 2) * np.log(0.05))
    # Check the boundaries.
    if XLeft < XLeft_Gaussian:
        XLeft = XLeft_Gaussian
    # ------------------------------------------------------------------------------------------------------------------
    # Now, check the second peak.
    Index = np.where((Y <= YPeak[1]) & (
        Y >= 0.6 * YPeak[1]) & (Y >= Ymid) & (X >= Xmid) & (X <= XRight))[0]
    # Exclude points far from the cluster of points.
    XX = X[Index]
    PeakIndx = np.argmin(np.abs(XPeak[1] - XX))
    XDiff = np.diff(XX)
    SplitIndex = np.insert(np.where(XDiff > 1.2 * np.median(XDiff))[0], 0, 0)
    SplitIndex = np.insert(SplitIndex, len(SplitIndex), len(Index))
    for i in range(1, len(SplitIndex)):
        if PeakIndx < SplitIndex[i]:
            Index = Index[SplitIndex[i-1]:SplitIndex[i]]
            break
    # fit the gaussian.
    InitialGuess = [YPeak[1], XPeak[1], 0.5 * (Xmid - XLeft)]
    FitCoeff2, _ = curve_fit(
        Gaussian_Function, X[Index], Y[Index], p0=InitialGuess)
    a2, Mu2, Sigma2 = FitCoeff2
    # Specify the boundaries of Gaussian at 5% of its peak, which corresponds to x_bound = Mu +- SQRT(-2*Sigma*Ln(0.05))
    XRight_Gaussian = Mu2 + np.sqrt(-2 * (Sigma2 ** 2) * np.log(0.05))
    # Check the boundaries.
    if XRight > XRight_Gaussian:
        XRight = XRight_Gaussian
    # Return the results.
    return XLeft, XRight
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def MovingAvg_Bound_Modify(X, Y, XLeft, XRight, YPeak):
    """
    This function uses the moving average concept to confine the boundaries where a nearly horizontal line appears next 
    to the peak bump.  

    :param X: An array of the wavenumbers (1/cm).
    :param Y: An array of the absorbances. 
    :param XLeft: Current lower wavenumber boundary (1/cm).
    :param XRight: Current upper wavenumber boundary (1/cm).
    :param YPeak: Absorbance of the peak point(s).
    :return: The updated lower and upper wavewnumber boundaries (1/cm).
    """
    # Find the index of the data points in the range of [XLeft, XRight].
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    # Define new variables for X- and Y-coordinates.
    XX = X[Index]
    YY = Y[Index]
    # First, for the left side, calculating the moving slope and update XLeft with change in moving slope of more than 1.
    MovingSlope = []
    for i in range(3, len(XX)):
        MovingSlope.append(YY[:i].mean())
    MovingSlope = np.abs(np.array(MovingSlope))
    MovingSlope = np.diff(MovingSlope) / MovingSlope[0] * 100   # In percent.
    RemoveIndex = np.where(MovingSlope >= 1)[0]
    if len(RemoveIndex) > 0:
        RemoveIndex = RemoveIndex[0]
    if RemoveIndex != 0:
        XLeft = X[Index[RemoveIndex + 2]]
    # Now, do the same for right side.
    MovingSlope = []
    for i in range(2, len(XX)):
        MovingSlope.append(YY[-i:].mean())
    MovingSlope = np.abs(np.array(MovingSlope))
    MovingSlope = np.diff(MovingSlope) / MovingSlope[0] * 100   # In percent.
    RemoveIndex = np.where(MovingSlope >= 1)[0][0]
    if RemoveIndex != 0:
        XRight = X[Index[-(RemoveIndex + 2)]]
    # Return the results.
    return XLeft, XRight
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def MinimumCheck_Bound_Modify(X, Y, XLeft, XRight, XPeak, YPeak):
    """
    This function simply checks if the outter wavenumber boundaries are local minima. 

    :param X: An array of the wavenumbers (1/cm).
    :param Y: An array of the absorbances. 
    :param XLeft: Current lower wavenumber boundary (1/cm).
    :param XRight: Current upper wavenumber boundary (1/cm).
    :param XPeak: Wavenumber of the peak point.
    :param YPeak: Absorbance of the peak point.
    :return: The updated lower and upper wavewnumber boundaries (1/cm).
    """
    # Find the index of the data points in the range of [XLeft, XRight].
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    # Define new variables for X- and Y-coordinates.
    XX = X[Index]
    YY = Y[Index]
    # Check the left side.
    LeftIndex = np.where(XX <= XPeak)[0]
    if YY[0] != YY[LeftIndex].min():
        XLeft = XX[LeftIndex[np.argmin(YY[LeftIndex])]]
    # Check the right side.
    RightIndex = np.where(XX >= XPeak)[0]
    if YY[-1] != YY[RightIndex].min():
        XRight = XX[RightIndex[np.argmin(YY[RightIndex])]]

    return XLeft, XRight
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def MinimumCheck_Bound_Modify_DoublePeak(X, Y, XLeft, XRight, XPeak, YPeak):
    """
    This function simply checks if the outter wavenumber boundaries are local minima. This function is for Aliphatic 
    functional group with two peaks.  

    :param X: An array of the wavenumbers (1/cm).
    :param Y: An array of the absorbances. 
    :param XLeft: Current lower wavenumber boundary (1/cm).
    :param XRight: Current upper wavenumber boundary (1/cm).
    :param XPeak: Wavenumber of the peak points (1/cm).
    :param YPeak: Absorbance of the peak points.
    :return: The updated lower and upper wavewnumber boundaries (1/cm).
    """
    # Find the index of the data points in the range of [XLeft, XRight].
    Index = np.where((X >= XLeft) & (X <= XRight))[0]
    # Define new variables for X- and Y-coordinates.
    XX = X[Index]
    YY = Y[Index]
    # Check the left side.
    LeftIndex = np.where(XX <= XPeak[0])[0]
    if YY[0] != YY[LeftIndex].min():
        XLeft = XX[LeftIndex[np.argmin(YY[LeftIndex])]]
    # Check the right side.
    RightIndex = np.where(XX >= XPeak[1])[0]
    if YY[-1] != YY[RightIndex].min():
        XRight = XX[RightIndex[np.argmin(YY[RightIndex])]]

    return XLeft, XRight
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Gaussian_Function(x, a, Mu, Sigma):
    """
    This function is the main formula for the Gaussian normal distribution. 

    :param x: The point of interest.
    :param a: Direct multiplier of the normal distribution.
    :param Mu: location of the peak value (average of data). 
    :param Sigma: Standard deviation of the data. 
    :return: 
    """
    return a * np.exp(-((x - Mu) ** 2) / (2 * Sigma ** 2))
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Get_Aliphatic_Peaks(X, Y, Xmin, Xmax, AliphaticGaussians):
    """
    This function finds the two Aliphatic peaks of a spectrum, for saving to the database. They are always the peaks of the
    measured spectrum. If the spectrum has fewer than two peaks in the range, but the two fitted Aliphatic Gaussians are in
    the range, the record can still be saved: only the peaks really found in the spectrum are returned, and the missing
    ones are None, along with a warning for the user. If neither of them has two peaks in the range, an error is raised.

    :param X: An array of the processed wavenumbers (1/cm).
    :param Y: An array of the processed absorbance.
    :param Xmin: Minimum of the Aliphatic range (1/cm).
    :param Xmax: Maximum of the Aliphatic range (1/cm).
    :param AliphaticGaussians: An array of the Aliphatic Gaussians (mean, standard deviation, amplitude).
    :return: A list of the two locations, a list of the two absorbance values, and the warning (an empty string if there
    is none). The first one is the lower wavenumber.
    """
    XPeak, YPeak = Find_Peaks(np.column_stack((X, Y)), [Xmin, Xmax], 0.001)[:2]
    XPeak, YPeak = np.array(XPeak, dtype=float), np.array(YPeak, dtype=float)
    if len(XPeak) >= 2:
        # If there are more than two peaks, the two highest ones are the main peaks, sorted based on their location.
        Index = np.argsort(YPeak)[-2:]
        Index = Index[np.argsort(XPeak[Index])]
        return XPeak[Index].tolist(), YPeak[Index].tolist(), ''
    # The spectrum doesn't have two peaks, so check the Gaussians, which the user can edit.
    Means = np.sort(AliphaticGaussians[:, 0]) if len(AliphaticGaussians) > 0 else np.zeros(0)
    Means = Means[(Means >= Xmin) & (Means <= Xmax)]
    Range = f'{Xmin:.1f} to {Xmax:.1f} cm^-1'
    def Show(Values):
        return f'{len(Values)}' + (f" ({', '.join(f'{Value:.1f}' for Value in Values)})" if len(Values) > 0 else '')
    if len(Means) < 2:
        raise Exception(f'Two Aliphatic peaks are needed in the range of {Range}, in either the measured spectrum or the '
                        f'fitted Gaussians, but neither of them has two.\n'
                        f'    Peaks of the measured spectrum in this range: {Show(XPeak)}\n'
                        f'    The two biggest Aliphatic Gaussians (used for the Aliphatic area) in this range: {Show(Means)}\n\n'
                        f'Editing the Gaussians does not change the peaks of the spectrum, but two Gaussians in this range '
                        f'are enough for saving. You can edit the Gaussians, or change the Aliphatic range.')
    # Keep the peak which was found in the spectrum, in the place of the Gaussian that it is closest to.
    Locations, Values = [None, None], [None, None]
    for Location, Value in zip(XPeak, YPeak):
        Place = int(np.argmin(np.abs(Means[:2] - Location)))
        Locations[Place], Values[Place] = float(Location), float(Value)
    Empty = [Name for Name, Location in zip(['first (lower wavenumber)', 'second'], Locations) if Location is None]
    Warning = (f'This record was saved, but please note:\n\n'
               f'The measured spectrum has fewer than two Aliphatic peaks in the range of {Range}. It has {Show(XPeak)}.\n\n'
               f'However, the two biggest fitted Aliphatic Gaussians (used for the Aliphatic area) satisfy this range: {Show(Means)}.\n\n'
               f'So, the Aliphatic peak values are only saved for the peaks found in the spectrum. The '
               f'{" and ".join(Empty)} Aliphatic peak location and absorbance are empty in the database.')
    return Locations, Values, Warning
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Find_Peaks(Data, Range, Prominence=0.001):
    """
    This function finds the peak in a specific range. This would be of a great importance in finding the peaks for 
    Carbonyl, Sulfoxide, and Aliphatic functional groups. 

    :param Data: 2D Array where the first column are the wavelengths (1/cm) and the second column are the absorbance 
    intesity (Baseline adjusted and normalized).
    :param Range: A list of minimum and maximum range of wavenumber of interest for each functional group (1/cm).
    :return 
    """
    # Limiting the data.
    Index = np.where((Data[:, 0] >= Range[0] - 100) &
                     (Data[:, 0] <= Range[1] + 100))[0]
    X = Data[Index, 0]
    Y = Data[Index, 1]
    # Finding the peaks in the data.
    PeakIndices, PeakProperties = find_peaks(
        Y, height=0, prominence=Prominence, wlen=200)
    # Filter the peaks in the range of interest.
    XPeakInRange, YPeakInRange, ProminencesInRange, XLeftBoundInRange, XRightBoundInRange = [], [], [], [], []
    for i in range(len(PeakIndices)):
        if Range[0] <= X[PeakIndices[i]] <= Range[1]:
            XPeakInRange.append(X[PeakIndices[i]])
            YPeakInRange.append(Y[PeakIndices[i]])
            ProminencesInRange.append(PeakProperties['prominences'][i])
            XLeftBoundInRange.append(X[PeakProperties['left_bases'][i]])
            XRightBoundInRange.append(X[PeakProperties['right_bases'][i]])
    # Return the results.
    return XPeakInRange, YPeakInRange, ProminencesInRange, XLeftBoundInRange, XRightBoundInRange
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Array_to_Binary(Arr):
    """
    This function converts a np.ndarray to binary bytes, so that it could be stored in SQL table. 

    :param Arr: Input numpy array.
    :return: three variable, including (i) serialized array in binary bytes, (ii) array shape as string, and (iii) 
    array type as string.
    """
    return Arr.tobytes(), str(Arr.shape), str(Arr.dtype)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Binary_to_Array(BinaryArr, StrShape, StrDtype):
    """
    This function converts the binary bytes into a np.ndarray. This is the reverse function for the "Array_to_Binary".

    :param BinaryArr: Serialized binary bytes of the array.
    :param StrShape: Shape of the array as string. 
    :param StrDtype: type of the data in array as string.
    """
    Shape = ast.literal_eval(StrShape)
    # Shape = int(StrShape[1:-1].split(',')[0])
    return np.frombuffer(BinaryArr, dtype=StrDtype).reshape(Shape)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


