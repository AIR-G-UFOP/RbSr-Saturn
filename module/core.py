import os
import sys
import pandas as pd
import numpy as np
import pyqtgraph as pg
import tkinter as tk
from tkinter import filedialog
import re
import random
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication, QWidget
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, pyqtSlot

root = tk.Tk()
root.withdraw()
