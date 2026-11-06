"""
This module lets the user edit the fitted Gaussians with the mouse, directly on the plots of the Main and Modify pages.

While the editing is on, the user clicks on a Gaussian and drags its three yellow triangles:
    Peak triangle (top)                 : up/down to change the amplitude.
    Center triangle (mirror line)       : left/right to change the mean.
    Leg triangle (one sigma from mean)  : left/right to change the standard deviation.

The areas, ICO, and ISO update live. Clicking on the button again keeps the changes for the current record, by updating
the Gaussian table and running the "Re-Plot" function of the page, and pressing Esc discards them. Nothing goes to the
database here: that is still done by the "OK & Accept" and "Mark as Outlier" buttons of the page.

For speed, the rest of the plots is saved as a background image, and only the Gaussians and triangles are redrawn on it.
"""
import traceback
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QMessageBox, QShortcut, QTableWidgetItem
from scripts.Sub07_Deconvolution_Analysis import gaussian_bell, Gaussian_Group_Ranges, Get_Gaussian_Group_Indices


Group_Axes = {'Carbonyl': 1, 'Sulfoxide': 2, 'Aliphatic': 3}    # The index of the plot of each group.
Mean_Margin = 0.5           # The mean stays this far (1/cm) inside its range, so rounding in the table can't push it out.
Sigma_Bounds = (1, 60)      # Limits of the standard deviation (1/cm), same as the deconvolution algorithm.
Min_Amplitude = 1e-4        # A Gaussian with zero amplitude would be removed by "Re-Plot".
Amplitude_Headroom = 0.10   # Extra room at the top of the plots while editing, as a ratio of their height.
Pick_Tolerance_Handle = 10  # Pixels.
Pick_Tolerance_Line = 7     # Pixels.
Min_Handle_Gap = 18         # Pixels: the triangles of a small Gaussian are kept this far apart to stay grabbable.
Hint_Text = 'Click on a Gaussian and drag its triangles. Esc to discard.'
Hint_Position = 0.523       # The gap between the labels of the two lower plots, as a ratio of the figure width.


def Fill_Gaussian_Table(Table, Gaussians, Format='.4e'):
    """
    This function writes the Gaussians to the table of the page.

    :param Table: The table widget.
    :param Gaussians: An array of the Gaussians, where the columns are the mean, standard deviation, and amplitude.
    :param Format: The format of the numbers, defaults to the one used by the pages.
    """
    Table.clearSelection()
    Table.setRowCount(Gaussians.shape[0])
    for Row in range(Gaussians.shape[0]):
        for Col in range(3):
            Table.setItem(Row, Col, QTableWidgetItem(f'{Gaussians[Row, Col]:{Format}}'))
# ======================================================================================================================
# ======================================================================================================================


def Table_Has_Pending_Edits(Table, Gaussians):
    """
    This function checks if the user changed the table without clicking on "Re-Plot" (or added a row to it).

    :param Table: The table widget.
    :param Gaussians: An array of the current Gaussians.
    :return: True if the table is not showing the current Gaussians.
    """
    if Table.rowCount() != Gaussians.shape[0]:
        return True
    for Row in range(Gaussians.shape[0]):
        for Col in range(3):
            Item = Table.item(Row, Col)
            if (Item is None) or (Item.text() != f'{Gaussians[Row, Col]:.4e}'):
                return True
    return False
# ======================================================================================================================
# ======================================================================================================================


