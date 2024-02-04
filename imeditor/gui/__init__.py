import pygame
import ctypes
import platform
from . import widgets

def init():
    if platform.system() == "Windows":
        ctypes.windll.user32.SetProcessDPIAware()
        widgets.BuildContext().scale = x = ctypes.windll.shcore.GetScaleFactorForDevice(0)/100
    pygame.init()

__all__ = ["layouthandler", "widgets", "colors"]