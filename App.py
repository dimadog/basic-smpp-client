from threading import *
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import socket
import os

import tkinter as tk
from tkinter import *
from tkinter import ttk
import tkinter.scrolledtext as scrolledtext

from libs import smpplib
from libs.smpplib import client, exceptions
from libs.smpplib import gsm
from libs.smpplib import consts


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("basic smpp client")
        self.geometry("1050x375")
        self.resizable(True, True)
        #self.iconphoto(False, tk.PhotoImage(file="assets/title_icon.png", master = self))

        logger_path = os.path.dirname(os.path.realpath(__file__))+'\\logs\\'+datetime.now().strftime("%d%m%Y-%H_%M")+'.log'
        print(logger_path)
        logger_handler = RotatingFileHandler(
            logger_path,
            maxBytes = 10485760,
            backupCount = 10
        )
        logging.basicConfig(handlers = [logger_handler], level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        TTL = {
                "1 min" :   '000000000100000R', 
                "2 mins":   '000000000200000R',
                "3 mins":   '000000000300000R', 
                "5 mins":   '000000000500000R', 
                "10 mins":  '000000001000000R', 
                "15 mins":  '000000001500000R', 
                "30 mins":  '000000003000000R', 
                "1 hour":   '000000010000000R', 
                "3 hours":  '000000030000000R', 
                "12 hours": '000000120000000R', 
                "1 day":    '000001000000000R', 
                "2 days":   '000002000000000R', 
                "3 days":   '000003000000000R'
        }

        STATUS = {1: 'ENROUTE', 
                  2: 'DELIVERED', 
                  3: 'EXPIRED', 
                  4: 'DELETED', 
                  5: 'UNDELIVERABLE', 
                  6: 'ACCEPTED', 
                  7: 'UNKNOWN',
                  8: 'REJECTED'}

        client = smpplib.client.Client('1','1')

        def ErrorPduHandler(pdu):
            LogScrolledText.insert(END,((f'\n{pdu.command} error code {hex(pdu.status)} at ' + datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f"))))
            LogScrolledText.see(END)
        client.set_error_pdu_handler(ErrorPduHandler)
        
        def SentMessageHandler(pdu) -> None:
            if pdu.status != 0:
                LogScrolledText.insert(END,((f'\nattempt to sent SMS FAILED({smpplib.consts.DESCRIPTIONS.get(pdu.status, 'Unknown status')}) at ' + datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f")).format(pdu.status)), 'FailedStatus')
            else:
                LogScrolledText.insert(END,((f'\nSMS {pdu.message_id} SENT at ' + datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f"))))
            LogScrolledText.see(END)
        client.set_message_sent_handler(SentMessageHandler)

        def ReceivedMassageHandler(pdu) -> None:
            if pdu.message_state == None:
                LogScrolledText.insert(END,((f'\nrecieved SMS {pdu.receipted_message_id} at ' + datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f"))))
                LogScrolledText.insert(END,(f'\nsender {pdu.source_addr} -> reciever {pdu.destination_addr}'))
                LogScrolledText.insert(END,(f'\ndata coding {pdu.data_coding}'))
                if pdu.data_coding == 8:
                    LogScrolledText.insert(END,('\ntext: ' + pdu.short_message.decode('utf-16-be', errors = 'ignore') ))
                else:
                    LogScrolledText.insert(END,('\ntext: ' + pdu.short_message.decode('utf8', errors = 'ignore')))
            else:
                LogScrolledText.insert(END,((f'\nSMS {pdu.receipted_message_id} '+(STATUS.get(pdu.message_state))+' at ' + datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f"))))
            LogScrolledText.see(END)
        client.set_message_received_handler(ReceivedMassageHandler)

        def threading(bind_type, command_name) -> None:
            try:
                #logger.info('threading() : connection thread STARTED')###
                #print('started', bind_type)
                BindThread = Thread(target = lambda: BindServer(bind_type,command_name))
                BindThread.daemon = True
                BindThread.start()
            except Exception as e:
                #logger.info(f'threading() : EXCEPTION {repr(e)}')###
                print('repr(e)')
                pass
               
        def BindServer(bind_type, command_name) -> None:
            if client.state != smpplib.consts.SMPP_CLIENT_STATE_CLOSED:
                client.host = None
                client.port = None
                client._socket = None
            try:
                client.host = ((Server_Combox.get()).split(':'))[0]
                client.port = int(((Server_Combox.get()).split(':'))[1])
                client.connect()
                client._bind(command_name, system_id = SystemId_Entry.get(), password = Password_Entry.get())
                LogScrolledText.insert(END,("\nconnection to "
                                            +str(client.host)
                                            +":"+str(client.port)
                                            +" ESTABLISHED ["
                                            + bind_type
                                            +"] at "
                                            +datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f")),
                                            'ConnectedStatus')
                LogScrolledText.see(END)
                ServerDisconnectButton.configure(state = ACTIVE)
                SendMessageButton.configure(state = ACTIVE)
                for element in button_dict:
                    button_dict.get(element).configure(state= DISABLED)
                client.listen()
            except (smpplib.exceptions.ConnectionError, 
                    smpplib.exceptions.UnknownCommandError, 
                    smpplib.exceptions.PDUError
                    ) as e:
                if type(e) == smpplib.exceptions.PDUError:
                    for element in button_dict:
                        button_dict.get(element).configure(state= ACTIVE)
                    ServerDisconnectButton.configure(state = DISABLED)
                    SendMessageButton.configure(state = DISABLED)
                    LogScrolledText.insert(END,("\nconnection to "
                                                +str(client.host)
                                                +":"
                                                +str(client.port)
                                                +" FAILED at "
                                                +datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f")),
                                                'FailedStatus')
                    LogScrolledText.see(END)
                    #logger.info('ServerConnect() : CONNECTION FAILED')######
                else:
                    for element in button_dict:
                        button_dict.get(element).configure(state= ACTIVE)
                    ServerDisconnectButton.configure(state = DISABLED)
                    SendMessageButton.configure(state = DISABLED)
                    LogScrolledText.insert(END,("\nconnection to "
                                                +str(client.host)
                                                +":"
                                                +str(client.port)
                                                +" CLOSED ["
                                                + bind_type
                                                +"] at "
                                                +datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f")))
                    LogScrolledText.see(END)
                    #logger.info('ServerConnect() : CONNECTION TERMINATED')######

        def ServerDisconnect() -> None:
            try:
                client.unbind()
                client.disconnect()
                client.__del__
            except smpplib.exceptions.PDUError:
                pass
            except smpplib.exceptions.ConnectionError:
                pass

        def SendMessage() -> None:
            try:
                SenderTON = int(SenderTON_Combox.get())
                SenderNPI = int(SenderNPI_Combox.get())
                Sender = Sender_Entry.get()
                ReceiverTON = int(ReceiverTON_Combox.get())
                ReceiverNPI = int(ReceiverNPI_Combox.get())
                Receiver = Receiver_Entry.get()
                MessageTTL = TTL.get(TTLCombox.get())
                parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts((u'{}').format(MessageScrolledText.get("1.0",'end-1c')))
                for part in parts:
                    pdu = client.send_message(source_addr_ton = SenderTON,
                                              source_addr_npi = SenderNPI,
                                              source_addr = Sender,
                                              dest_addr_ton = ReceiverTON,
                                              dest_addr_npi = ReceiverNPI,
                                              destination_addr = Receiver,
                                              short_message = part,
                                              data_coding = encoding_flag,
                                              esm_class = msg_type_flag,
                                              registered_delivery=True,
                                              validity_period= MessageTTL)
            except Exception as e:
                #logger.info(f'SendMessage() : {repr(e)}')######
                pass 
        
        #self.grid_rowconfigure((0,0), weight=1)
        self.grid_columnconfigure((3,3), weight=1)

        #SystemId Label + Entry
        SystemId_Label = tk.Label(self, text = 'system ID', font = ('', '8','bold'))
        SystemId_Label.grid(sticky="EW", row=0,  column=0, pady=3, padx=3)
        SystemId_Entry = tk.Entry(self, width=40 )
        SystemId_Entry.insert(END , 'dzyablicev')
        SystemId_Entry.grid(sticky="EW",row=0,  column=1, pady=3, padx=3)

        #Password Label + Entry
        Password_Label = tk.Label(self, text = 'password', font = ('', '8','bold'))
        Password_Label.grid(sticky="EW", row=1,  column=0, pady=3, padx=3)
        Password_Entry = tk.Entry(self, width=40 )
        Password_Entry.insert(END , 'Cpk8p6')
        Password_Entry.grid(sticky="EW", row=1,  column=1, pady=3, padx=3)

        #Server Label + Combox
        Server_Label = tk.Label(self, text = 'server')
        Bind_Label = tk.Label(self, text = 'bind')
        Server_Label.grid(sticky="EW", row=2,  column=0, pady=3, padx=3)
        Bind_Label.grid(sticky="EW", row=3,  column=0, pady=3, padx=3)
        Server_Combox = ttk.Combobox(
            self,
            width = 37,
            state = 'readonly',
            values= ["10.10.10.10:8888", "10.10.10.10:8888" , "10.10.10.10:8888"]
        )
        Server_Combox.grid(sticky="EW",row=2 , column=1, pady=3, padx=3)
        Server_Combox.current(0)

        BindTXButton = ttk.Button(self, 
                                         text = 'TX', 
                                         compound='text', 
                                         width = 3, 
                                         command = lambda: threading('TX', 'bind_transmitter'))
        BindTXButton.grid(sticky="W", row = 3, column = 1, padx=(2,0))

        BindRXButton = ttk.Button(self, 
                                         text = 'RX', 
                                         compound='text', 
                                         width = 3, 
                                         command = lambda: threading('RX', 'bind_receiver'))
        BindRXButton.grid(sticky="W", row = 3, column = 1, padx = (30,0))

        BindTRXButton = ttk.Button(self, 
                                         text = 'TRX', 
                                         compound='text', 
                                         width = 4, 
                                         command = lambda: threading('TRX', 'bind_transceiver'))
        BindTRXButton.grid(sticky="W", row = 3, column = 1, padx=(58,0))

        button_dict = {'TX' : BindTXButton, 'RX' : BindRXButton, 'TRX' : BindTRXButton}

        #ServerDisonnectButton
        ServerDisconnectButton = ttk.Button(self,
                                            text = 'disconnect',
                                            compound='text', 
                                            width = 12 , 
                                            command = ServerDisconnect, 
                                            state = DISABLED)
        ServerDisconnectButton.grid(sticky="E", row = 3, column = 1, padx=(0,3))

        #Sender(TON + NPI) Label + Combox + Entry
        Sender_Label = tk.Label(self, text = 'sender', font = ('', '8','bold'))
        Sender_Label.grid( sticky="EW", row=4,  column=0, pady=3, padx=3)
        SenderTON_Combox = ttk.Combobox(
            self,
            width = 2,
            state = 'readonly',
            values= ["0", "1", "2", "3", "4", "5", "6"]
        )
        SenderTON_Combox.grid(sticky="W", row=4,  column=1, pady=3, padx=3)
        SenderTON_Combox.current(0)
        SenderNPI_Combox = ttk.Combobox(
            self,
            width = 2,
            state = 'readonly',
            values= ["0", "1", "3", "5", "6", "8", "9", "10", "13", "18"]
        )
        SenderNPI_Combox.grid(row=4, column=1, padx=(0,120))
        SenderNPI_Combox.current(1)
        Sender_Entry = tk.Entry(self, width=25 )
        Sender_Entry.insert(END , '12345')
        Sender_Entry.grid(sticky="E", row=4,  column=1, pady=1 , padx = 3)

        #Receiver(TON + NPI) Label + Combox + Entry
        Receiver_Label = tk.Label(self, text = 'receiver', font = ('', '8','bold'))
        Receiver_Label.grid( sticky="EW", row=5,  column=0, pady=3, padx=3)
        ReceiverTON_Combox = ttk.Combobox(
            self,
            width = 2,
            state = 'readonly',
            values= ["0", "1", "2", "3", "4", "5", "6"]
        )
        ReceiverTON_Combox.grid(sticky="W", row=5,  column=1, pady=3, padx=3)
        ReceiverTON_Combox.current(1)
        ReceiverNPI_Combox = ttk.Combobox(
            self,
            width = 2,
            state = 'readonly',
            values= ["0", "1", "3", "5", "6", "8", "9", "10", "13", "18"]
        )
        ReceiverNPI_Combox.grid(row=5, column=1, padx=(0,120))
        ReceiverNPI_Combox.current(1)
        Receiver_Entry = tk.Entry(self, width=25,  )
        Receiver_Entry.insert(END , '12345')
        Receiver_Entry.grid(sticky="E", row=5,  column=1, pady=1 , padx = 3)

        #MessageLabel + MessageScrolledText
        MessageLabel = tk.Label(self, text = 'text')
        MessageLabel.grid(sticky="EW", row = 7, column = 0, rowspan = 3, padx = 3, pady = 3)
        MessageScrolledText = scrolledtext.ScrolledText(self, height = 11, width = 32 )
        MessageScrolledText.grid(sticky="W", row = 7, column = 1, rowspan = 3 , columnspan = 2, padx = 3, pady = 3)
        MessageScrolledText.insert(END, 'Hello!')

        #SendMessageButton + TTLLabel + TTLCombox
        TTLLabel = tk.Label(self, text = 'ttl', font = ('', '8','bold'))
        TTLLabel.grid( sticky="EW", row=11,  column=0, pady=3, padx=3)
        TTLCombox = ttk.Combobox(self,
                                 state = 'readonly',
                                 values= ["1 min", "2 mins", "3 mins", "5 mins", "10 mins", "15 mins", "30 mins", "1 hour", "3 hours", "12 hours", "1 day", "2 days", "3 days"]
        )
        TTLCombox.grid(sticky="W", row = 11, column = 1, pady = 3, padx=(2,0))
        TTLCombox.current(0)
        SendMessageButton = ttk.Button(self,
                                       text = 'send',
                                       compound='text',
                                       width = 12,
                                       command = SendMessage,
                                       state = DISABLED)
        SendMessageButton.grid(sticky="E", row = 11, column = 1, pady = 3, padx=(0,3))
        
        #LogScrolledText
        LogScrolledText = scrolledtext.ScrolledText(self, height = 23, width = 1000)
        LogScrolledText.see(tk.END)
        LogScrolledText.tag_configure('ConnectedStatus',foreground = 'green')                
        LogScrolledText.tag_configure('FailedStatus',foreground = 'red')                
        LogScrolledText.insert(END,("started at "+datetime.now().strftime("%d.%m.%Y , %H:%M:%S.%f")))
        LogScrolledText.grid( row = 0, column = 3, rowspan = 12) 
