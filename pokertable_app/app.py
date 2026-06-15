"""Our own desktop poker table (Tkinter) for Hold'em (2 cartas) and
Five Card Draw (5 cartas).

Runs on Windows with stock Python (Tkinter ships with the installer). It deals a
hand against the simulator's agents, shows the cards, and -- the point of the
study -- lets you run the OCR pipeline ON THIS APP'S OWN TABLE:

  * "OCR (render interno)"  reads the cards straight from our renderer
    (works anywhere, exact ground truth).
  * "OCR (print da janela)" takes a real screenshot of THIS window and runs
    pytesseract over it (needs mss/pillow/pytesseract + the tesseract binary;
    Windows desktop only).

It only ever captures and reads ITS OWN window -- never a third-party client.
"""
from __future__ import annotations

import random

from poker_sim.agents import LooseHumanAgent, ProAgent, TightHumanAgent
from poker_sim.cashgame import CashGame

from .ocr import recognize_grid, recognize_with_tesseract
from .render import render_cards


class PokerTableApp:
    def __init__(self, root):
        import tkinter as tk

        self.tk = tk
        self.root = root
        root.title("Mesa de Poker (estudo de OCR) - alvo próprio")
        self.game = tk.StringVar(value="holdem")
        self.visible_cards = []  # ground truth of what's drawn on the table

        top = tk.Frame(root, padx=8, pady=8)
        top.pack(fill="x")
        tk.Label(top, text="Variante:").pack(side="left")
        tk.OptionMenu(top, self.game, "holdem", "draw").pack(side="left")
        tk.Button(top, text="Nova mão", command=self.new_hand).pack(side="left", padx=4)
        tk.Button(top, text="OCR (render interno)",
                  command=self.ocr_internal).pack(side="left", padx=4)
        tk.Button(top, text="OCR (print da janela)",
                  command=self.ocr_screenshot).pack(side="left", padx=4)

        self.canvas = tk.Canvas(root, width=720, height=240, bg="#0a5c36")
        self.canvas.pack(padx=8, pady=8)
        self.status = tk.Label(root, text="Clique em 'Nova mão'.", anchor="w",
                               justify="left", font=("Courier", 10))
        self.status.pack(fill="x", padx=8, pady=(0, 8))

        self.rng = random.Random()
        self.new_hand()

    # --- gameplay -------------------------------------------------------
    def new_hand(self):
        game = self.game.get()
        agents = [ProAgent("Pro"), TightHumanAgent("Tight"), LooseHumanAgent("Loose")]
        cg = CashGame(agents, buyin_bb=100, game=game, rng=self.rng)
        events = []
        cg.play(1, behavior_log=events)
        # reconstruct the visible cards from a fresh deal for display
        from poker_sim.cards import Deck
        deck = Deck(self.rng)
        if game == "holdem":
            self.visible_cards = deck.deal(2) + deck.deal(5)
            layout = "2 hole + 5 board"
        else:
            self.visible_cards = deck.deal(5)
            layout = "5-card hand"
        self._draw_table()
        self.status.config(text=f"Variante: {game} ({layout}). "
                                f"Ações simuladas: {len(events)} decisões.")

    def _draw_table(self):
        c = self.canvas
        c.delete("all")
        x = 30
        for card in self.visible_cards:
            self._draw_card(c, x, 80, repr(card))
            x += 90
        c.create_text(360, 30, text="Mesa nossa (alvo de OCR controlado)",
                      fill="white", font=("Helvetica", 12, "bold"))

    def _draw_card(self, c, x, y, label):
        red = label[1] in ("d", "h")
        c.create_rectangle(x, y, x + 70, y + 100, fill="white", outline="black")
        c.create_text(x + 35, y + 50, text=label,
                      fill=("#c00" if red else "black"), font=("Courier", 22, "bold"))

    # --- OCR demos ------------------------------------------------------
    def ocr_internal(self):
        grid, origins = render_cards(self.visible_cards)
        read = recognize_grid(grid, origins)
        truth = [repr(c) for c in self.visible_cards]
        ok = sum(t == r for t, r in zip(truth, read))
        self.status.config(
            text=f"OCR (render interno): {ok}/{len(truth)} cartas corretas\n"
                 f"  verdade : {' '.join(truth)}\n"
                 f"  lido    : {' '.join(read)}")

    def ocr_screenshot(self):
        try:
            import mss  # type: ignore
            from PIL import Image  # type: ignore
        except Exception:
            self.status.config(text="OCR (print): instale 'mss', 'pillow' e "
                                    "'pytesseract' (+ binário tesseract) no Windows.")
            return
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + self.canvas.winfo_x()
        y = self.root.winfo_rooty() + self.canvas.winfo_y()
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        with mss.mss() as sct:
            raw = sct.grab({"left": x, "top": y, "width": w, "height": h})
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        text = recognize_with_tesseract(img)
        if text is None:
            self.status.config(text="OCR (print): pytesseract/tesseract ausente.")
        else:
            self.status.config(text=f"OCR (print da janela) -> texto lido:\n{text.strip()}")


def main():
    import tkinter as tk
    root = tk.Tk()
    PokerTableApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
