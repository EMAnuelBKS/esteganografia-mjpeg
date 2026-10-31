#class RTPpacket

class RTPpacket:

    #size of the RTP header:
    HEADER_SIZE = 12

    #--------------------------
    #Constructor of an RTPpacket object from header fields and payload bitstream
    #  RTPpacket(PType, Framenb, Time, data, data_length)
    #Constructor of an RTPpacket object from the packet bistream
    #  RTPpacket(packet, packet_size)
    #--------------------------
    def __init__(self, *args):
        if len(args) == 5:
            PType, Framenb, Time, data, data_length = args

            #fill by default header fields:
            self.Version = 2
            self.Padding = 0
            self.Extension = 0
            self.CC = 0
            self.Marker = 0
            self.Ssrc = 0

            #fill changing header fields:
            self.SequenceNumber = Framenb
            self.TimeStamp = Time
            self.PayloadType = PType

            #build the header bistream:
            #--------------------------
            self.header = bytearray(RTPpacket.HEADER_SIZE)

            #fill the header array of byte with RTP header fields
            self.header[0] = (self.Version << 6) | (self.Padding << 5) | (self.Extension << 4) | self.CC
            self.header[1] = (self.Marker << 7) | self.PayloadType
            self.header[2] = (self.SequenceNumber >> 8) & 0xFF
            self.header[3] = self.SequenceNumber & 0xFF
            self.header[4] = (self.TimeStamp >> 24) & 0xFF
            self.header[5] = (self.TimeStamp >> 16) & 0xFF
            self.header[6] = (self.TimeStamp >> 8) & 0xFF
            self.header[7] = self.TimeStamp & 0xFF
            self.header[8] = (self.Ssrc >> 24) & 0xFF
            self.header[9] = (self.Ssrc >> 16) & 0xFF
            self.header[10] = (self.Ssrc >> 8) & 0xFF
            self.header[11] = self.Ssrc & 0xFF

            #fill the payload bitstream:
            #--------------------------
            self.payload_size = data_length
            self.payload = bytearray(data_length)

            #fill payload array of byte from data (given in parameter of the constructor)
            for i in range(data_length):
                self.payload[i] = data[i]

        else:
            packet, packet_size = args

            #fill default fields:
            self.Version = 2
            self.Padding = 0
            self.Extension = 0
            self.CC = 0
            self.Marker = 0
            self.Ssrc = 0

            #check if total packet size is lower than the header size
            if packet_size >= RTPpacket.HEADER_SIZE:
                #get the header bitsream:
                self.header = bytearray(RTPpacket.HEADER_SIZE)
                for i in range(RTPpacket.HEADER_SIZE):
                    self.header[i] = packet[i]

                #get the payload bitstream:
                self.payload_size = packet_size - RTPpacket.HEADER_SIZE
                self.payload = bytearray(self.payload_size)
                for i in range(RTPpacket.HEADER_SIZE, packet_size):
                    self.payload[i - RTPpacket.HEADER_SIZE] = packet[i]

                #interpret the changing fields of the header:
                self.PayloadType = self.header[1] & 127
                self.SequenceNumber = RTPpacket.unsigned_int(self.header[3]) + 256 * RTPpacket.unsigned_int(self.header[2])
                self.TimeStamp = (RTPpacket.unsigned_int(self.header[7]) + 256 * RTPpacket.unsigned_int(self.header[6])
                                  + 65536 * RTPpacket.unsigned_int(self.header[5]) + 16777216 * RTPpacket.unsigned_int(self.header[4]))

    #--------------------------
    #getpayload: return the payload bistream of the RTPpacket and its size
    #--------------------------
    def getpayload(self, data):

        for i in range(self.payload_size):
            data[i] = self.payload[i]

        return self.payload_size

    #--------------------------
    #getpayload_length: return the length of the payload
    #--------------------------
    def getpayload_length(self):
        return self.payload_size

    #--------------------------
    #getlength: return the total length of the RTP packet
    #--------------------------
    def getlength(self):
        return self.payload_size + RTPpacket.HEADER_SIZE

    #--------------------------
    #getpacket: returns the packet bitstream and its length
    #--------------------------
    def getpacket(self, packet):
        #construct the packet = header + payload
        for i in range(RTPpacket.HEADER_SIZE):
            packet[i] = self.header[i]
        for i in range(self.payload_size):
            packet[i + RTPpacket.HEADER_SIZE] = self.payload[i]

        #return total size of the packet
        return self.payload_size + RTPpacket.HEADER_SIZE

    #--------------------------
    #gettimestamp
    #--------------------------
    def gettimestamp(self):
        return self.TimeStamp

    #--------------------------
    #getsequencenumber
    #--------------------------
    def getsequencenumber(self):
        return self.SequenceNumber

    #--------------------------
    #getpayloadtype
    #--------------------------
    def getpayloadtype(self):
        return self.PayloadType

    #--------------------------
    #print headers without the SSRC
    #--------------------------
    def printheader(self):
        for i in range(RTPpacket.HEADER_SIZE - 4):
            for j in range(7, -1, -1):
                if ((1 << j) & self.header[i]) != 0:
                    print("1", end="")
                else:
                    print("0", end="")
            print(" ", end="")

        print()

    #return the unsigned value of 8-bit integer nb
    @staticmethod
    def unsigned_int(nb):
        if nb >= 0:
            return nb
        else:
            return 256 + nb
