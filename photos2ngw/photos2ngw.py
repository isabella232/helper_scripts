#!/usr/bin/env python
# -*- coding: utf-8 -*-
#******************************************************************************
#
# photos2ngw.py
# ---------------------------------------------------------
# Upload images to a Web GIS
# More: https://gitlab.com/nextgis/helper_scripts
#
# Usage: 
#      photos2ngw.py [-h] [-o] [-of ORIGINALS_FOLDER]
#      where:
#           -h              show this help message and exit
#           -o              overwrite
#           -of             relative path to folder with originals
#           -t              type of data, license or gin
# Example:
#      python photos2ngw.py -of originals_gkm -t gkm
#
# Copyright (C) 2019-present Artem Svetlov (artem.svetlov@nextgis.com)
#
# This source is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This code is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# A copy of the GNU General Public License is available on the World Wide Web
# at <http://www.gnu.org/copyleft/gpl.html>. You can also obtain it by writing
# to the Free Software Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA.
#
#******************************************************************************

import os, sys
import exifread
import json
import math
import argparse
import requests
from json import dumps
from datetime import datetime

try:
    import config
except ImportError:
    print "config.py not found. Copy config.example.py to config.py, and set your Web GIS credentials here. See readme.md"
    quit()

def get_args():
    p = argparse.ArgumentParser(description='Upload images to a Web GIS')
    p.add_argument('--resource_id', help='nextgis.com folder id', type=int)
    p.add_argument('--debug', '-d', help='debug mode', action='store_false')
    p.add_argument('path', help='Path to folder containing JPG files')
    return p.parse_args()

def lon_3857(lon):
  r_major=6378137.000
  return r_major*math.radians(lon)

def lat_3857(lat):
  if lat>89.5:lat=89.5
  if lat<-89.5:lat=-89.5
  r_major=6378137.000
  r_minor=6356752.3142
  temp=r_minor/r_major
  eccent=math.sqrt(1-temp**2)
  phi=math.radians(lat)
  sinphi=math.sin(phi)
  con=eccent*sinphi
  com=eccent/2
  con=((1.0-con)/(1.0+con))**com
  ts=math.tan((math.pi/2-phi)/2)/con
  y=0-r_major*math.log(ts)
  return y

def progress(count, total, status=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    sys.stdout.flush()  # As suggested by Rom Ruben (see: http://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console/27871113#comment50529068_27871113)

def _get_if_exist(data, key):
    if key in data:
        return data[key]

    return None

def _convert_to_degress(value):
    """
    Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
    :param value:
    :type value: exifread.utils.Ratio
    :rtype: float
    """
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)

    return d + (m / 60.0) + (s / 3600.0)

def get_exif_location(exif_data):
    """
    Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)
    """
    lat = None
    lon = None

    gps_latitude = _get_if_exist(exif_data, 'GPS GPSLatitude')
    gps_latitude_ref = _get_if_exist(exif_data, 'GPS GPSLatitudeRef')
    gps_longitude = _get_if_exist(exif_data, 'GPS GPSLongitude')
    gps_longitude_ref = _get_if_exist(exif_data, 'GPS GPSLongitudeRef')

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = _convert_to_degress(gps_latitude)
        if gps_latitude_ref.values[0] != 'N':
            lat = 0 - lat

        lon = _convert_to_degress(gps_longitude)
        if gps_longitude_ref.values[0] != 'E':
            lon = 0 - lon

    return lat, lon

