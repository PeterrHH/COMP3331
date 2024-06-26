import sys
import random
import socket
import time
import threading
from dataclasses import dataclass
import utils.Constant as Constant

class Control:
    def __init__(self,
                 receiver_port:int,
                 sender_port:int,
                 socket:socket.socket,
                 max_win: int) -> None:
        self.receiver_port = receiver_port
        self.sender_port =sender_port
        self.socket = socket
        self.max_win = max_win
        self.all_state = ["CLOSED","LISTEN","ESTABLISHED","TIME_WAIT"]
        self.state = "CLOSED"
        self.is_alive = True
        self.start_time = None
        self.buffer = []
        self.received_data = ""
        self.in_order_seqno = None
        self.timer = None
        self.prev_segment = []
        self.prev_segment_max = self.max_win / 1000
        self.first_data = False

        # Log data
        self.segment_received = 0
        self.duplicate_received = 0
        self.duplicate_ack = 0
    
    def seqno_match(self,seqno):
        return self.in_order_seqno == seqno
    
    def start_timer(self):
        if self.timer is not None:
            self.timer.cancel()
        self.timer = threading.Timer(Constant.MSL*2,timer_thread,args=(self,))
        self.timer.start()
    
    def stop_timer(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def update_seq_num(self,seq_num,data = None):
        if data:
            update_num = seq_num + len(data)
        else:
            update_num = seq_num + 1
        if update_num >= Constant.MAX_SEQ:
            update_num -= Constant.MAX_SEQ
        return update_num
    def transit(self,state):
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state


def receive(control):
    control.transit("LISTEN")
    while control.is_alive:

        try:

            buf,addr = control.socket.recvfrom(2048)
            if control.timer:
                control.stop_timer()
            type_field = int.from_bytes(buf[:2],byteorder='big')
            seqno_num = int.from_bytes(buf[2:4],byteorder='big')
            ack_type_num = Constant.ACK
            log_data(
                control,
                flag = "rcv",
                time= time.time(),
                type_segment=type_field,
                seq_no= seqno_num,
                number_of_bytes=len(buf[4:])
            )


            if type_field == Constant.SYN:

                if control.state == "LISTEN":
                    control.start_time = time.time()
                    control.in_order_seqno = control.update_seq_num(seqno_num)
                ack_seqno_num = control.in_order_seqno
                ack_type_field = ack_type_num.to_bytes(2,"big")
                ack_seqno_field =  ack_seqno_num.to_bytes(2,"big")
                ack_segment = ack_type_field + ack_seqno_field
                control.socket.send(ack_segment)

                log_data(control,
                    flag = "snd",
                    time = time.time(),
                    type_segment=ack_type_num,
                    seq_no=ack_seqno_num,
                    number_of_bytes=0)


                control.transit("ESTABLISHED")

            elif type_field == Constant.DATA:

                data_received = buf[4:].decode('utf-8') 
                if seqno_num in control.prev_segment:
                    control.duplicate_received += 1
                else:
                    if len(control.prev_segment) == control.prev_segment_max:
                        control.prev_segment.pop(0)
                    control.prev_segment.append(seqno_num)
                # if in order directly add to data read
                if seqno_num == control.in_order_seqno:

                    control.received_data += data_received
                    control.segment_received += 1
                    control.in_order_seqno = control.update_seq_num(control.in_order_seqno,data_received)
                    # check that with this data being read, if any previous gotten data
                    # can be put into the read file
                    removable = []
                    for segment in control.buffer:
                        if int.from_bytes(segment[2:4],byteorder='big') == control.in_order_seqno:
                            control.received_data += segment[4:].decode('utf-8') 
                            control.in_order_seqno = control.update_seq_num(control.in_order_seqno,segment[4:]) # !!!!
                            # Check for Duplicates
                            control.segment_received += 1
                            removable.append(segment)
                    
                    for segment in removable:
                        control.buffer.remove(segment)

             

                else:
                    # No inorder, previous packets are lost
                    # the ACK NUMBER SHOULD BE FOR PREVIOUS 
                    control.buffer.append(buf)
                    control.buffer.sort(key=lambda x: int.from_bytes(x[2:4], byteorder='big'))
                    if control.first_data:
                        control.duplicate_ack += 1

                length_data = len(data_received)
                ack_seqno_num= control.in_order_seqno
                ack_type_field = ack_type_num.to_bytes(2,"big")
                ack_seqno_field = ack_seqno_num.to_bytes(2,"big")
                ack_segment = ack_type_field + ack_seqno_field
                control.socket.send(ack_segment)
                log_data(control,
                    flag = "snd",
                    time = time.time(),
                    type_segment=ack_type_num,
                    seq_no=ack_seqno_num,
                    number_of_bytes=0)
                if not control.first_data:
                    control.first_data = True
            elif type_field == Constant.FIN:
                # When receiving FIN, move to TIME_WAIT state
                # wait for two maximum segment lifetime (MSLs). One MSL is 1s.
                # Then reentering CLOSED state.
                control.transit("TIME_WAIT")
                ack_seqno_num = control.update_seq_num(seqno_num)
                ack_type_field = ack_type_num.to_bytes(2,"big")
                ack_seqno_field = ack_seqno_num.to_bytes(2,"big")
                ack_segment = ack_type_field + ack_seqno_field
                control.socket.send(ack_segment)
                log_data(control,
                    flag = "snd",
                    time = time.time(),
                    type_segment=ack_type_num,
                    seq_no=ack_seqno_num,
                    number_of_bytes=0)
                control.start_timer()
                '''
                Should wait two seconds, set is_alive to False and close but it does not
                '''

            else:
                pass
        except socket.timeout:
            print(f"socket timeout")
            continue
        except ConnectionRefusedError as e:
            print(f"Connection refused error: {e}")
            control.is_alive = False
            break
        except BlockingIOError:
            if not control.is_alive:
                break
            continue
        except KeyboardInterrupt:
            print("Server stopped by user")
            break
        except Exception as e:
            print(f"RECEIVE EXCEPTION")
            print(e)



def parse_port(
        port_str, min_port=49152, max_port=65535):
    try:
        port = int(port_str)
    except ValueError:
        sys.exit(f"Invalid port argument, must be numerical: {port_str}")
    
    if not (min_port <= port <= max_port):
        sys.exit(f"Invalid port argument, must be between {min_port} and {max_port}: {port}")
                 
    return port

def log_data(
        control,flag,time,type_segment,seq_no,number_of_bytes):
    file_name = Constant.RECEIVER_LOG_TEXT
    if not control.start_time:
        log_time = 0
    else:
        log_time = round((time-control.start_time)*1000,2)
    segment_name = Constant.SEQNO_REVERSE_MAP[type_segment]
    log_string = f"{flag} {log_time} {segment_name} {seq_no} {number_of_bytes}\n"
    with open(file_name,"a") as log_file:
        log_file.write(log_string)

def write_text_to_file(
        control,dest_path):
    with open(dest_path,"w") as file:
        file.write(control.received_data)

def timer_thread(control):
    control.transit("CLOSED")
    control.is_alive = False # Clear the event to signal the main thread to stop

def log_summary(control):
    dest_path = Constant.RECEIVER_LOG_TEXT
    with open(dest_path,"a") as file:
        file.write("\n")
        file.write(f"Original data received:        {len(control.received_data)}\n")
        file.write(f"Original segments received:    {str(control.segment_received)}\n")
        file.write(f"Dup data segments received:    {str(control.duplicate_received)}\n")
        file.write(f"Dup ack segments sent:         {str(control.duplicate_ack)}\n")



if __name__ == "__main__":
    receiver_port = parse_port(sys.argv[1])
    sender_port = parse_port(sys.argv[2])
    txt_file_received = sys.argv[3]
    max_win = int(sys.argv[4])

    with open(Constant.RECEIVER_LOG_TEXT, "w") as file:
        file.write("")
    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((Constant.ADDRESS,receiver_port))
    sock.connect((Constant.ADDRESS,sender_port))
    sock.settimeout(0)  # Set socket to non-blocking mode
    control = Control(
        receiver_port= receiver_port,
        sender_port=sender_port,
        socket=sock,
        max_win = max_win,
    )

    try:
        receive(control)

    except KeyboardInterrupt:
        print("Shutting down receiver.")
        control.is_alive = False
    finally:
        write_text_to_file(control,txt_file_received)
        log_summary(control,)
        control.socket.close()
        print("Receiver shut down complete.")
        sys.exit(0)

  