import os
import sys
import pandas as pd
import numpy as np
import pyqtgraph as pg
import tkinter as tk
from tkinter import filedialog
import re
import random
import hashlib
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.signal import find_peaks
from scipy import stats
from scipy.ndimage import gaussian_filter1d
from collections import defaultdict
import glob
from scipy.optimize import curve_fit, leastsq, root_scalar
from scipy.interpolate import UnivariateSpline, interp1d, make_smoothing_spline

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication, QWidget, QDialog, QMdiSubWindow
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, pyqtSlot, QTimer

root = tk.Tk()
root.withdraw()

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

import warnings
warnings.filterwarnings('ignore')
