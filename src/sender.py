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
        self.rto = rto/1000
        self.is_alive = is_alive
        # self.socket.settimeout(self.rto/1000)
        self.all_state = ["CLOSED","SYN_SENT","ESTABLISHED","CLOSING","FIN_WAIT"]
        self.state = "CLOSED"
        self.curr_seqno = 0 # track the ACK that is supposed to be received from the receiver
        self.max_win = max_win
        self.init_seqno = utils.gen_random()
        # self.init_seqno = 2 ** 16-5 # purely testing
        self.buffer = []
        self.timer = None
        self.start_time = None

        self.dup_count = 0
        # Log data
        self.data_sent = 0
        self.data_ack = 0
        self.segment_sent = 0
        self.retransmit_segment = 0
        self.dup_ack_received = 0
        self.data_segment_dropped = 0
        self.ack_segment_dropped = 0

    def get_state(self):
        return self.state
        
    def transit(self,state):
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state

    
    def check_buffer_full(self):
        total_len = sum(len(segment[4:]) for segment in self.buffer)
        return total_len >= self.max_win
    
    def start_timer(self):
        #print(f"START TIMER")
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(self.rto, timer_thread, args=(self,flp,))
        self.timer.start()
    
    def stop_timer(self):
        #print(f"STOP TIMER")
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
    
    def update_seqno(self,data = None,data_length = None):
        if data:
            self.curr_seqno += len(data)
        else:
            if data_length:
                self.curr_seqno += data_length
            else:
                self.curr_seqno += 1
        if self.curr_seqno >= Constant.MAX_SEQ:
            self.curr_seqno -= Constant.MAX_SEQ
        #print(f"Update Seqno to {self.curr_seqno}")
    
    def get_send_seqno(self,data):
        total_length = 0
        for segment in self.buffer[1:]:
            total_length += len(segment[4:])
        return_length = self.curr_seqno + total_length
        while return_length >= Constant.MAX_SEQ:
            return_length -= Constant.MAX_SEQ
        return return_length

