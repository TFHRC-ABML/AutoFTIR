# Title: This script include the codes and algorithms for the deconvolution method. 
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 12/20/2024
# ======================================================================================================================

# Importing the required libraries.
import os
import sys
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


def Run_Deconvolution(X, Y):
    """
    This is the main function to perform the deconvolution of the FTIR result spectrum. For this purpose, the code will 
    try to fit Gaussian functions to highest peak of the spectrum, and continue this process after subtracting the 
    fitted Gaussian from the spectrum. This process will continue as possible. Finally, to account for the Original 
    asphalt binders with almost negligible peaks, the code will try to find the peaks in the range of 1600 to 1800, 
    even if it might capture the noise. Next, the code will calculate the corresponding indices and areas. It will then 
    return detailed results as a dictionary. 
    It is recoemmended that the input is baseline adjusted and normalized to 0.15 for the wavenumbers in the range of 
    600 to 2000 (1/cm). Therefore, the algorithm will ignore any peak less than 0.008 (except for search in Carbonyl 
    area).

    :param X: An array of the sorted wavenumbers (1/cm). 
    :param Y: An array of the absorbance values.
    :return: A dictionary of detailed results, including a list of fitted Gaussians, ICO and ISO indices, etc. 
    """
    # First of all, take an slice of the data, with wavenumbers between 550 to 2000.
    Index = np.where((X >= 550) & (X <= 2000))[0]
    X = X[Index]
    Y = Y[Index]
    # ------------------------------------------------------------------------------------------------------------------
    # Define the required variables. 
    Gaussian_List = []
    Xvalues = X
    Yvalues = Y
    MaxPeakFlag, CarbonylAreaSearchFlag = False, False
    General_Xmin, General_Xmax = 600, 2000
    CIndex  = np.where((X >= 1600) & (X <= 1800))[0]
    # ------------------------------------------------------------------------------------------------------------------
    # Start the algorithm for deconvolution. 
    while True:
        # First, check for the maximum peak value. 
        GeneralRange = np.where((X >= General_Xmin) & (X <= General_Xmax))[0]
        if Yvalues[GeneralRange].max() < 0.008:
            MaxPeakFlag = True
        # Check if the Carbonyl area was searched to break the loop. 
        if MaxPeakFlag and CarbonylAreaSearchFlag:
            break
        # Otherwise, continue fitting Gaussian to the peaks. 
        try:
            Gaussian_List, Yvalues = Fit_Gaussian_to_Biggest_Peak(Xvalues, Yvalues, Gaussian_List, 
                                                                  General_Xmin, General_Xmax)
        except:
            # In case of error, perform the search on the carbonyl area. 
            while True:
                if Yvalues[CIndex].max() < 0.0015:
                    break
                try:
                    Gaussian_List, Yvalues = Fit_Gaussian_to_Biggest_Peak(Xvalues, Yvalues, Gaussian_List, 1600, 1800)
                except:
                    break
            CarbonylAreaSearchFlag = True
            General_Xmin += 20
            General_Xmax -= 20
    # ------------------------------------------------------------------------------------------------------------------
    # Convert the Gaussian results into an array and sort them. 
    Gaussian_List = np.array(Gaussian_List)
    Gaussian_List = Gaussian_List[Gaussian_List[:, 0].argsort(), :]         # Sort based on wavenumber (report purpose).
    # ------------------------------------------------------------------------------------------------------------------
    # Calculate the Aliphatic area: it only include the two main peaks between 1350 to 1525 (1/cm). Usually, we're 
    #   expecting them around 1375 and 1450 1/cm. 
    Aliphatic_Gaussians = Gaussian_List[(Gaussian_List[:, 0] < 1525) & (Gaussian_List[:, 0] > 1350), :]
    Aliphatic_Gaussians = Aliphatic_Gaussians[Aliphatic_Gaussians[:, 2].argsort(), :]       # Sort based on Amplitude.
    Aliphatic_Gaussians = Aliphatic_Gaussians[-2:, :]       # Took only the biggest peaks. 
    Aliphatic_Area = (Aliphatic_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Aliphatic_Gaussians[:, 1])).sum()
    # ------------------------------------------------------------------------------------------------------------------
    # Calculate the Carbonyl area: it is calculated using the peaks in the range of 1660 to 1720 1/cm.
    Carbonyl_Gaussians = Gaussian_List[(Gaussian_List[:, 0] < 1720) & (Gaussian_List[:, 0] > 1660), :]
    Carbonyl_Area = (Carbonyl_Gaussians[:, 2] * np.sqrt(2 * np.pi) * np.abs(Carbonyl_Gaussians[:, 1])).sum()
    # ------------------------------------------------------------------------------------------------------------------
    # Calculate the Sulfoxide area: it is calculated using one peak in the range of 970 to 1070 1/cm, which is the 
    #   closest to 1030 1/cm.
    Sulfoxide_Gaussian = Gaussian_List[(Gaussian_List[:, 0] < 1070) & (Gaussian_List[:, 0] > 970), :]
    Index = np.argmin(np.abs(Sulfoxide_Gaussian[:, 0] - 1030))
    Index2= np.argmax(Sulfoxide_Gaussian[:, 2])
    # if Index != Index2:
    #     print(f"Indices are not the same: closest: {Sulfoxide_Gaussian[Index, 0]:.2f}, " +
    #           f"Highest peak at: {Sulfoxide_Gaussian[Index2, 0]:.2f}, " + 
    #           f"Values: {Sulfoxide_Gaussian[Index, 2]:.4f}, {Sulfoxide_Gaussian[Index2, 2]:.4f}")
    Sulfoxide_Area = Sulfoxide_Gaussian[Index2, 2] * np.sqrt(2 * np.pi) * np.abs(Sulfoxide_Gaussian[Index2, 1])
    # ------------------------------------------------------------------------------------------------------------------
    # Calculating the ICO and ISO indices. 
    ICO = Carbonyl_Area  / Aliphatic_Area
    ISO = Sulfoxide_Area / Aliphatic_Area
    # ------------------------------------------------------------------------------------------------------------------
    # Prepare the results for returning. 
    Res = {'Gaussian_List'      : Gaussian_List, 
           'Carbonyl_Gaussians' : Carbonyl_Gaussians,
           'Sulfoxide_Gaussians': Sulfoxide_Gaussian[[Index2], :],
           'Aliphatic_Gaussians': Aliphatic_Gaussians,
           'Carbonyl_Area'      : Carbonyl_Area, 
           'Sulfoxide_Area'     : Sulfoxide_Area, 
           'Aliphatic_Area'     : Aliphatic_Area,
           'ISO'                : ISO, 
           'ICO'                : ICO}
    # Return the results. 
    return Res
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Fit_Gaussian_to_Biggest_Peak(X, Y, Gaussians, Xmin=None, Xmax=None):
    """
    This function will first find the highest peak in the specified interval and then tries to fit a Gaussian to the 
    data.

    :param X: An array of Wavenumbers (1/cm).
    :param Y: An array of Absorptions (updated with deconvoluted results so far).
    :param Gaussians: A list of all fitted Gaussians. 
    :param Xmin: Minimum wavenumber to be considered, defaults to None
    :param Xmax: Maximum wavenumber to be considered, defaults to None
    :return: The updated list of Gaussians with the new fit, and the updated "Y" array after subtracting the fitted 
    Gaussian.
    """
    # First, get a copy of the original data.
    Xcopy = X.copy()
    Ycopy = Y.copy()
    # Apply the specified interval.
    if Xmin != None:
        ValidIndex = np.where((X > Xmin) & (X < Xmax))[0]
        X = X[ValidIndex]
        Y = Y[ValidIndex]
    # Find the highest peak in the data. 
    PeakIndex = np.argmax(Y)
    Xpeak = X[PeakIndex]
    Ypeak = Y[PeakIndex]
    # Try to find data points around the peak using moving average with window size of 3. 
    window = np.ones(3) / 3
    YmRight = np.convolve(Y[PeakIndex:], window, mode='valid')
    YmLeft  = np.convolve(Y[:PeakIndex], window, mode='valid')
    XmRight = X[PeakIndex+1:-1]
    XmLeft  = X[1:PeakIndex-1]
    dYmRight = np.diff(YmRight)
    dYmLeft  = np.diff(YmLeft)
    IndexRight = PeakIndex + np.where(dYmRight >= 0)[0][0] + 1
    IndexLeft  = np.where(dYmLeft  <= 0)[0][-1]
    XX = X[IndexLeft:IndexRight]
    YY = Y[IndexLeft:IndexRight]
    # Use data up to 60% of the peak (to increase the accuracy of the gaussian fit to the peak).
    Index = np.where(YY > 0.6 * YY.max())[0]
    XX = XX[Index]
    YY = YY[Index]
    # Check the number of datapoint at the right and left hand sides. If the number of datapoints at either sides are 
    # not matching, the result might only fit to the side with more datapoints, while ignoring the other side. 
    IndexLeft = np.where(XX < XX[np.argmax(YY)])[0]
    IndexRight= np.where(XX > XX[np.argmax(YY)])[0]
    if np.abs(len(IndexRight) - len(IndexLeft)) < 2:
        pass
    elif len(IndexLeft) < len(IndexRight):
        Xdense = np.linspace(XX[IndexLeft].min(), XX[IndexLeft].max(), len(IndexRight))
        Ydense = np.interp(Xdense, XX[IndexLeft], YY[IndexLeft])
        XX = np.hstack((Xdense, XX[np.argmax(YY)], XX[IndexRight]))
        YY = np.hstack((Ydense, YY[np.argmax(YY)], YY[IndexRight]))
    elif len(IndexRight) < len(IndexLeft):
        Xdense = np.linspace(XX[IndexRight].min(), XX[IndexRight].max(), len(IndexLeft))
        Ydense = np.interp(Xdense, XX[IndexRight], YY[IndexRight])
        XX = np.hstack((XX[IndexLeft], XX[np.argmax(YY)], Xdense))
        YY = np.hstack((YY[IndexLeft], YY[np.argmax(YY)], Ydense))
    # Fitting Gaussian, but with fixed amplitude. 
    initial_guess = [X[PeakIndex], XX[-1] - XX[0]]
    Amplitude = Y[PeakIndex]
    NewFunc = lambda X, mu, sigma: gaussian_bell(X, mu, sigma, Amplitude)
    for trial in range(3):
        params, _ = curve_fit(NewFunc, XX, YY, p0=initial_guess, sigma=1/YY)
        Mu, Sigma = params
        # Check the results.
        if (Mu < 2100) and (Mu >= 400) and np.abs(Sigma) < 100:
            break
        if trial == 2:
            print("Three trials didn't work!")
            return Gaussians, Ycopy
        else:
            # try smaller initial guess, maybe converge!
            initial_guess[1] /= 2
    # Calculating the absorption from the fitted Gaussian function and define the new absorption values.
    YG = gaussian_bell(Xcopy, Mu, Sigma, Amplitude)
    NewY = Ycopy - YG
    NewY[NewY < 0] = 0          # For now, just ignoring the negative values! (Might need to subtract it from Area?!)
    # Add the fitted Gaussian to the list. 
    Gaussians.append([Mu, Sigma, Amplitude])
    # # Plotting section. 
    # plt.figure()
    # plt.plot(Xcopy, Ycopy, ls='--', lw=0.5)
    # plt.plot(Xcopy, NewY, ls='--', lw=0.5)
    # plt.plot(XX, YY, ls='', marker='x', ms=4)
    # plt.plot(Xcopy, YG, ls='-', lw=1, color='r')
    # Return the results. 
    return Gaussians, NewY
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def gaussian_bell(x, mu, sigma, amplitude):
    """
    Gaussian function for fitting.

    :param x: An array of Wavenumbers (1/cm).
    :param mu: Mean (center of the Gaussian function).
    :param sigma: Standard deviation (controls the width of the Gaussian function).
    :param amplitude: Peak hight of the Gaussian function. 
    :return: The calculated absorption values. 
    """
    return amplitude * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
