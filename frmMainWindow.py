import RPi.GPIO as GPIO
import numpy
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import QTimer
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtWidgets import QApplication
from QLed import QLed

class ApplicationWindow(QtWidgets.QMainWindow):

    def __init__(self, db, tc, io, pid):
        super(ApplicationWindow, self).__init__()
        self.db = db
        self.tc = tc  # Thermocouple
        self.io = io
        self.pid = pid
        self.temperature_data = [] # list of tempeatures to be plotted
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.control_mode = 'bang_bang'
        self.win = uic.loadUi('mainwindow.ui', self)
        self.duty_cycle = 0

        # dict = quieres.db_fetch_table_data(self.db, 'tblPlotSettings')

        self.show()

        self.__plot_config()
        self.data_idx = 0
        self.seconds_elapsed = [0]

        self.pid.Initialize()
        self.__init_ui()

        self.set_callback_ftns()
        self.read_params_from_db()

        self.setStyleSheet(open("HeaterTest.css", "r").read())
        self.timer = QTimer(self)

    def set_callback_ftns(self):

        self.win.spinHysteresisC.valueChanged.connect(self.__update_hysteresis)

        self.win.spinP.valueChanged.connect(self.__set_p)
        self.win.spinI.valueChanged.connect(self.__set_i)
        self.win.spinD.valueChanged.connect(self.__set_d)

        self.win.chkRelay1.released.connect(self.__relay1_operate)
        self.win.chkRelay2.released.connect(self.__relay2_operate)
        self.win.chkRelay3.released.connect(self.__relay3_operate)

        self.win.btnStartTest.released.connect(self.start_heater_test)
        self.win.btnStopTest.released.connect(self.stop_heater_test)
        self.win.slide_bb_pid.released.connect(self.__set_control_mode)
        self.win.dialTcFilter.valueChanged.connect(self.__tc_filter_change)

        self.win.spinSetptC.valueChanged.connect(self.__update_setpoint)
        self.win.spinTestSeconds.valueChanged.connect(self.__update_duration)
        self.win.spinMaxTempC.valueChanged.connect(self.__update_max_temp)

    def read_params_from_db(self):

        hysteresis = int(self.db_select_parameter('HYSTERESIS'))
        self.win.spinHysteresisC.setValue(hysteresis)

        tc_filter = int(self.db_select_parameter('TC_FILTER'))
        self.win.dialTcFilter.setValue(tc_filter)
        self.tc.write_tc_filter_value(tc_filter)

        max_temp = int(self.db_select_parameter('MAX_TEMP'))
        self.win.spinMaxTempC.setValue(max_temp)

        duration = int(self.db_select_parameter('SECONDS'))
        self.win.spinTestSeconds.setValue(duration)

        setpt = int(self.db_select_parameter('SETPT'))
        self.win.spinSetptC.setValue(setpt)

        self.control_mode = self.db_select_parameter('MODE')
        if self.control_mode == 'bang_bang':
            self.win.slide_bb_pid.setChecked(True)
        else:
            self.win.slide_bb_pid.setChecked(False)

        self.__set_control_mode()

        self.pid.Kp = float(self.db_select_parameter('P'))
        self.win.spinP.setValue(self.pid.Kp)

        self.pid.Ki = float(self.db_select_parameter('I'))
        self.win.spinI.setValue(self.pid.Ki)

        self.pid.Kd = float(self.db_select_parameter('D'))
        self.win.spinD.setValue(self.pid.Kd)

        for i in range(1, 4, 1):
            r_state = int(self.db_select_parameter('RELAY' + str(i)))
            if i == 1:
                self.win.chkRelay1.setChecked(r_state)
            elif i == 2:
                self.win.chkRelay2.setChecked(r_state)
            elif i == 3:
                self.win.chkRelay3.setChecked(r_state)
            pin = self.io.pin_map['RELAY' + str(i)]
            GPIO.output(pin, not r_state)

    def __init_ui(self):
        self.slide_switch_config()

        self.lcdThermoCouple.setProperty('class', 'lcd')
        self.setProperty('class', 'main_window')
        self.btnStartTest.setProperty('class', 'blue_btn')
        self.btnStopTest.setProperty('class', 'blue_btn')
        self.dialTcFilter.setProperty('class', 'dial')
        self.setWindowTitle("Aux Heater Test")

        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Quit', self.file_quit, QtCore.Qt.CTRL + QtCore.Qt.Key_Q)
        self.menuBar().addMenu(self.file_menu)

        self.help_menu = QtWidgets.QMenu('&Help', self)
        self.menuBar().addSeparator()
        self.menuBar().addMenu(self.help_menu)
        self.help_menu.addAction('&About', self.about)

        self.main_widget = QtWidgets.QWidget(self)
        self.statusBar().showMessage("Running...", 2000)

        self.win.widget_led.value = False
        self.win.widget_led.setProperty('onColour', QLed.Red)
        self.win.widget_led.setProperty('shape', QLed.Square)

    def slide_switch_config(self):

        sw = self.win.slide_bb_pid
        sw._thumb_radius = 11
        sw._track_radius = 13
        sw._margin = max(0, sw._thumb_radius - sw._track_radius)

        sw._base_offset = max(sw._thumb_radius, sw._track_radius)
        sw._end_offset = {
            True: lambda: sw.width() - sw._base_offset,
            False: lambda: sw._base_offset,
        }
        sw._offset = sw._base_offset
        sw.sizeHint()
        palette = sw.palette()
        if sw._thumb_radius > sw._track_radius:
            sw._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            sw._thumb_color = {
                True: palette.highlight(),
                False: palette.light(),
            }
            sw._text_color = {
                True: palette.highlightedText().color(),
                False: palette.dark().color(),
            }
            sw._thumb_text = {
                True: '',
                False: '',
            }
            sw._track_opacity = 0.5
        else:
            sw._thumb_color = {
                True: palette.highlightedText(),
                False: palette.light(),
            }
            sw._track_color = {
                True: palette.highlight(),
                False: palette.dark(),
            }
            sw._text_color = {
                True: palette.highlight().color(),
                False: palette.dark().color(),
            }
            sw._thumb_text = {
                True: '',
                False: '',
            }
            sw._track_opacity = 1

    def __plot_config(self):

        self.plot_opts = {
            'connect': 'all',

            'fftMode': False,
            'logMode': [False, False],
            'alphaHint': 1.0,
            'alphaMode': False,

            'pen': (255, 0, 0),
            'shadowPen': None,
            'fillLevel': None,
            'fillBrush': None,
            'stepMode': None,

            'symbol': 'o',
            'symbolSize': 2,
            'symbolPen': (255, 0, 0),
            'symbolBrush': (255, 0, 0),
            'pxMode': True,

            'antialias': True,
            'pointMode': None,

            'downsample': 1,
            'autoDownsample': False,
            'downsampleMethod': 'peak',
            'autoDownsampleFactor': 5.,  # draw ~5 samples per pixel
            'clipToView': False,

            'data': None,
        }
        self.plot = self.graphicsView.plot(
            connect=self.plot_opts['connect'],
            fftMode=self.plot_opts['fftMode'],
            logMode=self.plot_opts['logMode'],
            alphaHint=self.plot_opts['alphaHint'],
            alphaMode=self.plot_opts['alphaMode'],
            pen=self.plot_opts['pen'],
            shadowPen=self.plot_opts['shadowPen'],
            fillLevel=self.plot_opts['fillLevel'],
            fillBrush=self.plot_opts['fillBrush'],
            stepMode=self.plot_opts['stepMode'],
            symbol=self.plot_opts['symbol'],
            symbolSize=self.plot_opts['symbolSize'],
            symbolPen=self.plot_opts['symbolPen'],
            symbolBrush=self.plot_opts['symbolBrush'],
            pxMode=self.plot_opts['pxMode'],
            antialias=self.plot_opts['antialias'],
            pointMode=self.plot_opts['pointMode'],
            downsample=self.plot_opts['downsample'],
            autoDownsample=self.plot_opts['autoDownsample'],
            downsampleMethod=self.plot_opts['downsampleMethod'],
            autoDownsampleFactor=self.plot_opts['autoDownsampleFactor'],
            clipToView=self.plot_opts['clipToView'],
            data=self.plot_opts['data'],
        )
        self.graphicsView.showGrid(x=True, y=True)
        self.graphicsView.setTitle('<b><font color="blue">Heater Temp Vs Time</font></b>')
        self.graphicsView.setBackground('w')
        # self.graphicsView.enableAutoScale()
        # self.graphicsView.useOpenGL(True)
        # self.graphicsView.addLegend(size=None, offset=(30, 30))
        ax = self.graphicsView.getAxis('bottom')  # This is the trick
        ax.setLabel("<b>Time</b>", "<b>Seconds</b>")
        ax.setGrid(128)  # set x grid intensity 0 to 255
        ax.setStyle(tickLength=10, tickTextOffset=5)
        ax.setLogMode(False)
        ax.setPen('b')
        ay = self.graphicsView.getAxis('left')  # This is the trick
        ay.setLabel("<b>Temperature</b>", "<b>°C</b>")
        ay.setGrid(128)  # set y grid intensity 0 to 255
        ay.setStyle(tickLength=10, tickTextOffset=5)
        ay.setLogMode(False)
        ay.setPen('b')

    def __update_hysteresis(self):
        value = self.win.spinHysteresisC.value()
        self.db_update_parameter("HYSTERESIS", str(value))

    def __tc_filter_change(self):
        value = self.win.dialTcFilter.value()
        self.tc.write_tc_filter_value(value)
        self.db_update_parameter("TC_FILTER", str(value))

    def __relay1_operate(self):
        if self.win.chkRelay1.isChecked():
            relay_state = 1
        else:
            relay_state = 0

        self.db_update_parameter("RELAY1", str(relay_state))

        pin = self.io.pin_map['RELAY1']
        GPIO.output(pin, not relay_state)

    def __relay2_operate(self):
        if self.win.chkRelay2.isChecked():
            relay_state = 1
        else:
            relay_state = 0

        self.db_update_parameter("RELAY2", str(relay_state))

        pin = self.io.pin_map['RELAY2']
        GPIO.output(pin, not relay_state)

    def __relay3_operate(self):
        if self.win.chkRelay3.isChecked():
            relay_state = 1
        else:
            relay_state = 0

        self.db_update_parameter("RELAY3", str(relay_state))

        pin = self.io.pin_map['RELAY3']
        GPIO.output(pin, not relay_state)

    def __set_p(self):
        self.db_update_parameter('P', self.win.spinP.value())

    def __set_i(self):
        self.db_update_parameter('I', self.win.spinI.value())

    def __set_d(self):
        self.db_update_parameter('D', self.win.spinD.value())

    def __update_setpoint(self):
        self.db_update_parameter('SETPT', self.win.spinSetptC.value())

    def __update_duration(self):
        self.db_update_parameter('SECONDS', self.win.spinTestSeconds.value())

    def __update_max_temp(self):
        self.db_update_parameter('MAX_TEMP', self.win.spinMaxTempC.value())

    def file_quit(self):
        self.io.turn_heater_off()
        self.close()

    def closeEvent(self, ce):
        self.io.turn_heater_off()
        self.file_quit()

    def about(self):
        QtWidgets.QMessageBox.about(self, "About",
                                    """<b>Heater Test</b>
                                    PACE INC 7/28/2019
                                    Joe Orndorff
                                    """
                                    )

    def __set_control_mode(self):
        # Using Bang Bang Mode
        if self.win.slide_bb_pid.isChecked() == True:
            self.control_mode = 'bang_bang'
            self.db_update_parameter('MODE', 'bang_bang')
            self.win.spinHysteresisC.show()
            self.win.lblHysteresis.show()
            self.win.spinP.hide()
            self.win.spinI.hide()
            self.win.spinD.hide()
            self.win.lblP.hide()
            self.win.lblI.hide()
            self.win.lblD.hide()
        # Using PID Mode
        else:
            self.control_mode = 'pid'
            self.db_update_parameter('MODE', 'pid')
            self.win.spinHysteresisC.hide()
            self.win.lblHysteresis.hide()
            self.win.spinP.show()
            self.win.spinI.show()
            self.win.spinD.show()
            self.win.lblP.show()
            self.win.lblI.show()
            self.win.lblD.show()

    def start_heater_test(self):
        self.temperature_data.clear()

        self.seconds_elapsed.clear()
        self.seconds_elapsed = [0]
        self.data_idx = 0
        xmax = self.spinTestSeconds.value()
        ymax = self.spinSetptC.value() + 20

        self.graphicsView.setXRange(0, xmax)
        self.graphicsView.setYRange(20, ymax)
        if self.control_mode == 'bang_bang':
            self.timer.timeout.connect(self.__process_bang_bang_loop)
        if self.control_mode == 'pid':
            self.timer.timeout.connect(self.__process_pid_loop)
        self.timer.start(1000)

    def stop_heater_test(self):
        self.timer.stop()
        self.io.turn_heater_off()
        self.win.widget_led.value = False

    def __process_bang_bang_loop(self):

        tempc = self.tc.read_tc()
        self.temperature_data.append(tempc)
        self.win.lcdThermoCouple.display(tempc)
        self.plot.setData(self.seconds_elapsed, self.temperature_data, clear=True)

        self.data_idx += 1
        self.seconds_elapsed.append(self.data_idx)

        proc_error = self.win.spinSetptC.value() - tempc
        control_value = self.pid.GenOut(proc_error)
        print(control_value)

        hysteresis = self.spinHysteresisC.value()
        htr_pwr = self.io.pin_map['HTR_PWR1']

        if GPIO.input(htr_pwr) == 0:  # Heater is off
            if tempc <= self.spinSetptC.value() - (hysteresis / 2):
                self.io.turn_heater_on()
                self.win.widget_led.value = True

        if GPIO.input(htr_pwr) == 1:  # Heater is on
            if tempc >= self.spinSetptC.value() + (hysteresis / 2):
                self.io.turn_heater_off()
                self.win.widget_led.value = False

        if self.data_idx > self.spinTestSeconds.value():
            self.stop_heater_test()

        QApplication.processEvents()

    def __process_pid_loop(self):

        self.pid.Kp = self.win.spinP.value()
        self.pid.Ki = self.win.spinI.value()
        self.pid.Kd = self.win.spinD.value()

        period = 10.0  # PWM period is 10 seconds

        tempc = self.tc.read_tc()
        self.temperature_data.append(tempc)
        self.win.lcdThermoCouple.display(tempc)
        self.plot.setData(self.seconds_elapsed, self.temperature_data, clear=True)

        self.data_idx += 1
        self.seconds_elapsed.append(self.data_idx)

        htr_pwr = self.io.pin_map['HTR_PWR1']

        if self.data_idx % 10 == 0 or self.data_idx == 0:
            error = self.win.spinSetptC.value() - tempc
            correction = self.pid.GenOut(error)
            self.win.lblPidCorrection.setText("{:.1f}".format(correction))

            control_percent = (correction / self.win.spinSetptC.value()) * 100

            self.win.lblPidControlPercent.setText("{:.1f}".format(control_percent))

            self.duty_cycle = (control_percent / 100) * period

        i = self.data_idx % 10
        print(i)
        if i <= self.duty_cycle:
            GPIO.output(htr_pwr, 1)
            self.win.widget_led.value = True
        else:
            GPIO.output(htr_pwr, 0)
            self.win.widget_led.value = False

        if self.data_idx > self.spinTestSeconds.value():
            self.stop_heater_test()

        QApplication.processEvents()

    def db_update_parameter(self, parameter, value):
        query = QSqlQuery(self.db)
        qrytxt = ('UPDATE tblParameters '
                  'SET VALUE = \'{v}\' '
                  'WHERE PARAMETER = \'{p}\'') \
            .format(v=value, p=parameter)
        query.exec(qrytxt)

    def db_select_parameter(self, parameter):
        query = QSqlQuery(self.db)
        qrytxt = ("SELECT VALUE from tblParameters WHERE PARAMETER = '{p}'") \
            .format(p=parameter)

        query.exec(qrytxt)
        lst = []
        while query.next():
            lst.append(query.value(0))
        return lst[0]
