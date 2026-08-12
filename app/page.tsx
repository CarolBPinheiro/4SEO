import { FAQ } from "@/components/landing/FAQ";
import { Features } from "@/components/landing/Features";
import { Footer } from "@/components/landing/Footer";
import { Hero } from "@/components/landing/Hero";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Integrations } from "@/components/landing/Integrations";
import { SiteNavbar } from "@/components/landing/Navbar";
import { Pricing } from "@/components/landing/Pricing";
import { Problem } from "@/components/landing/Problem";
import { ProductDemo } from "@/components/landing/ProductDemo";
import { ParallaxComponent } from "@/components/ui/parallax-scrolling";

export default function Home() {
  return (
    <ParallaxComponent>
      <SiteNavbar />
      <main className="overflow-x-clip">
        <Hero />
        <Problem />
        <ProductDemo />
        <HowItWorks />
        <Features />
        <Integrations />
        <Pricing />
        <FAQ />
      </main>
      <Footer />
    </ParallaxComponent>
  );
}
