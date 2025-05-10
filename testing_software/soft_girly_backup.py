# Простой одностраничный интерфейс на HTML + JS для запуска в Python-среде (например, с Flask)
# Сохрани этот файл как app.py и запусти его командой: python app.py

from flask import Flask, render_template_string

app = Flask(__name__)

html_code = '''
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Тестовое SPA</title>
  <style>
    body {
      font-family: "Comic Sans MS", cursive, sans-serif;
      background-color: #fff0f6;
      padding: 2rem;
      max-width: 800px;
      margin: auto;
      color: #880e4f;
    }
    h1 {
      text-align: center;
      color: #ad1457;
    }
    .card {
      background-color: #ffe4ec;
      border: 2px solid #f8bbd0;
      border-radius: 15px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 8px rgba(255, 105, 180, 0.2);
    }
    button {
      background-color: #f06292;
      color: white;
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      margin-top: 0.5rem;
      transition: background-color 0.3s;
    }
    button:hover {
      background-color: #ec407a;
    }
    input, select {
      padding: 0.5rem;
      border-radius: 10px;
      border: 1px solid #f48fb1;
      width: calc(100% - 1rem);
      margin-top: 0.25rem;
      background-color: #fff0f6;
    }
    label {
      display: block;
      margin-top: 0.75rem;
      font-weight: bold;
    }
    .hover-box {
      position: relative;
      display: inline-block;
      cursor: pointer;
      color: #c2185b;
      text-decoration: underline;
    }
    .hover-box .tooltip {
      display: none;
      position: absolute;
      background: #880e4f;
      color: white;
      padding: 0.5rem;
      border-radius: 10px;
      top: 1.5rem;
      left: 0;
      white-space: nowrap;
    }
    .hover-box:hover .tooltip {
      display: block;
    }
    .input-group {
      display: flex;
      gap: 0.5rem;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .error {
      margin-top: 0.5rem;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <h1>Добро пожаловать в девичье SPA-приложение 💖</h1>

  <div class="card">
    <button onclick="document.getElementById('output').innerText='Вы нажали на кнопку!'">
      Нажми меня
    </button>
    <p id="output" style="color: #d81b60; font-weight: bold;"></p>
  </div>

  <div class="card">
    <label for="textInput">Поле для признаний 🌸:</label>
    <div class="input-group">
      <input type="text" id="textInput" placeholder="Введите что-нибудь прекрасное..." />
      <button type="button" onclick="displayInput()">Показать</button>
    </div>
    <p id="error" class="error"></p>
  </div>

  <div class="card">
    <div class="hover-box">
      Наведи на меня 🌷
      <div class="tooltip">Ты чудо, что наводишь мышку 🦋</div>
    </div>
  </div>

  <div class="card">
    <label><input type="checkbox" id="checkbox" onchange="showCheckboxState()" /> Мне нравится это приложение 💕</label>
    <p id="checkboxState"></p>

    <label for="colorSelect">Выбери любимый цвет:</label>
    <select id="colorSelect" onchange="showSelectedColor()">
      <option value="">-- выбери --</option>
      <option value="pink">Розовый</option>
      <option value="purple">Фиолетовый</option>
      <option value="sky">Небесный</option>
    </select>
    <p id="colorChoice"></p>
  </div>

  <script>
    function displayInput() {
      const input = document.getElementById('textInput').value.trim();
      const error = document.getElementById('error');
      if (input === '') {
        error.textContent = 'Не оставляй пустым, красотка 💌';
        error.style.color = '#e91e63';
      } else {
        error.textContent = 'Ты написала: ' + input;
        error.style.color = '#4caf50';
      }
    }

    function showCheckboxState() {
      const checkbox = document.getElementById('checkbox');
      const stateText = document.getElementById('checkboxState');
      if (checkbox.checked) {
        stateText.textContent = 'Рада, что тебе нравится! 💕';
      } else {
        stateText.textContent = 'Может, я постараюсь лучше? 😢';
      }
    }

    function showSelectedColor() {
      const color = document.getElementById('colorSelect').value;
      const colorText = document.getElementById('colorChoice');
      if (color) {
        colorText.textContent = 'Ты выбрала: ' + color + ' 💗';
      } else {
        colorText.textContent = '';
      }
    }
  </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(html_code)

if __name__ == '__main__':
    app.run(debug=True)