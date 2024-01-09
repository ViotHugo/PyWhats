import os
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog
import base64
from ttkthemes import ThemedTk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import asyncio
import websockets
import threading

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("PyWhats")
        
        # Choix d'un thème proche de WhatsApp
        self.style = ttk.Style('minty')

        # Créer des styles personnalisés pour les cadres
        self.style.configure('TopFrame.TFrame', background='#f0ead6')
        self.style.configure('ChatFrame.TFrame', background='#eae0c8')

        # Barre de menu supérieure avec mise en valeur de l'interlocuteur
        self.top_frame = ttk.Frame(self.root, padding="3 12 12 12", style='TopFrame.TFrame')
        self.top_frame.grid(row=0, column=0, sticky="ew")
        self.partner_username_label = ttk.Label(
            self.top_frame, 
            text="Interlocuteur : Inconnu",
            font=('Helvetica', 16, 'bold')
        )
        self.partner_username_label.pack(side=tk.LEFT, padx=10)

        # Configuration de la zone de chat avec Canvas
        self.setup_chat_area()

        # Champ de saisie de message et bouton d'envoi
        self.entry_frame = ttk.Frame(self.root, padding="3 3 12 12")
        self.entry_frame.grid(row=2, column=0, sticky="ew")
        self.msg_entry = ttk.Entry(self.entry_frame, width=50)
        self.msg_entry.pack(side=tk.LEFT, padx=20, pady=10, expand=True)
        self.msg_entry.bind("<Return>", self.send_message_event)
        self.send_button = ttk.Button(self.entry_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=20, pady=20)

        # Bouton d'envoi de fichier
        self.send_file_button = ttk.Button(self.entry_frame, text="Send File", command=self.send_file)
        self.send_file_button.pack(side=tk.RIGHT, padx=5)

        # Username
        self.username = simpledialog.askstring("Nom d'utilisateur", "Entrez votre nom d'utilisateur:", parent=root)
        if not self.username:
            self.username = "Anonyme"

        self.last_received_file_name = None
        self.download_mode = False
        self.is_next_message_file = False
        self.last_received_file = None
        self.websocket = None
        self.loop = asyncio.get_event_loop()
        self.thread = threading.Thread(target=self.start_asyncio_loop, args=(), daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    

    def start_asyncio_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())
    
    def send_message_event(self, event):
        self.send_message()

    def setup_chat_area(self):
        self.chat_canvas = tk.Canvas(self.root, bg='white')
        self.chat_frame = ttk.Frame(self.chat_canvas, style='ChatFrame.TFrame')
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)

        # Utiliser grid pour positionner le scrollbar
        self.scrollbar.grid(row=1, column=1, sticky="ns")

        # Utiliser grid pour le Canvas
        self.chat_canvas.grid(row=1, column=0, sticky="nsew")
        self.chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw", tags="self.chat_frame")

        self.chat_frame.bind("<Configure>", self.on_frame_configure)
        self.root.grid_columnconfigure(0, weight=1)  # Assure que le canvas s'élargit correctement
        self.root.grid_rowconfigure(1, weight=1)


    def on_frame_configure(self, event=None):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def create_chat_bubbles(self, message, sent=False):
        # Styles personnalisés pour les bulles de chat
        bubble_background = '#dcf8c6' if sent else '#ffffff'  # Couleurs de fond
        self.style.configure('SentBubble.TFrame', background=bubble_background)
        self.style.configure('ReceivedBubble.TFrame', background=bubble_background)

        bubble_style = 'SentBubble.TFrame' if sent else 'ReceivedBubble.TFrame'
        bubble = ttk.Frame(self.chat_frame, style=bubble_style, padding=10)
        
        # Label avec la même couleur de fond que la bulle
        label = ttk.Label(bubble, text=message, background=bubble_background, wraplength=350)
        label.pack(padx=10, pady=5, fill='both', expand=True)

        # Positionner la bulle à droite ou à gauche
        if sent:
            bubble.pack(fill='x', padx=10, pady=5, anchor='e')
        else:
            bubble.pack(fill='x', padx=10, pady=5, anchor='w')


    def toggle_download_button(self, download_mode):
        if download_mode:
            self.send_file_button.config(text="Download File", command=self.download_file)
            self.download_mode = True
        else:
            self.send_file_button.config(text="Send File", command=self.send_file)
            self.download_mode = False

    def download_file(self):
        if self.last_received_file:
            file_path = filedialog.asksaveasfilename(
                title="Save file",
                initialfile=self.last_received_file_name,  # Utilisez le nom du fichier comme nom par défaut
                filetypes=[("All files", "*.*")]
            )
            if file_path:
                file_data = base64.b64decode(self.last_received_file)
                with open(file_path, 'wb') as file:
                    file.write(file_data)
                self.last_received_file = None
                self.toggle_download_button(False)  # Désactiver le download

    def on_file_bubble_click(self, message):
        if "Fichier reçu de" in message and self.last_received_file:
            file_path = filedialog.asksaveasfilename(title="Save file", filetypes=[("All files", "*.*")])
            if file_path:
                file_data = base64.b64decode(self.last_received_file)
                with open(file_path, 'wb') as file:
                    file.write(file_data)
                self.last_received_file = None


    def display_message(self, message, sent=False):
        if message.startswith("FILE:") and not sent:
            _, username, file_name, file_content = message.split(":", 3)
            self.last_received_file = file_content
            self.last_received_file_name = file_name  # Stockez le nom du fichier
            self.create_chat_bubbles(f"{username} sent a file: {file_name}. Click to download.", sent=False)
            self.toggle_download_button(True)
        else:
            if ":" in message:
                username, message_content = message.split(":", 1)
                message_content = message_content.strip()

                if not sent and username != self.username:
                    self.partner_username_label.config(text=f"Contact : {username}")
                    message_to_display = f"{username}: {message_content}"
                else:
                    message_to_display = message
            else:
                message_to_display = message

            self.create_chat_bubbles(message_to_display, sent=sent)

    def send_message(self):
        message = self.msg_entry.get()
        if message:
            full_message = f"{self.username}: {message}"
            asyncio.run_coroutine_threadsafe(self.websocket.send(full_message), self.loop)
            self.display_message(f"You: {message}", sent=True)
            self.msg_entry.delete(0, tk.END)
    
    def send_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            with open(file_path, 'rb') as file:
                file_data = file.read()
                encoded_file = base64.b64encode(file_data).decode()
                file_name = os.path.basename(file_path)
                file_message = f"FILE:{self.username}:{file_name}:{encoded_file}"
                asyncio.run_coroutine_threadsafe(self.websocket.send(file_message), self.loop)
                # Afficher une bulle de chat indiquant que le fichier a été envoyé
                self.create_chat_bubbles(f"You sent a file: {file_name}", sent=True)


    
    def on_file_bubble_click(self, event):
        if self.last_received_file:
            file_path = filedialog.asksaveasfilename(title="Save file", filetypes=[("All files", "*.*")])
            if file_path:
                file_data = base64.b64decode(self.last_received_file)
                with open(file_path, 'wb') as file:
                    file.write(file_data)
                self.last_received_file = None


    def save_received_file(self, file_content):
        file_data = base64.b64decode(file_content)
        file_path = filedialog.asksaveasfilename(title="Save file", filetypes=[("All files", "*.*")])
        if file_path:
            with open(file_path, 'wb') as file:
                file.write(file_data)

    def on_close(self):
        if self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
        self.root.destroy()

    async def connect(self):
        self.websocket = await websockets.connect("ws://localhost:6789")
        while True:
            message = await self.websocket.recv()
            self.loop.call_soon_threadsafe(self.display_message, message)

if __name__ == "__main__":
    root = ttk.Window(themename='minty')
    client = ChatClient(root)
    root.mainloop()