#!/usr/bin/env python3
"""
Dell G15 5520 Thermal & Fan Command Center
Entry point script: Launches the PyQt6 GUI by default, or runs CLI mode if command arguments are supplied.
"""

import sys
import os

def main():
    # If arguments are given (other than just script name), forward to CLI
    if len(sys.argv) > 1:
        import dell_g15_fan_cli
        dell_g15_fan_cli.main()
    else:
        import dell_g15_fan_gui
        dell_g15_fan_gui.main()

if __name__ == "__main__":
    main()
