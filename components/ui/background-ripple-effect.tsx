"use client";

import type React from "react";
import { useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export type BackgroundRippleTone = "neutral" | "brand";

const TONE_VARS: Record<BackgroundRippleTone, string> = {
  neutral:
    "[--cell-border-color:rgba(255,255,255,0.14)] [--cell-fill-color:rgba(255,255,255,0.03)] [--cell-shadow-color:rgba(255,255,255,0.08)] [--cell-border-hover:rgba(255,255,255,0.35)] [--cell-fill-hover:rgba(255,255,255,0.06)]",
  brand:
    "[--cell-border-color:rgba(255,255,255,0.1)] [--cell-fill-color:transparent] [--cell-shadow-color:rgba(255,117,26,0.22)] [--cell-border-hover:rgba(255,117,26,0.55)] [--cell-fill-hover:rgba(255,117,26,0.08)]",
};

export function BackgroundRippleEffect({
  rows = 8,
  cols = 27,
  cellSize = 56,
  tone = "neutral",
  className,
  gridClassName,
}: {
  rows?: number;
  cols?: number;
  cellSize?: number;
  tone?: BackgroundRippleTone;
  className?: string;
  gridClassName?: string;
}) {
  const [clickedCell, setClickedCell] = useState<{
    row: number;
    col: number;
  } | null>(null);
  const [rippleKey, setRippleKey] = useState(0);
  const ref = useRef<HTMLDivElement | null>(null);

  return (
    <div
      ref={ref}
      className={cn(
        "pointer-events-none absolute inset-0 h-full w-full",
        TONE_VARS[tone],
        className,
      )}
    >
      <div className="relative h-auto w-auto overflow-hidden pointer-events-auto">
        <div className="pointer-events-none absolute inset-0 z-[2] h-full w-full overflow-hidden" />
        <DivGrid
          key={`base-${rippleKey}`}
          className={cn(
            "mask-radial-from-20% mask-radial-at-top opacity-60",
            gridClassName,
          )}
          rows={rows}
          cols={cols}
          cellSize={cellSize}
          borderColor="var(--cell-border-color)"
          fillColor="var(--cell-fill-color)"
          clickedCell={clickedCell}
          onCellClick={(row, col) => {
            setClickedCell({ row, col });
            setRippleKey((k) => k + 1);
          }}
          interactive
        />
      </div>
    </div>
  );
}

type DivGridProps = {
  className?: string;
  rows: number;
  cols: number;
  cellSize: number;
  borderColor: string;
  fillColor: string;
  clickedCell: { row: number; col: number } | null;
  onCellClick?: (row: number, col: number) => void;
  interactive?: boolean;
};

type CellStyle = React.CSSProperties & {
  ["--delay"]?: string;
  ["--duration"]?: string;
};

function DivGrid({
  className,
  rows = 7,
  cols = 30,
  cellSize = 56,
  borderColor = "#3f3f46",
  fillColor = "rgba(14,165,233,0.3)",
  clickedCell = null,
  onCellClick = () => {},
  interactive = true,
}: DivGridProps) {
  const cells = useMemo(
    () => Array.from({ length: rows * cols }, (_, idx) => idx),
    [rows, cols],
  );

  const gridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: `repeat(${cols}, ${cellSize}px)`,
    gridTemplateRows: `repeat(${rows}, ${cellSize}px)`,
    width: cols * cellSize,
    height: rows * cellSize,
    marginInline: "auto",
  };

  return (
    <div className={cn("relative z-[3]", className)} style={gridStyle}>
      {cells.map((idx) => {
        const rowIdx = Math.floor(idx / cols);
        const colIdx = idx % cols;
        const distance = clickedCell
          ? Math.hypot(clickedCell.row - rowIdx, clickedCell.col - colIdx)
          : 0;
        const delay = clickedCell ? Math.max(0, distance * 55) : 0;
        const duration = 200 + distance * 80;

        const style: CellStyle = clickedCell
          ? {
              "--delay": `${delay}ms`,
              "--duration": `${duration}ms`,
            }
          : {};

        return (
          <div
            key={idx}
            className={cn(
              "cell relative border-[0.5px] opacity-40 transition-[opacity,border-color,background-color,box-shadow] duration-150 will-change-transform",
              "shadow-[0px_0px_40px_1px_var(--cell-shadow-color)_inset]",
              "hover:opacity-80 hover:border-[var(--cell-border-hover)] hover:bg-[var(--cell-fill-hover)]",
              clickedCell &&
                "animate-cell-ripple [animation-fill-mode:none] border-[var(--cell-border-hover)] bg-[var(--cell-fill-hover)]",
              !interactive && "pointer-events-none",
            )}
            style={{
              backgroundColor: fillColor,
              borderColor: borderColor,
              ...style,
            }}
            onClick={
              interactive ? () => onCellClick?.(rowIdx, colIdx) : undefined
            }
          />
        );
      })}
    </div>
  );
}