def receive(
        control,rlp):

    while control.is_alive:
        try: 
            #print(f"waiting")
            buf, addr = control.socket.recvfrom(2048)        

            type_field = int.from_bytes(buf[:2],byteorder='big')
            seqno_field = int.from_bytes(buf[2:4],byteorder='big')

            if random.random() < rlp:
                log_data(control,
                    flag = "drp",
                    time = time.time(),
                    type_segment=type_field,
                    seq_no=seqno_field,
                    number_of_bytes=len(buf)-4)
                if control.get_state() in ["ESTABLISHED","CLOSING"]:
                    control.ack_segment_dropped += 1
                continue

            log_data(control,
                flag = "rcv",
                time = time.time(),
                type_segment=type_field,
                seq_no=seqno_field,
                number_of_bytes=len(buf)-4)
            
            if type_field == Constant.ACK:
                if control.get_state() == "SYN_SENT":
                # transit state
                    control.transit("ESTABLISHED")
                    control.stop_timer()
                    assert seqno_field == control.curr_seqno

                # Starting sendng file
                elif control.get_state() == "FIN_WAIT":
                    # transit state
                    print(f"receivedat FINWAIT with {type_field} {seqno_field}")
                    control.transit("CLOSED")
                    control.stop_timer()
                    control.is_alive = False

                elif control.get_state() == "ESTABLISHED":
                    top_segment = control.buffer[0]
                    print(f"recevied ACK # {seqno_field} curr_seqno {control.curr_seqno}")
                    if seqno_field == control.curr_seqno:
                        # match the first one
                        control.stop_timer()
                        if len(control.buffer) > 1:
                            control.update_seqno(data = control.buffer[1][4:])
                            control.start_timer()

                        control.data_ack += len(top_segment[4:])
                        control.buffer.remove(top_segment)
                        print(f"REMOVING")
                    elif seqno_field > control.curr_seqno:
                        # Cumulative ACK
                        # for segment in control.buffer:
                        #     control.stop_timer()
                        #     control.buffer.remove(segment)
                        #     if 
                        #     control.start_timer()
                        control.stop_timer()
                        total_data_len = 0
                        removable = []
                        for idx,segment in enumerate(control.buffer):
                            curr_segment_seqno = int.from_bytes(segment[2:4],byteorder="big")
                            curr_segment_length = len(segment[4:])
                            removable.append(segment)
                            if idx > 0:
                                total_data_len += curr_segment_length
                            if curr_segment_seqno + curr_segment_length == seqno_field:
                                control.data_ack += (curr_segment_length+ len(control.buffer[0][4:]))
                                break
                        
                        for segment in removable:
                            control.buffer.remove(segment)
                        control.update_seqno(data_length = total_data_len)

                        if control.buffer:
                            control.update_seqno(data = control.buffer[0][4:])
                            control.start_timer()
                        

                        pass

                        

                    else:
                        # duplicate ACK
                        control.dup_ack_received += 1

                elif control.get_state() == "CLOSING":
                    print(f"RECEIVED IN CLOSING")

                    print(f"recevied ACK # {seqno_field} curr_seqno {control.curr_seqno} length {len(control.buffer)}")
                    if control.buffer:
                        
                        top_segment = control.buffer[0]
                        if seqno_field == control.curr_seqno:
                            control.stop_timer()
                            if len(control.buffer) > 1:
                                control.start_timer()
                                control.update_seqno(data = control.buffer[1][4:])
                            print(f"before remove buffer size {len(control.buffer)}")
                            control.buffer.remove(top_segment)
                            print(f"before after buffer size {len(control.buffer)}")
                            control.data_ack += len(top_segment[4:])
                            # if control.buffer:
                            #     #print(f"start the timer here with buffer {control.buffer}")
                            #     control.start_timer()
                            #     control.update_seqno(data = control.buffer[0][:4])
        except socket.timeout:
            continue
        except ConnectionRefusedError as e:
            print(f"Connection refused error: {e}")
            print(f"Control state {control.get_state()}")
            control.is_alive = False
            break
        except BlockingIOError:
            # print(f"Non-blocking socket didn't receive data, retrying...")
            continue
        except KeyboardInterrupt:
            print("Server stopped by user")
            break
        except Exception as e:
            print(f"RECEIVE EXCEPTION as")
            print(e)

def setup_socket(
        host, my_port,peer_port):
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

def parse_port(
        port_str, min_port=49152, max_port=65535):
    try:
        port = int(port_str)
    except ValueError:
        sys.exit(f"Invalid port argument, must be numerical: {port_str}")
    
    if not (min_port <= port <= max_port):
        sys.exit(f"Invalid port argument, must be between {min_port} and {max_port}: {port}")
                 
    return port


'''
Initial Handshake, sent SYN and wait for ACK
if no ACK for rto amount of time
resent the SYN

'''

def send_setup(
        control,flp):

    control.curr_seqno = control.init_seqno
    type_num = Constant.SYN
    type_field = type_num.to_bytes(2,"big")
    seqno_field = control.curr_seqno.to_bytes(2,"big")
    sent_segment = type_field + seqno_field
    if random.random() < flp:
        print(f"setup DROPPED")
        log_data(control,
            flag = "drp",
            time = time.time(),
            type_segment=type_num,
            seq_no=control.curr_seqno,
            number_of_bytes=0)
    else:
        control.socket.send(sent_segment)
        log_data(control,
            flag = "snd",
            time = time.time(),
            type_segment=type_num,
            seq_no=control.curr_seqno,
            number_of_bytes=0)
    if control.start_time is None:
        control.start_time = time.time()

    control.update_seqno()
    control.transit("SYN_SENT")
    # print(f"transit to SYN start time {control.start_time}")


