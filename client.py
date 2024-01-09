import tkinter as tk
from tkinter import ttk, simpledialog 
from ttkthemes import ThemedTk
import asyncio
import websockets
import threading

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("PyWhats")
        
        # Utilisation d'un thème vert
        self.style = ttk.Style(self.root)
        self.style.configure('TButton', background='#25D366', font=('Helvetica', 12), borderwidth='4')
        self.style.configure('TEntry', font=('Helvetica', 12), padding=10)
        self.style.configure('TLabel', font=('Helvetica', 14, 'bold'), background='#25D366')

        # Configuration du grid pour le root
        root.grid_rowconfigure(1, weight=1)  # Donne plus de poids à la rangée du Canvas
        root.grid_columnconfigure(0, weight=1)

        # Barre de menu supérieure
        self.top_frame = ttk.Frame(self.root, padding="3 3 12 12", relief=tk.RIDGE, style='TFrame')
        self.top_frame.grid(row=0, column=0, sticky="ew")
        self.partner_username_label = ttk.Label(self.top_frame, text="Interlocuteur: Inconnu", style='TLabel')
        self.partner_username_label.pack(side=tk.LEFT, padx=10)

        # Configuration de la zone de chat avec Canvas
        self.setup_chat_area()

        # Champ de saisie de message et bouton d'envoi
        self.entry_frame = ttk.Frame(self.root, padding="3 3 12 12", relief=tk.RIDGE)
        self.entry_frame.grid(row=2, column=0, sticky="ew")
        self.msg_entry = ttk.Entry(self.entry_frame, width=50, style='TEntry')
        self.msg_entry.pack(side=tk.LEFT, padx=20, pady=10, expand=True)
        self.msg_entry.bind("<Return>", self.send_message_event)
        self.send_button = ttk.Button(self.entry_frame, text="Send", command=self.send_message, style='TButton')
        self.send_button.pack(side=tk.RIGHT, padx=20, pady=20)

        # Username
        self.username = simpledialog.askstring("Nom d'utilisateur", "Entrez votre nom d'utilisateur:", parent=root)
        if not self.username:
            self.username = "Anonyme"

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
        self.chat_frame = ttk.Frame(self.chat_canvas)
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
        bubble = ttk.Frame(self.chat_frame, style='Bubble.TFrame')
        label = ttk.Label(bubble, text=message, style='Bubble.TLabel')
        label.pack(padx=10, pady=5)
        bubble.pack(fill='x', padx=10, pady=5, anchor='e' if sent else 'w')

        self.style.configure('Bubble.TFrame', background='#e2ffc7' if sent else '#ffffff')
        self.style.configure('Bubble.TLabel', background='#e2ffc7' if sent else '#ffffff')

    def display_message(self, message, sent=False):
        if ":" in message:
            username, message_content = message.split(":", 1)
            message_content = message_content.strip()

            if not sent and username != self.username:
                self.partner_username_label.config(text=f"Interlocuteur: {username}")
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
    root = ThemedTk()
    client = ChatClient(root)
    root.mainloop()