class Gaussian_Drag_Editor:
    def __init__(self, Page, Button, Get_Gaussians, FreezeWidgets):
        """
        :param Page: The Main or Modify page, including the canvas, plots, table, labels, and "Re-Plot" function.
        :param Button: The button for turning the editing on and off.
        :param Get_Gaussians: A function returning the array of the current Gaussians of the page.
        :param FreezeWidgets: A list of the widgets to disable while editing.
        """
        self.Page = Page
        self.Button = Button
        self.Get_Gaussians = Get_Gaussians
        self.FreezeWidgets = FreezeWidgets
        self.Labels = [Page.Decon_Label_CArea, Page.Decon_Label_SArea, Page.Decon_Label_AArea, Page.Decon_Label_Index]
        self.Active = False
        self.Reset_State()
        # Setting up the button and the Esc key.
        self.Button.setFocusPolicy(Qt.NoFocus)      # So the keyboard can't click on it by accident.
        self.Button.clicked.connect(self.Function_Button)
        self.Update_Button()
        self.Shortcut = QShortcut(QKeySequence(Qt.Key_Escape), Page, activated=self.Function_Cancel)
        self.Shortcut.setEnabled(False)
        # As a safeguard: if the page gets replaced while editing, keep the changes and finish.
        Page.stack.currentChanged.connect(self.Function_Stack_Changed)
    # ------------------------------------------------------------------------------------------------------------------
    def Reset_State(self):
        self.GL = None              # The working copy of all Gaussians.
        self.Backup = None          # The latest saved Gaussians.
        self.LabelsBackup = []      # The latest saved text of the labels.
        self.Rows = {}              # {Row of the Gaussian: Name of its group}, for the editable Gaussians.
        self.Lines = {}             # {Row of the Gaussian: The plotted line}.
        self.Axis = {}              # {Row of the Gaussian: Its plot}.
        self.AmplitudeMax = {}      # {Row of the Gaussian: Maximum allowed amplitude}.
        self.Selected = None        # Row of the selected Gaussian.
        self.Dragging = None        # Name of the triangle which is being dragged.
        self.DragStart = None       # Position of the mouse and values of the Gaussian when the dragging started.
        self.LegSide = 1            # The side of the mean with the leg triangle.
        self.Handles = {}           # The three triangles.
        self.Hint = None            # The text showing how to use the tool, or the values of the selected Gaussian.
        self.Background = None      # The image of the plots, without the Gaussians.
        self.HiddenLines = []       # The Gaussians plotted by the page.
        self.Limits = []            # The limits of the plots, for restoring them.
        self.Frozen = []            # The widgets that this tool disabled.
        self.EventIDs = []          # The connections to the mouse events.
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Button(self):
        Style = self.Page.PushButtonStyle
        self.Button.setText("Ready to Save" if self.Active else "Edit Gaussians")
        self.Button.setStyleSheet(Style['AddData'] if self.Active else Style['Review'])
        self.Button.setToolTip("Keep the changes for this record. They go to the database by 'OK && Accept'. "
                               "Esc discards them." if self.Active else "Edit the fitted Gaussians with the mouse.")
    # ==================================================================================================================
    # Turning the editing on and off.
    # ==================================================================================================================
    def Function_Button(self):
        try:
            if self.Active:
                self.Finish(Save=True)
            else:
                self.Start()
        except Exception:
            self.Handle_Error()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Cancel(self):
        try:
            self.Finish(Save=False)
        except Exception:
            self.Handle_Error()
    # ------------------------------------------------------------------------------------------------------------------
    def Function_Stack_Changed(self, Index):
        if self.Active and (not self.Page.isVisible()):
            self.Function_Button()
    # ------------------------------------------------------------------------------------------------------------------
    def Handle_Error(self):
        # Something unexpected happened, so go back to the latest saved values, instead of crashing the software.
        Error = traceback.format_exc()
        try:
            self.Finish(Save=False)
        except Exception:
            Error += '\n' + traceback.format_exc()
            self.Active = False
            self.Update_Button()
        QMessageBox.critical(self.Page, "Edit Gaussians", "Editing the Gaussians was stopped, and the changes were " +
                             f"discarded, because of an error:\n\n{Error}")
    # ------------------------------------------------------------------------------------------------------------------
    def Start(self):
        # First, apply the changes in the table which are not plotted yet, as they would be overwritten otherwise.
        Gaussians = np.array(self.Get_Gaussians(), dtype=float)
        if Gaussians.ndim != 2 or Gaussians.shape[1] != 3:
            Gaussians = np.zeros((0, 3))
        if Table_Has_Pending_Edits(self.Page.GL_Table, Gaussians):
            try:
                self.Page.RePlot_Button_Function()
            except Exception:
                QMessageBox.critical(self.Page, "Edit Gaussians", "The values in the Gaussian table could not be " +
                                     f"plotted, so please fix them first:\n\n{traceback.format_exc()}")
                return
            Gaussians = np.array(self.Get_Gaussians(), dtype=float)
        # Find the Gaussians that can be edited.
        Rows = {}
        for Group, (Xmin, Xmax) in Gaussian_Group_Ranges.items():
            Valid = np.all(np.isfinite(Gaussians), axis=1) & (Gaussians[:, 0] > Xmin) & (Gaussians[:, 0] < Xmax) & \
                    (Gaussians[:, 1] != 0) & (Gaussians[:, 2] > 0)
            Rows.update({int(Row): Group for Row in np.where(Valid)[0]})
        if len(Rows) == 0:
            QMessageBox.information(self.Page, "Edit Gaussians", "There are no Gaussians to edit in the Carbonyl, " +
                                    "Sulfoxide, and Aliphatic ranges of this record.")
            return
        # Start the editing.
        self.Reset_State()
        self.Active = True
        self.GL = Gaussians
        self.Backup = Gaussians.copy()
        self.Rows = Rows
        self.LabelsBackup = [Label.text() for Label in self.Labels]
        self.Freeze_Page()
        self.Prepare_Plots()
        self.EventIDs = [self.Page.canvas.mpl_connect(Name, self.Guard(Function)) for Name, Function in [
            ('draw_event', self.Event_Draw), ('button_press_event', self.Event_MousePress),
            ('motion_notify_event', self.Event_MouseMove), ('button_release_event', self.Event_MouseRelease)]]
        self.Shortcut.setEnabled(True)
        self.Update_Button()
        self.Page.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def Finish(self, Save):
        if not self.Active:
            return
        Changed = Save and (not np.allclose(self.GL, self.Backup, rtol=0, atol=0, equal_nan=True))
        Gaussians, Backup, LabelsBackup = self.GL, self.Backup, self.LabelsBackup
        self.Active = False
        self.Shortcut.setEnabled(False)
        for Widget, Enabled in self.Frozen:
            Widget.setEnabled(Enabled)
        self.Clean_Up_Plots()
        self.Reset_State()
        self.Update_Button()
        self.Page.canvas.setCursor(Qt.ArrowCursor)
        if Changed:
            self.Apply_Gaussians(Gaussians, Backup, LabelsBackup)
        else:
            # Nothing to apply, so the page goes back to exactly how it was.
            for Label, Text in zip(self.Labels, LabelsBackup):
                Label.setText(Text)
            if hasattr(self.Page, 'Update_SBS_Tab'):
                self.Page.Update_SBS_Tab()
            self.Page.canvas.draw()
    # ------------------------------------------------------------------------------------------------------------------
    def Apply_Gaussians(self, Gaussians, Backup, LabelsBackup):
        # The "Re-Plot" function of the page reads the table. More digits are used here so nothing gets lost by rounding
        #   (it shows the table in the usual format at the end).
        try:
            Fill_Gaussian_Table(self.Page.GL_Table, Gaussians, Format='.10e')
            self.Page.RePlot_Button_Function()
        except Exception:
            Error = traceback.format_exc()
            Fill_Gaussian_Table(self.Page.GL_Table, Backup, Format='.10e')
            self.Page.RePlot_Button_Function()
            for Label, Text in zip(self.Labels, LabelsBackup):
                Label.setText(Text)
            QMessageBox.critical(self.Page, "Edit Gaussians", "The changes could not be applied, so the latest saved " +
                                 f"values were restored:\n\n{Error}")
    # ------------------------------------------------------------------------------------------------------------------
    def Freeze_Page(self):
        # Disable anything which can change the Gaussians or leave the page while editing, including the menu bar.
        Widgets = list(self.FreezeWidgets) + [self.Page.window().menuBar()]
        self.Frozen = [(Widget, Widget.isEnabled()) for Widget in Widgets]
        for Widget in Widgets:
            Widget.setEnabled(False)
    # ------------------------------------------------------------------------------------------------------------------
    def Prepare_Plots(self):
        Axes = self.Page.axes
        # Hide the Gaussians of the page, and fix the limits of the plots so they don't jump while dragging.
        for Index in Group_Axes.values():
            Ax = Axes[Index]
            self.Limits.append((Ax, Ax.get_xlim(), Ax.get_ylim(), Ax.get_autoscalex_on(), Ax.get_autoscaley_on()))
            self.HiddenLines += [Line for Line in Ax.lines if Line.get_linestyle() == '--']
            Bottom, Top = Ax.get_ylim()
            Ax.set_xlim(Ax.get_xlim())
            Ax.set_ylim(Bottom, Top + Amplitude_Headroom * (Top - Bottom))
        for Line in self.HiddenLines:
            Line.set_visible(False)
        # Add all the editable Gaussians. Those which don't count toward the areas are shown in gray.
        for Row, Group in self.Rows.items():
            Ax = Axes[Group_Axes[Group]]
            self.Axis[Row] = Ax
            self.AmplitudeMax[Row] = Ax.get_ylim()[1]
            X = np.linspace(*sorted(Ax.get_xlim()), num=500)
            self.Lines[Row], = Ax.plot(X, self.Calc_Line(Row, X), ls='--', lw=0.5, color='r', animated=True,
                                       scalex=False, scaley=False, label='_nolegend_')
        self.Hint = self.Page.fig.text(Hint_Position, 0.006, Hint_Text, ha='center', va='bottom', fontsize=9,
                                       fontweight='bold', color='#B00000', animated=True)
        self.Update_Line_Styles()
    # ------------------------------------------------------------------------------------------------------------------
    def Clean_Up_Plots(self):
        for ID in self.EventIDs:
            self.Page.canvas.mpl_disconnect(ID)
        self.Remove_Handles()
        for Line in self.Lines.values():
            Line.remove()
        if self.Hint is not None:
            self.Hint.remove()
        for Line in self.HiddenLines:
            Line.set_visible(True)
        for Ax, Xlim, Ylim, AutoX, AutoY in self.Limits:
            Ax.set_xlim(Xlim)
            Ax.set_ylim(Ylim)
            Ax.set_autoscalex_on(AutoX)
            Ax.set_autoscaley_on(AutoY)
    # ==================================================================================================================
    # Drawing.
    # ==================================================================================================================
    def Calc_Gaussian(self, Row, X):
        return gaussian_bell(X, self.GL[Row, 0], np.abs(self.GL[Row, 1]), self.GL[Row, 2])
    # ------------------------------------------------------------------------------------------------------------------
    def Calc_Line(self, Row, X):
        # The flat tails are not drawn, as they would cover the zero line with the lines of all the Gaussians.
        Y = self.Calc_Gaussian(Row, X)
        Y[np.abs(X - self.GL[Row, 0]) > 4.5 * np.abs(self.GL[Row, 1])] = np.nan
        return Y
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Line_Styles(self):
        Groups = Get_Gaussian_Group_Indices(self.GL)
        Counted = set(int(Row) for Rows in Groups.values() for Row in Rows)
        for Row, Line in self.Lines.items():
            Line.set_color('r' if Row in Counted else '#808080')
            Line.set_linestyle('-' if Row == self.Selected else '--')
            Line.set_linewidth(1.5 if Row == self.Selected else 0.7)
        return Groups
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Labels(self, Groups):
        # Same calculation as "Re-Plot".
        Areas = [(self.GL[Groups[Group], 2] * np.sqrt(2 * np.pi) * np.abs(self.GL[Groups[Group], 1])).sum()
                 for Group in ['Carbonyl', 'Sulfoxide', 'Aliphatic']]
        self.Labels[0].setText(f'Carbonyl Area: {Areas[0]:.2f}')
        self.Labels[1].setText(f'Sulfoxide Area: {Areas[1]:.2f}')
        self.Labels[2].setText(f'Aliphatic Area: {Areas[2]:.2f}')
        if Areas[2] > 0:
            self.Labels[3].setText(f'ICO: {Areas[0] / Areas[2]:.4f}, ISO: {Areas[1] / Areas[2]:.4f}')
        else:
            self.Labels[3].setText('ICO: N/A, ISO: N/A')
        # The SBS detection of the "Modification" tab is live as well (e.g., the 1377 Gaussian is its reference).
        if hasattr(self.Page, 'Update_SBS_Tab'):
            self.Page.Update_SBS_Tab(self.GL)
    # ------------------------------------------------------------------------------------------------------------------
    def Get_Handle_Pixels(self):
        """
        This function finds the position of the triangles in pixels. They normally sit on the Gaussian, but the triangles
        of a very small or narrow Gaussian are pushed apart, so each of them can still be grabbed.
        """
        Mu, Sigma, Amplitude = self.GL[self.Selected, 0], np.abs(self.GL[self.Selected, 1]), self.GL[self.Selected, 2]
        Ax = self.Axis[self.Selected]
        Transform = Ax.transData.transform
        CenterX, CenterY = Transform((Mu, 0.5 * Amplitude))
        PeakY = max(Transform((Mu, Amplitude))[1], CenterY + Min_Handle_Gap)
        LegX, LegY = Transform((Mu + self.LegSide * Sigma, Amplitude * np.exp(-0.5)))
        if np.abs(LegX - CenterX) < Min_Handle_Gap:
            Direction = np.sign(Transform((Mu + self.LegSide, 0))[0] - CenterX)
            LegX = CenterX + Direction * Min_Handle_Gap
        return {'Peak': (CenterX, PeakY), 'Center': (CenterX, CenterY), 'Leg': (LegX, LegY)}
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Selected_Artists(self):
        if self.Selected is None:
            self.Hint.set_text(Hint_Text)
            return
        Row = self.Selected
        Ax = self.Axis[Row]
        # Keep the leg triangle inside the plot, by moving it to the other side when it is needed.
        if self.Dragging != 'Leg':
            self.LegSide = 1 if self.GL[Row, 0] + np.abs(self.GL[Row, 1]) <= max(Ax.get_xlim()) else -1
        self.Lines[Row].set_ydata(self.Calc_Line(Row, self.Lines[Row].get_xdata()))
        Inverted = Ax.transData.inverted()
        for Name, Pixel in self.Get_Handle_Pixels().items():
            X, Y = Inverted.transform(Pixel)
            self.Handles[Name].set_data([X], [Y])
        self.Hint.set_text(f'Mean: {self.GL[Row, 0]:.1f},  Std: {np.abs(self.GL[Row, 1]):.1f},  '
                           f'Amp: {self.GL[Row, 2]:.4f}.  Esc to discard.')
    # ------------------------------------------------------------------------------------------------------------------
    def Draw_Artists(self):
        for Row, Line in self.Lines.items():
            if Row != self.Selected:
                self.Axis[Row].draw_artist(Line)
        if self.Selected is not None:
            Ax = self.Axis[self.Selected]
            Ax.draw_artist(self.Lines[self.Selected])
            for Handle in self.Handles.values():
                Ax.draw_artist(Handle)
        self.Page.fig.draw_artist(self.Hint)
    # ------------------------------------------------------------------------------------------------------------------
    def Refresh(self):
        # Fast update: put back the background, and only draw the Gaussians and the triangles on it.
        self.Update_Selected_Artists()
        if self.Background is None:
            self.Page.canvas.draw_idle()
            return
        self.Page.canvas.restore_region(self.Background)
        self.Draw_Artists()
        self.Page.canvas.blit(self.Page.fig.bbox)
    # ------------------------------------------------------------------------------------------------------------------
    def Remove_Handles(self):
        for Handle in self.Handles.values():
            Handle.remove()
        self.Handles = {}
    # ------------------------------------------------------------------------------------------------------------------
    def Select_Gaussian(self, Row):
        # Selecting another Gaussian keeps the changes of the previous one, in the working copy.
        self.Remove_Handles()
        self.Selected = Row
        if Row is not None:
            Ax = self.Axis[Row]
            for Name, Marker in [('Peak', '^'), ('Center', '>'), ('Leg', '>')]:
                self.Handles[Name], = Ax.plot([], [], ls='', marker=Marker, ms=10, markerfacecolor='yellow',
                                              markeredgecolor='k', markeredgewidth=1, animated=True, scalex=False,
                                              scaley=False, label='_nolegend_')
        self.Update_Line_Styles()
        self.Refresh()
    # ==================================================================================================================
    # Mouse events.
    # ==================================================================================================================
    def Guard(self, Function):
        # Any unexpected error in the mouse events stops the editing, instead of leaving it in an unknown state.
        def Guarded(event):
            if not self.Active:
                return
            try:
                Function(event)
            except Exception:
                self.Handle_Error()
        return Guarded
    # ------------------------------------------------------------------------------------------------------------------
    def Event_Draw(self, event):
        # The whole figure was redrawn (e.g., the window was resized), so save the new background.
        self.Background = self.Page.canvas.copy_from_bbox(self.Page.fig.bbox)
        self.Update_Selected_Artists()
        self.Draw_Artists()
    # ------------------------------------------------------------------------------------------------------------------
    def Find_Handle_At(self, event):
        if self.Selected is None:
            return None
        Closest, ClosestDistance = None, Pick_Tolerance_Handle
        for Name, (X, Y) in self.Get_Handle_Pixels().items():
            Distance = np.hypot(X - event.x, Y - event.y)
            if Distance <= ClosestDistance:
                Closest, ClosestDistance = Name, Distance
        return Closest
    # ------------------------------------------------------------------------------------------------------------------
    def Find_Gaussian_At(self, event):
        # Find the closest Gaussian to the mouse. The flat tails lie on the zero line, so they are not considered.
        Closest, ClosestDistance = None, Pick_Tolerance_Line
        for Row, Ax in self.Axis.items():
            if Ax is not event.inaxes:
                continue
            X = self.Lines[Row].get_xdata()
            X = X[np.abs(X - self.GL[Row, 0]) <= 3.5 * np.abs(self.GL[Row, 1])]
            if X.size == 0:
                continue
            Pixels = Ax.transData.transform(np.column_stack((X, self.Calc_Gaussian(Row, X))))
            Distance = np.hypot(Pixels[:, 0] - event.x, Pixels[:, 1] - event.y).min()
            if Distance <= ClosestDistance:
                Closest, ClosestDistance = Row, Distance
        return Closest
    # ------------------------------------------------------------------------------------------------------------------
    def Mouse_To_Data(self, event):
        # Using the pixels instead of event.xdata, since event.xdata is None when the mouse leaves the plot.
        return self.Axis[self.Selected].transData.inverted().transform((event.x, event.y))
    # ------------------------------------------------------------------------------------------------------------------
    def Event_MousePress(self, event):
        if event.button != 1:
            return
        self.Dragging = None        # In case the release of the previous drag never arrived (e.g., by Alt+Tab).
        Name = self.Find_Handle_At(event)
        if Name is not None:
            # The changes are relative to this point, so grabbing a triangle off-center doesn't make it jump.
            self.Dragging = Name
            self.DragStart = (self.Mouse_To_Data(event), self.GL[self.Selected, :].copy())
            return
        self.Select_Gaussian(self.Find_Gaussian_At(event))
        self.Update_Cursor(event)
    # ------------------------------------------------------------------------------------------------------------------
    def Event_MouseMove(self, event):
        if self.Dragging is None:
            self.Update_Cursor(event)
            return
        # If the button is not down anymore, the release was missed (e.g., by Alt+Tab), so the dragging is over.
        if not (event.guiEvent.buttons() & Qt.LeftButton):
            self.Event_MouseRelease(event)
            return
        Row = self.Selected
        (StartX, StartY), Start = self.DragStart
        X, Y = self.Mouse_To_Data(event)
        # All the safeguards on the values are here.
        if self.Dragging == 'Peak':
            self.GL[Row, 2] = np.clip(Start[2] + (Y - StartY), Min_Amplitude, self.AmplitudeMax[Row])
        elif self.Dragging == 'Center':
            Xmin, Xmax = Gaussian_Group_Ranges[self.Rows[Row]]
            self.GL[Row, 0] = np.clip(Start[0] + (X - StartX), Xmin + Mean_Margin, Xmax - Mean_Margin)
        else:
            self.GL[Row, 1] = np.clip(np.abs(Start[1]) + self.LegSide * (X - StartX), Sigma_Bounds[0], Sigma_Bounds[1])
        self.Update_Labels(self.Update_Line_Styles())
        self.Refresh()
    # ------------------------------------------------------------------------------------------------------------------
    def Event_MouseRelease(self, event):
        if self.Dragging is None:
            return
        self.Dragging = None
        self.DragStart = None
        self.Refresh()
        self.Update_Cursor(event)
    # ------------------------------------------------------------------------------------------------------------------
    def Update_Cursor(self, event):
        Name = self.Find_Handle_At(event)
        if Name == 'Peak':
            Cursor = Qt.SizeVerCursor
        elif Name is not None:
            Cursor = Qt.SizeHorCursor
        elif self.Find_Gaussian_At(event) is not None:
            Cursor = Qt.PointingHandCursor
        else:
            Cursor = Qt.ArrowCursor
        if self.Page.canvas.cursor().shape() != Cursor:
            self.Page.canvas.setCursor(Cursor)
