# Title: This script includes the window for changing the spectral ranges of the Carbonyl, Sulfoxide, and Aliphatic regions.
#
# Author: Farhad Abdollahi (farhad.abdollahi.ctr@dot.gov)
# Date: 11/05/2026
# ======================================================================================================================
#
# These are the ranges of the mean of the Gaussians for each region ("Gaussian_Group_Ranges" in Sub07), which decide the
#   Gaussians that count toward the deconvolution areas, and so ICO and ISO. On purpose, a change is not saved anywhere: it
#   stays until the program is closed, and the next start uses the default ranges.
# ======================================================================================================================

# Importing the required libraries.
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFontMetrics, QPainter, QPen
from PyQt5.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from scripts.Sub05_ReviewPage import Dialog_Button_Style
from scripts.Sub07_Deconvolution_Analysis import Default_Gaussian_Group_Ranges, Gaussian_Group_Limits, \
    Gaussian_Group_Ranges


Region_Colors = {'Carbonyl': '#E57373', 'Sulfoxide': '#D4B106', 'Aliphatic': '#66BB6A'}     # Same as the plots.


class Range_Slider(QWidget):
    """
    A slider with two pins, for the lower and upper limits of a range, since Qt doesn't have one. Each pin can only move in
    its own allowed part of the slider (shown lighter), and they can never reach each other. The values are whole numbers.
    """
    Values_Changed = pyqtSignal(int, int)
    Margin = 22         # Pixels at each side, so the pins and numbers at the ends stay inside the widget.
    Pin_Radius = 8      # Pixels.

    def __init__(self, LowerLimits, UpperLimits, Values, Color):
        """
        :param LowerLimits: The minimum and maximum of the lower pin.
        :param UpperLimits: The minimum and maximum of the upper pin.
        :param Values: The lower and upper values.
        :param Color: The color of the selected range.
        """
        super().__init__()
        self.LowerLimits, self.UpperLimits = LowerLimits, UpperLimits
        self.Lower, self.Upper = Values
        self.Color = QColor(Color)
        self.Dragging = None
        self.setMinimumSize(420, 62)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
    # ------------------------------------------------------------------------------------------------------------------
    def Set_Values(self, Lower, Upper):
        self.Lower = max(self.LowerLimits[0], min(self.LowerLimits[1], int(round(Lower))))
        self.Upper = max(self.UpperLimits[0], min(self.UpperLimits[1], int(round(Upper))))
        # As a safeguard, in case the allowed parts of the two pins overlap.
        if self.Lower >= self.Upper:
            self.Upper = min(self.Lower + 1, self.UpperLimits[1])
            self.Lower = min(self.Lower, self.Upper - 1)
        self.update()
        self.Values_Changed.emit(self.Lower, self.Upper)
    # ------------------------------------------------------------------------------------------------------------------
    def Value_To_X(self, Value):
        Start, End = self.LowerLimits[0], self.UpperLimits[1]
        return self.Margin + (Value - Start) / (End - Start) * (self.width() - 2 * self.Margin)
    # ------------------------------------------------------------------------------------------------------------------
    def X_To_Value(self, X):
        Start, End = self.LowerLimits[0], self.UpperLimits[1]
        return Start + (X - self.Margin) / max(self.width() - 2 * self.Margin, 1) * (End - Start)
    # ------------------------------------------------------------------------------------------------------------------
    def Move_Pin(self, Name, X):
        Value = int(round(self.X_To_Value(X)))
        if Name == 'Lower':
            Value = max(self.LowerLimits[0], min(self.LowerLimits[1], min(Value, self.Upper - 1)))
            Changed = Value != self.Lower
            self.Lower = Value
        else:
            Value = max(self.UpperLimits[0], min(self.UpperLimits[1], max(Value, self.Lower + 1)))
            Changed = Value != self.Upper
            self.Upper = Value
        if Changed:
            self.update()
            self.Values_Changed.emit(self.Lower, self.Upper)
    # ------------------------------------------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        X = event.pos().x()
        # The closest pin to the mouse moves. Between them, the middle decides.
        self.Dragging = 'Lower' if abs(X - self.Value_To_X(self.Lower)) <= abs(X - self.Value_To_X(self.Upper)) else 'Upper'
        self.Move_Pin(self.Dragging, X)
    # ------------------------------------------------------------------------------------------------------------------
    def mouseMoveEvent(self, event):
        if self.Dragging is not None:
            self.Move_Pin(self.Dragging, event.pos().x())
    # ------------------------------------------------------------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        self.Dragging = None
    # ------------------------------------------------------------------------------------------------------------------
    def paintEvent(self, event):
        Painter = QPainter(self)
        Painter.setRenderHint(QPainter.Antialiasing)
        Y = 24.0
        Height = 6.0
        def Bar(Start, End, Color):
            Painter.setPen(Qt.NoPen)
            Painter.setBrush(QColor(Color))
            Painter.drawRoundedRect(QRectF(self.Value_To_X(Start), Y - Height / 2,
                                           self.Value_To_X(End) - self.Value_To_X(Start), Height), 3, 3)
        # The whole slider, the parts that the pins can move in, and the selected range.
        Bar(self.LowerLimits[0], self.UpperLimits[1], '#D0D0D0')
        Light = QColor(self.Color)
        Light.setAlpha(90)
        Bar(self.LowerLimits[0], self.LowerLimits[1], Light)
        Bar(self.UpperLimits[0], self.UpperLimits[1], Light)
        Bar(self.Lower, self.Upper, self.Color)
        # The numbers of the limits, below the slider.
        Painter.setPen(QColor('#606060'))
        Metrics = QFontMetrics(self.font())
        for Value in [self.LowerLimits[0], self.LowerLimits[1], self.UpperLimits[0], self.UpperLimits[1]]:
            Text = f'{Value}'
            X = self.Value_To_X(Value)
            Painter.drawLine(QPointF(X, Y + 5), QPointF(X, Y + 9))
            Painter.drawText(QPointF(X - Metrics.horizontalAdvance(Text) / 2 if hasattr(Metrics, 'horizontalAdvance')
                                     else X - Metrics.width(Text) / 2, Y + 24), Text)
        # The pins.
        Painter.setPen(QPen(QColor('#404040'), 1.5))
        Painter.setBrush(QColor('#FFFFFF'))
        for Value in [self.Lower, self.Upper]:
            Painter.drawEllipse(QPointF(self.Value_To_X(Value), Y), self.Pin_Radius, self.Pin_Radius)
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================


