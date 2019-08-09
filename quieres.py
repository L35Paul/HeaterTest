from PyQt5.QtCore import *
from PyQt5.QtSql import QSqlQuery

def db_fetch_tablenames(db):
    query = QSqlQuery(db)
    qrytxt = ("SELECT name FROM sqlite_master "
              "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
              "UNION ALL "
              "SELECT name FROM sqlite_temp_master "
              "WHERE type IN ('table','view') ORDER BY 1")
    query.exec_(qrytxt)
    list = []
    while query.next():
        list.append(query.value(0))
    return list

def db_fetch_table_fields(db, tblname):
    query = QSqlQuery(db)
    qrytxt = "pragma table_info({tn})".format(tn=tblname)
    query.exec_(qrytxt)
    tblheader = []
    while query.next():
        tblheader.append(query.value(1))
    return tblheader

def db_fetch_table_data(db, tblname):
    query = QSqlQuery(db)
    query.exec_("SELECT * FROM " + tblname)
    data_list = []
    while query.next():
        i = 0
        data = {}
        while query.value(i) is not None:
            data[i] = query.value(i)
            i += 1
        data_list.append(data)
    return data_list

def db_table_data_to_dictionary(db, tblname):
    query = QSqlQuery(db)
    query.exec_("SELECT * FROM " + tblname)
    data_list = []
    column_names = db_fetch_table_fields(db, tblname)
    data_dict = {}
    i = 0
    while query.next():
        for i in range(len(column_names)):
            data_dict[column_names[i]] = query.value(i)
        data_list.append(data_dict)
        data_dict = {}

    return data_list

def db_register_data_to_dictionary(db, regname, tbl_regs, tbl_bits):

    query = QSqlQuery(db)
    qrytxt = "select {name}, {mask}, {shift}, {value} ,{parent} from {tn1} inner join {tn2} on " \
             "{parent} = {tn2}.ADDRESS where {tn2}.NAME = '{rn}'" \
        .format(name=tbl_bits + ".NAME", mask=tbl_bits + ".MASK", shift=tbl_bits + ".SHIFT",
                value=tbl_bits + ".VALUE", parent=tbl_bits + ".FK_PARENT_ID", tn1=tbl_bits,
                tn2=tbl_regs, rn=regname)
    data_dict = {}
    data = []
    query.exec_(qrytxt)

    while query.next():
        data_dict["NAME"] = query.value(0)
        data_dict["MASK"] = query.value(1)
        data_dict["SHIFT"] = query.value(2)
        data_dict["VALUE"] = query.value(3)
        data_dict["PK_PAPRENT_ID"] = query.value(4)

        data.append(data_dict)
        data_dict = {}
    return data

def db_fetch_names_n_values(db, regname, tbl_regs, tbl_bits ):
    # Retrieve sub register names and values for a given register.
    query = QSqlQuery(db)

    qrytxt = "select {name}, {value} from {tn1} inner join {tn2} on {parent} = {tn2}.ADDRESS " \
             "where {tn2}.NAME = '{rn}'".format(name=tbl_bits + ".NAME",
                                                value=tbl_bits + ".VALUE",
                                                tn1=tbl_bits, parent=tbl_bits + ".FK_PARENT_ID",
                                                rn=regname, tn2=tbl_regs)
    query.exec_(qrytxt)
    regdict = {}

    while query.next():
        regdict[query.value(0)] = query.value(1)

    return regdict


class DbTableModel(QAbstractTableModel):


    def __init__(self, datain, headerdata, parent=None):
        """
        Args:
            datain: a list of lists\n
            headerdata: a list of strings
        """
        QAbstractTableModel.__init__(self, parent)
        self.arraydata = datain
        self.headerdata = headerdata

    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        if len(self.arraydata) > 0:
            return len(self.arraydata[0])
        return 0

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return str(self.arraydata[index.row()][index.column()])

    def setData(self, index, value, role):
        pass         # not sure what to put here

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self.headerdata[col])
        return None

    def sort(self, ncol, order):
        """
        Sort table by given column number.
        """
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.arraydata = sorted(self.arraydata, key=operator.itemgetter(ncol))
        if order == Qt.DescendingOrder:
            self.arraydata.reverse()
        self.emit(SIGNAL("layoutChanged()"))


def config_table(tv, tblheader, tabledata):
    # set the table model
    tablemodel = DbTableModel(tabledata, tblheader)
    tv.setModel(tablemodel)
    # set the minimum size
    tv.setMinimumSize(400, 300)
    # hide grid
    tv.setShowGrid(True)
    # hide vertical header
    vh = tv.verticalHeader()
    vh.setVisible(False)
    # set horizontal header properties
    hh = tv.horizontalHeader()
    hh.setStretchLastSection(True)
    # set column width to fit contents
    tv.resizeColumnsToContents()
    # set row height
    tv.resizeRowsToContents()
    # enable sorting
    tv.setSortingEnabled(False)
