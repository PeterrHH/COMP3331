#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###
#  Overview
#  --------
#  
#  The scenario is simple: a sender, or multiple senders, send a sequence of 
#  random numbers to a receiver. The receiver performs some basic modulo 
#  arithmetic to determine whether each random number it receives is odd or
#  even, and sends this information back to the sender.
#  
#  Message format from sender to receiver (2 bytes total):
#  
#  +-------------+
#  | Byte Offset |
#  +------+------+
#  |   0  |   1  |
#  +------+------+
#  |    number   |
#  +-------------+
#  
#  Message format from receiver to sender (3 bytes total):
#  
#  +--------------------+
#  |    Byte Offset     |
#  +------+------+------+
#  |   0  |   1  |   2  |
#  +------+------+------+
#  |    number   |  odd |
#  +-------------+------+
#  
#  
#  Description
#  -----------
#  
#  - The sender is invoked with three command-line arguments:  
#      1. the hostname or IP address of the receiver  
#      2. the port number of the receiver
#      3. the duration to run, in seconds, before terminating
#  
#  - The receiver is invoked with two command-line arguments:
#      1. the port number on which to listen for incoming messages
#      2. the duration to wait for a message, in seconds, before terminating
#  
#  The sender will spawn two child threads: one to listen for responses from
#  the receiver, and another to wait for a timer to expire. Meanwhile, the 
#  main thread will sit in a loop and send a sequence of random 16-bit 
#  unsigned integers to the receiver. Messages will be sent and received 
#  through an ephemeral (OS allocated) port. After each message is sent, the 
#  sender may sleep for a random amount of time.  Once the timer expires, 
#  the child threads, and then the sender process, will gracefully terminate.
#  
#  The receiver is single threaded and sits in a loop, waiting for messages. 
#  Each message is expected to contain a 16-bit unsigned integer. The receiver 
#  will determine whether the number is odd or even, and send a message back 
#  with the original number as well as a flag indicating whether the number 
#  is odd or even. If no message is received within a certain amount of time, 
#  the receiver will terminate.
#  
#  
#  Features
#  --------
#  
#  - Parsing command-line arguments
#  - Random number generation (sender only)
#  - Modulo arithmetic (receiver only)
#  - Communication via UDP sockets
#  - Non-blocking sockets (sender only)
#  - Blocking sockets with a timeout (receiver only)
#  - Using a "connected" UDP socket, to send() and recv() (sender only)
#  - Using an "unconnected" UDP socket, to sendto() and recvfrom() (receiver 
#    only)
#  - Conversion between host byte order and network byte order for 
#    multi-byte fields.
#  - Timers (sender only)
#  - Multi-threading (sender only)
#  - Simple logging
#  
#  
#  Usage
#  -----
#  
#  1. Run the receiver program:
#  
#      $ python3 receiver.py 54321 10
#  
#     This will invoke the receiver to listen on port 54321 and terminate
#     if no message is receieved within 10 seconds.
#  
#  2. Run the sender program:
#  
#      $ python3 sender.py 127.0.0.1 54321 30
#  
#     This will invoke the sender to send a sequence of random numbers to
#     the receiver at 127.0.0.1:54321, and terminate after 30 seconds.
#  
#     Multiple instances of the sender can be run against the same receiver.
#  
#  
#  Notes
#  -----
#  
#  - The sender and receiver are designed to be run on the same machine, 
#    or on different machines on the same network. They are not designed 
#    to be run on different networks, or on the public internet.
#  
#  
#  Author
#  ------
#  
#  Written by Tim Arney (t.arney@unsw.edu.au) for COMP3331/9331.
#  
#  
#  CAUTION
#  -------
#  
#  - This code is not intended to be simply copy and pasted.  Ensure you 
#    understand this code before using it in your own projects, and adapt
#    it to your own requirements.
#  - The sender adds artificial delay to its sending thread.  This is purely 
#    for demonstration purposes.  In general, you should NOT add artificial
#    delay as this will reduce efficiency and potentially mask other issues.
###

