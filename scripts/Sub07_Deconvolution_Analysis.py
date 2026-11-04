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
from scipy.optimize import curve_fit, root_scalar, least_squares
from scipy.interpolate import interp1d


def Run_Deconvolution(X, Y, GlobalRefit=False, MinPeakHeight=0.004, MaxIterations=200):
    """
    This is the main function to perform the deconvolution of the FTIR result spectrum. For this purpose, the code will
    try to fit Gaussian functions to highest peak of the spectrum, and continue this process after subtracting the
    fitted Gaussian from the spectrum. This process will continue as possible. Finally, to account for the Original
    asphalt binders with almost negligible peaks, the code will try to find the peaks in the range of 1600 to 1800,
    even if it might capture the noise. Optionally, all the fitted Gaussians are then refined simultaneously (global
    refit), so that the errors of the early (frozen) Gaussians do not propagate into the later ones. Next, the code
    will calculate the corresponding indices and areas. It will then return detailed results as a dictionary.
    It is recoemmended that the input is baseline adjusted and normalized to 0.15 for the wavenumbers in the range of
    600 to 2000 (1/cm). Therefore, the algorithm will ignore any peak less than 0.004 (except for search in Carbonyl
    area, which goes down to 0.0015).

    :param X: An array of the sorted wavenumbers (1/cm).
    :param Y: An array of the absorbance values.
    :param GlobalRefit: If True, refine all the Gaussians simultaneously after the peak-by-peak fitting, defaults to
    False. Note: the refit improves the overall fit, but it may move the Gaussians across the boundaries of the
    Carbonyl/Sulfoxide/Aliphatic ranges, which made the indices less repeatable for some datasets (e.g., PTF5).
    :param MinPeakHeight: Peaks smaller than this value are ignored in the general search, defaults to 0.004 (the
    Sulfoxide peak of some Original binders is smaller than 0.008).
    :param MaxIterations: Safety limit for the number of peak-by-peak iterations in each search, defaults to 200.
    :return: A dictionary of detailed results, including a list of fitted Gaussians, ICO and ISO indices, etc.
    """
    # First of all, take an slice of the data, with wavenumbers between 550 to 2000.
    Index = np.where((X >= 550) & (X <= 2000))[0]
    X = X[Index]
    Y = Y[Index]
    # ------------------------------------------------------------------------------------------------------------------
    # Define the required variables.
    Gaussian_List = []
    Yvalues = Y.copy()
    General_Xmin, General_Xmax = 600, 2000
    GeneralRange  = (X > General_Xmin) & (X < General_Xmax)
    CarbonylRange = (X > 1600) & (X < 1800)
    Eligible = np.ones(len(X), dtype=bool)      # Points that still can be selected as a peak (rejected ones are False).
    # ------------------------------------------------------------------------------------------------------------------
    # Start the algorithm for deconvolution: fit Gaussians to the peaks, from the biggest one, until all the remaining
    #   peaks are smaller than the threshold.
    for Iteration in range(MaxIterations):
        Candidates = GeneralRange & Eligible
        if (not Candidates.any()) or (Yvalues[Candidates].max() < MinPeakHeight):
            break
        Gaussian_List, Yvalues, Eligible = Fit_Gaussian_to_Biggest_Peak(X, Yvalues, Gaussian_List, Eligible,
                                                                         General_Xmin, General_Xmax)
    # Then, perform the search on the carbonyl area (for the Original binders with almost negligible peaks).
    for Iteration in range(MaxIterations):
        Candidates = CarbonylRange & Eligible
        if (not Candidates.any()) or (Yvalues[Candidates].max() < 0.0015):
            break
        Gaussian_List, Yvalues, Eligible = Fit_Gaussian_to_Biggest_Peak(X, Yvalues, Gaussian_List, Eligible, 1600, 1800)
    # ------------------------------------------------------------------------------------------------------------------
    # Refine all the Gaussians simultaneously.
    if GlobalRefit and len(Gaussian_List) > 0:
        Gaussian_List = Global_Refit_Gaussians(X, Y, Gaussian_List, General_Xmin, General_Xmax)
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