class Spectral_Ranges_Dialog(QDialog):
    """
    This class is the window for changing the spectral ranges. It doesn't change anything by itself: after "Apply", the new
    ranges are in "Get_Ranges".
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spectral Ranges")
        Layout = QVBoxLayout(self)
        Note = QLabel("The ranges of the Gaussians for each region (1/cm). They decide which Gaussians count toward the "
                      "deconvolution areas, and so ICO and ISO.\n\nEach pin only moves in the lighter part of its slider. "
                      "Any change lasts until you close the program, and the next start uses the default ranges.")
        Note.setWordWrap(True)
        Layout.addWidget(Note)
        self.Sliders = {}
        self.Labels = {}
        for Region, Values in Gaussian_Group_Ranges.items():
            Box = QGroupBox(Region)
            BoxLayout = QVBoxLayout(Box)
            Limits = Gaussian_Group_Limits[Region]
            self.Labels[Region] = QLabel()
            self.Sliders[Region] = Range_Slider(Limits[0], Limits[1], Values, Region_Colors[Region])
            self.Sliders[Region].Values_Changed.connect(lambda Lower, Upper, Name=Region: self.Update_Label(Name))
            BoxLayout.addWidget(self.Labels[Region])
            BoxLayout.addWidget(self.Sliders[Region])
            Layout.addWidget(Box)
            self.Update_Label(Region)
        Buttons = QHBoxLayout()
        self.Button_Reset = QPushButton("Reset to Defaults")
        self.Button_Reset.setStyleSheet(Dialog_Button_Style['Modify'])
        self.Button_Reset.setAutoDefault(False)
        self.Button_Reset.clicked.connect(self.Function_Reset)
        self.Button_Cancel = QPushButton("Cancel")
        self.Button_Cancel.setStyleSheet(Dialog_Button_Style['General'])
        self.Button_Cancel.setAutoDefault(False)
        self.Button_Cancel.clicked.connect(self.reject)
        self.Button_Apply = QPushButton("Apply")
        self.Button_Apply.setStyleSheet(Dialog_Button_Style['Accept'])
        self.Button_Apply.setDefault(True)
        self.Button_Apply.clicked.connect(self.accept)
        Buttons.addWidget(self.Button_Reset)
        Buttons.addStretch(1)
        Buttons.addWidget(self.Button_Cancel)
        Buttons.addWidget(self.Button_Apply)
        Layout.addLayout(Buttons)
        self.resize(620, self.sizeHint().height())
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Label(self, Region):
        Slider = self.Sliders[Region]
        Default = Default_Gaussian_Group_Ranges[Region]
        self.Labels[Region].setText(f'Current: <b>{Slider.Lower} to {Slider.Upper}</b> &nbsp;&nbsp; '
                                    f'(default: {Default[0]} to {Default[1]})')
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Reset(self):
        # Only moves the pins. Nothing changes until "Apply".
        for Region, Slider in self.Sliders.items():
            Slider.Set_Values(*Default_Gaussian_Group_Ranges[Region])
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Ranges(self):
        return {Region: (Slider.Lower, Slider.Upper) for Region, Slider in self.Sliders.items()}
