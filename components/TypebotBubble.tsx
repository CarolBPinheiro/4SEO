"use client";

import { Bubble } from "@typebot.io/react";
import { useEffect } from "react";

const TYPEBOT_ID =
  process.env.NEXT_PUBLIC_TYPEBOT_ID?.trim() || "ajuda-4-seo";
const TYPEBOT_API_HOST =
  process.env.NEXT_PUBLIC_TYPEBOT_API_HOST?.trim() ||
  "https://chat.deangelitech.com.br";

const STYLE_ID = "fourseo-typebot-theme";

/**
 * Painel dark glass + bolhas no estilo Aceternity
 * (rounded-xl, neutral-800, text-sm, avatar size-8).
 */
const TYPEBOT_THEME_CSS = `
:host {
  --bot-bg-color: rgba(5, 5, 6, 0.72) !important;
}

[part="bot"] {
  background: rgba(5, 5, 6, 0.72) !important;
  background-color: rgba(5, 5, 6, 0.72) !important;
  backdrop-filter: blur(28px) saturate(1.4) !important;
  -webkit-backdrop-filter: blur(28px) saturate(1.4) !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 12px 40px rgba(0, 0, 0, 0.55) !important;
  isolation: isolate !important;
}

.typebot-container,
.typebot-chat-view,
[class*="typebot-chat"],
.flex.flex-col.h-full {
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
}

.typebot-container {
  --typebot-container-bg-color: transparent !important;
  --typebot-container-bg-image: none !important;
  --typebot-chat-container-bg-rgb: 5, 5, 6 !important;
  --typebot-chat-container-opacity: 0 !important;
  --typebot-chat-container-blur: 0 !important;
  --typebot-chat-container-color: #e5e5e5 !important;
  /* neutral-800 / neutral-200 — estilo do exemplo */
  --typebot-host-bubble-bg-rgb: 38, 38, 38 !important;
  --typebot-host-bubble-color: #e5e5e5 !important;
  --typebot-host-bubble-opacity: 1 !important;
  --typebot-host-bubble-border-rgb: 0, 0, 0 !important;
  --typebot-host-bubble-border-opacity: 0.05 !important;
  --typebot-host-bubble-border-width: 1px !important;
  --typebot-host-bubble-border-radius: 12px !important;
  --typebot-host-bubble-box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
  --typebot-guest-bubble-bg-rgb: 38, 38, 38 !important;
  --typebot-guest-bubble-color: #e5e5e5 !important;
  --typebot-guest-bubble-opacity: 1 !important;
  --typebot-guest-bubble-border-rgb: 0, 0, 0 !important;
  --typebot-guest-bubble-border-opacity: 0.05 !important;
  --typebot-guest-bubble-border-width: 1px !important;
  --typebot-guest-bubble-border-radius: 12px !important;
  --typebot-guest-bubble-box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
  --typebot-button-bg-rgb: 255, 117, 26 !important;
  --typebot-button-color: #ffffff !important;
  --typebot-button-opacity: 1 !important;
  --typebot-button-border-radius: 12px !important;
  --typebot-input-bg-rgb: 38, 38, 38 !important;
  --typebot-input-color: #e5e5e5 !important;
  --typebot-input-placeholder-color: #a3a3a3 !important;
  --typebot-input-border-rgb: 0, 0, 0 !important;
  --typebot-input-border-opacity: 0.05 !important;
  --typebot-input-border-radius: 12px !important;
  --typebot-input-opacity: 1 !important;
  color: #e5e5e5 !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  font-size: 0.875rem !important;
}

.typebot-chat-chunk {
  gap: 0.75rem !important;
}

.typebot-host-bubble,
.typebot-guest-bubble {
  max-width: min(100%, 20rem) !important;
}

.typebot-host-bubble > .bubble-typing,
.typebot-guest-bubble {
  border-radius: 12px !important;
  padding: 0.5rem 0.75rem !important;
  font-size: 0.875rem !important;
  line-height: 1.375 !important;
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.05),
    0 0 0 1px rgba(255, 255, 255, 0.06) !important;
}

.typebot-host-bubble,
.typebot-host-bubble .slate-html-container,
.typebot-host-bubble p,
.typebot-host-bubble span,
.typebot-guest-bubble,
.typebot-guest-bubble .slate-html-container,
.typebot-guest-bubble p,
.typebot-guest-bubble span {
  color: #e5e5e5 !important;
  font-size: 0.875rem !important;
  line-height: 1.375 !important;
}

.typebot-button {
  border-radius: 12px !important;
  border: none !important;
  font-weight: 500 !important;
  font-size: 0.875rem !important;
  line-height: 1.25 !important;
  padding: 0.5rem 0.75rem !important;
  min-height: 36px !important;
  width: auto !important;
  max-width: 100% !important;
  align-self: flex-start !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
  transition: background-color 0.15s ease, transform 0.15s ease !important;
}

.typebot-button:hover {
  background-color: #ff8a3d !important;
}

.typebot-input {
  border-radius: 12px !important;
  font-size: 0.875rem !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

/* Avatar size-8 (32px) — como no exemplo */
.typebot-avatar-container,
.typebot-avatar-container.w-6 {
  width: 32px !important;
  min-width: 32px !important;
  max-width: 32px !important;
  height: 32px !important;
  min-height: 32px !important;
}

.typebot-avatar-container > div {
  width: 32px !important;
  height: 32px !important;
  min-width: 32px !important;
  min-height: 32px !important;
  top: auto !important;
}

.typebot-avatar-container img,
.typebot-avatar-container figure,
.typebot-avatar-container [class*="rounded"] {
  width: 32px !important;
  height: 32px !important;
  min-width: 32px !important;
  min-height: 32px !important;
  border-radius: 9999px !important;
  object-fit: cover !important;
  border: none !important;
  box-shadow: none !important;
}

/* Preview flutuante: só o texto, sem card/avatar/fechar */
[part="preview-message"] {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  padding: 0 !important;
  color: #ffffff !important;
  font-size: 0.9375rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.01em !important;
  white-space: nowrap !important;
}

[part="preview-message"] img,
[part="preview-message"] .typebot-avatar-container,
[part="preview-message"] [class*="avatar"],
[part="preview-message"] button {
  display: none !important;
}
`;

