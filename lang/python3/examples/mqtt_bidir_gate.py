#!/usr/bin/env python3

'''
Created on 24.12.2017

@author: dz

Listen to all traffic on MQTT/UDP, pump updates to MQTT broker
'''

# will work even if package is not installed
import sys
sys.path.append('..')
#sys.path.append('../mqttudp')

import threading
#import re

import mqttudp.engine as me
import mqttudp.interlock
import mqttudp.config as cfg

import paho.mqtt.client as broker


cfg.set_group('mqtt-gate')
log = cfg.log

blackList=cfg.get('blacklist' )


SUBSCRIBE_TOPIC=cfg.config.get('mqtt-gate','subscribe' )
MQTT_BROKER_HOST=cfg.config.get('mqtt-gate','host' )
MQTT_BROKER_PORT=cfg.config.getint('mqtt-gate','port' )
#SUBSCRIBE_TOPIC="#"
#MQTT_BROKER_HOST="smart."
#MQTT_BROKER_HOST="iot.eclipse.org"



ilock = mqttudp.interlock.Bidirectional(5)

def broker_on_connect(client, userdata, rc, unkn):  # @UnusedVariable
    #print("Connected with result code "+str(rc))
    log.info("Connected with result code "+str(rc))
    client.subscribe(SUBSCRIBE_TOPIC)

def broker_on_message(client, userdata, msg):  # @UnusedVariable
    #print( msg )
#    if (len(blackList) > 0) and (re.match( blackList, msg.topic )):
    if cfg.check_black_list(msg.topic, blackList):
        log.info("To UDP BLACKLIST: "+ msg.topic+" "+str(msg.payload))
        #print("To UDP BLACKLIST: "+ msg.topic+" "+str(msg.payload))
        return
    if ilock.broker_to_udp(msg.topic, msg.payload):
        me.send_publish( msg.topic, msg.payload )
        log.info("To UDP: "+msg.topic+"="+str(msg.payload))
        #print("To UDP: "+msg.topic+"="+str(msg.payload))
    else:
        #print("BLOCKED to UDP: "+msg.topic+"="+str(msg.payload))
        log.info("BLOCKED to UDP: "+msg.topic+"="+str(msg.payload))





def broker_listen_thread(bclient):
    bclient.loop_forever()


def recv_packet_from_udp(pkt):
    global last
    if pkt.ptype != me.PacketType.Publish:
        return
    if last.__contains__(pkt.topic) and last[pkt.topic] == pkt.value:
        return
    last[pkt.topic] = pkt.value
    if ilock.udp_to_broker(pkt.topic, pkt.value):
        bclient.publish(pkt.topic, pkt.value, qos=0)
        #print( "From UDP: "+topic+"="+value )
        log.info( "From UDP: "+pkt.topic+"="+pkt.value )
    else:
        #print( "BLOCKED from UDP: "+topic+"="+value )
        log.info( "BLOCKED from UDP: "+pkt.topic+"="+pkt.value )


def udp_listen_thread(bclient):
    global last
    last = {}
    me.listen(recv_packet_from_udp)


if __name__ == "__main__":
    print( "Will exchange all the traffic between MQTT/UDP and MQTT broker at "+MQTT_BROKER_HOST )

    bclient = broker.Client()
    bclient.on_connect = broker_on_connect
    bclient.on_message = broker_on_message

    b_login  = None
    b_passwd = None

    if( cfg.config['mqtt-gate'].__contains__('login')):
        b_login  = cfg.config.get('mqtt-gate','login' )
    if( cfg.config['mqtt-gate'].__contains__('password')):
        b_passwd = cfg.config.get('mqtt-gate','password' )

    bclient.username_pw_set( b_login , b_passwd )

    bclient.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    #print("connected", bclient)
    log.info( "connected " + str(bclient) )

    blt = threading.Thread(target=broker_listen_thread, args=(bclient,))
    ult = threading.Thread(target=udp_listen_thread, args=(bclient,))

    blt.start()
    ult.start()

    blt.join()
    ult.join()
