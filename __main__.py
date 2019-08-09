#!/usr/bin/env python3
import os
import sys
import GPIO_config
from smbus import SMBus
from PID import PID

from PyQt5 import QtWidgets
from PyQt5.QtSql import *
from PyQt5.QtWidgets import QMessageBox

from frmMainWindow import ApplicationWindow
from mcp9600 import MCP9600

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

def main():
    
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName("HtrTest.db")
    if not db.open():
        result = QMessageBox.warning(None, 'HtrTest', "Database Error: %s" % db.lastError().text())
        print(result)
        sys.exit(1)

    # create IO object
    io = GPIO_config.io()
    pid = PID()

    # create i2c smbus object
    i2c_bus = SMBus(1)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
    # create MCP9600 T/C readout object
    tc = MCP9600(db, i2c_bus)
    
    cid=tc.mcp9600_read_id()
    print("chip id = %x" % cid)

    qApp = QtWidgets.QApplication(sys.argv)
    aw = ApplicationWindow(db, tc, io, pid)
    aw.setWindowTitle("%s" % progname)
    aw.show()
    sys.exit(qApp.exec_())
    i2c_bus.close()


if __name__ == "__main__":
    main()
