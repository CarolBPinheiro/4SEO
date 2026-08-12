import type { Metadata } from "next";
import { AboutContent } from "@/components/about/AboutContent";
import { Footer } from "@/components/landing/Footer";
import { SiteNavbar } from "@/components/landing/Navbar";
import { ParallaxComponent } from "@/components/ui/parallax-scrolling";

export const metadata: Metadata = {
  title: "Sobre nós | 4SEO",
  description:
    "Escalando seu negócio de forma inteligente. Conheça a 4Scale Marketing e Tecnologia — estratégia, criatividade e tecnologia para impulsionar o crescimento.",
};

export default function SobrePage() {
  return (
    <ParallaxComponent>
      <SiteNavbar />
      <AboutContent />
      <Footer />
    </ParallaxComponent>
  );
}
