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
                max_win: int,           # maximum number of unACKed bytes sent. i.e. max size of BUFFER
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
        self.max_win = max_win
        self.init_seqno = utils.gen_random()
        self.buffer = []
        self.timer = None
        self.start_time = None

    def get_state(self):
        return self.state
        
    def transit(self,state):
        print(f"FROM {self.state} to {state}")
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state

    
    def check_buffer_full(self):
        total_len = sum(len(segment[4:]) for segment in self.buffer)
        # print(total_len)
        return total_len >= self.max_win
    
    def start_timer(self):
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(control.rto, timer_thread, args=(control,))
        self.timer.start()
    
    def stop_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
 
    '''
    Initial Handshake, sent SYN and wait for ACK
    if no ACK for rto amount of time
    resent the SYN

    '''

def send_setup(control):
    if control.start_time is None:
        control.start_time = time.time()
    control.curr_seqno = control.init_seqno
    type_num = Constant.SYN
    type_field = type_num.to_bytes(2,"big")
    seqno_field = control.curr_seqno.to_bytes(2,"big")
    sent_segment = type_field + seqno_field
    control.socket.send(sent_segment)
    control.curr_seqno += 1
    control.transit("SYN_SENT")
    print(f"transit to SYN start time {control.start_time}")



def receive(control):

    while control.is_alive:
        try: 
            print(f"waiting")
            buf, addr = control.socket.recvfrom(2048)        

            type_field = int.from_bytes(buf[:2],byteorder='big')
            seqno_field = int.from_bytes(buf[2:4],byteorder='big')
            #print(f"type {type_field} seqno {seqno_field} state is {control.get_state()}")
            if type_field == Constant.ACK:
                if control.get_state() == "SYN_SENT":
                # transit state
                    control.transit("ESTABLISHED")
                    control.stop_timer()

                    print(f"Transition to - ESTABLISHED")
                # print(f"state in sender is {self.state}")
                # Starting sendng file
                elif control.get_state() == "FIN_WAIT":
                    # transit state
                    print(f"receivedat FINWAIT with {type_field} {seqno_field}")
                    control.transit("CLOSED")
                    control.stop_timer()
                    control.is_alive = False

                elif control.get_state() == "ESTABLISHED":
                    # print(f"recevied ACK # {seqno_field}")
                    for segment in control.buffer:
                        if int.from_bytes(segment[2:4],byteorder='big')+len(segment[4:]) == seqno_field:
                            control.buffer.remove(segment)
                            print(f"ACK for packet {seqno_field} ")


                elif control.get_state() == "CLOSING":
                    if not control.buffer:
                        control.timer.cancel()
                    else:
                        for segment in control.buffer:
                            if int.from_bytes(segment[2:4],byteorder='big')+len(segment[4:]) == seqno_field:
                                control.buffer.remove(segment)
                                print(f"ACK for packet {seqno_field} ")
                                break
                print(f"Buffer length is {len(control.buffer)}")
        except socket.timeout:
            continue
        except ConnectionRefusedError as e:
            print(f"Connection refused error: {e}")
            control.is_alive = False
            break
        except BlockingIOError:
            print(f"Non-blocking socket didn't receive data, retrying...")
            continue
        except KeyboardInterrupt:
            print("Server stopped by user")
            break
        except Exception as e:
            print(f"RECEIVE EXCEPTION as")
            print(e)

