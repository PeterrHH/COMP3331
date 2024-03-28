import sys
import random
import socket
import time
import threading
import random
from dataclasses import dataclass
import utils.Constant as Constant
import utils

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
        self.init_seqno = utils.gen_random()

    def get_state(self):
        return self.state
        
    def transit(self,state):
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state

    def get_segment(self,type_field,seqno_field,data=None):
        if data:
            pass
        else:
            sent_segment = type_field + seqno_field
        return sent_segment
    '''
    Initial Handshake, sent SYN and wait for ACK
    if no ACK for rto amount of time
    resent the SYN

    '''

    def send_setup(self):
        self.curr_seqno = self.init_seqno
        type_num = Constant.SYN
        type_field = type_num.to_bytes(2,"big")
        seqno_field = type_num.to_bytes(2,"big")
        sent_segment = self.get_segment(type_field,seqno_field)
        self.socket.send(sent_segment)
        self.transit("SYN_SENT")
        pass

    def send_data(file_name):
        pass

    def receive(self):

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
                    # Starting sendng file
            except socket.timeout:
                continue
            except ConnectionRefusedError as e:
                print(f"Connection refused error: {e}")
                break
            except KeyboardInterrupt:
                print("Server stopped by user")
                break

            
            print(f"T- ESTABLISH")
            # Connection established


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
    
    '''
    Add Threading
    Thread for Receiving
    
    '''
    receiver = threading.Thread(target = control.receive) #
    receiver.start()

    # # threading.Timer()
    # control.receive()
    try:
        while control.is_alive:
            if control.get_state() == "CLOSED" or control.get_state == "SYN_SENT":
                try:
                    control.send_setup()
                    if control.get_state() == "ESTABLISHED":
                        break
                except control.socket.timeout:
                    control.send_setup()
            else:
                # Connectoin established, ready to sent file
                control.send_data(txt_file_to_send)
                pass
    except KeyboardInterrupt:
        print(f"Control Z is PRESSED")

    finally:
        receiver.join()
        print(f"control satte is {control.get_state()}")
        control.socket.close()  # Close the socket

        print("Shut down complete.")

        sys.exit(0)
'''
1. The sender should first open a UDP socket on sender_port and initiate a two-way
handshake (SYN, ACK) for the connection establishment. The sender sends a SYN segment, and
the receiver responds with an ACK. This is different to the three-way handshake implemented by
TCP. If the ACK is not received before a timeout (rto msec), the sender should retransmit the
SYN.

FLP: probabiility of DATA SYN or FIN created by sender being dropped
RLP: Determine prob of an ACK in reverse direction from the sender being dropped

python3 sender.py 49998 59998 a.txt 1200 3000 0.1 0.05

USE WIRESHARK TO TEST
'''