const BUBBLE_THEME = {
  button: {
    backgroundColor: "#ff751a",
    iconColor: "#ffffff",
    size: "large" as const,
  },
  previewMessage: {
    backgroundColor: "transparent",
    textColor: "#ffffff",
    closeButtonBackgroundColor: "transparent",
    closeButtonIconColor: "transparent",
  },
  chatWindow: {
    backgroundColor: "rgba(5, 5, 6, 0.72)",
  },
  placement: "right" as const,
};

function injectThemeStyles(root: ShadowRoot | Document | Element) {
  if (!("querySelector" in root)) return;

  const existing = root.querySelector(`#${STYLE_ID}`);
  if (existing instanceof HTMLStyleElement) {
    if (existing.textContent !== TYPEBOT_THEME_CSS) {
      existing.textContent = TYPEBOT_THEME_CSS;
    }
  } else {
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = TYPEBOT_THEME_CSS;
    root.appendChild(style);
  }

  applyGlassInline(root);
}

function applyGlassInline(root: ShadowRoot | Document | Element) {
  if (!("querySelector" in root)) return;

  const botPanel = root.querySelector<HTMLElement>('[part="bot"]');
  if (botPanel) {
    botPanel.style.setProperty("background", "rgba(5, 5, 6, 0.72)", "important");
    botPanel.style.setProperty("background-color", "rgba(5, 5, 6, 0.72)", "important");
    botPanel.style.setProperty("backdrop-filter", "blur(28px) saturate(1.4)", "important");
    botPanel.style.setProperty(
      "-webkit-backdrop-filter",
      "blur(28px) saturate(1.4)",
      "important",
    );
    botPanel.style.setProperty("border", "1px solid rgba(255, 255, 255, 0.12)", "important");
    botPanel.style.setProperty(
      "box-shadow",
      "inset 0 1px 0 rgba(255,255,255,0.06), 0 12px 40px rgba(0,0,0,0.55)",
      "important",
    );
    botPanel.style.setProperty("--bot-bg-color", "rgba(5, 5, 6, 0.72)", "important");
  }

  root.querySelectorAll<HTMLElement>(".typebot-container, .typebot-chat-view").forEach((el) => {
    el.style.setProperty("background", "transparent", "important");
    el.style.setProperty("background-color", "transparent", "important");
    el.style.setProperty("background-image", "none", "important");
  });
}

function applyThemeToTypebotHosts() {
  const hosts = document.querySelectorAll("typebot-bubble, typebot-standard, typebot-popup");

  hosts.forEach((host) => {
    if (host instanceof HTMLElement) {
      host.style.setProperty("--bot-bg-color", "rgba(5, 5, 6, 0.72)");
    }

    const shadow = host.shadowRoot;
    if (!shadow) return;

    injectThemeStyles(shadow);

    shadow.querySelectorAll("*").forEach((node) => {
      if (node instanceof Element && node.shadowRoot) {
        injectThemeStyles(node.shadowRoot);
      }
    });
  });
}

export function TypebotBubble() {
  useEffect(() => {
    applyThemeToTypebotHosts();

    const observer = new MutationObserver(() => {
      applyThemeToTypebotHosts();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    const intervalId = window.setInterval(applyThemeToTypebotHosts, 400);
    const timeoutId = window.setTimeout(() => {
      window.clearInterval(intervalId);
    }, 20_000);

    return () => {
      observer.disconnect();
      window.clearInterval(intervalId);
      window.clearTimeout(timeoutId);
    };
  }, []);

  return (
    <Bubble
      typebot={TYPEBOT_ID}
      apiHost={TYPEBOT_API_HOST}
      previewMessage={{
        message: "Precisa de ajuda?",
        autoShowDelay: 10_000,
      }}
      theme={BUBBLE_THEME}
      onInit={applyThemeToTypebotHosts}
      onOpen={applyThemeToTypebotHosts}
    />
  );
}
