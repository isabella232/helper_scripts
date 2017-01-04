#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Project: Валидатор наличия в QMS слоёв из набора OSMLAB
# Author: Artem Svetlov <artem.svetlov@nextgis.com>
# Copyright: 2016, NextGIS <info@nextgis.com>

import urllib
import json
from pprint import pprint
import os
import urlparse
import re
import csv

def import_qms():
    url='https://qms.nextgis.com/api/v1/geoservices/?format=json'
    filename='qms.json'
    testfile = urllib.URLopener()
    testfile.retrieve(url, filename)

    #response = urllib.urlopen(url)
    #data = json.loads(response.read())
    with open(filename) as data_file:    
        data = json.load(data_file)
    #read intomemory
    return data

def downloadqms():
    qmslist=import_qms()
    newlist=[]
    os.unlink('qms.json')
    for layer in qmslist:

        url='https://qms.nextgis.com/api/v1/geoservices/'+str(layer['id'])+'/?format=json'
        print url
        response = urllib.urlopen(url)
        data = json.loads(response.read())
        layer.update(data)

        #print layer
        newlist.append(layer)
        with open('qms.json', 'wb') as outfile:
            json.dump(newlist, outfile)

    #quit('теперь закомментируйте вызов downloadqms() и перезапускайте')        

def openqmsfile():

    with open('qms.json') as data_file:
        data = json.load(data_file)

    return data

def getLayerDomain(url):
    '''
    Convert 
    http://tiles{switch:1,2,3,4}-4001b3692e229e3215c9b7a73e528198.skobblermaps.com/TileService/tiles/2.0/00021210101/0/{zoom}/{x}/{y}.png
    to
    skobblermaps.com
    '''
    stripped_url = re.sub('{.+?}', '', url)

    subdomain=''
    url = urlparse.urlparse(stripped_url)
    try:
        subdomain = url.hostname.split('.')[-2] + '.' + url.hostname.split('.')[-1]
    except:
        subdomain=None
    return subdomain

def url_osmlabTMS2qms(url):
    if 'switch' in url:
        regex = r'\{switch:.*?\}'
        pt = re.compile(regex)
        res = pt.search(url)
        switch = res.group(0)
        new_val =  switch.split(':')[1].split(',')[0]
        url = re.sub(regex,new_val,url)
    url = url.replace('{zoom}','{z}')
    url = url.replace('{zoom-1}','{z-1}')
    
    return url

def url_osmlabWMS2qms(url):
    url = url.split("?")[0]
    return url
    
def getLayersWMS(url):
    list = url.split("?")[1].split("&")
    params = dict(map(None,x.split('=')) for x in list)
    params = dict((k.upper(), v) for k,v in params.iteritems())
    layers = params['LAYERS']
    
    return layers

def getFormatWMS(url):
    list = url.split("?")[1].split("&")
    params = dict(map(None,x.split('=')) for x in list)
    params = dict((k.upper(), v) for k,v in params.iteritems())
    format = ''
    if 'FORMAT' in params:
        format = params['FORMAT']
    
    return format
    
def getParamsWMS(url):
    list = url.split("?")[1].split("&")
    params = dict(map(None,x.split('=')) for x in list)
    params = dict((k.upper(), v) for k,v in params.iteritems())
    getparams = ''
    for param in params:
        if param != 'LAYERS' and param != 'FORMAT' and params[param] != '':
            getparams = getparams + '&' + param + '=' + params[param]
    return getparams
    
if __name__ == '__main__':

    #downloadqms()
    qmslist=openqmsfile()
    
    #read file from github
    url='https://raw.githubusercontent.com/osmlab/editor-layer-index/gh-pages/imagery.json'
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    print('Fresh OSMLab imagery.json dowloaded')

    fieldnames = ['id', 'name', 'type', 'url','url_qms','layers_qms','format_qms','getparams_qms','country_code','start_date','end_date','min_zoom','max_zoom','best','overlay','license_url','attribution_text','attribution_url','available_projections', 'likely_already_qms','likely_qms_layers']
    
    with open('list.csv', 'wb') as csvfile:
        listwriter = csv.DictWriter(csvfile, fieldnames, delimiter=';',quotechar='"', quoting=csv.QUOTE_ALL)
        headers = {} 
        for n in fieldnames:
            headers[n] = n
        listwriter.writerow(headers)
    
        for layer in data:
    
            #   Search in qms for layer with same domain
            osmlab_layer_domain=getLayerDomain(layer.get('url'))
            likely_already_qms = False
            likely_qms_layers = []
            for qmslayer in qmslist:
                #print qmslayer
                if qmslayer['type'].upper() == layer.get('type').upper():
                    if getLayerDomain(qmslayer['url']) == getLayerDomain(layer.get('url')):
                        likely_already_qms = True
                        likely_qms_layers.append(qmslayer['url'])


            #   /Search

            row=dict()
            row['id'] = layer.get('id')
            row['name'] = layer.get('name').encode('utf8')
            row['type'] = layer.get('type')
            
            row['url'] = layer.get('url')
            print row['url']
            if row['type'] == 'tms':
                row['url_qms'] = url_osmlabTMS2qms(row['url'])
            elif row['type'] == 'wms':
                row['url_qms'] = url_osmlabWMS2qms(row['url']) + '?'
                
            row['start_date'] = layer.get('start_date')
            row['end_date'] = layer.get('end_date')
            row['country_code'] = layer.get('country_code')
            row['best'] = layer.get('best')
            row['overlay'] = layer.get('overlay')
            row['license_url'] = layer.get('license_url')
            row['likely_already_qms'] = likely_already_qms
            row['likely_qms_layers'] = likely_qms_layers
            row['available_projections'] = layer.get('available_projections')
            if row['type'] == 'wms':
                row['layers_qms'] = getLayersWMS(row['url'])
                row['format_qms'] = getFormatWMS(row['url'])
                row['getparams_qms'] = getParamsWMS(row['url']).lstrip('&')
            if 'attribution' in layer:
                if 'text' in layer['attribution']:
                    row['attribution_text'] = layer['attribution']['text'].encode('utf8')            
            if 'attribution' in layer:
                if 'url' in layer['attribution']:
                    row['attribution_url'] = layer['attribution']['url'].encode('utf8')
            if 'extent' in layer:
                if 'max_zoom' in layer['extent']:
                    row['max_zoom'] = layer['extent']['max_zoom']
                if 'min_zoom' in layer['extent']:
                    row['min_zoom'] = layer['extent']['min_zoom']
            #print layer
            #quit()
            #row['attribution_text'] = layer.get('attribution',{'text':''}).get('text')
            #row['attribution_url'] = layer.get('attribution').get('url')

            listwriter.writerow(row)