#VideoStream

class VideoStream:

    #-----------------------------------
    #constructor
    #-----------------------------------
    def __init__(self, filename):

        #init variables
        self.fis = open(filename, 'rb') #video file
        self.frame_nb = 0 #current frame nb

    #-----------------------------------
    # getnextframe
    #returns the next frame as an array of byte and the size of the frame
    #-----------------------------------
    def getnextframe(self, frame):
        length = 0

        #read current frame length
        frame_length = self.fis.read(5)

        #transform frame_length to integer
        length_string = frame_length.decode()
        length = int(length_string)

        data = self.fis.read(length)
        frame[0:len(data)] = data
        return len(data) if len(data) > 0 else -1
