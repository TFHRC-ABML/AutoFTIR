# Title: This script include a class to design a page for plotting FTIR spectra of selected database records.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 09/23/2026
# ======================================================================================================================

# Importing the required libraries.
import os
import sys
import sqlite3
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QGroupBox, QHBoxLayout,
                             QVBoxLayout, QPushButton, QWidget, QMessageBox, QLabel, QFormLayout, QComboBox,
                             QFileDialog, QAbstractItemView, QSpinBox, QDoubleSpinBox, QColorDialog, QCheckBox,
                             QLineEdit, QInputDialog)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QSize, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font as ExcelFont
from scripts.Sub02_CreateNewSQLTable import Get_DB_SummaryData, Get_Identifier_Combinations
from scripts.Sub04_FTIR_Analysis_Functions import Binary_to_Array


class FTIR_PlotPage(QMainWindow):
    """
    This class designs a page for plotting the (processed) FTIR spectra of one or more selected database records
    on top of each other, so the user can visually compare records. The user filters/selects candidate records with
    the same B-number/Lab-Aging controls used elsewhere, picks one or more rows from the resulting table, and adds
    them to the plot explicitly via the "Plot Selected" button.
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
        # Fixed columns shown in the record-selection table (kept simple/non-configurable, unlike the Review page's
        #   tables, since this table exists only to let the user identify and select rows to plot).
        self.SQL_ColumnNames = ['id', 'Bnumber', 'Lab_Aging', 'RepNumber']
        self.ColumnNames = ['id', 'ID-number', 'Lab Aging', 'Rep #']
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
        # Tracks the records currently drawn on the plot: {id: {'line': Line2D, 'label': str, 'X': ndarray,
        #   'YBase': ndarray (unshifted by the comparison offset), 'LineStyle', 'LineWidth', 'Color'}}. Dict
        #   insertion order doubles as the stacking order used by the comparison offset.
        self.PlottedLines = {}
        # Counter for synthetic (negative, never colliding with a real DB "id") keys used for "Plot average of
        #   selected" entries in "self.PlottedLines" -- see "Function_Button_PlotSelected".
        self.NextAverageKey = -1
        # Named custom dash patterns beyond matplotlib's 4 standard styles, per the user's naming convention: a
        #   dash, then N dots, then repeat (matplotlib dash tuples are (offset, (on, off, on, off, ...)) in points).
        self.CustomLineStyles = {
            '-..-':   (0, (4, 1.5, 1, 1.5, 1, 1.5)),
            '-...-':  (0, (4, 1.5, 1, 1.5, 1, 1.5, 1, 1.5)),
            '-....-': (0, (4, 1.5, 1, 1.5, 1, 1.5, 1, 1.5, 1, 1.5)),
        }
        self.LegendLocations = ['best', 'upper right', 'upper left', 'lower left', 'lower right', 'right',
                                'center left', 'center right', 'lower center', 'upper center', 'center']
        # Preset X-axis crops for the "Plot region" control. Carbonyl/Sulfoxide/Aliphatic ranges match the zoomed
        #   sub-plots' "Xlims" used on the Add-Data/Revise pages (Sub03_MainPage.py/Sub06_FTIR_RevisePage.py).
        self.PlotRegions = {
            'Whole Spectrum (~4000-400)': [4000, 400],
            'Binder Region (~2000-600)': [2000, 600],
            'Carbonyl (~1780-1620)': [1780, 1620],
            'Sulfoxide (~1100-940)': [1100, 940],
            'Aliphatic (~1600-1300)': [1600, 1300],
        }
        # (label, xlim, color) for the "Highlight regions" checkbox's shaded axvspans, reusing "self.PlotRegions"'
        #   ranges (colors match the Carbonyl/Sulfoxide/Aliphatic fill_between colors on the Add-Data/Revise pages).
        self.HighlightRegionSpecs = [
            ('Carbonyl', self.PlotRegions['Carbonyl (~1780-1620)'], 'r', ''),
            ('Sulfoxide', self.PlotRegions['Sulfoxide (~1100-940)'], 'y', 'XX'),
            ('Aliphatic', self.PlotRegions['Aliphatic (~1600-1300)'], 'g', '\\\\'),
        ]
        # Currently-drawn highlight-region axvspan artists, and the two separate legend objects (plotted-lines
        #   legend vs. region-highlight legend) -- kept as explicit references since "Axes.get_legend()" only ever
        #   reports the most-recently-created one, not both, once a second legend is added via "add_artist".
        self.RegionHighlights = []
        self.MainLegend = None
        self.RegionLegend = None
        # Current legend settings, applied by "Update_Legend" (updated from the controls whenever "Refresh Plot" is
        #   clicked) so a legend redrawn afterward (e.g. after plotting another record) keeps using them.
        self.LegendFontSize = 12
        self.LegendLoc = 'best'
        self.LegendHandleLength = 2.0
        # Color pending in the "Line Properties" color-picker button, applied to the selected line on "Refresh Plot".
        self.PendingLineColor = None
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
            "Export": """
        QPushButton:enabled {
            background-color: #93E9BE; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: #56C28B; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:pressed {
            background-color: gray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        """,
            "Delete": """
        QPushButton:enabled {
            background-color: #FA8072; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:disabled {
            background-color: #dcdcdc; color: #808080;border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:hover {
            background-color: #CC5F55; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
        QPushButton:pressed {
            background-color: gray; color: #000; border: 1px solid #B0B0B0; border-radius: 8px; padding: 6px 12px;}
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
        """, }
        self.initUI()
    # ------------------------------------------------------------------------------------------------------------------
    def initUI(self):
        # Main widget and layout.
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)
        # Generate the left and right layouts, where the left one includes the summary info and the plot, and the
        #   right one includes the filtering options, record selection table, and operation controls.
        LeftLayout = QVBoxLayout()
        RightLayout = QVBoxLayout()
        # --------------------------------------------------------------------------------------------------------------
        # Section 1: summary information.
        SummaryData = Get_DB_SummaryData(self.cursor)
        Section01 = QGroupBox("Summary Information")
        Section01.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section01_Layout = QHBoxLayout()
        FormLayout_Left = QFormLayout()
        FormLayout_Right = QFormLayout()
        Label01 = QLabel("Number of data:")
        self.Label_NumData = QLabel(f'{SummaryData["NumRows"]}')
        Label02 = QLabel("Number of valid data:")
        self.Label_NumValidData = QLabel(f'{SummaryData["NumValidRows"]}')
        Label03 = QLabel("Avg Number Replicates:")
        self.Label_AvgNumReplicates = QLabel(f'{SummaryData["AvgNumRep"]:.1f}')
        Label04 = QLabel("Number of unique B-numbers:")
        self.Label_NumUniqueBnum = QLabel(f'{SummaryData["NumUniqueBnumber"]}')
        Label05 = QLabel("Number of unique Lab agings:")
        self.Label_NumUniqueLabAge = QLabel(f'{SummaryData["NumUniqueLabAging"]}')
        Label06 = QLabel("Number of Unique Bnum/LabAge:")
        self.Label_NumUniqueBnumLabAge = QLabel(f'{SummaryData["NumUniqueBnumLabAge"]}')
        self.Button_Sync = QPushButton("Refresh summay")
        self.Button_Sync.setFont(QFont("Arial", 8))
        self.Button_Sync.clicked.connect(self.Sync_Summary_Info)
        self.Button_Sync.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Sync.setSizePolicy(self.Button_Sync.sizePolicy().Expanding, self.Button_Sync.sizePolicy().Preferred)
        FormLayout_Left.addRow(Label01, self.Label_NumData)
        FormLayout_Left.addRow(Label02, self.Label_NumValidData)
        FormLayout_Left.addRow(Label03, self.Label_AvgNumReplicates)
        FormLayout_Right.addRow(Label04, self.Label_NumUniqueBnum)
        FormLayout_Right.addRow(Label05, self.Label_NumUniqueLabAge)
        FormLayout_Right.addRow(Label06, self.Label_NumUniqueBnumLabAge)
        Section01_Layout.addLayout(FormLayout_Left)
        Section01_Layout.addLayout(FormLayout_Right)
        Section01_Layout.addWidget(self.Button_Sync)
        Section01.setLayout(Section01_Layout)
        LeftLayout.addWidget(Section01, 8)
        # --------------------------------------------------------------------------------------------------------------
        # Section 2: the plot itself (single axes showing the whole spectrum). Built here, before the Visualization
        #   Properties section, so its natural (pre-distortion) box aspect ratio can be read and used to seed the
        #   "Aspect ratio" spinbox below; it is only added to "LeftLayout" after Section 1b (see below), to keep the
        #   visual stacking order Summary -> Visualization Properties -> Plot.
        Section02 = QGroupBox("Plot")
        Section02.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section02_Layout = QVBoxLayout()
        self.Label_NumPlotted = QLabel('Number of plotted records: 0')
        self.fig = Figure(figsize=(10, 7))
        self.fig.set_facecolor("#f0f0f0")
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.set_xlabel('Wavenumber (1/cm)', fontsize=12, fontweight='bold', color='k')
        self.ax.set_ylabel('Normalized Absorption', fontsize=12, fontweight='bold', color='k')
        self.ax.grid(which='both', color='gray', alpha=0.1)
        self.ax.set_xlim([2000, 600])
        self.ax.set_ylim([0, 1])
        # Comma-format the X tick labels (e.g. "1,800") via a formatter rather than fixed "set_xticks" +
        #   "set_xticklabels" calls: the latter locks in a FixedFormatter, which does not know how to format an
        #   arbitrary (non-tick) X value, breaking the toolbar's mouse coordinate readout, and freezes the tick
        #   positions themselves, so they stop updating when the user pans/zooms with the toolbar.
        self.ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{x:,.0f}'))
        # Custom status-bar coordinate readout for the toolbar (replaces the default "x=... y=...").
        self.ax.format_coord = lambda x, y: f'Wavenumber: {x:.2f} cm⁻¹; Absorption: {y:.3f}'
        self.fig.tight_layout()
        self.canvas.draw()
        # Provisional natural box aspect ratio (width:height), used only to seed the "Aspect ratio" spinbox below
        # before the page is actually shown on screen. "self.fig"'s inches size is still just the constructor's
        # figsize=(10, 7) at this point -- FigureCanvasQT.resizeEvent() only rescales it to match the widget's real
        # on-screen pixel size once the page is actually shown/laid out, so the *true* natural aspect can only be
        # read accurately after that first show (done once in "showEvent" via "self.Set_Initial_Aspect_Ratio").
        NaturalAspectRatio = self.fig.get_size_inches()[0] / self.fig.get_size_inches()[1]
        self.AspectRatioInitialized = False
        # Matplotlib's own navigation toolbar (pan/zoom/home/save, etc.), placed above the canvas.
        self.Toolbar = NavigationToolbar2QT(self.canvas, self)
        self.Toolbar.setIconSize(QSize(16, 16))
        # NavigationToolbar2 never records a baseline view on its own (its "home" is just wherever the nav stack
        #   happened to start): without this, the user's first zoom/pan would push the only stack entry, and
        #   clicking "Home" right after would do nothing. Push the initial view now so "Home" always means this.
        self.Toolbar.push_current()
        Section02_Layout.addWidget(self.Label_NumPlotted)
        Section02_Layout.addWidget(self.Toolbar)
        Section02_Layout.addWidget(self.canvas)
        Section02.setLayout(Section02_Layout)
        # --------------------------------------------------------------------------------------------------------------
        # Section 1b: visualization properties (legend/label, per-line, and plot-wide controls), applied via
        #   "Refresh Plot". One full-width row per group (an inline bold label followed by its controls), stacked
        #   vertically, rather than the three groups side by side.
        Section01b = QGroupBox("Visualization Properties")
        Section01b.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section01b_Layout = QVBoxLayout()
        # --- Legend and label properties -----------------------------------------------------------------------
        LegendRow_Layout = QHBoxLayout()
        LegendRow_Layout.addWidget(QLabel("<b>Legend and Label Properties:</b>"))
        self.Spin_LegendFontSize = QSpinBox()
        self.Spin_LegendFontSize.setRange(4, 24)
        self.Spin_LegendFontSize.setValue(self.LegendFontSize)
        self.Spin_LegendFontSize.setMaximumWidth(55)
        self.Combo_LegendLoc = QComboBox()
        self.Combo_LegendLoc.addItems(self.LegendLocations)
        self.Combo_LegendLoc.setCurrentText(self.LegendLoc)
        self.Spin_LegendHandleLength = QDoubleSpinBox()
        self.Spin_LegendHandleLength.setRange(1.0, 8.0)
        self.Spin_LegendHandleLength.setSingleStep(0.5)
        self.Spin_LegendHandleLength.setValue(self.LegendHandleLength)
        self.Spin_LegendHandleLength.setMaximumWidth(60)
        self.Spin_XLabelSize = QSpinBox()
        self.Spin_XLabelSize.setRange(4, 24)
        self.Spin_XLabelSize.setValue(12)
        self.Spin_XLabelSize.setMaximumWidth(55)
        self.Spin_YLabelSize = QSpinBox()
        self.Spin_YLabelSize.setRange(4, 24)
        self.Spin_YLabelSize.setValue(12)
        self.Spin_YLabelSize.setMaximumWidth(55)
        LegendRow_Layout.addWidget(QLabel("Font size:"))
        LegendRow_Layout.addWidget(self.Spin_LegendFontSize)
        LegendRow_Layout.addWidget(QLabel("Location:"))
        LegendRow_Layout.addWidget(self.Combo_LegendLoc)
        LegendRow_Layout.addWidget(QLabel("Handle length:"))
        LegendRow_Layout.addWidget(self.Spin_LegendHandleLength)
        LegendRow_Layout.addWidget(QLabel("X label size:"))
        LegendRow_Layout.addWidget(self.Spin_XLabelSize)
        LegendRow_Layout.addWidget(QLabel("Y label size:"))
        LegendRow_Layout.addWidget(self.Spin_YLabelSize)
        LegendRow_Layout.addStretch()
        Section01b_Layout.addLayout(LegendRow_Layout)
        # --- Line properties -----------------------------------------------------------------------------------
        LineRow_Layout = QHBoxLayout()
        LineRow_Layout.addWidget(QLabel("<b>Line Properties:</b>"))
        self.Combo_SelectLine = QComboBox()
        self.Combo_SelectLine.setMinimumWidth(120)
        self.Combo_SelectLine.currentIndexChanged.connect(self.Sync_Line_Property_Widgets)
        self.Combo_LineStyle = QComboBox()
        for Style in ['-', '--', '-.', ':']:
            self.Combo_LineStyle.addItem(Style, Style)
        for Name, Dashes in self.CustomLineStyles.items():
            self.Combo_LineStyle.addItem(Name, Dashes)
        self.Spin_LineWidth = QDoubleSpinBox()
        self.Spin_LineWidth.setRange(0.5, 4.0)
        self.Spin_LineWidth.setSingleStep(0.1)
        self.Spin_LineWidth.setValue(1.2)
        self.Spin_LineWidth.setMaximumWidth(60)
        self.Button_LineColor = QPushButton("Color...")
        self.Button_LineColor.clicked.connect(self.Function_Button_PickLineColor)
        LineRow_Layout.addWidget(self.Combo_SelectLine)
        LineRow_Layout.addWidget(QLabel("Style:"))
        LineRow_Layout.addWidget(self.Combo_LineStyle)
        LineRow_Layout.addWidget(QLabel("Width:"))
        LineRow_Layout.addWidget(self.Spin_LineWidth)
        LineRow_Layout.addWidget(self.Button_LineColor)
        self.LineEdit_LineLabel = QLineEdit()
        self.LineEdit_LineLabel.setPlaceholderText("Legend label...")
        self.LineEdit_LineLabel.setMinimumWidth(160)
        LineRow_Layout.addWidget(QLabel("Label:"))
        LineRow_Layout.addWidget(self.LineEdit_LineLabel)
        # Y-value scaling: multiplies this line's Absorption values, handy for overlaying a fingerprint region
        #   plot on top of a binder spectrum at a comparable visual scale.
        self.Spin_YScale = QDoubleSpinBox()
        self.Spin_YScale.setRange(0.01, 10.0)
        self.Spin_YScale.setSingleStep(0.1)
        self.Spin_YScale.setDecimals(2)
        self.Spin_YScale.setValue(1.0)
        self.Spin_YScale.setMaximumWidth(65)
        LineRow_Layout.addWidget(QLabel("Y-scale:"))
        LineRow_Layout.addWidget(self.Spin_YScale)
        LineRow_Layout.addStretch()
        Section01b_Layout.addLayout(LineRow_Layout)
        # --- Plot properties -----------------------------------------------------------------------------------
        PlotRow_Layout = QHBoxLayout()
        PlotRow_Layout.addWidget(QLabel("<b>Plot Properties:</b>"))
        self.Combo_DataType = QComboBox()
        self.Combo_DataType.addItems(['Processed', 'Raw'])
        self.Combo_DataType.setMinimumWidth(90)
        self.Combo_PlotRegion = QComboBox()
        for Name, XLim in self.PlotRegions.items():
            self.Combo_PlotRegion.addItem(Name, XLim)
        self.Combo_PlotRegion.setCurrentText('Binder Region (~2000-600)')
        self.Combo_PlotRegion.setMinimumWidth(210)
        self.Spin_Offset = QDoubleSpinBox()
        self.Spin_Offset.setRange(0.0, 0.2)
        self.Spin_Offset.setSingleStep(0.005)
        self.Spin_Offset.setDecimals(3)
        self.Spin_Offset.setValue(0.0)
        self.Spin_Offset.setMaximumWidth(65)
        self.Spin_AspectRatio = QDoubleSpinBox()
        self.Spin_AspectRatio.setRange(0.5, 5.0)
        self.Spin_AspectRatio.setSingleStep(0.1)
        self.Spin_AspectRatio.setValue(round(NaturalAspectRatio, 1))
        self.Spin_AspectRatio.setMaximumWidth(60)
        PlotRow_Layout.addWidget(QLabel("Data type:"))
        PlotRow_Layout.addWidget(self.Combo_DataType)
        PlotRow_Layout.addWidget(QLabel("Region:"))
        PlotRow_Layout.addWidget(self.Combo_PlotRegion)
        PlotRow_Layout.addWidget(QLabel("Offset:"))
        PlotRow_Layout.addWidget(self.Spin_Offset)
        PlotRow_Layout.addWidget(QLabel("Aspect ratio:"))
        PlotRow_Layout.addWidget(self.Spin_AspectRatio)
        self.Checkbox_HighlightRegions = QCheckBox("Highlight regions")
        self.Checkbox_HighlightRegions.setChecked(True)
        self.Checkbox_HighlightRegions.stateChanged.connect(self.Function_Checkbox_HighlightRegions)
        PlotRow_Layout.addWidget(self.Checkbox_HighlightRegions)
        PlotRow_Layout.addStretch()
        Section01b_Layout.addLayout(PlotRow_Layout)
        # --- Action buttons -------------------------------------------------------------------------------------
        ButtonsRow_Layout = QHBoxLayout()
        self.Button_PlotProperties = QPushButton("Plot Properties...")
        self.Button_PlotProperties.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_PlotProperties.clicked.connect(self.Function_Button_PlotProperties)
        self.Button_AxisOptions = QPushButton("Axis Options...")
        self.Button_AxisOptions.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_AxisOptions.clicked.connect(self.Function_Button_AxisOptions)
        self.Button_RefreshPlot = QPushButton("Refresh Plot")
        self.Button_RefreshPlot.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_RefreshPlot.clicked.connect(self.Function_Button_RefreshPlot)
        ButtonsRow_Layout.addWidget(self.Button_PlotProperties)
        ButtonsRow_Layout.addWidget(self.Button_AxisOptions)
        ButtonsRow_Layout.addWidget(self.Button_RefreshPlot)
        Section01b_Layout.addLayout(ButtonsRow_Layout)
        Section01b.setLayout(Section01b_Layout)
        LeftLayout.addWidget(Section01b, 22)
        # --------------------------------------------------------------------------------------------------------------
        LeftLayout.addWidget(Section02, 70)
        # --------------------------------------------------------------------------------------------------------------
        # Section 3: filtering the candidate records.
        Section03 = QGroupBox("Filtering Options")
        Section03.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section03_Layout = QVBoxLayout()
        Label_DropDown01 = QLabel("Select the asphalt binder B-number:")
        self.DropDown_Bnumber = QComboBox()
        self.DropDown_Bnumber.addItems(['Please Select...', 'All binders'] +
                                       list(self.IdentifierCombs['Bnumber'].unique()))
        self.DropDown_Bnumber.currentIndexChanged.connect(self.Function_DropDown_Bnumber)
        Label_DropDown02 = QLabel("Select the laboratory aging level:")
        self.DropDown_LabAging = QComboBox()
        self.DropDown_LabAging.addItems(['All Aging Levels'])
        self.DropDown_LabAging.setEnabled(False)
        self.DropDown_LabAging.currentIndexChanged.connect(self.Function_DropDown_LabAging)
        self.Button_Fetch = QPushButton("Fetch data")
        self.Button_Fetch.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Fetch.setSizePolicy(self.Button_Fetch.sizePolicy().Expanding,
                                        self.Button_Fetch.sizePolicy().Preferred)
        self.Button_Fetch.clicked.connect(self.Function_Button_Fetch)
        Section03_Layout.addWidget(Label_DropDown01)
        Section03_Layout.addWidget(self.DropDown_Bnumber)
        Section03_Layout.addWidget(Label_DropDown02)
        Section03_Layout.addWidget(self.DropDown_LabAging)
        Section03_Layout.addWidget(self.Button_Fetch)
        Section03.setLayout(Section03_Layout)
        RightLayout.addWidget(Section03, 20)
        # --------------------------------------------------------------------------------------------------------------
        # Section 4: table of candidate records, multi-selectable, to be added to the plot.
        Section04 = QGroupBox("Select Records for Plotting")
        Section04.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section04_Layout = QVBoxLayout()
        self.Label_NumFetchedRows = QLabel('Number of fetched data (rows): 0')
        self.Table_Records = QTableWidget()
        self.Table_Records.setRowCount(10)
        self.Table_Records.setColumnCount(len(self.ColumnNames))
        self.Table_Records.setHorizontalHeaderLabels(self.ColumnNames)
        self.Table_Records.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.Table_Records.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.Fit_Columns_To_Content()
        Section04_Layout.addWidget(self.Label_NumFetchedRows)
        Section04_Layout.addWidget(self.Table_Records)
        Section04.setLayout(Section04_Layout)
        RightLayout.addWidget(Section04, 50)
        # --------------------------------------------------------------------------------------------------------------
        # Section 5: operation buttons.
        Section05 = QGroupBox("Operation")
        Section05.setStyleSheet("QGroupBox { font-weight: bold; }")
        Section05_Layout = QVBoxLayout()
        self.Checkbox_PlotAverage = QCheckBox("Plot average of selected")
        self.Checkbox_PlotAverage.setChecked(False)
        self.Button_PlotSelected = QPushButton("Plot Selected")
        self.Button_PlotSelected.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_PlotSelected.clicked.connect(self.Function_Button_PlotSelected)
        self.Button_PlotSelected.setSizePolicy(self.Button_PlotSelected.sizePolicy().Expanding,
                                               self.Button_PlotSelected.sizePolicy().Preferred)
        self.Button_RemoveSelected = QPushButton("Remove Selected from Plot")
        self.Button_RemoveSelected.setStyleSheet(self.PushButtonStyle['Modify'])
        self.Button_RemoveSelected.clicked.connect(self.Function_Button_RemoveSelected)
        self.Button_RemoveSelected.setSizePolicy(self.Button_RemoveSelected.sizePolicy().Expanding,
                                                 self.Button_RemoveSelected.sizePolicy().Preferred)
        self.Button_ClearPlot = QPushButton("Clear Plot")
        self.Button_ClearPlot.setStyleSheet(self.PushButtonStyle['Delete'])
        self.Button_ClearPlot.clicked.connect(self.Function_Button_ClearPlot)
        self.Button_ClearPlot.setSizePolicy(self.Button_ClearPlot.sizePolicy().Expanding,
                                            self.Button_ClearPlot.sizePolicy().Preferred)
        self.Button_SavePlot = QPushButton("Save Plot...")
        self.Button_SavePlot.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_SavePlot.clicked.connect(self.Function_Button_SavePlot)
        self.Button_SavePlot.setSizePolicy(self.Button_SavePlot.sizePolicy().Expanding,
                                           self.Button_SavePlot.sizePolicy().Preferred)
        self.Button_ExportData = QPushButton("Export Data...")
        self.Button_ExportData.setStyleSheet(self.PushButtonStyle['Export'])
        self.Button_ExportData.clicked.connect(self.Function_Button_ExportData)
        self.Button_ExportData.setSizePolicy(self.Button_ExportData.sizePolicy().Expanding,
                                             self.Button_ExportData.sizePolicy().Preferred)
        self.Button_Go2Main = QPushButton("Main Page")
        self.Button_Go2Main.setStyleSheet(self.PushButtonStyle['General'])
        self.Button_Go2Main.clicked.connect(self.Function_Button_Go2Main)
        self.Button_Go2Main.setSizePolicy(self.Button_Go2Main.sizePolicy().Expanding,
                                          self.Button_Go2Main.sizePolicy().Preferred)
        Section05_Layout.addWidget(self.Checkbox_PlotAverage)
        Section05_Layout.addWidget(self.Button_PlotSelected)
        Section05_Layout.addWidget(self.Button_RemoveSelected)
        Section05_Layout.addWidget(self.Button_ClearPlot)
        Section05_Layout.addWidget(self.Button_SavePlot)
        Section05_Layout.addWidget(self.Button_ExportData)
        Section05_Layout.addWidget(self.Button_Go2Main)
        Section05.setLayout(Section05_Layout)
        RightLayout.addWidget(Section05, 30)
        # --------------------------------------------------------------------------------------------------------------
        # Final placement of the right and left layouts.
        layout.addLayout(LeftLayout, 82)
        layout.addLayout(RightLayout, 18)
        # Draw the highlight regions' initial (checked-by-default) state.
        self.Update_Region_Highlights()
        self.Update_Legend()
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def showEvent(self, event):
        # Refresh the identifier combinations, summary info, and filter dropdowns whenever this page becomes
        #   visible, since records may have been added/removed/changed elsewhere since it was last shown.
        super().showEvent(event)
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
        self.Sync_Summary_Info()
        self.Refresh_Filter_Dropdowns()
        if not self.AspectRatioInitialized:
            # Defer to the next event-loop iteration: right when "showEvent" fires, the canvas may not have
            #   received its real on-screen resize event yet, so "self.fig"'s size would still be the constructor's
            #   provisional figsize rather than its true displayed size.
            self.AspectRatioInitialized = True
            QTimer.singleShot(0, self.Set_Initial_Aspect_Ratio)
    # ------------------------------------------------------------------------------------------------------------------
    def Set_Initial_Aspect_Ratio(self):
        """
        Seeds the "Aspect ratio" spinbox with the plot's actual current (natural, undistorted) box aspect ratio
        (width:height), read from the axes' real on-screen geometry. Called once, shortly after this page is first
        shown (see "showEvent"), not on every subsequent visit, so it never overwrites a value the user has set.
        """
        Pos = self.ax.get_position()
        FigW, FigH = self.fig.get_size_inches()
        NaturalAspectRatio = (Pos.width * FigW) / (Pos.height * FigH)
        self.Spin_AspectRatio.setValue(round(NaturalAspectRatio, 1))
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh_Filter_Dropdowns(self):
        """
        Repopulates the B-number/Lab-Aging filter dropdowns from the latest "self.IdentifierCombs" (just refreshed
        in "showEvent"), so B-numbers/aging levels added to the database after this page was first built actually
        show up, without needing to restart the program. Preserves the current selection (by text) where it is
        still valid, and leaves any already-fetched table content untouched (signals are blocked throughout, so
        this never triggers "Function_DropDown_Bnumber"/"Function_DropDown_LabAging"'s own table-resetting logic).
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
    def Get_Auto_Labels(self):
        """
        Returns the default legend label of every plotted line, built from the current database values.
        """
        Labels = {}
        for Key, Entry in self.PlottedLines.items():
            if Entry['IsAverage']:
                Labels[Key] = self.Get_Average_Label(Entry['MemberIDs'])
                continue
            self.cursor.execute("SELECT Bnumber, Lab_Aging, RepNumber FROM FTIR WHERE id = ?", (Key,))
            Row = self.cursor.fetchone()
            Labels[Key] = None if Row is None else f'{Row[0]} | {Row[1]} | Rep {Row[2]}'
        return Labels
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh_After_Identifier_Change(self, LabelsBefore):
        """
        Updates this page after B-numbers or aging levels were changed in the database: the summary, dropdowns, and
        fetched table (emptied if the filtered B-number no longer exists), plus the legend labels of the plotted lines.
        "LabelsBefore" is the "Get_Auto_Labels" output from before the change, used to leave any label customized by the
        user untouched.
        """
        self.IdentifierCombs = Get_Identifier_Combinations(self.cursor)
        self.Sync_Summary_Info()
        self.Refresh_Filter_Dropdowns()
        if self.DropDown_Bnumber.currentIndex() > 0:
            self.Function_Button_Fetch()
        else:
            self.Reset_Table_Empty()
        if len(self.PlottedLines) == 0:
            return
        LabelsAfter = self.Get_Auto_Labels()
        for Key, Entry in self.PlottedLines.items():
            if LabelsAfter[Key] is not None and Entry['label'] == LabelsBefore[Key]:
                Entry['label'] = LabelsAfter[Key]
        self.Reapply_Line_Data()
        self.Update_Legend()
        self.canvas.draw()
        self.Refresh_Line_Selector()
    # ------------------------------------------------------------------------------------------------------------------
    def Sync_Summary_Info(self):
        SummaryData = Get_DB_SummaryData(self.cursor)
        self.Label_NumData.setText(f'{SummaryData["NumRows"]}')
        self.Label_NumValidData.setText(f'{SummaryData["NumValidRows"]}')
        self.Label_AvgNumReplicates.setText(f'{SummaryData["AvgNumRep"]:.1f}')
        self.Label_NumUniqueBnum.setText(f'{SummaryData["NumUniqueBnumber"]}')
        self.Label_NumUniqueLabAge.setText(f'{SummaryData["NumUniqueLabAging"]}')
        self.Label_NumUniqueBnumLabAge.setText(f'{SummaryData["NumUniqueBnumLabAge"]}')
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_Bnumber(self):
        self.Reset_Table_Empty()
        if self.DropDown_Bnumber.currentIndex() == 0:
            self.DropDown_LabAging.setEnabled(False)
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'])
        elif self.DropDown_Bnumber.currentIndex() == 1:
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'] + list(self.IdentifierCombs['Lab_Aging'].unique()))
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(True)
        else:
            Bnumber = self.DropDown_Bnumber.currentText()
            TempDF = self.IdentifierCombs[self.IdentifierCombs['Bnumber'] == Bnumber]
            self.DropDown_LabAging.clear()
            self.DropDown_LabAging.addItems(['All Aging Levels'] + list(TempDF['Lab_Aging'].unique()))
            self.DropDown_LabAging.setCurrentIndex(0)
            self.DropDown_LabAging.setEnabled(True)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_DropDown_LabAging(self):
        self.Reset_Table_Empty()
    # ------------------------------------------------------------------------------------------------------------------
    def Reset_Table_Empty(self):
        self.Table_Records.clearSelection()
        self.Label_NumFetchedRows.setText('Number of fetched data (rows): 0')
        self.Table_Records.setRowCount(10)
        for row_idx in range(10):
            for col_idx in range(len(self.ColumnNames)):
                self.Table_Records.setItem(row_idx, col_idx, QTableWidgetItem(''))
        self.Fit_Columns_To_Content()
    # ------------------------------------------------------------------------------------------------------------------
    def Fit_Columns_To_Content(self, MaxColumnWidth=400):
        """
        Auto-fit every column's width to its header/content, so a header is never clipped and a column is never
        needlessly wide (mirrors "DB_ReviewPage.Fit_Columns_To_Content" in Sub05_ReviewPage.py).
        """
        self.Table_Records.resizeColumnsToContents()
        Header = self.Table_Records.horizontalHeader()
        for col in range(self.Table_Records.columnCount()):
            if Header.sectionSize(col) > MaxColumnWidth:
                Header.resizeSection(col, MaxColumnWidth)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Fetch(self):
        self.Table_Records.clearSelection()
        Bnumber = self.DropDown_Bnumber.currentText()
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
        Rows = self.cursor.fetchall()
        self.Label_NumFetchedRows.setText(f'Number of fetched data (rows): {len(Rows)}')
        self.Table_Records.setRowCount(len(Rows))
        for row_idx, row_data in enumerate(Rows):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.Table_Records.setItem(row_idx, col_idx, item)
        self.Fit_Columns_To_Content()
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Selected_Record_IDs(self):
        """
        Returns the sorted, de-duplicated list of database "id" values for the currently selected rows in
        "self.Table_Records".
        """
        SelectedRows = sorted(set(Index.row() for Index in self.Table_Records.selectionModel().selectedRows()))
        IDs = []
        for row in SelectedRows:
            IDItem = self.Table_Records.item(row, 0)
            if IDItem is None or IDItem.text() == '':
                continue
            IDs.append(int(IDItem.text()))
        return IDs
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Legend(self):
        """
        (Re)draws two independent legends, using the current legend settings (self.LegendFontSize/LegendLoc/
        LegendHandleLength, updated by "Refresh Plot"):
          - The main legend (plotted records only, never the highlight regions), shown only when at least one
            record is plotted, at the user-chosen location.
          - The highlight-region legend (Carbonyl/Sulfoxide/Aliphatic, only when "self.RegionHighlights" is
            non-empty), always placed outside the axes, centered above it.
        Both legends must be tracked and removed by direct reference (not "Axes.get_legend()", which only ever
        reports the most-recently-created legend, not both, once a second one is added via "add_artist").

        Also re-applies "tight_layout()" first (so margins adapt to the current label sizes/tick text, e.g. after
        the X/Y label font sizes or aspect ratio changed), then -- crucially -- reserves headroom for the region
        legend (if any) via "subplots_adjust" *after* that, so it always wins and is never undone by tight_layout,
        which has no idea a legend will be placed just above the axes (see the comment below).
        """
        self.fig.tight_layout()
        if self.MainLegend is not None:
            self.MainLegend.remove()
            self.MainLegend = None
        if self.RegionLegend is not None:
            self.RegionLegend.remove()
            self.RegionLegend = None
        if len(self.PlottedLines) > 0:
            Handles = [Entry['line'] for Entry in self.PlottedLines.values()]
            Labels = [Entry['label'] for Entry in self.PlottedLines.values()]
            self.MainLegend = self.ax.legend(Handles, Labels, loc=self.LegendLoc, fontsize=self.LegendFontSize,
                                             handlelength=self.LegendHandleLength)
        if self.RegionHighlights:
            if self.MainLegend is not None:
                # Keep the main legend drawn: a second call to "Axes.legend()" would otherwise replace it.
                self.ax.add_artist(self.MainLegend)
            RegionLabels = [Span.get_label() for Span in self.RegionHighlights]
            self.RegionLegend = self.ax.legend(self.RegionHighlights, RegionLabels, loc='lower center',
                                               bbox_to_anchor=(0.5, 1.01), ncol=len(self.RegionHighlights),
                                               fontsize=self.LegendFontSize)
            # "tight_layout()" (called once, at construction) has no idea this legend would later be placed just
            #   above the axes -- left unadjusted, the axes' top edge sits almost flush with the figure's top edge,
            #   so this legend renders mostly/entirely clipped off the top of the canvas. Reserve headroom for it.
            self.fig.subplots_adjust(top=0.85)
        else:
            # No region legend: let the axes reclaim that headroom.
            self.fig.subplots_adjust(top=0.97)
        self.Label_NumPlotted.setText(f'Number of plotted records: {len(self.PlottedLines)}')
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Region_Highlights(self):
        """
        Adds (or removes) the shaded Carbonyl/Sulfoxide/Aliphatic axvspan regions per the "Highlight regions"
        checkbox. These are intentionally excluded from the main (plotted-records) legend -- see "Update_Legend".
        """
        for Span in self.RegionHighlights:
            Span.remove()
        self.RegionHighlights = []
        if not self.Checkbox_HighlightRegions.isChecked():
            return
        for Label, XLim, Color, Hatch in self.HighlightRegionSpecs:
            XMin, XMax = sorted(XLim)
            Span = self.ax.axvspan(XMin, XMax, color=Color, alpha=0.15, label=Label, hatch=Hatch)
            self.RegionHighlights.append(Span)
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Checkbox_HighlightRegions(self):
        """
        Toggles the Carbonyl/Sulfoxide/Aliphatic highlight regions on/off immediately (unlike most of the other
        Visualization Properties controls, this one applies live rather than waiting for "Refresh Plot", since it
        is a pure display toggle with no data to re-fetch).
        """
        self.Update_Region_Highlights()
        self.Update_Legend()
        self.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def Rescale_Y_Axis(self, Padding=0.05):
        """
        Fits the Y axis to the range of Y-values actually visible within the current X view, rather than each
        line's full data range: a spectrum's tallest peak (e.g. a normalization reference peak) often falls outside
        the visible wavenumber window, and naively autoscaling to the full data would leave most of the plot empty
        below that off-screen peak. Resets to the default [0, 1] range when nothing is plotted.
        """
        if len(self.PlottedLines) == 0:
            self.ax.set_ylim([0, 1])
            return
        XMin, XMax = sorted(self.ax.get_xlim())
        VisibleY = []
        for Entry in self.PlottedLines.values():
            X = Entry['line'].get_xdata()
            Y = Entry['line'].get_ydata()
            Mask = (X >= XMin) & (X <= XMax)
            if np.any(Mask):
                VisibleY.append(Y[Mask])
        if len(VisibleY) == 0:
            # None of the plotted data falls within the current X view (e.g. the user zoomed/panned somewhere with
            #   no data); fall back to a full autoscale rather than leaving a stale/empty Y range.
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)
            return
        AllY = np.concatenate(VisibleY)
        YMin, YMax = float(np.min(AllY)), float(np.max(AllY))
        Margin = (YMax - YMin) * Padding if YMax > YMin else 0.05
        self.ax.set_ylim([YMin - Margin, YMax + Margin])
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Spectrum_Columns(self, DataType):
        """
        Returns the (X_bin, X_shape, X_dtype, Y_bin, Y_shape, Y_dtype) SQL column names for either the "Processed"
        (baseline-adjusted, normalized) or "Raw" spectrum, per the "Data type" control.
        """
        if DataType == 'Raw':
            return ['RawWavenumber', 'RawWavenumber_shape', 'RawWavenumber_dtype',
                    'RawAbsorbance', 'RawAbsorbance_shape', 'RawAbsorbance_dtype']
        return ['Wavenumber', 'Wavenumber_shape', 'Wavenumber_dtype',
                'Absorption', 'Absorption_shape', 'Absorption_dtype']
    # ------------------------------------------------------------------------------------------------------------------
    def Compute_Average_Spectrum(self, IDs, SpecCols):
        """
        Fetches the given records' spectra (using "SpecCols", from "Get_Spectrum_Columns") and averages their
        Absorption values. Since different records' Wavenumber arrays can differ slightly (different resolution/
        range), the first successfully-fetched record's Wavenumber array is used as the reference grid, and every
        other record's Absorption is linearly interpolated onto it (via "np.interp") before averaging. Records
        that no longer exist in the DB are silently skipped. Returns (X, Y) or (None, None) if none could be
        fetched at all.
        """
        Placeholders = ', '.join(['?'] * len(IDs))
        self.cursor.execute(
            f"SELECT id, {', '.join(SpecCols)} FROM FTIR WHERE id IN ({Placeholders})", tuple(IDs))
        Fetched = {Row[0]: Row[1:] for Row in self.cursor.fetchall()}
        # Preserve the original selection order, so "the first selected record" really is the reference grid.
        Spectra = []
        for ID in IDs:
            if ID not in Fetched:
                continue
            WvBin, WvShape, WvDtype, AbBin, AbShape, AbDtype = Fetched[ID]
            X = Binary_to_Array(WvBin, WvShape, WvDtype)
            Y = Binary_to_Array(AbBin, AbShape, AbDtype)
            Spectra.append((X, Y))
        if len(Spectra) == 0:
            return None, None
        RefX = Spectra[0][0]
        Interpolated = [Y if (X.shape == RefX.shape and np.array_equal(X, RefX)) else np.interp(RefX, X, Y)
                        for X, Y in Spectra]
        AvgY = np.mean(Interpolated, axis=0)
        return RefX, AvgY
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Average_Label(self, IDs):
        """
        Builds the legend label for an averaged line: if every record being averaged shares the same B-number and
        Lab-Aging, uses the same "Bnumber | LabAging | ..." pattern as individual records, with "Rep #" replaced by
        "Average" -- otherwise (a mixed selection) falls back to a generic "Average (n=N)".
        """
        Placeholders = ', '.join(['?'] * len(IDs))
        self.cursor.execute(
            f"SELECT DISTINCT Bnumber, Lab_Aging FROM FTIR WHERE id IN ({Placeholders})", tuple(IDs))
        Combos = self.cursor.fetchall()
        if len(Combos) == 1:
            Bnumber, LabAging = Combos[0]
            return f'{Bnumber} | {LabAging} | Average'
        return f'Average (n={len(IDs)})'
    # ------------------------------------------------------------------------------------------------------------------
    def Reapply_Line_Data(self):
        """
        Redraws every plotted line from its stored base X/Y -- scaled by its own "YScale" factor, then plus its
        stacking offset (its position among the plotted lines times the "Comparison offset" spinbox) -- and its
        stored style/width/color/label. Called whenever the set of plotted lines changes (so the offset stacking
        stays consistent/gap-free) and by "Refresh Plot".
        """
        Offset = self.Spin_Offset.value()
        for i, Entry in enumerate(self.PlottedLines.values()):
            Y = Entry['YBase'] * Entry['YScale'] + i * Offset
            Entry['line'].set_data(Entry['X'], Y)
            Entry['line'].set_linestyle(Entry['LineStyle'])
            Entry['line'].set_linewidth(Entry['LineWidth'])
            Entry['line'].set_color(Entry['Color'])
            Entry['line'].set_label(Entry['label'])
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh_Line_Selector(self):
        """
        Repopulates the "Line Properties" line-selector combo box from the currently plotted records (using each
        line's current legend label as the item text), trying to keep the previous selection if it is still
        plotted, then syncs the style/width/color/label controls to match.
        """
        self.Combo_SelectLine.blockSignals(True)
        PreviousID = self.Combo_SelectLine.currentData()
        self.Combo_SelectLine.clear()
        for ID, Entry in self.PlottedLines.items():
            self.Combo_SelectLine.addItem(Entry['label'], ID)
        if PreviousID is not None:
            Idx = self.Combo_SelectLine.findData(PreviousID)
            if Idx >= 0:
                self.Combo_SelectLine.setCurrentIndex(Idx)
        self.Combo_SelectLine.blockSignals(False)
        self.Sync_Line_Property_Widgets()
    # ------------------------------------------------------------------------------------------------------------------
    def Sync_Line_Property_Widgets(self):
        """
        Updates the line style/width/color/label/Y-scale controls to reflect whichever line is currently selected
        in the "Line Properties" combo box, so editing a different line starts from that line's own current
        properties.
        """
        ID = self.Combo_SelectLine.currentData()
        if ID is None or ID not in self.PlottedLines:
            self.PendingLineColor = None
            self.Button_LineColor.setStyleSheet('')
            self.LineEdit_LineLabel.clear()
            self.Spin_YScale.setValue(1.0)
            return
        Entry = self.PlottedLines[ID]
        StyleIdx = self.Combo_LineStyle.findData(Entry['LineStyle'])
        if StyleIdx >= 0:
            self.Combo_LineStyle.setCurrentIndex(StyleIdx)
        self.Spin_LineWidth.setValue(Entry['LineWidth'])
        self.PendingLineColor = Entry['Color']
        self.Button_LineColor.setStyleSheet(f"background-color: {Entry['Color']};")
        self.LineEdit_LineLabel.setText(Entry['label'])
        self.Spin_YScale.setValue(Entry['YScale'])
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_PickLineColor(self):
        """
        Opens a color-picker dialog and stashes the chosen color to be applied (to whichever line is currently
        selected in the "Line Properties" combo box) the next time "Refresh Plot" is clicked.
        """
        Initial = QColor(self.PendingLineColor) if self.PendingLineColor else QColor('black')
        Selected = QColorDialog.getColor(Initial, self, "Select Line Color")
        if not Selected.isValid():
            return
        self.PendingLineColor = Selected.name()
        self.Button_LineColor.setStyleSheet(f"background-color: {self.PendingLineColor};")
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_PlotSelected(self):
        """
        Adds the currently selected records in "self.Table_Records" to the plot, using the currently selected
        "Data type" (raw/processed), stacked by the current "Comparison offset". Normally each (not-already-
        plotted) record becomes its own colored line, labeled from its B-number/Lab-Aging/Rep #; if "Plot average
        of selected" is checked, all currently selected records are instead combined into a single new averaged
        line (see "Compute_Average_Spectrum"), regardless of whether any of them are already individually plotted.
        """
        IDs = self.Get_Selected_Record_IDs()
        if len(IDs) == 0:
            QMessageBox.critical(self, "No Records Selected",
                                 'Please select one or more rows from the "Select Records for Plotting" table '
                                 'first.')
            return
        SpecCols = self.Get_Spectrum_Columns(self.Combo_DataType.currentText())
        if self.Checkbox_PlotAverage.isChecked():
            X, Y = self.Compute_Average_Spectrum(IDs, SpecCols)
            if X is None:
                QMessageBox.critical(self, "Average Failed",
                                     "None of the selected records could be fetched from the database.")
                return
            Label = self.Get_Average_Label(IDs)
            Line, = self.ax.plot(X, Y, lw=1.2, label=Label)
            Key = self.NextAverageKey
            self.NextAverageKey -= 1
            self.PlottedLines[Key] = {'line': Line, 'label': Label, 'X': X, 'YBase': Y, 'LineStyle': '-',
                                      'LineWidth': 1.2, 'Color': Line.get_color(), 'YScale': 1.0, 'IsAverage': True,
                                      'MemberIDs': list(IDs)}
        else:
            NewIDs = [ID for ID in IDs if ID not in self.PlottedLines]
            if len(NewIDs) == 0:
                return
            Placeholders = ', '.join(['?'] * len(NewIDs))
            self.cursor.execute(
                f"SELECT id, Bnumber, Lab_Aging, RepNumber, {', '.join(SpecCols)} FROM FTIR " +
                f"WHERE id IN ({Placeholders})", tuple(NewIDs))
            Rows = self.cursor.fetchall()
            for ID, Bnumber, LabAging, RepNumber, WvBin, WvShape, WvDtype, AbBin, AbShape, AbDtype in Rows:
                X = Binary_to_Array(WvBin, WvShape, WvDtype)
                Y = Binary_to_Array(AbBin, AbShape, AbDtype)
                Label = f'{Bnumber} | {LabAging} | Rep {RepNumber}'
                Line, = self.ax.plot(X, Y, lw=1.2, label=Label)
                self.PlottedLines[ID] = {'line': Line, 'label': Label, 'X': X, 'YBase': Y, 'LineStyle': '-',
                                         'LineWidth': 1.2, 'Color': Line.get_color(), 'YScale': 1.0,
                                         'IsAverage': False, 'MemberIDs': [ID]}
        self.Reapply_Line_Data()
        self.Rescale_Y_Axis()
        self.Update_Legend()
        self.canvas.draw()
        self.Refresh_Line_Selector()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_RemoveSelected(self):
        """
        Removes every currently selected record in "self.Table_Records" from the plot (records that are selected but
        not currently plotted are simply ignored), then re-stacks any remaining offset lines to close the gap.
        """
        IDs = self.Get_Selected_Record_IDs()
        if len(IDs) == 0:
            QMessageBox.critical(self, "No Records Selected",
                                 'Please select one or more rows to remove from the plot.')
            return
        Removed = 0
        for ID in IDs:
            if ID in self.PlottedLines:
                self.PlottedLines[ID]['line'].remove()
                del self.PlottedLines[ID]
                Removed += 1
        if Removed == 0:
            return
        self.Reapply_Line_Data()
        self.Rescale_Y_Axis()
        self.Update_Legend()
        self.canvas.draw()
        self.Refresh_Line_Selector()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_ClearPlot(self):
        """
        Removes every currently plotted record from the plot.
        """
        if len(self.PlottedLines) == 0:
            return
        for Entry in self.PlottedLines.values():
            Entry['line'].remove()
        self.PlottedLines = {}
        self.Rescale_Y_Axis()
        self.Update_Legend()
        self.canvas.draw()
        self.Refresh_Line_Selector()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_PlotProperties(self):
        """
        Opens matplotlib's own "Edit axis, curve and image parameters" dialog (the same one behind the toolbar's
        "Customize" button) for the plot, giving the user direct control over axis limits/labels/scale and each
        plotted curve's color/style/label/legend visibility.
        """
        self.Toolbar.edit_parameters()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_AxisOptions(self):
        """
        Opens matplotlib's own "Configure subplots" dialog (the same one behind the toolbar's "Subplots" button),
        which controls the axes' margins/spacing within the figure.
        """
        self.Toolbar.configure_subplots()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_RefreshPlot(self):
        """
        Applies every current "Visualization Properties" control to the plot: re-fetches every currently plotted
        record's spectrum if the "Data type" changed, applies the selected line's style/width/color/legend
        label/Y-scale, reapplies the comparison-offset stacking, crops to the selected plot region, sets the axes
        aspect ratio, resizes the X/Y axis labels, rescales Y to what is now visible, and redraws the legend with
        the current legend settings.
        """
        # 1. Re-fetch every currently plotted record's data using the currently selected data type (records deleted
        #   from the DB since being plotted are dropped). Average entries are re-fetched by their member ids and
        #   re-averaged, rather than looked up by their own (synthetic, non-DB) key.
        if self.PlottedLines:
            SpecCols = self.Get_Spectrum_Columns(self.Combo_DataType.currentText())
            RegularKeys = [Key for Key, Entry in self.PlottedLines.items() if not Entry.get('IsAverage')]
            if RegularKeys:
                Placeholders = ', '.join(['?'] * len(RegularKeys))
                self.cursor.execute(
                    f"SELECT id, {', '.join(SpecCols)} FROM FTIR WHERE id IN ({Placeholders})", tuple(RegularKeys))
                Fetched = {Row[0]: Row[1:] for Row in self.cursor.fetchall()}
                for ID in RegularKeys:
                    if ID not in Fetched:
                        self.PlottedLines[ID]['line'].remove()
                        del self.PlottedLines[ID]
                        continue
                    WvBin, WvShape, WvDtype, AbBin, AbShape, AbDtype = Fetched[ID]
                    self.PlottedLines[ID]['X'] = Binary_to_Array(WvBin, WvShape, WvDtype)
                    self.PlottedLines[ID]['YBase'] = Binary_to_Array(AbBin, AbShape, AbDtype)
            for Key in [Key for Key, Entry in self.PlottedLines.items() if Entry.get('IsAverage')]:
                Entry = self.PlottedLines[Key]
                NewX, NewY = self.Compute_Average_Spectrum(Entry['MemberIDs'], SpecCols)
                if NewX is None:
                    Entry['line'].remove()
                    del self.PlottedLines[Key]
                    continue
                Entry['X'] = NewX
                Entry['YBase'] = NewY
        # 2. Apply the selected line's style/width/(pending) color/legend label/Y-scale.
        SelectedID = self.Combo_SelectLine.currentData()
        if SelectedID is not None and SelectedID in self.PlottedLines:
            Entry = self.PlottedLines[SelectedID]
            Entry['LineStyle'] = self.Combo_LineStyle.currentData()
            Entry['LineWidth'] = self.Spin_LineWidth.value()
            if self.PendingLineColor:
                Entry['Color'] = self.PendingLineColor
            Entry['label'] = self.LineEdit_LineLabel.text()
            Entry['YScale'] = self.Spin_YScale.value()
        # 3. Redraw every line from its (possibly just re-fetched) base data, offset, and style/width/color.
        self.Reapply_Line_Data()
        # 4. Apply the plot region (X-axis crop).
        self.ax.set_xlim(self.Combo_PlotRegion.currentData())
        # 5. Apply the aspect ratio (the control is width:height; matplotlib's box_aspect is height:width).
        self.ax.set_box_aspect(1.0 / self.Spin_AspectRatio.value())
        # 6. Apply the X/Y axis label font sizes.
        self.ax.xaxis.label.set_fontsize(self.Spin_XLabelSize.value())
        self.ax.yaxis.label.set_fontsize(self.Spin_YLabelSize.value())
        # 7. Rescale Y to whatever is now visible, and redraw the legend with the current legend settings.
        self.Rescale_Y_Axis()
        self.LegendFontSize = self.Spin_LegendFontSize.value()
        self.LegendLoc = self.Combo_LegendLoc.currentText()
        self.LegendHandleLength = self.Spin_LegendHandleLength.value()
        self.Update_Legend()
        self.canvas.draw()
        # 8. Keep the line selector's displayed text (and the style/width/color/label controls) in sync, in case a
        #   record was dropped above or the selected line's label was just changed.
        self.Refresh_Line_Selector()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_SavePlot(self):
        """
        Saves the current figure to an image/vector file chosen by the user.
        """
        if len(self.PlottedLines) == 0:
            QMessageBox.critical(self, "Nothing to Save",
                                 "The plot is currently empty. Please plot at least one record before saving.")
            return
        FilePath, _ = QFileDialog.getSaveFileName(
            self, "Save Plot As", os.path.join(self.DB_Folder, "FTIR_Plot.png"),
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Image (*.svg);;JPEG Image (*.jpg)")
        if not FilePath:
            return
        self.fig.savefig(FilePath, dpi=300, bbox_inches='tight')
        QMessageBox.information(self, "Plot Saved", f"The plot was successfully saved to:\n{FilePath}")
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_ExportData(self):
        """
        Exports the underlying (unshifted by the comparison offset) X/Y data of every currently plotted record to
        an Excel file: each record gets two adjacent columns (Wavenumber, Absorption), with its legend label in a
        merged cell spanning that pair on row 1, and "Wavenumber"/"Absorption" sub-headers on row 2.
        """
        if len(self.PlottedLines) == 0:
            QMessageBox.critical(self, "Nothing to Export",
                                 "The plot is currently empty. Please plot at least one record before exporting.")
            return
        Directory = QFileDialog.getExistingDirectory(self, "Please Select Saving Directory", "")
        if not Directory:
            QMessageBox.critical(self, "Directory Selection Failed!", "Directory was NOT selected. Please try again.")
            return
        FileName, IsOkButtonPressed = QInputDialog.getText(
            self, "Output File Name", "Please enter the output file name (without .xlsx):",
            text=f'{self.DB_Name}_PlotData')
        if not IsOkButtonPressed:
            QMessageBox.critical(self, "Output File Name Failed!",
                                 "Output file name was NOT confirmed. Please try again.")
            return
        FileName = FileName + '.xlsx'
        wb = Workbook()
        ws = wb.active
        ws.title = "Plot Data"
        HeaderFill = ExcelFont(bold=True)
        CenterAlign = Alignment(horizontal='center', vertical='center')
        Entries = list(self.PlottedLines.values())
        for i, Entry in enumerate(Entries):
            ColX = 2 * i + 1
            ColY = 2 * i + 2
            ws.merge_cells(start_row=1, start_column=ColX, end_row=1, end_column=ColY)
            LabelCell = ws.cell(row=1, column=ColX, value=Entry['label'])
            LabelCell.font = HeaderFill
            LabelCell.alignment = CenterAlign
            ws.cell(row=2, column=ColX, value='Wavenumber').font = HeaderFill
            ws.cell(row=2, column=ColY, value='Absorption').font = HeaderFill
            X, Y = Entry['X'], Entry['YBase']
            for j in range(len(X)):
                ws.cell(row=3 + j, column=ColX, value=float(X[j]))
                ws.cell(row=3 + j, column=ColY, value=float(Y[j]))
        FullPath = os.path.join(Directory, FileName)
        wb.save(FullPath)
        QMessageBox.information(self, "Data Exported", f"The plotted data was successfully exported to:\n{FullPath}")
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Button_Go2Main(self):
        """
        Resets the filters/table (but leaves the plot itself untouched) and moves back to the main page.
        """
        self.Table_Records.clearSelection()
        self.DropDown_Bnumber.setCurrentIndex(0)
        self.DropDown_LabAging.setCurrentIndex(0)
        self.Reset_Table_Empty()
        self.stack.setCurrentIndex(0)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
