# ------------------
#    Server
#    usage: python Server.py [RTSP listening port]
# ----------------------

import os
import socket
import sys
import threading
import time
import tkinter as tk

from RTPpacket import RTPpacket
from VideoStream import VideoStream


class Timer:
    def __init__(self, delay, listener):
        self.delay = delay / 1000.0
        self.listener = listener
        self.running = False
        self._gen = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self._gen += 1
        threading.Thread(target=self._run, args=(self._gen,), daemon=True).start()

    def stop(self):
        self.running = False

    def _run(self, gen):
        while self.running and gen == self._gen:
            self.listener()
            time.sleep(self.delay)


class Server(tk.Tk):

    #Video variables:
    #----------------
    MJPEG_TYPE = 26 #RTP payload type for MJPEG video
    FRAME_PERIOD = 100 #Frame period of the video to stream, in ms
    VIDEO_LENGTH = 500 #length of the video in frames

    #RTSP variables
    #----------------
    #rtsp states
    INIT = 0
    READY = 1
    PLAYING = 2
    #rtsp message types
    SETUP = 3
    PLAY = 4
    PAUSE = 5
    TEARDOWN = 6

    state = None #RTSP Server state == INIT or READY or PLAY
    RTSPBufferedReader = None
    RTSPBufferedWriter = None
    VideoFileName = None #video file requested from the client
    RTSP_ID = 123456 #ID of the RTSP session

    CRLF = "\r\n"

    #--------------------------------
    #Constructor
    #--------------------------------
    def __init__(self):

        #init Frame
        super().__init__()
        self.title("Server")

        #RTP variables:
        #----------------
        self.RTPsocket = None #socket to be used to send and receive UDP packets
        self.senddp = None #UDP packet containing the video frames

        self.ClientIPAddr = None #Client IP address
        self.RTP_dest_port = 0 #destination port for RTP packets  (given by the RTSP Client)

        #Video variables:
        #----------------
        self.imagenb = 0 #image nb of the image currently transmitted
        self.video = None #VideoStream object used to access video frames

        self.RTSPsocket = None #socket used to send/receive RTSP messages
        self.RTSPSeqNb = 0 #Sequence number of RTSP messages within the session

        #init Timer
        self.timer = Timer(Server.FRAME_PERIOD, self.actionPerformed)

        #allocate memory for the sending buffer
        self.buf = bytearray(15000)

        #Handler to close the main window
        def windowClosing():
            #stop the timer and exit
            self.timer.stop()
            os._exit(0)
        self.protocol("WM_DELETE_WINDOW", windowClosing)

        #GUI:
        self.label = tk.Label(self, text="Send frame #        ")
        self.label.pack(fill="both", expand=True)

        #the RTSP/timer threads only set label_text; the GUI thread applies it
        self.label_text = "Send frame #        "
        self.after(50, self.refresh_label)

    def refresh_label(self):
        self.label.config(text=self.label_text)
        self.after(50, self.refresh_label)

    #------------------------
    #Handler for timer
    #------------------------
    def actionPerformed(self):

        #if the current image nb is less than the length of the video
        if self.imagenb < Server.VIDEO_LENGTH:
            #update current imagenb
            self.imagenb += 1

            try:
                #get next frame to send from the video, as well as its size
                image_length = self.video.getnextframe(self.buf)

                #Builds an RTPpacket object containing the frame
                rtp_packet = RTPpacket(Server.MJPEG_TYPE, self.imagenb, self.imagenb * Server.FRAME_PERIOD, self.buf, image_length)

                #get to total length of the full rtp packet to send
                packet_length = rtp_packet.getlength()

                #retrieve the packet bitstream and store it in an array of bytes
                packet_bits = bytearray(packet_length)
                rtp_packet.getpacket(packet_bits)

                #send the packet as a DatagramPacket over the UDP socket
                self.RTPsocket.sendto(bytes(packet_bits), (self.ClientIPAddr, self.RTP_dest_port))

                #print("Send frame #" + str(self.imagenb))
                #print the header bitstream
                rtp_packet.printheader()

                #update GUI
                self.label_text = "Send frame #" + str(self.imagenb)
            except Exception as ex:
                print("Exception caught: " + str(ex))
                os._exit(0)
        else:
            #if we have reached the end of the video file, stop the timer
            self.timer.stop()

    #------------------------------------
    #Parse RTSP Request
    #------------------------------------
    def parse_RTSP_request(self):
        request_type = -1
        try:
            #parse request line and extract the request_type:
            RequestLine = Server.RTSPBufferedReader.readline().rstrip("\r\n")
            #print("RTSP Server - Received from Client:")
            print(RequestLine)

            tokens = RequestLine.split()
            request_type_string = tokens.pop(0)

            #convert to request_type structure:
            if request_type_string == "SETUP":
                request_type = Server.SETUP
            elif request_type_string == "PLAY":
                request_type = Server.PLAY
            elif request_type_string == "PAUSE":
                request_type = Server.PAUSE
            elif request_type_string == "TEARDOWN":
                request_type = Server.TEARDOWN

            if request_type == Server.SETUP:
                #extract VideoFileName from RequestLine
                Server.VideoFileName = tokens.pop(0)

            #parse the SeqNumLine and extract CSeq field
            SeqNumLine = Server.RTSPBufferedReader.readline().rstrip("\r\n")
            print(SeqNumLine)
            tokens = SeqNumLine.split()
            self.RTSPSeqNb = int(tokens[1])

            #get LastLine
            LastLine = Server.RTSPBufferedReader.readline().rstrip("\r\n")
            print(LastLine)

            if request_type == Server.SETUP:
                #extract RTP_dest_port from LastLine
                tokens = LastLine.split()
                self.RTP_dest_port = int(tokens[3]) #skip unused stuff
            #else LastLine will be the SessionId line ... do not check for now.
        except Exception as ex:
            print("Exception caught: " + str(ex))
            os._exit(0)
        return request_type

    #------------------------------------
    #Send RTSP Response
    #------------------------------------
    def send_RTSP_response(self):
        try:
            Server.RTSPBufferedWriter.write("RTSP/1.0 200 OK" + Server.CRLF)
            Server.RTSPBufferedWriter.write("CSeq: " + str(self.RTSPSeqNb) + Server.CRLF)
            Server.RTSPBufferedWriter.write("Session: " + str(Server.RTSP_ID) + Server.CRLF)
            Server.RTSPBufferedWriter.flush()
            #print("RTSP Server - Sent response to Client.")
        except Exception as ex:
            print("Exception caught: " + str(ex))
            os._exit(0)


