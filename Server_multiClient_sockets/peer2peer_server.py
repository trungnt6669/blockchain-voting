import socket
import threading
import csv

#----------------------------------------------------------------------------------------------------------------------#
#--------------------------- These identifiers will be hard coded onto each machine -----------------------------------#
SERVER_ID = "Server0001"
SERVER_KEY = 10101

HOST = "localhost"
PORT_NUMBER = 999

COMMAND_LENGTH = 4
MACHINE_ID_LENGTH = 10
KEY_LENGTH = 5

#----------------------------------------------------------------------------------------------------------------------#
#--  --------------------------------List of all peers and their info -------------------------------------------------#
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
# ----------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------- Create Socket ------------------------------------------------------#
def makeserversocket(portNumber, backlog=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #-- allows us to reuse socket immediately after it is closed --#
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #-- binds to whatever IP Address the peer is assigne --#
    s.bind(("", portNumber))
    print("binding peer server socket to port %s" %((PORT_NUMBER)))
    s.listen(backlog)
    print("Listening for connections...")
    return s
# ---------------------------------------------------------------------------------------------------------------------#
# ---------------------- Parse recieved message into command, machineID, Key, and message ------------------------------#

'''function takes socket connection and reveives message which it then parses out to obtain the connecting peer's command, 
machineID, key, and message containing block to add to blockchain if that is the command. Returns tuple containing:
(command, machineID, Key, message)'''

def parse_incoming_message(incoming_message):

    # -- command 4 char long, machineID 10 char long, key 5 char long --#
    message_length = len(incoming_message)

    command = ""
    machineID = ""
    key = ""
    message = ""

    index = 0
    # -- Parse first four character to obtain command --#
    while(index < COMMAND_LENGTH):
        command += incoming_message[index]
        index += 1

    command = command.upper()

    # -- Parse next 10 characters to get machineID --#
    while index < (COMMAND_LENGTH + MACHINE_ID_LENGTH):
        machineID += incoming_message[index]
        index += 1

    # -- parse next five characters to get peer key --#
    while index < (COMMAND_LENGTH + MACHINE_ID_LENGTH + KEY_LENGTH):
        key += incoming_message[index]
        index += 1

    # -- Parse message which will contain block to add to blockchain --#
    while index < message_length:
        message += incoming_message[index]
        index += 1

    return (command, machineID, key, message)
#----------------------------------------------------------------------------------------------------------------------#
# --------------------------------------------- Authentication Function -----------------------------------------------#

'''Function takes the machineID and key that have been extracted from the parse_incoming_message function, and checks 
the list of peers to make sure the connecting peer is authorized to connect. If it is the function returns true, if not
returns false'''

def verify_incoming_peer(connection, machineID, key):

    found_match = False
    
    '''I need to figure out a way to get the ip address and the port number for this to work properly!!!'''
    
    '''
    ipAddress = connection.gethostbyname[0]
    portNumber = connection.getjhostbyname[1]
    '''
    ipAddress = ""
    portNumber = 999
    print("Machine login info is: %s %s %s %s" % (machineID, key, ipAddress, portNumber))
    # -------------------------------------------------------------------------------------------------------------#

    # -------------- Loop through list of clients and see if a match with login info is found -------------------#
    for x in peers:
        # -- Client's machine id and private key match so it is confirmed to connect --#
        if (x.machineID == machineID) and (x.privateKey == key):
            print("match found!")

            '''
            # -- Client's IP address does not match so we update it in the Client list --#
            if (x.ipAddress != ipAddress):
                x.change_ip_address(ipAddress)
                print("Updated IP Address: " + ipAddress)

            if (x.portNumber != portNumber):
                x.change_port_number(portNumber)
                print("Updated Port Number: " + str(portNumber))
            '''

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
                #p.ipAddress = ipAddress
                #p.portNumber = portNumber

                ipAddress = p.ipAddress
                portNumber = p.portNumber

                already_exist = True
                break
        if already_exist is False:
            with lock:
                registered_peers.append(Peer_Info(machineID, key, ipAddress, portNumber))
                print("Added to list of registered peers.")

        return True
# ---------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------- Handle connection -------------------------------------------------#
def handle_incoming_peer(connection):

    incoming_message = connection.recv(2048)
    incoming_message = incoming_message.decode()

    command, machineID, key, message = parse_incoming_message(incoming_message)

    if verify_incoming_peer(connection, machineID, key):
        print("peer verified")

        incoming_command_handler(connection, command, message)

    else:
        connection.send("ERRO".encode("utf-8"))
        #connection.close()
# ---------------------------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------------------------#
def handle_outgoing_peer(connection, address, command, message):

    outgoing_message = command+str(SERVER_ID)+str(SERVER_KEY)+message
    connection.send(outgoing_message.encode("utf-8"))

    handle_incoming_peer(connection)
#----------------------------------------------------------------------------------------------------------------------#
# ------------------ Command Handler takes commands from peer and performs necessary operation ------------------------#

'''This function take the command send to peer and handles it, performing the necessary operation in accordance with the
command. The peers identity has already been established at this point so that in not a concern. Once this function
finishes it exits and the function that called it is responsible for closing the connection'''

def incoming_command_handler(connection, command, incoming_message):

    global registered_peers

    machineID = ""
    key = ""
    ipAddress = ""
    port = ""

    outgoing_message = ""
#--------------------------Sever sends list of peers connected to peer to peer network --------------------------------#
    if command == "LIST":
        print("sending list of peers to %s " %(connection))

        outgoing_message = "PEER" + SERVER_ID + str(SERVER_KEY)

        for x in peers:
            outgoing_message += (str(x.machineID) + " " + str(x.privateKey) + " " + str(x.ipAddress) + " " + str(x.portNumber) + " ")

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))

