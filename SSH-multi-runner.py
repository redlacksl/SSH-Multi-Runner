# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 20:38:34 2015
@author: sredlack

See here for inspiration:
https://pynet.twb-tech.com/blog/python/paramiko-ssh-part1.html
http://jessenoller.com/blog/2009/02/05/ssh-programming-with-paramiko-completely-different
http://docs.paramiko.org/en/1.16/index.html

"""

import paramiko
import getpass
import os.path
import sys
import threading
import re
import yaml
from datetime import date
from time import sleep

WAIT_TIME = 2

# Delay new threads by this number of seconds to reduce load on the auth server
THREAD_PERIOD = 3

class myThread (threading.Thread):
    def __init__(self, ip, commands, regex, log):
        threading.Thread.__init__(self)
        self.ip = ip
        self.commands = commands
        self.regex = regex
        self.log = log
    def run(self):
        print ("Starting " + self.ip)
        run_script(self.ip, self.commands, self.regex, self.log)
        print ("Exiting " + self.ip)

def run_script(ip, commands, regex, log):
     # setup the connection
    log_string = ""
    log_string = log_string + "\r\nConnecting to " + ip + "\r\n"
    try:
        client=paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password)
    except Exception as error:
        log_string = log_string + str(error.args[0])
        log.write(log_string.encode())
        client.close()
        return
    shell_channel = client.invoke_shell()
    while (shell_channel.recv_ready() == False): sleep(WAIT_TIME)
    print("Receiving response from " + ip)  
    shell_channel.recv(1000)

    for command in commands:
        shell_channel.send(command)
        print("Sent: " + command + " to " + ip)
        while (shell_channel.recv_ready() == False): sleep(WAIT_TIME)
        print("Receiving response from " + ip)
        sleep(WAIT_TIME)
        receive = shell_channel.recv(10000)
        log_string = log_string + receive.decode()
    print("Applying regex",regex)
    # If there is no regex, then save the whole output
    if not regex:
        log.write(log_string.encode())
    else:
        parse = re.search(regex, log_string)
        if parse != None:
            print("Found",str(parse.group(0)))
            # Write the output to the log
            log.write(str('Output for ' + ip + ',').encode())       
            log.write(str(parse.group(0)).encode())
            log.write(str("\r\n").encode())
        else:
            log.write(str('Output for ' + ip + ',None\r\n').encode())
    # Close the connection when done
    print("Closing connection to " + ip)
    client.close()
    return


# MAIN PROGRAM

sa = sys.argv
lsa = len(sys.argv)
print("Found",lsa,"args")
for i in sa: print(i)
if lsa != 2:
    print ("Usage: [ python ] SSH-multi-runner.py script_file_name")
    print ("Example: [ python ] SSH-multi-runner.py script_file_name.txt")
    sa.append(input("Filename: "))

os.chdir(os.path.dirname(sa[1]))
with open(sa[1]) as f:
    script = yaml.load(f)
print(script)

username = script['username']
password = getpass.getpass(prompt="Password: ")

# Double-check the password to prevent fat finger errors
password_check = getpass.getpass(prompt="Verify Password: ")
if password != password_check:
    print ("Mismatched Password. Please rerun to try again.")
    exit()

log_path = date.today().isoformat() + "_log.txt"
log = open(log_path, 'ab')
log.write('\r\n'.encode())

# Setup the command list
print('Commands are:', script['commands'])

# Setup the ip list
print('IPs are:', script['targets'])

# Setup the regex
print('Regex is:', script['regex'])

# Build the threads
threadList = []    
for ip in script['targets']:
    threadList.append(myThread(ip, script['commands'], script['regex'], log))

# Run the threads
for t in threadList:
    t.start()
    sleep(THREAD_PERIOD)
    
# Wait for all threads to finish
for t in threadList:
    t.join()
   
# Close the log when all done
log.close() 

print("Completed. Exiting.")

