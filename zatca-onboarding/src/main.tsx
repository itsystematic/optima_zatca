(globalThis as any).isDev = import.meta.env.DEV;
(globalThis as any).__ = (text: string) => text;
import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import './App.css';
import App from "./App.tsx";
import { store } from "./app/store.ts";
import "./index.css";


createRoot(document.getElementById("root")!).render(
    <Provider store={store}>
      <App />
    </Provider>
);
