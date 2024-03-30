# COMP3331

Assignment for COMP3331 Term 1 2024. For details checkout assignment spec.

## Project Architecture
.
├── src                     # Source files (including all project implementation file)
│    ├──  utils             # Contains Helper functions and Constants Defined for the project
│    ├──  receiver.py       # Implementation file for recevier.py
│    ├──  sender.py         # Implementation file for sender.py
│    ├──  sender_log.txt    # Log file that logs behavior of segments send and received by sender as well as summary statistics in the connection
│    ├──  receiver_log.txt  # Log file that logs behavior of segments send and received by receiver as well as summary statistics in the connection
├── sample_txt              # Contains sample txt files that can be used for testing purposes


## Sender Implementation
1. Initialised a Initial Sequence Number (ISN), which is randomly chosen from 0 to 2**16-1. 
2. Establish Connection by sending *SYN* to receiver with the sequence number as the ISN.

## Receiver Implementation
1. Wait for a *SYN* from Sender. Once received, send an *ACK* back to Sender.
