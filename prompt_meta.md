После применения предложенного тобой промпта получен **актуальный repository snapshot (прилагаю файл):** `concat_NN.md`.

**Что я лично проверил в приложении после предыдущей итерации:**
<конкретные наблюдения: что работает, что не работает, сообщения об ошибках, особенности интерфейса>

**Новые пожелания или приоритеты:**
<если есть; иначе: нет>

Вот output в VS Code после реализации агентом ИИ предложенного тобой промпта:
```
```

---
На основе актуального repository snapshot (в файле `concat_NN.md`) и моих наблюдений выше: тщательно проанализируй и детально сообщи, какие ошибки есть в коде и как их можно исправить?

На основе актуального repository snapshot: тщательно проанализируй и детально сообщи, какие ошибки есть в коде и как их можно исправить? Выполнена ли поставленная задача/этап или нет, если нет, то какие вещи нужно доработать?
Какие тесты нужно провести и предоставить тебе ответ, чтобы лучше понять состояние кода в репозитории и наличие ошибок?


---

На основе актуального repository snapshot, текущего кода и моих наблюдений:

1. Проанализируй, что реализовано, частично реализовано, не реализовано и какие новые ошибки появились.

2. Сам сформируй временный план подзадач для текущей итерации.
   - Не используй постоянную нумерацию групп между итерациями.
   - Объединяй в одну подзадачу только тесно связанные изменения, образующие один пользовательский сценарий или один общий state/data flow.
   - Разделяй независимые изменения по разным подзадачам.
   - Учитывай текущую структуру репозитория, пересечение изменяемых файлов, зависимости между задачами и реалистичный объём работы Qwen3-Coder-Next за один проход.
   - Не включай в одну подзадачу слишком много независимых подсистем.

3. Сначала покажи мне только план временных подзадач:
   - название каждой подзадачи;
   - что в неё входит;
   - почему эти изменения объединены;
   - порядок выполнения;
   - краткий ожидаемый итог каждой подзадачи.

======================

Сформулируй CLI prompt (на основе твоего предыдущего ответа и repository snapshot в файле `concat_NN.md`) только для подзадачи <название выбранной подзадачи>.

CLI prompt для Qwen3-Coder-Next должен:
   - быть на английском языке;
   - описывать реальные изменения реального текущего репозитория;
   - не упоминать repository snapshot и не советовать читать `concat_NN.md`;
   - всегда указывать полный относительный путь при упоминании файла, например `lib/game_page.dart`, а не `game_page.dart`;
   - включать фрагменты кода только для критической логики, опасных асинхронных мест, сложной структуры данных или того, что легко реализовать неверно;
   - указывать краткий ожидаемый итог подзадачи в наблюдаемой форме;
   - требовать тест для исправления, если проблема относится к воспроизводимой логике, данным, сохранению состояния;
   - не считать задачу выполненной только по наличию строки, метода, класса, импорта, grep-вывода или успешной компиляции;
   - не скрывать ошибки через подавление вывода, `// ignore`, `// ignore_for_file` или lint suppression; если исключение действительно необходимо, агент обязан явно объяснить причину;
   - не менять несвязанные файлы, зависимости, конфигурацию чего-либо без явного объяснения необходимости;
   - требовать в финальном отчёте: изменённые файлы, реализованные требования, выполненные тесты, известные ограничения.

Включи следующие два блока в итоговый промпт:
```
============================================================
TOOL-CALL DISCIPLINE
============================================================

- Use the editor's native structured tool interface; do not print pseudo-tool calls,
  XML tool calls, Markdown JSON blocks, or narration instead of invoking a tool.
- For each edit, make one small atomic replacement in one full-path file.
- Before editing, read the exact target fragment from the file.
- The edit must send all required fields in the tool schema:
  filePath, oldString, newString.
- Use camelCase schema names exactly; do not use file_path, old_string, or new_string.
- If a tool validation error occurs, retry once with the exact required schema.
  Do not repeat narration or issue another empty tool call.
- Prefer several small edits over one large write containing a whole long source file.

============================================================
RECOVERY FROM INVALID-TOOL ERRORS
============================================================

- If the system returns an error such as
  `Model tried to call unavailable tool 'invalid'`,
  treat it as a temporary internal Kilo Code client error.
- Do not conclude that the intended tool is unavailable.
- Do not change the planned workflow solely because of this error.
- Never attempt to invoke a tool named `invalid`.
- Immediately retry the same intended native structured tool call with the same valid
  tool name and the same arguments.
- Do not replace the retry with pseudo-tool calls, XML, Markdown JSON blocks,
  narration, or an explanation of the failed call.
- If the same call fails again, inspect the tool schema and retry once only with
  corrected valid arguments; then report the unresolved error clearly.
```
