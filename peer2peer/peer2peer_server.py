
'''
The header for each byte stream sent and received is of the following format:
XXXXXXXXXX YYYYY Z* A* BBBB C*

- X represents the 10 character id of the sender
- Y represents the 5 character key of the sender
- Z represents any number of characters representing the ip address of the sender
- A represents any number of characters representing the port number of the sender
- B represents the uppercase 4 character command
- C represents the any number of characters making up the message sent

MACHINE_ID-MACHINE_KEY-IP_ADDRESS-PORT_NUMBER-COMMAND-MESSAGE
'''
import socket
import threading
import csv
import time

#----------------------------------------------------------------------------------------------------------------------#
#--------------------------- These identifiers will be hard coded onto each machine -----------------------------------#
SERVER_ID = "Server0001"
SERVER_KEY = "10101"

HOST = "localhost"
IP_ADDRESS = socket.gethostbyname(socket.getfqdn())
PORT_NUMBER = "999"

#-- This message header will be used to send every message for verification purposes --#
MESSAGE_HEADER = SERVER_ID + "|" + SERVER_KEY + "|" + IP_ADDRESS + "|" + PORT_NUMBER

#----------------------------------------------------------------------------------------------------------------------#
#------------------------------------List of all peers and their info -------------------------------------------------#
peers = []
registered_peers = [] #-- List of peer connected to the network --#
#----------------------------------------------------------------------------------------------------------------------#
#----------------------------------------- Lock to prevent race conditions --------------------------------------------#
lock = threading.Lock()
#----------------------------------------------------------------------------------------------------------------------#
#-------------------------------------- Block Chain will replace this list --------------------------------------------#
block_chain = []
#----------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------#
#------------------------------------------ Class for holding client info ---------------------------------------------#
class Peer_Info:
    #-- Constructor --#
    def __init__(self, machineID, privateKey, ipAddress, portNumber):
        self.machineID = machineID
        self.privateKey = privateKey
        self.ipAddress = ipAddress
        self.portNumber = portNumber

    def change_ip_address(self, ipAddress):
        self.ipAddress = ipAddress

    def change_port_number(self, portNumber):
        self.portNumber = portNumber

#----------------------------------------------------------------------------------------------------------------------#
#------------------- Import peer info from csv file and place into list of Client Info objects ------------------------#
def read_peer_info(CSV_file_to_read):
    global peers
	
    with open(CSV_file_to_read) as csvFile:
        readCSV = csv.reader(csvFile, delimiter=',')

        for row in readCSV:
            machineID = row[0]
            privateKey = row[1]
            ipAddress = row[2]
            portNumber = row[3]

            peers.append(Peer_Info(machineID,privateKey,ipAddress,portNumber ))

        for x in peers:
            print("machine ID: ", x.machineID, " private key: ", x.privateKey, " IP Address: ", x.ipAddress, x.portNumber)
# ---------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------ Create Socket ------------------------------------------------------#
def makeserversocket(portNumber, backlog=5):

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #-- allows us to reuse socket immediately after it is closed --#
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #-- binds to whatever IP Address the peer is assigne --#
    s.bind(("", int(portNumber)))
    s.listen(backlog)

    print("binding peer server socket to port " + portNumber)
    print("Listening for connections...")
    return s
#------------------- Schedule outgoing message to inform peer that it is now the "leader" -----------------------------#
def choose_the_leader():
    start_time = time.time()
    print("Appoint Leader...")

    i = 0
    while True:

        time.sleep(5.0)
        length = len(registered_peers)

        if i >= length:
            i = 0

        if length > 0:
            outgoing_message = MESSAGE_HEADER +"|" + "LEAD" + "|" + ""

            try:
                #send message to node that it is the leader
                sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except socket.error as msg:
                print(str(msg))

            try:
                sender.connect((registered_peers[i].ipAddress, int(registered_peers[i].portNumber)))
            except socket.error as msg:
                print(str(msg))

            try:
                sender.send(outgoing_message.encode("utf-8"))
            except socket.error as msg:
                print(str(msg))

            sender.close()
            i +=1
#----------------------------------------------------------------------------------------------------------------------#
# --------------------------------------------- Authentication Function -----------------------------------------------#
'''
Function takes the machineID and key that have been extracted from the parse_incoming_message function, and checks 
the list of peers to make sure the connecting peer is authorized to connect. If it is the function returns true, if not
returns false
'''

def verify_incoming_peer(connection, machineID, key, ip_address, port_number):

    found_match = False

    print("Machine login info is: " + machineID + " " + key + " " + ip_address + " " + port_number)
    # -------------------------------------------------------------------------------------------------------------#

    # -------------- Loop through list of clients and see if a match with login info is found -------------------#
    for x in peers:
        # -- Client's machine id and private key match so it is confirmed to connect --#
        if (x.machineID == machineID) and (x.privateKey == key):
            print("match found!")

            # -- Client's IP address does not match so we update it in the Client list --#
            if (x.ipAddress != ip_address):
                x.change_ip_address(ip_address)
                print("Updated IP Address: " + ip_address)

            if (x.portNumber != int(port_number)):
                x.change_port_number(port_number)
                print("Updated Port Number: " + port_number)

            # -- Match found so update variable --#
            found_match = True
            break
    # ------------------------------------------------------------------------------------------------------------#
    # ------------------------------------------- Peer failed to connect to ----------------------------------------#
    if found_match is False:
        print("Peer failed to provide a valid machine name and/or key.")
        return False
    # -----------------------------------------------------------------------------------------------------------------#
    # -------------------------------------- Client successfully connected --------------------------------------------#
    else:
        already_exist = False

        # -- Add socket to list of connections --#
        for p in registered_peers:
            if p.machineID == machineID:
                p.ipAddress = ip_address
                p.portNumber = port_number

                already_exist = True
                break
        if already_exist is False:
            with lock:
                registered_peers.append(Peer_Info(machineID, key, ip_address, port_number))
                print("Added to list of registered peers.")

        return True
