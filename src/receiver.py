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
                 socket:socket.socket) -> None:
        self.receiver_port = receiver_port
        self.sender_port =sender_port
        self.socket = socket
        self.all_state = ["CLOSED","LISTEN","ESTABLISHED","TIME_WAIT"]
        self.state = "CLOSED"
        self.is_alive = True
        self.start_time = None


    def transit(self,state):
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state

    def receive(self):
        # if self.state != "CLOSED":
        #     sys.exit(f"Receiver Handshaking when not CLOSED state is {self.state}")
        self.transit("LISTEN")
        while self.is_alive:
            try:
                buf,addr = self.socket.recvfrom(2048)
                # print(buf)
                # print("---------------")
                type_field = int.from_bytes(buf[:2],byteorder='big')
                seqno_num = int.from_bytes(buf[2:4],byteorder='big')
                ack_type_num = Constant.ACK
                log_data(
                    self,
                    flag = "rcv",
                    time= time.time(),
                    type_segment=type_field,
                    seq_no= seqno_num,
                    number_of_bytes=len(buf)-4
                )
                self.start_time = time.time()
                if type_field == Constant.SYN:
                    # resent ACK
 
                    ack_seqno_num = seqno_num + 1
                    ack_type_field = ack_type_num.to_bytes(2,"big")
                    ack_seqno_field =  ack_seqno_num.to_bytes(2,"big")
                    ack_segment = ack_type_field + ack_seqno_field
                    self.socket.send(ack_segment)
                    log_data(control,
                        flag = "snd",
                        time = time.time(),
                        type_segment=ack_type_num,
                        seq_no=ack_seqno_num,
                        number_of_bytes=0)
    

                    self.transit("ESTABLISHED")
                    # print(f"state in receiver is {self.state}")
                elif type_field == Constant.DATA:
                    data_received = buf[4:]
    
                    # print(data_received)
                    #print(f"Receive DATA {len(data_received)}")
                    length_data = len(data_received)
                    ack_seqno_num= seqno_num+length_data
                    ack_type_field = ack_type_num.to_bytes(2,"big")
                    ack_seqno_field = ack_seqno_num.to_bytes(2,"big")
                    ack_segment = ack_type_field + ack_seqno_field
                    #print(f"received {type_field} sent ack_segment ack_segment {int.from_bytes(ack_seqno_field,byteorder='big')}")
                    self.socket.send(ack_segment)
                    log_data(control,
                        flag = "snd",
                        time = time.time(),
                        type_segment=ack_type_num,
                        seq_no=ack_seqno_num,
                        number_of_bytes=0)
                elif type_field == Constant.FIN:
                    # When receiving FIN, move to TIME_WAIT state
                    # wait for two maximum segment lifetime (MSLs). One MSL is 1s.
                    # Then reentering CLOSED state.
                    self.transit("TIME_WAIT")
                    # print(f"received {type_field}  sent ack_segment ack_segment {int.from_bytes(ack_seqno_field,byteorder='big')}")
                    ack_seqno_num = seqno_num+1
                    ack_type_field = ack_type_num.to_bytes(2,"big")
                    ack_seqno_field = ack_seqno_num.to_bytes(2,"big")
                    self.socket.send(ack_segment)
                    log_data(control,
                        flag = "snd",
                        time = time.time(),
                        type_segment=ack_type_num,
                        seq_no=ack_seqno_num,
                        number_of_bytes=0)

                    time.sleep(2*Constant.MSL)
                    self.transit("CLOSED")
                    self.is_alive = False
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
                print(f"RECEIVE EXCEPTION")
                print(e)



def parse_port(port_str, min_port=49152, max_port=65535):
    try:
        port = int(port_str)
    except ValueError:
        sys.exit(f"Invalid port argument, must be numerical: {port_str}")
    
    if not (min_port <= port <= max_port):
        sys.exit(f"Invalid port argument, must be between {min_port} and {max_port}: {port}")
                 
    return port

def log_data(control,flag,time,type_segment,seq_no,number_of_bytes):
    if not control.start_time:
        log_time = 0
    else:
        log_time = round((time-control.start_time)*1000,2)
    segment_name = Constant.SEQNO_REVERSE_MAP[type_segment]
    log_string = f"{flag} {log_time} {segment_name} {seq_no} {number_of_bytes}"
    print(log_string)

if __name__ == "__main__":
    receiver_port = parse_port(sys.argv[1])
    sender_port = parse_port(sys.argv[2])
    txt_file_received = sys.argv[3]
    max_win = sys.argv[4]

    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((Constant.ADDRESS,receiver_port))
    sock.connect((Constant.ADDRESS,sender_port))
    control = Control(
        receiver_port= receiver_port,
        sender_port=sender_port,
        socket=sock
    )

    try:

        control.receive()
        # while True:
            
        #     buf,addr = control.socket.recvfrom(2048)
        #     if int.from_bytes(buf[:2],byteorder='big') == Constant.SYN and control.state == "ESTABLISHED":
        #         continue
    except KeyboardInterrupt:
        print("Shutting down receiver.")
        control.is_alive = False
    finally:
        # control.stop()
        control.socket.close()
        print("Receiver shut down complete.")
        sys.exit(0)

    '''
    At thsi stage, established connection. If received any more, and in eestalished state
    we ignore it 

    python3 receiver.py 59979 49979 ../sample_txt/random1.txt 1200
    '''

    # control.socket.close()  # Close the socket

    # print("Shut down complete.")

    # sys.exit(0)