def Fit_Gaussian_to_Biggest_Peak(X, Y, Gaussians, Eligible, Xmin, Xmax, MuTolerance=3, SigmaBounds=(1, 60),
                                 MaxSideRatio=3):
    """
    This function will first find the highest peak in the specified interval and then tries to fit a Gaussian to the
    data. A peak is rejected (and its surrounding points are excluded from the future peak searches) if it is the
    shoulder left behind after subtracting a narrower Gaussian from a neighboring peak, i.e., it is not supported by the
    data on the side of that neighbor. Fitting such one-sided data results in an artificial wide Gaussian with a
    shifted center.

    :param X: An array of Wavenumbers (1/cm).
    :param Y: An array of Absorptions (updated with deconvoluted results so far).
    :param Gaussians: A list of all fitted Gaussians.
    :param Eligible: A boolean array (same size as X), where True means the point still can be selected as a peak.
    :param Xmin: Minimum wavenumber to be considered.
    :param Xmax: Maximum wavenumber to be considered.
    :param MuTolerance: Maximum allowed shift of the Gaussian center from the peak location (1/cm), defaults to 3.
    :param SigmaBounds: Lower and upper bounds of the Gaussian standard deviation (1/cm), defaults to (1, 60).
    :param MaxSideRatio: Maximum allowed ratio between the number of datapoints at the two sides of the peak, when the
    short side is next to a previously fitted Gaussian, defaults to 3.
    :return: The updated list of Gaussians with the new fit, the updated "Y" array after subtracting the fitted
    Gaussian (unchanged if the peak was rejected), and the updated "Eligible" array.
    """
    # First, get a copy of the original data.
    Xcopy = X.copy()
    Ycopy = Y.copy()
    Eligible = Eligible.copy()
    # Apply the specified interval.
    ValidIndex = np.where((X > Xmin) & (X < Xmax))[0]
    X = X[ValidIndex]
    Y = Y[ValidIndex]
    # Find the highest peak in the data (only among the eligible points).
    Candidates = np.where(Eligible[ValidIndex])[0]
    PeakIndex = Candidates[np.argmax(Y[Candidates])]
    Xpeak = X[PeakIndex]
    Ypeak = Y[PeakIndex]
    # Try to find data points around the peak using moving average with window size of 3. If the data keeps falling
    #   up to the end of the interval, the window is extended to the end of the interval.
    window = np.ones(3) / 3
    IndexLeft, IndexRight = 0, len(Y)
    if len(Y) - PeakIndex >= 4:
        dYmRight = np.diff(np.convolve(Y[PeakIndex:], window, mode='valid'))
        if (dYmRight >= 0).any():
            IndexRight = PeakIndex + np.where(dYmRight >= 0)[0][0] + 1
    if PeakIndex >= 4:
        dYmLeft = np.diff(np.convolve(Y[:PeakIndex], window, mode='valid'))
        if (dYmLeft <= 0).any():
            IndexLeft = np.where(dYmLeft <= 0)[0][-1]
    WindowIndex = ValidIndex[IndexLeft:IndexRight]          # Window indices in the original (full) arrays.
    XX = X[IndexLeft:IndexRight]
    YY = Y[IndexLeft:IndexRight]
    # Use data up to 60% of the peak (to increase the accuracy of the gaussian fit to the peak).
    Index = np.where(YY > 0.6 * Ypeak)[0]
    XX = XX[Index]
    YY = YY[Index]
    # Check the number of datapoint at the right and left hand sides.
    IndexLeft = np.where(XX < Xpeak)[0]
    IndexRight= np.where(XX > Xpeak)[0]
    # If the data is mainly one-sided and the short side is within the footprint (3 sigma) of a previously fitted
    #   Gaussian, it is not a true peak, but the shoulder left behind after subtracting that Gaussian. So, reject it and
    #   exclude its window from the future peak searches. Note that some true peaks are naturally asymmetric (e.g.,
    #   Sulfoxide), so the one-sided data alone is not a reason for rejection.
    if max(len(IndexLeft), len(IndexRight)) > MaxSideRatio * max(min(len(IndexLeft), len(IndexRight)), 1):
        ShortSide = 1 if len(IndexRight) < len(IndexLeft) else -1
        for Gaussian in Gaussians:
            if 0 < ShortSide * (Gaussian[0] - Xpeak) < 3 * np.abs(Gaussian[1]):
                Eligible[WindowIndex] = False
                return Gaussians, Ycopy, Eligible
    # If the number of datapoints at either sides are not matching, the result might only fit to the side with more
    #   datapoints, while ignoring the other side (not applicable when one side is empty, i.e., very narrow peaks).
    if (np.abs(len(IndexRight) - len(IndexLeft)) < 2) or (min(len(IndexLeft), len(IndexRight)) == 0):
        pass
    elif len(IndexLeft) < len(IndexRight):
        Xdense = np.linspace(XX[IndexLeft].min(), XX[IndexLeft].max(), len(IndexRight))
        Ydense = np.interp(Xdense, XX[IndexLeft], YY[IndexLeft])
        XX = np.hstack((Xdense, Xpeak, XX[IndexRight]))
        YY = np.hstack((Ydense, Ypeak, YY[IndexRight]))
    elif len(IndexRight) < len(IndexLeft):
        Xdense = np.linspace(XX[IndexRight].min(), XX[IndexRight].max(), len(IndexLeft))
        Ydense = np.interp(Xdense, XX[IndexRight], YY[IndexRight])
        XX = np.hstack((XX[IndexLeft], Xpeak, Xdense))
        YY = np.hstack((YY[IndexLeft], Ypeak, Ydense))
    # Fitting Gaussian, but with fixed amplitude. The center is bounded to stay close to the peak (with a fixed amplitude,
    #   a shifted center means the Gaussian no longer represents the peak), and the width is bounded too.
    Amplitude = Ypeak
    Bounds = ([Xpeak - MuTolerance, SigmaBounds[0]], [Xpeak + MuTolerance, SigmaBounds[1]])
    initial_guess = [Xpeak, np.clip(XX[-1] - XX[0], SigmaBounds[0] * 1.01, SigmaBounds[1] * 0.99)]
    NewFunc = lambda X, mu, sigma: gaussian_bell(X, mu, sigma, Amplitude)
    try:
        # Note: the weights are scaled by the peak value (same solution as "sigma=1/YY"); otherwise, the residuals are
        #   so small that the bounded solver ("trf") stops at the initial guess due to its gradient tolerance.
        params, _ = curve_fit(NewFunc, XX, YY, p0=initial_guess, sigma=Ypeak/YY, bounds=Bounds)
    except (RuntimeError, ValueError):
        # The fit didn't converge, so reject this peak and exclude its window from the future peak searches.
        Eligible[WindowIndex] = False
        return Gaussians, Ycopy, Eligible
    Mu, Sigma = params
    # Calculating the absorption from the fitted Gaussian function and define the new absorption values. The negative
    #   values are kept, so the over-subtraction is not hidden from the next fits.
    YG = gaussian_bell(Xcopy, Mu, Sigma, Amplitude)
    NewY = Ycopy - YG
    # Make sure that the peak cannot be selected again if the fit could not reduce it significantly.
    if NewY[ValidIndex[PeakIndex]] > 0.5 * Amplitude:
        Eligible[ValidIndex[PeakIndex]] = False
    # Add the fitted Gaussian to the list.
    Gaussians.append([Mu, Sigma, Amplitude])
    # # Plotting section. 
    # plt.figure()
    # plt.plot(Xcopy, Ycopy, ls='--', lw=0.5)
    # plt.plot(Xcopy, NewY, ls='--', lw=0.5)
    # plt.plot(XX, YY, ls='', marker='x', ms=4)
    # plt.plot(Xcopy, YG, ls='-', lw=1, color='r')
    # Return the results.
    return Gaussians, NewY, Eligible
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


