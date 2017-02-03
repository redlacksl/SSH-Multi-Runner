# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 20:38:34 2015
@author: sredlack

See here for inspiration:
https://pynet.twb-tech.com/blog/python/paramiko-ssh-part1.html
http://jessenoller.com/blog/2009/02/05/ssh-programming-with-paramiko-completely-different
http://docs.paramiko.org/en/1.16/index.html

"""

import csv
import paramiko
import getpass
import os.path
import sys
import threading
import re
from datetime import date
from time import sleep

WAIT_TIME = 2

# Delay new threads by this number of seconds to reduce load on the auth server
THREAD_PERIOD = 3

def read_tag_block(filename, tag, add_newline = False):
    values = []
    with open(filename) as f:
        lines = list(csv.reader(f))
        for line in lines:
            the_line = line[0]
            if the_line.startswith(tag):               
                value = the_line.split(':')[1]
                 # Handle the case where a command is just 'enter'
                if (len(value) == 1): values.append('\n')
                else:
                    if add_newline:
                        values.append(value + '\n')
                    else:
                        values.append(value)
        return values
        
def read_commands(filename):
    commands = []
    with open(filename) as f:
        lines = list(csv.reader(f))
        for line in lines:
            the_line = line[0]
            if the_line.startswith("command:"):               
                command = the_line.split(':')[1]
                 # Handle the case where a command is just 'enter'
                if (len(command) == 1): commands.append('\n')
                else: commands.append(command + '\n')
        return commands
            
def read_ips(filename):
    ips = []
    with open(filename) as ip_list:
        lines = list(csv.reader(ip_list))
        for line in lines:
            the_line = line[0]
            if the_line.startswith("target:"):
                ips.append(the_line.split(':')[1])
    return ips

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
username = read_tag_block(sa[1],'username:')[0]
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
commands = read_tag_block(sa[1],'command:', add_newline = True)
print(commands)

# Setup the ip list
ips = read_tag_block(sa[1],'target:')
print(ips)

# Setup the regex
regex = read_tag_block(sa[1],'regex:')[0]
print(regex)

# Build the threads
threadList = []    
for ip in ips:
    threadList.append(myThread(ip, commands, regex, log))

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

