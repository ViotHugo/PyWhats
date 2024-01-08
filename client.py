import tkinter as tk
from tkinter import simpledialog, scrolledtext
import asyncio
import websockets
import threading

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Messenger")
        self.root.configure(bg="#ECE5DD")  # Couleur de fond

        # Zone de texte pour l'affichage des messages
        self.text_area = scrolledtext.ScrolledText(root, state='disabled', wrap=tk.WORD, bg="#FFFFFF", fg="#000000")
        self.text_area.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # Champ de saisie de message
        self.msg_entry = tk.Entry(root, width=50, bg="#FFFFFF", fg="#000000")
        self.msg_entry.pack(padx=20, pady=10)
        self.msg_entry.focus_set()  # Met le focus sur le champ de saisie

        # Bouton d'envoi
        self.send_button = tk.Button(root, text="Send", command=self.send_message, bg="#075E54", fg="#FFFFFF")
        self.send_button.pack(padx=20, pady=20)

        self.websocket = None
        self.loop = asyncio.get_event_loop()
        self.thread = threading.Thread(target=self.start_asyncio_loop, args=(), daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_asyncio_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())

    async def connect(self):
        self.websocket = await websockets.connect("ws://localhost:6789")
        while True:
            message = await self.websocket.recv()
            self.loop.call_soon_threadsafe(self.display_message, message)

    def display_message(self, message):
        if self.text_area:
            self.text_area.config(state=tk.NORMAL)
            self.text_area.insert(tk.END, f"\n{message}")
            self.text_area.config(state=tk.DISABLED)

    def send_message(self):
        message = self.msg_entry.get()
        if message:
            # Planifier l'envoi du message dans la boucle d'événements asyncio
            asyncio.run_coroutine_threadsafe(self.websocket.send(message), self.loop)
            self.display_message(f"You: {message}")
            self.msg_entry.delete(0, tk.END)


    def on_close(self):
        if self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    client = ChatClient(root)
    root.mainloop()
