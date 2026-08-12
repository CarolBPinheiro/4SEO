import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, Menu, Store, ShoppingBag, Sparkles, FileSearch, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";

const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { to: "/shopify", label: "Shopify", icon: Store },
    { to: "/nuvemshop", label: "Nuvemshop", icon: ShoppingBag },
    { to: "/app", label: "Auditoria", icon: FileSearch },
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  ];

  const NavItems = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      {navLinks.map((link) => {
        const isActive = location.pathname === link.to;
        const Icon = link.icon;
        return (
          <Link
            key={link.to}
            to={link.to}
            onClick={() => mobile && setMobileMenuOpen(false)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
            } ${mobile ? "w-full" : ""}`}
          >
            <Icon className="w-4 h-4" />
            {link.label}
          </Link>
        );
      })}
    </>
  );

  return (
    <header className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-border bg-background/95 backdrop-blur-md sticky top-0 z-30">
      <div className="flex items-center gap-4 sm:gap-6">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg btn-gradient flex items-center justify-center text-primary-foreground font-extrabold text-sm shadow-md">
            4
          </div>
          <span className="font-bold text-lg sm:text-xl tracking-wider">
            4<span className="text-primary">SEO</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          <NavItems />
        </nav>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Badge */}
        <Badge variant="secondary" className="hidden sm:flex">
          4SEO V.1.0
        </Badge>

        {/* Sair */}
        <Button variant="ghost" size="sm" onClick={() => navigate("/")} className="hidden sm:flex gap-2 hover:text-[#040406]">
          <LogOut className="w-4 h-4" />
          Sair
        </Button>

        {/* Mobile Menu */}
        <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button variant="ghost" size="icon" className="h-9 w-9">
              <Menu className="w-5 h-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[280px] bg-background border-border">
            <div className="flex items-center gap-2 mb-6 pt-2">
              <div className="w-7 h-7 rounded-lg btn-gradient flex items-center justify-center text-primary-foreground font-extrabold text-sm">
                4
              </div>
              <span className="font-bold text-lg tracking-wider">
                4<span className="text-primary">SEO</span>
              </span>
            </div>
            <nav className="flex flex-col gap-1">
              <NavItems mobile />
              <button
                onClick={() => { setMobileMenuOpen(false); navigate("/"); }}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted w-full mt-2 border-t pt-3"
              >
                <LogOut className="w-4 h-4" />
                Sair
              </button>
            </nav>
            <div className="absolute bottom-6 left-6 right-6">
              <div className="p-3 rounded-lg bg-muted/50">
                <p className="text-xs text-muted-foreground">4SEO V.1.0</p>
                <p className="text-xs text-primary">Análise SEO + Otimização</p>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
};

export default Header;
