# Task: Home Organization & Inventory Web App

Complete this task. Return your answer EXACTLY in this format:

```
CODE:
```html
<the complete single-file app>
```
```

The task:

Build a complete, working single-file web application: a "Home Organization & Inventory" manager for a household.

1. Rooms management: create, rename, delete rooms (e.g. Kitchen, Garage, Study).
2. Items: add an item with name, quantity, category (choose from a fixed list: Food, Tools, Documents, Electronics, Cleaning, Other), room, and optional notes. Edit and delete items.
3. Search: a text box that filters items live by name/notes; plus filter by room and by category.
4. Low-stock indicator: items with quantity <= 2 are highlighted.
5. Persistence: everything is saved in the browser via localStorage and survives a page reload. Include a "Load demo data" button that fills in a few example rooms and items.
6. Export/Import: buttons to download the data as JSON and to load it back from a JSON file.
7. UI: clean and usable on desktop and phone, clear headings, no horizontal scrolling, keyboard accessible forms, visible feedback when an item is saved or deleted.
8. Code quality: one HTML file with inline `<style>` and `<script>`, no frameworks, well-named variables, sensible structure, no console errors.

Constraints: must work offline in the browser, no build step, no external libraries or CDNs.

Output contract: reply with ONE single fenced code block containing the complete HTML file and nothing else — no explanation, no commentary before or after. Start the file with `<!DOCTYPE html>` and end it with `</html>`.

## How this task is scored

Nothing is scored by eye. Each reply is parsed, the HTML extracted, and then:

| Check | Method |
|---|---|
| File complete | ends with `</html>`, valid structure |
| JS parses | every inline `<script>` run through `node --check` |
| Feature markers | presence of localStorage, add/edit/delete, search, category filter, rooms, quantity, low-stock rule, export, import, demo data, responsive CSS, no external URLs |
| Actually works | app opened in a real browser: demo data loads, an item is added with real input events, search filters, and the new item survives a reload |

The harness for every check is in `harness/local/`.
