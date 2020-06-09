# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GTFS
                                 A QGIS plugin
 Otevírám GTFS.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-03-26
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Skupina B
        email                : martin.kouba@fsv.cvut.cz
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .GTFS_dockwidget import GTFSDockWidget
import os.path

from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QFileDialog
from qgis.utils import iface
from qgis.core import *
from qgis.gui import *

from zipfile import ZipFile
from PyQt5.QtCore import QVariant
from osgeo import ogr
import shutil 
import ctypes
import sqlite3


class GTFS:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GTFS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GTFS load')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GTFS')
        self.toolbar.setObjectName(u'GTFS')

        #print "** INITIALIZING GTFS"

        self.pluginIsActive = False
        self.dockwidget = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.
        :param message: String for translation.
        :type message: str, QString
        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GTFS', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.
        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str
        :param text: Text that should be shown in menu items for this action.
        :type text: str
        :param callback: Function to be called when the action is triggered.
        :type callback: function
        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool
        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool
        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool
        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str
        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GTFS/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'GTFS Load'),
            callback=self.run,
            parent=self.iface.mainWindow())

    #--------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        #print "** CLOSING GTFS"

        # disconnects
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        #print "** UNLOAD GTFS"

        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GTFS load'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    #--------------------------------------------------------------------------

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True

            #print "** STARTING GTFS"

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self.dockwidget == None:
                self.browsePathSetting="/plugins/2020-b-qgis-gtfs-plugin"
                self._home = QSettings().value(self.browsePathSetting,'')
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = GTFSDockWidget()
                self.dockwidget.input_dir.setDialogTitle("Select GTFS")
                self.dockwidget.input_dir.setFilter("GTFS *.zip")
                self.dockwidget.input_dir.setStorageMode(QgsFileWidget.GetFile)
                self.dockwidget.submit.clicked.connect(self.load_file)

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            # TODO: fix to allow choice of dock location
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()

    # The function unzip file to new folder
    def unzip_file(self, GTFS_folder):
        """
        Unzip input archive.

        :param str path: full path to input zip file
        
        :return list: list of input CSV file to be loaded
        """
        # Load file - function that reads a GTFS ZIP file. 
        GTFS_name = os.path.splitext(os.path.basename(GTFS_folder))[0]
        GTFS_path = os.path.join(os.path.dirname(GTFS_folder), GTFS_name)
        # Create a folder for files.
        os.mkdir(GTFS_path)
        # Extracts files to path. 
        with ZipFile(GTFS_folder, 'r') as zip:
            # printing all the contents of the zip file 
            zip.printdir() 
            zip.extractall(GTFS_path)
        # Select text files only.
        csv_files = []
        # r=root, d=directories, f = files
        for r, d, f in os.walk(GTFS_path):
            for csv_file in f:
                current_file = os.path.splitext(os.path.basename(csv_file))[1]
                if current_file == '.txt':
                    csv_files.append(os.path.join(r, csv_file))
        return csv_files

    # The function save layers from unzipped path into geopackage
    def save_layers_into_gpkg(self, csv_files, GTFS_path):
        layer_names = []
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'

        for csv in csv_files:
            # build URI
            uri = 'file:///{}?delimiter=,'.format(csv)
            csv_name = os.path.splitext(os.path.basename(csv))[0]
            if csv_name == 'stops':
                uri += '&xField=stop_lon&yField=stop_lat&crs=epsg:4326'
            elif csv_name == 'shapes':
                uri += '&xField=shape_pt_lon&yField=shape_pt_lat&crs=epsg:4326'
                csv_name='shapes_point'

            # create CSV-based layer
            layer_names.append(csv_name)
            layer = QgsVectorLayer(uri, csv_name, 'delimitedtext')

            # save layer to GPKG
            options.layerName = layer.name().replace(' ', '_')
            QgsVectorFileWriter.writeAsVectorFormat(layer, GTFS_path, options)
            # append layers into single GPKG
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer 

        # Return all layers from geopackage
        return layer_names
    
    # The function load layers from geopackage to the layer tree
    def load_layers_from_gpkg(self,GPKG_path,layer_names):
        # Create groups
        GTFS_name=os.path.splitext(os.path.basename(GPKG_path))[0]
        root=QgsProject.instance().layerTreeRoot()
        group_gtfs = root.addGroup("gtfs import ("+GTFS_name+")")
        g_trans = group_gtfs.addGroup("transfer")
        g_time = group_gtfs.addGroup("time management")
        g_service = group_gtfs.addGroup("service info")
        for layer_name in layer_names:
            if layer_name != 'shapes_point':
                path_to_layer = GPKG_path + "|layername=" + layer_name
                layer = QgsVectorLayer(path_to_layer, layer_name, "ogr")
                QgsProject.instance().addMapLayer(layer, False)
                if layer_name in ['trips','transfers','stops','routes', 'lines']:
                    group_gtfs.insertChildNode(0,QgsLayerTreeLayer(layer))
                if layer_name in ['levels','pathways']:
                    g_trans.insertChildNode(0,QgsLayerTreeLayer(layer))
                if layer_name in ['stop_times','calendar','calendar_dates','frequencies']:
                    g_time.insertChildNode(0,QgsLayerTreeLayer(layer))
                if layer_name in ['agency','feed_info','route_sub_agencies', 'fare_rules','fare_attributes','attributions','translations']:
                    g_service.insertChildNode(0,QgsLayerTreeLayer(layer))

        # create index on on shape_id, shape_pt_sequence
        with sqlite3.connect(GPKG_path) as connection:
            cursor = connection.cursor()
            for idx in ('shape_id', 'shape_pt_sequence'):
                cursor.execute("CREATE INDEX {0}_index ON shapes_point({0})".format(idx))
            cursor.close()
            
        with sqlite3.connect(GPKG_path) as connection:
            cursor = connection.cursor()
            cursor.execute("CREATE INDEX route_id_index ON routes(route_id)".format())
            cursor.close()

    # The function delete unzipped folder
    def delete_folder(self,GTFS_path):
        shutil.rmtree(GTFS_path)

    # The function create polyline by joining the points from point layer "shapes" and adds information to the attribute table
    def connect_shapes(self,GPKG_path):
        path_to_shapes = GPKG_path + "|layername=" + 'shapes_point'
        layer = QgsVectorLayer(path_to_shapes, 'shapes', "ogr")
        #Index used to decide id field shape_dist_traveled exist 
        idx=(layer.fields().indexFromName('shape_dist_traveled'))
        # load attribute table of shapes into variable features
        features = layer.getFeatures()
        # selecting unique id of shapes from features
        IDList=[]
        for feat in features:
            id=feat['shape_id']
            IDList.append(id)
        uniqueId=list(set(IDList))
        # create polyline layer
        shapes_layer = QgsVectorLayer("LineString?crs=epsg:4326", "shapes_line", "memory")
        pr = shapes_layer.dataProvider()
        layer_provider=shapes_layer.dataProvider()
        # add new fields to polyline layer
        layer_provider.addAttributes([QgsField("shape_id",QVariant.String), QgsField("shape_dist_traveled",QVariant.Double), QgsField("shape_id_short",QVariant.String)])
        shapes_layer.updateFields()
        for Id in uniqueId:
            # select rows from attribute table, where shape_id agree with current Id in for-cycle
            expression = ('"shape_id" = \'%s%s\''%(Id,''))
            request = QgsFeatureRequest().setFilterExpression(expression)
            features_shape =layer.getFeatures(request)
            # sorting attribute table of features_shape by field shape_pt_sequence
            sorted_f_shapes=sorted(features_shape,key=lambda por:por['shape_pt_sequence'])
            PointList=[]
            DistList=[]
            # add coordinates of shape points and traveled distance to the list
            for f in sorted_f_shapes:
                point=QgsPoint(f['shape_pt_lon'],f['shape_pt_lat'])
                PointList.append(point)
                if idx!=-1:
                    dist=(f['shape_dist_traveled'])
                    DistList.append(dist)
            # create polyline from PointList
            polyline=QgsFeature()
            polyline.setGeometry(QgsGeometry.fromPolyline(PointList))
            if type(Id) == str and Id.find('V')!=-1:
                # Create shape id short, used for joining routes
                shape_id_s=Id[0:Id.index('V')]
                # find last distance of each shape
                for j in range(0, len(sorted_f_shapes)):
                    if j == (len(sorted_f_shapes)-1):
                        Dist=DistList[j]
                # adding features to attribute table of polyline
                polyline.setAttributes([Id,Dist,shape_id_s])
                pr.addFeatures( [ polyline ] )
            else:
                polyline.setAttributes([Id])
                pr.addFeatures( [ polyline ] )
        shapes_layer.updateExtents()
        return shapes_layer

    def set_line_colors(self, v_line):
        # TODO: solve duplicated layers in layer tree
        layer_routes = QgsProject.instance().mapLayersByName('routes')[0]

        #---JOIN---
        lineField = 'shape_id_short'
        routesField = 'route_id'
        joinObject = QgsVectorLayerJoinInfo()
        joinObject.setJoinFieldName(routesField)
        joinObject.setTargetFieldName(lineField)
        joinObject.setJoinLayerId(layer_routes.id())
        joinObject.setUsingMemoryCache(True)
        joinObject.setJoinLayer(layer_routes)
        v_line.addJoin(joinObject)
        
        #---COLORING---
        target_field = 'routes_fid'
        features_shape = v_line.getFeatures()
        myRangeList = []
        colors = {}
        for f in features_shape:
            r_fid = f['routes_fid']
            if r_fid not in colors:
                colors[r_fid] = (f['routes_route_color'], f['routes_route_short_name'])

        for r_fid, r_item in colors.items():
            symbol = QgsSymbol.defaultSymbol(v_line.geometryType())
            symbol.setColor(QColor('#' + r_item[0]))
            myRange = QgsRendererCategory(r_fid, symbol, r_item[1])
            myRangeList.append(myRange)
            myRenderer = QgsCategorizedSymbolRenderer(target_field, myRangeList)
            v_line.setRenderer(myRenderer)
        v_line.triggerRepaint()

    # The function that restricts the input file to a zip file
    def load_file(self):
        GTFS_folder = self.dockwidget.input_dir.filePath()
        if not GTFS_folder.endswith('.zip'):
            self.iface.messageBar().pushMessage(
                "Error", "Please select a zipfile", level=Qgis.Critical
            )
            return
        # Use of defined functions
        GTFS_name = os.path.splitext(os.path.basename(GTFS_folder))[0]
        GTFS_path = os.path.join(os.path.dirname(GTFS_folder), GTFS_name)

        # unzip input archive, get list of CVS files
        csv_files = self.unzip_file(GTFS_folder)
        self.iface.messageBar().pushMessage(
            "Warning", "It will take a while!", level=Qgis.Warning
        )
        self.iface.mainWindow().repaint()
        # load csv files, ..., save memory layers into target GeoPackage DB
        layer_names = self.save_layers_into_gpkg(csv_files, GTFS_path)
        # load layers from GPKG into map canvas
        self.load_layers_from_gpkg(GTFS_path + '.gpkg', layer_names)
        # delete working directory with CSV files
        self.delete_folder(GTFS_path)
        # create polyline by joining points
        polyline=self.connect_shapes(GTFS_path + '.gpkg')
        # create polyline file in GPKG
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer 
        options.driverName = 'GPKG' 
        options.layerName = polyline.name()
        QgsVectorFileWriter.writeAsVectorFormat(polyline,GTFS_path,options)
        # add shapes_layer to the map canvas
        path_to_layer = GTFS_path + '.gpkg' + '|layername=' + polyline.name()
        with sqlite3.connect(GTFS_path + '.gpkg') as connection:
            cursor = connection.cursor()
            cursor.execute("CREATE INDEX shape_id_short_index ON shapes_line(shape_id_short)".format())
            cursor.close()
        shapes_layer = QgsVectorLayer(path_to_layer, 'shapes', "ogr")
        features_shape =shapes_layer.getFeatures()
        for feat in features_shape:
            if str(feat['shape_id_short']) == 'NULL':
                possible_join=-1
            else:
                possible_join=1
        if possible_join !=-1:
            self.set_line_colors(shapes_layer)
        QgsProject.instance().addMapLayer(shapes_layer, False)
        root=QgsProject.instance().layerTreeRoot()
        group_gtfs = root.findGroup("gtfs import ("+GTFS_name+")")
        group_gtfs.insertChildNode(0,QgsLayerTreeLayer(shapes_layer))
