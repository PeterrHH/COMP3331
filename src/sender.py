import sys
import random
import socket
import time
import threading
import random
from dataclasses import dataclass
import Constant

'''

Message format

--------------------------------------------------
type 2 btyes | seqno 2 byte | Data 0 to MSS byte |
--------------------------------------------------
MSS = 1000 bytes
'''




# @dataclass
class Control:
    """Control block: parameters for the sender program."""
    def __init__(self,
                sender_port: str  ,      # Port number of sender
                receiver_port: int ,     # Port number of the receiver
                socket: socket.socket ,  # Socket for sending/receiving messages
                rto: int ,               # retrainsimission timer in Milliseconds
                is_alive = True   # Flag to signal the sender program to terminate) -> None:
                ):
        self.sender_port = sender_port
        self.receiver_port = receiver_port
        self.socket = socket
        self.rto = rto
        self.is_alive = is_alive
        self.socket.settimeout(self.rto/1000)
        self.all_state = ["CLOSED","SYN_SENT","ESTABLISHED","CLOSING","FIN_WAIT"]
        self.state = "CLOSED"
        self.curr_seqno = 0
        self.handshake()

        
    def transit(self,state):
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state
    '''
    Initial Handshake, sent SYN and wait for ACK
    if no ACK for rto amount of time
    resent the SYN
    '''
    def handshake(self):
        if self.state != "CLOSED":
            sys.exit(f"Sender Handshaking when not CLOSED")
        seqno = random.randrange(2**16-1) 
        self.curr_seqno = seqno
        type_num = Constant.SYN
        type_field = type_num.to_bytes(2,"big")
        seqno_field = type_num.to_bytes(2,"big")
        sent_segment = type_field + seqno_field
        print(f"add is {Constant.ADDRESS} port is {self.sender_port}")
        self.socket.send(sent_segment)
        #self.socket.sendto(sent_segment,(Constant.ADDRESS,self.receiver_port))
        self.transit("SYN_SENT")
        print(f"state in sender is {self.state}")
        # waiting on the ACK
        while True:
            try: 
                print(f"waiting")
                buf, addr = self.socket.recvfrom(2048)
                print(buf)
                type_field = int.from_bytes(buf[:2],byteorder='big')
                seqno_field = int.from_bytes(buf[2:4],byteorder='big')
                if type_field == Constant.ACK:
                    # transit state
                    self.transit("ESTABLISHED")
                    print(f"state in sender is {self.state}")
            except socket.timeout:
                self.socket.send(sent_segment)
            except ConnectionRefusedError as e:
                print(f"Connection refused error: {e}")
                break
                        

    



def setup_socket(host, port):
    """Setup a UDP socket for sending messages and receiving replies.
    Args:
        host (str): The hostname or IP address of the receiver.
        port (int): The port number of the receiver.
    Returns:
        socket: The newly created socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # UDP sockets are "connection-less", but we can still connect() to
    # set the socket's peer address.  The peer address identifies where 
    # all datagrams are sent on subsequent send() calls, and limits the
    # remote sender for subsequent recv() calls.
    try:
        sock.connect((host, port))
    except Exception as e:
        sys.exit(f"Failed to connect to {host}:{port}: {e}")

    sock.settimeout(0)  # Set socket to non-blocking mode

    return sock
def parse_port(port_str, min_port=49152, max_port=65535):
    try:
        port = int(port_str)
    except ValueError:
        sys.exit(f"Invalid port argument, must be numerical: {port_str}")
    
    if not (min_port <= port <= max_port):
        sys.exit(f"Invalid port argument, must be between {min_port} and {max_port}: {port}")
                 
    return port

'''
Initiate handshake with receiver:
- send a SYN segment
- expect to receive ACK back
- if over rto time, resend SYN segment
'''
def handshake(control,rto):

    while control.is_alive:
        
        break

    pass

if __name__ == "__main__":

    sender_port = parse_port(sys.argv[1])
    receiver_port = parse_port(sys.argv[2])
    txt_file_to_send = sys.argv[3] # name of text file
    max_win = sys.argv[4] #  the maximum window size in bytes for the sender window
    rto = int(sys.argv[5]) # retrainsimission timer in Milliseconds
    flp = sys.argv[6] # forward lost probability
    rlp = sys.argv[7] # reverse loss probability
    sock = setup_socket(Constant.ADDRESS, receiver_port)
    # initialise a control block

    control = Control(
        sender_port = sender_port,
        receiver_port= receiver_port,
        socket= sock,
        rto = rto)
    
    control.socket.close()  # Close the socket

    print("Shut down complete.")

    sys.exit(0)
'''
1. The sender should first open a UDP socket on sender_port and initiate a two-way
handshake (SYN, ACK) for the connection establishment. The sender sends a SYN segment, and
the receiver responds with an ACK. This is different to the three-way handshake implemented by
TCP. If the ACK is not received before a timeout (rto msec), the sender should retransmit the
SYN.

'''