import socket
import sys

NUM_ARGS = 2  # Number of command-line arguments
BUF_SIZE = 3  # Size of buffer for sending/receiving data

def parse_wait_time(wait_time_str, min_wait_time=1, max_wait_time=60):
    """Parse the wait_time argument from the command-line.

    The parse_wait_time() function will attempt to parse the wait_time argument
    from the command-line into an integer. If the wait_time argument is not 
    numerical, or within the range of acceptable wait times, the program will
    terminate with an error message.

    Args:
        wait_time_str (str): The wait_time argument from the command-line.
        min_wait_time (int, optional): Minimum acceptable wait time. Defaults to 1.
        max_wait_time (int, optional): Maximum acceptable wait time. Defaults to 60.

    Returns:
        int: The wait_time as an integer.
    """
    try:
        wait_time = int(wait_time_str)
    except ValueError:
        sys.exit(f"Invalid wait_time argument, must be numerical: {wait_time_str}")
    
    if not (min_wait_time <= wait_time <= max_wait_time):
        sys.exit(f"Invalid wait_time argument, must be between {min_wait_time} and {max_wait_time} seconds: {wait_time_str}")
                 
    return wait_time

def parse_port(port_str, min_port=49152, max_port=65535):
    """Parse the port argument from the command-line.

    The parse_port() function will attempt to parse the port argument
    from the command-line into an integer. If the port argument is not 
    numerical, or within the acceptable port number range, the program will
    terminate with an error message.

    Args:
        port_str (str): The port argument from the command-line.
        min_port (int, optional): Minimum acceptable port. Defaults to 49152.
        max_port (int, optional): Maximum acceptable port. Defaults to 65535.

    Returns:
        int: The port as an integer.
    """
    try:
        port = int(port_str)
    except ValueError:
        sys.exit(f"Invalid port argument, must be numerical: {port_str}")
    
    if not (min_port <= port <= max_port):
        sys.exit(f"Invalid port argument, must be between {min_port} and {max_port}: {port}")
                 
    return port

if __name__ == "__main__":
    if len(sys.argv) != NUM_ARGS + 1:
        sys.exit(f"Usage: {sys.argv[0]} port wait_time")

    port      = parse_port(sys.argv[1])
    wait_time = parse_wait_time(sys.argv[2])

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('', port))              # bind to `port` on all interfaces
        s.settimeout(wait_time)         # set timeout for receiving data

        while True:
            # Here we're using recvfrom() and sendto(), but we could also 
            # connect() this UDP socket to set communication with a particular 
            # peer. This would allow us to use send() and recv() instead, 
            # but only communicate with one peer at a time.
            
            try:
                buf, addr = s.recvfrom(BUF_SIZE)
            except socket.timeout:
                print(f"No data within {wait_time} seconds, shutting down.")
                break

            if len(buf) < BUF_SIZE-1:
                print(f"recvfrom: received short message: {buf}", file=sys.stderr)
                continue

            # Packet was received, first (and only) field is multi-byte, 
            # so need to convert from network byte order (big-endian) to 
            # host byte order.  Then log the recv.
            num = int.from_bytes(buf[:2], byteorder='big')
            print(f"{addr[0]}:{addr[1]}: rcv: {num:>5}")

            # Determine whether the number is odd or even, and append the 
            # result (as a single byte) to the buffer.
            odd = num % 2
            buf += odd.to_bytes(1, byteorder='big')

            # Log the send and send the reply.
            print(f"{addr[0]}:{addr[1]}: snd: {num:>5} {'odd' if odd else 'even'}")
            if (s.sendto(buf, addr) != len(buf)):
                print(f"sendto: partial/failed send, message: {buf}", file=sys.stderr)
                continue

    sys.exit(0)