'''
Potential edge case:
before reading, buffer is fine, but after adding it to buffer, it exceeds in size
WHICH SHOULD NOT BE SENT

NEED TO ADD TIMER FOR SEND DATA

First in the buffer,
- Update Curr sequence, the ACK received later be used to match this, indicting in order recevied
Not in the buffer,
-  Put it in the buffer, do not update curtr seqeucen just yet, wait till it becomes first in the packet.
'''
def send_data(
        control,file_name,flp):
    #print(f"file_name is {file_name}")
    with open(file_name,"rb") as f:
        while True:
            if not control.check_buffer_full():
                #print(f"buffer length { sum(len(segment[4:]) for segment in control.buffer)} max_win {control.max_win}")
                bytes_read = f.read(Constant.MAX_MSS)
                #print(f"read segment with byte size {len(bytes_read)}")
                if not bytes_read:
                    control.transit("CLOSING")
                    print(f"transmitting done")
                    # file transmitting is done
                    break
                # print(f"READ ABOVE")
                type_num = Constant.DATA
                type_field = type_num.to_bytes(2,"big")
                print(f"sending with {control.curr_seqno} with len {len(bytes_read)}")
                send_seqno = control.get_send_seqno(bytes_read)
                seqno_field = send_seqno.to_bytes(2,"big")
                segment = type_field+seqno_field+bytes_read
                                # control.curr_seqno += len(bytes_read)
                # if control.curr_seqno >= Constant.MAX_SEQ:
                #     control.curr_seqno -= Constant.MAX_SEQ
                if random.random() < flp:
                    print(f"Data seqno {control.curr_seqno} DROPPED")
                    log_data(control,
                        flag = "drp",
                        time = time.time(),
                        type_segment=type_num,
                        seq_no=control.curr_seqno,
                        number_of_bytes=len(bytes_read))
                    control.data_segment_dropped += 1
                else:

                    log_data(control,
                        flag = "snd",
                        time = time.time(),
                        type_segment=type_num,
                        seq_no=control.curr_seqno,
                        number_of_bytes=len(bytes_read))


                    control.socket.send(segment)
                control.segment_sent += 1
                control.data_sent += len(bytes_read)
                if not control.buffer:
                    control.start_timer()
                    #print(f"Update_seqno")
                    control.update_seqno(bytes_read)
                '''
                Distinction required, on whether segment is first in buffer
                or others in buffer
                '''
                control.buffer.append(segment)
                # control.start_timer()



                
            pass
    pass

def send_finish(
        control,flp):
    ''''
    Ensure all buffered data arrived correctly
    '''
    # while True:
    #     try:
    type_num = Constant.FIN
    type_field = type_num.to_bytes(2,"big")
    # control.curr_seqno += 1
    seqno_field = control.curr_seqno.to_bytes(2,"big")
    segment = type_field+seqno_field
    if random.random() < flp:
        print(f"FINISH DROPPED")
        log_data(control,
                flag = "drp",
                time = time.time(),
                type_segment=type_num,
                seq_no=control.curr_seqno,
                number_of_bytes=0)
    else:
        control.socket.send(segment)
        print(f"FIN SENDED")
        log_data(control,
                flag = "snd",
                time = time.time(),
                type_segment=type_num,
                seq_no=control.curr_seqno,
                number_of_bytes=0)
    control.transit("FIN_WAIT")

    
'''

'''
def log_data(
        control, flag, time, type_segment, seq_no, number_of_bytes):
    file_name = Constant.SENDER_LOG_TEXT
    if not control.start_time:
        log_time = 0
    else:
        log_time = round((time - control.start_time) * 1000, 2)
    segment_name = Constant.SEQNO_REVERSE_MAP[type_segment]
    log_string = f"{flag} {log_time} {segment_name} {seq_no} {number_of_bytes}\n"

    with open(file_name, "a") as log_file:
        log_file.write(log_string)

