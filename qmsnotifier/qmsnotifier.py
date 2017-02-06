#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import urllib
import json
import os
from bs4 import BeautifulSoup

#################BOT TOKEN##################
token = open('token').read().rstrip('\n')
#################BOT TOKEN##################

method = 'sendMessage'
chat_id = -1001084564203

def downloadqms():
    url='https://qms.nextgis.com/api/v1/geoservices/?format=json'
    filename='qms.json'
    testfile = urllib.URLopener()
    testfile.retrieve(url, filename)
    with open(filename) as data_file:    
        qmslist_new = json.load(data_file)
        
    return qmslist_new

def find_qms(id):
    #   Search in qms for layer
    exist_qms = False
    for qmslayer in qmslist_old:
        if id == qmslayer['id']:
                exist_qms = True

    return exist_qms

def get_name(guid):
    userpage = urllib.urlopen('https://my.nextgis.com/public_profile/' + guid).read()
    soup = BeautifulSoup(userpage, 'html.parser')
    divs = soup.findAll("div", { "class" : "form-group label-floating clearfix" })
    username = divs[0].next_element.next_element.next_element.next_element.strip(' ').strip('\n').strip(' ')
    
    return username
    
def notify(type,link,name,submitter):
    text = u'Новый %s сервис в QMS %s\n %s\n Добавил: %s' % (type,link,name,submitter)

    response = requests.post(
        url='https://api.telegram.org/bot{0}/{1}'.format(token, method),
        data={'chat_id': chat_id, 'text': text}
    ).json()
    print(response)
    
if __name__ == '__main__':
    #os.chdir('/home/sim/helper_scripts/qmsnotifier')
    os.remove("qms_old.json")
    os.rename("qms.json","qms_old.json")
    qmslist_new = downloadqms()
    
    with open("qms_old.json") as data_file:    
        qmslist_old = json.load(data_file)
    
    for item in qmslist_new:
        exist_qms = find_qms(item['id'])
        if exist_qms == False:
            #print('id' + str(item['id']))
            type = item['type'].upper()
            link = 'https://qms.nextgis.com/geoservices/' + str(item['id'])
            name = item['name']
            submitter = get_name(item['submitter'])
            notify(type,link,name,submitter)