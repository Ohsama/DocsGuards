# DocsGuards 🏥

**DocsGuards** is an intelligent, algorithmic Medical On-Call Scheduling System designed to ensure strict fairness, accommodate different doctor pool shifts, and balance holiday assignments over time.

## 🚀 Features

- **Strict Classifications:** Separate pools for Standard (Weekday Nights) and Weekend Workers.
- **Fair Round-Robin Algorithm:** Rotates assignments strictly and evenly. No doctor is given a second assignment until every eligible and available doctor has had one.
- **Holiday Memory Engine:** Automatically looks at historical data to ensure the exact same holiday (e.g. Eid Al-Adha) is balanced perfectly across the entire pool of doctors over time.
- **Leave Window Checks:** Automatically bypasses and respects doctors on leave without destroying their place in the queue.
- **Beautiful Exporting:** Instantly exports schedules to dynamic, colour-coded Excel spreadsheets (.xlsx).
- **Elegant UI:** Fast, glass-morphic interface built to manage doctors, holidays, and history cleanly.

## 🛠️ Stack & Principles

- **Language:** Python 3.8+
- **Backend Framework:** Flask
- **Algorithmic Logic:** Custom-built continuous Round-Robin queuing over multiple time domains.
- **File Exporting:** `openpyxl`
- **Design System:** Raw HTML/CSS with Inter font, heavily optimized for readability without relying on heavy frontend frameworks.

## 🔧 Installation & Usage

1. Clone the repository.
2. Ensure you have Python installed.
3. Run the startup script:
   - On Windows: Double click `run.bat`
   - On Mac/Linux: `pip install -r requirements.txt` then `python app.py`
4. Access the portal at `http://localhost:5000`

## ⚖️ License & Copyright

**All rights reserved.**
Please refer to the `LICENSE.md` file. Permission is strictly required to use, modify, or distribute this software.
