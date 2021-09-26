#!/usr/bin/env python3

import requests
import json
import urllib3
import re
import random
import  configparser

def getFilename_fromCd(cd):
    """
    Get filename from content-disposition
    """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]

def random_ua():
    """
    From https://stackoverflow.com/a/65144558
    """
    response = requests.get('https://fake-useragent.herokuapp.com/browsers/0.1.11',verify=False)
    agents_dictionary = json.loads(response.text)
    random_browser_number = str(random.randint(0, len(agents_dictionary['randomize'])))
    random_browser = agents_dictionary['randomize'][random_browser_number]
    user_agents_list = agents_dictionary['browsers'][random_browser]
    user_agent = user_agents_list[random.randint(0, len(user_agents_list)-1)]
    return user_agent

urllib3.disable_warnings()



#URLs del servicio
base_url = 'https://ccdservicios.scsalud.es/api/v1/'
verifica_datos = 'citizen/request-pin'
solicita_pin = 'citizen/send-pin'
verifica_pin = 'citizen/check-pin'
solicita_token = 'citizen/request-token'
certificado_pdf = 'dgc/generate-cert/vaccination/pdf'
certificado_digital = 'citizen/request-pin-and-url'
certificado_qr = 'dgc/generate-cert/vaccination/pwa'

#UA aleatorio
user_agent = random_ua()

#Datos para el certificado

config_object = configparser.ConfigParser()
fichero_config = config_object.read("dgc.properties")
if len(fichero_config) != 1:
    print("No se encuentra el fichero de configuración dgc.properties")
    exit()
datos_usuario = config_object["USERINFO"]

try:
    nombre = datos_usuario["NOMBRE"].upper()
    apellidos = datos_usuario["APELLIDOS"].upper()
    dni = datos_usuario["DNI"].upper()
    nacimiento = datos_usuario["NACIMIENTO"]
    tlf = datos_usuario["TELEFONO"]
except KeyError:
    print("El archivo de configuración dgc.properties no es correcto")
    exit()    

#Solicitud del token para pedir PIN (validez de 5 minutos)
datos = {'phoneNumber': tlf,'identityDocument': dni,'birthdate': nacimiento}
cabeceras = {'User-Agent': user_agent}
response = requests.post(base_url+verifica_datos,json=datos,verify=False,headers=cabeceras)
token = response.json()['tokenAuth']

#Solicitud de envío de PIN
cabeceras = {'Authorization': 'Bearer ' + token,'User-Agent': user_agent}
datos = {'phoneNumber': tlf,'identityDocument': dni,'birthdate': nacimiento, 'phoneAuthRequiredMessage' : "Usted NO ha dado CONSENTIMIENTO sobre este TELÉFONO para envío de SMS desde el servicio de salud, ¿DESEA DAR SU CONSENTIMIENTO A ESTE TELÉFONO AHORA?"}
response = requests.post(base_url+solicita_pin,json=datos,headers=cabeceras,verify=False)

pin = input("Introduce el PIN recibido: ")

#Verificación del PIN, devuelve un token nuevo (validez de 24h)
cabeceras = {'Authorization': 'Bearer ' + token,'User-Agent': user_agent}
datos = {'pin': pin, 'phoneNumber': tlf,'identityDocument': dni,'birthdate': nacimiento, 'phoneAuthRequiredMessage' : "Usted NO ha dado CONSENTIMIENTO sobre este TELÉFONO para envío de SMS desde el servicio de salud, ¿DESEA DAR SU CONSENTIMIENTO A ESTE TELÉFONO AHORA?"}
response = requests.post(base_url+verifica_pin,json=datos,headers=cabeceras,verify=False)
if response.status_code == 200:
    token = response.json()['token']
else:
    print("El código no es correcto, reinicie el script")
    exit()

#Obtención del certificado en PDF
datos = {'identityDocument': dni,'birthdate': nacimiento, 'phoneNumber': tlf, 'name' : nombre , 'surname' : apellidos}
cabeceras = {'Authorization': 'Bearer ' + token, 'Origin' : 'https://ccdcantabria.scsalud.es', 'Referer': 'https://ccdcantabria.scsalud.es/' , 'User-Agent': user_agent}
response = requests.post(base_url+certificado_pdf,json=datos,verify=False,headers=cabeceras)
if response.status_code == 200:
    filename = getFilename_fromCd(response.headers.get('content-disposition'))
    open(filename, 'wb').write(response.content)
    print("Certificado guardado como "+filename)
else:
    print("El certificado no se descargó correctamente")