# ---------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------- Handle connection -------------------------------------------------#
def handle_incoming_peer(connection):

    incoming_message = connection.recv(2048)
    incoming_message = incoming_message.decode()

    machine_id, key, ip_address, port_number, command, message = incoming_message.split("|", 6)

    #machine_id, key, ip_address, port_number, command, message = parse_incoming_message(incoming_message)

    if verify_incoming_peer(connection, machine_id, key, ip_address, port_number):
        print("peer verified, command: " + command)

        incoming_command_handler(connection, ip_address, port_number, command, message)

    else:
        outgoing_message = MESSAGE_HEADER + "|" + "ERRO" + "|" + ""
        connection.send(outgoing_message.encode("utf-8"))
# ---------------------------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------------------------#
def handle_outgoing_peer(connection, command, message=""):

    outgoing_message = MESSAGE_HEADER + "|" + command + "|" + message
    connection.send(outgoing_message.encode("utf-8"))

    handle_incoming_peer(connection)
#----------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------#
# ------------------ Command Handler takes commands from peer and performs necessary operation ------------------------#

def incoming_command_handler(connection, ip_address, port_number, command, incoming_message):
    global registered_peers

    outgoing_message = ""
    #---------------Server receives command to send list of peers elligible to connect to network ---------------------#
    if command == "INIT":

        print("sending list of peers to %s " %(connection))

        outgoing_message = MESSAGE_HEADER + "|" + "PEER" + "|" + ""

        for x in peers:
            #outgoing_message += (str(x.machineID) + " " + str(x.privateKey) + " " + str(x.ipAddress) + " " + str(x.portNumber) + " ")
            outgoing_message += (x.machineID + " " + x.privateKey + " " + x.ipAddress + " " + x.portNumber + " ")

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))

    #------------------------  Server receives command to send copy of registered peer list -----------------------------#
    elif command == "REGP":

        print("sending list of registered peers to %s " %(connection))

        outgoing_message = MESSAGE_HEADER + "|" + "REPL" + "|" + ""

        for x in registered_peers:
            #outgoing_message += (str(x.machineID) + " " + str(x.privateKey) + " " + str(x.ipAddress) + " " + str(x.portNumber) + " ")
            outgoing_message += (x.machineID + " " + x.privateKey + " " + x.ipAddress + " " + x.portNumber + " ")

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))

    #------------------------------------------------------------------------------------------------------------------#
    #--------------- Peer receive request from another node to join it's list of registered peers ---------------------#
    elif command == "JOIN":
        outgoing_message = MESSAGE_HEADER + "|" + "WELC" + "|" + incoming_message
        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))
    #------------------------------------------------------------------------------------------------------------------#
	#----------------------------- Server receives command to update it's blockchain ----------------------------------#
    elif command == "ADDB":

        print("Adding block to blockchain, sent from peer: %s " % (connection))
        block_chain.append(incoming_message)

        outgoing_message = MESSAGE_HEADER + "|" + "CONF" + "|" + incoming_message

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))
    #------------------------------------------------------------------------------------------------------------------#
	#-------- Server receives error message notifying it that something went wrong durring communication ----------------#
    elif command == "ERRO":
        print("error performing operation")
    #------------------------------------------------------------------------------------------------------------------#
    # ----------------------- Server receives notification that peer has quit the network -----------------------------#
    elif command == "QUIT":
        outgoing_message = MESSAGE_HEADER + "|" + "DONE" + "|" + incoming_message
        connection.send(outgoing_message.encode("utf-8"))

        for i, p in enumerate(registered_peers):
            if (p.ipAddress == ip_address) and (p.portNumber == port_number):
                print("Peer: %s signed off from network." %(p.machineID))
                del registered_peers[i]
    #------------------------------------------------------------------------------------------------------------------#
	#------------------------------------------ Recieves invalid input ------------------------------------------------#
    else:
        outgoing_message = MESSAGE_HEADER + "|" + "ERRO" + "|" + incoming_message

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))
        print("Invalid input")
    #------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------#

#----------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------  Main body of program  ------------------------------------------------#

#-- Call function to read from csv table and populate peer and registered_peer lists --#
read_peer_info("peer_info_port.csv")

#-- Create server socket to listen for connections --#
server_socket = makeserversocket(PORT_NUMBER)

t1 = threading.Thread(target=choose_the_leader,)
t1.daemon = True
t1.start()

#-- Infinite loop listens for peers connecting --#
while True:
    print("Entering infinite loop")

    peer, address = server_socket.accept()
    print("Connection from: %s" %(peer))

    #handle_incoming_peer(peer)

    #-- Create new thread to handle verification function --#
    t2 = threading.Thread(target=handle_incoming_peer, args=(peer,))
    t2.daemon = True
    t2.start()

#----------------------------------------------------------------------------------------------------------------------#

#server.close()
	
