# -*- coding: utf-8 -*-

# Discovery Plugin
#
# Copyright (C) 2015 Lutra Consulting
# info@lutraconsulting.co.uk
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

import dbutils

plugin_dir = os.path.dirname(__file__)

uiConfigDialog, qtBaseClass = uic.loadUiType(os.path.join(plugin_dir, 'config_dialog.ui'))



class ConfigDialog(qtBaseClass, uiConfigDialog):

    def __init__(self, config_combo, parent=None):
        qtBaseClass.__init__(self, parent)
        self.setupUi(self)

        self.conn = None
        self.key = ""  # currently selected config key
        self.config_combo = config_combo

        # signals
        self.buttonBox.button(QDialogButtonBox.Help).clicked.connect(self.show_help)
        self.addButton.clicked.connect(self.add_config)
        self.deleteButton.clicked.connect(self.delete_config)
        self.configListW.currentRowChanged.connect(self.config_selection_changed)

        settings = QSettings()
        settings.beginGroup("/Discovery")

        # init config list
        if not settings.value("config_list"):
            settings.setValue("config_list", [])
        config_list = settings.value("config_list")

        for key in config_list:
            item = QListWidgetItem(key)
            self.configListW.addItem(item)

        if self.configListW.count():
            self.configListW.setCurrentRow(0)

        key = self.configListW.currentItem().text() if self.configListW.currentItem() else ""
        if not self.configListW.count():
            self.enable_form(False)
        self.set_form_fields(key)
        self.chkMarkerTime.stateChanged.connect(self.time_checkbox_changed)

    def set_form_fields(self, key = ""):

        QApplication.setOverrideCursor(Qt.WaitCursor)
        settings = QSettings()
        settings.beginGroup("/Discovery")

        if key:
            self.cboName.setText(key)
        else:
            self.cboName.setText("")
        # connections
        for conn in dbutils.get_postgres_connections():
            self.cboConnection.addItem(conn)
        self.init_combo_from_settings(self.cboConnection, key + "connection")
        self.cboConnection.currentIndexChanged.connect(self.connect_db)
        self.connect_db()
        # schemas
        self.init_combo_from_settings(self.cboSchema, key + "schema")
        self.cboSchema.currentIndexChanged.connect(self.populate_tables)
        self.populate_tables()
        # tables
        self.init_combo_from_settings(self.cboTable, key + "table")
        self.cboTable.currentIndexChanged.connect(self.populate_columns)
        self.populate_columns()
        # columns
        self.init_combo_from_settings(self.cboSearchColumn, key + "search_column")
        self.init_combo_from_settings(self.cboGeomColumn, key + "geom_column")
        echo_search_col = settings.value(key + "echo_search_column", True, type=bool)
        if echo_search_col:
            self.cbEchoSearchColumn.setCheckState(Qt.Checked)
        else:
            self.cbEchoSearchColumn.setCheckState(Qt.Unchecked)
        columns = settings.value(key + "display_columns", "", type=str)
        if len(columns) != 0:
            lst = columns.split(",")
            self.set_combo_current_text(self.cboDisplayColumn1, lst[0])
            if len(lst) > 1:
                self.set_combo_current_text(self.cboDisplayColumn2, lst[1])
            if len(lst) > 2:
                self.set_combo_current_text(self.cboDisplayColumn3, lst[2])
            if len(lst) > 3:
                self.set_combo_current_text(self.cboDisplayColumn4, lst[3])
            if len(lst) > 4:
                self.set_combo_current_text(self.cboDisplayColumn5, lst[4])
        self.editScaleExpr.setText(settings.value(key + "scale_expr", "", type=str))
        self.editBboxExpr.setText(settings.value(key + "bbox_expr", "", type=str))
        self.chkMarkerTime.setChecked(settings.value(key + "marker_time_enabled", True, type=bool))
        self.spinMarkerTime.setValue(settings.value(key + "marker_time", 5000, type=int) / 1000)
        self.time_checkbox_changed()

        QApplication.restoreOverrideCursor()


    def init_combo_from_settings(self, cbo, settings_key):
        settings = QSettings()
        settings.beginGroup("/Discovery")
        name = settings.value(settings_key, "", type=str)
        self.set_combo_current_text(cbo, name)

    def set_combo_current_text(self, cbo, name):
        idx = cbo.findText(name)
        cbo.setCurrentIndex(idx) if idx != -1 else cbo.setEditText(name)

    def connect_db(self):
        name = self.cboConnection.currentText()
        try:
            self.conn = dbutils.get_connection(dbutils.get_postgres_conn_info(name))
            self.lblMessage.setText("")
        except StandardError, e:
            self.conn = None
            self.lblMessage.setText("<font color=red>"+ e.message +"</font>")
        self.populate_schemas()

    def populate_schemas(self):
        self.cboSchema.clear()
        self.cboSchema.addItem('')
        if self.conn is None: return
        for schema in dbutils.list_schemas(self.conn.cursor()):
            self.cboSchema.addItem(schema)

    def populate_tables(self):
        self.cboTable.clear()
        self.cboTable.addItem('')
        if self.conn is None: return
        for table in dbutils.list_tables(self.conn.cursor(), self.cboSchema.currentText()):
            self.cboTable.addItem(table)

    def populate_columns(self):
        cbos = [self.cboSearchColumn, self.cboGeomColumn, self.cboDisplayColumn1, self.cboDisplayColumn2,
                self.cboDisplayColumn3, self.cboDisplayColumn4, self.cboDisplayColumn5]
        for cbo in cbos:
            cbo.clear()
            cbo.addItem("")
        if self.conn is None: return
        columns = dbutils.list_columns(self.conn.cursor(), self.cboSchema.currentText(), self.cboTable.currentText())
        for cbo in cbos:
            for column in columns:
                cbo.addItem(column)

    def delete_config_from_settings(self, key, settings):
        settings.remove(key + "connection")
        settings.remove(key + "schema")
        settings.remove(key + "table")
        settings.remove(key + "search_column")
        settings.remove(key + "echo_search_column")
        settings.remove(key + "display_columns")
        settings.remove(key + "geom_column")
        settings.remove(key + "scale_expr")
        settings.remove(key + "bbox_expr")
        settings.remove(key + "marker_time_enabled")
        settings.remove(key + "marker_time")


    def validate_key(self, key, config_list):

        if len(key) <= 3: return False
        if key in config_list: return False




        return True

    def write_config(self):

        settings = QSettings()
        settings.beginGroup("/Discovery")

        config_list = settings.value("config_list")
        if not config_list:
            config_list = []

        key = self.cboName.text()

        self.validate_key(key, config_list)

        if self.key != key:

            if not self.validate_key(key, config_list):
                # TODO show unvalid key
                return

            if self.key in config_list:
                config_list.remove(self.key)
            self.config_combo.removeItem(self.configListW.currentRow())
            self.delete_config_from_settings(self.key, settings)
            self.key = key

        if key not in config_list:
            config_list.append(key)
            settings.setValue("config_list", config_list)

        all_items = [self.config_combo.itemText(i) for i in range(self.config_combo.count())]
        if key not in all_items:
            self.config_combo.addItem(key)

        settings.setValue(key + "connection", self.cboConnection.currentText())
        settings.setValue(key + "schema", self.cboSchema.currentText())
        settings.setValue(key + "table", self.cboTable.currentText())
        settings.setValue(key + "search_column", self.cboSearchColumn.currentText())
        settings.setValue(key + "echo_search_column", self.cbEchoSearchColumn.isChecked())
        settings.setValue(key + "display_columns", self.display_columns())
        settings.setValue(key + "geom_column", self.cboGeomColumn.currentText())
        settings.setValue(key + "scale_expr", self.editScaleExpr.text())
        settings.setValue(key + "bbox_expr", self.editBboxExpr.text())
        settings.setValue(key + "marker_time_enabled", self.chkMarkerTime.isChecked())
        settings.setValue(key + "marker_time", self.spinMarkerTime.value()*1000)


    def time_checkbox_changed(self):
        self.spinMarkerTime.setEnabled(self.chkMarkerTime.isChecked())

    def display_columns(self):
        """ Make a string out of display columns, e.g. "column1,column2" or just "column1"
        """
        lst = []
        for cbo in [self.cboDisplayColumn1, self.cboDisplayColumn2, self.cboDisplayColumn3, self.cboDisplayColumn4,
                    self.cboDisplayColumn5]:
            txt = cbo.currentText()
            if len(txt) > 0:
                lst.append(txt)
        return ",".join(lst)

    def enable_form(self, enable = True):
        # TODO put all to one widget and enable/disable only it
        #self.formLayout.setEnabled(enable)
        self.cboName.setEnabled(enable)
        self.cboConnection.setEnabled(enable)
        self.cboSchema.setEnabled(enable)
        self.cboTable.setEnabled(enable)
        self.cboSearchColumn.setEnabled(enable)
        self.cbEchoSearchColumn.setEnabled(enable)
        self.cboDisplayColumn1.setEnabled(enable)
        self.cboDisplayColumn2.setEnabled(enable)
        self.cboDisplayColumn3.setEnabled(enable)
        self.cboDisplayColumn4.setEnabled(enable)
        self.cboDisplayColumn5.setEnabled(enable)
        self.cboGeomColumn.setEnabled(enable)
        self.editScaleExpr.setEnabled(enable)
        self.editBboxExpr.setEnabled(enable)
        self.chkMarkerTime.setEnabled(enable)
        self.spinMarkerTime.setEnabled(enable)

    def add_config(self):
        txt = "New config"
        item = QListWidgetItem(txt)
        self.configListW.addItem(item)
        self.configListW.setCurrentItem(item)
        self.config_combo.addItem(txt)

        settings = QSettings()
        settings.beginGroup("/Discovery")
        config_list = settings.value("config_list")
        if not (config_list):
            config_list = []
            self.enable_form()
        config_list.append(txt)
        settings.setValue("config_list", config_list)

        # reset fields
        self.set_form_fields()
        self.cboName.setText(txt)
        self.key = txt


    # TODO ask if really wanted to delete
    def delete_config(self):
        if self.configListW.currentItem():
            self.config_combo.removeItem(self.configListW.currentRow())
            item_text = self.configListW.currentItem().text()
            item = self.configListW.takeItem(self.configListW.currentRow())
            del item

            settings = QSettings()
            settings.beginGroup("/Discovery")
            config_list = settings.value("config_list")
            config_list.remove(item_text)
            settings.setValue("config_list", config_list)

            if (self.configListW.count()):
                self.configListW.setCurrentRow(0)
            else:
                self.enable_form(False)
                self.key = ""


    def config_selection_changed(self):
        if not self.configListW.count(): return

        self.key = self.configListW.currentItem().text()
        index = self.config_combo.findData(self.key)
        if (index != -1):
            self.config_combo.setCurrentIndex(index)
        self.set_form_fields(self.key)

    def show_help(self):
        QDesktopServices.openUrl(QUrl("http://www.lutraconsulting.co.uk/products/discovery/"))