def timer_thread(
        control,flp):
    # Loook at different cases. 
    if control.get_state() == "SYN_SENT":
        # print("Timeout: Resending SYN")
        control.stop_timer()
        # send_setup(control,flp)
    elif  control.get_state() == "FIN_WAIT":
        # print("Timeout: Resending FIN")
        control.stop_timer()
        # send_finish(control,flp)
    elif control.get_state() == "CLOSING" or control.get_state() == "ESTABLISHED":
        #print(f"Resending segment buf size {len(control.buffer)} timer is {control.timer}")
        control.stop_timer()
        poped_segment = control.buffer[0]
        control.retransmit_segment += 1
        if random.random() < flp:
            # still need to be dropped
            log_data(control,
                flag = "drp",
                time = time.time(),
                type_segment=int.from_bytes(poped_segment[:2],byteorder='big'),
                seq_no=int.from_bytes(poped_segment[2:4],byteorder='big'),
                number_of_bytes=len(poped_segment[4:]))
            control.data_segment_dropped += 1
            
            pass
        else:
            log_data(control,
                flag = "snd",
                time = time.time(),
                type_segment=int.from_bytes(poped_segment[:2],byteorder='big'),
                seq_no=int.from_bytes(poped_segment[2:4],byteorder='big'),
                number_of_bytes=len(poped_segment[4:]))

            print(f"Retransmit for seq {int.from_bytes(poped_segment[2:4],byteorder='big')}")
            control.socket.send(poped_segment)
        # control.buffer.append(poped_segment)
    # Restart the timer if the control is still alive and in a state where ACK is expected
    if control.is_alive and control.get_state() in ["CLOSING","ESTABLISHED"]:
        control.start_timer()
'''
self.data_sent = 0
self.data_ack = 0
self.segment_sent = 0
self.retransmit_segment = 0
self.dup_ack_received = 0
self.data_segment_dropped = 0
self.ack_segment_dropped = 0
'''
def log_summary(control):
    dest_path = Constant.SENDER_LOG_TEXT
    with open(dest_path,"a") as file:
        file.write("\n")
        file.write(f"Original data sent:        {control.data_sent}\n")
        file.write(f"Original data acked:       {control.data_ack}\n")
        file.write(f"Original segments sent:    {control.segment_sent}\n")
        file.write(f"Retransmitted segments:    {control.retransmit_segment}\n")
        file.write(f"Dup acks received:         {control.dup_ack_received}\n")
        file.write(f"Data segments dropped:     {control.data_segment_dropped}\n")
        file.write(f"Ack segments dropped:      {str(control.ack_segment_dropped)}\n")
        

if __name__ == "__main__":

    sender_port = parse_port(sys.argv[1])
    receiver_port = parse_port(sys.argv[2])
    txt_file_to_send = sys.argv[3] # name of text file
    max_win = int(sys.argv[4]) #  the maximum window size in bytes for the sender window
    rto = int(sys.argv[5]) # retrainsimission timer in Milliseconds
    flp = float(sys.argv[6]) # forward lost probability
    rlp = float(sys.argv[7]) # reverse loss probability
    sock = setup_socket(Constant.ADDRESS, sender_port,receiver_port)
    # initialise a control block

    with open(Constant.SENDER_LOG_TEXT, "w") as file:
        file.write("")
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
    receiver = threading.Thread(target = receive,args=(control,rlp,)) #
    receiver.start()

    try:
        while control.is_alive:
            # print(f"start with state {control.get_state()} cont alive {control.is_alive}")
            if control.timer:
                continue
            if control.get_state() == "CLOSED" or control.get_state() == "SYN_SENT":
                #send_setup(control,0.3) # use to test drop ACK in SYN
                send_setup(control,flp)
                control.start_timer()
            elif control.get_state() == "ESTABLISHED":
                # Connectoin established, ready to sent file
                send_data(control,txt_file_to_send,flp)
                #print(f"Finish Sending DATA at state {control.get_state()}")
                # control.is_alive = False  
            elif control.get_state() == "CLOSING" or control.get_state() == "FIN_WAIT":
                #print(f"control buffer length {control.buffer} and time {control.timer} state is {control.get_state()}")
                if not control.buffer:

                    #send_finish(control,0.6)# For testing purporses
                    send_finish(control,flp) 
                    control.start_timer()
            else:
                print(f"ending at state {control.get_state()} is alive {control.is_alive}")
                control.is_alive = False
                break


    except KeyboardInterrupt:
        print(f"Control Z is PRESSED")
    except Exception as e:
        print(f"Exception is {e}")
    finally:
        log_summary(control)
        if control.timer:
            control.timer.cancel()
        receiver.join()

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

python3 sender.py 49974 59974 ../sample_txt/random1.txt 1000 1000 0 0

USE WIRESHARK TO TEST
'''

'''
In slidding window, sender and receiver thread sometimes work a bit arbitrarily,
packet removes, MAKE IT TRANSFER THE NEXT PACKET

'''