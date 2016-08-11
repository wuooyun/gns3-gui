# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import shutil

from gns3.qt import QtCore, QtWidgets, QtGui, QtNetwork
from gns3.controller import Controller
from gns3.gns3_vm import GNS3VM
from gns3.local_server import LocalServer
from gns3.utils.progress_dialog import ProgressDialog
from gns3.utils.wait_for_connection_worker import WaitForConnectionWorker

from ..ui.setup_wizard_ui import Ui_SetupWizard
from ..version import __version__


class SetupWizard(QtWidgets.QWizard, Ui_SetupWizard):

    """
    Base class for VM wizard.
    """

    def __init__(self, parent):

        super().__init__(parent)
        self.setupUi(self)

        self.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        if sys.platform.startswith("darwin"):
            # we want to see the cancel button on OSX
            self.setOptions(QtWidgets.QWizard.NoDefaultButton)

        self.uiGNS3VMDownloadLinkUrlLabel.setText('')
        self.uiRefreshPushButton.clicked.connect(self._refreshVMListSlot)
        self.uiVmwareRadioButton.clicked.connect(self._listVMwareVMsSlot)
        self.uiVirtualBoxRadioButton.clicked.connect(self._listVirtualBoxVMsSlot)
        self.uiVMwareBannerButton.clicked.connect(self._VMwareBannerButtonClickedSlot)
        settings = parent.settings()
        self.uiShowCheckBox.setChecked(settings["hide_setup_wizard"])

        # by default all radio buttons are unchecked
        self.uiVmwareRadioButton.setAutoExclusive(False)
        self.uiVirtualBoxRadioButton.setAutoExclusive(False)
        self.uiVmwareRadioButton.setChecked(False)
        self.uiVirtualBoxRadioButton.setChecked(False)

        # Mandatory fields
        self.uiLocalServerWizardPage.registerField("path*", self.uiLocalServerPathLineEdit)

        # load all available addresses
        for address in QtNetwork.QNetworkInterface.allAddresses():
            address_string = address.toString()
            # if address.protocol() == QtNetwork.QAbstractSocket.IPv6Protocol:
            # we do not want the scope id when using an IPv6 address...
            # address.setScopeId("")
            self.uiLocalServerHostComboBox.addItem(address_string, address.toString())

        if sys.platform.startswith("darwin"):
            self.uiVMwareBannerButton.setIcon(QtGui.QIcon(":/images/vmware_fusion_banner.jpg"))
        else:
            self.uiVMwareBannerButton.setIcon(QtGui.QIcon(":/images/vmware_workstation_banner.jpg"))

    def _localServerBrowserSlot(self):
        """
        Slot to open a file browser and select a local server.
        """

        filter = ""
        if sys.platform.startswith("win"):
            filter = "Executable (*.exe);;All files (*.*)"
        server_path = shutil.which("gns3server")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select the local server", server_path, filter)
        if not path:
            return

        self.uiLocalServerPathLineEdit.setText(path)

    def _VMwareBannerButtonClickedSlot(self):
        if sys.platform.startswith("darwin"):
            url = "http://send.onenetworkdirect.net/z/616461/CD225091/"
        else:
            url = "http://send.onenetworkdirect.net/z/616460/CD225091/"
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _listVMwareVMsSlot(self):
        """
        Slot to refresh the VMware VMs list.
        """

        download_url = "https://github.com/GNS3/gns3-gui/releases/download/v{version}/GNS3.VM.VMware.Workstation.{version}.zip".format(version=__version__)
        self.uiGNS3VMDownloadLinkUrlLabel.setText('The GNS3 VM can <a href="{download_url}">downloaded here</a>.<br>Import the VM in your virtualization software and hit refresh.'.format(download_url=download_url))
        self.uiVirtualBoxRadioButton.setChecked(False)
        from gns3.modules import VMware
        settings = VMware.instance().settings()
        if not os.path.exists(settings["vmrun_path"]):
            QtWidgets.QMessageBox.critical(self, "VMware", "VMware vmrun tool could not be found, VMware or the VIX API (required for VMware player) is probably not installed. You can download it from https://www.vmware.com/support/developer/vix-api/")
            return
        self._refreshVMListSlot()

    def _listVirtualBoxVMsSlot(self):
        """
        Slot to refresh the VirtualBox VMs list.
        """

        QtWidgets.QMessageBox.warning(self, "GNS3 VM on VirtualBox", "VirtualBox doesn't support nested virtualization, this means running Qemu based VM could be very slow")
        download_url = "https://github.com/GNS3/gns3-gui/releases/download/v{version}/GNS3.VM.VirtualBox.{version}.zip".format(version=__version__)
        self.uiGNS3VMDownloadLinkUrlLabel.setText('If you don\'t have the GNS3 Virtual Machine you can <a href="{download_url}">download it here</a>.<br>And import the VM in the virtualization software and hit refresh.'.format(download_url=download_url))
        self.uiVmwareRadioButton.setChecked(False)
        from gns3.modules import VirtualBox
        settings = VirtualBox.instance().settings()
        if not os.path.exists(settings["vboxmanage_path"]):
            QtWidgets.QMessageBox.critical(self, "VirtualBox", "VBoxManage could not be found, VirtualBox is probably not installed")
            return
        self._refreshVMListSlot()

    def _setPreferencesPane(self, dialog, name):
        """
        Finds the first child of the QTreeWidgetItem name.

        :param dialog: PreferencesDialog instance
        :param name: QTreeWidgetItem name

        :returns: current QWidget
        """

        pane = dialog.uiTreeWidget.findItems(name, QtCore.Qt.MatchFixedString)[0]
        child_pane = pane.child(0)
        dialog.uiTreeWidget.setCurrentItem(child_pane)
        return dialog.uiStackedWidget.currentWidget()

    def initializePage(self, page_id):
        """
        Initialize Wizard pages.

        :param page_id: page identifier
        """

        super().initializePage(page_id)
        gns3_vm = GNS3VM().instance(parent=self)
        gns3_vm_settings = gns3_vm.settings()
        if self.page(page_id) == self.uiVMWizardPage:
            if not gns3_vm_settings:
                QtWidgets.QMessageBox.critical(self, "GNS3 VM", "Could not retrieve the GNS3 VM settings from the controller")
                return
            if gns3_vm_settings["engine"] == "vmware":
                self.uiVmwareRadioButton.setChecked(True)
                self._listVMwareVMsSlot()
            elif gns3_vm_settings["engine"] == "virtualbox":
                self.uiVirtualBoxRadioButton.setChecked(True)
                self._listVirtualBoxVMsSlot()
            self.uiCPUSpinBox.setValue(gns3_vm_settings["vcpus"])
            self.uiRAMSpinBox.setValue(gns3_vm_settings["ram"])

        elif self.page(page_id) == self.uiLocalServerWizardPage:
            local_server_settings = LocalServer.instance().localServerSettings()
            self.uiLocalServerPathLineEdit.setText(local_server_settings["path"])
            index = self.uiLocalServerHostComboBox.findData(local_server_settings["host"])
            if index != -1:
                self.uiLocalServerHostComboBox.setCurrentIndex(index)
            self.uiLocalServerPortSpinBox.setValue(local_server_settings["port"])

        elif self.page(page_id) == self.uiSummaryWizardPage:
            use_local_server = self.uiLocalRadioButton.isChecked()
            self.uiSummaryTreeWidget.clear()
            if use_local_server:
                local_server_settings = LocalServer.instance().localServerSettings()
                self._addSummaryEntry("Server type:", "Local")
                self._addSummaryEntry("Path:", local_server_settings["path"])
                self._addSummaryEntry("Host:", local_server_settings["host"])
                self._addSummaryEntry("Port:", str(local_server_settings["port"]))
            else:
                self._addSummaryEntry("Server type:", "GNS3 Virtual Machine")
                self._addSummaryEntry("VM engine:", gns3_vm_settings["engine"].capitalize())
                self._addSummaryEntry("VM name:", gns3_vm_settings["vmname"])
                self._addSummaryEntry("VM vCPUs:", str(gns3_vm_settings["vcpus"]))
                self._addSummaryEntry("VM RAM:", str(gns3_vm_settings["ram"]) + " MB")

    def _addSummaryEntry(self, name, value):

        item = QtWidgets.QTreeWidgetItem(self.uiSummaryTreeWidget, [name, value])
        item.setText(0, name)
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

    def validateCurrentPage(self):
        """
        Validates the settings.
        """

        gns3_vm = GNS3VM().instance(parent=self)
        if self.currentPage() == self.uiVMWizardPage:
            vmname = self.uiVMListComboBox.currentText()
            if vmname:
                # save the GNS3 VM settings
                vm_settings = {"vmname": vmname,
                               "auto_start": True}

                if self.uiVmwareRadioButton.isChecked():
                    vm_settings["engine"] = "vmware"
                elif self.uiVirtualBoxRadioButton.isChecked():
                    vm_settings["engine"] = "virtualbox"

                # set the vCPU count and RAM
                vpcus = self.uiCPUSpinBox.value()
                ram = self.uiRAMSpinBox.value()
                if ram < 1024:
                    QtWidgets.QMessageBox.warning(self, "GNS3 VM memory", "It is recommended to allocate a minimum of 1024 MB of memory to the GNS3 VM")
                vm_settings["vcpus"] = vpcus
                vm_settings["ram"] = ram

                # update the GNS3 VM
                gns3_vm.update(vm_settings)

                # start the GNS3 VM
                gns3_vm.start()

            else:
                if not self.uiVmwareRadioButton.isChecked() and not self.uiVirtualBoxRadioButton.isChecked():
                    QtWidgets.QMessageBox.warning(self, "GNS3 VM", "Please select VMware or VirtualBox")
                else:
                    QtWidgets.QMessageBox.warning(self, "GNS3 VM", "Please select a VM. If no VM is listed, check if the GNS3 VM is correctly imported and press refresh.")
                return False

        elif self.currentPage() == self.uiLocalServerWizardPage:

            local_server_settings = LocalServer.instance().localServerSettings()
            local_server_settings["auto_start"] = True
            local_server_settings["path"] = self.uiLocalServerPathLineEdit.text().strip()
            local_server_settings["host"] = self.uiLocalServerHostComboBox.itemData(self.uiLocalServerHostComboBox.currentIndex())
            local_server_settings["port"] = self.uiLocalServerPortSpinBox.value()

            if not os.path.isfile(local_server_settings["path"]):
                QtWidgets.QMessageBox.critical(self, "Local server", "Could not find local server {}".format(local_server_settings["path"]))
                return False
            if not os.access(local_server_settings["path"], os.X_OK):
                QtWidgets.QMessageBox.critical(self, "Local server", "{} is not an executable".format(local_server_settings["path"]))
                return False

            LocalServer.instance().setLocalServerSettings(local_server_settings)
            print(local_server_settings)
            LocalServer.instance().stopLocalServer(wait=True)
            if LocalServer.instance().startLocalServer():
                worker = WaitForConnectionWorker(local_server_settings["host"], local_server_settings["port"])
                dialog = ProgressDialog(worker, "Local server", "Connecting...", "Cancel", busy=True, parent=self)
                dialog.show()
                dialog.exec_()
                Controller.instance().setHttpClient(LocalServer.instance().httpClient())
            else:
                QtWidgets.QMessageBox.critical(self, "Local server", "Could not start the local server process: {}".format(local_server_settings["path"]))

        elif self.currentPage() == self.uiSummaryWizardPage:
            use_local_server = self.uiLocalRadioButton.isChecked()
            if use_local_server:
                # deactivate the GNS3 VM if using the local server
                vm_settings = {"auto_start": False}
                gns3_vm.update(vm_settings)

            # update the modules so they use the local server
            from gns3.modules import Dynamips
            Dynamips.instance().setSettings({"use_local_server": use_local_server})
            if sys.platform.startswith("linux"):
                # IOU only works on Linux
                from gns3.modules import IOU
                IOU.instance().setSettings({"use_local_server": use_local_server})
            from gns3.modules import Qemu
            Qemu.instance().setSettings({"use_local_server": use_local_server})
            from gns3.modules import VPCS
            VPCS.instance().setSettings({"use_local_server": use_local_server})

        return True

    def _refreshVMListSlot(self):
        """
        Refresh the list of VM available in VMware or VirtualBox.
        """

        if self.uiVmwareRadioButton.isChecked():
            Controller.instance().get("/gns3vm/vmware/vms", self._getVMsFromServerCallback, progressText="Retrieving VMware VM list from server...")
        elif self.uiVirtualBoxRadioButton.isChecked():
            Controller.instance().get("/gns3vm/virtualbox/vms", self._getVMsFromServerCallback, progressText="Retrieving VirtualBox VM list from server...")

    def _getVMsFromServerCallback(self, result, error=False, **kwargs):
        """
        Callback for getVMsFromServer.

        :param progress_dialog: QProgressDialog instance
        :param result: server response
        :param error: indicates an error (boolean)
        """

        if error:
            QtWidgets.QMessageBox.critical(self, "VM List", "{}".format(result["message"]))
        else:
            self.uiVMListComboBox.clear()
            for vm in result:
                self.uiVMListComboBox.addItem(vm["vmname"])

            gns3_vm = GNS3VM().instance().settings()
            index = self.uiVMListComboBox.findText(gns3_vm["vmname"])
            if index != -1:
                self.uiVMListComboBox.setCurrentIndex(index)
            else:
                index = self.uiVMListComboBox.findText("GNS3 VM")
                if index != -1:
                    self.uiVMListComboBox.setCurrentIndex(index)
                else:
                    QtWidgets.QMessageBox.critical(self, "GNS3 VM", "Could not find a VM named 'GNS3 VM', is it imported in VMware or VirtualBox?")

    def done(self, result):
        """
        This dialog is closed.

        :param result: ignored
        """

        settings = self.parentWidget().settings()
        settings["hide_setup_wizard"] = self.uiShowCheckBox.isChecked()
        self.parentWidget().setSettings(settings)
        super().done(result)

    def nextId(self):
        """
        Wizard rules!
        """

        current_id = self.currentId()
        if self.page(current_id) == self.uiServerWizardPage and self.uiVMRadioButton.isChecked():
            # skip the local server page if using the GNS3 VM
            return self.uiLocalServerWizardPage.nextId()
        if self.page(current_id) == self.uiLocalServerWizardPage:
            return self.uiVMWizardPage.nextId()
        return QtWidgets.QWizard.nextId(self)
