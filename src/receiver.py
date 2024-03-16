import sys
import random
import socket
import time
import threading
from dataclasses import dataclass
import Constant

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

        self.handshake()
    def transit(self,state):
        if state not in self.all_state:
            print(f"State {state} does not exists in Sender")
        else:
            self.state =  state

    def handshake(self):
        if self.state != "CLOSED":
            sys.exit(f"Receiver Handshaking when not CLOSED state is {self.state}")
        self.transit("LISTEN")
        while True:
            buf,addr = self.socket.recvfrom(2048)
            print(buf)
            type_field = int.from_bytes(buf[:2],byteorder='big')
            seqno_field = int.from_bytes(buf[2:4],byteorder='big')
            if type_field == Constant.SYN:
                # resent ACK
                type_num = Constant.ACK
                ack_seqno_field = seqno_field + 1
                ack_type_field = type_num.to_bytes(2,"big")
                ack_seqno_field =  ack_seqno_field.to_bytes(2,"big")
                ack_segment = ack_type_field + ack_seqno_field
                print(f"sent ack_segment {ack_segment}")
                self.socket.sendto(ack_segment,addr)
                #self.socket.send(ack_segment)
                self.transit("ESTABLISHED")
                print(f"state in receiver is {self.state}")
                break


def parse_port(port_str, min_port=49152, max_port=65535):
    try:
        port = int(port_str)
    except ValueError:
        sys.exit(f"Invalid port argument, must be numerical: {port_str}")
    
    if not (min_port <= port <= max_port):
        sys.exit(f"Invalid port argument, must be between {min_port} and {max_port}: {port}")
                 
    return port

if __name__ == "__main__":
    receiver_port = parse_port(sys.argv[1])
    sender_port = parse_port(sys.argv[2])
    txt_file_received = sys.argv[3]
    max_win = sys.argv[4]

    sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((Constant.ADDRESS,receiver_port))
    try:
        control = Control(
            receiver_port= receiver_port,
            sender_port=sender_port,
            socket=sock
        )
        while True:

            buf,addr = control.socket.recvfrom(2048)
            if int.from_bytes(buf[:2],byteorder='big') == Constant.SYN and control.state == "ESTABLISHED":
                continue
    except KeyboardInterrupt:
        print("Shutting down receiver.")
    finally:
        # control.stop()
        control.socket.close()
        print("Receiver shut down complete.")

    '''
    At thsi stage, established connection. If received any more, and in eestalished state
    we ignore it 
    '''

    # control.socket.close()  # Close the socket

    # print("Shut down complete.")

    # sys.exit(0)