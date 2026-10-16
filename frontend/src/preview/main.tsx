import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "../styles/tokens.css";
import "../styles/base.css";
import "../styles/layout.css";
import "../styles/legacy.css";
import "../styles/screens.css";
import "../styles/preview.css";
import { Gallery } from "./Gallery";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Gallery />
  </StrictMode>,
);
