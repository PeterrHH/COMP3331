import random
import utils.Constant as Constant

def gen_random():
    return random.randint(0, 2**16)

'''
Check if the segment matches the seq# from ACK received

If segment seq# + length of data > MAX 2**16-1, it will get deducted by 2**16-1,
Then it checks if they matches

segment: segment of your choice (e.g. segment from buffer)
seqno_field: seq# from packet

can be use to check for matches and duplicates.
'''
def check_seqno_match(segment, seqno_field):
    segment_seqno = int.from_bytes(segment[2:4],byteorder='big')+len(segment[4:])
    if  segment_seqno > Constant.MAX_SEQ:
        segment_seqno -= Constant.MAX_SEQ
    
    if segment_seqno == seqno_field:
        return True
    else:
        return False