#------------------------  Peer receives command to send copy of registered peer list ---------------------------------#
    elif command == "REGP":

        print("sending list of registered peers to %s " %(connection))

        outgoing_message = "REPL" + SERVER_ID + str(SERVER_KEY)

        for x in registered_peers:
            outgoing_message += (str(x.machineID) + " " + str(x.privateKey) + " " + str(x.ipAddress) + " " + str(x.portNumber) + " ")

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))

#----------------------------------------  Peer receive list of registered peers  -------------------------------------#
    elif command == "REPL":

        message_length = len(incoming_message)
        index = 0

        while index < message_length:

            # -- MachineID --#
            while (index < message_length) and (incoming_message[index] != " "):
                machineID += incoming_message[index]
                index += 1

            index += 1

            # -- Key --#
            while (index < message_length) and (incoming_message[index] != " "):
                key += incoming_message[index]
                index += 1

            index += 1

            # -- ipAddress --#
            while (index < message_length) and (incoming_message[index] != " "):
                ipAddress += incoming_message[index]
                index += 1

            index += 1

            # -- portNumber --#
            while (index < message_length) and (incoming_message[index] != " "):
                port += incoming_message[index]
                index += 1

            index += 1

        # -- Add peer to list of registered peers if not already there --#
            found = False
            for p in registered_peers:
                if (p.machineID == machineID) and (p.privateKey == key):
                    p.ipAddress = ipAddress
                    p.portNumber = port
                    found = True

            if found == False:
                registered_peers.append(Peer_Info(machineID, key, ipAddress, port))

#-------------------------------- Peer receives command to update it's blockchain -------------------------------------#
    elif command == "ADDB":

        print("Adding block to blockchain, sent from peer: %s " % (connection))
        block_chain.append(incoming_message)

        outgoing_message = "CONF" + SERVER_ID + str(SERVER_KEY)+ incoming_message

        print(outgoing_message)
        connection.send(outgoing_message.encode("utf-8"))

#-------------------------- Peer sends out command to update the blockchain with new block ----------------------------#
    #elif command == "SEND":

        #outgoing_message = outgoing_message = "ADDB" + SERVER_ID + str(SERVER_KEY)+ incoming_message
        #connection.send(outgoing_message.encode("utf-8"))
#-----------------------------------------------------------------------------------------------------------------------#
    elif command == "ERRO":
        print("error performing operation")
        #outgoing_message = outgoing_message = "QUIT" + SERVER_ID + str(SERVER_KEY)+ incoming_message

        #connection.send(outgoing_message.encode("utf-8"))
#---------------------------------------- Peer receives Command to close socket ---------------------------------------#
    #elif command == "QUIT":
        #connection.close()
#----------------------------------------------------------------------------------------------------------------------#
    else:
        print("Invalid input")
#----------------------------------------------------------------------------------------------------------------------#


#----------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------  Main body of program  ------------------------------------------------#

#-- Call function to read from csv table and populate peer and registered_peer lists --#
read_peer_info("peer_info_port.csv")


#server_socket.settimeout(2)

#peer, address = server_socket.accept()

#print(address[0] + " " + str(address[1]))
#print("Connection from: %s" % (peer))

#-- Create server socket to listen for connections --#
server_socket = makeserversocket(PORT_NUMBER)
while True:
	
    peer, address = server_socket.accept()
    print("Connection from: %s" %(peer))

    handle_incoming_peer(peer)
    '''
    #-- Create new thread to handle verification function --#
    t = threading.Thread(target=handle_incoming_peer(peer))
    t.daemon = True
    t.start()
    '''
#----------------------------------------------------------------------------------------------------------------------#

#server.close()
	
