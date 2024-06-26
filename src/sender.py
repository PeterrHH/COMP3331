import sys
import random
import socket
import time
import threading
import random
from dataclasses import dataclass
import utils.Constant as Constant
import utils

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
        self.buffer = []
 
        self.past_ack = []
        self.timer = None
        self.start_time = None

        self.finish_sent = False
        # self.finish_receive = False

        self.first_receive = False

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
        total_len = sum(len(segment[0][4:]) for segment in self.buffer)
        return total_len >= self.max_win
    
    def start_timer(self):

        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(self.rto, timer_thread, args=(self,flp,))
        self.timer.start()
    
    def stop_timer(self):

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

    def add_ack_buffer(self,ack_number):
        if len(self.past_ack) == 3:
            self.past_ack.pop(0)

        self.past_ack.append(ack_number)
        

    
    def get_send_seqno(self,data):
        total_length = 0
        if self.buffer:
            seq_no_prev = int.from_bytes(self.buffer[-1][0][2:4],byteorder="big")
            return_length = seq_no_prev + len(self.buffer[-1][0][4:])
        else:
            return_length = self.curr_seqno
        # for segment in self.buffer[1:]:
        #     total_length += len(segment[4:])
        # return_length = self.curr_seqno + total_length
        while return_length >= Constant.MAX_SEQ:
            return_length -= Constant.MAX_SEQ
        return return_length

    # def check_ack_seqno(receive_seqno):
    #     if receive_seqno = self.curr_seqno:
    #         return Constant.MATCH
        
        


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

                # Starting sendng file
                elif control.get_state() == "FIN_WAIT":
                    # transit state
                    control.transit("CLOSED")
                    control.stop_timer()
                    control.is_alive = False

                elif control.get_state() == "ESTABLISHED":
                    control.add_ack_buffer(seqno_field)

                    acked_segment_count = 0
                    acked_data_size = 0
                    first = True

                    found = any(seqno_field == element[1] for element in control.buffer)
                    #print(f"---------NOT FOUND {[element[1] for element in control.buffer]} with seqno_field {seqno_field}---------")
                    removable = []
                    if not found:
                        # Duplicate
                        if control.first_receive:
                            control.dup_ack_received += 1
                    else:
                        # Remove all segments from the buffer that are acknowledged by the received ACK
                        while control.buffer:
                            top_segment = control.buffer[0][0]
                            top_segment_seqno = int.from_bytes(top_segment[2:4], byteorder="big")
                            top_segment_end_seqno = (top_segment_seqno + len(top_segment[4:])) % Constant.MAX_SEQ
                            #print(f"---top seg end seqno {top_segment_end_seqno} receive seqno {seqno_field}---")
                            removable.append(top_segment)
                            
                            if first:
                                control.stop_timer()
                                first = False
                            control.update_seqno(data = top_segment[4:]) 
                            acked_segment_count += 1
                            control.buffer.pop(0)
                            control.data_ack += len(top_segment[4:])
                            if top_segment_end_seqno == seqno_field:
                                break
                
                    # Restart the timer if there are still segments in the buffer
                    if control.buffer:
                        control.start_timer()
                    
                    control.first_receive = True
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
            print(f"!!!!!!! RECEIVE EXCEPTION as !!!!!!!!!!!")
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
    with open(file_name,"rb") as f:
        while True:
            # if 3 past_ack and all receive, Retransmit
            if len(control.past_ack) == 3:
                if control.past_ack[0] == control.past_ack[1] == control.past_ack[2]:
                    data_retransmit(control,flp)
                    control.start_timer()
                    control.past_ack = []

                    
            if not control.check_buffer_full():
                bytes_read = f.read(Constant.MAX_MSS)
                # finish reading
                if not bytes_read:
                    # finish reading and receive all ACK for data
                    if control.finish_sent and control.data_sent == control.data_ack:
                        control.transit("CLOSING")
                    # file transmitting is done
                        break
                    else:
                        control.finish_sent = True
                        continue

                type_num = Constant.DATA
                type_field = type_num.to_bytes(2,"big")
                send_seqno = control.get_send_seqno(bytes_read)
            
            
                seqno_field = send_seqno.to_bytes(2,"big")
                segment = type_field+seqno_field+bytes_read

                if random.random() < flp:
                    log_data(control,
                        flag = "drp",
                        time = time.time(),
                        type_segment=type_num,
                        seq_no=send_seqno,
                        number_of_bytes=len(bytes_read))
                    control.data_segment_dropped += 1
                else:

                    log_data(control,
                        flag = "snd",
                        time = time.time(),
                        type_segment=type_num,
                        seq_no=send_seqno,
                        number_of_bytes=len(bytes_read))


                    control.socket.send(segment)
                control.segment_sent += 1
                control.data_sent += len(bytes_read)
                if not control.buffer:
                    control.start_timer()

                required_ack = utils.get_segment_ack_num(segment)

                control.buffer.append((segment,required_ack))


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
        log_data(control,
                flag = "drp",
                time = time.time(),
                type_segment=type_num,
                seq_no=control.curr_seqno,
                number_of_bytes=0)
    else:
        control.socket.send(segment)
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

def data_retransmit(control,flp):
    control.stop_timer()
    poped_segment = control.buffer[0][0]
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

        control.socket.send(poped_segment)
        
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
    elif control.get_state() == "ESTABLISHED":
        #print(f"Resending segment buf size {len(control.buffer)} timer is {control.timer}")
        data_retransmit(control,flp)
    # Restart the timer if the control is still alive and in a state where ACK is expected
    if control.is_alive and control.get_state() in ["ESTABLISHED"]:
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

    receiver = threading.Thread(target = receive,args=(control,rlp,)) #
    receiver.start()

    try:
        while control.is_alive:
            # print(f"start with state {control.get_state()} cont alive {control.is_alive}")
            if control.timer:
                continue
            if control.get_state() == "CLOSED" or control.get_state() == "SYN_SENT":
                send_setup(control,flp)
                control.start_timer()
            elif control.get_state() == "ESTABLISHED":
                # Connectoin established, ready to sent file
                send_data(control,txt_file_to_send,flp)
            elif control.get_state() == "CLOSING" or control.get_state() == "FIN_WAIT":
                #print(f"control buffer length {control.buffer} and time {control.timer} state is {control.get_state()}")
                if not control.buffer:
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
python3 sender.py 49974 59974 ../sample_txt/random1.txt 1000 1000 0 0
'''