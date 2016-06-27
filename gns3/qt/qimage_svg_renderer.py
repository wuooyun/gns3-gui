#!/usr/bin/env python
#
# Copyright (C) 2015 GNS3 Technologies Inc.
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

import base64
import os

from . import QtCore
from . import QtSvg
from . import QtGui


class QImageSvgRenderer(QtSvg.QSvgRenderer):
    """
    Renderer pixmap and svg to SVG item

    :param path_or_data: Svg element of path to a SVG
    """
    def __init__(self, path_or_data=None):
        super().__init__()
        self.load(path_or_data)

    def load(self, path_or_data):
        if not os.path.exists(path_or_data) and not path_or_data.startswith(":"):
            self._svg = path_or_data
            path_or_data = path_or_data.encode("utf-8")
            return super().load(path_or_data)
        else:
            return super().load(path_or_data)
            # If we can't render a SVG we load and base64 the image to create a SVG
            if not self.isValid():
                image = QtGui.QImage(path_or_data)
                data = QtCore.QByteArray()
                buf = QtCore.QBuffer(data)
                image.save(buf, 'PNG')
                self._svg = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}">
    <image width="{width}" height="{height}" xlink:href="data:image/png;base64,{data}"/>
    </svg>""".format(data=bytes(data.toBase64()).decode(),
                    width=image.rect().width(),
                    height=image.rect().height())
                return super().load(self._svg.encode())

    def svg(self):
        """
        :returns: SVG source code
        """
        return self._svg

