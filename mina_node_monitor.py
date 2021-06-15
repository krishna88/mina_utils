import time
import datetime
import sys
import yaml
import telegram
import os
from MinaPyClient import Client
from time import sleep
import logging

c = yaml.load(open('config.yml', encoding='utf8'), Loader=yaml.SafeLoader)

TELEGRAM_TOKEN      = str(c["TELEGRAM_TOKEN"])
CHAT_ID             = str(c["CHAT_ID"])
CHAT_ID_ALERT       = str(c["CHAT_ID_ALERT"])
NODE_NAME           = str(c["NODE_NAME"])
GRAPHQL_HOST        = str(c["GRAPHQL_HOST"])
GRAPHQL_PORT        = int(c["GRAPHQL_PORT"])
WAIT_TIME_IN_CHECKS        = int(c["WAIT_TIME_IN_CHECKS"])
CHECK_FREQ_IN_MIN        = int(c["CHECK_FREQ_IN_MIN"])

bot=telegram.Bot(token=TELEGRAM_TOKEN)


COUNT = 0 

def record_status(msg, type="standard"):
    # sending a telgram message
    chat_id = CHAT_ID
    chat_id_alert  = CHAT_ID_ALERT
    bot.sendMessage(chat_id=chat_id, text=msg, timeout=20)

    # additional message to the alert channel
    if type=="alert":
        bot.sendMessage(chat_id=chat_id_alert, text=msg, timeout=20)
    
    # this is for the console
    print(msg) 
    
    # to record in log file  
    ln = logging.getLogger('main_logger')
    ln.setLevel('INFO')  
    fh = logging.FileHandler('nodestatus_logs/nodestatus_{:%Y%m%d}.log'.format(datetime.datetime.now()))
    ln.addHandler(fh)
    ln.info(msg)
    ln.handlers.clear() # to avoid multiple instances of loggers getting created

def get_node_status():
    attempts = 0
    while attempts < 3: # tries 3 times to get node status before raising exception
        try:
            coda = Client(graphql_host=GRAPHQL_HOST, graphql_port=GRAPHQL_PORT)
            daemon_status = coda.get_daemon_status()
            sync_status = daemon_status['daemonStatus']['syncStatus']
            uptime = daemon_status['daemonStatus']['uptimeSecs'] 	
            blockchainLength = daemon_status['daemonStatus']['blockchainLength']
            highestBlockLengthReceived = daemon_status['daemonStatus']['highestBlockLengthReceived']
            highestUnvalidatedBlockLengthReceived = daemon_status['daemonStatus']['highestUnvalidatedBlockLengthReceived']
            try:
                nextBlockTime = daemon_status['daemonStatus']['nextBlockProduction']['times'][0]['startTime']
            except:
                nextBlockTime = 100000

            return {    "sync_status": sync_status, 
                        "uptime": uptime, 
                        "blockchainLength": blockchainLength, 
                        "highestBlockLengthReceived": highestBlockLengthReceived, 
                        "highestUnvalidatedBlockLengthReceived": highestUnvalidatedBlockLengthReceived,
                        "nextBlockTime": nextBlockTime
                    }
        except:
            attempts += 1
            if attempts == 2:
                return None

def restart_node():
    #restart mina daemon
    os.system("systemctl --user restart mina")
    sleep(60*5)
    #restart sidecar
    os.system("service mina-bp-stats-sidecar restart")
    #update telegram on restart
    record_status(NODE_NAME + " | mina daemon and sidecar has been restarted")

def check_node_sync():
    d = get_node_status()
    global COUNT

    if d == None:
        msg = NODE_NAME + " | unable to reach mina daemon. Attention required!!!"
        record_status(msg, type='alert')
    else:
        try: #fix for issue with length provided as NoneType by daemon
            delta_height = int(d["highestUnvalidatedBlockLengthReceived"]) -  int(d["blockchainLength"])
        except:
            delta_height = "NA"
    
        current_epoch_time = int(time.time()*1000)
        next_block_in_sec = int(d["nextBlockTime"]) - current_epoch_time
        next_block_in = str(datetime.timedelta(milliseconds=next_block_in_sec)).split(".")[0]
        uptime_readable = str(datetime.timedelta(seconds=d["uptime"]))
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        base_msg = current_time + "|" + NODE_NAME + "|" + d["sync_status"] + "|" + uptime_readable + "|" + str(d["blockchainLength"]) + "|" + \
                    str(d["highestBlockLengthReceived"]) + "|" + str(d["highestUnvalidatedBlockLengthReceived"]) + "|" + \
                    str(delta_height) + "|" + next_block_in + "| "
        
        # Action logic for different scenarios
        if d["sync_status"] == "SYNCED" and delta_height == 0: #perfect scenario
            msg = base_msg + "no action taken"
            record_status(msg)
            COUNT = 0


        elif d["sync_status"] in {"SYNCED","CATCHUP"} and COUNT <= WAIT_TIME_IN_CHECKS: #OK to wait a few minutes    
            msg = base_msg + "waiting for few mins" 
            record_status(msg, type='alert')
            COUNT = COUNT + 1

        elif d["sync_status"] in {"SYNCED","CATCHUP"}  and COUNT > WAIT_TIME_IN_CHECKS: #restart routine  
            msg = base_msg + "restarting node"  
            record_status(msg, type='alert')
            restart_node()
            COUNT = 0   
          
        else:
            msg = base_msg + " in unknown mode. Attention required"
            record_status(msg, type='alert')

def checksidecarstatusandrestart():
    command = 'journalctl -u mina-bp-stats-sidecar.service --since "10 minutes ago" | grep -c "Got block data"'
    output,error  = subprocess.Popen(
                    command, universal_newlines=True, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    print(f'Total sidecar updates sent in 10 mts is {output}.')
    if int(output) < 2:
        os.system("service mina-bp-stats-sidecar restart")
        record_status(NODE_NAME + " | sidecar has been restarted")


if __name__ == "__main__": 
       
    while True:
        try:
            check_node_sync()
            checksidecarstatusandrestart()
        except Exception as e:
            msg = str(e)
            record_status(msg, type='alert')
        sleep(60*CHECK_FREQ_IN_MIN)
    