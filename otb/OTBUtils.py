# -*- coding: utf-8 -*-

"""
***************************************************************************
    OTBUtils.py
    ---------------------
    Date                 : August 2012
    Copyright            : (C) 2012 by Victor Olaya
                           (C) 2013 by CS Systemes d'information (CS SI)
    Email                : volayaf at gmail dot com
                           otb at c-s dot fr (CS SI)
    Contributors         : Victor Olaya
                           Julien Malik, Oscar Picas  (CS SI) - add functions to manage xml tree
                           Alexia Mondot (CS SI) - add a trick for OTBApplication SplitImages
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
from builtins import str

__author__ = 'Victor Olaya'
__date__ = 'August 2012'
__copyright__ = '(C) 2012, Victor Olaya'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import os
import re
import time
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsApplication,
                       QgsProcessingFeedback)
import subprocess
from processing.core.ProcessingConfig import ProcessingConfig
from processing.core.ProcessingLog import ProcessingLog
from processing.tools.system import isMac, isWindows
import logging
import xml.etree.ElementTree as ET
import traceback


OTB_FOLDER = "OTB_FOLDER"
OTB_LIB_FOLDER = "OTB_LIB_FOLDER"
OTB_SRTM_FOLDER = "OTB_SRTM_FOLDER"
OTB_GEOID_FILE = "OTB_GEOID_FILE"


def findOtbPath():
    folder = ""
    #try to configure the path automatically
    if isMac():
        testfolder = os.path.join(str(QgsApplication.prefixPath()), "bin")
        if os.path.exists(os.path.join(testfolder, "otbcli")):
            folder = testfolder
        else:
            testfolder = "/usr/local/bin"
            if os.path.exists(os.path.join(testfolder, "otbcli")):
                folder = testfolder
    elif isWindows():
        testfolder = os.path.join(os.path.dirname(QgsApplication.prefixPath()),
                                  os.pardir, "bin")
        if os.path.exists(os.path.join(testfolder, "otbcli.bat")):
            folder = testfolder
    else:
        testfolder = "/usr/bin"
        if os.path.exists(os.path.join(testfolder, "otbcli")):
            folder = testfolder
    return folder


def otbPath():
    folder = ProcessingConfig.getSetting(OTB_FOLDER)
    if folder is None:
        folder = ""
    return folder


def findOtbLibPath():
    folder = ""
    #try to configure the path automatically
    if isMac():
        testfolder = os.path.join(str(QgsApplication.prefixPath()), "lib/otb/applications")
        if os.path.exists(testfolder):
            folder = testfolder
        else:
            testfolder = "/usr/local/lib/otb/applications"
            if os.path.exists(testfolder):
                folder = testfolder
    elif isWindows():
        testfolder = os.path.join(os.path.dirname(QgsApplication.prefixPath()), "orfeotoolbox", "applications")
        if os.path.exists(testfolder):
            folder = testfolder
    else:
        testfolder = "/usr/lib/otb/applications"
        if os.path.exists(testfolder):
            folder = testfolder
    return folder


def otbLibPath():
    return ProcessingConfig.getSetting(OTB_LIB_FOLDER) or ''


def otbSRTMPath():
    return ProcessingConfig.getSetting(OTB_SRTM_FOLDER) or ''


def otbGeoidPath():
    return ProcessingConfig.getSetting(OTB_GEOID_FILE) or ''


def otbDescriptionPath():
    return os.path.join(os.path.dirname(__file__), "description")

_installedVersion = None
_installedVersionFound = False


def getInstalledVersion(runOtb=False):
    global _installedVersion
    global _installedVersionFound

    if _installedVersionFound and not runOtb:
        return _installedVersion

    if otbPath() is None or otbLibPath() is None:
        _installedVersionFound = False
        return None
    commands = [os.path.join(otbPath(), "otbcli_Smoothing")]
    feedback = QgsProcessingFeedback()
    out = executeOtb(commands, feedback, False)
    for line in out:
        if "version" in line:
            _installedVersionFound = True
            _installedVersion = line.split("version")[-1].strip()
            break
    return _installedVersion


def compatibleDescriptionPath(version):
    supportedVersions = {"5.0.0": "5.0.0",
                         "5.4.0": "5.4.0",
                         "5.6.0": "5.6.0",
                         "5.8.0": "5.8.0"}
    if version is None:
        return None
    if version not in supportedVersions:
        lastVersion = sorted(supportedVersions.keys())[-1]
        if version > lastVersion:
            version = lastVersion
        else:
            return None

    return os.path.join(otbDescriptionPath(), supportedVersions[version])


def executeOtb(commands, feedback, addToLog=True):
    loglines = []
    loglines.append(tr("OTB execution console output"))
    os.putenv('ITK_AUTOLOAD_PATH', otbLibPath())
    fused_command = ''.join(['"%s" ' % re.sub(r'^"|"$', '', c) for c in commands])
    with subprocess.Popen(fused_command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, stderr=subprocess.STDOUT, universal_newlines=True) as proc:
        if isMac():  # This trick avoids having an uninterrupted system call exception if OTB is not installed
            time.sleep(1)
        for line in iter(proc.stdout.readline, ""):
            if "[*" in line:
                idx = line.find("[*")
                perc = int(line[idx - 4:idx - 2].strip(" "))
                if perc != 0:
                    feedback.setProgress(perc)
            else:
                loglines.append(line)
                feedback.pushConsoleInfo(line)

    if addToLog:
        ProcessingLog.addToLog(ProcessingLog.LOG_INFO, loglines)

    return loglines


def tr(string, context=''):
    if context == '':
        context = 'OTBUtils'
    return QCoreApplication.translate(context, string)


def get_choices_of(doc, parameter):
    choices = []
    try:
        t5 = [item for item in doc.findall('.//parameter') if item.find('key').text == parameter]
        choices = [item.text for item in t5[0].findall('options/choices/choice')]
    except:
        logger = logging.getLogger('OTBGenerator')
        logger.warning(traceback.format_exc())
    return choices


def remove_dependent_choices(doc, parameter, choice):
    choices = get_choices_of(doc, parameter)
    choices.remove(choice)
    for a_choice in choices:
        t4 = [item for item in doc.findall('.//parameter') if '.%s' % a_choice in item.find('key').text]
        for t5 in t4:
            doc.remove(t5)


def renameValueField(doc, textitem, field, newValue):
    t4 = [item for item in doc.findall('.//parameter') if item.find('key').text == textitem]
    for t5 in t4:
        t5.find(field).text = newValue


def remove_independent_choices(doc, parameter, choice):
    choices = []
    choices.append(choice)
    for a_choice in choices:
        t4 = [item for item in doc.findall('.//parameter') if '.%s' % a_choice in item.find('key').text]
        for t5 in t4:
            doc.remove(t5)


def remove_parameter_by_key(doc, parameter):
    t4 = [item for item in doc.findall('.//parameter') if item.find('key').text == parameter]
    for t5 in t4:
        doc.remove(t5)


def remove_other_choices(doc, parameter, choice):
    t5 = [item for item in doc.findall('.//parameter') if item.find('key').text == parameter]
    if len(t5) > 0:
        choices = [item for item in t5[0].findall('options/choices/choice') if item.text != choice]
        choice_root = t5[0].findall('options/choices')[0]
        for a_choice in choices:
            choice_root.remove(a_choice)


def remove_choice(doc, parameter, choice):
    t5 = [item for item in doc.findall('.//parameter') if item.find('key').text == parameter]
    if len(t5) > 0:
        choices = [item for item in t5[0].findall('options/choices/choice') if item.text == choice]
        choice_root = t5[0].findall('options/choices')[0]
        for a_choice in choices:
            choice_root.remove(a_choice)


def split_by_choice(doc, parameter):
    """
    splits the given doc into several docs according to the given parameter
    returns a dictionary of documents
    """
    result = {}
    choices = get_choices_of(doc, parameter)
    import copy
    for choice in choices:
        #creates a new copy of the document
        working_copy = copy.deepcopy(doc)
        remove_dependent_choices(working_copy, parameter, choice)
        #remove all other choices except the current one
        remove_other_choices(working_copy, parameter, choice)
        #set a new name according to the choice
        old_app_name = working_copy.find('key').text
        working_copy.find('key').text = '%s-%s' % (old_app_name, choice)
        working_copy.find('longname').text = '%s (%s)' % (old_app_name, choice)
        #add it to the dictionary
        result[choice] = working_copy
    return result


def remove_parameter_by_criteria(doc, criteria):
    t4 = [item for item in doc.findall('./parameter') if criteria(item)]
    for t5 in t4:
        doc.getroot().remove(t5)


def defaultWrite(available_app, original_dom_document):
    with open("description/%s.xml" % available_app, "w") as fh:
        the_root = original_dom_document
        ET.ElementTree(the_root).write(fh)


def defaultSplit(available_app, original_dom_document, parameter):
    the_root = original_dom_document
    split = split_by_choice(the_root, parameter)
    the_list = []
    for key in split:
        defaultWrite('%s-%s' % (available_app, key), split[key])
        the_list.append(split[key])
    return the_list
