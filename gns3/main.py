#!/usr/bin/env python
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

# Try to install updates & restart application if an update is installed
try:
    import gns3.update_manager
    if gns3.update_manager.UpdateManager().installDownloadedUpdates():
        print("Update installed restart the application")
        python = sys.executable
        os.execl(python, python, * sys.argv)
except Exception as e:
    print("Fail update installation: {}".format(str(e)))


# WARNING
# Due to buggy user machines we choose to put this as the first loading modules
# otherwise the egg cache is initialized in his standard location and
# if is not writetable the application crash. It's the user fault
# because one day the user as used sudo to run an egg and break his
# filesystem permissions, but it's a common mistake.
from gns3.utils.get_resource import get_resource


import datetime
import traceback
import time
import locale
import argparse
import signal

try:
    from gns3.qt import QtCore, QtGui, QtWidgets, DEFAULT_BINDING
except ImportError:
    raise SystemExit("Can't import Qt modules: Qt and/or PyQt is probably not installed correctly...")
from gns3.main_window import MainWindow

from gns3.logger import init_logger
from gns3.crash_report import CrashReport
from gns3.local_config import LocalConfig

import logging
log = logging.getLogger(__name__)


from gns3.version import __version__


def locale_check():
    """
    Checks if this application runs with a correct locale (i.e. supports UTF-8 encoding) and attempt to fix
    if this is not the case.

    This is to prevent UnicodeEncodeError with unicode paths when using standard library I/O operation
    methods (e.g. os.stat() or os.path.*) which rely on the system or user locale.

    More information can be found there: http://seasonofcode.com/posts/unicode-i-o-and-locales-in-python.html
    or there: http://robjwells.com/post/61198832297/get-your-us-ascii-out-of-my-face
    """

    # no need to check on Windows or when frozen
    if sys.platform.startswith("win") or hasattr(sys, "frozen"):
        return

    language = encoding = None
    try:
        language, encoding = locale.getlocale()
    except ValueError as e:
        log.error("could not determine the current locale: {}".format(e))
    if not language and not encoding:
        try:
            log.warn("could not find a default locale, switching to C.UTF-8...")
            locale.setlocale(locale.LC_ALL, ("C", "UTF-8"))
        except locale.Error as e:
            log.error("could not switch to the C.UTF-8 locale: {}".format(e))
            raise SystemExit
    elif encoding != "UTF-8":
        log.warn("your locale {}.{} encoding is not UTF-8, switching to the UTF-8 version...".format(language, encoding))
        try:
            locale.setlocale(locale.LC_ALL, (language, "UTF-8"))
        except locale.Error as e:
            log.error("could not set an UTF-8 encoding for the {} locale: {}".format(language, e))
            raise SystemExit
    else:
        log.info("current locale is {}.{}".format(language, encoding))


