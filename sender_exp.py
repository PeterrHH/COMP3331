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

import random
import socket
import sys
import threading
import time
from dataclasses import dataclass

NUM_ARGS  = 3  # Number of command-line arguments
BUF_SIZE  = 3  # Size of buffer for receiving messages
MAX_SLEEP = 2  # Max seconds to sleep before sending the next message

@dataclass
class Control:
    """Control block: parameters for the sender program."""
    host: str               # Hostname or IP address of the receiver
    port: int               # Port number of the receiver
    socket: socket.socket   # Socket for sending/receiving messages
    run_time: int           # Run time in seconds
    is_alive: bool = True   # Flag to signal the sender program to terminate

def parse_run_time(run_time_str, min_run_time=1, max_run_time=60):
    """Parse the run_time argument from the command-line.

    The parse_run_time() function will attempt to parse the run_time argument
    from the command-line into an integer. If the run_time argument is not 
    numerical, or within the range of acceptable run times, the program will
    terminate with an error message.

    Args:
        run_time_str (str): The run_time argument from the command-line.
        min_run_time (int, optional): Minimum acceptable run time. Defaults to 1.
        max_run_time (int, optional): Maximum acceptable run time. Defaults to 60.

    Returns:
        int: The run_time as an integer.
    """
    try:
        run_time = int(run_time_str)
    except ValueError:
        sys.exit(f"Invalid run_time argument, must be numerical: {run_time_str}")
    
    if not (min_run_time <= run_time <= max_run_time):
        sys.exit(f"Invalid run_time argument, must be between {min_run_time} and {max_run_time} seconds: {run_time_str}")
                 
    return run_time

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

def setup_socket(host, port):
    """Setup a UDP socket for sending messages and receiving replies.

    The setup_socket() function will setup a UDP socket for sending data and
    receiving replies. The socket will be associated with the peer address 
    given by the host:port arguments. This will allow for send() calls without
    having to specify the peer address each time. It will also limit the 
    datagrams received to only those from the peer address.  The socket will
    be set to non-blocking mode.  If the socket fails to connect the program 
    will terminate with an error message.

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

def recv_thread(control):
    """The receiver thread function.

    The recv_thread() function is the entry point for the receiver thread. It
    will sit in a loop, checking for messages from the receiver. When a message 
    is received, the sender will unpack the message and print it to the log. On
    each iteration of the loop, it will check the `is_alive` flag. If the flag
    is false, the thread will terminate. The `is_alive` flag is shared with the
    main thread and the timer thread.

    Args:
        control (Control): The control block for the sender program.
    """
    while control.is_alive:
        try:
            nread = control.socket.recv(BUF_SIZE)
        except BlockingIOError:
            continue    # No data available to read
        except ConnectionRefusedError:
            print(f"recv: connection refused by {control.host}:{control.port}, shutting down...", file=sys.stderr)
            control.is_alive = False
            break

        if len(nread) < BUF_SIZE - 1:
            print(f"recv: received short message of {nread} bytes", file=sys.stderr)
            continue    # Short message, ignore it

        # Convert first 2 bytes (i.e. the number) from network byte order 
        # (big-endian) to host byte order, and extract the `odd` flag.
        num = int.from_bytes(nread[:2], "big")
        odd = nread[2]

        # Log the received message
        print(f"{control.host}:{control.port}: rcv: {num:>5} {'odd' if odd else 'even'}")

def timer_thread(control):
    """Stop execution when the timer expires.

    The timer_thread() function will be called when the timer expires. It will
    print a message to the log, and set the `is_alive` flag to False. This will
    signal the receiver thread, and the sender program, to terminate.

    Args:
        control (Control): The control block for the sender program.
    """
    print(f"{control.run_time} second timer expired, shutting down...")
    control.is_alive = False

if __name__ == "__main__":
    if len(sys.argv) != NUM_ARGS + 1:
        sys.exit(f"Usage: {sys.argv[0]} host port run_time")

    host     = sys.argv[1]
    port     = parse_port(sys.argv[2])
    run_time = parse_run_time(sys.argv[3])
    sock     = setup_socket(host, port)

    # Create a control block for the sender program.
    control = Control(host, port, sock, run_time)

    # Start the receiver and timer threads.
    receiver = threading.Thread(target=recv_thread, args=(control,))
    receiver.start()

    timer = threading.Timer(run_time, timer_thread, args=(control,))
    timer.start()

    random.seed()  # Seed the random number generator
    
    # Send a sequence of random numbers as separate datagrams, until the 
    # timer expires.
    while control.is_alive:
        num = random.randrange(2**16)       # Random number in range [0, 65535]
        net_num = num.to_bytes(2, "big")    # Convert number to network byte order

        # Log the send and then send the random number.
        print(f"{host}:{port}: snd: {num:>5}")
        nsent = control.socket.send(net_num)
        if nsent != len(net_num):
            control.is_alive = False
            sys.exit(f"send: partial/failed send of {nsent} bytes")

        # Sleep for a random amount of time before sending the next message.
        # This is ONLY done for the sake of the demonstration, it should be 
        # removed to maximise the efficiency of the sender.
        time.sleep(random.uniform(0, MAX_SLEEP + 1))
    
    # Suspend execution here and wait for the threads to finish.
    receiver.join()
    timer.cancel()

    control.socket.close()  # Close the socket

    print("Shut down complete.")

    sys.exit(0)