"use client";

import { InfiniteSlider } from "@/components/ui/infinite-slider";
import { ProgressiveBlur } from "@/components/ui/progressive-blur";
import { cn } from "@/lib/utils";

export type CustomerLogo = {
  src: string;
  alt: string;
  height: number;
  /** Visible brand name next to the mark. Defaults to `alt`. */
  name?: string;
};

export type CustomersSectionProps = {
  customers: CustomerLogo[];
  className?: string;
  "aria-label"?: string;
};

export function CustomersSection({
  customers,
  className,
  "aria-label": ariaLabel = "Plataformas compatíveis",
}: CustomersSectionProps) {
  if (customers.length === 0) {
    return null;
  }

  // Enough items for a seamless loop on wide viewports without inventing brands.
  const loopItems =
    customers.length < 6
      ? [...customers, ...customers, ...customers]
      : customers;

  return (
    <div
      className={cn("relative overflow-hidden", className)}
      role="region"
      aria-label={ariaLabel}
    >
      <ul className="sr-only">
        {customers.map((customer) => (
          <li key={customer.alt}>{customer.name ?? customer.alt}</li>
        ))}
      </ul>

      <div aria-hidden="true">
        <InfiniteSlider
          speed={40}
          speedOnHover={20}
          gap={72}
          className="py-6 sm:py-8 lg:py-10"
        >
          {loopItems.map((customer, index) => {
            const label = customer.name ?? customer.alt;

            return (
              <div
                key={`${customer.alt}-${index}`}
                className="flex h-16 shrink-0 items-center gap-3 px-2 sm:h-20 sm:gap-3.5 lg:h-24 lg:gap-4"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- remote brand CDNs; next/image remotePatterns not required */}
                <img
                  src={customer.src}
                  alt=""
                  height={customer.height}
                  width={customer.height}
                  className="h-7 w-7 shrink-0 object-contain opacity-70 sm:h-8 sm:w-8 lg:h-9 lg:w-9"
                  loading="lazy"
                  decoding="async"
                  draggable={false}
                />
                <span className="whitespace-nowrap text-[1.05rem] font-semibold tracking-[-0.02em] text-white/70 sm:text-xl lg:text-[1.35rem]">
                  {label}
                </span>
              </div>
            );
          })}
        </InfiniteSlider>

        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-20 bg-gradient-to-r from-[#050506] to-transparent sm:w-32 lg:w-40" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-20 bg-gradient-to-l from-[#050506] to-transparent sm:w-32 lg:w-40" />

        <ProgressiveBlur
          className="pointer-events-none absolute top-0 left-0 z-10 h-full w-20 sm:w-32 lg:w-40"
          direction="left"
          blurIntensity={0.6}
        />
        <ProgressiveBlur
          className="pointer-events-none absolute top-0 right-0 z-10 h-full w-20 sm:w-32 lg:w-40"
          direction="right"
          blurIntensity={0.6}
        />
      </div>
    </div>
  );
}
