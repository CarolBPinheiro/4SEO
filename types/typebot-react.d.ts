declare module "@typebot.io/react" {
  import type { ComponentType, CSSProperties } from "react";

  export type TypebotBubbleTheme = {
    button?: {
      backgroundColor?: string;
      iconColor?: string;
      size?: "medium" | "large" | `${number}px`;
      isHidden?: boolean;
      customIconSrc?: string;
      customCloseIconSrc?: string;
    };
    previewMessage?: {
      backgroundColor?: string;
      textColor?: string;
      closeButtonBackgroundColor?: string;
      closeButtonIconColor?: string;
    };
    chatWindow?: {
      backgroundColor?: string;
      maxWidth?: string;
      maxHeight?: string;
    };
    placement?: "left" | "right";
    position?: "fixed" | "static";
  };

  export type TypebotBubbleProps = {
    typebot: string;
    apiHost?: string;
    previewMessage?: {
      message: string;
      autoShowDelay?: number;
      avatarUrl?: string;
    };
    theme?: TypebotBubbleTheme;
    prefilledVariables?: Record<string, string | number | boolean>;
    autoShowDelay?: number;
    isOpen?: boolean;
    onInit?: () => void;
    onOpen?: () => void;
    onClose?: () => void;
  };

  export type TypebotStandardProps = TypebotBubbleProps & {
    style?: CSSProperties;
    className?: string;
  };

  export const Bubble: ComponentType<TypebotBubbleProps>;
  export const Popup: ComponentType<TypebotBubbleProps>;
  export const Standard: ComponentType<TypebotStandardProps>;
}
