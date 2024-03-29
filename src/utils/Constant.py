# both sender and receiver are localhost, will use the same address
ADDRESS = "127.0.0.1"

DATA = 0
ACK = 1
SYN = 2
FIN = 3

MAX_MSS = 1000 # in byte

MSL = 1 # maximum Segment Life (in seconds)

MAX_SEQ = 2**16-1

SENDER_LOG_TEXT = "sender_log.txt"
RECEIVER_LOG_TEXT = "receiver_log.txt"