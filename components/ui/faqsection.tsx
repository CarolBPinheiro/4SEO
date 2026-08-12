"use client";

import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Parallax } from "@/components/ui/parallax-scrolling";
import { Reveal } from "@/components/ui/Reveal";
import { cn } from "@/lib/utils";

export type FAQItem = {
  question: string;
  answer: string;
};

export type FAQSectionProps = {
  title?: string;
  subtitle?: string;
  description?: string;
  buttonLabel?: string;
  buttonHref?: string;
  faqsLeft: FAQItem[];
  faqsRight: FAQItem[];
  className?: string;
  id?: string;
};

function FAQAccordionItem({
  item,
  isOpen,
  onToggle,
}: {
  item: FAQItem;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const panelId = useId();
  const buttonId = useId();

  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl border transition-colors duration-200",
        isOpen
          ? "border-brand/30 bg-white/[0.04]"
          : "border-white/10 bg-white/[0.03] hover:border-white/16",
      )}
    >
      <h3 className="m-0">
        <button
          id={buttonId}
          type="button"
          aria-expanded={isOpen}
          aria-controls={panelId}
          onClick={onToggle}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-base font-medium tracking-tight text-white transition-colors duration-200 hover:text-white/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60 focus-visible:ring-offset-2 focus-visible:ring-offset-[#050506] sm:px-6 sm:py-5"
        >
          <span>{item.question}</span>
          <ChevronDown
            className={cn(
              "h-5 w-5 shrink-0 text-white/50 transition-transform duration-200",
              isOpen && "rotate-180",
            )}
            aria-hidden
          />
        </button>
      </h3>

      <div
        id={panelId}
        role="region"
        aria-labelledby={buttonId}
        className={cn(
          "grid transition-[grid-template-rows] duration-300 ease-out",
          isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <p className="px-5 pb-5 text-[15px] leading-relaxed tracking-[-0.01em] text-white/55 sm:px-6 sm:pb-6">
            {item.answer}
          </p>
        </div>
      </div>
    </div>
  );
}

function FAQColumn({
  items,
  openKey,
  columnKey,
  onToggle,
}: {
  items: FAQItem[];
  openKey: string | null;
  columnKey: "left" | "right";
  onToggle: (key: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {items.map((item, index) => {
        const key = `${columnKey}-${index}`;
        return (
          <FAQAccordionItem
            key={key}
            item={item}
            isOpen={openKey === key}
            onToggle={() => onToggle(key)}
          />
        );
      })}
    </div>
  );
}

export function FAQSection({
  title = "Perguntas frequentes",
  subtitle,
  description,
  buttonLabel,
  buttonHref = "#",
  faqsLeft,
  faqsRight,
  className,
  id = "faq",
}: FAQSectionProps): ReactNode {
  const [openKey, setOpenKey] = useState<string | null>("left-0");
  const headingId = useId();

  const handleToggle = (key: string) => {
    setOpenKey((current) => (current === key ? null : key));
  };

  return (
    <section
      id={id}
      className={cn(
        "relative scroll-mt-28 overflow-hidden px-4 py-20 lg:py-24",
        className,
      )}
      aria-labelledby={headingId}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[#050506]"
      />

      <div className="relative mx-auto max-w-6xl">
        <Reveal>
          <Parallax
            start={8}
            end={-8}
            disable="mobile"
            scrub={0.55}
            className="will-change-transform"
          >
            <div className="mx-auto max-w-3xl text-center">
              {subtitle ? (
                <p className="mb-4 text-xs font-medium tracking-[0.18em] text-brand uppercase sm:text-[13px]">
                  {subtitle}
                </p>
              ) : null}

              <h2
                id={headingId}
                className="text-[clamp(2rem,4vw,2.75rem)] font-bold leading-[1.1] tracking-[-0.02em] text-white"
              >
                {title}
              </h2>

              {description ? (
                <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed tracking-[-0.01em] text-white/65 sm:text-[1.05rem]">
                  {description}
                </p>
              ) : null}

              {buttonLabel ? (
                <a
                  href={buttonHref}
                  className="btn-secondary mt-8 inline-flex rounded-full px-5"
                >
                  {buttonLabel}
                </a>
              ) : null}
            </div>
          </Parallax>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 items-start gap-3 md:mt-14 md:grid-cols-2 md:gap-5">
          <FAQColumn
            items={faqsLeft}
            openKey={openKey}
            columnKey="left"
            onToggle={handleToggle}
          />
          <FAQColumn
            items={faqsRight}
            openKey={openKey}
            columnKey="right"
            onToggle={handleToggle}
          />
        </div>
      </div>
    </section>
  );
}
