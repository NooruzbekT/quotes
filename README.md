# 📚 Quotes App

A Django web application that displays random quotes from movies or books with rating and popularity features.

## Requirements

- Python 3.13
- Django 5.2
- SQLite3 
- IDE: PyCharm or VS Code

## Features

- **Home page**
  - Shows a **random quote** from the database.
  - Quote selection depends on its **weight** (higher weight → higher probability).
  - Each view is counted.
  - Users can give a **like** or **dislike**.

- **Quote management**
  - Add new quotes via a form.
  - **No duplicates** allowed.
  - Maximum of **3 quotes per source** (movie, book, etc.).
  - Weight value set when creating a quote.

- **Popular quotes**
  - Separate page with **Top-10 quotes** sorted by likes.
  - Can be extended with filters, dashboards, or analytics.

---

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/NooruzbekT/quotes.git
    cd project
    ```

2. Create a virtual environment and activate it:
    ```sh
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Contact

For any inquiries or issues, please contact `nookentoktobaev@gmail.com`.
