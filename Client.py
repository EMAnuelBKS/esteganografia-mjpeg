# ------------------
#    Client
#    usage: python Client.py [Server hostname] [Server RTSP listening port] [Video file requested]
# ----------------------

import io
import socket
import sys
import tkinter as tk

from PIL import Image, ImageTk

from RTPpacket import RTPpacket


class Timer:
    def __init__(self, root, delay, listener):
        self.root = root
        self.delay = delay
        self.listener = listener
        self.running = False
        self._gen = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self._gen += 1
        gen = self._gen
        self.root.after(0, lambda: self._tick(gen))

    def stop(self):
        self.running = False

    def _tick(self, gen):
        if not self.running or gen != self._gen:
            return
        self.listener()
        self.root.after(self.delay, lambda: self._tick(gen))


class Client:

    #RTP variables:
    #----------------
    RTP_RCV_PORT = 25000 #port where the client will receive the RTP packets

    #RTSP variables
    #----------------
    #rtsp states
    INIT = 0
    READY = 1
    PLAYING = 2
    state = None #RTSP state == INIT or READY or PLAYING
    RTSPBufferedReader = None
    RTSPBufferedWriter = None
    VideoFileName = None #video file to request to the server

    CRLF = "\r\n"

    #Video constants:
    #------------------
    MJPEG_TYPE = 26 #RTP payload type for MJPEG video

    #--------------------------
    #Constructor
    #--------------------------
    def __init__(self):

        #GUI
        #----
        self.f = tk.Tk()
        self.f.title("Client")
        self.mainPanel = tk.Frame(self.f)
        self.imagePanel = tk.Frame(self.mainPanel, width=380, height=280)
        self.buttonPanel = tk.Frame(self.mainPanel)
        self.iconLabel = tk.Label(self.imagePanel)
        self.icon = None

        #RTP variables:
        #----------------
        self.rcvdp = None #UDP packet received from the server
        self.RTPsocket = None #socket to be used to send and receive UDP packets

        #RTSP variables
        #----------------
        self.RTSPsocket = None #socket used to send/receive RTSP messages
        self.RTSPSeqNb = 0 #Sequence number of RTSP messages within the session
        self.RTSPid = 0 #ID of the RTSP session (given by the RTSP Server)

        #build GUI
        #--------------------------

        #Frame
        self.f.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

        #Buttons
        for c in range(4):
            self.buttonPanel.columnconfigure(c, weight=1)
        self.buttonPanel.rowconfigure(0, weight=1)
        self.setupButton = tk.Button(self.buttonPanel, text="Setup", command=self.setupButtonListener)
        self.playButton = tk.Button(self.buttonPanel, text="Play", command=self.playButtonListener)
        self.pauseButton = tk.Button(self.buttonPanel, text="Pause", command=self.pauseButtonListener)
        self.tearButton = tk.Button(self.buttonPanel, text="Teardown", command=self.tearButtonListener)
        self.setupButton.grid(row=0, column=0, sticky="nsew")
        self.playButton.grid(row=0, column=1, sticky="nsew")
        self.pauseButton.grid(row=0, column=2, sticky="nsew")
        self.tearButton.grid(row=0, column=3, sticky="nsew")

        #Image display label
        self.iconLabel.config(image="")

        #frame layout
        self.mainPanel.pack(fill="both", expand=True)
        self.mainPanel.columnconfigure(0, weight=1)
        self.mainPanel.rowconfigure(0, weight=1)
        self.imagePanel.grid(row=0, column=0, sticky="nsew")
        self.iconLabel.place(x=0, y=0, relwidth=1, relheight=1)
        self.buttonPanel.grid(row=1, column=0, sticky="ew")

        self.f.geometry("390x370")
        self.f.minsize(300, 200)

        #init timer
        #--------------------------
        self.timer = Timer(self.f, 20, self.timerListener)

        #allocate enough memory for the buffer used to receive data from the server
        self.buf = bytearray(65535)

    #------------------------------------
    #Handler for buttons
    #------------------------------------

    #.............
    #TO COMPLETE
    #.............

    #Handler for Setup button
    #-----------------------
    def setupButtonListener(self):

        #print("Setup Button pressed !")

        if Client.state == Client.INIT:
            #Init non-blocking RTPsocket that will be used to receive data
            try:
                #construct a new DatagramSocket to receive RTP packets from the server, on port RTP_RCV_PORT
                self.RTPsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.RTPsocket.bind(("", Client.RTP_RCV_PORT))

                #set TimeOut value of the socket to 5msec.
                self.RTPsocket.settimeout(0.005)
            except socket.error as se:
                print("Socket exception: " + str(se))
                sys.exit(0)

            #init RTSP sequence number
            self.RTSPSeqNb = 1

            #Send SETUP message to the server
            self.send_RTSP_request("SETUP")

            #Wait for the response
            if self.parse_server_response() != 200:
                print("Invalid Server Response")
            else:
                #change RTSP state and print new state
                Client.state = Client.READY
                print("New RTSP state: READY")
        #else if state != INIT then do nothing

    #Handler for Play button
    #-----------------------
    def playButtonListener(self):

        #print("Play Button pressed !")

        if Client.state == Client.READY:
            #increase RTSP sequence number
            self.RTSPSeqNb += 1

            #Send PLAY message to the server
            self.send_RTSP_request("PLAY")

            #Wait for the response
            if self.parse_server_response() != 200:
                print("Invalid Server Response")
            else:
                #change RTSP state and print out new state
                Client.state = Client.PLAYING
                print("New RTSP state: PLAYING")

                #start the timer
                self.timer.start()
        #else if state != READY then do nothing

    #Handler for Pause button
    #-----------------------
    def pauseButtonListener(self):

        #print("Pause Button pressed !")

        if Client.state == Client.PLAYING:
            #increase RTSP sequence number
            self.RTSPSeqNb += 1

            #Send PAUSE message to the server
            self.send_RTSP_request("PAUSE")

            #Wait for the response
            if self.parse_server_response() != 200:
                print("Invalid Server Response")
            else:
                #change RTSP state and print out new state
                Client.state = Client.READY
                print("New RTSP state: READY")

                #stop the timer
                self.timer.stop()
        #else if state != PLAYING then do nothing

    #Handler for Teardown button
    #-----------------------
    def tearButtonListener(self):

        #print("Teardown Button pressed !")

        #increase RTSP sequence number
        self.RTSPSeqNb += 1

        #Send TEARDOWN message to the server
        self.send_RTSP_request("TEARDOWN")

        #Wait for the response
        if self.parse_server_response() != 200:
            print("Invalid Server Response")
        else:
            #change RTSP state and print out new state
            Client.state = Client.INIT
            print("New RTSP state: INIT")

            #stop the timer
            self.timer.stop()

            #exit
            sys.exit(0)

    #------------------------------------
    #Handler for timer
    #------------------------------------
    def timerListener(self):

        #Construct a DatagramPacket to receive data from the UDP socket
        #(buf is used as the receive buffer)

        try:
            #receive the DP from the socket:
            data, addr = self.RTPsocket.recvfrom(len(self.buf))
            self.rcvdp = data

            #create an RTPpacket object from the DP
            rtp_packet = RTPpacket(self.rcvdp, len(self.rcvdp))

            #print important header fields of the RTP packet received:
            print("Got RTP packet with SeqNum # " + str(rtp_packet.getsequencenumber()) + " TimeStamp " + str(rtp_packet.gettimestamp()) + " ms, of type " + str(rtp_packet.getpayloadtype()))

            #print header bitstream:
            rtp_packet.printheader()

            #get the payload bitstream from the RTPpacket object
            payload_length = rtp_packet.getpayload_length()
            payload = bytearray(payload_length)
            rtp_packet.getpayload(payload)

            #get an Image object from the payload bitstream
            image = Image.open(io.BytesIO(bytes(payload)))

            #scale the image to the current size of the display area, keeping the aspect ratio
            w = self.iconLabel.winfo_width()
            h = self.iconLabel.winfo_height()
            if w > 1 and h > 1:
                scale = min(w / image.width, h / image.height)
                image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.BILINEAR)

            #display the image as an ImageIcon object
            self.icon = ImageTk.PhotoImage(image)
            self.iconLabel.config(image=self.icon)
        except socket.timeout:
            #print("Nothing to read")
            pass
        except OSError as ioe:
            print("Exception caught: " + str(ioe))

    #------------------------------------
    #Parse Server Response
    #------------------------------------
    def parse_server_response(self):
        reply_code = 0

        try:
            #parse status line and extract the reply_code:
            StatusLine = Client.RTSPBufferedReader.readline().rstrip("\r\n")
            #print("RTSP Client - Received from Server:")
            print(StatusLine)

            tokens = StatusLine.split()
            reply_code = int(tokens[1]) #skip over the RTSP version

            #if reply code is OK get and print the 2 other lines
            if reply_code == 200:
                SeqNumLine = Client.RTSPBufferedReader.readline().rstrip("\r\n")
                print(SeqNumLine)

                SessionLine = Client.RTSPBufferedReader.readline().rstrip("\r\n")
                print(SessionLine)

                #if state == INIT gets the Session Id from the SessionLine
                tokens = SessionLine.split()
                self.RTSPid = int(tokens[1]) #skip over the Session:
        except Exception as ex:
            print("Exception caught: " + str(ex))
            sys.exit(0)

        return reply_code

    #------------------------------------
    #Send RTSP Request
    #------------------------------------

    #.............
    #TO COMPLETE
    #.............

    def send_RTSP_request(self, request_type):
        try:
            #Use the RTSPBufferedWriter to write to the RTSP socket

            #write the request line:
            Client.RTSPBufferedWriter.write(request_type + " " + Client.VideoFileName + " RTSP/1.0" + Client.CRLF)

            #write the CSeq line:
            Client.RTSPBufferedWriter.write("CSeq: " + str(self.RTSPSeqNb) + Client.CRLF)

            #check if request_type is equal to "SETUP" and in this case write the Transport: line advertising to the server the port used to receive the RTP packets RTP_RCV_PORT
            if request_type == "SETUP":
                Client.RTSPBufferedWriter.write("Transport: RTP/UDP; client_port= " + str(Client.RTP_RCV_PORT) + Client.CRLF)
            #otherwise, write the Session line from the RTSPid field
            else:
                Client.RTSPBufferedWriter.write("Session: " + str(self.RTSPid) + Client.CRLF)

            Client.RTSPBufferedWriter.flush()
        except Exception as ex:
            print("Exception caught: " + str(ex))
            sys.exit(0)


#------------------------------------
#main
#------------------------------------
def main(argv):
    #Create a Client object
    theClient = Client()

    #get server RTSP port and IP address from the command line
    #------------------
    RTSP_server_port = int(argv[1])
    ServerHost = argv[0]
    ServerIPAddr = socket.gethostbyname(ServerHost)

    #get video filename to request:
    Client.VideoFileName = argv[2]

    #Establish a TCP connection with the server to exchange RTSP messages
    #------------------
    theClient.RTSPsocket = socket.create_connection((ServerIPAddr, RTSP_server_port))

    #Set input and output stream filters:
    Client.RTSPBufferedReader = theClient.RTSPsocket.makefile('r')
    Client.RTSPBufferedWriter = theClient.RTSPsocket.makefile('w', newline='')

    #init RTSP state:
    Client.state = Client.INIT

    theClient.f.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])