def main():
    """
    Entry point for GNS3 GUI.
    """

    # Sometimes (for example at first launch) the OSX app service launcher add
    # an extra argument starting with -psn_. We filter it
    if sys.platform.startswith("darwin"):
        sys.argv = [a for a in sys.argv if not a.startswith("-psn_")]

    parser = argparse.ArgumentParser()
    parser.add_argument("project", help="load a GNS3 project (.gns3)", metavar="path", nargs="?")
    parser.add_argument("--version", help="show the version", action="version", version=__version__)
    parser.add_argument("--debug", help="print out debug messages", action="store_true", default=False)
    parser.add_argument("--config", help="Configuration file")
    options = parser.parse_args()
    exception_file_path = "exceptions.log"

    if options.config:
        LocalConfig.instance(config_file=options.config)
    else:
        LocalConfig.instance()

    if hasattr(sys, "frozen"):
        # We add to the path where the OS search executable our binary location starting by GNS3
        # packaged binary
        frozen_dir = os.path.dirname(os.path.abspath(sys.executable))
        if sys.platform.startswith("darwin"):
            frozen_dirs = [
                frozen_dir,
                os.path.normpath(os.path.join(frozen_dir, '..', 'Resources'))
            ]
        elif sys.platform.startswith("win"):
            frozen_dirs = [
                frozen_dir,
                os.path.normpath(os.path.join(frozen_dir, 'dynamips')),
                os.path.normpath(os.path.join(frozen_dir, 'vpcs'))
            ]

        os.environ["PATH"] = os.pathsep.join(frozen_dirs) + os.pathsep + os.environ.get("PATH", "")

        if options.project:
            os.chdir(frozen_dir)

    def exceptionHook(exception, value, tb):

        if exception == KeyboardInterrupt:
            sys.exit(0)

        lines = traceback.format_exception(exception, value, tb)
        print("****** Exception detected, traceback information saved in {} ******".format(exception_file_path))
        print("\nPLEASE REPORT ON https://community.gns3.com/community/software/bug\n")
        print("".join(lines))
        try:
            curdate = time.strftime("%d %b %Y %H:%M:%S")
            logfile = open(exception_file_path, "a", encoding="utf-8")
            logfile.write("=== GNS3 {} traceback on {} ===\n".format(__version__, curdate))
            logfile.write("".join(lines))
            logfile.close()
        except OSError as e:
            print("Could not save traceback to {}: {}".format(os.path.normpath(exception_file_path), e))

        if not sys.stdout.isatty():
            # if stdout is not a tty (redirected to the console view),
            # then print the exception on stderr too.
            print("".join(lines), file=sys.stderr)

        if exception is MemoryError:
            print("YOUR SYSTEM IS OUT OF MEMORY!")
        else:
            CrashReport.instance().captureException(exception, value, tb)

    # catch exceptions to write them in a file
    sys.excepthook = exceptionHook

    current_year = datetime.date.today().year
    print("GNS3 GUI version {}".format(__version__))
    print("Copyright (c) 2007-{} GNS3 Technologies Inc.".format(current_year))

    # we only support Python 3 version >= 3.4
    if sys.version_info < (3, 4):
        raise SystemExit("Python 3.4 or higher is required")

    def version(version_string):
        return [int(i) for i in version_string.split('.')]

    if version(QtCore.QT_VERSION_STR) < version("4.6"):
        raise SystemExit("Requirement is Qt version 4.6 or higher, got version {}".format(QtCore.QT_VERSION_STR))

    # 4.8.3 because of QSettings (http://pyqt.sourceforge.net/Docs/PyQt4/pyqt_qsettings.html)
    if DEFAULT_BINDING == "PyQt4" and version(QtCore.BINDING_VERSION_STR) < version("4.8.3"):
        raise SystemExit("Requirement is PyQt version 4.8.3 or higher, got version {}".format(QtCore.BINDING_VERSION_STR))

    if DEFAULT_BINDING == "PyQt5" and version(QtCore.BINDING_VERSION_STR) < version("5.0.0"):
        raise SystemExit("Requirement is PyQt5 version 5.0.0 or higher, got version {}".format(QtCore.BINDING_VERSION_STR))

    # check for the correct locale
    # (UNIX/Linux only)
    locale_check()

    try:
        os.getcwd()
    except FileNotFoundError:
        log.critical("the current working directory doesn't exist")
        return

    # always use the INI format on Windows and OSX (because we don't like the registry and plist files)
    if sys.platform.startswith('win') or sys.platform.startswith('darwin'):
        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)

    if sys.platform.startswith('win') and hasattr(sys, "frozen"):
        try:
            import win32console
            import win32con
            import win32gui
        except ImportError:
            raise SystemExit("Python for Windows extensions must be installed.")

        if not options.debug:
            try:
                # hide the console
                console_window = win32console.GetConsoleWindow()
                win32gui.ShowWindow(console_window, win32con.SW_HIDE)
            except win32console.error as e:
                print("warning: could not allocate console: {}".format(e))

    app = QtWidgets.QApplication(sys.argv)

    # this info is necessary for QSettings
    app.setOrganizationName("GNS3")
    app.setOrganizationDomain("gns3.net")
    app.setApplicationName("GNS3")
    app.setApplicationVersion(__version__)

    # save client logging info to a file
    logfile = os.path.join(LocalConfig.configDirectory(), "gns3_gui.log")

    # on debug enable logging to stdout
    if options.debug:
        root_logger = init_logger(logging.DEBUG, logfile)
    else:
        root_logger = init_logger(logging.INFO, logfile)

    # update the exception file path to have it in the same directory as the settings file.
    exception_file_path = os.path.join(LocalConfig.configDirectory(), exception_file_path)

    # Manage Ctrl + C or kill command
    def sigint_handler(*args):
        log.info("Signal received exiting the application")
        app.closeAllWindows()
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)

    mainwindow = MainWindow(options.project)
    mainwindow.show()
    exit_code = app.exec_()
    delattr(MainWindow, "_instance")
    app.deleteLater()

    # We force a full garbage collect before exit
    # for unknow reason otherwise Qt Segfault on OSX in some
    # conditions
    import gc
    gc.collect()

    sys.exit(exit_code)

if __name__ == '__main__':
    main()