if __name__ == '__main__':
    args = get_args()
    file_list = []
    for root, sub_folders, files in os.walk(args.path):
        for name in files:
            file_list += [os.path.join(root, name)  ]

    index = 0
    IterationStep = 1
    total = len(file_list)

    ngwFeatures = list()
    while index < total:
        filename = file_list[index]

        file = open(filename, 'rb')
        tags = exifread.process_file(file, details=False)
        file.close()

        lat, lon = get_exif_location(tags)
        ngwFeature = dict()
        ngwFeature['extensions'] = dict()
        ngwFeature['extensions']['attachment'] = None
        ngwFeature['extensions']['description'] = None
        ngwFeature['fields'] = dict()
        ngwFeature['fields']['filename'] = filename
        ngwFeature['fields']['datetime'] = str(_get_if_exist(tags,'Image DateTime'))

        if lat is not None and lon is not None :

            ngwFeature['geom'] = 'POINT ({lon} {lat})'.format(lon=lon_3857(lon),lat=lat_3857(lat))
            ngwFeatures.append(ngwFeature)

        index = index+IterationStep
        if index > total:
            index=total
        progress(index, len(file_list), status='Read photos, total = '+str(total))

    URL = config.ngw_url
    AUTH = config.ngw_creds
    GRPNAME = "photos"

    # Пока удаление ресурсов не работает, добавим дату и время к имени группы
    GRPNAME = datetime.now().isoformat() + " " + GRPNAME

    s = requests.Session()

    def req(method, url, json=None, **kwargs):
        """ Простейшая обертка над библиотекой requests c выводом отправляемых
        запросов в stdout. К работе NextGISWeb это имеет малое отношение. """

        jsonuc = None

        if json:
            kwargs['data'] = dumps(json)
            jsonuc = dumps(json, ensure_ascii=False)

        req = requests.Request(method, url, auth=AUTH, **kwargs)
        preq = req.prepare()

        print ""
        print ">>> %s %s" % (method, url)

        if jsonuc:
            print ">>> %s" % jsonuc

        resp = s.send(preq)

        print resp.status_code
        assert resp.status_code / 100 == 2

        jsonresp = resp.json()

        for line in dumps(jsonresp, ensure_ascii=False, indent=4).split("\n"):
            print "<<< %s" % line

        return jsonresp

    # Обертки по именам HTTP запросов, по одной на каждый тип запроса
    def get(url, **kwargs): return req('GET', url, **kwargs)            # NOQA
    def post(url, **kwargs): return req('POST', url, **kwargs)          # NOQA
    def put(url, **kwargs): return req('PUT', url, **kwargs)            # NOQA
    def delete(url, **kwargs): return req('DELETE', url, **kwargs)      # NOQA

    # Собственно работа с REST API
    iturl = lambda (id): '%s/api/resource/%d' % (URL, id)
    courl = lambda: '%s/api/resource/' % URL

    if args.resource_id is None:
        # Создаем группу ресурсов внутри основной группы ресурсов, в которой будут
        # производится все дальнешние манипуляции.
        grp = post(courl(), json=dict(
            resource=dict(
                cls='resource_group',   # Идентификатор типа ресурса
                parent=dict(id=0),      # Создаем ресурс в основной группе ресурсов
                display_name=GRPNAME,   # Наименование (или имя) создаваемого ресурса
            )
        ))
    
        # Поскольку все дальнейшие манипуляции будут внутри созданной группы,
        # поместим ее ID в отдельную переменную.
        grpid = grp['id']
    else:
        grpid = args.resource_id
    grpref = dict(id=grpid)

    # Метод POST возвращает только ID созданного ресурса, посмотрим все данные
    # только что созданной подгруппы.
    get(iturl(grpid))

    #create empty layer using REST API

    structure = dict()
    structure['resource']=dict()
    structure['resource']['cls']='vector_layer'
    structure['resource']['parent']=dict(id=int(grpid))
    structure['resource']['display_name']='photos'
    structure['vector_layer']=dict()
    structure['vector_layer']['srs']=dict(id=3857)
    structure['vector_layer']['geometry_type']='POINT'
    structure['vector_layer']['fields']=list()
    structure['vector_layer']['fields'].append(dict(keyname='filename',datatype='STRING'))
    structure['vector_layer']['fields'].append(dict(keyname='datetime',datatype='STRING'))
    vectlyr = post(courl(), json=structure)

    for feature in ngwFeatures:

        print 'upload feature'

        #ngw_feature = post(vectlyr['id']+'/feature/', json=feature)
        post_url = URL + '/api/resource/' + str(vectlyr['id'])+'/feature/'
        print post_url
        response = requests.post(post_url, data=json.dumps(feature),auth=AUTH)
        print response.content

        with open(feature['fields']['filename']) as f:

            #upload attachment to nextgisweb
            req = requests.put(URL + '/api/'+ '/component/file_upload/upload', data=f, auth=AUTH)
            json_data = req.json()
            json_data['name'] = os.path.basename(feature['fields']['filename'])

            attach_data = {}
            attach_data['file_upload'] = json_data

            #add attachment to nextgisweb feature
            post_url = URL + '/api/resource/' + str(vectlyr['id']) +'/feature/' + str(response.json()['id'])+ '/attachment/'
            print post_url
            req = requests.post(post_url, data=json.dumps(attach_data), auth=AUTH)

    #create map mapstyle
    filename = 'photos.qml'

    with open(filename) as f:
        #upload attachment to nextgisweb
        req = requests.put(URL + '/api/'+ '/component/file_upload/upload', data=f, auth=AUTH)
        json_data = req.json()
        print json_data

        mapstyle_data = {}
        mapstyle_data['qgis_vector_style'] = {}
        mapstyle_data['qgis_vector_style']['file_upload'] = {}
        mapstyle_data['qgis_vector_style']['file_upload']['id'] = json_data['id']
        mapstyle_data['qgis_vector_style']['file_upload']['mime_type'] = json_data['mime_type']
        mapstyle_data['qgis_vector_style']['file_upload']['size'] = json_data['size']
        #mapstyle_data['qgis_vector_style']['file_upload']['name'] = json_data['name']
        mapstyle_data['resource'] = {}
        mapstyle_data['resource']['cls'] = 'qgis_vector_style'
        mapstyle_data['resource']['display_name'] = 'photos'
        mapstyle_data['resource']['parent'] = {}
        mapstyle_data['resource']['parent']['id'] = vectlyr['id']

        #add attachment to nextgisweb feature
        post_url = URL + '/api/resource/'
        #print post_url
        #print mapstyle_data
        req = requests.post(post_url, data=json.dumps(mapstyle_data), auth=AUTH)