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

"""
Wizard for IOS routers.
"""

import os
import re

from gns3.qt import QtGui
from gns3.servers import Servers

from ..ui.ios_router_wizard_ui import Ui_IOSRouterWizard
from ..settings import PLATFORMS_DEFAULT_RAM, CHASSIS, ADAPTER_MATRIX, WIC_MATRIX
from .. import Dynamips


class IOSRouterWizard(QtGui.QWizard, Ui_IOSRouterWizard):
    """
    Wizard to create an IOS router.

    :param parent: parent widget
    """

    def __init__(self, parent):

        QtGui.QWizard.__init__(self, parent)
        self.setupUi(self)
        self.setPixmap(QtGui.QWizard.LogoPixmap, QtGui.QPixmap(":/symbols/router.normal.svg"))
        self.setWizardStyle(QtGui.QWizard.ModernStyle)

        self.uiIOSImageToolButton.clicked.connect(self._iosImageBrowserSlot)
        self.uiIdlePCFinderPushButton.clicked.connect(self._idlePCFinderSlot)
        self.uiPlatformComboBox.currentIndexChanged[str].connect(self._platformChangedSlot)
        self.uiPlatformComboBox.addItems(list(PLATFORMS_DEFAULT_RAM.keys()))

        # Mandatory fields
        self.uiNameImageWizardPage.registerField("name*", self.uiNameLineEdit)
        self.uiNameImageWizardPage.registerField("image*", self.uiIOSImageLineEdit)

        self._widget_slots = {0: self.uiSlot0comboBox,
                              1: self.uiSlot1comboBox,
                              2: self.uiSlot2comboBox,
                              3: self.uiSlot3comboBox,
                              4: self.uiSlot4comboBox,
                              5: self.uiSlot5comboBox,
                              6: self.uiSlot6comboBox}

        self._widget_wics = {0: self.uiWic0comboBox,
                             1: self.uiWic1comboBox,
                             2: self.uiWic2comboBox}

    def _platformChangedSlot(self, platform):
        """
        Updates the chassis comboBox based on the selected platform.

        :param platform: selected router platform
        """

        self.uiChassisComboBox.clear()
        if platform in CHASSIS:
            self.uiChassisComboBox.addItems(CHASSIS[platform])

    def _idlePCFinderSlot(self):

        QtGui.QMessageBox.critical(self, "Idle-PC", "Sorry, this hasn't been implemented yet")

    def _iosImageBrowserSlot(self):
        """
        Slot to open a file browser and select an IOU image.
        """

        from ..pages.ios_router_preferences_page import IOSRouterPreferencesPage
        path = IOSRouterPreferencesPage.getIOSImage(self)
        if not path:
            return
        self.uiIOSImageLineEdit.clear()
        self.uiIOSImageLineEdit.setText(path)

        # try to guess the platform
        image = os.path.basename(path)
        match = re.match("^(c[0-9]+)\\-\w+", image)
        if not match:
            QtGui.QMessageBox.warning(self, "IOS image", "Could not detect the platform, make sure this is a valid IOS image!")
            return

        detected_platform = match.group(1)
        detected_chassis = ""
        # IOS images for the 3600 platform start with the chassis name (c3620 etc.)
        for platform, chassis in CHASSIS.items():
            if detected_platform[1:] in chassis:
                detected_chassis = detected_platform[1:]
                detected_platform = platform
                break

        if detected_platform not in PLATFORMS_DEFAULT_RAM:
            QtGui.QMessageBox.warning(self, "IOS image", "This IOS image is for the {} platform/chassis and is not supported by this application!".format(detected_platform))
            return

        index = self.uiPlatformComboBox.findText(detected_platform)
        if index != -1:
            self.uiPlatformComboBox.setCurrentIndex(index)

        index = self.uiChassisComboBox.findText(detected_chassis)
        if index != -1:
            self.uiChassisComboBox.setCurrentIndex(index)

    def _populateAdapters(self, platform, chassis):
        """
        Loads the adapter and WIC configuration.

        :param platform: the router platform (string)
        :param chassis: the router chassis (string)
        """

        # clear all the slot combo boxes.
        for widget in self._widget_slots.values():
            widget.clear()
            widget.setEnabled(False)

        # load the available adapters to the correct slot for the corresponding platform and chassis
        for slot_number, slot_adapters in ADAPTER_MATRIX[platform][chassis].items():
            self._widget_slots[slot_number].setEnabled(True)

            if type(slot_adapters) == str:
                # only one default adapter for this slot.
                self._widget_slots[slot_number].addItem(slot_adapters)
            else:
                # list of adapters
                module_list = list(slot_adapters)
                self._widget_slots[slot_number].addItems([""] + module_list)

        # clear all the WIC combo boxes.
        for widget in self._widget_wics.values():
            widget.setEnabled(False)
            widget.clear()

        # load the available WICs to the correct slot for the corresponding platform
        if platform in WIC_MATRIX:
            for wic_number, wics in WIC_MATRIX[platform].items():
                self._widget_wics[wic_number].setEnabled(True)
                wic_list = list(wics)
                self._widget_wics[wic_number].addItems([""] + wic_list)

    def initializePage(self, page_id):

        if self.page(page_id) == self.uiMemoryWizardPage:
            # set the correct amount of RAM based on the platform
            from ..pages.ios_router_preferences_page import IOSRouterPreferencesPage
            platform = self.uiPlatformComboBox.currentText()
            path = self.uiIOSImageLineEdit.text()
            if os.path.isfile(path):
                minimum_required_ram = IOSRouterPreferencesPage.getMinimumRequiredRAM(path)
                if minimum_required_ram > PLATFORMS_DEFAULT_RAM[platform]:
                    self.uiRamSpinBox.setValue(minimum_required_ram)
                else:
                    self.uiRamSpinBox.setValue(PLATFORMS_DEFAULT_RAM[platform])
            else:
                self.uiRamSpinBox.setValue(PLATFORMS_DEFAULT_RAM[platform])

        elif self.page(page_id) == self.uiNetworkAdaptersWizardPage:
            platform = self.uiPlatformComboBox.currentText()
            chassis = self.uiChassisComboBox.currentText()
            if not chassis:
                chassis = ""
            self._populateAdapters(platform, chassis)
            if platform == "c7200":
                self.uiSlot0comboBox.setCurrentIndex(self.uiSlot0comboBox.findText("C7200-IO-2FE"))

    def validateCurrentPage(self):
        """
        Validates the IOS name.
        """

        # if self.currentPage() == self.uiNameImageWizardPage:
        #     name = self.uiNameLineEdit.text()
        #     if not re.search(r"""^[\-\w]+$""", name):
        #         # IOS names must start with a letter, end with a letter or digit, and
        #         # have as interior characters only letters, digits, and hyphens.
        #         # They must be 63 characters or fewer.
        #         QtGui.QMessageBox.critical(self, "Name", "Invalid name detected: {}".format(name))
        #         return False
        return True


    #     minimum_required_ram = self._getMinimumRequiredRAM(path)
    #     if minimum_required_ram > ram:
    #         QtGui.QMessageBox.warning(self, "IOS image", "There is not sufficient RAM allocated to this IOS image, recommended RAM is {} MB".format(minimum_required_ram))
    #
    #     # basename doesn't work on Unix with Windows paths
    #     if not sys.platform.startswith('win') and len(path) > 2 and path[1] == ":":
    #         import ntpath
    #         image = ntpath.basename(path)
    #     else:
    #         image = os.path.basename(path)
    #
    #     if image.startswith("c7200p"):
    #         QtGui.QMessageBox.warning(self, "IOS image", "This IOS image is for the c7200 platform with NPE-G2 and using it is not recommended.\nPlease use an IOS image that do not start with c7200p.")

    def getSettings(self):
        """
        Returns the settings set in this Wizard.

        :return: settings dict
        """

        path = self.uiIOSImageLineEdit.text()

        #TODO: mutiple remote server
        if Dynamips.instance().settings()["use_local_server"]:
            server = "local"
        else:
            server = next(iter(Servers.instance()))
            if not server:
                QtGui.QMessageBox.critical(self, "IOS image", "No remote server available!")
                return
            server = server.host

        settings = {
            "name": self.uiNameLineEdit.text(),
            "path": path,
            "ram": self.uiRamSpinBox.value(),
            "idlepc": self.uiIdlepcLineEdit.text(),
            "image": os.path.basename(path),
            "platform": self.uiPlatformComboBox.currentText(),
            "chassis": self.uiChassisComboBox.currentText(),
            "server": server,
        }

        for slot_id, widget in self._widget_slots.items():
            if widget.isEnabled():
                settings["slot{}".format(slot_id)] = widget.currentText()

        for wic_id, widget in self._widget_wics.items():
            if widget.isEnabled():
                settings["wic{}".format(wic_id)] = widget.currentText()

        return settings

    def nextId(self):
        """
        Wizard rules!
        """

        current_id = self.currentId()
        if self.page(current_id) == self.uiNetworkAdaptersWizardPage:
            platform = self.uiPlatformComboBox.currentText()
            if platform not in WIC_MATRIX:
                # skip the WIC modules page if the platform doesn't support any.
                return self.uiNetworkAdaptersWizardPage.nextId() + 1
        return QtGui.QWizard.nextId(self)