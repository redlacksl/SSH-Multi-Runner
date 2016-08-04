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
from datetime import date
from time import sleep

WAIT_TIME = 2

def read_commands(filename):
    commands = []
    with open(sa[1]) as f:
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
    def __init__(self, ip, commands, log):
        threading.Thread.__init__(self)
        self.ip = ip
        self.commands = commands
        self.log = log
    def run(self):
        print ("Starting " + self.ip)
        run_script(self.ip, self.commands, self.log)
        print ("Exiting " + self.ip)

def run_script(ip, commands, log):
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
 
    # Write the output to the log       
    log.write(log_string.encode())
    # Close the connection when done
    print("Closing connection to " + ip)
    client.close()
    return


# MAIN PROGRAM

sa = sys.argv
lsa = len(sys.argv)
if lsa != 3:
    print ("Usage: [ python ] nora2.py script_file_name username")
    print ("Example: [ python ] nora2.py script_file_name.txt stephen.redlack")
    sa.append(input("Filename: "))
    sa.append(input("Username: "))

os.chdir(os.path.dirname(sa[1]))
username = sa[2]
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
commands = read_commands(sa[1])
print(commands)

# Setup the ip list
ips = read_ips(sa[1])
print(ips)

# Build the threads
threadList = []    
for ip in ips:
    threadList.append(myThread(ip, commands, log))

# Run the threads
for t in threadList:
    t.start()
    
# Wait for all threads to finish
for t in threadList:
    t.join()
   
# Close the log when all done
log.close() 

input("All done. Press enter to exit.")
