"use client";

import { motion } from "framer-motion";

const EASE_OUT_EXPO: [number, number, number, number] = [0.16, 1, 0.3, 1];

type ClientLogo = {
  name: string;
  src: string;
};

/** Single-row “Trusted by” set — matches the inspected layout. */
const CLIENTS: readonly ClientLogo[] = [
  { name: "AT3 Internet", src: "/brands/clients/at3.png" },
  { name: "Colibri Festas", src: "/brands/clients/colibri.png" },
  { name: "Loga Internet", src: "/brands/clients/loga.png" },
  { name: "Netsul Internet", src: "/brands/clients/netsul.png" },
  { name: "Vinsel Vinhos", src: "/brands/clients/vinsel.png" },
] as const;

export function AboutClients() {
  return (
    <div className="about-clients" aria-labelledby="about-clients-heading">
      <h2 id="about-clients-heading" className="about-clients__title">
        Nossos clientes
      </h2>

      <div className="about-clients__logos">
        {CLIENTS.map((client, index) => (
          <motion.div
            key={client.name}
            className="about-clients__logo-wrap"
            initial={{ opacity: 0, filter: "blur(8px)", y: 6 }}
            whileInView={{ opacity: 1, filter: "blur(0px)", y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{
              duration: 0.7,
              ease: EASE_OUT_EXPO,
              delay: 0.08 * index,
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- local brand crops */}
            <img
              src={client.src}
              alt={client.name}
              className="about-clients__logo"
              loading="lazy"
              decoding="async"
              draggable={false}
            />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