#------------------------------------
#main
#------------------------------------
def rtsp_main(theServer, argv):
    #get RTSP socket port from the command line
    RTSPport = int(argv[0])

    #Initiate TCP connection with the client for the RTSP session
    listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listenSocket.bind(("", RTSPport))
    listenSocket.listen(1)
    theServer.RTSPsocket, addr = listenSocket.accept()
    listenSocket.close()

    #Get Client IP address
    theServer.ClientIPAddr = theServer.RTSPsocket.getpeername()[0]

    #Initiate RTSPstate
    Server.state = Server.INIT

    #Set input and output stream filters:
    Server.RTSPBufferedReader = theServer.RTSPsocket.makefile('r')
    Server.RTSPBufferedWriter = theServer.RTSPsocket.makefile('w', newline='')

    #Wait for the SETUP message from the client
    done = False
    while not done:
        request_type = theServer.parse_RTSP_request() #blocking

        if request_type == Server.SETUP:
            done = True

            #update RTSP state
            Server.state = Server.READY
            print("New RTSP state: READY")

            #Send response
            theServer.send_RTSP_response()

            #init the VideoStream object:
            theServer.video = VideoStream(Server.VideoFileName)

            #init RTP socket
            theServer.RTPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #loop to handle RTSP requests
    while True:
        #parse the request
        request_type = theServer.parse_RTSP_request() #blocking

        if request_type == Server.PLAY and Server.state == Server.READY:
            #send back response
            theServer.send_RTSP_response()
            #start timer
            theServer.timer.start()
            #update state
            Server.state = Server.PLAYING
            print("New RTSP state: PLAYING")
        elif request_type == Server.PAUSE and Server.state == Server.PLAYING:
            #send back response
            theServer.send_RTSP_response()
            #stop timer
            theServer.timer.stop()
            #update state
            Server.state = Server.READY
            print("New RTSP state: READY")
        elif request_type == Server.TEARDOWN:
            #send back response
            theServer.send_RTSP_response()
            #stop timer
            theServer.timer.stop()
            #close sockets
            theServer.RTSPsocket.close()
            theServer.RTPsocket.close()

            os._exit(0)


if __name__ == "__main__":
    #create a Server object
    theServer = Server()

    #the RTSP loop blocks, so it runs in its own thread while the GUI runs here
    threading.Thread(target=rtsp_main, args=(theServer, sys.argv[1:]), daemon=True).start()

    #show GUI:
    theServer.mainloop()
