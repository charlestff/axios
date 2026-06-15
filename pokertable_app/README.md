# Mesa de Poker própria + estudo de OCR

Um aplicativo de mesa de poker **nosso** (Hold'em = 2 cartas, Five Card Draw =
5 cartas) e um **estudo de OCR que roda em cima dessa mesa**. O alvo do OCR é
**a janela do nosso próprio aplicativo** — uma superfície que controlamos e cuja
verdade conhecemos. **Não captura, lê ou mira PokerStars / GGPoker / PPoker** nem
qualquer cliente de terceiros. O objetivo é estudar o pipeline
*captura de tela → OCR → verificação* e sua confiabilidade sob ruído, contra um
alvo controlado.

## Componentes

| Arquivo | Papel |
|---------|-------|
| `glyphs.py` | Fonte bitmap 5x7 própria (ranks `2-9 T J Q K A`, naipes `c d h s`) |
| `render.py` | Renderiza as cartas da mesa para uma imagem (grade de pixels) + ruído |
| `ocr.py` | OCR por template-matching da nossa fonte; backend opcional pytesseract |
| `study.py` | Estudo de acurácia do OCR vs. ruído (roda em qualquer lugar) |
| `app.py` | App desktop Tkinter (Windows) com demos de OCR sobre a própria mesa |
| `tests/` | Round-trip do OCR (100% sem ruído; degrada com ruído) |

## Rodar no Windows

Python 3.10+ (o Tkinter já vem no instalador oficial do Windows).

```bat
:: estudo de OCR (sem dependências externas) — funciona em qualquer máquina
python -m pokertable_app.study --game holdem --deals 1500
python -m pokertable_app.study --game draw   --deals 1500

:: o aplicativo de mesa (janela)
python -m pokertable_app.app

:: testes
python -m pytest pokertable_app -q
```

No app:
- **"Nova mão"** distribui uma mão (2 ou 5 cartas) na nossa mesa.
- **"OCR (render interno)"** lê as cartas direto do nosso renderizador — funciona
  em qualquer lugar e compara com a verdade conhecida.
- **"OCR (print da janela)"** tira um *screenshot real desta janela* e passa pelo
  `pytesseract`. Requer, só no Windows desktop:

  ```bat
  pip install mss pillow pytesseract
  ```
  e o binário do Tesseract instalado (UB Mannheim build). Esse botão captura
  **apenas a própria janela do app**.

## Resultado do estudo (exemplo, 1500 deals)

Acurácia do OCR (acerto por carta) conforme o ruído de captura aumenta:

| ruído | Hold'em (2 cartas) | Draw (5 cartas) |
|------:|-------------------:|----------------:|
| 0.00 | 1.000 | 1.000 |
| 0.05 | 0.996 | 0.996 |
| 0.10 | 0.980 | 0.982 |
| 0.15 | 0.932 | 0.928 |
| 0.20 | 0.818 | 0.825 |

Leitura para o trabalho: com um alvo limpo e fonte conhecida o OCR é
praticamente perfeito; a confiabilidade cai de forma previsível com ruído de
captura — o que, do lado **defensivo**, sugere que degradar/variar a renderização
(ou exigir leitura sob ruído) é um vetor contra automação baseada em OCR.

## Escopo / limites

Este projeto é um **alvo de estudo próprio**. Ele não inclui — e não deve ser
estendido para incluir — leitura de tela ou automação de qualquer aplicativo de
poker de terceiros. Toda a captura/OCR aqui é sobre a janela deste mesmo app.
