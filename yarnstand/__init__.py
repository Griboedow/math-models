"""Small, inspectable yarn-stand mechanics model. All internal units are SI."""
from .model import Ball, Stand, Motion, Setup, simulate

__all__ = ['Ball', 'Stand', 'Motion', 'Setup', 'simulate']
__version__ = '0.2.0'
