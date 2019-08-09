import quieres


class MCP9600(object):


    def __init__(self, db, i2c_bus):

        self.db = db
        self.i2c_addr = 0x66
        self.i2c_bus = i2c_bus
        self.registers = []
        self.__mcp9600_initialize()

    def __mcp9600_initialize(self):
        # Read register table from database and store it in a list of dictionaries
        self.registers = quieres.db_table_data_to_dictionary(self.db, 'tblMcp9600_Registers')
        for register in self.registers:
            self.__mcp9600_write_word(register['NAME'], register['VALUE'])
            if register['NAME'] == 'ThermocoupleSensorConfiguration':
                data_16 = self.__mcp9600_read_word(register['NAME'])
                UpperByte = data_16[1]
                LowerByte = data_16[0]
                value = UpperByte << 8 | LowerByte

                print(value)


    def mcp9600_read_id(self):
        data_16 = self.__mcp9600_read_word('DeviceId')
        chip_id = data_16[0]

        try:
            if chip_id != 0x40:
                raise RuntimeError("Unable to find mcp9600 on 0x{:02x}, CHIP_ID returned {:02x}".format(self.i2c_addr, chip_id))
        except IOError:
            raise RuntimeError("Unable to find mcp9600 on 0x{:02x}, IOError".format(self.i2c_addr))
        return chip_id

    def read_tc(self):
        data_16 = self.__mcp9600_read_word('ThermocoupleHotJunction')
        UpperByte = data_16[1]
        LowerByte = data_16[0]
        if LowerByte & 0x80 == 0x80: # Tempearture < 0C
            temperature = (((LowerByte * 16.0) + (UpperByte/16.0))) - 4096.0
        else: # Temperature >= 0C
            temperature = ((LowerByte * 16.0) + (UpperByte/16.0))
        return temperature

    def read_tc_filter(self):
        data_16 = self.__mcp9600_read_word('ThermocoupleSensorConfiguration')
        UpperByte = data_16[1]
        LowerByte = data_16[0]
        filter_setting = LowerByte & 0x07
        return filter_setting

    def write_tc_filter_value(self, value):
        data_16 = self.__mcp9600_read_word('ThermocoupleHotJunction')
        UpperByte = data_16[1]
        LowerByte = data_16[0]
        LowerByte = LowerByte & 0xF8
        LowerByte - LowerByte | value
        data_16 = UpperByte << 8 | LowerByte

        self.__mcp9600_write_word('ThermocoupleHotJunction', data_16)


    def __search_reg_address_from_name(self, reg_name):
        for register in self.registers:
            if register['NAME'] == reg_name:
                return register['ADDRESS']
        return 0

    def __mcp9600_read_word(self, reg_name):
        reg_add = self.__search_reg_address_from_name(reg_name)
        data_16 = self.i2c_bus.read_i2c_block_data(self.i2c_addr, reg_add, 2)
        return data_16

    def __mcp9600_write_word(self, reg_name, data_16):
        reg_add = self.__search_reg_address_from_name(reg_name)
        self.i2c_bus.write_word_data(self.i2c_addr, reg_add, data_16)