def Global_Refit_Gaussians(X, Y, Gaussians, Xmin, Xmax, MuTolerance=2, SigmaBounds=(1, 60), MaxSigmaRatio=1.5,
                           MaxAmplitudeRatio=1.3):
    """
    This function refines all the Gaussians simultaneously using a bounded least squares fit to the spectrum. In the
    peak-by-peak fitting, each Gaussian is fixed after it is fitted, so its error (e.g., a too narrow Gaussian for a
    peak with broad base) remains in the residual and affects all the next fits. The global refit corrects these
    errors. The bounds keep each Gaussian close to its initial values (from the peak-by-peak fitting), so the Gaussians
    keep their identity (location) during the refit.

    :param X: An array of Wavenumbers (1/cm).
    :param Y: An array of the absorbance values (the original spectrum, not the residual).
    :param Gaussians: A list of all fitted Gaussians (each one as [Mu, Sigma, Amplitude]), used as the initial values.
    :param Xmin: Minimum wavenumber to be considered in the fit.
    :param Xmax: Maximum wavenumber to be considered in the fit.
    :param MuTolerance: Maximum allowed shift of each Gaussian center (1/cm), defaults to 2.
    :param SigmaBounds: Lower and upper bounds of the Gaussian standard deviation (1/cm), defaults to (1, 60).
    :param MaxSigmaRatio: Maximum allowed change of each Gaussian standard deviation, as a ratio of (or to) its initial
    value, defaults to 1.5.
    :param MaxAmplitudeRatio: Maximum allowed amplitude, as a ratio of the initial amplitude, defaults to 1.3.
    :return: The refined list of Gaussians as a 2D array (Gaussians vanished during the refit are removed). In case
    the refit fails, the initial Gaussians are returned.
    """
    # Apply the specified interval.
    Index = np.where((X >= Xmin) & (X <= Xmax))[0]
    x = X[Index]
    y = Y[Index]
    # Define the initial values and bounds; each row is [Mu, Sigma, Amplitude].
    G = np.array(Gaussians, dtype=float)
    G[:, 1] = np.abs(G[:, 1])
    N = G.shape[0]
    SigmaLower = np.maximum(G[:, 1] / MaxSigmaRatio, SigmaBounds[0])
    SigmaUpper = np.minimum(G[:, 1] * MaxSigmaRatio, SigmaBounds[1])
    Lower = np.column_stack((G[:, 0] - MuTolerance, SigmaLower, np.zeros(N)))
    Upper = np.column_stack((G[:, 0] + MuTolerance, SigmaUpper, MaxAmplitudeRatio * G[:, 2] + 2e-3))
    P0 = np.clip(G, Lower + 1e-6, Upper - 1e-6)
    # Define the residual function and its Jacobian (analytical, for speed).
    Scale = np.abs(y).max()                 # Scaling (same solution), so the solver tolerances are not reached early.
    def Residual(P):
        P = P.reshape(N, 3)
        return (gaussian_bell(x[None, :], P[:, [0]], P[:, [1]], P[:, [2]]).sum(axis=0) - y) / Scale
    def Jacobian(P):
        P = P.reshape(N, 3)
        Z = (x[None, :] - P[:, [0]]) / P[:, [1]]
        E = np.exp(-0.5 * Z ** 2)
        J = np.empty((len(x), N, 3))
        J[:, :, 0] = (P[:, [2]] * E * Z / P[:, [1]]).T            # d/dMu
        J[:, :, 1] = (P[:, [2]] * E * Z ** 2 / P[:, [1]]).T       # d/dSigma
        J[:, :, 2] = E.T                                            # d/dAmplitude
        return J.reshape(len(x), 3 * N) / Scale
    # Perform the fit.
    try:
        Res = least_squares(Residual, P0.ravel(), jac=Jacobian, bounds=(Lower.ravel(), Upper.ravel()), x_scale='jac',
                            max_nfev=1000)      # Usually converges in ~300 evaluations; the limit avoids long runs.
    except (ValueError, np.linalg.LinAlgError):
        return G
    G = Res.x.reshape(N, 3)
    # Return the results (removing the vanished Gaussians).
    return G[G[:, 2] > 1e-6, :]
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
    try: 
        a = amplitude * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    except:
        print(mu, sigma, amplitude)
    return amplitude * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
