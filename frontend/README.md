# Frontend – Stock Sentiment Dashboard (React + Vite)

This is the frontend for my stock sentiment / price prediction project.

The goal is to build a simple dashboard where I can:

- Enter one or more tickers and a date range
- Trigger model training from the UI
- See training metrics (rows, features, ROC-AUC)
- Call `/predict-next` and display the probability that the next day’s close will be up

The app is built with React, TypeScript, Vite, Tailwind CSS, and shadcn-ui.

---

## Tech stack

- **React**
- **TypeScript**
- **Vite**
- **Tailwind CSS**
- **shadcn-ui** (component library)

---

## Project structure (frontend)

Approximate layout:

```text
frontend/
  src/
    components/
      # shared UI components (buttons, cards, forms, etc.)
    pages/
      # main screens / routes
    hooks/
    lib/
    App.tsx
    main.tsx
  index.html
  vite.config.ts
  tailwind.config.cjs
  postcss.config.cjs
  package.json
```

This might change as I refactor and add more features, but the overall idea stays the same.

---

## Getting started

Make sure you have **Node.js** and **npm** installed  
(I usually use `nvm` to manage Node versions).

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Run the dev server

```bash
npm run dev
```

Vite will print a local dev URL, usually:

```text
http://localhost:5173
```

Open that in your browser.

---

## Available scripts

From the `frontend` directory:

```bash
# Start development server with hot reload
npm run dev

# Create a production build
npm run build

# Preview the production build locally
npm run preview

# (if/when tests are added)
npm test
```

---

## Tailwind & shadcn-ui

Styling is based on **Tailwind CSS**.  
Most layout and spacing is done using utility classes.

For common UI building blocks, I’m using **shadcn-ui** components (buttons, cards, inputs, dialogs, etc.) so:

- The design stays consistent
- Components are accessible and easy to customize

If you want to customize the theme:

- Update `tailwind.config.*` for colors, fonts, etc.
- Adjust shadcn-ui component styles in `src/components`

---

## Connecting to the backend

The frontend is meant to talk to the FastAPI backend described in the backend README.

Typical local setup:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

I usually set an API base URL via an env variable:

```env
# .env (in the frontend folder)
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Then in the code:

```ts
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function trainModel(payload: unknown) {
  const resp = await fetch(`${API_BASE_URL}/model/train`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    // handle errors gracefully in the UI
    throw new Error(`Training failed with status ${resp.status}`);
  }

  return resp.json();
}
```

---

## Notes

- The first focus is on getting the basic flow working: choose tickers → train → display metrics → run `/predict-next`.
- Once the pipeline is solid, I plan to add:
  - Better loading and error states
  - Historical charts for prices and model predictions
  - Maybe some comparison views across tickers