def setup_socket(host, my_port,peer_port):
    """Setup a UDP socket for sending messages and receiving replies.
    Args:
        host (str): The hostname or IP address of the receiver.
        port (int): The port number of the receiver.
    Returns:
        socket: The newly created socket.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind(('127.0.0.1', my_port))
        sock.connect((host, peer_port))
    except Exception as e:
        sys.exit(f"Failed to connect to {host}:{peer_port}: {e}")

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
Potential edge case:
before reading, buffer is fine, but after adding it to buffer, it exceeds in size
WHICH SHOULD NOT BE SENT

NEED TO ADD TIMER FOR SEND DATA
'''
def send_data(control,file_name):
    print(f"file_name is {file_name}")
    with open(file_name,"rb") as f:
        while True:
            if not control.check_buffer_full():
                bytes_read = f.read(Constant.MAX_MSS)
                print(f"read segment with byte size {len(bytes_read)}")
                if not bytes_read:
                    control.transit("CLOSING")
                    # file transmitting is done
                    break
                # print(f"READ ABOVE")
                type_num = Constant.DATA
                type_field = type_num.to_bytes(2,"big")
                seqno_field = control.curr_seqno.to_bytes(2,"big")
                segment = type_field+seqno_field+bytes_read
                control.socket.send(segment)
                control.buffer.append(segment)
                control.curr_seqno += len(bytes_read)
                if control.curr_seqno > Constant.MAX_SEQ:
                    control.curr_seqno -= Constant.MAX_SEQ
                # control.start_timer()


                
            pass
    pass

def send_finish(control):
    ''''
    Ensure all buffered data arrived correctly
    '''
    # while True:
    #     try:
    type_num = Constant.FIN
    type_field = type_num.to_bytes(2,"big")
    control.curr_seqno += 1
    seqno_field = control.curr_seqno.to_bytes(2,"big")
    segment = type_field+seqno_field
    print(f"Before Send with segment {segment}")
    control.socket.send(segment)
    control.transit("FIN_WAIT")

        # except socket.timeout:
        #     continue
        # except ConnectionRefusedError as e:
        #     print(f"Connection refused error: {e}")
        #     control.is_alive = False
        #     break
        # except BlockingIOError:
        #     print(f"Non-blocking socket didn't receive data, retrying...")
        #     continue
    
'''

'''
def log_data(control,flag,time,type_segment,seq_no, number_of_bytes):
    log_time = round((time-control.start_time)*1000,2)
    log_string = f"{flag} {time} {type_segment} {seq_no} {number_of_bytes}"
    pass
def timer_thread(control):
    # Loook at different cases. 
    if control.get_state() == "SYN_SENT":
        print("Timeout: Resending SYN")
        send_setup(control)
    elif control.get_state() == "CLOSING":
        print("Timeout: Resending FIN")
        send_finish(control)
    # Restart the timer if the control is still alive and in a state where ACK is expected
    if control.is_alive and control.get_state() in ["SYN_SENT", "CLOSING"]:
        control.start_timer()


if __name__ == "__main__":

    sender_port = parse_port(sys.argv[1])
    receiver_port = parse_port(sys.argv[2])
    txt_file_to_send = sys.argv[3] # name of text file
    max_win = int(sys.argv[4]) #  the maximum window size in bytes for the sender window
    rto = int(sys.argv[5]) # retrainsimission timer in Milliseconds
    flp = sys.argv[6] # forward lost probability
    rlp = sys.argv[7] # reverse loss probability
    sock = setup_socket(Constant.ADDRESS, sender_port,receiver_port)
    # initialise a control block

    control = Control(
        sender_port = sender_port,
        receiver_port= receiver_port,
        socket= sock,
        rto = rto,
        max_win = max_win)
    '''
    Add Threading
    Thread for Receiving
    
    '''
    receiver = threading.Thread(target = receive,args=(control,)) #
    receiver.start()

    # timer = threading.Timer(control.rto, timer_thread, args=(control,))
    # timer.start()

    # # threading.Timer()
    # control.receive()
    print(f"try: control is {control.is_alive}")
    try:
        print(f"in try: control is {control.is_alive}")
        while control.is_alive:
            # print(f"start with state {control.get_state()} cont alive {control.is_alive}")
            if control.timer:
                continue
            if control.get_state() == "CLOSED" or control.get_state() == "SYN_SENT":
                send_setup(control)
                control.start_timer()
            elif control.get_state() == "ESTABLISHED":
                print(f"Now here send file data")
                # Connectoin established, ready to sent file
                send_data(control,txt_file_to_send)
                # control.is_alive = False
            elif control.get_state() == "CLOSING":
                print("SEND CLOSING")
                if not control.buffer:
                    send_finish(control)
                    control.start_timer()
            else:
                print(f"ending at state {control.get_state()} is alive {control.is_alive}")
                control.is_alive = False
                break

    
        print(f"state {control.get_state()}")
    except KeyboardInterrupt:
        print(f"Control Z is PRESSED")
    except Exception as e:
        print(f"Exception is {e}")
    finally:
        if control.timer:
            control.timer.cancel()
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

python3 sender.py 49979 59979 ../sample_txt/random1.txt 1200 3000 0.1 0.05

USE WIRESHARK TO TEST
'''