# Научное одностраничное приложение для тестирования UI в Flask
# Сохрани этот файл как app.py и запусти его командой: python app.py

from flask import Flask, render_template_string

app = Flask(__name__)

html_code = '''
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Научное SPA-приложение</title>
  <style>
    body {
      font-family: "Segoe UI", sans-serif;
      background-color: #f4f6f8;
      padding: 2rem;
      max-width: 900px;
      margin: auto;
      color: #2c3e50;
    }
    h1 {
      text-align: center;
      color: #34495e;
    }
    .card {
      background-color: #ffffff;
      border: 1px solid #dcdfe3;
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    }
    button {
      background-color: #3498db;
      color: white;
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 0.3s;
    }
    button:hover {
      background-color: #2980b9;
    }
    input, select {
      padding: 0.5rem;
      border-radius: 6px;
      border: 1px solid #ccd1d9;
      width: calc(100% - 1rem);
      margin-top: 0.25rem;
      background-color: #fbfcfd;
    }
    label {
      display: block;
      margin-top: 0.75rem;
      font-weight: 600;
    }
    .hover-box {
      position: relative;
      display: inline-block;
      cursor: pointer;
      color: #2980b9;
      text-decoration: underline;
    }
    .hover-box .tooltip {
      display: none;
      position: absolute;
      background: #2c3e50;
      color: white;
      padding: 0.5rem;
      border-radius: 6px;
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
    .message {
      margin-top: 0.5rem;
      font-weight: 500;
    }
  </style>
</head>
<body>
  <h1>Научный интерфейс для UI-тестирования</h1>

  <div class="card" id="card-test-button">
    <button id="button-trigger-event" onclick="document.getElementById('output-event-result').innerText='Кнопка нажата: событие зарегистрировано.'">
      Тестовая кнопка
    </button>
    <p id="output-event-result" class="message" style="color: #27ae60;"></p>
  </div>

  <div class="card" id="card-input-field">
    <label for="input-text-data">Поле ввода данных:</label>
    <div class="input-group">
      <input type="text" id="input-text-data" placeholder="Введите текст..." />
      <button id="button-show-input" type="button" onclick="displayInput()">Показать</button>
    </div>
    <p id="output-input-text" class="message"></p>
  </div>

  <div class="card" id="card-hover-info">
    <div class="hover-box" id="hover-element-info">
      Наведи курсор для подсказки
      <div class="tooltip" id="hover-tooltip-text">Элемент hover успешно работает</div>
    </div>
  </div>

  <div class="card" id="card-checkbox-and-select">
    <label><input type="checkbox" id="checkbox-consent" onchange="showCheckboxState()" /> Подтверждаю участие в тестировании</label>
    <p id="output-checkbox-state" class="message"></p>

    <label for="select-environment-param">Выберите параметр среды:</label>
    <select id="select-environment-param" onchange="showSelectedColor()">
      <option value="">-- выберите --</option>
      <option value="Температура">Температура</option>
      <option value="Давление">Давление</option>
      <option value="Влажность">Влажность</option>
    </select>
    <p id="output-selected-param" class="message"></p>
  </div>

  <script>
    function displayInput() {
      const input = document.getElementById('input-text-data').value.trim();
      const output = document.getElementById('output-input-text');
      if (input === '') {
        output.textContent = 'Поле ввода не должно быть пустым';
        output.style.color = '#c0392b';
      } else {
        output.textContent = 'Введённое значение: ' + input;
        output.style.color = '#2ecc71';
      }
    }

    function showCheckboxState() {
      const checkbox = document.getElementById('checkbox-consent');
      const stateText = document.getElementById('output-checkbox-state');
      if (checkbox.checked) {
        stateText.textContent = 'Согласие подтверждено.';
        stateText.style.color = '#2c3e50';
      } else {
        stateText.textContent = 'Согласие не получено.';
        stateText.style.color = '#e67e22';
      }
    }

    function showSelectedColor() {
      const select = document.getElementById('select-environment-param');
      const output = document.getElementById('output-selected-param');
      if (select.value) {
        output.textContent = 'Выбран параметр: ' + select.value;
        output.style.color = '#2980b9';
      } else {
        output.textContent = '';
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
